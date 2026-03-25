"""
🤖 BOTLIVE API - Routes pour intégration Frontend/N8N
Endpoints pour le système de commandes en direct
"""

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging
import time
import uuid
import asyncio
from datetime import datetime
import os
import httpx
import re

from config import N8N_OUTBOUND_WEBHOOK_URL, N8N_API_KEY, N8N_DEBUG_MODE
from core.intervention_logger import log_intervention_in_conversation_logs, log_message_in_conversation_logs, upsert_required_intervention
from core.intervention_guardian import get_intervention_guardian
from core.production_pipeline import ProductionPipeline
from core.rule_overrides import RuleOverrides
from config import BOTLIVE_COOPERATIVE_HUMAN_MODE
from core.order_state_tracker import order_tracker

logger = logging.getLogger(__name__)

production_pipeline = ProductionPipeline()

_PENDING_HUMAN: Dict[str, Dict[str, Any]] = {}

FAREWELL_PATTERNS = [
    "bonne continuation",
    "au revoir",
    "a bientot",
    "à bientôt",
    "bonne journée",
    "bonne journee",
    "bonne soirée",
    "bonne soiree",
    "bonne nuit",
    "merci bye",
    "bye",
    "ciao",
]

# Messages de handoff contextuels par intent
HANDOFF_MESSAGES = {
    "SAV_SUIVI": {
        "tracking": "Je transfère ta demande de suivi à l'équipe ! Un instant. 📦",
        "probleme": "Je comprends ton problème. L'équipe SAV va te contacter rapidement ! 🙏",
        "reclamation": "Je note ta réclamation et la transmets immédiatement à l'équipe. 💬",
        "default": "Je transfère ta demande à l'équipe qui va t'aider au plus vite ! 😊"
    },
    "MODIFICATION_COMMANDE": {
        "default": "Je transmets ta demande de modification à l'équipe. Un instant ! ✏️"
    },
    "HORS_ZONE": {
        "default": "On ne livre pas encore dans ta zone 😔 mais je note ta demande pour l'équipe !"
    },
    "QUESTION_TECHNIQUE": {
        "default": "Je transfère ta question technique à un expert qui va te répondre ! 🔧"
    },
    "DEFAULT": {
        "default": "Je transfère ta demande à l'équipe. Un instant ! 😊"
    }
}

def get_handoff_message(intent: str, message_text: str = "") -> str:
    """Retourne un message contextuel selon l'intent et le contenu du message.
    
    Args:
        intent: Intent détecté (SAV_SUIVI, MODIFICATION_COMMANDE, etc.)
        message_text: Message original de l'utilisateur
        
    Returns:
        Message de transfert empathique et contextualisé
    """
    intent_messages = HANDOFF_MESSAGES.get(intent, HANDOFF_MESSAGES["DEFAULT"])
    
    # Détection du sous-type pour SAV_SUIVI
    if intent == "SAV_SUIVI":
        message_lower = (message_text or "").lower()
        # Normalisation légère: on garde aussi une version sans accents pour matcher robustement
        try:
            message_ascii = (
                message_lower
                .replace("à", "a")
                .replace("â", "a")
                .replace("ä", "a")
                .replace("é", "e")
                .replace("è", "e")
                .replace("ê", "e")
                .replace("ë", "e")
                .replace("î", "i")
                .replace("ï", "i")
                .replace("ô", "o")
                .replace("ö", "o")
                .replace("ù", "u")
                .replace("û", "u")
                .replace("ü", "u")
                .replace("ç", "c")
            )
        except Exception:
            message_ascii = message_lower

        def _has_word(*words: str) -> bool:
            # Match mots entiers pour éviter les faux positifs (ex: "ou" dans "remboursement")
            for w in words:
                if not w:
                    continue
                pattern = r"\\b" + re.escape(w) + r"\\b"
                if re.search(pattern, message_lower, flags=re.IGNORECASE) or re.search(pattern, message_ascii, flags=re.IGNORECASE):
                    return True
            return False

        def _has_any_substring(*subs: str) -> bool:
            for s in subs:
                if s and (s in message_lower or s in message_ascii):
                    return True
            return False

        # IMPORTANT: ordre de priorité
        # 1) Réclamation / Retour
        if _has_any_substring(
            "remboursement",
            "rembourser",
            "rembourse",
            "retour",
            "retourner",
            "annulation",
            "annuler",
            "reclamation",
            "réclamation",
            "insatisfait",
            "insatisfaite",
        ):
            return intent_messages["reclamation"]

        # 2) Problème / Défaut
        if _has_any_substring(
            "abime",
            "abîme",
            "abimee",
            "abîmée",
            "casse",
            "cassé",
            "cassee",
            "cassée",
            "probleme",
            "problème",
            "defaut",
            "défaut",
            "manque",
            "manquant",
            "incomplet",
        ):
            return intent_messages["probleme"]

        # 3) Tracking / Suivi (sans "ou" qui provoque des faux positifs)
        if (
            _has_word("ou", "où", "quand")
            or _has_any_substring("arrive", "livraison", "delai", "délai", "colis", "suivi", "tracking")
        ):
            return intent_messages["tracking"]
    
    return intent_messages["default"]


def _pending_key(company_id: str, user_id: str) -> str:
    return f"{company_id}::{user_id}"

ENABLE_POST_RECAP_STOP_FLOW = False

router = APIRouter(prefix="/botlive", tags=["botlive"])
shared_router = APIRouter(prefix="/botliveandrag", tags=["botliveandrag"])

DISABLE_VISION_MODELS = os.getenv("DISABLE_VISION_MODELS", "false").lower() == "true"

# ═══════════════════════════════════════════════════════════════════════════════
# 📋 MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class BotliveMessageRequest(BaseModel):
    """Requête pour envoyer un message au bot"""
    company_id: str = Field(..., description="ID de l'entreprise")
    user_id: str = Field(..., description="ID utilisateur (numéro WhatsApp/Messenger)")
    message: str = Field(default="", description="Message texte")
    images: List[str] = Field(default=[], description="URLs des images")
    conversation_history: str = Field(default="", description="Historique conversation")
    user_display_name: Optional[str] = Field(default=None, description="Nom affiché du client (si disponible)")

class BotliveStatsRequest(BaseModel):
    """Requête pour les statistiques"""
    company_id: str
    time_range: str = Field(default="today", description="today, week, month")

class BotliveOrderStatusRequest(BaseModel):
    """Requête pour vérifier le statut d'une commande"""
    user_id: str
    company_id: str


class HumanReplyRequest(BaseModel):
    """Requête pour une réponse humaine envoyée depuis le dashboard.

    Cette requête est simplement relayée vers un webhook N8N dédié qui :
    - loggue dans conversation_logs
    - envoie le message au client (Messenger, etc.)
    """

    company_id: str = Field(..., description="ID texte de l'entreprise (company_id_text)")
    user_id: str = Field(..., description="ID utilisateur final (PSID Messenger, numéro WhatsApp, etc.)")
    message: str = Field(..., description="Message saisi par l'opérateur")
    images: List[str] = Field(default_factory=list, description="URLs des images jointes (optionnel)")
    channel: str = Field("messenger", description="Canal de communication : messenger, whatsapp, ...")
    user_display_name: Optional[str] = Field(
        default=None,
        description="Nom affiché du client (facilite l'affichage dans le dashboard)",
    )
    page_id: Optional[str] = Field(
        default=None,
        description="ID de la page (ex: page Facebook Messenger)",
    )

class SharedInterventionCheckRequest(BaseModel):
    company_id: str = Field(..., description="ID texte de l'entreprise")
    user_id: str = Field(..., description="ID utilisateur")
    user_message: str = Field(default="", description="Dernier message client")
    bot_response: str = Field(default="", description="Dernière réponse bot")
    conversation_history: str = Field(default="", description="Historique conversationnel sérialisé")
    order_state: Dict[str, Any] = Field(default_factory=dict, description="État commande courant")
    next_step: str = Field(default="", description="Étape courante")
    source: str = Field(default="shared", description="Source appelante")
    log_intervention: bool = Field(default=True, description="Persister ou non l'intervention")
    channel: str = Field(default="whatsapp", description="Canal conversationnel")

class WebhookConfig(BaseModel):
    """Configuration webhook N8N"""
    webhook_url: str = Field(..., description="URL webhook N8N")
    events: List[str] = Field(default=["order_completed", "payment_validated", "intervention_required"])
    company_id: str

class DepositRequest(BaseModel):
    company_id: str = Field(..., description="ID de l'entreprise")
    amount_xof: int = Field(..., description="Montant de l'acompte en XOF")
    order_id: Optional[str] = None
    payment_method: Optional[str] = None
    validated_by: str = "ocr_easy"


class UpdateOrderStatusRequest(BaseModel):
    """Requête pour mettre à jour le statut d'une commande (orders.status)."""
    status: str


class BotPauseRequest(BaseModel):
    company_id: str
    user_id: str
    enabled: bool

def _compute_rule_based_intervention(msg_text: str) -> Dict[str, Any]:
    msg_text = msg_text or ""
    msg_lower = msg_text.lower()

    # --- 1. Explicit handoff ---
    explicit_handoff_keywords = [
        "parler a un humain", "parler à un humain", "parler a quelqu'un",
        "parler à quelqu'un", "parler a un conseiller", "parler à un conseiller",
        "parler a un agent", "parler à un agent", "parler a quelquun",
        "parler à quelquun", "un humain", "un agent", "service client",
        "conseiller", "un humain stp", "un humain svp",
        "un humain s'il vous plait", "un humain s il vous plait",
    ]
    explicit_handoff = any(kw in msg_lower for kw in explicit_handoff_keywords)

    # --- 2. Frustration ---
    caps_ratio = 0.0
    letters = [c for c in msg_text if c.isalpha()]
    if letters:
        caps = [c for c in letters if c.isupper()]
        if caps:
            caps_ratio = len(caps) / len(letters)
    negative_keywords = [
        "service de merde", "arnaque", "scandale", "nul", "nulle", "honte",
        "rembourse", "remboursement", "pas content", "mécontent", "mecontent",
        "insatisfait", "insatisfaite", "catastrophe", "pourri", "inadmissible",
        "voleur", "voleurs", "escroc", "escrocs", "je vais porter plainte",
        "porter plainte", "tribunal", "inacceptable",
    ]
    is_frustrated = caps_ratio > 0.7 or any(kw in msg_lower for kw in negative_keywords)

    # --- 3. SAV / réclamation ---
    sav_keywords = [
        "ma commande", "mon colis", "pas reçu", "pas recu", "pas livré",
        "pas livre", "en retard", "retard livraison", "mauvais produit",
        "produit cassé", "produit casse", "erreur commande", "commande erronée",
        "commande erronee", "je veux un remboursement", "j'ai pas reçu",
        "j ai pas recu", "ou est ma commande", "où est ma commande",
        "suivi commande", "suivi de commande", "numéro de suivi",
        "numero de suivi", "quand est-ce que je recois", "quand est ce que je recois",
    ]
    is_sav = any(kw in msg_lower for kw in sav_keywords)

    # --- 4. Payment mention ---
    payment_keywords = [
        "j'ai payé", "j ai paye", "j'ai envoyé", "j ai envoye",
        "j'ai fait le paiement", "j ai fait le paiement",
        "wave ne marche pas", "paiement refusé", "paiement refuse",
        "problème paiement", "probleme paiement", "erreur paiement",
        "montant incorrect", "mauvais montant",
    ]
    is_payment_issue = any(kw in msg_lower for kw in payment_keywords)

    # --- Priority: explicit_handoff > frustration > sav > payment ---
    reason = None
    if explicit_handoff:
        reason = "explicit_handoff"
    elif is_frustrated:
        reason = "customer_frustration"
    elif is_sav:
        reason = "sav_issue"
    elif is_payment_issue:
        reason = "payment_issue"

    return {
        "explicit_handoff": explicit_handoff,
        "is_frustrated": is_frustrated,
        "is_sav": is_sav,
        "is_payment_issue": is_payment_issue,
        "caps_ratio": caps_ratio,
        "reason": reason,
        "requires_intervention": bool(reason),
    }


def _compute_context_based_intervention(
    order_state: Dict[str, Any],
    next_step: str,
    bot_response: str,
    source: str,
) -> Optional[Dict[str, Any]]:
    """Détection d'intervention basée sur le contexte commande/conversation.

    Retourne un dict {reason, priority} si intervention détectée, None sinon.
    """
    order_state = order_state or {}
    next_step = (next_step or "").lower().strip()
    bot_response = (bot_response or "").lower()

    # --- order_blocked: commande en cours mais bloquée ---
    # Détection robuste : temps réel depuis last_progress + nombre de relances bot
    completion = order_state.get("completion_rate")
    try:
        completion = float(completion) if completion is not None else None
    except (ValueError, TypeError):
        completion = None
    if completion is not None and 0 < completion < 1.0:
        user_id_ctx = order_state.get("user_id") or order_state.get("_user_id", "")
        if user_id_ctx:
            try:
                from core.order_state_tracker import order_tracker as _ot
                _mins = _ot.get_minutes_since_last_progress(user_id_ctx)
                _relances = _ot.get_bot_relance_count(user_id_ctx)
                if _mins >= 30 and _relances >= 2:
                    return {"reason": "order_blocked", "priority": "high"}
            except Exception:
                pass
        # Fallback legacy si user_id non disponible dans order_state
        stale_turns = order_state.get("stale_turns") or 0
        try:
            stale_turns = int(stale_turns)
        except (ValueError, TypeError):
            stale_turns = 0
        if stale_turns >= 4:
            return {"reason": "order_blocked", "priority": "high"}

    # --- post_order_followup: désactivé (off) — non-critique, éviter spam opérateur ---
    # is_complete = order_state.get("is_complete") or order_state.get("completed") or False
    # if is_complete and source in ("botlive", "ragbot", "shared"):
    #     return {"reason": "post_order_followup", "priority": "normal"}

    # --- payment_issue: OCR échoué plusieurs fois OU paiement non confirmé ---
    user_id_pay = order_state.get("user_id") or order_state.get("_user_id", "")
    ocr_fail_count = 0
    if user_id_pay:
        try:
            from core.order_state_tracker import order_tracker as _ot
            ocr_fail_count = _ot.get_ocr_fail_count(user_id_pay)
        except Exception:
            pass
    # Fallback: flag binaire legacy
    pay_err = order_state.get("payment_error") or order_state.get("ocr_error")
    payment_mismatch = str(order_state.get("paiement") or "").upper()
    payment_mismatch_flag = payment_mismatch.startswith("INSUFFISANT") or payment_mismatch.startswith("REFUS")
    if ocr_fail_count >= 2 or (pay_err and next_step in ("paiement", "request_wave")) or (payment_mismatch_flag and next_step in ("paiement", "request_wave")):
        return {"reason": "payment_issue", "priority": "high"}

    return None

# ═══════════════════════════════════════════════════════════════════════════════
# 🔥 ENDPOINTS PRINCIPAUX
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/message")
async def process_botlive_message(req: BotliveMessageRequest, background_tasks: BackgroundTasks):
    """
    🎯 ENDPOINT PRINCIPAL - Traite un message utilisateur (texte + images)
    
    Utilisé par:
    - Frontend (interface chat)
    - N8N (orchestration WhatsApp/Messenger)
    
    Returns:
        {
            "response": "Réponse du bot",
            "order_status": {...},
            "next_step": "produit|paiement|zone|numero|completed"
        }
    """
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    logger.info(f"[BOTLIVE][{request_id}] Message reçu: user={req.user_id}, company={req.company_id}")
    
    try:
        # Shadow Mode: enregistre le message client (mode écoute, sans intervention)
        try:
            if os.getenv("SHADOW_MODE_ENABLED", "true").lower() == "true":
                from core.shadow_recorder import record_user_message
                await record_user_message(req.company_id, req.user_id, req.message or "", req.user_display_name)
        except Exception:
            # Ne jamais casser le flux si la capture échoue
            pass
        # Détection simple d'escalade explicite ou de frustration forte
        msg_text = req.message or ""
        msg_lower = msg_text.lower()

        if msg_lower and any(p in msg_lower for p in FAREWELL_PATTERNS):
            return JSONResponse(
                content={
                    "success": True,
                    "response": "Merci à vous ! Bonne continuation ! 😊",
                    "status": "OK",
                    "human_required": False,
                    "bypass_llm": True,
                    "llm_used": None,
                    "intent": "FAREWELL",
                    "confidence": 0.95,
                    "mode": "REASSURANCE",
                    "source": "python",
                    "cache_hit": False,
                    "missing_fields": [],
                    "router_metrics": {
                        "intent": "FAREWELL",
                        "confidence": 0.95,
                        "mode": "REASSURANCE",
                        "router_source": "prefilter_farewell",
                    },
                    "order_status": {
                        "produit": "",
                        "paiement": "",
                        "zone": "",
                        "numero": "",
                        "completion_rate": 0.0,
                        "is_complete": False,
                    },
                    "next_step": "produit",
                    "duration_ms": int((time.time() - start_time) * 1000),
                    "request_id": request_id,
                },
                media_type="application/json; charset=utf-8",
            )

        # Utiliser le moteur partagé de détection rule-based
        rule_result = _compute_rule_based_intervention(msg_text)
        explicit_handoff = rule_result.get("explicit_handoff", False)
        is_frustrated = rule_result.get("is_frustrated", False)
        caps_ratio = rule_result.get("caps_ratio", 0.0)

        logger.info(
            "[BOTLIVE][%s] Intervention signals (shared engine) | explicit_handoff=%s is_frustrated=%s caps_ratio=%.2f",
            request_id,
            explicit_handoff,
            is_frustrated,
            caps_ratio,
        )

        if rule_result.get("requires_intervention"):
            reason = rule_result.get("reason", "explicit_handoff")
            # Actifs : seulement les 3 triggers infaillibles
            _ACTIVE_TRIGGERS = {"explicit_handoff", "order_blocked", "payment_issue"}
            try:
                logger.info(
                    "[BOTLIVE][%s] Intervention (rule-based, shared engine) triggered | reason=%s message=%s",
                    request_id,
                    reason,
                    msg_text,
                )
                await log_intervention_in_conversation_logs(
                    company_id_text=req.company_id,
                    user_id=req.user_id,
                    message=msg_text,
                    metadata={
                        "needs_intervention": True,
                        "reason": reason,
                        "priority": "high",
                        "caps_ratio": caps_ratio,
                        "detected_by": "rule_based",
                        "source_bot": "botlive",
                    },
                    channel="botlive",
                    direction="user",
                    source="botlive_gateway",
                )
                # Écrire dans required_interventions uniquement pour les 3 types actifs
                if reason in _ACTIVE_TRIGGERS:
                    try:
                        order_tracker.set_flag(req.user_id, "bot_paused", True)
                        order_tracker.set_custom_meta(req.user_id, "bot_paused_at", datetime.now().isoformat())
                        order_tracker.set_custom_meta(req.user_id, "bot_paused_by", reason)
                    except Exception:
                        pass
                    await upsert_required_intervention(
                        company_id=req.company_id,
                        user_id=req.user_id,
                        channel="whatsapp",
                        intervention_type=reason,
                        priority="critical" if reason == "explicit_handoff" else "high",
                        detected_by="rule_based",
                        source_bot="botlive",
                        reason=f"Détecté par règles dures | caps_ratio={caps_ratio:.2f}",
                        user_message=msg_text[:500],
                    )
                    logger.info("[BOTLIVE][%s] ✅ upsert_required_intervention OK | type=%s", request_id, reason)
            except Exception as log_err:
                logger.error("[BOTLIVE][%s] Failed to log explicit/frustration intervention: %s", request_id, log_err)

        # Traiter le message
        user_display_name = req.user_display_name

        # Vérifier si la commande est déjà complétée AVANT d'appeler le moteur Botlive
        pre_order_status = await get_order_state(req.user_id, req.company_id)
        pre_next_step = _determine_next_step(pre_order_status)

        post_recap = bool(pre_order_status.get("is_complete")) or pre_next_step == "completed"

        if ENABLE_POST_RECAP_STOP_FLOW and post_recap:
            # Après récap/confirmation de commande, tout nouveau message client déclenche
            # automatiquement une intervention humaine et le bot ne répond plus.
            logger.info(
                "[BOTLIVE][%s] Post-recap message detected -> auto intervention, no bot reply",
                request_id,
            )

            conversation_id = None
            try:
                from core.activities_logger import log_new_conversation
                logger.info(
                    "[BOTLIVE][%s] (post-recap) Début logging conversation: company_id=%s user_id=%s",
                    request_id,
                    req.company_id,
                    req.user_id,
                )

                conversation_id = await get_or_create_conversation(
                    req.company_id,
                    req.user_id,
                    user_display_name,
                )
                logger.info(
                    "[BOTLIVE][%s] (post-recap) get_or_create_conversation -> %s",
                    request_id,
                    conversation_id,
                )

                if not conversation_id:
                    logger.warning(
                        "[BOTLIVE][%s] (post-recap) Aucune conversation_id retournee, skip insert_message/log_new_conversation",
                        request_id,
                    )
                else:
                    user_metadata: Dict[str, Any] = {
                        "source": "botlive",
                        "channel": "messenger",
                        "user_id": req.user_id,
                    }
                    if user_display_name:
                        user_metadata["user_display_name"] = user_display_name

                    author_name = user_display_name or req.user_id[-4:]

                    user_ok = await insert_message(
                        conversation_id,
                        "user",
                        req.message or "",
                        {**user_metadata, "author_name": author_name},
                    )
                    logger.info(
                        "[BOTLIVE][%s] (post-recap) insert_message user -> %s",
                        request_id,
                        user_ok,
                    )

                    activity_ok = await log_new_conversation(
                        req.company_id,
                        req.user_id,
                        conversation_id,
                        user_display_name,
                    )
                    logger.info(
                        "[BOTLIVE][%s] (post-recap) log_new_conversation -> %s",
                        request_id,
                        activity_ok,
                    )
            except Exception as conv_err:
                logger.error(
                    f"[BOTLIVE][{request_id}] (post-recap) Erreur logging conversation/messages: {conv_err}",
                    exc_info=True,
                )

            try:
                await log_intervention_in_conversation_logs(
                    company_id_text=req.company_id,
                    user_id=req.user_id,
                    message=req.message or "[Post-recap] Nouveau message client après commande confirmée",
                    metadata={
                        "needs_intervention": True,
                        "reason": "post_recap_followup",
                        "priority": "high",
                    },
                    channel="botlive",
                    direction="user",
                    source="botlive_post_recap",
                )
            except Exception as log_err:
                logger.error(
                    "[BOTLIVE][%s] (post-recap) Failed to log post-recap intervention: %s",
                    request_id,
                    log_err,
                )

            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(
                "[BOTLIVE][%s] (post-recap) Intervention routed to human, duration_ms=%s",
                request_id,
                duration_ms,
            )

            return JSONResponse(
                content={
                    "success": True,
                    "response": "",
                    "order_status": pre_order_status,
                    "next_step": "completed",
                    "duration_ms": duration_ms,
                    "request_id": request_id,
                }
            )

        # Construire automatiquement l'historique depuis Supabase (conversations + messages)
        # NOTE: en local/simulateur on veut pouvoir bypass Supabase pour éviter timeouts.
        skip_supabase_history = os.getenv("BOTLIVE_SKIP_SUPABASE_HISTORY", "false").strip().lower() in {"1", "true", "yes", "y", "on"}
        if skip_supabase_history or (req.conversation_history or "").strip():
            conversation_history = req.conversation_history or ""
        else:
            conversation_history = await _build_conversation_history_from_messages(
                company_id=req.company_id,
                user_id=req.user_id,
            )

        # ═══════════════════════════════════════════════════════════════
        # RULE OVERRIDES (avant le routeur)
        # ═══════════════════════════════════════════════════════════════
        override_action = None
        forced_intent = None
        if os.getenv("BOTLIVE_RULE_OVERRIDES_ENABLED", "true").lower() == "true" and (req.message or ""):
            try:
                # ctx minimal (le runtime lit company_id/user_id)
                ctx = {"company_id": req.company_id, "user_id": req.user_id}
                override_triggered, override_reason = RuleOverrides.should_trigger_before_router(req.message or "", ctx)
                if override_triggered:
                    override_action = RuleOverrides.get_override_action(override_reason, req.message or "", ctx)
                    if override_reason.startswith("deployed_rule_force_intent:"):
                        try:
                            forced_intent = override_reason.split(":", 3)[3]
                        except Exception:
                            forced_intent = None
                    logger.info(
                        "[BOTLIVE][%s] RULE_OVERRIDE triggered: %s -> %s",
                        request_id,
                        override_reason,
                        (override_action or ""),
                    )
                    if override_action:
                        # Court-circuit: réponse immédiate (MVP direct_response)
                        return JSONResponse(
                            content={
                                "success": True,
                                "response": override_action,
                                "order_status": pre_order_status,
                                "next_step": pre_next_step,
                                "duration_ms": int((time.time() - start_time) * 1000),
                                "request_id": request_id,
                                "router": {
                                    "mode": "RULE_OVERRIDE",
                                    "reason": override_reason,
                                },
                            }
                        )
            except Exception as _over_e:
                logger.warning("[BOTLIVE][%s] RULE_OVERRIDE error: %s", request_id, _over_e)

        # 🔀 NOUVEAU: passer par le système hybride Botlive (Jessica + HYDE) au lieu de _botlive_handle
        from core.botlive_rag_hybrid import botlive_hybrid
        from core.botlive_prompts_hardcoded import DEEPSEEK_V3_PROMPT
        from Zeta_AI import app as zeta_app

        # Extraire le numéro entreprise depuis le prompt hardcodé (même logique que l'endpoint /chat)
        botlive_prompt_template = DEEPSEEK_V3_PROMPT
        company_phone = None
        if botlive_prompt_template:
            import re

            phone_patterns = [
                # Après mot-clé (WhatsApp, Tel, Contact, etc.)
                r'(?:whatsapp|tel|téléphone|telephone|contact|appel|numéro|numero)[\s:]*[^\d]*((?:\+?225\s*)?\d{2}[\s\-]*\d{2}[\s\-]*\d{2}[\s\-]*\d{2}[\s\-]*\d{2})',
                # N'importe où avec code pays
                r'\+225[\s\-]*\d{2}[\s\-]*\d{2}[\s\-]*\d{2}[\s\-]*\d{2}[\s\-]*\d{2}',
                # 10 chiffres quelque part
                r'0\d{9}',
            ]

            for pattern in phone_patterns:
                phone_match = re.search(botlive_prompt_template, pattern, re.IGNORECASE) if False else re.search(pattern, botlive_prompt_template, re.IGNORECASE)
                if phone_match:
                    if len(phone_match.groups()) > 0:
                        company_phone = phone_match.group(1)
                    else:
                        company_phone = phone_match.group(0)
                    company_phone = company_phone.strip()
                    break

        # Contexte initial pour le système hybride
        context = {
            "detected_objects": [],
            "filtered_transactions": [],
            "expected_deposit": "2000 FCFA",
            "company_phone": company_phone,
        }

        images_list: List[str] = []
        try:
            if isinstance(req.images, list) and req.images:
                images_list = [str(u).strip() for u in req.images if str(u).strip()]
        except Exception:
            images_list = []

        if not images_list:
            try:
                msg_for_media = str(req.message or "")
                candidates = re.findall(r"https?://[^\s\]\)\}\>\"']+", msg_for_media)
                extracted: List[str] = []
                for u in candidates:
                    uu = (u or "").strip().rstrip(".,;:)")
                    uul = uu.lower()
                    is_img = any(uul.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"]) or "fbcdn" in uul or "scontent" in uul
                    if is_img:
                        extracted.append(uu)
                if extracted:
                    images_list = extracted
            except Exception:
                images_list = []

        if images_list:
            context["images"] = images_list
        logger.info(
            "🔍 [SCAN][VISION_INPUT] images_count=%s source=%s",
            len(images_list),
            "req.images" if (isinstance(req.images, list) and req.images) else ("message_url" if images_list else "none"),
        )

        # Vision: si une image est présente, réutiliser le pipeline léger de Zeta_AI.app
        if images_list and len(images_list) > 0:
            try:
                vision_result = await zeta_app._process_botlive_vision(
                    images_list[0],
                    company_phone=company_phone,
                )
                if isinstance(vision_result, dict):
                    context.update(vision_result)
                    try:
                        logger.info(
                            "🔍 [SCAN][OCR/BLIP] Résultat : detected_objects=%s filtered_transactions=%s",
                            len(vision_result.get("detected_objects") or []),
                            len(vision_result.get("filtered_transactions") or []),
                        )
                    except Exception:
                        pass
            except Exception as vision_err:
                # Gérer gracieusement les erreurs vision (403 Facebook, timeouts, etc.)
                logger.warning(
                    "[BOTLIVE][%s] Erreur traitement vision: %s (image ignorée, continuer sans vision)",
                    request_id,
                    str(vision_err)[:200]
                )
                # Continuer sans vision - le bot peut fonctionner sans image

        # Déduplication légère de l'historique (même helper que le /chat endpoint)
        try:
            conversation_history = zeta_app.deduplicate_conversation_history(
                conversation_history or ""
            )
        except Exception:
            conversation_history = conversation_history or ""

        pipeline_result = None
        routing_result = None
        cache_hit = False
        pipeline_error = None
        try:
            order_status_for_routing = pre_order_status or {}
            produit = str(order_status_for_routing.get("produit") or "").strip()
            paiement = str(order_status_for_routing.get("paiement") or "").strip()
            zone = str(order_status_for_routing.get("zone") or "").strip()
            numero = str(order_status_for_routing.get("numero") or "").strip()
            tel_valide = bool(numero and len(numero) >= 8)
            collected_count = int(bool(produit)) + int(bool(paiement)) + int(bool(zone)) + int(bool(numero))

            state_compact = {
                "collected_count": collected_count,
                "is_complete": bool(order_status_for_routing.get("is_complete", False)),
                "photo_collected": bool(produit),
                "paiement_collected": bool(paiement),
                "zone_collected": bool(zone),
                "tel_collected": bool(numero),
                "tel_valide": tel_valide,
            }

            pipeline_result = await production_pipeline.route_message(
                req.company_id,
                req.user_id,
                req.message or "",
                conversation_history,
                state_compact,
                forced_intent=forced_intent,
            )
            routing_result = pipeline_result.get("result") if isinstance(pipeline_result, dict) else None
            cache_hit = bool(pipeline_result.get("cache_hit")) if isinstance(pipeline_result, dict) else False
        except Exception as e:
            pipeline_error = str(e)
            logger.error("[BOTLIVE][%s] ProductionPipeline routing failed: %s", request_id, e, exc_info=True)

        hybrid_result = await botlive_hybrid.process_request(
            user_id=req.user_id,
            message=req.message or "",
            context=context,
            conversation_history=conversation_history,
            company_id=req.company_id,
        )

        response = hybrid_result.get("response", "") if isinstance(hybrid_result, dict) else ""
        status = hybrid_result.get("status") if isinstance(hybrid_result, dict) else None
        if BOTLIVE_COOPERATIVE_HUMAN_MODE and status == "PENDING_HUMAN":
            # IMPORTANT: En mode coopératif, on peut vouloir notifier l'humain SANS appeler le LLM,
            # tout en envoyant un court message fallback au client.
            # Si une réponse non vide est fournie, on la conserve.
            try:
                if not (isinstance(response, str) and response.strip()):
                    response = None
            except Exception:
                response = None

            try:
                _PENDING_HUMAN[_pending_key(req.company_id, req.user_id)] = {
                    "status": "PENDING_HUMAN",
                    "created_at": datetime.utcnow().isoformat(),
                    "company_id": req.company_id,
                    "user_id": req.user_id,
                    "message": req.message or "",
                    "router_metrics": hybrid_result.get("router_metrics"),
                    "router_debug": getattr(routing_result, "debug", None) if routing_result else None,
                    "request_id": request_id,
                }
            except Exception:
                pass

            try:
                await log_intervention_in_conversation_logs(
                    company_id_text=req.company_id,
                    user_id=req.user_id,
                    message=req.message or "",
                    metadata={
                        "needs_intervention": True,
                        "reason": "cooperative_pending_human",
                        "priority": "high",
                        "cooperative_mode": True,
                        "status": "PENDING_HUMAN",
                        "router_metrics": hybrid_result.get("router_metrics") if isinstance(hybrid_result, dict) else None,
                    },
                    channel="botlive",
                    direction="user",
                    source="botlive_cooperative",
                )
            except Exception as log_err:
                logger.error("[BOTLIVE][%s] Failed to log cooperative pending human: %s", request_id, log_err)
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Récupérer l'état de la commande
        order_status = await get_order_state(req.user_id, req.company_id)
        
        # Déterminer la prochaine étape
        next_step = _determine_next_step(order_status)

        conversation_id = None
        try:
            from core.activities_logger import log_new_conversation
            logger.info(
                "[BOTLIVE][%s] Début logging conversation: company_id=%s user_id=%s",
                request_id,
                req.company_id,
                req.user_id,
            )

            conversation_id = await get_or_create_conversation(
                req.company_id,
                req.user_id,
                user_display_name,
            )
            logger.info(
                "[BOTLIVE][%s] get_or_create_conversation -> %s",
                request_id, conversation_id)

            if not conversation_id:
                logger.warning(
                    "[BOTLIVE][%s] Aucune conversation_id retourneee, skip insert_message/log_new_conversation",
                    request_id,
                )
            else:
                # Enrichir metadata pour exposer user_id / user_display_name dans la table messages
                user_metadata: Dict[str, Any] = {
                    "source": "botlive",
                    "channel": "messenger",
                    "user_id": req.user_id,
                }
                if user_display_name:
                    user_metadata["user_display_name"] = user_display_name

                # Déterminer un nom lisible pour l'auteur (colonne messages.author_name)
                author_name = user_display_name or req.user_id[-4:]

                user_ok = await insert_message(
                    conversation_id,
                    "user",
                    req.message or "",
                    {**user_metadata, "author_name": author_name},
                )
                logger.info(
                    "[BOTLIVE][%s] insert_message user -> %s",
                    request_id,
                    user_ok,
                )

                try:
                    await log_message_in_conversation_logs(
                        company_id_text=req.company_id,
                        user_id=req.user_id,
                        message=req.message or "",
                        channel="botlive",
                        direction="user",
                        conversation_id=conversation_id,
                        source="botlive_gateway",
                        status="active",
                    )
                except Exception as log_err:
                    logger.error(
                        "[BOTLIVE][%s] Failed to log user message in conversation_logs: %s",
                        request_id,
                        log_err,
                    )

                if isinstance(response, str) and response:
                    assistant_ok = await insert_message(
                        conversation_id,
                        "assistant",
                        response,
                        {"source": "botlive", "channel": "bot", "author_name": "Botlive"},
                    )
                    logger.info(
                        "[BOTLIVE][%s] insert_message assistant -> %s",
                        request_id,
                        assistant_ok,
                    )

                    try:
                        await log_message_in_conversation_logs(
                            company_id_text=req.company_id,
                            user_id=req.user_id,
                            message=response,
                            channel="botlive",
                            direction="assistant",
                            conversation_id=conversation_id,
                            source="botlive_gateway",
                            status="active",
                        )
                    except Exception as log_err:
                        logger.error(
                            "[BOTLIVE][%s] Failed to log assistant message in conversation_logs: %s",
                            request_id,
                            log_err,
                        )

                activity_ok = await log_new_conversation(
                    req.company_id,
                    req.user_id,
                    conversation_id,
                    user_display_name,
                )
                logger.info(
                    "[BOTLIVE][%s] log_new_conversation -> %s",
                    request_id,
                    activity_ok,
                )
        except Exception as conv_err:
            logger.error(
                f"[BOTLIVE][{request_id}] Erreur logging conversation/messages: {conv_err}",
                exc_info=True,
            )

        if next_step == "completed" and conversation_id:
            try:
                from core.orders_manager import create_order
                from core.activities_logger import log_order_created
                from core.supabase_notepad import get_supabase_notepad

                produit = ""
                numero_client = req.user_id[-4:]
                if isinstance(order_status, dict):
                    produit = order_status.get("produit") or ""
                    numero_client = order_status.get("numero") or numero_client

                total_amount = 2000.0
                delivery_zone = None
                image_url = None
                try:
                    notepad_manager = get_supabase_notepad()
                    notepad = await notepad_manager.get_notepad(req.user_id, req.company_id)
                    paiement_info = notepad.get("paiement") or {}
                    montant_notepad = paiement_info.get("montant") or paiement_info.get("amount")
                    if montant_notepad:
                        total_amount = float(montant_notepad)

                    # Zone de livraison validée (priorité notepad, fallback order_status.zone)
                    delivery_zone = notepad.get("delivery_zone")
                    if not delivery_zone and isinstance(order_status, dict):
                        delivery_zone = order_status.get("zone")

                    # URL d'image produit validée par BLIP et stockée dans le notepad
                    image_url = notepad.get("photo_produit_url")
                except Exception as np_err:
                    logger.warning(f"[BOTLIVE][{request_id}] Impossible de lire montant notepad: {np_err}")

                items = [{"name": produit or "Commande Botlive", "quantity": 1, "acompte": total_amount}]

                # Pour les cartes commandes frontend, customer_name doit être le NUMÉRO du client
                order_customer_name = numero_client

                order = await create_order(
                    company_id=req.company_id,
                    user_id=req.user_id,
                    customer_name=order_customer_name,
                    total_amount=total_amount,
                    items=items,
                    conversation_id=conversation_id,
                    delivery_zone=delivery_zone,
                    image_url=image_url,
                )
                if order and isinstance(order, dict) and order.get("id"):
                    await log_order_created(req.company_id, order_customer_name, order["id"], total_amount)
            except Exception as order_err:
                logger.error(f"[BOTLIVE][{request_id}] Erreur création commande/activité: {order_err}")

        try:
            guardian = get_intervention_guardian()
            if guardian:
                order_is_complete = bool(order_status.get("is_complete")) if isinstance(order_status, dict) else False
                hard_signals = {
                    "explicit_handoff": explicit_handoff,
                    "customer_frustration": is_frustrated,
                    "next_step": next_step,
                    "order_is_complete": order_is_complete,
                    "completion_rate": order_status.get("completion_rate") if isinstance(order_status, dict) else None,
                }
                logger.info(
                    "[BOTLIVE][%s] Guardian hard_signals | order_is_complete=%s next_step=%s signals=%s",
                    request_id,
                    order_is_complete,
                    next_step,
                    hard_signals,
                )
                # Le Guardian NE DOIT PAS modifier ou bloquer la réponse Botlive. Il sert uniquement à logguer.
                if not order_is_complete and not explicit_handoff and not is_frustrated:
                    guardian_decision = await guardian.analyze(
                        conversation_history=conversation_history,
                        user_message=req.message or "",
                        bot_response=response if isinstance(response, str) else "",
                        order_state=order_status if isinstance(order_status, dict) else {},
                        next_step=next_step,
                        hard_signals=hard_signals,
                    )
                    logger.info(
                        "[BOTLIVE][%s] Guardian decision | requires_intervention=%s category=%s priority=%s confidence=%s",
                        request_id,
                        guardian_decision.get("requires_intervention"),
                        guardian_decision.get("category"),
                        guardian_decision.get("priority"),
                        guardian_decision.get("confidence"),
                    )
                    if guardian_decision.get("requires_intervention"):
                        metadata: Dict[str, Any] = {
                            "needs_intervention": True,
                            "reason": guardian_decision.get("category") or "guardian_intervention",
                            "priority": guardian_decision.get("priority") or "normal",
                            "guardian_confidence": guardian_decision.get("confidence"),
                            "guardian_reason": guardian_decision.get("reason"),
                            "detected_by": "intervention_guardian_v1",
                            "source_bot": "botlive",
                            "caps_ratio": caps_ratio,
                        }
                        suggested = guardian_decision.get("suggested_handoff_message")
                        if suggested:
                            metadata["guardian_handoff_message"] = suggested

                        logger.info(
                            "[BOTLIVE][%s] Guardian triggered intervention logging via conversation_logs",
                            request_id,
                        )
                        await log_intervention_in_conversation_logs(
                            company_id_text=req.company_id,
                            user_id=req.user_id,
                            message=guardian_decision.get("reason") or "[Guardian Intervention] Intervention recommandée",
                            metadata=metadata,
                            channel="botlive",
                            direction="system",
                            source="intervention_guardian_v1",
                        )
        except Exception as guardian_err:
            # Le Guardian ne doit JAMAIS casser la réponse Botlive
            logger.error("[BOTLIVE][%s] Erreur Guardian d'intervention: %s", request_id, guardian_err)

        logger.info(f"[BOTLIVE][{request_id}] Réponse générée en {duration_ms}ms, next_step={next_step}")
        
        # Déclencher webhook si commande complétée
        if next_step == "completed":
            background_tasks.add_task(trigger_webhook, "order_completed", {
                "user_id": req.user_id,
                "company_id": req.company_id,
                "order_status": order_status
            })
        
        router_debug_out = getattr(routing_result, "debug", None) if routing_result else None
        try:
            if isinstance(router_debug_out, dict) and not router_debug_out.get("router_source"):
                rname = str(router_debug_out.get("router") or "").strip().lower()
                if rname in {"setfit_v4", "setfit"}:
                    router_debug_out["router_source"] = "setfit"
                elif rname == "prefilter":
                    router_debug_out["router_source"] = "setfit_prefilter"
                elif rname in {"embeddings", "emb_router"}:
                    router_debug_out["router_source"] = "embeddings"
                elif rname == "rule_override":
                    router_debug_out["router_source"] = "rule_override"
                elif rname == "global_handoff":
                    router_debug_out["router_source"] = "global_handoff"
        except Exception:
            pass

        pipeline_intent = getattr(routing_result, "intent", None) if routing_result else None
        pipeline_confidence = getattr(routing_result, "confidence", None) if routing_result else None
        pipeline_mode = getattr(routing_result, "mode", None) if routing_result else None

        final_intent = pipeline_intent
        final_confidence = pipeline_confidence
        final_mode = pipeline_mode
        try:
            rm = (hybrid_result.get("router_metrics") or {}) if isinstance(hybrid_result, dict) else {}
            if isinstance(rm, dict):
                if rm.get("intent") is not None:
                    final_intent = rm.get("intent")
                if rm.get("confidence") is not None:
                    final_confidence = rm.get("confidence")
                if rm.get("mode") is not None:
                    final_mode = rm.get("mode")
        except Exception:
            pass

        # Vérifier si la réponse est vide et appliquer un message contextuel si handoff
        if response is None or (isinstance(response, str) and not response.strip()):
            logger.warning(
                "[BOTLIVE][%s] Réponse vide détectée (llm_used=%s, intent=%s). Fallback appliqué.",
                request_id,
                (hybrid_result.get("llm_used") if isinstance(hybrid_result, dict) else None),
                final_intent
            )
            
            # Message contextuel si handoff détecté, sinon fallback générique
            if final_intent and final_intent in ["SAV_SUIVI", "MODIFICATION_COMMANDE", "HORS_ZONE", "QUESTION_TECHNIQUE"]:
                response = get_handoff_message(final_intent, req.message or "")
                logger.info(
                    "[BOTLIVE][%s] Handoff contextuel: intent=%s message='%s'",
                    request_id,
                    final_intent,
                    response[:50]
                )
            else:
                response = "Désolé, je n'ai pas pu générer une réponse. Peux-tu reformuler ta demande ?"

        # --- Strip ##HANDOFF## de la réponse BotLive avant envoi client ---
        try:
            from config import LLM_TRANSMISSION_TOKEN as _TOKEN
            _tok = (_TOKEN or "##HANDOFF##").strip()
            _resp_str = str(response or "")
            _raw_thinking = (hybrid_result.get("thinking") or "") if isinstance(hybrid_result, dict) else ""
            _has_token = bool(_tok) and (
                _tok.lower() in _resp_str.lower()
                or (isinstance(_raw_thinking, str) and re.search(r'<handoff>\s*true\s*</handoff>', _raw_thinking, re.IGNORECASE))
            )
            if _has_token:
                # Nettoyer le token + séparateur §§ de la réponse
                if _tok.lower() in _resp_str.lower():
                    _parts = re.split(re.escape(_tok), _resp_str, flags=re.IGNORECASE)
                    response = (_parts[0] or "").replace("§§", "").strip()
                if not response:
                    response = "Un instant, je vous passe le responsable."
                # Écrire dans required_interventions
                try:
                    try:
                        order_tracker.set_flag(req.user_id, "bot_paused", True)
                        order_tracker.set_custom_meta(req.user_id, "bot_paused_at", datetime.now().isoformat())
                        order_tracker.set_custom_meta(req.user_id, "bot_paused_by", "explicit_handoff")
                    except Exception:
                        pass
                    await upsert_required_intervention(
                        company_id=req.company_id,
                        user_id=req.user_id,
                        channel="whatsapp",
                        intervention_type="explicit_handoff",
                        priority="critical",
                        detected_by="rule_based",
                        source_bot="botlive",
                        reason="##HANDOFF## dans réponse BotLive",
                        user_message=(req.message or "")[:500],
                        bot_response=response[:500],
                    )
                    logger.info("[BOTLIVE][%s] ✅ ##HANDOFF## strippé + upsert_required_intervention OK", request_id)
                except Exception as _uh_e:
                    logger.warning("[BOTLIVE][%s] upsert handoff failed (non-blocking): %s", request_id, _uh_e)
        except Exception as _strip_e:
            logger.warning("[BOTLIVE][%s] ##HANDOFF## strip error (non-blocking): %s", request_id, _strip_e)

        return JSONResponse(content={
            "success": True,
            "response": response,
            "status": ("PENDING_HUMAN" if (BOTLIVE_COOPERATIVE_HUMAN_MODE and status == "PENDING_HUMAN") else "OK"),
            "human_required": bool(hybrid_result.get("human_required")) if isinstance(hybrid_result, dict) else False,
            "bypass_llm": bool(hybrid_result.get("bypass_llm")) if isinstance(hybrid_result, dict) else False,
            "llm_used": hybrid_result.get("llm_used") if isinstance(hybrid_result, dict) else None,
            "thinking": hybrid_result.get("thinking") if isinstance(hybrid_result, dict) else None,
            "llm_raw": hybrid_result.get("llm_raw") if isinstance(hybrid_result, dict) else None,
            "prompt_tokens": hybrid_result.get("prompt_tokens") if isinstance(hybrid_result, dict) else None,
            "completion_tokens": hybrid_result.get("completion_tokens") if isinstance(hybrid_result, dict) else None,
            "total_tokens": hybrid_result.get("total_tokens") if isinstance(hybrid_result, dict) else None,
            "total_cost": hybrid_result.get("total_cost") if isinstance(hybrid_result, dict) else None,
            "cost": hybrid_result.get("cost") if isinstance(hybrid_result, dict) else None,
            "usage": hybrid_result.get("usage") if isinstance(hybrid_result, dict) else None,
            "intent": final_intent,
            "confidence": final_confidence,
            "mode": final_mode,
            "pipeline_intent": pipeline_intent,
            "pipeline_confidence": pipeline_confidence,
            "pipeline_mode": pipeline_mode,
            "missing_fields": getattr(routing_result, "missing_fields", None) if routing_result else None,
            "router_debug": router_debug_out,
            "router_error": pipeline_error,
            "router_metrics": hybrid_result.get("router_metrics") if isinstance(hybrid_result, dict) else None,
            "source": "cache" if cache_hit else "llm",
            "cache_hit": cache_hit,
            "latency_ms": duration_ms,
            "order_status": order_status,
            "next_step": next_step,
            "duration_ms": duration_ms,
            "request_id": request_id
        })
        
    except Exception as e:
        logger.error(f"[BOTLIVE][{request_id}] Erreur: {e}", exc_info=True)
        try:
            await log_intervention_in_conversation_logs(
                company_id_text=req.company_id,
                user_id=req.user_id,
                message=str(e),
                metadata={
                    "needs_intervention": True,
                    "reason": "system_errors",
                    "priority": "critical",
                },
                channel="botlive",
                direction="system",
                source="botlive_gateway_error",
            )
        except Exception as log_err:
            logger.error("[BOTLIVE][%s] Failed to log system error intervention: %s", request_id, log_err)
        raise HTTPException(status_code=500, detail=f"Erreur traitement message: {str(e)}")

    logger.warning(f"[BOTLIVE][{request_id}] ZETA-AI v6.5 active | RequestID: {request_id}")

@shared_router.post("/check-intervention")
async def check_shared_intervention(req: SharedInterventionCheckRequest):
    # --- Couche 1 : règles textuelles ---
    rule_result = _compute_rule_based_intervention(req.user_message)
    result: Dict[str, Any] = {
        "requires_intervention": False,
        "priority": "normal",
        "category": None,
        "reason": None,
        "detected_by": None,
        "confidence": None,
        "caps_ratio": rule_result.get("caps_ratio", 0.0),
        "explicit_handoff": rule_result.get("explicit_handoff", False),
        "is_frustrated": rule_result.get("is_frustrated", False),
        "source": req.source,
    }

    if rule_result.get("requires_intervention"):
        prio = "critical" if rule_result.get("reason") == "explicit_handoff" else "high"
        result.update({
            "requires_intervention": True,
            "priority": prio,
            "category": rule_result.get("reason"),
            "reason": rule_result.get("reason"),
            "detected_by": "rule_based",
        })
    else:
        # --- Couche 2 : règles contextuelles (order_state, next_step) ---
        ctx_result = _compute_context_based_intervention(
            order_state=req.order_state or {},
            next_step=req.next_step or "",
            bot_response=req.bot_response or "",
            source=req.source or "shared",
        )
        if ctx_result:
            result.update({
                "requires_intervention": True,
                "priority": ctx_result.get("priority", "normal"),
                "category": ctx_result.get("reason"),
                "reason": ctx_result.get("reason"),
                "detected_by": "context_rules",
            })
        else:
            # --- Couche 3 : Guardian LLM (cas ambigus) ---
            guardian = get_intervention_guardian()
            if guardian:
                hard_signals = {
                    "explicit_handoff": rule_result.get("explicit_handoff", False),
                    "customer_frustration": rule_result.get("is_frustrated", False),
                    "is_sav": rule_result.get("is_sav", False),
                    "is_payment_issue": rule_result.get("is_payment_issue", False),
                    "next_step": req.next_step or "",
                    "order_is_complete": bool((req.order_state or {}).get("is_complete")),
                    "completion_rate": (req.order_state or {}).get("completion_rate"),
                }
                decision = await guardian.analyze(
                    conversation_history=req.conversation_history or "",
                    user_message=req.user_message or "",
                    bot_response=req.bot_response or "",
                    order_state=req.order_state or {},
                    next_step=req.next_step or "",
                    hard_signals=hard_signals,
                )
                if decision.get("requires_intervention"):
                    result.update({
                        "requires_intervention": True,
                        "priority": decision.get("priority") or "normal",
                        "category": decision.get("category") or "guardian_intervention",
                        "reason": decision.get("reason") or "guardian_intervention",
                        "detected_by": "intervention_guardian_v1",
                        "confidence": decision.get("confidence"),
                        "suggested_handoff_message": decision.get("suggested_handoff_message") or "",
                    })

    # --- Log si intervention détectée ---
    if req.log_intervention and result.get("requires_intervention"):
        # 1) Écrire dans required_interventions (table métier)
        await upsert_required_intervention(
            company_id=req.company_id,
            user_id=req.user_id,
            channel=req.channel or "whatsapp",
            intervention_type=result.get("category") or "explicit_handoff",
            priority=result.get("priority") or "normal",
            detected_by=result.get("detected_by") or "rule_based",
            source_bot=req.source or "botliveandrag",
            confidence=result.get("confidence"),
            reason=result.get("reason") or "",
            signals={
                "caps_ratio": result.get("caps_ratio"),
                "explicit_handoff": result.get("explicit_handoff"),
                "is_frustrated": result.get("is_frustrated"),
            },
            user_message=req.user_message or "",
            bot_response=req.bot_response or "",
            order_state=req.order_state or {},
        )
        # 2) Écrire aussi dans conversation_logs (historique + push notification)
        await log_intervention_in_conversation_logs(
            company_id_text=req.company_id,
            user_id=req.user_id,
            message=result.get("reason") or (req.user_message or "[Shared Intervention]"),
            metadata={
                "needs_intervention": True,
                "reason": result.get("category") or result.get("reason"),
                "priority": result.get("priority") or "normal",
                "caps_ratio": result.get("caps_ratio"),
                "source": req.source,
                "detected_by": result.get("detected_by"),
                "source_bot": req.source or "shared",
                "guardian_confidence": result.get("confidence"),
            },
            channel=req.channel or "whatsapp",
            direction="assistant",
            source=req.source or "botliveandrag_check",
        )
    return JSONResponse(content=result)


class OperatorHandledRequest(BaseModel):
    company_id: str = Field(..., description="ID texte de l'entreprise")
    user_id: str = Field(..., description="ID utilisateur WhatsApp (numéro normalisé)")
    channel: str = Field(default="whatsapp")
    human_takeover_hours: float = Field(default=4.0, description="Durée de blocage bot en heures")


@shared_router.post("/operator-handled")
async def operator_handled(req: OperatorHandledRequest):
    """Appelé quand l'opérateur répond directement depuis WhatsApp (hors app).

    Actions atomiques :
    1. Ferme toutes les interventions ouvertes pour ce user_id
    2. Écrit un log conversation avec human_takeover=True (bloque bot N heures)
    3. Met à jour order_tracker (bot_paused en mémoire)
    """
    from datetime import timedelta

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    headers_sb = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    resolved_at = datetime.utcnow().isoformat() + "Z"
    takeover_until = (datetime.utcnow() + timedelta(hours=req.human_takeover_hours)).isoformat() + "Z"

    errors: list = []

    # 1. Fermer les interventions ouvertes dans required_interventions
    try:
        patch_url = (
            f"{supabase_url}/rest/v1/required_interventions"
            f"?company_id=eq.{req.company_id}"
            f"&user_id=eq.{req.user_id}"
            f"&status=in.(open,acknowledged,in_progress,reopened)"
        )
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.patch(
                patch_url,
                headers=headers_sb,
                json={
                    "status": "resolved",
                    "resolved_by": "operator_whatsapp",
                    "resolved_at": resolved_at,
                    "resolution_note": "Opérateur a répondu directement depuis WhatsApp",
                },
            )
        if resp.status_code not in (200, 201, 204):
            errors.append(f"ri_close={resp.status_code}")
            logger.warning("[OPERATOR_HANDLED] required_interventions patch failed: %s %s", resp.status_code, resp.text[:200])
        else:
            logger.info("[OPERATOR_HANDLED] ✅ interventions fermées | company=%s user=%s", req.company_id, req.user_id)
    except Exception as e:
        errors.append(f"ri_close_exc={e}")
        logger.error("[OPERATOR_HANDLED] Exception closing interventions: %s", e)

    # 2. Écrire conversation_log avec human_takeover (bloque le bot dans N8N / If7)
    try:
        log_url = f"{supabase_url}/rest/v1/conversation_logs"
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp2 = await client.post(
                log_url,
                headers=headers_sb,
                json={
                    "company_id_text": req.company_id,
                    "user_id": req.user_id,
                    "channel": req.channel,
                    "direction": "assistant",
                    "message": "[Opérateur a pris en charge depuis WhatsApp]",
                    "content": "[Opérateur a pris en charge depuis WhatsApp]",
                    "source": "operator_whatsapp",
                    "status": "active",
                    "metadata": {
                        "human_takeover": True,
                        "human_takeover_until": takeover_until,
                        "trigger": "operator_whatsapp_direct",
                        "resolved_intervention": True,
                    },
                },
            )
        if resp2.status_code not in (200, 201):
            errors.append(f"conv_log={resp2.status_code}")
            logger.warning("[OPERATOR_HANDLED] conversation_log insert failed: %s", resp2.status_code)
        else:
            logger.info("[OPERATOR_HANDLED] ✅ human_takeover log écrit jusqu'à %s", takeover_until)
    except Exception as e:
        errors.append(f"conv_log_exc={e}")
        logger.error("[OPERATOR_HANDLED] Exception writing conv log: %s", e)

    # 3. Mettre à jour order_tracker en mémoire
    try:
        order_tracker.set_flag(req.user_id, "bot_paused", True)
        order_tracker.set_custom_meta(req.user_id, "bot_paused_at", resolved_at)
        order_tracker.set_custom_meta(req.user_id, "bot_paused_by", "operator_whatsapp")
    except Exception as e:
        logger.warning("[OPERATOR_HANDLED] order_tracker update failed (non-blocking): %s", e)

    return JSONResponse(content={
        "success": len(errors) == 0,
        "company_id": req.company_id,
        "user_id": req.user_id,
        "human_takeover_until": takeover_until,
        "errors": errors,
    })


@router.post("/human-reply")
async def send_human_reply(req: HumanReplyRequest):
    """Relaye une réponse humaine depuis le frontend vers N8N.

    Le frontend appelle cet endpoint quand un opérateur répond dans l'interface
    de chat. Cet endpoint NE fait pas appel au LLM : il se contente de pousser
    un payload propre vers un webhook N8N dédié (workflow "botlive/human-reply").

    Le payload envoyé à N8N est volontairement simple et explicite pour que le
    workflow puisse ensuite :
    - insérer une ligne dans conversation_logs (direction = outbound, source = human)
    - envoyer le message au client via Messenger/WhatsApp.
    """

    # Envoi direct via WhatsApp Cloud API si demandé
    channel_lower = (req.channel or "").lower()
    if channel_lower == "whatsapp":
        try:
            # Shadow Mode: enregistre la réponse opérateur (mode écoute)
            try:
                if os.getenv("SHADOW_MODE_ENABLED", "true").lower() == "true":
                    from core.shadow_recorder import record_operator_reply
                    await record_operator_reply(req.company_id, req.user_id, req.message or "", req.user_display_name)
            except Exception:
                pass

            # Envoi via Meta WhatsApp Cloud API
            from config import WHATSAPP_TOKEN
            if WHATSAPP_TOKEN:
                try:
                    from core.meta_whatsapp import send_text
                    send_res = await send_text(req.user_id, req.message or "")
                    logger.info("[BOTLIVE][HUMAN_REPLY] WhatsApp META send -> %s", send_res.get("status"))
                    # Log dans messages (assistant)
                    try:
                        from core.conversations_manager import get_or_create_conversation, insert_message
                        conv_id = await get_or_create_conversation(req.company_id, req.user_id)
                        if conv_id:
                            await insert_message(
                                conv_id, "assistant", req.message or "",
                                {"source": "human", "channel": "whatsapp", "author_name": (req.user_display_name or "Opérateur")} 
                            )
                    except Exception as log_err:
                        logger.warning(f"[BOTLIVE][HUMAN_REPLY] conv log failed: {log_err}")
                    return JSONResponse(content={"success": True, "sent_via": "whatsapp_meta", "status": send_res.get("status")})
                except Exception as e:
                    logger.error("[BOTLIVE][HUMAN_REPLY] WhatsApp META send error: %s", e)
                    # fallback N8N si dispo
            else:
                logger.warning("[BOTLIVE][HUMAN_REPLY] WHATSAPP_TOKEN manquant, fallback N8N")
        except Exception as e:
            logger.error("[BOTLIVE][HUMAN_REPLY] Branch WhatsApp error: %s", e)

    if not N8N_OUTBOUND_WEBHOOK_URL:
        logger.error("[BOTLIVE][HUMAN_REPLY] N8N_OUTBOUND_WEBHOOK_URL n'est pas configurée")
        raise HTTPException(status_code=500, detail="Webhook N8N non configuré côté backend")

    payload: Dict[str, Any] = {
        # Compat : exposer les deux clés company_id & company_id_text
        "company_id": req.company_id,
        "company_id_text": req.company_id,
        "user_id": req.user_id,
        "message": req.message,
        "channel": req.channel or "messenger",
        "user_display_name": req.user_display_name,
        "source": "human",
    }

    # Relayer les images si fournies (même format que pour les messages client)
    if req.images:
        payload["images"] = req.images

    # Ajouter page_id si fourni (pour routage précis côté N8N, ex: multi-pages Messenger)
    if req.page_id:
        payload["page_id"] = req.page_id

    headers: Dict[str, str] = {}
    if N8N_API_KEY:
        headers["X-N8N-API-KEY"] = N8N_API_KEY

    try:
        # Shadow Mode (déjà fait pour WhatsApp branch). Ici on refait au cas où
        try:
            if os.getenv("SHADOW_MODE_ENABLED", "true").lower() == "true":
                from core.shadow_recorder import record_operator_reply
                await record_operator_reply(req.company_id, req.user_id, req.message or "", req.user_display_name)
        except Exception:
            pass

        logger.info(
            "[BOTLIVE][HUMAN_REPLY] Envoi vers N8N | company_id=%s user_id=%s channel=%s",
            req.company_id,
            req.user_id,
            req.channel,
        )

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                N8N_OUTBOUND_WEBHOOK_URL,
                json=payload,
                headers=headers,
            )

        if response.status_code not in (200, 201, 202, 204):
            body_preview = response.text[:500]
            logger.error(
                "[BOTLIVE][HUMAN_REPLY] Erreur N8N %s | body=%s",
                response.status_code,
                body_preview,
            )
            raise HTTPException(
                status_code=500,
                detail=f"Erreur webhook N8N (status={response.status_code})",
            )

        # Log dans messages (assistant)
        try:
            from core.conversations_manager import get_or_create_conversation, insert_message
            conv_id = await get_or_create_conversation(req.company_id, req.user_id)
            if conv_id:
                await insert_message(
                    conv_id, "assistant", req.message or "",
                    {"source": "human", "channel": (req.channel or "messenger"), "author_name": (req.user_display_name or "Opérateur")} 
                )
        except Exception as log_err:
            logger.warning(f"[BOTLIVE][HUMAN_REPLY] conv log failed (N8N): {log_err}")

        if N8N_DEBUG_MODE:
            logger.info(
                "[BOTLIVE][HUMAN_REPLY] Réponse N8N: status=%s body=%s",
                response.status_code,
                response.text[:300],
            )

        return JSONResponse(
            content={
                "success": True,
                "relayed_to_n8n": True,
                "status_code": response.status_code,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[BOTLIVE][HUMAN_REPLY] Exception lors de l'appel N8N: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de l'envoi à N8N")


@router.get("/pending-response")
async def get_pending_response(company_id: str, user_id: str):
    key = _pending_key(company_id, user_id)
    payload = _PENDING_HUMAN.get(key)
    if not payload:
        return JSONResponse(content={"success": True, "status": "NONE", "response": None})
    return JSONResponse(content={"success": True, **payload, "response": None})


@router.post("/bot/enabled")
async def set_bot_enabled(req: BotPauseRequest):
    """Active/désactive le bot pour un user_id.

    Mapping unique (pas de nouveau flag):
    - enabled=True  => bot_paused=False
    - enabled=False => bot_paused=True
    """
    try:
        order_tracker.set_flag(req.user_id, "bot_paused", (not bool(req.enabled)))
        if bool(req.enabled):
            order_tracker.set_custom_meta(req.user_id, "bot_paused_auto_resumed_at", datetime.now().isoformat())
        else:
            order_tracker.set_custom_meta(req.user_id, "bot_paused_at", datetime.now().isoformat())
            order_tracker.set_custom_meta(req.user_id, "bot_paused_by", "manual_toggle")
        return {
            "success": True,
            "company_id": req.company_id,
            "user_id": req.user_id,
            "enabled": bool(req.enabled),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/message/stream")
async def process_botlive_message_stream(req: BotliveMessageRequest):
    """
    🌊 ENDPOINT STREAMING - Réponse en temps réel (SSE)
    
    Pour une meilleure UX avec affichage progressif de la réponse
    """
    request_id = str(uuid.uuid4())[:8]
    
    async def event_generator():
        try:
            # Import lazy vers le backend principal (évite les conflits avec un module externe "app")
            from Zeta_AI import app as zeta_app
            
            # Envoyer événement de démarrage
            yield f"data: {{'event': 'start', 'request_id': '{request_id}'}}\n\n"
            
            # Traiter le message via le handler Botlive du backend principal
            response = await zeta_app._botlive_handle(
                company_id=req.company_id,
                user_id=req.user_id,
                message=req.message,
                images=req.images,
                conversation_history=req.conversation_history
            )
            
            # Simuler streaming (découper la réponse)
            words = response.split()
            for i, word in enumerate(words):
                yield f"data: {{'event': 'token', 'content': '{word} '}}\n\n"
                await asyncio.sleep(0.05)  # 50ms entre chaque mot
            
            # État final
            order_status = await get_order_state(req.user_id, req.company_id)
            next_step = _determine_next_step(order_status)
            
            yield f"data: {{'event': 'done', 'order_status': {order_status}, 'next_step': '{next_step}'}}\n\n"
            
        except Exception as e:
            logger.error(f"[BOTLIVE][STREAM][{request_id}] Erreur: {e}")
            yield f"data: {{'event': 'error', 'message': '{str(e)}'}}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# ═══════════════════════════════════════════════════════════════════════════════
# SHADOW MODE - ENDPOINTS DÉDIÉS (pas de réponse bot)

class ShadowUserRecordRequest(BaseModel):
    company_id: str
    user_id: str
    message: str = ""
    user_display_name: Optional[str] = None


class ShadowOperatorRecordRequest(BaseModel):
    company_id: str
    user_id: str
    message: str
    operator_display_name: Optional[str] = None


@router.post("/shadow/user")
async def shadow_record_user(req: ShadowUserRecordRequest):
    try:
        from core.shadow_recorder import record_user_message
        await record_user_message(req.company_id, req.user_id, req.message or "", req.user_display_name)
        return JSONResponse(content={"success": True, "recorded": "user"})
    except Exception as e:
        logger.error(f"[BOTLIVE][SHADOW][USER] Error: {e}")
        raise HTTPException(status_code=500, detail="Erreur enregistrement shadow user")


@router.post("/shadow/operator")
async def shadow_record_operator(req: ShadowOperatorRecordRequest):
    try:
        from core.shadow_recorder import record_operator_reply
        await record_operator_reply(req.company_id, req.user_id, req.message or "", req.operator_display_name)
        return JSONResponse(content={"success": True, "recorded": "operator"})
    except Exception as e:
        logger.error(f"[BOTLIVE][SHADOW][OPERATOR] Error: {e}")
        raise HTTPException(status_code=500, detail="Erreur enregistrement shadow operator")

# ═══════════════════════════════════════════════════════════════════════════════
# 📊 ENDPOINTS STATISTIQUES & MONITORING
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/stats/{company_id}")
async def get_botlive_stats(company_id: str, time_range: str = "today"):
    """
    📊 Statistiques Mode LIVE
    
    Returns:
        {
            "ca_live_session": 1247.0,
            "ca_variation": "+23%",
            "commandes_total": 34,
            "commandes_variation": "+12",
            "clients_actifs": 156,
            "interventions_requises": 2,
            "activite_temps_reel": [...]
        }
    """
    try:
        # Utiliser le module de données réelles
        from core.botlive_dashboard_data import get_live_stats
        
        stats = await get_live_stats(company_id, time_range)
        
        return JSONResponse(content=stats)
        
    except Exception as e:
        logger.error(f"[BOTLIVE][STATS] Erreur: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur stats: {str(e)}")

@router.get("/orders/active/{company_id}")
async def get_active_orders_endpoint(company_id: str, limit: int = 50):
    """
    📦 Liste des commandes actives (en cours)
    
    Pour afficher dans le frontend les commandes en attente de validation
    """
    try:
        from core.botlive_dashboard_data import get_active_orders
        
        active_orders = await get_active_orders(company_id, limit)
        
        return JSONResponse(content={
            "success": True,
            "orders": active_orders,
            "total": len(active_orders)
        })
        
    except Exception as e:
        logger.error(f"[BOTLIVE][ACTIVE_ORDERS] Erreur: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orders/{order_id}/status")
async def update_order_status_endpoint(order_id: str, req: UpdateOrderStatusRequest):
    """Met à jour le statut d'une commande (pending/completed/cancelled)."""
    from core.orders_manager import update_order_status

    allowed_status = {"pending", "completed", "cancelled"}
    if req.status not in allowed_status:
        raise HTTPException(status_code=400, detail="Invalid status value")

    ok = await update_order_status(order_id, req.status)
    if not ok:
        raise HTTPException(status_code=500, detail="Erreur mise à jour commande")

    return JSONResponse(content={"success": True, "order_id": order_id, "status": req.status})

@router.get("/interventions/{company_id}")
async def get_interventions_required_endpoint(company_id: str):
    """
    ⚠️ Interventions requises (alertes)
    
    Retourne les commandes nécessitant une intervention manuelle
    """
    try:
        from core.botlive_dashboard_data import get_interventions_required
        
        interventions = await get_interventions_required(company_id)
        
        return JSONResponse(content={
            "success": True,
            "interventions": interventions,
            "count": len(interventions)
        })
        
    except Exception as e:
        logger.error(f"[BOTLIVE][INTERVENTIONS] Erreur: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/activity/{company_id}")
async def get_realtime_activity_endpoint(company_id: str, limit: int = 10):
    """
    ⚡ Activité en temps réel
    
    Returns:
        [
            {
                "type": "commande_enregistree",
                "client": "Sophie Laurent",
                "produit": "1x Produit A",
                "timestamp": "il y a 2 min"
            },
            ...
        ]
    """
    try:
        from core.botlive_dashboard_data import get_realtime_activity
        
        activities = await get_realtime_activity(company_id, limit)
        
        return JSONResponse(content={
            "success": True,
            "activities": activities
        })
        
    except Exception as e:
        logger.error(f"[BOTLIVE][ACTIVITY] Erreur: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/deposits")
async def create_deposit(req: DepositRequest):
    try:
        from core.botlive_dashboard_data import insert_deposit

        deposit = await insert_deposit(
            company_id=req.company_id,
            amount_xof=req.amount_xof,
            order_id=req.order_id,
            payment_method=req.payment_method,
            validated_by=req.validated_by,
        )

        return JSONResponse(content={
            "success": True,
            "deposit": deposit,
        })

    except Exception as e:
        logger.error(f"[BOTLIVE][DEPOSITS][CREATE] Erreur: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/deposits/{company_id}")
async def list_deposits(company_id: str, limit: int = 50):
    try:
        from core.botlive_dashboard_data import _fetch_deposits

        now = datetime.utcnow()
        start_date = now - timedelta(days=30)
        deposits = await _fetch_deposits(company_id, start_date, now)
        deposits_sorted = sorted(deposits, key=lambda d: d.get("validated_at", ""), reverse=True)

        return JSONResponse(content={
            "success": True,
            "deposits": deposits_sorted[:limit],
            "total": len(deposits_sorted),
        })

    except Exception as e:
        logger.error(f"[BOTLIVE][DEPOSITS][LIST] Erreur: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str, limit: int = 50):
    try:
        import httpx
        from core.botlive_dashboard_data import SUPABASE_URL, SUPABASE_KEY

        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
        }
        url = f"{SUPABASE_URL}/rest/v1/messages"
        params = {
            "conversation_id": f"eq.{conversation_id}",
            "select": "*",
            "order": "created_at.asc",
            "limit": str(limit),
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers, params=params)

        if resp.status_code == 200:
            return JSONResponse(content={"success": True, "messages": resp.json()})

        logger.error(f"[BOTLIVE][MESSAGES] Erreur fetch messages: {resp.status_code} - {resp.text}")
        return JSONResponse(content={"success": False, "error": "Erreur récupération messages"}, status_code=500)

    except Exception as e:
        logger.error(f"[BOTLIVE][MESSAGES] Exception: {e}")
        raise HTTPException(status_code=500, detail="Erreur récupération messages")


@router.post("/interventions/{conversation_id}/take-over")
async def take_over_intervention(conversation_id: str):
    try:
        import httpx
        from core.botlive_dashboard_data import SUPABASE_URL, SUPABASE_KEY

        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
        }
        url = f"{SUPABASE_URL}/rest/v1/conversations"
        params = {"id": f"eq.{conversation_id}"}
        payload = {
            "priority": "high",
            "status": "in_progress",
            "updated_at": datetime.utcnow().isoformat(),
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.patch(url, headers=headers, params=params, json=payload)

        if resp.status_code in (200, 204):
            return JSONResponse(content={"success": True})

        logger.error(f"[BOTLIVE][INTERVENTIONS] Erreur take-over: {resp.status_code} - {resp.text}")
        return JSONResponse(content={"success": False, "error": "Erreur mise à jour intervention"}, status_code=500)

    except Exception as e:
        logger.error(f"[BOTLIVE][INTERVENTIONS] Exception take-over: {e}")
        raise HTTPException(status_code=500, detail="Erreur prise en charge intervention")


@router.post("/interventions/{conversation_id}/resolve")
async def resolve_intervention(conversation_id: str):
    try:
        import httpx
        from core.botlive_dashboard_data import SUPABASE_URL, SUPABASE_KEY

        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
        }
        url = f"{SUPABASE_URL}/rest/v1/conversations"
        params = {"id": f"eq.{conversation_id}"}
        payload = {
            "priority": "normal",
            "status": "resolved",
            "updated_at": datetime.utcnow().isoformat(),
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.patch(url, headers=headers, params=params, json=payload)

        if resp.status_code in (200, 204):
            return JSONResponse(content={"success": True})

        logger.error(f"[BOTLIVE][INTERVENTIONS] Erreur resolve: {resp.status_code} - {resp.text}")
        return JSONResponse(content={"success": False, "error": "Erreur résolution intervention"}, status_code=500)

    except Exception as e:
        logger.error(f"[BOTLIVE][INTERVENTIONS] Exception resolve: {e}")
        raise HTTPException(status_code=500, detail="Erreur résolution intervention")


# ═══════════════════════════════════════════════════════════════════════════════
# 🔗 ENDPOINTS WEBHOOKS N8N
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/webhook/register")
async def register_webhook(config: WebhookConfig):
    """
    📡 Enregistrer un webhook N8N
    
    Permet à N8N de s'abonner aux événements Botlive
    """
    try:
        # TODO: Stocker config webhook dans Supabase
        logger.info(f"[BOTLIVE][WEBHOOK] Enregistrement webhook: {config.webhook_url}")
        
        return JSONResponse(content={
            "success": True,
            "message": "Webhook enregistré",
            "config": config.dict()
        })
        
    except Exception as e:
        logger.error(f"[BOTLIVE][WEBHOOK] Erreur enregistrement: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhook/test")
async def test_webhook(webhook_url: str):
    """
    🧪 Tester un webhook
    
    Envoie un événement de test pour vérifier la connexion N8N
    """
    try:
        import httpx
        
        test_payload = {
            "event": "test",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "message": "Test webhook Botlive"
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=test_payload, timeout=5.0)
            
        return JSONResponse(content={
            "success": response.status_code == 200,
            "status_code": response.status_code,
            "response": response.text[:200]
        })
        
    except Exception as e:
        logger.error(f"[BOTLIVE][WEBHOOK][TEST] Erreur: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════════════════════════════════════════
# 🛠️ HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

async def get_order_state(user_id: str, company_id: str) -> Dict[str, Any]:
    """Récupère l'état actuel de la commande"""
    try:
        from core.order_state_tracker import order_tracker
        
        state = order_tracker.get_state(user_id)
        
        return {
            "produit": state.produit or "",
            "produit_details": getattr(state, "produit_details", None) or "",
            "paiement": state.paiement or "",
            "zone": state.zone or "",
            "numero": state.numero or "",
            "completion_rate": state.get_completion_rate(),
            "is_complete": state.is_complete()
        }
    except Exception as e:
        logger.error(f"[BOTLIVE] Erreur get_order_state: {e}")
        return {
            "produit": "",
            "produit_details": "",
            "paiement": "",
            "zone": "",
            "numero": "",
            "completion_rate": 0,
            "is_complete": False
        }

def _determine_next_step(order_status: Dict[str, Any]) -> str:
    """Détermine la prochaine étape du workflow"""
    if order_status["is_complete"]:
        return "completed"
    elif not order_status["produit"]:
        return "produit"
    elif not order_status["paiement"]:
        return "paiement"
    elif not order_status["zone"]:
        return "zone"
    elif not order_status["numero"]:
        return "numero"
    else:
        return "completed"

async def trigger_webhook(event_type: str, data: Dict[str, Any]):
    """Déclenche un webhook N8N"""
    try:
        # TODO: Récupérer webhook URL depuis Supabase
        # TODO: Envoyer requête HTTP au webhook
        logger.info(f"[BOTLIVE][WEBHOOK] Événement: {event_type}, data: {data}")
        pass
    except Exception as e:
        logger.error(f"[BOTLIVE][WEBHOOK] Erreur trigger: {e}")


async def get_or_create_conversation(
    company_id: str,
    user_id: str,
    user_display_name: Optional[str] = None,
) -> Optional[str]:
    """Récupère ou crée une conversation pour (company_id, user_id) via Supabase.

    Utilise la table `company_mapping` pour mapper company_id texte -> UUID,
    puis la table `conversations`.

    customer_name reste basé sur user_id (identifiant logique), tandis que
    user_display_name est stocké dans metadata si fourni pour l'affichage.
    """

    try:
        import httpx
        from core.botlive_dashboard_data import SUPABASE_URL, SUPABASE_KEY, _get_company_uuid

        company_uuid = await _get_company_uuid(company_id)
        if not company_uuid:
            logger.warning(
                "[CONVERSATIONS] UUID introuvable pour company_id_text=%s",
                company_id,
            )
            return None

        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
        }

        # 1) Chercher une conversation existante pour ce couple
        conv_url = f"{SUPABASE_URL}/rest/v1/conversations"
        conv_params = [
            ("company_id", f"eq.{company_uuid}"),
            # Le schéma Lovable n'a pas de colonne user_id, on utilise customer_name
            ("customer_name", f"eq.{user_id}"),
            ("select", "id"),
            ("order", "created_at.desc"),
            ("limit", "1"),
        ]

        async with httpx.AsyncClient() as client:
            conv_resp = await client.get(conv_url, headers=headers, params=conv_params)

        if conv_resp.status_code != 200:
            logger.error(f"[BOTLIVE][HISTORY] Erreur fetch conversations: {conv_resp.status_code} - {conv_resp.text}")
            return ""

        conversations = conv_resp.json() or []
        if not conversations:
            return ""

        conversation_id = conversations[0].get("id")
        if not conversation_id:
            return ""

        # 2) Récupérer les messages de cette conversation
        msg_url = f"{SUPABASE_URL}/rest/v1/messages"
        msg_params = [
            ("conversation_id", f"eq.{conversation_id}"),
            ("select", "role,content,created_at"),
            ("order", "created_at.asc"),
            ("limit", "20"),
        ]

        async with httpx.AsyncClient() as client:
            msg_resp = await client.get(msg_url, headers=headers, params=msg_params)

        if msg_resp.status_code != 200:
            logger.error(f"[BOTLIVE][HISTORY] Erreur fetch messages: {msg_resp.status_code} - {msg_resp.text}")
            return ""

        messages = msg_resp.json() or []
        if not messages:
            return ""

        # 3) Construire l'historique textuel user:/IA:
        lines = []
        for m in messages:
            role = (m.get("role") or "").lower()
            content = m.get("content") or ""
            # Les tables Lovable stockent déjà content en texte
            prefix = "user:" if role == "user" else "IA:"
            lines.append(f"{prefix} {content}".strip())

        history = "\n".join(lines)
        logger.info(f"[BOTLIVE][HISTORY] Reconstruit {len(messages)} messages pour {user_id} ({len(history)} chars)")
        return history

    except Exception as e:
        logger.error(f"[BOTLIVE][HISTORY] Exception reconstruction historique: {e}")
        return ""

# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 ENDPOINTS ADMIN
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/admin/clear-state/{user_id}")
async def clear_user_state(user_id: str):
    """🗑️ Réinitialiser l'état d'une commande (admin)"""
    try:
        from core.order_state_tracker import order_tracker
        order_tracker.clear_state(user_id)
        
        return JSONResponse(content={
            "success": True,
            "message": f"État réinitialisé pour {user_id}"
        })
    except Exception as e:
        logger.error(f"[BOTLIVE][ADMIN] Erreur clear_state: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def botlive_health():
    """🏥 Health check du système Botlive"""
    try:
        if DISABLE_VISION_MODELS:
            return JSONResponse(content={
                "status": "healthy",
                "engine": "disabled",
                "timestamp": datetime.utcnow().isoformat()
            })

        from core.botlive_engine import get_botlive_engine

        engine = get_botlive_engine()

        return JSONResponse(content={
            "status": "healthy",
            "engine": "initialized",
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"[BOTLIVE][HEALTH] Erreur: {e}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "error_type": type(e).__name__,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            },
            status_code=503
        )
