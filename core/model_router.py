from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ModelChoice:
    model: str
    reason: str


def choose_model(intent: Optional[str], complexity: Optional[int] = None) -> ModelChoice:
    upper_intent = (intent or "").strip().upper()

    if upper_intent in {
        "PROBLEME_RECLAMATION",
        "RECLAMATION",
        "SAV",
        "REMBOURSEMENT",
        "RETOUR_REMBOURSEMENT",
        "PROBLEME_LIVRAISON",
        "LIVRAISON_PROBLEME",
    }:
        return ModelChoice(model="openai/gpt-oss-120b", reason="sav_complexe")

    if upper_intent in {
        "COMMANDE",
        "SUIVI_COMMANDE",
        "MODIFICATION_COMMANDE",
        "ANNULATION_COMMANDE",
        "PAIEMENT",
        "ADRESSE_LIVRAISON",
    }:
        return ModelChoice(model="groq/compound", reason="commande_tool_use")

    if complexity is not None and int(complexity) >= 70:
        return ModelChoice(model="openai/gpt-oss-120b", reason="complexite_elevee")

    return ModelChoice(model="llama-3.3-70b-versatile", reason="general")
