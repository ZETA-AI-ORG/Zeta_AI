import logging
from typing import Dict

from core.centroid_router import CentroidRouter

_logger = logging.getLogger(__name__)
_router = None  # lazy-init

_GUIDANCE: Dict[int, str] = {
    9: (
        "Guidage livraison: si question d'information pure, donner frais par zone + délai du jour. "
        "Ne pas demander le produit. Format bref et clair."
    ),
    8: (
        "Guidage commande: demander acompte (2000F) + capture, puis zone de livraison et numéro. "
        "Toujours rester sur le processus 4 étapes."
    ),
    11: (
        "Guidage suivi: vérifier statut/avancement, informer simplement (en route/aujourd'hui/demain). "
        "Rester concis."
    ),
}

_DEFAULT_GUIDANCE = (
    "Guidage: rester focalisé sur le processus commande. "
    "Étapes: PRODUIT → PAIEMENT (2000F) → ZONE → NUMÉRO. "
    "Répondre en 2-3 phrases max."
)


def _get_router() -> CentroidRouter:
    global _router
    if _router is None:
        _router = CentroidRouter(use_cache=True)
    return _router


def build_intent_hypothesis(message: str) -> str:
    """
    Retourne un bloc HYDE-like basé sur l'intent détecté pour guider le LLM,
    sans retrieval ni FAQ. Utilise CentroidRouter top-k.
    """
    msg = (message or "").strip()
    if not msg:
        return ""
    try:
        router = _get_router()
        res = router.route(msg, top_k=3)
        best_id = int(res.get("intent_id") or 0)
        best_name = str(res.get("intent_name") or "?")
        conf = float(res.get("confidence") or 0.0)
        topk = res.get("top_k_intents") or []

        topk_str = ", ".join(
            f"{it.get('intent_name','?')}({it.get('confidence',0.0):.2f})" for it in topk[1:3]
        )
        guidance = _GUIDANCE.get(best_id, _DEFAULT_GUIDANCE)

        block = (
            "═══ INTENT HYPOTHÈSE\n"
            f"Intent: {best_name} (conf {conf:.2f})\n"
            f"Top2: {topk_str if topk_str else '—'}\n"
            f"{guidance}"
        )
        return block
    except Exception as e:
        _logger.warning(f"[INTENT_HYPOTHESIS] erreur: {e}")
        return ""
