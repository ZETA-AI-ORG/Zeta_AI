import os
import re
from typing import Optional


def _truthy(v: Optional[str]) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


def should_inject_placeorder_logistique(query: str) -> bool:
    """Decide whether to inject the PLACEORDER_LOGISTIQUE block."""
    enabled = os.getenv("PLACEORDER_LOGISTIQUE_ENABLED", "true")
    if not _truthy(enabled):
        return False

    mode = str(os.getenv("PLACEORDER_LOGISTIQUE_MODE", "always") or "always").strip().lower()
    if mode in {"always", "on", "true", "1"}:
        return True

    if mode in {"on_delay", "delay", "keyword"}:
        q = str(query or "")
        q_l = q.lower()
        # Trigger on common French phrasing
        return bool(
            re.search(r"\b(d[ée]lai|delai|d[ée]lais)\b", q_l)
            or re.search(r"\b(livr[ée]e?\s*quand|livraison\s+quand)\b", q_l)
        )

    # Unknown mode -> safe default: do not inject
    return False


def build_placeorder_logistique_block() -> str:
    """Build the Markdown block the LLM will see."""
    heure = ""
    try:
        from core.timezone_helper import get_current_time_ci

        now_ci = get_current_time_ci()
        if now_ci is not None:
            heure = now_ci.strftime("%H:%M")
    except Exception:
        heure = ""

    heure_out = heure if heure else "∅"

    return (
        "\n\n"
        "# [PLACEORDER_LOGISTIQUE]\n"
        f"- HEURE_LOCALE_ACTUELLE : {heure_out} (ex: 10:45)\n"
        "- REGLE_OR : Avant 13h = Aujourd'hui | Après 13h = Demain\n"
    )
