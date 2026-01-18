from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import json

from core.greeting_analyzer import GreetingAnalyzer

try:
    from sentence_transformers import SentenceTransformer, util
except Exception:
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
_greeting_analyzer: GreetingAnalyzer | None = None
_word_families: Dict[str, Any] | None = None


def _load_model_and_prototypes() -> Tuple[SentenceTransformer, Dict[str, Any]]:
    """Charge le modèle HF et les prototypes d'intents à partir du JSON."""
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

        try:
            from core.universal_corpus import UNIVERSAL_ECOMMERCE_INTENT_CORPUS as UC

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


def _get_greeting_analyzer() -> GreetingAnalyzer:
    global _greeting_analyzer
    if _greeting_analyzer is None:
        _greeting_analyzer = GreetingAnalyzer()
    return _greeting_analyzer


def _load_word_families() -> Dict[str, Any]:
    """Charge les familles de mots depuis le JSON généré par extract_word_families.

    Si le fichier n'existe pas, on retourne une structure vide et on laisse
    les boosts lexicaux standards fonctionner seuls.
    """

    global _word_families

    if _word_families is None:
        families_path = (
            Path(__file__).resolve().parents[1]
            / "intents"
            / "keywords"
            / "word_families.json"
        )

        if not families_path.exists():
            # Pas de familles définies → pas de boosts additionnels
            _word_families = {"families_by_intent": {}}
            return _word_families

        with families_path.open("r", encoding="utf-8") as f:
            _word_families = json.load(f)

    return _word_families or {"families_by_intent": {}}


def _match_word_family(text: str, intent: str) -> float:
    """Calcule un score de correspondance avec les familles de mots d'un intent.

    Retourne un score entre 0.0 et 1.0.
    """

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

    # 🔴 ERREUR 1 - "Paiement à la livraison c'est possible"
    # Problème: confusion PAYMENT ↔ DELIVERY (maintenant routé LIVRAISON avec conf=1.00)
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
        # C'est VRAIMENT du paiement avec contexte livraison
        _apply("PAIEMENT", 1.50)  # Boost plus fort
        _apply("LIVRAISON", 0.80)  # Déboost pour que PAIEMENT gagne
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
    # Problème: routé vers PROBLEME au lieu de PAYMENT
    if "facture" in t or "reçu" in t or "recu" in t:
        _apply("PAIEMENT", 1.35)
        _apply("PROBLEME", 0.65)
        _apply("SUIVI", 0.85)

    # 🔴 ERREUR 2 - "La livraison prend combien de temps"
    # Problème: routé TRACKING au lieu de DELIVERY_INFO
    # C'est une question sur le DÉLAI de livraison (info), pas le suivi d'une commande existante
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
        _apply("SUIVI", 0.65)  # Déboost fort pour éviter confusion avec tracking
        _apply("PRIX_PROMO", 0.80)
    # Problème: tiré vers PRIX au lieu de DELIVERY_INFO
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
    # Problème: tiré vers INFO_GENERAL au lieu de DELIVERY_INFO
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
    # Problème: routé CLARIFICATION (conf=0.48) - besoin de boost plus fort
    modify_address_kw = [
        "modifier l'adresse", "modifier adresse",
        "changer l'adresse", "changer adresse",
        "modifier la zone", "changer la zone",
        "changer de zone", "modifier zone",
        "correction adresse", "corriger adresse",
        "nouvelle adresse", "autre adresse",
    ]
    if any(kw in t for kw in modify_address_kw):
        _apply("LIVRAISON", 1.50)  # Boost plus fort pour dépasser seuil 0.5
        _apply("ACHAT_COMMANDE", 0.75)
        _apply("CLARIFICATION", 0.60)

    # 🔴 ERREUR 4 - "Ça n'est pas arrivé"
    # Problème: routé SALUT au lieu de TRACKING
    # Phrases courtes négatives sans "commande" explicite
    delivery_problem_short = [
        "pas arrivé", "pas arrivée",
        "n'est pas arrivé", "n est pas arrivé",
        "ça n'est pas arrivé", "ca n est pas arrivé",
        "toujours rien", "rien reçu", "rien recu",
        "pas de nouvelle", "aucune nouvelle",
    ]
    if any(phrase in t for phrase in delivery_problem_short):
        _apply("SUIVI", 1.60)  # Boost très fort
        _apply("SALUT", 0.50)  # Déboost fort SALUT
        _apply("PROBLEME", 1.30)  # C'est aussi un problème
        _apply("ACHAT_COMMANDE", 0.60)
    # "Quand arrive ma commande" / "expédiée" / "pas arrivé"
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

    # Mots de suivi généraux
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
            _apply("RECHERCHE_PRODUIT", 1.25)
            _apply("PRIX_PROMO", 0.88)
        elif is_stock_quantity_question:
            _apply("DISPONIBILITE", 1.25)
            _apply("PRIX_PROMO", 0.85)
        else:
            _apply("PRIX_PROMO", 1.25)
            _apply("INFO_GENERALE", 0.92)
            _apply("PAIEMENT", 0.92)

    if has_product:
        _apply("RECHERCHE_PRODUIT", 1.15)
        _apply("CATALOGUE", 1.08)
        _apply("INFO_GENERALE", 0.90)

    if has_stock:
        _apply("DISPONIBILITE", 1.18)
        _apply("INFO_GENERALE", 0.90)

        if (
            "plus ce modèle" in t
            or "plus ce modele" in t
            or "n'avez plus ce modèle" in t
            or "n avez plus ce modele" in t
        ):
            _apply("DISPONIBILITE", 1.10)
            _apply("RECHERCHE_PRODUIT", 0.70)

    if has_pay:
        _apply("PAIEMENT", 1.18)
        _apply("INFO_GENERALE", 0.90)

    if has_ship:
        _apply("LIVRAISON", 1.20)
        _apply("INFO_GENERALE", 0.88)

    if has_order:
        _apply("ACHAT_COMMANDE", 1.28)
        _apply("INFO_GENERALE", 0.90)
        _apply("CATALOGUE", 0.92)
        _apply("RECHERCHE_PRODUIT", 0.92)

        if has_price:
            _apply("ACHAT_COMMANDE", 0.90)

    # Contact / joindre → INFO_GENERALE plutôt que SALUT
    contact_patterns = [
        "comment vous joindre",
        "comment je peux vous joindre",
        "comment vous contacter",
        "vous joindre comment",
        "contact",
    ]
    if any(p in t for p in contact_patterns):
        _apply("INFO_GENERALE", 1.40)
        _apply("SALUT", 0.70)

    return updated


def _apply_lexical_boosts_with_families(text: str, scores: Dict[str, float]) -> Dict[str, float]:
    """Boosts lexicaux standards + renfort via familles de mots Shadow.

    - On applique d'abord les boosts existants (_apply_lexical_boosts).
    - Puis, pour chaque intent, on regarde s'il y a des familles de mots
      associées dans word_families.json et on applique un léger boost
      proportionnel au score de famille.
    """

    # 1. Boosts actuels (inchangés)
    updated = _apply_lexical_boosts(text, scores)

    # 2. Boosts via familles de mots
    intent_mapping = {
        "SALUT": "SALUT",
        "INFO_GENERALE": "INFO_GENERALE",
        "CLARIFICATION": "CLARIFICATION",
        "CATALOGUE": "CATALOGUE",
        "RECHERCHE_PRODUIT": "RECHERCHE_PRODUIT",
        "PRIX_PROMO": "PRIX_PROMO",
        "DISPONIBILITE": "DISPONIBILITE",
        "ACHAT_COMMANDE": "ACHAT_COMMANDE",
        "LIVRAISON": "LIVRAISON",
        "PAIEMENT": "PAIEMENT",
        "SUIVI": "SUIVI",
        "PROBLEME": "PROBLEME",
    }

    for intent_code, base_score in list(updated.items()):
        family_name = intent_mapping.get(intent_code)
        if not family_name:
            continue

        family_score = _match_word_family(text, family_name)
        if family_score <= 0.2:
            continue

        # Exemple: score 0.2 → +6%, 0.5 → +15%, 1.0 → +30%
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
    # "Bonjour madame vous livrez à Abobo" → doit être DELIVERY pas GREETING
    if route_to == "SALUT":
        # Vérifier si la phrase contient une vraie question métier après politesse
        rest_text = (analysis.get("rest_text") or "").strip().lower()
        
        business_triggers = [
            "vous livrez", "livrez", "vous couvrez",
            "mobile money", "wave", "orange money",
            "vous acceptez", "acceptez",
            "combien", "prix", "tarif",
            "commander", "acheter",
        ]
        
        has_business_question = any(trigger in rest_text for trigger in business_triggers)
        
        # Si greeting + question métier, on analyse la question
        if has_business_question and len(rest_text) > 8:  # Seuil abaissé à 8 caractères
            route_to = "EMBED_REST"
            text = rest_text
        else:
            # Vraiment juste un salut
            confidence = float(analysis.get("confidence", 0.9))
            return "SALUT", confidence
    
    if route_to == "EMBED_REST":
        text = (analysis.get("rest_text") or raw).strip()
    else:  # EMBED_FULL
        text = raw

    model, prototypes = _load_model_and_prototypes()
    query_emb = model.encode(text, convert_to_tensor=True)

    scores: Dict[str, float] = {}
    for intent, proto in prototypes.items():
        scores[intent] = float(util.cos_sim(query_emb, proto).item())

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
        best_intent = "SUIVI"
        # S'assurer que la confiance est suffisante pour ne pas tomber en CLARIFICATION
        best_score = max(best_score, 0.75)

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
    """Router d'intention Botlive basé sur embeddings HuggingFace."""

    intent, score = _route_with_embeddings(message)
    confidence = float(max(0.0, min(1.0, score)))

    collected_count = int(state_compact.get("collected_count", 0))
    is_complete = bool(state_compact.get("is_complete", False))

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