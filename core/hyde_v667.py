import re
from typing import Dict, Any

from core.order_state_tracker import order_tracker

INTENT_KEYWORDS = {
    "INTENT_ACHAT": [
        "je veux", "je desire", "je désire", "commande", "commander", "acheter",
        "prix", "coûte", "cout", "promo", "promotions", "disponible", "stock"
    ],
    "PAIEMENT": ["paiement", "payer", "acompte", "versement", "reçu", "preuve"],
    "LIVRAISON": ["livraison", "livrer", "zone", "quartier", "où êtes", "ou etes"],
    "QUESTION_INFO": ["info", "informations", "comment", "combien", "c'est quoi", "cest quoi"],
    "SALUTATION": ["bonjour", "bonsoir", "salut", "merci", "coucou", "hello", "hey"],
    "SUIVI_COMMANDE": ["suivi", "où est ma commande", "ou est ma commande", "avancement", "statut"],
}


def _detect_intent(message: str) -> str:
    m = (message or "").lower()
    # strong purchase first
    for intent, kws in INTENT_KEYWORDS.items():
        for kw in kws:
            if kw in m:
                return intent
    if len(m.strip()) <= 1:
        return "MESSAGE_FLOU"
    if re.fullmatch(r"[\?\!\.]+", m):
        return "MESSAGE_FLOU"
    return "QUESTION_INFO"


def _compute_state(user_id: str) -> Dict[str, Any]:
    st = order_tracker.get_state(user_id)
    digits = "".join(ch for ch in (st.numero or "") if ch.isdigit()) if getattr(st, "numero", None) else ""
    tel_valide = len(digits) == 10
    s = {
        "photo_collected": bool(getattr(st, "produit", None)),
        "paiement_collected": bool(getattr(st, "paiement", None)),
        "zone_collected": bool(getattr(st, "zone", None)),
        "tel_collected": bool(getattr(st, "numero", None)),
        "tel_valide": tel_valide,
    }
    s["collected_count"] = int(s["photo_collected"]) + int(s["paiement_collected"]) + int(s["zone_collected"]) + int(s["tel_collected"] and s["tel_valide"])
    s["is_complete"] = bool(getattr(st, "is_complete", lambda: False)()) if hasattr(st, "is_complete") else False
    return s


def _missing_fields(state: Dict[str, Any]) -> list:
    out = []
    if not state.get("photo_collected"): out.append("photo")
    if not state.get("paiement_collected"): out.append("paiement")
    if not state.get("zone_collected"): out.append("zone")
    if not (state.get("tel_collected") and state.get("tel_valide")): out.append("tel")
    return out


def _decide_mode(intent: str, state: Dict[str, Any]) -> str:
    if state.get("is_complete"): return "RECEPTION_SAV"
    if intent in ("INTENT_ACHAT", "PAIEMENT", "LIVRAISON") or state.get("collected_count", 0) > 0:
        return "COMMANDE"
    if intent == "SUIVI_COMMANDE":
        return "RECEPTION_SAV"
    return "GUIDEUR"


def _confidence_heuristic(intent: str, message: str, state: Dict[str, Any]) -> float:
    m = (message or "").lower()
    c = 0.6
    if intent == "INTENT_ACHAT": c = 0.85
    if intent in ("PAIEMENT", "LIVRAISON"): c = 0.8
    if intent == "SALUTATION": c = 0.65
    if intent == "SUIVI_COMMANDE": c = 0.75
    if intent == "MESSAGE_FLOU": c = 0.4
    # boosters
    if any(k in m for k in ["couche", "lingette", "pampers", "pack", "taille"]):
        c = max(c, 0.82)
    if state.get("collected_count", 0) >= 2:
        c = max(c, 0.88)
    return min(max(c, 0.0), 1.0)


def route_v667(company_id: str, user_id: str, message: str, conversation_history: str) -> Dict[str, Any]:
    state = _compute_state(user_id)
    intent = _detect_intent(message)
    mode = _decide_mode(intent, state)
    conf = _confidence_heuristic(intent, message, state)
    missing = _missing_fields(state)

    if conf >= 0.90:
        action = "PROMPT_LIGHT"
    elif conf >= 0.70:
        action = "PROMPT_NORMAL"
    elif conf >= 0.50:
        action = "HYBRID_ENGINE"
    else:
        action = "CLARIFY"

    return {
        "success": True,
        "intent": intent,
        "confidence": conf,
        "mode": mode,
        "missing_fields": missing,
        "state": state,
        "action": action,
    }
