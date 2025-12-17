MONITORED_INTENTS = {"COMMANDE_EXISTANTE", "PAIEMENT"}
TRUST_HIGH_THRESHOLD = {"score": 0.95}
TRUST_MONITORED_MARGIN_THRESHOLD = 0.05
TRUST_MARGIN_THRESHOLD = 0.50


def is_safe_to_trust(intent: str, score: float, margin: float) -> bool:
    upper_intent = (intent or "").upper().strip()

    try:
        score_f = float(score)
    except Exception:
        score_f = 0.0

    try:
        margin_f = float(margin)
    except Exception:
        margin_f = 0.0

    if score_f >= float(TRUST_HIGH_THRESHOLD["score"]):
        if upper_intent in MONITORED_INTENTS:
            return margin_f >= float(TRUST_MONITORED_MARGIN_THRESHOLD)
        return True

    if margin_f >= float(TRUST_MARGIN_THRESHOLD):
        return True

    return False
