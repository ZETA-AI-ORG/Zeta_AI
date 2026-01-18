from __future__ import annotations

import os
import logging
from typing import Any, Dict

from core.setfit_intent_router import route_botlive_intent as _route_setfit, BotliveRoutingResult
from core.legacy.botlive_intent_router_embeddings import (
    route_botlive_intent as _route_embeddings,
    get_delivery_delay_similarity,
)

logger = logging.getLogger(__name__)


def _should_use_embeddings_router() -> bool:
    force_embeddings = os.getenv("BOTLIVE_ROUTER_EMBEDDINGS_ENABLED", "false").strip().lower() in {"1", "true", "yes", "y", "on"}
    return force_embeddings


async def route_botlive_intent(
    company_id: str,
    user_id: str,
    message: str,
    conversation_history: str,
    state_compact: Dict[str, Any],
    hyde_pre_enabled: bool | None = None,
) -> BotliveRoutingResult:
    """
    Routeur d'intention hybride :
    - Utilise SetFit par défaut (core/setfit_intent_router.py)
    - Fallback sur embeddings legacy si modèle SetFit absent/erreur ou si variable d'env BOTLIVE_ROUTER_EMBEDDINGS_ENABLED=true
    """
    if _should_use_embeddings_router():
        logger.info("[ROUTER] Embeddings legacy forcé par variable d'environnement.")
        res = await _route_embeddings(company_id, user_id, message, conversation_history, state_compact, hyde_pre_enabled)
        try:
            if isinstance(getattr(res, "debug", None), dict):
                res.debug.setdefault("router", "embeddings")
                res.debug["router_source"] = "embeddings_forced_env"
        except Exception:
            pass
        return res
    try:
        res = await _route_setfit(company_id, user_id, message, conversation_history, state_compact, hyde_pre_enabled)
        try:
            if isinstance(getattr(res, "debug", None), dict):
                res.debug.setdefault("router", "setfit")
                res.debug["router_source"] = "setfit"
        except Exception:
            pass
        return res
    except Exception as e:
        logger.error(f"[ROUTER] Erreur SetFit (pas de fallback embeddings): {e}")
        try:
            return BotliveRoutingResult(
                intent="REASSURANCE",
                confidence=0.5,
                intent_group="REASSURANCE",
                mode="REASSURANCE",
                missing_fields=[],
                state=state_compact or {},
                debug={
                    "router": "setfit",
                    "router_source": "setfit_error_fallback",
                    "router_error": str(e),
                },
            )
        except Exception:
            # Dernier recours: re-raise si la dataclass n'est pas instanciable pour une raison quelconque.
            raise


# Pour compatibilité :
# from core.botlive_intent_router import get_delivery_delay_similarity
# (utilisé dans botlive_rag_hybrid.py)


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
class _DeprecatedBotliveRoutingResult:
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
            try:
                from core.universal_corpus import UNIVERSAL_ECOMMERCE_INTENT_CORPUS_V4 as UC
            except Exception:
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

    # ========================================================================
    # 🎯 CORRECTIONS CIBLÉES - TOP 10 ERREURS
    # ========================================================================

    # Coordonnées / téléphone (souvent remplissage du champ tel)
    contact_coord_kw = [
        "mon numéro", "mon numero", "mon num", "numéro", "numero",
        "téléphone", "telephone", "tel", "whatsapp", "sms",
        "appelez", "appelle", "contactez", "joindre",
    ]
    has_digits = any(ch.isdigit() for ch in t)
    if (any(kw in t for kw in contact_coord_kw) or (has_digits and "tel" in t)) and "CONTACT_COORDONNEES" in updated:
        _apply("CONTACT_COORDONNEES", 1.60)
        _apply("INFO_GENERALE", 0.85)
        _apply("SALUT", 0.70)

    stop = {
        "bonjour", "bonsoir", "salut", "hey", "coucou", "bjr", "slt",
        "merci", "svp", "stp", "pardon",
        "je", "tu", "il", "elle", "on", "nous", "vous", "ils", "elles",
        "mon", "ma", "mes", "ton", "ta", "tes", "son", "sa", "ses",
        "de", "du", "des", "la", "le", "les", "un", "une", "et", "ou", "a", "à",
        "pour", "avec", "sur", "dans", "chez", "par", "en",
        "veux", "voudrais", "prends", "prendre", "acheter", "commande", "commander",
        "chercher", "cherche", "besoin",
        "quoi", "comment", "quand", "où", "ou", "combien", "quel", "quelle", "quels", "quelles",
        "prix", "tarif", "promo", "promotion", "stock", "dispo", "disponible",
        "livraison", "livrer", "vous livrez", "frais de livraison", "livr ", "livr",
    }
    tokens = [w for w in re.findall(r"[a-zA-ZÀ-ÖØ-öø-ÿ]+", t) if len(w) >= 3]
    product_terms = [w for w in tokens if w not in stop]
    uniq_terms = list(dict.fromkeys(product_terms))
    ambiguity_markers = [" je sais pas", " j sais pas", " jsp", " je ne sais pas", " je sais plus", " je ne sais plus"]
    has_ambig = (" ou " in t) or any(m in t for m in ambiguity_markers)
    if has_ambig and len(uniq_terms) >= 2:
        _apply("PRODUIT_GLOBAL", 1.20)
        _apply("SALUT", 0.75)

    # 🔴 ERREUR 1 - "Paiement à la livraison c'est possible"
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

    # Moyens de paiement mobiles (Côte d'Ivoire)
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

    # 🔴 ERREUR 2 - "Je veux une facture"
    if "facture" in t or "reçu" in t or "recu" in t:
        _apply("PAIEMENT", 1.35)
        _apply("PROBLEME", 0.65)
        _apply("COMMANDE_EXISTANTE", 0.85)

    # 🔴 ERREUR 2 - "La livraison prend combien de temps"
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
        _apply("COMMANDE_EXISTANTE", 0.65)
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

    # Quartiers d'Abidjan (contexte livraison)
    abidjan_zones = [
        "cocody", "yopougon", "abobo", "marcory", "koumassi",
        "treichville", "adjamé", "adjame", "plateau", "attecoube",
        "port-bouet", "portbouet",
    ]
    if any(zone in t for zone in abidjan_zones):
        if "livr" in t or "zone" in t or "vous couvrez" in t:
            _apply("LIVRAISON", 1.30)
            _apply("INFO_GENERALE", 0.80)

    # 🔴 ERREUR 4 - "Quelles zones vous couvrez"
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

    # 🔴 ERREUR 3 - "Modifier l'adresse svp"
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

    # 🔴 ERREUR 4 - "Ça n'est pas arrivé"
    delivery_problem_short = [
        "pas arrivé", "pas arrivée",
        "n'est pas arrivé", "n est pas arrivé",
        "ça n'est pas arrivé", "ca n est pas arrivé",
        "toujours rien", "rien reçu", "rien recu",
        "pas de nouvelle", "aucune nouvelle",
    ]
    if any(phrase in t for phrase in delivery_problem_short):
        _apply("COMMANDE_EXISTANTE", 1.60)
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
        _apply("COMMANDE_EXISTANTE", 1.50)
        _apply("ACHAT_COMMANDE", 0.70)
        _apply("LIVRAISON", 0.80)

    # Mots de suivi généraux
    tracking_general_kw = [
        "où est", "ou est",
        "suivi", "tracking", "statut",
        "numéro de suivi", "numero de suivi",
        "référence commande", "reference commande",
        "n° commande", "no commande", "num commande",
    ]
    if any(kw in t for kw in tracking_general_kw):
        _apply("COMMANDE_EXISTANTE", 1.35)
        _apply("ACHAT_COMMANDE", 0.75)

    # ========================================================================
    # 🟢 BOOSTS ORIGINAUX (maintenus)
    # ========================================================================

    product_kw = [
        "caractér", "caracter", "taille", "dimension", "format",
        "couleur", "modèle", "modele", "modèles", "gramme", "grammes",
        "poids", "marque", "référence", "reference", "fabriqué", "fabrique",
        "composition", "garantie",
    ]
    has_product = any(k in t for k in product_kw)

    stock_kw = [
        "stock", "dispo", "plus en stock", "rupture",
        "il en reste", "reste combien", "combien de pièces", "combien de pieces",
        "plus ce modèle", "plus ce modele", "n'avez plus ce modèle", "n avez plus ce modele",
        "reste des paquets", "reste des paquet",
    ]
    has_stock = any(k in t for k in stock_kw)

    pay_kw = [
        "payer", "paye", "payé",
        "paiement", "mode de paiement", "moyen de paiement",
        "espèces", "especes", "cash",
    ]
    has_pay = any(k in t for k in pay_kw)

    price_terms_simple = ["prix", "combien", "coût", "cout", "tarif"]
    has_price_term = any(p in t for p in price_terms_simple)
    if has_price_term:
        strong_method_kw = [
            "mobile money", "wave", "orange money", "mtn", "moov",
            "espèces", "especes", "cash", "facture",
        ]
        has_pay = any(k in t for k in strong_method_kw)

    ship_kw = [
        "livraison", "livrer", "vous livrez", "frais de livraison",
        "combien pour livrer", "zone de livraison",
        "temps de livraison", "délai de livraison",
    ]
    has_ship = any(k in t for k in ship_kw)

    order_kw = [
        "je veux commander", "je commande", "je prends", "je prend",
        "je veux acheter", "mets-moi", "met moi", "garde-moi", "garde moi",
        "je réserve", "je reserve", "je souhaite commander", "commande pour",
        "je voudrais acheter", "j'achète", "j achete",
        "envoie-moi", "envoie moi", "envoyez-moi", "envoyez moi",
        "passer commande", "passer ma commande", "passer la commande",
        "comment passer commande", "comment passer ma commande", "comment passer la commande",
    ]
    has_order = any(k in t for k in order_kw)

    price_kw = [
        "prix", "combien", "coût", "cout", "tarif",
        "promo", "promotion", "réduction", "reduction",
        "remise", "remises", "soldes", "solde",
    ]
    has_price = any(k in t for k in price_kw)

    is_stock_quantity_question = any(
        pat in t
        for pat in [
            "il en reste", "reste combien", "combien de pièces", "combien de pieces",
            "combien de paquets", "combien de paquet",
        ]
    )
    is_weight_question = (
        ("gramme" in t or "grammes" in t or "kg" in t or "kilo" in t)
        and "combien" in t
    )

    if has_price:
        if is_weight_question:
            _apply("PRODUIT_GLOBAL", 1.25)
            _apply("PRIX_PROMO", 0.88)
        elif is_stock_quantity_question:
            _apply("PRODUIT_GLOBAL", 1.25)
            _apply("PRIX_PROMO", 0.85)
        else:
            _apply("PRIX_PROMO", 1.25)
            _apply("INFO_GENERALE", 0.92)
            _apply("PAIEMENT", 0.92)

    if has_product:
        _apply("PRODUIT_GLOBAL", 1.15)
        _apply("INFO_GENERALE", 0.90)

    if has_stock:
        _apply("PRODUIT_GLOBAL", 1.18)
        _apply("INFO_GENERALE", 0.90)

        if (
            "plus ce modèle" in t
            or "plus ce modele" in t
            or "n'avez plus ce modèle" in t
            or "n avez plus ce modele" in t
        ):
            _apply("PRODUIT_GLOBAL", 1.10)

    if has_pay:
        _apply("PAIEMENT", 1.18)
        _apply("INFO_GENERALE", 0.90)

    if has_ship:
        _apply("LIVRAISON", 1.20)
        _apply("INFO_GENERALE", 0.88)

    if has_order:
        _apply("ACHAT_COMMANDE", 1.28)
        _apply("INFO_GENERALE", 0.90)
        _apply("PRODUIT_GLOBAL", 0.92)

        if has_price:
            _apply("ACHAT_COMMANDE", 0.90)

    contact_patterns = [
        "comment vous contacter",
        "vous joindre comment",
        "contact",
    ]
    if any(p in t for p in contact_patterns):
        if "CONTACT_COORDONNEES" in updated:
            _apply("CONTACT_COORDONNEES", 1.30)
            _apply("INFO_GENERALE", 0.90)
        else:
            _apply("INFO_GENERALE", 1.40)
        _apply("SALUT", 0.70)

    return updated


def _apply_lexical_boosts_with_families(text: str, scores: Dict[str, float]) -> Dict[str, float]:
    """Boosts lexicaux standards + renfort via familles de mots Shadow."""

    # 1. Boosts actuels (inchangés)
    updated = _apply_lexical_boosts(text, scores)

    # 2. Boosts via familles de mots
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
    """🔧 PATCH - Routing avec GreetingAnalyzer amélioré."""
    raw = (message or "").strip()
    if not raw:
        return "CLARIFICATION", 0.0

    analyzer = _get_greeting_analyzer()
    analysis = analyzer.analyze(raw)
    route_to = analysis.get("route_to", "EMBED_FULL")

    # 🔴 ERREUR 9 & 10 - Greetings longs avec question métier
    if route_to == "SALUT":
        rest_text = (analysis.get("rest_text") or "").strip().lower()
        
        business_triggers = [
            "vous livrez", "livrez", "vous couvrez",
            "mobile money", "wave", "orange money",
            "vous acceptez", "acceptez",
            "combien", "prix", "tarif",
            "commander", "acheter",
            "numéro", "numero", "téléphone", "telephone", "tel", "whatsapp",
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
    else:  # EMBED_FULL
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

    # Nudge PRIX_PROMO sur textes courts
    t = text.lower()
    price_triggers = ["prix", "combien", "tarif", "coût", "cout", "promo", "réduc", "reduc", "soldes"]
    if any(w in t for w in price_triggers) and "PRIX_PROMO" in scores:
        words = text.split()
        ship_tokens = ["livraison", "livrer", "vous livrez", "frais de livraison", "livr ", "livr"]
        has_ship = any(st in t for st in ship_tokens)

        if len(words) <= 6 and not has_ship:
            current_best_intent, current_best_score = max(scores.items(), key=lambda x: x[1])
            if current_best_intent != "PRIX_PROMO":
                bumped = max(scores["PRIX_PROMO"] * 1.08, current_best_score + 1e-4)
                scores["PRIX_PROMO"] = min(bumped, 1.0)
        else:
            scores["PRIX_PROMO"] = min(scores["PRIX_PROMO"] * 1.08, 1.0)

    # 🔧 Application des boosts lexicaux patchés + familles de mots Shadow
    scores = _apply_lexical_boosts_with_families(text, scores)

    best_intent = max(scores.items(), key=lambda x: x[1])[0]
    best_score = scores[best_intent]

    # Renforcer le routage des demandes de MODIFICATION / ANNULATION de commande vers le SAV (segment D)
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
    return "GUIDEUR" if collected_count > 0 else "RECEPTION_SAV"


async def _route_botlive_intent_legacy(
    company_id: str,
    user_id: str,
    message: str,
    conversation_history: str,
    state_compact: Dict[str, Any],
    hyde_pre_enabled: bool | None = None,
) -> _DeprecatedBotliveRoutingResult:
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

    return _DeprecatedBotliveRoutingResult(
        intent=upper_intent,
        confidence=confidence,
        mode=mode,
        missing_fields=missing,
        state=state_compact,
        debug=debug,
    )