from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple, Any

# Importer MeiliHelper sans dépendre du nom de package contenant un point (CHATBOT2.0)
import os
import importlib.util
from pathlib import Path

_MEILI_PATH = os.path.join(Path(__file__).resolve().parents[1], "database", "meili_client.py")
_spec = importlib.util.spec_from_file_location("_meili_client", _MEILI_PATH)
if _spec and _spec.loader:
    _meili_mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_meili_mod)  # type: ignore[attr-defined]
    MeiliHelper = getattr(_meili_mod, "MeiliHelper")
else:  # pragma: no cover
    raise ImportError(f"Impossible d'importer MeiliHelper depuis {_MEILI_PATH}")


# ---------------------- Intent schema ----------------------
@dataclass
class Intent:
    name: str
    attrs: Dict[str, Any]


_COLOR_ALIASES = {
    "rouge": ["rouge", "red"],
    "noir": ["noir", "black"],
    "bleu": ["bleu", "blue"],
    "gris": ["gris", "gray", "grey"],
    "blanc": ["blanc", "white"],
}

_PAYMENT_TERMS = ["wave", "orange money", "mtn", "moov", "visa", "mastercard", "cash"]


def _extract_color_fr(text: str) -> Optional[str]:
    t = text.lower()
    for canon, variants in _COLOR_ALIASES.items():
        for v in variants:
            if re.search(rf"\b{re.escape(v)}\b", t):
                return canon
    return None


def detect_intent(user_query: str) -> Intent:
    q = (user_query or "").strip().lower()

    # Livraison
    if re.search(r"\b(livraison|livrer|frais de livraison|delai|délais)\b", q):
        return Intent("delivery", {})

    # Support / Paiement
    if re.search(r"\b(paiement|payer|support|assistance|garantie|retour)\b", q):
        # Détecter un moyen de paiement si mentionné
        for m in _PAYMENT_TERMS:
            if re.search(rf"\b{re.escape(m)}\b", q):
                return Intent("support", {"method": m})
        return Intent("support", {})

    # Produits: prix, stock, couleur
    if re.search(r"\b(prix|coût|cout|tarif|stock|disponible|disponibilité|disponibilite|couleur)\b", q):
        color = _extract_color_fr(q)
        return Intent("products", {"color": color})

    # Fallback
    return Intent("fallback", {})


# ---------------------- Router ----------------------
class IntentRouter:
    def __init__(self, meili: Optional[MeiliHelper] = None):
        self.meili = meili or MeiliHelper()

    def route(
        self,
        company_id: str,
        user_query: str,
        *,
        fallback_pgvector: Callable[[str, str], Any],
    ) -> Tuple[str, Any]:
        """
        Route vers Meili (products/delivery/support) ou vers le fallback PGVector.
        Retourne (channel, results) où channel ∈ {products, delivery, support, pgvector}.
        """
        intent = detect_intent(user_query)

        if intent.name == "products":
            res = self.meili.search_products(company_id, user_query, color=intent.attrs.get("color"))
            return ("products", res)
        if intent.name == "delivery":
            res = self.meili.search_delivery(company_id, user_query)
            return ("delivery", res)
        if intent.name == "support":
            res = self.meili.search_support(company_id, user_query, method=intent.attrs.get("method"))
            return ("support", res)

        # Fallback vers PGVector
        res = fallback_pgvector(company_id, user_query)
        return ("pgvector", res)
