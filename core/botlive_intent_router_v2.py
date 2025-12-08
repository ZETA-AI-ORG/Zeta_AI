from __future__ import annotations

import json
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

from core.greeting_analyzer import GreetingAnalyzer

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - dépendance optionnelle
    SentenceTransformer = None  # type: ignore


@dataclass
class BotliveRoutingResult:
    intent: str
    confidence: float
    mode: str
    missing_fields: List[str]
    state: Dict[str, Any]
    debug: Dict[str, Any]


# ============================================================================
# CONFIGURATION
# ============================================================================

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_MODELS_DIR = Path(__file__).resolve().parents[1] / "models"


def _find_latest_classifier() -> Tuple[Path | None, Path | None]:
    """Trouve la dernière version du classifieur dans models/.

    On cherche des fichiers de la forme:
        - intent_classifier_vX.pkl
        - intent_classifier_config_vX.json

    et on prend le plus récent (date de modification du .pkl).
    """

    if not _MODELS_DIR.exists():
        return None, None

    versions: List[Tuple[Path, Path]] = []
    for pkl_file in _MODELS_DIR.glob("intent_classifier_v*.pkl"):
        version_str = pkl_file.stem.replace("intent_classifier_", "")
        config_file = _MODELS_DIR / f"intent_classifier_config_{version_str}.json"
        if config_file.exists():
            versions.append((pkl_file, config_file))

    if not versions:
        return None, None

    versions.sort(key=lambda x: x[0].stat().st_mtime)
    return versions[-1]


_CLASSIFIER_PATH, _CONFIG_PATH = _find_latest_classifier()

_encoder: SentenceTransformer | None = None
_classifier: Any | None = None
_classifier_config: Dict[str, Any] | None = None
_greeting_analyzer: GreetingAnalyzer | None = None


# ============================================================================
# CHARGEMENT EN PILE UNIQUE
# ============================================================================


def _load_encoder_and_classifier() -> Tuple[SentenceTransformer, Any, Dict[str, Any]]:
    """Charge l'encodeur HF et le classifieur ML.

    - L'encodeur est partagé avec le router V1 (même modèle MiniLM).
    - Le classifieur est un LogisticRegression scikit-learn entraîné via
      scripts/train_intent_classifier.py.
    """

    global _encoder, _classifier, _classifier_config

    if SentenceTransformer is None:
        raise RuntimeError(
            "sentence-transformers n'est pas installé. Installe: pip install sentence-transformers"
        )

    # 1) Encodeur
    if _encoder is None:
        _encoder = SentenceTransformer(_MODEL_NAME)

    # 2) Classifieur
    if _classifier is None:
        if _CLASSIFIER_PATH is None or not _CLASSIFIER_PATH.exists():
            raise FileNotFoundError(
                f"❌ Classifieur introuvable dans {_MODELS_DIR}.\n"
                f"   Exécute d'abord: python scripts/train_intent_classifier.py"
            )

        with _CLASSIFIER_PATH.open("rb") as f:
            _classifier = pickle.load(f)

    # 3) Config
    if _classifier_config is None:
        if _CONFIG_PATH is None or not _CONFIG_PATH.exists():
            raise FileNotFoundError(f"Config introuvable: {_CONFIG_PATH}")

        with _CONFIG_PATH.open("r", encoding="utf-8") as f:
            _classifier_config = json.load(f)

    return _encoder, _classifier, _classifier_config


def _get_greeting_analyzer() -> GreetingAnalyzer:
    global _greeting_analyzer
    if _greeting_analyzer is None:
        _greeting_analyzer = GreetingAnalyzer()
    return _greeting_analyzer


# ============================================================================
# BOOSTS LEXICAUX (ADAPTÉS AUX PROBABILITÉS)
# ============================================================================


def _apply_lexical_boosts(text: str, proba_dict: Dict[str, float]) -> Dict[str, float]:
    """Applique les boosts lexicaux sur les probabilités du classifieur.

    - Entrée: proba_dict = {intent: proba}, somme ≈ 1.0
    - On applique des facteurs multiplicatifs par intent.
    - Puis on re-normalise pour garder une distribution de probas.
    """

    t = (text or "").lower()
    if not t.strip():
        return proba_dict

    updated = proba_dict.copy()

    def _apply(intent: str, factor: float) -> None:
        if intent not in updated:
            return
        updated[intent] *= factor

    # --- PAIEMENT / LIVRAISON / INFO_GENERALE ---
    payment_delivery_phrases = [
        "paiement à la livraison",
        "paiement livraison",
        "payer à la livraison",
        "payer livraison",
        "contre remboursement",
        "paiement à réception",
        "paiement réception",
    ]
    if any(phrase in t for phrase in payment_delivery_phrases):
        _apply("PAIEMENT", 1.50)
        _apply("LIVRAISON", 0.80)
        _apply("INFO_GENERALE", 0.70)

    mobile_payment_kw = [
        "mobile money", "mobilemoney", "mobile-money",
        "wave", "orange money", "orangemoney", "orange-money",
        "mtn money", "mtnmoney", "mtn-money",
        "moov money", "moovmoney", "moov-money",
        "flooz",
    ]
    if any(kw in t for kw in mobile_payment_kw):
        _apply("PAIEMENT", 1.40)
        _apply("INFO_GENERALE", 0.80)
        _apply("LIVRAISON", 0.85)

    if "facture" in t or "reçu" in t or "recu" in t:
        _apply("PAIEMENT", 1.35)
        _apply("PROBLEME", 0.65)
        _apply("SUIVI", 0.85)

    # --- TEMPS / TARIF DE LIVRAISON ---
    delivery_time_questions = [
        "livraison prend combien",
        "combien de temps livraison",
        "délai de livraison",
        "délai livraison",
        "temps de livraison",
        "livraison en combien",
        "vous livrez en combien",
    ]
    if any(pattern in t for pattern in delivery_time_questions):
        _apply("LIVRAISON", 1.50)
        _apply("SUIVI", 0.65)
        _apply("PRIX_PROMO", 0.80)

    delivery_price_patterns = [
        "combien pour livrer",
        "combien livraison",
        "frais de livraison",
        "frais livraison",
        "prix de livraison",
        "prix livraison",
        "coût de livraison",
        "cout de livraison",
        "tarif livraison",
    ]
    if any(pattern in t for pattern in delivery_price_patterns):
        _apply("LIVRAISON", 1.40)
        _apply("PRIX_PROMO", 0.75)

    # --- ZONES D'ABIDJAN ---
    abidjan_zones = [
        "cocody", "yopougon", "abobo", "marcory", "koumassi",
        "treichville", "adjamé", "adjame", "plateau", "attecoube",
        "port-bouet", "portbouet",
    ]
    if any(zone in t for zone in abidjan_zones):
        if "livr" in t or "zone" in t or "vous couvrez" in t:
            _apply("LIVRAISON", 1.30)
            _apply("INFO_GENERALE", 0.80)

    delivery_coverage_kw = [
        "quelles zones",
        "quelle zone",
        "zones de livraison",
        "zone de livraison",
        "vous couvrez",
        "couvrez quelles zones",
        "livrez où", "livrez ou",
        "où livrez", "ou livrez",
        "vous livrez où", "vous livrez ou",
        "secteurs de livraison",
        "desservez", "desservir",
        "zones desservies",
    ]
    if any(kw in t for kw in delivery_coverage_kw):
        _apply("LIVRAISON", 1.45)
        _apply("INFO_GENERALE", 0.70)

    # --- MODIFICATION D'ADRESSE ---
    modify_address_kw = [
        "modifier l'adresse", "modifier adresse",
        "changer l'adresse", "changer adresse",
        "modifier la zone", "changer la zone",
        "changer de zone", "modifier zone",
        "correction adresse", "corriger adresse",
        "nouvelle adresse", "autre adresse",
    ]
    if any(kw in t for kw in modify_address_kw):
        _apply("LIVRAISON", 1.50)
        _apply("ACHAT_COMMANDE", 0.75)
        _apply("CLARIFICATION", 0.60)

    # --- PROBLÈME DE LIVRAISON / SUIVI ---
    delivery_problem_short = [
        "pas arrivé", "pas arrivée",
        "n'est pas arrivé", "n est pas arrivé",
        "ça n'est pas arrivé", "ca n est pas arrivé",
        "toujours rien", "rien reçu", "rien recu",
        "pas de nouvelle", "aucune nouvelle",
    ]
    if any(phrase in t for phrase in delivery_problem_short):
        _apply("SUIVI", 1.60)
        _apply("SALUT", 0.50)
        _apply("PROBLEME", 1.30)
        _apply("ACHAT_COMMANDE", 0.60)

    tracking_time_kw = [
        "quand arrive", "quand arrivera",
        "quand je reçois", "quand je recois",
        "combien de temps", "délai",
        "dans combien de jours",
    ]
    tracking_status_kw = [
        "expédiée", "expediee", "expédié", "expedie",
        "envoyée", "envoyee", "envoyé", "envoye",
        "en cours", "en route", "en chemin",
        "pas arrivé", "pas arrivee", "pas encore arrivé",
        "toujours pas", "pas encore reçu", "pas encore recu",
        "retard", "en retard",
    ]
    has_commande = "commande" in t or "colis" in t or "livraison" in t

    if has_commande and any(kw in t for kw in tracking_time_kw + tracking_status_kw):
        _apply("SUIVI", 1.50)
        _apply("ACHAT_COMMANDE", 0.70)
        _apply("LIVRAISON", 0.80)

    tracking_general_kw = [
        "où est", "ou est",
        "suivi", "tracking", "statut",
        "numéro de suivi", "numero de suivi",
        "référence commande", "reference commande",
        "n° commande", "no commande", "num commande",
    ]
    if any(kw in t for kw in tracking_general_kw):
        _apply("SUIVI", 1.35)
        _apply("ACHAT_COMMANDE", 0.75)

    # --- INFO PRODUIT / STOCK / COMMANDE / PRIX ---
    product_kw = [
        "caractér", "caracter", "taille", "dimension", "format",
        "couleur", "modèle", "modele", "modèles", "gramme", "grammes",
        "poids", "marque", "référence", "reference", "fabriqué", "fabrique",
        "composition", "garantie",
    ]
    if any(k in t for k in product_kw):
        _apply("RECHERCHE_PRODUIT", 1.15)
        _apply("CATALOGUE", 1.08)
        _apply("INFO_GENERALE", 0.90)

    stock_kw = [
        "stock", "dispo", "plus en stock", "rupture",
        "il en reste", "reste combien", "combien de pièces", "combien de pieces",
        "plus ce modèle", "plus ce modele", "n'avez plus ce modèle", "n avez plus ce modele",
        "reste des paquets", "reste des paquet",
    ]
    if any(k in t for k in stock_kw):
        _apply("DISPONIBILITE", 1.18)
        _apply("INFO_GENERALE", 0.90)

        if any(p in t for p in ["plus ce modèle", "plus ce modele", "n'avez plus", "n avez plus"]):
            _apply("DISPONIBILITE", 1.10)
            _apply("RECHERCHE_PRODUIT", 0.70)

        if ("couleur" in t or "taille" in t) and "combien" not in t:
            _apply("RECHERCHE_PRODUIT", 1.10)
            _apply("DISPONIBILITE", 0.85)

    pay_kw = [
        "payer", "paye", "payé", "paiement", "mode de paiement",
        "moyen de paiement", "espèces", "especes", "cash",
    ]
    price_terms = ["prix", "combien", "coût", "cout", "tarif"]
    has_price_term = any(p in t for p in price_terms)

    if has_price_term:
        strong_method_kw = [
            "mobile money", "wave", "orange money", "mtn", "moov",
            "espèces", "especes", "cash", "facture",
        ]
        has_pay = any(k in t for k in strong_method_kw)
    else:
        has_pay = any(k in t for k in pay_kw)

    if has_pay:
        _apply("PAIEMENT", 1.18)
        _apply("INFO_GENERALE", 0.90)

    ship_kw = [
        "livraison", "livrer", "vous livrez", "frais de livraison",
        "combien pour livrer", "zone de livraison", "temps de livraison",
        "délai de livraison",
    ]
    if any(k in t for k in ship_kw):
        _apply("LIVRAISON", 1.20)
        _apply("INFO_GENERALE", 0.88)

    order_kw = [
        "je veux commander", "je commande", "je prends", "je prend",
        "je veux acheter", "mets-moi", "met moi", "garde-moi", "garde moi",
        "je réserve", "je reserve", "je souhaite commander", "commande pour",
        "je voudrais acheter", "j'achète", "j achete",
        "envoie-moi", "envoie moi", "envoyez-moi", "envoyez moi",
        "passer commande", "passer ma commande", "passer la commande",
        "comment passer commande",
    ]
    if any(k in t for k in order_kw):
        _apply("ACHAT_COMMANDE", 1.28)
        _apply("INFO_GENERALE", 0.90)
        _apply("CATALOGUE", 0.92)
        _apply("RECHERCHE_PRODUIT", 0.92)

        if has_price_term:
            _apply("ACHAT_COMMANDE", 0.90)

    price_kw = [
        "prix", "combien", "coût", "cout", "tarif",
        "promo", "promotion", "réduction", "reduction",
        "remise", "remises", "soldes", "solde",
    ]
    is_stock_question = any(
        p in t
        for p in [
            "il en reste", "reste combien", "combien de pièces",
            "combien de pieces", "combien de paquets",
        ]
    )
    is_weight_question = (
        ("gramme" in t or "grammes" in t or "kg" in t or "kilo" in t)
        and "combien" in t
    )

    if any(k in t for k in price_kw):
        if is_weight_question:
            _apply("RECHERCHE_PRODUIT", 1.25)
            _apply("PRIX_PROMO", 0.88)
        elif is_stock_question:
            _apply("DISPONIBILITE", 1.25)
            _apply("PRIX_PROMO", 0.85)
        else:
            _apply("PRIX_PROMO", 1.25)
            _apply("INFO_GENERALE", 0.92)
            _apply("PAIEMENT", 0.92)

    # Re-normalisation pour garder somme = 1.0
    total = float(sum(updated.values())) or 0.0
    if total > 0.0:
        for k in updated:
            updated[k] = float(updated[k]) / total

    return updated


# ============================================================================
# ROUTING V2 AVEC CLASSIFIEUR ML
# ============================================================================


def _route_with_classifier(message: str) -> Tuple[str, float]:
    """Route le message avec le classifieur ML + GreetingAnalyzer + boosts.

    - Utilise GreetingAnalyzer pour séparer politesse et question métier.
    - Encode la partie pertinente avec MiniLM.
    - Applique LogisticRegression pour obtenir P(intent | message).
    - Applique les boosts lexicaux sur les probas puis renormalise.
    - Si la meilleure proba est trop basse, renvoie CLARIFICATION.
    """

    raw = (message or "").strip()
    if not raw:
        return "CLARIFICATION", 0.0

    analyzer = _get_greeting_analyzer()
    analysis = analyzer.analyze(raw)
    route_to = analysis.get("route_to", "EMBED_FULL")

    if route_to == "SALUT":
        rest_text = (analysis.get("rest_text") or "").strip().lower()

        business_triggers = [
            "vous livrez", "livrez", "vous couvrez",
            "mobile money", "wave", "orange money",
            "vous acceptez", "acceptez",
            "combien", "prix", "tarif",
            "commander", "acheter",
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

    encoder, clf, config = _load_encoder_and_classifier()

    embedding = encoder.encode([text], convert_to_tensor=False)
    proba = clf.predict_proba(embedding)[0]
    classes = clf.classes_

    proba_dict: Dict[str, float] = {intent: float(p) for intent, p in zip(classes, proba)}

    # Nudge PRIX_PROMO sur messages courts type "C'est combien" sans livraison
    t_lower = text.lower()
    price_triggers = [
        "prix", "combien", "tarif", "coût", "cout",
        "promo", "réduc", "reduc", "soldes",
    ]
    if any(w in t_lower for w in price_triggers) and "PRIX_PROMO" in proba_dict:
        words = text.split()
        ship_tokens = ["livraison", "livrer", "frais de livraison", "livr "]
        has_ship = any(st in t_lower for st in ship_tokens)

        if len(words) <= 6 and not has_ship:
            current_best = max(proba_dict.items(), key=lambda x: x[1])
            if current_best[0] != "PRIX_PROMO":
                boost_val = max(
                    proba_dict["PRIX_PROMO"] * 1.08,
                    current_best[1] + 0.01,
                )
                proba_dict["PRIX_PROMO"] = boost_val
                total = float(sum(proba_dict.values())) or 0.0
                if total > 0.0:
                    for k in proba_dict:
                        proba_dict[k] = float(proba_dict[k]) / total

    proba_dict = _apply_lexical_boosts(text, proba_dict)

    best_intent, best_proba = max(proba_dict.items(), key=lambda x: x[1])
    best_proba_f = float(best_proba)

    # Seuil de confiance: en-dessous → CLARIFICATION
    if best_proba_f < 0.35:
        return "CLARIFICATION", best_proba_f

    return best_intent, best_proba_f


# ============================================================================
# INTERFACE PUBLIQUE COMPATIBLE BACKEND
# ============================================================================


async def route_botlive_intent(
    company_id: str,
    user_id: str,
    message: str,
    conversation_history: str,
    state_compact: Dict[str, Any],
) -> BotliveRoutingResult:
    """Router d'intention Botlive V2 - Classifieur ML supervisé.

    - Même interface que V1 (même dataclass BotliveRoutingResult).
    - Peut être branché en A/B test ou en remplacement du router V1.
    """

    intent, confidence = _route_with_classifier(message)
    confidence = float(max(0.0, min(1.0, confidence)))

    collected_count = int(state_compact.get("collected_count", 0))
    is_complete = bool(state_compact.get("is_complete", False))

    upper_intent = intent.upper()

    # Décision MODE Jessica (copiée de V1)
    if is_complete:
        mode = "RECEPTION_SAV"
    elif upper_intent == "ACHAT_COMMANDE":
        mode = "COMMANDE"
    elif upper_intent in {
        "SALUT",
        "INFO_GENERALE",
        "CATALOGUE",
        "RECHERCHE_PRODUIT",
        "PRIX_PROMO",
        "DISPONIBILITE",
        "LIVRAISON",
        "PAIEMENT",
    }:
        mode = "RECEPTION_SAV"
    elif upper_intent in {"SUIVI", "PROBLEME"}:
        mode = "RECEPTION_SAV"
    else:
        mode = "GUIDEUR" if collected_count > 0 else "RECEPTION_SAV"

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
        "intent_score": confidence,
        "router_version": "v2_ml_classifier",
    }

    return BotliveRoutingResult(
        intent=upper_intent,
        confidence=confidence,
        mode=mode,
        missing_fields=missing,
        state=state_compact,
        debug=debug,
    )
