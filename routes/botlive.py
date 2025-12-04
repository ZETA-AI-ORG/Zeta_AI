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

from config import N8N_OUTBOUND_WEBHOOK_URL, N8N_API_KEY, N8N_DEBUG_MODE
from core.intervention_logger import log_intervention_in_conversation_logs, log_message_in_conversation_logs
from core.intervention_guardian import get_intervention_guardian

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/botlive", tags=["botlive"])

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

        explicit_handoff_keywords = [
            "parler a un humain",
            "parler à un humain",
            "parler a quelqu'un",
            "parler à quelqu'un",
            "parler a un conseiller",
            "parler à un conseiller",
            "parler a un agent",
            "parler à un agent",
            "parler a quelquun",
            "parler à quelquun",
            "un humain s'il vous plait",
            "un humain s il vous plait",
        ]
        explicit_handoff = any(kw in msg_lower for kw in explicit_handoff_keywords)

        caps_ratio = 0.0
        if msg_text:
            letters = [c for c in msg_text if c.isalpha()]
            if letters:
                caps = [c for c in letters if c.isupper()]
                if caps:
                    caps_ratio = len(caps) / len(letters)

        negative_keywords = [
            "service de merde",
            "nul",
            "pourri",
            "inadmissible",
        ]
        is_frustrated = caps_ratio > 0.7 or any(kw in msg_lower for kw in negative_keywords)

        logger.info(
            "[BOTLIVE][%s] Intervention signals | explicit_handoff=%s is_frustrated=%s caps_ratio=%.2f",
            request_id,
            explicit_handoff,
            is_frustrated,
            caps_ratio,
        )

        if explicit_handoff or is_frustrated:
            reason = "explicit_handoff" if explicit_handoff else "customer_frustration"
            try:
                logger.info(
                    "[BOTLIVE][%s] Intervention (rule-based) triggered | reason=%s message=%s",
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
                    },
                    channel="botlive",
                    direction="user",
                    source="botlive_gateway",
                )
            except Exception as log_err:
                logger.error("[BOTLIVE][%s] Failed to log explicit/frustration intervention: %s", request_id, log_err)

        # Traiter le message
        start_time = time.time()
        user_display_name = req.user_display_name

        # Vérifier si la commande est déjà complétée AVANT d'appeler le moteur Botlive
        pre_order_status = await get_order_state(req.user_id, req.company_id)
        pre_next_step = _determine_next_step(pre_order_status)

        post_recap = bool(pre_order_status.get("is_complete")) or pre_next_step == "completed"

        if post_recap:
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
        conversation_history = await _build_conversation_history_from_messages(
            company_id=req.company_id,
            user_id=req.user_id,
        )

        # Import lazy pour éviter circular import
        import app
        response = await app._botlive_handle(
            company_id=req.company_id,
            user_id=req.user_id,
            message=req.message,
            images=req.images,
            conversation_history=conversation_history
        )
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
        
        return JSONResponse(content={
            "success": True,
            "response": response,
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

@router.post("/message/stream")
async def process_botlive_message_stream(req: BotliveMessageRequest):
    """
    🌊 ENDPOINT STREAMING - Réponse en temps réel (SSE)
    
    Pour une meilleure UX avec affichage progressif de la réponse
    """
    request_id = str(uuid.uuid4())[:8]
    
    async def event_generator():
        try:
            # Import
            from app import _botlive_handle
            
            # Envoyer événement de démarrage
            yield f"data: {{'event': 'start', 'request_id': '{request_id}'}}\n\n"
            
            # Traiter le message
            response = await _botlive_handle(
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

        url = f"{SUPABASE_URL}/rest/v1/conversations"

        # 1) Chercher une conversation existante pour ce couple
        params = {
            "company_id": f"eq.{company_uuid}",
            "customer_name": f"eq.{user_id}",
            "select": "id,metadata",
            "order": "created_at.desc",
            "limit": "1",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, params=params, timeout=5.0)

        if resp.status_code == 200:
            rows = resp.json() or []
            if rows:
                conv = rows[0]
                conv_id = conv.get("id")
                if conv_id:
                    # Si un user_display_name est fourni et absent de la metadata existante,
                    # on met à jour la conversation pour faciliter l'affichage dans le dashboard.
                    if user_display_name:
                        try:
                            existing_meta = conv.get("metadata") or {}
                            # metadata peut être une chaîne JSON ou un dict
                            if isinstance(existing_meta, str):
                                import json as _json
                                try:
                                    existing_meta = _json.loads(existing_meta)
                                except Exception:
                                    existing_meta = {}

                            if not isinstance(existing_meta, dict):
                                existing_meta = {}

                            if existing_meta.get("user_display_name") != user_display_name:
                                existing_meta.setdefault("user_id", user_id)
                                existing_meta["user_display_name"] = user_display_name

                                # Mettre à jour metadata + nouvelle colonne customer_display_name
                                patch_payload = {
                                    "metadata": existing_meta,
                                    "customer_display_name": user_display_name,
                                }
                                patch_params = {"id": f"eq.{conv_id}"}

                                async with httpx.AsyncClient() as client:
                                    await client.patch(
                                        url,
                                        headers=headers,
                                        params=patch_params,
                                        json=patch_payload,
                                        timeout=5.0,
                                    )
                        except Exception as meta_err:
                            logger.warning(
                                "[CONVERSATIONS] Impossible de mettre à jour metadata pour %s: %s",
                                conv_id,
                                meta_err,
                            )

                    return conv_id

        # 2) Aucune conversation → en créer une nouvelle
        metadata: Dict[str, Any] = {"user_id": user_id}
        if user_display_name:
            metadata["user_display_name"] = user_display_name

        payload: Dict[str, Any] = {
            "company_id": company_uuid,
            "customer_name": user_id,
            "metadata": metadata,
        }

        # Nouvelle colonne texte: customer_display_name
        if user_display_name:
            payload["customer_display_name"] = user_display_name

        async with httpx.AsyncClient() as client:
            create_resp = await client.post(
                url,
                headers={**headers, "Prefer": "return=representation"},
                json=payload,
                timeout=5.0,
            )

        if create_resp.status_code in (200, 201):
            body = create_resp.json()
            if isinstance(body, list) and body:
                return body[0].get("id")
            if isinstance(body, dict):
                return body.get("id")

        logger.error(
            "[CONVERSATIONS] Erreur création conversation: %s - %s",
            create_resp.status_code,
            create_resp.text,
        )
        return None

    except Exception as exc:  # pragma: no cover - log uniquement
        logger.error("[CONVERSATIONS] Exception get_or_create_conversation: %s", exc)
        return None


async def insert_message(
    conversation_id: str,
    role: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """Insère un message dans la table messages."""

    try:
        import httpx
        from core.botlive_dashboard_data import SUPABASE_URL, SUPABASE_KEY

        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
        }

        url = f"{SUPABASE_URL}/rest/v1/messages"

        payload: Dict[str, Any] = {
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
        }

        if metadata is not None:
            # Si un author_name est fourni dans metadata, le refléter aussi
            # dans la colonne texte dédiée messages.author_name.
            author_name = metadata.get("author_name") if isinstance(metadata, dict) else None
            if author_name:
                payload["author_name"] = author_name

            payload["metadata"] = metadata

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                headers={**headers, "Prefer": "return=minimal"},
                json=payload,
                timeout=5.0,
            )

        if resp.status_code in (200, 201, 204):
            logger.info(
                "[CONVERSATIONS] Message inséré (conv=%s, role=%s, len=%s)",
                conversation_id,
                role,
                len(content or ""),
            )
            return True

        logger.error(
            "[CONVERSATIONS] Erreur insert_message: %s - %s",
            resp.status_code,
            resp.text,
        )
        return False

    except Exception as exc:  # pragma: no cover - log uniquement
        logger.error("[CONVERSATIONS] Exception insert_message: %s", exc)
        return False


async def _build_conversation_history_from_messages(company_id: str, user_id: str, max_messages: int = 20) -> str:
    """Reconstruit l'historique textuel depuis les tables conversations/messages.

    Format de sortie aligné avec les anciens tests Botlive:
        user: Bonjour, je veux commander
        IA: D'accord ! ...

    On récupère la conversation la plus récente pour (company_id_text, user_id)
    puis les messages associés, triés par created_at asc.
    """
    try:
        import httpx
        from core.botlive_dashboard_data import SUPABASE_URL, SUPABASE_KEY, _get_company_uuid

        # Mapper company_id texte -> UUID si possible
        company_uuid = await _get_company_uuid(company_id)
        if not company_uuid:
            company_uuid = company_id

        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
        }

        # 1) Récupérer la conversation la plus récente pour ce couple
        conv_url = f"{SUPABASE_URL}/rest/v1/conversations"
        conv_params = [
            ("company_id", f"eq.{company_uuid}"),
            # Le schéma Lovable n'a pas de colonne user_id, on utilise customer_name
            ("customer_name", f"eq.{user_id}"),
            ("select", "id"),
            ("order", "created_at.desc"),
            ("limit", "1"),
        ]

        async with httpx.AsyncClient(timeout=10.0) as client:
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
            ("limit", str(max_messages)),
        ]

        async with httpx.AsyncClient(timeout=10.0) as client:
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
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            },
            status_code=503
        )
