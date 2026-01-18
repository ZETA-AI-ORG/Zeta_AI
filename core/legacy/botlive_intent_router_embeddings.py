from __future__ import annotations

from dataclasses import dataclass

import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

import json
import logging
import re

import numpy as np

from core.greeting_analyzer import GreetingAnalyzer
from core.hyde_prefilter import HydePrefilter
from core.hyde_reformulator import HydeReformulator
from core.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)

@dataclass
class BotliveRoutingResult:
    intent: str
    confidence: float
    mode: str
    missing_fields: List[str]
    state: Dict[str, Any]
    debug: Dict[str, Any]

_INTENTS_JSON_PATH = Path(__file__).resolve().parents[1] / "intents" / "ecommerce_intents.json"
_intent_prototypes: Dict[str, np.ndarray] | None = None
_greeting_analyzer: GreetingAnalyzer | None = None
_word_families: Dict[str, Any] | None = None


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _normalize_vec(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=np.float32)
    n = float(np.linalg.norm(v))
    if n <= 0.0:
        return v
    return v / n


def _embed_query(text: str) -> np.ndarray | None:
    t = (text or "").strip()
    if not t:
        return None

    service = get_embedding_service()
    vec = service.encode(t)
    return _normalize_vec(np.asarray(vec, dtype=np.float32))


def _load_model_and_prototypes() -> Dict[str, np.ndarray]:
    """Charge le modèle HF et les prototypes d'intents à partir du JSON."""
    global _intent_prototypes

    if _intent_prototypes is None:
        data = None
        used_source = "json"

        try:
            from core.universal_corpus import UNIVERSAL_ECOMMERCE_INTENT_CORPUS as UC

            index_to_intent = {
                1: "SALUT",
                2: "INFO_GENERALE",
                3: "CLARIFICATION",
                4: "PRODUIT_GLOBAL",
                5: "PRIX_PROMO",
                6: "ACHAT_COMMANDE",
                7: "LIVRAISON",
                8: "PAIEMENT",
                9: "CONTACT_COORDONNEES",
                10: "COMMANDE_EXISTANTE",
                11: "PROBLEME",
            }

            built = []
            for k in sorted(UC.keys()):
                try:
                    idx = int(k)
                except Exception:
                    continue
                canon = index_to_intent.get(idx)
                if not canon:
                    continue
                entry = UC[k]
                examples = entry.get("exemples_universels", []) or []
                examples = [e for e in examples if isinstance(e, str) and e.strip()]
                if not examples:
                    continue
                built.append({"intent": canon, "examples": examples})

            if built:
                data = built
                used_source = "universal_python"
        except Exception:
            data = None
            used_source = "json"

        if data is None:
            if not _INTENTS_JSON_PATH.exists():
                raise FileNotFoundError(f"Corpus intents introuvable: {_INTENTS_JSON_PATH}")

            with _INTENTS_JSON_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)

        prototypes: Dict[str, Any] = {}
        service = get_embedding_service()
        for item in data:
            intent_name = str(item.get("intent")).strip()
            examples = [e for e in item.get("examples", []) if isinstance(e, str) and e.strip()]
            if not intent_name or not examples:
                continue

            vecs = service.encode(examples)
            mat = np.vstack([np.asarray(v, dtype=np.float32) for v in vecs])
            proto = _normalize_vec(mat.mean(axis=0))
            prototypes[intent_name] = proto
            used_source = "local_embedding_service"

        if not prototypes:
            raise RuntimeError("Aucun prototype d'intent généré depuis le corpus JSON")

        _intent_prototypes = {k: np.asarray(v, dtype=np.float32) for k, v in prototypes.items()}

    return _intent_prototypes


def _get_greeting_analyzer() -> GreetingAnalyzer:
    global _greeting_analyzer
    if _greeting_analyzer is None:
        _greeting_analyzer = GreetingAnalyzer()
    return _greeting_analyzer


def _load_word_families() -> Dict[str, Any]:
    """Charge les familles de mots depuis le JSON généré par extract_word_families."""

    global _word_families

    if _word_families is None:
        families_path = (
            Path(__file__).resolve().parents[1]
            / "intents"
            / "keywords"
            / "word_families.json"
        )

        if not families_path.exists():
            _word_families = {"families_by_intent": {}}
            return _word_families

        with families_path.open("r", encoding="utf-8") as f:
            _word_families = json.load(f)

    return _word_families or {"families_by_intent": {}}


def get_delivery_delay_similarity(message: str) -> float:
    """Calcule la similarité embeddings entre le message et l'intent LIVRAISON.

    Utilisé pour router les questions de délai de livraison vers Python quand
    la confiance est élevée (>= 0.80), afin d'éviter un appel LLM inutile.
    """

    text = (message or "").strip()
    if not text:
        return 0.0

    try:
        prototypes = _load_model_and_prototypes()
    except Exception:
        return 0.0

    proto = prototypes.get("LIVRAISON")
    if proto is None:
        return 0.0

    try:
        query_emb = _embed_query(text)
        if query_emb is None:
            return 0.0
        if query_emb.shape != proto.shape:
            return 0.0
        score = float(cosine_sim(query_emb, proto))
        return max(-1.0, min(1.0, score))
    except Exception:
        return 0.0


def _match_word_family(text: str, intent: str) -> float:
    """Calcule un score de correspondance avec les familles de mots d'un intent."""

    families_data = _load_word_families()
    families = families_data.get("families_by_intent", {}).get(intent, [])

    if not families:
        return 0.0

    text_lower = (text or "").lower()
    matches = 0
    total_weight = 0

    for family in families:
        canonical = family.get("canonical", "")
        variants = family.get("variants", []) or []
        freq = int(family.get("total_frequency", 1) or 1)

        all_forms = [canonical] + [v for v in variants if isinstance(v, str)]

        if any(form and form in text_lower for form in all_forms):
            matches += 1
            total_weight += max(freq, 1)

    if not families:
        return 0.0

    match_ratio = matches / len(families)

    if total_weight > 0 and matches > 0:
        avg_freq = total_weight / matches
        freq_bonus = min(avg_freq / 50.0, 0.3)
        match_ratio = min(match_ratio + freq_bonus, 1.0)

    return float(match_ratio)


def _apply_lexical_boosts(text: str, scores: Dict[str, float]) -> Dict[str, float]:
    """🔧 PATCH - Boosts lexicaux renforcés pour PAYMENT/DELIVERY/TRACKING."""
    t = (text or "").lower()
    if not t.strip():
        return scores

    updated = scores.copy()

    def _apply(intent: str, factor: float) -> None:
        if intent not in updated:
            return
        val = updated[intent] * factor
        val = max(-1.0, min(1.0, val))
        updated[intent] = val

    if "facture" in t or "reçu" in t or "recu" in t:
        _apply("PAIEMENT", 1.35)
        _apply("PROBLEME", 0.65)
        _apply("COMMANDE_EXISTANTE", 0.85)

    if "suivi" in t or "tracking" in t or "statut" in t:
        _apply("COMMANDE_EXISTANTE", 1.25)
        _apply("ACHAT_COMMANDE", 0.85)

    if "livraison" in t and "combien" in t:
        _apply("LIVRAISON", 1.20)
        _apply("COMMANDE_EXISTANTE", 0.90)

    return updated


def _apply_lexical_boosts_with_families(text: str, scores: Dict[str, float]) -> Dict[str, float]:
    """Boosts lexicaux standards + renfort via familles de mots Shadow."""

    updated = _apply_lexical_boosts(text, scores)

    intent_mapping = {
        "SALUT": "SALUT",
        "INFO_GENERALE": "INFO_GENERALE",
        "CLARIFICATION": "CLARIFICATION",
        "PRODUIT_GLOBAL": "PRODUIT_GLOBAL",
        "PRIX_PROMO": "PRIX_PROMO",
        "ACHAT_COMMANDE": "ACHAT_COMMANDE",
        "LIVRAISON": "LIVRAISON",
        "PAIEMENT": "PAIEMENT",
        "CONTACT_COORDONNEES": "CONTACT_COORDONNEES",
        "COMMANDE_EXISTANTE": "COMMANDE_EXISTANTE",
        "PROBLEME": "PROBLEME",
    }

    for intent_code, base_score in list(updated.items()):
        family_name = intent_mapping.get(intent_code)
        if not family_name:
            continue

        family_score = _match_word_family(text, family_name)
        if family_score <= 0.2:
            continue

        boost_factor = 1.0 + family_score * 0.30
        boosted = base_score * boost_factor
        updated[intent_code] = max(-1.0, min(1.0, boosted))

    return updated


def _route_with_embeddings(message: str) -> Tuple[str, float]:
    raw = (message or "").strip()
    if not raw:
        return "CLARIFICATION", 0.0

    analyzer = _get_greeting_analyzer()
    analysis = analyzer.analyze(raw)
    route_to = analysis.get("route_to", "EMBED_FULL")

    if route_to == "SALUT":
        rest_text = (analysis.get("rest_text") or "").strip().lower()
        business_triggers = [
            "vous livrez",
            "livrez",
            "vous couvrez",
            "mobile money",
            "wave",
            "orange money",
            "vous acceptez",
            "acceptez",
            "combien",
            "prix",
            "tarif",
            "commander",
            "acheter",
            "numéro",
            "numero",
            "téléphone",
            "telephone",
            "tel",
            "whatsapp",
        ]

        has_business_question = any(trigger in rest_text for trigger in business_triggers)
        if has_business_question and len(rest_text) > 8:
            route_to = "EMBED_REST"
            text = rest_text
        else:
            confidence = float(analysis.get("confidence", 0.9))
            return "SALUT", confidence

    if route_to == "EMBED_REST":
        text = (analysis.get("rest_text") or raw).strip()
    else:
        text = raw

    prototypes = _load_model_and_prototypes()
    query_emb = _embed_query(text)
    if query_emb is None:
        return "CLARIFICATION", 0.0

    scores: Dict[str, float] = {}
    for intent, proto in prototypes.items():
        if query_emb.shape != proto.shape:
            scores[intent] = 0.0
            continue
        scores[intent] = float(cosine_sim(query_emb, proto))

    scores = _apply_lexical_boosts_with_families(text, scores)

    best_intent = max(scores.items(), key=lambda x: x[1])[0]
    best_score = scores[best_intent]

    t_lower = text.lower()
    modification_annulation_triggers = ["modifier", "annuler", "changer", "supprimer"]
    modification_hit = any(trigger in t_lower for trigger in modification_annulation_triggers)
    modification_context = ["commande", "colis", "livraison", "adresse", "zone"]
    has_order_context = any(ctx in t_lower for ctx in modification_context)

    if modification_hit and has_order_context:
        best_intent = "COMMANDE_EXISTANTE"
        best_score = max(best_score, 0.75)

    try:
        min_score = float(os.getenv("BOTLIVE_EMBEDDING_MIN_SCORE", "0.45"))
    except Exception:
        min_score = 0.45

    if best_score < min_score:
        return "CLARIFICATION", best_score

    return best_intent, best_score


def _determine_mode_from_intent(intent: str, *, is_complete: bool, collected_count: int) -> str:
    """Détermine le mode Jessica (COMMANDE / GUIDEUR / RECEPTION_SAV) à partir de l'intent.

    Règles métier:
    - Si la commande est complète → RECEPTION_SAV (prise en charge humaine / SAV)
    - ACHAT_COMMANDE / CONFIRMATION_PAIEMENT → COMMANDE
    - Intents "guidage" (recherche, infos, salut, clarification, prix, livraison, etc.) → GUIDEUR
    - Intents SAV (COMMANDE_EXISTANTE, PROBLEME, PROBLEME_LIVRAISON, etc.) → RECEPTION_SAV
    - Fallback: GUIDEUR si au moins un champ est collecté, sinon RECEPTION_SAV.
    """

    if is_complete:
        return "RECEPTION_SAV"

    upper_intent = (intent or "").upper()

    mode_mapping = {
        # Commande
        "ACHAT_COMMANDE": "COMMANDE",
        "CONFIRMATION_PAIEMENT": "COMMANDE",
        "CONTACT_COORDONNEES": "COMMANDE",

        # Guidage
        "PRODUIT_GLOBAL": "GUIDEUR",
        "INFO_GENERALE": "GUIDEUR",
        "QUESTION_PAIEMENT": "GUIDEUR",
        "INFO_LIVRAISON": "GUIDEUR",
        "PRIX_PROMO": "GUIDEUR",
        "SALUT": "GUIDEUR",
        "CLARIFICATION": "GUIDEUR",

        # SAV / post-commande
        "COMMANDE_EXISTANTE": "RECEPTION_SAV",
        "PROBLEME": "RECEPTION_SAV",
        "PROBLEME_LIVRAISON": "RECEPTION_SAV",
    }

    if upper_intent in mode_mapping:
        return mode_mapping[upper_intent]

    # Fallback en fonction de la progression de la collecte
    # ... (unchanged)


async def route_botlive_intent(
    company_id: str,
    user_id: str,
    message: str,
    conversation_history: str,
    state_compact: Dict[str, Any],
    hyde_pre_enabled: bool | None = None,
) -> BotliveRoutingResult:
    """Router d'intention Botlive basé sur embeddings HuggingFace + HYDE pré-routage."""

    ctx: Dict[str, Any] = {
        "conversation_history": conversation_history or "",
        "state_compact": state_compact or {},
    }

    hyde_pre_used = False
    hyde_pre_reason = "CLEAR_MESSAGE"
    original_message = message
    routed_message = message

    # Étape 1: HYDE pré-routage éventuel (reformulation avant embeddings)
    try:
        effective_hyde_pre_enabled = hyde_pre_enabled
        if effective_hyde_pre_enabled is None:
            effective_hyde_pre_enabled = os.getenv("BOTLIVE_HYDE_PRE_ENABLED", "true").strip().lower() in {
                "1",
                "true",
                "yes",
                "y",
                "on",
            }

        if not effective_hyde_pre_enabled:
            raise RuntimeError("HYDE_PRE_DISABLED")

        prefilter = HydePrefilter()
        should_use, reason = prefilter.should_use_hyde(message, ctx)
        hyde_pre_reason = reason

        if should_use:
            logger.info(f"[HYDE_PRE] Activation pour company={company_id}, reason={reason}")
            try:
                reformulator = HydeReformulator()
                routed_message = await reformulator.reformulate(company_id, message, ctx)
                hyde_pre_used = routed_message != message
            except Exception as e:
                logger.error(f"[HYDE_PRE] Erreur reformulation: {e}")
                routed_message = message
        else:
            routed_message = message
    except Exception as e:
        if str(e) != "HYDE_PRE_DISABLED":
            logger.error(f"[HYDE_PRE] Erreur préfiltre: {e}")
        routed_message = message

    # Étape 2: routage embeddings standard (sur message potentiellement reformulé)
    intent, score = _route_with_embeddings(routed_message)

    # Normaliser l'intent en MAJUSCULES pour l'exposer dans BotliveRoutingResult
    upper_intent = (intent or "").upper()

    confidence = float(max(0.0, min(1.0, score)))

    collected_count = int(state_compact.get("collected_count", 0))
    is_complete = bool(state_compact.get("is_complete", False))

    mode = _determine_mode_from_intent(upper_intent, is_complete=is_complete, collected_count=collected_count)

    missing: List[str] = []
    if not state_compact.get("photo_collected", False):
        missing.append("photo")
    if not state_compact.get("paiement_collected", False):
        missing.append("paiement")
    if not state_compact.get("zone_collected", False):
        missing.append("zone")
    if not state_compact.get("tel_collected", False) or not state_compact.get("tel_valide", False):
        missing.append("tel")

    debug = {
        "company_id": company_id,
        "user_id": user_id,
        "raw_message": message,
        "conversation_history_sample": conversation_history[-300:] if conversation_history else "",
        "intent_score": score,
        "hyde_pre_used": hyde_pre_used,
        "hyde_pre_reason": hyde_pre_reason,
        "original_message": original_message,
        "routed_message": routed_message,
    }

    return BotliveRoutingResult(
        intent=upper_intent,
        confidence=confidence,
        mode=mode,
        missing_fields=missing,
        state=state_compact,
        debug=debug,
    )