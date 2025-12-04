 from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import json

try:  # Import local, pour ne pas casser si sentence-transformers non installé
    from sentence_transformers import SentenceTransformer, util
except Exception:  # pragma: no cover
    SentenceTransformer = None  # type: ignore
    util = None  # type: ignore


@dataclass
class BotliveRoutingResult:
    intent: str
    confidence: float
    mode: str
    missing_fields: List[str]
    state: Dict[str, Any]
    debug: Dict[str, Any]


_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_INTENTS_JSON_PATH = Path(__file__).resolve().parents[1] / "intents" / "ecommerce_intents.json"

_model: SentenceTransformer | None = None
_intent_prototypes: Dict[str, Any] | None = None


def _load_model_and_prototypes() -> Tuple[SentenceTransformer, Dict[str, Any]]:
    """Charge le modèle HF et les prototypes d'intents à partir du JSON.

    - Un prototype = moyenne des embeddings des exemples d'un intent.
    - Résultat mis en cache module-global pour performance.
    """

    global _model, _intent_prototypes

    if SentenceTransformer is None:
        raise RuntimeError(
            "sentence-transformers n'est pas installé. Installe: pip install sentence-transformers"
        )

    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)

    if _intent_prototypes is None:
        data = None
        used_source = "json"

        # 1) Essayer d'utiliser le corpus universel Python si disponible
        try:
            from core.universal_corpus import UNIVERSAL_ECOMMERCE_INTENT_CORPUS as UC  # type: ignore

            # Mapping index → intent canonique
            index_to_intent = {
                1: "SALUT",
                2: "INFO_GENERALE",
                3: "CLARIFICATION",
                4: "CATALOGUE",
                5: "RECHERCHE_PRODUIT",
                6: "PRIX_PROMO",
                7: "DISPONIBILITE",
                8: "ACHAT_COMMANDE",
                9: "LIVRAISON",
                10: "PAIEMENT",
                11: "SUIVI",
                12: "PROBLEME",
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
                # Nettoyer exemples
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

        # 2) Fallback JSON si pas de corpus universel
        if data is None:
            if not _INTENTS_JSON_PATH.exists():
                raise FileNotFoundError(f"Corpus intents introuvable: {_INTENTS_JSON_PATH}")

            with _INTENTS_JSON_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)

        prototypes: Dict[str, Any] = {}
        for item in data:
            intent_name = str(item.get("intent")).strip()
            examples = [e for e in item.get("examples", []) if isinstance(e, str) and e.strip()]
            if not intent_name or not examples:
                continue

            emb = _model.encode(examples, convert_to_tensor=True)
            proto = emb.mean(dim=0)
            prototypes[intent_name] = proto

        if not prototypes:
            raise RuntimeError("Aucun prototype d'intent généré depuis le corpus JSON")

        _intent_prototypes = prototypes

    return _model, _intent_prototypes


def _route_with_embeddings(message: str) -> Tuple[str, float]:
    """Retourne (intent, score) basé sur la similarité cosinus avec les 12 intents.

    Si aucun intent n'est suffisamment proche, la fonction renvoie
    ("CLARIFICATION", score) pour rester safe.
    """

    text = (message or "").strip()
    if not text:
        return "CLARIFICATION", 0.0

    model, prototypes = _load_model_and_prototypes()

    query_emb = model.encode(text, convert_to_tensor=True)

    best_intent = "CLARIFICATION"
    best_score = -1.0

    for intent, proto in prototypes.items():
        score = float(util.cos_sim(query_emb, proto).item())
        if score > best_score:
            best_score = score
            best_intent = intent

    # Seuil 0.5: en-dessous, on bascule vers CLARIFICATION
    if best_score < 0.5:
        return "CLARIFICATION", best_score

    return best_intent, best_score


async def route_botlive_intent(
    company_id: str,
    user_id: str,
    message: str,
    conversation_history: str,
    state_compact: Dict[str, Any],
) -> BotliveRoutingResult:
    """Router d'intention Botlive basé sur embeddings HuggingFace.

    - Utilise un corpus global JSON (12 intents) pour construire des prototypes.
    - Encodage du message → similarité cosinus → intent le plus proche.
    - Applique ensuite les règles Python (checklist) pour décider le MODE.
    """

    # 1) Routing d'intent via embeddings
    intent, score = _route_with_embeddings(message)

    confidence = float(max(0.0, min(1.0, score)))

    collected_count = int(state_compact.get("collected_count", 0))
    is_complete = bool(state_compact.get("is_complete", False))

    # 2) Décision MODE Jessica en fonction de l'intent + checklist
    # Intent labels attendus: SALUT, INFO_GENERALE, CLARIFICATION,
    # CATALOGUE, RECHERCHE_PRODUIT, PRIX_PROMO, DISPONIBILITE,
    # ACHAT_COMMANDE, LIVRAISON, PAIEMENT, SUIVI, PROBLEME

    upper_intent = intent.upper()

    if is_complete:
        mode = "RECEPTION_SAV"
    elif upper_intent == "ACHAT_COMMANDE":
        mode = "COMMANDE"
    elif upper_intent in {"SALUT", "INFO_GENERALE", "CATALOGUE", "RECHERCHE_PRODUIT", "PRIX_PROMO", "DISPONIBILITE", "LIVRAISON", "PAIEMENT"}:
        mode = "RECEPTION_SAV"
    elif upper_intent in {"SUIVI", "PROBLEME"}:
        mode = "RECEPTION_SAV"
    else:
        # CLARIFICATION ou tout autre cas flou
        mode = "GUIDEUR" if collected_count > 0 else "RECEPTION_SAV"

    # 3) Champs manquants basés sur l'état compact
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
        "conversation_history_sample": conversation_history[-300:],
        "intent_score": score,
    }

    return BotliveRoutingResult(
        intent=upper_intent,
        confidence=confidence,
        mode=mode,
        missing_fields=missing,
        state=state_compact,
        debug=debug,
    )
