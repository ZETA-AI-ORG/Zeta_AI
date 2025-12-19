from __future__ import annotations

from dataclasses import dataclass
from collections import deque
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.decision_engine import is_safe_to_trust
from core.hyde_reformulator import HydeReformulator
from core.text_preprocessing import preprocess_for_routing, should_skip_preprocessing

logger = logging.getLogger(__name__)

SetFitModel = None  # type: ignore

@dataclass
class BotliveRoutingResult:
    intent: str
    confidence: float
    intent_group: str
    mode: str
    missing_fields: List[str]
    state: Dict[str, Any]
    debug: Dict[str, Any]

_MODEL_DIR = Path(__file__).resolve().parents[1] / "models" / "setfit-intent-classifier-v1"
_SET_FIT_MODEL: Any | None = None
_HYDE_MARGIN_HISTORY: deque[float] = deque(maxlen=500)


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def _truthy_env(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "y", "on"}


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return float(default)


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return int(default)


def _percentile_nearest_rank(sorted_vals: List[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    q = max(0.0, min(1.0, float(q)))
    import math
    k = max(1, math.ceil(q * len(sorted_vals))) - 1
    return float(sorted_vals[k])


def _hyde_margin_threshold() -> Tuple[float, str]:
    """Retourne seuil marge (top1-top2) pour déclencher HYDE sur ~bottom 15%."""
    bottom_pct = _float_env("BOTLIVE_HYDE_MARGIN_BOTTOM_PCT", 0.15)
    min_calls = _int_env("BOTLIVE_HYDE_MARGIN_MIN_CALLS", 50)

    if len(_HYDE_MARGIN_HISTORY) >= min_calls:
        vals = sorted(float(x) for x in _HYDE_MARGIN_HISTORY)
        thr = _percentile_nearest_rank(vals, bottom_pct)
        return float(thr), "rolling_percentile"

    return _float_env("BOTLIVE_HYDE_MARGIN_THRESHOLD", 0.10), "static_threshold"


def is_setfit_model_available(model_dir: Optional[Path] = None) -> bool:
    p = model_dir or _MODEL_DIR
    return bool(p and p.exists() and p.is_dir())


def _load_setfit_model() -> Any:
    global _SET_FIT_MODEL, SetFitModel

    if _SET_FIT_MODEL is not None:
        return _SET_FIT_MODEL

    if SetFitModel is None:
        try:
            import importlib
            try:
                import huggingface_hub as _hfh
                if not hasattr(_hfh, "DatasetFilter"):
                    class _DF:
                        pass
                    _hfh.DatasetFilter = _DF  # type: ignore[attr-defined]
            except Exception:
                pass
            SetFitModel = importlib.import_module("setfit").SetFitModel  # type: ignore[attr-defined]
        except Exception as e:
            raise RuntimeError(f"SetFit import error: {e}")

    if not is_setfit_model_available():
        raise FileNotFoundError(f"Modèle SetFit introuvable: {_MODEL_DIR}")

    _SET_FIT_MODEL = SetFitModel.from_pretrained(str(_MODEL_DIR))  # type: ignore[call-arg]
    return _SET_FIT_MODEL


# ==============================================================================
# MAPPING V4 - CORPUS REFACTORÉ
# ==============================================================================

def _map_setfit_label_to_legacy_intent(label: str) -> str:
    """
    Mapping SetFit V4 labels → Legacy intent names.
    
    CHANGEMENTS V3 → V4:
    - CATALOGUE + RECHERCHE_PRODUIT + DISPONIBILITE → PRODUIT_GLOBAL
    - SUIVI_COMMANDE + ANNULATION → COMMANDE_EXISTANTE
    """
    k = (label or "").strip().upper()

    mapping = {
        # GROUPE A - Conversationnels (inchangé)
        "SALUT_POLITESSE": "SALUT",
        "INFO_GENERALE": "INFO_GENERALE",
        
        # GROUPE B - Produits (FUSION)
        "PRODUIT_GLOBAL": "PRODUIT_GLOBAL",  # NOUVEAU - Fusion
        "CATALOGUE": "PRODUIT_GLOBAL",
        "RECHERCHE_PRODUIT": "PRODUIT_GLOBAL",
        "DISPONIBILITE": "PRODUIT_GLOBAL",
        "PRIX_PROMO": "PRIX_PROMO",
        
        # GROUPE C - Commande (inchangé)
        "COMMANDE": "ACHAT_COMMANDE",
        "LIVRAISON_INFO": "LIVRAISON",
        "PAIEMENT_TRANSACTION": "PAIEMENT",
        "CONTACT_COORDONNEES": "CONTACT_COORDONNEES",
        
        # GROUPE D - SAV (FUSION)
        "COMMANDE_EXISTANTE": "COMMANDE_EXISTANTE",  # NOUVEAU - Fusion
        "SUIVI_COMMANDE": "COMMANDE_EXISTANTE",
        "ANNULATION": "COMMANDE_EXISTANTE",
        "PROBLEME_RECLAMATION": "PROBLEME",
    }

    return mapping.get(k, k)


def _map_intent_to_group(intent: str) -> str:
    """
    Mapping intent → groupe métier.
    
    V4: PRODUIT_GLOBAL remplace CATALOGUE + RECHERCHE_PRODUIT + DISPONIBILITE
    """
    upper_intent = (intent or "").upper()

    if upper_intent in {"PRODUIT_GLOBAL", "PRIX_PROMO"}:  # V4
        return "PRODUIT"
    if upper_intent in {"ACHAT_COMMANDE", "COMMANDE_EXISTANTE"}:  # V4
        return "COMMANDE"
    if upper_intent in {"SALUT", "INFO_GENERALE", "CONTACT_COORDONNEES"}:
        return "INFO"
    if upper_intent == "PAIEMENT":
        return "PAIEMENT"
    if upper_intent == "LIVRAISON":
        return "LIVRAISON"

    return "AUTRE"


def _determine_mode_from_intent(intent: str, *, is_complete: bool, collected_count: int) -> str:
    """
    Détermine le mode Jessica selon intent V4.
    
    PATCH V2 (2025-12-16): Mode basé sur l'INTENT d'abord, puis le state.
    Cela évite que is_complete=True force RECEPTION_SAV partout.
    """
    upper_intent = (intent or "").upper()

    # PRIORITÉ 1: Intent prime sur state
    mode_mapping = {
        # COMMANDE (même si is_complete=True)
        "ACHAT_COMMANDE": "COMMANDE",
        "CONFIRMATION_PAIEMENT": "COMMANDE",
        "CONTACT_COORDONNEES": "COMMANDE",

        # GUIDEUR (même si is_complete=True, sauf SAV)
        "PRODUIT_GLOBAL": "GUIDEUR",
        "INFO_GENERALE": "GUIDEUR",
        "QUESTION_PAIEMENT": "GUIDEUR",
        "PAIEMENT": "GUIDEUR",
        "LIVRAISON": "GUIDEUR",
        "PRIX_PROMO": "GUIDEUR",
        "SALUT": "GUIDEUR",
        "CLARIFICATION": "GUIDEUR",

        # RECEPTION_SAV (uniquement intents SAV)
        "COMMANDE_EXISTANTE": "RECEPTION_SAV",
        "PROBLEME": "RECEPTION_SAV",
        "PROBLEME_LIVRAISON": "RECEPTION_SAV",
    }

    if upper_intent in mode_mapping:
        return mode_mapping[upper_intent]

    # PRIORITÉ 2: State (seulement si intent inconnu)
    if is_complete:
        return "RECEPTION_SAV"

    # Défaut
    return "GUIDEUR" if collected_count > 0 else "RECEPTION_SAV"


# ==============================================================================
# SUB-ROUTING PYTHON (NON DESTRUCTIF)
# ==============================================================================

def _sub_route_produit_global(message: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Sub-routing pour PRODUIT_GLOBAL (post-SetFit).
    Détermine: catalogue / stock / caracteristiques / recherche_generale.
    
    RÈGLE ABSOLUE: NE modifie JAMAIS l'intent principal.
    """
    text = (message or "").lower()
    
    # Priorité 1: Stock/Dispo
    stock_keywords = [
        "stock", "disponible", "dispo", "en rupture", "rupture",
        "il en reste", "reste combien", "vous avez encore"
    ]
    if any(k in text for k in stock_keywords):
        return "stock_disponibilite", "stock_keywords"
    
    # Priorité 2: Caractéristiques
    char_keywords = [
        "taille", "couleur", "âge", "age", "marque", "modèle", "modele",
        "caractéristique", "caracteristique", "garantie", "version",
        "référence", "reference", "composition", "fabriqué", "fabrique"
    ]
    if any(k in text for k in char_keywords):
        return "caracteristiques", "caracteristiques_keywords"
    
    # Priorité 3: Catalogue
    catalog_keywords = [
        "catalogue", "liste", "gamme", "voir tous", "tous les produits", "menu"
    ]
    if any(k in text for k in catalog_keywords):
        return "catalogue_general", "catalogue_keywords"
    
    # Défaut: recherche générale
    return "recherche_generale", "default"


def _sub_route_commande_existante(message: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Sub-routing pour COMMANDE_EXISTANTE (post-SetFit).
    Détermine: annulation / modification / suivi_simple.
    
    RÈGLE ABSOLUE: NE modifie JAMAIS l'intent principal.
    """
    text = (message or "").lower()
    
    # Priorité 1: Annulation (critique)
    annulation_keywords = [
        "annuler", "annulation", "annule", "je ne veux plus",
        "supprimer ma commande", "supprimez ma commande", "j'abandonne"
    ]
    if any(k in text for k in annulation_keywords):
        return "annulation", "annulation_keywords"
    
    # Priorité 2: Modification
    modif_keywords = [
        "modifier", "modification", "changer", "changement",
        "rectifier", "corriger", "changer l'adresse", "changer adresse",
        "ajouter", "retirer", "enlever"
    ]
    if any(k in text for k in modif_keywords):
        return "modification", "modification_keywords"
    
    # Défaut: suivi simple
    return "suivi_simple", "default"


def _apply_sub_routing(intent: str, message: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Applique sub-routing selon l'intent principal.
    Retourne (sub_route, sub_route_reason).
    
    RÈGLE ABSOLUE: NE modifie JAMAIS l'intent.
    """
    upper_intent = (intent or "").upper()
    
    if upper_intent == "PRODUIT_GLOBAL":
        return _sub_route_produit_global(message)
    
    elif upper_intent == "COMMANDE_EXISTANTE":
        return _sub_route_commande_existante(message)
    
    # Contact coordonnées (transversal)
    elif upper_intent in {"INFO_GENERALE", "SALUT"}:
        text = message.lower()
        contact_keywords = [
            "whatsapp", "numéro", "numero", "appelez-moi", "appelez",
            "joindre", "mon contact"
        ]
        phone_pattern = re.compile(r"\b(0[1-9](?:[ .-]?\d){7,})\b")
        if any(k in text for k in contact_keywords) or phone_pattern.search(text):
            return "contact_coordonnees", "contact_keywords_or_phone"
    
    return None, None


# ==============================================================================
# ROUTING SETFIT V4
# ==============================================================================

def _clip_text(s: str, max_len: int) -> str:
    val = (s or "").strip()
    if max_len <= 0:
        return ""
    return val[:max_len]


def _encode_state_compact(state_compact: Dict[str, Any]) -> str:
    s = state_compact or {}
    parts: List[str] = []
    try:
        parts.append(f"collected={int(s.get('collected_count', 0) or 0)}")
    except Exception:
        parts.append("collected=0")
    parts.append(f"complete={bool(s.get('is_complete', False))}")
    parts.append(f"photo={bool(s.get('photo_collected', False))}")
    parts.append(f"paiement={bool(s.get('paiement_collected', False))}")
    parts.append(f"zone={bool(s.get('zone_collected', False))}")
    parts.append(f"tel={bool(s.get('tel_collected', False))}")
    parts.append(f"tel_ok={bool(s.get('tel_valide', False))}")
    return " ".join(parts)


def _build_setfit_input(
    *,
    processed_message: str,
    conversation_history: str,
    state_compact: Dict[str, Any],
) -> str:
    ctx_enabled = _truthy_env("BOTLIVE_SETFIT_CONTEXT_ENABLED", "true")
    if not ctx_enabled:
        return processed_message

    hist_tail = _clip_text(conversation_history, 280)
    state_txt = _encode_state_compact(state_compact)
    return f"[CTX] {state_txt} [HIST] {hist_tail} [MSG] {processed_message}"


def _infer_last_bot_request(conversation_history: str) -> Optional[str]:
    tail = (conversation_history or "")[-400:].lower()
    if not tail.strip():
        return None
    if "num" in tail or "numero" in tail or "numéro" in tail or "telephone" in tail or "téléphone" in tail or "whatsapp" in tail:
        return "tel"
    if "adresse" in tail or "zone" in tail or "quartier" in tail:
        return "zone"
    if "paiement" in tail or "payer" in tail or "wave" in tail or "orange money" in tail or "mtn" in tail:
        return "paiement"
    if "photo" in tail or "image" in tail:
        return "photo"
    return None


def _is_short_confirmation(message: str) -> bool:
    t = (message or "").strip().lower()
    if not t:
        return False
    if len(t) > 18:
        return False
    confirm = {
        "ok",
        "d'accord",
        "dac",
        "oui",
        "ouais",
        "c'est bon",
        "cest bon",
        "ça marche",
        "ca marche",
        "vas-y",
        "vasy",
        "go",
    }
    return t in confirm


def _normalize_text_basic(message: str) -> str:
    raw = (message or "").strip().lower()
    raw = re.sub(r"[\s\t\r\n]+", " ", raw)
    return raw


def _has_payment_signal(message: str) -> bool:
    """
    Détecte si le message contient un signal de PAIEMENT explicite.
    
    PATCH V2 (2025-12-16): Ajout d'une blacklist pour forcer PRIX_PROMO
    quand "combien", "prix", "coût" apparaissent SANS verbe paiement.
    """
    t = _normalize_text_basic(message)
    if not t:
        return False
    
    # Mots-clés transactionnels PAIEMENT
    payment_keywords = [
        "paiement",
        "payer",
        "pay",
        "wave",
        "orange money",
        "mobile money",
        "mtn",
        "moov",
        "espece",
        "espèce",
        "carte",
        "facture",
        "recu",
        "reçu",
        "preuve",
        "acompte",
        "depot",
        "dépôt",
        "verser",
    ]
    
    # NOUVEAUTÉ: Blacklist PRIX (bloque PAIEMENT)
    price_keywords = ["combien", "prix", "coût", "cout", "tarif"]
    
    has_payment = any(k in t for k in payment_keywords)
    has_price = any(k in t for k in price_keywords)
    
    # Si question de prix SANS mention paiement → PAS PAIEMENT
    if has_price and not has_payment:
        return False
    
    return has_payment


def _lexical_fallback(message: str) -> Optional[str]:
    text = _normalize_text_basic(message)
    if not text:
        return None

    prix_keywords = {
        "combien",
        "prix",
        "coût",
        "cout",
        "tarif",
        "promo",
        "promotion",
        "réduction",
        "solde",
        "remise",
    }
    if any(k in text for k in prix_keywords):
        return "PRIX_PROMO"

    achat_keywords = {
        "commander",
        "commande",
        "acheter",
        "achète",
        "prendre",
        "prends",
        "je veux",
        "je prend",
        "mets-moi",
        "garde-moi",
        "réserve",
    }
    if any(k in text for k in achat_keywords):
        if "ma commande" not in text and "modifier" not in text and "annuler" not in text:
            return "ACHAT_COMMANDE"

    produit_keywords = {
        "disponible",
        "dispo",
        "stock",
        "rupture",
        "taille",
        "couleur",
        "âge",
        "age",
        "marque",
        "modèle",
        "modele",
        "caractéristique",
        "caracteristique",
        "garantie",
        "référence",
        "reference",
    }
    if any(k in text for k in produit_keywords):
        return "PRODUIT_GLOBAL"

    info_keywords = {
        "adresse",
        "où",
        "ou",
        "situé",
        "située",
        "situés",
        "quartier",
        "boutique",
        "magasin",
        "horaires",
        "ouvert",
        "ouvrez",
        "fermez",
    }
    if any(k in text for k in info_keywords):
        return "INFO_GENERALE"

    salut_keywords = {
        "bonjour",
        "bonsoir",
        "salut",
        "hello",
        "hey",
        "coucou",
        "yo",
        "wesh",
        "merci",
        "thanks",
    }
    tokens = text.split()
    if len(tokens) < 8 and any(k in text for k in salut_keywords):
        return "SALUT"

    return None


def _looks_like_social_only(message: str) -> bool:
    """
    Détecte si le message est UNIQUEMENT une salutation sociale.
    
    PATCH V2 (2025-12-16): Seuil réduit de 12 → 5 tokens pour éviter
    de classer "Bonjour, c'est combien" comme SALUT.
    """
    raw = (message or "").strip()
    if not raw:
        return False

    if "?" in raw:
        return False

    t = _normalize_text_basic(raw)
    tokens = [x for x in re.split(r"\s+", t) if x]
    if not tokens:
        return False

    greetings = {
        "bonjour", "bonsoir", "salut", "hello", "hey", "coucou",
        "yo", "wesh", "merci", "thanks",
    }

    has_greeting = any(tok in greetings for tok in tokens)
    if not has_greeting:
        return False

    action_verbs = {
        "commander", "acheter", "prendre", "reserver", "réserver",
        "livrer", "livraison", "payer", "paiement", "modifier",
        "annuler", "changer", "prix", "combien", "adresse",
        "ou", "où", "whatsapp", "numero", "numéro",
    }
    if any(tok in action_verbs for tok in tokens):
        return False

    # SEUIL RÉDUIT: 5 au lieu de 12
    return len(tokens) <= 5


def _deterministic_prefilter(
    *,
    message: str,
    conversation_history: str,
) -> Tuple[Optional[str], Optional[float], Dict[str, Any]]:
    raw = (message or "").strip()
    if not raw:
        return None, None, {}

    if _truthy_env("BOTLIVE_HUMAN_HANDOFF_ENABLED", "false"):
        t_norm = _normalize_text_basic(raw)
        sav_markers = [
            "abîmé",
            "abime",
            "cassé",
            "casse",
            "défectueux",
            "defectueux",
            "réclamation",
            "reclamation",
            "plainte",
            "remboursement",
            "rembourser",
            "retour",
            "retourner",
            "échange",
            "echange",
            "échanger",
            "echanger",
            "mauvais produit",
            "pas bon",
            "pas reçu",
            "pas recu",
            "pas encore reçu",
            "pas encore recu",
            "ne marche pas",
            "ça marche pas",
            "ca marche pas",
            "il manque",
            "incomplet",
            "erreur de commande",
            "j'ai reçu autre",
            "jai recu autre",
        ]
        if any(k in t_norm for k in sav_markers):
            return (
                "COMMANDE_EXISTANTE",
                0.95,
                {
                    "prefilter": "human_handoff_sav_marker",
                    "human_handoff": True,
                    "human_handoff_reason": "SAV_RECLAMATION_OR_RETURN",
                },
            )

    t_norm = _normalize_text_basic(raw)

    contact_markers = [
        "numéro",
        "numero",
        "téléphone",
        "telephone",
        "coordonnées",
        "coordonnees",
        "joindre",
        "appeler",
        "appel",
        "whatsapp",
    ]
    if any(k in t_norm for k in contact_markers):
        return "CONTACT_COORDONNEES", 0.90, {"prefilter": "lexical_contact"}

    achat_markers = [
        "je commande",
        "je veux commander",
        "je veux acheter",
        "je passe commande",
        "je passe la commande",
        "je veux passer commande",
        "je prends",
        "passer commande",
        "passe commande",
        "commander maintenant",
        "je commande maintenant",
        "je reviens pour commander",
        "envoie-moi",
        "envoie moi",
    ]
    if any(k in t_norm for k in achat_markers):
        return "ACHAT_COMMANDE", 0.88, {"prefilter": "lexical_achat"}

    if "il en reste" in t_norm or "en reste combien" in t_norm or "il vous reste" in t_norm:
        return "PRODUIT_GLOBAL", 0.82, {"prefilter": "lexical_stock"}

    if "livraison" in t_norm or "livrer" in t_norm or "livrez" in t_norm or "livré" in t_norm:
        if any(k in t_norm for k in ["combien", "prix", "tarif", "coute", "coûte", "ça coûte", "ca coute"]):
            return "LIVRAISON", 0.85, {"prefilter": "lexical_livraison_prix"}
        if "temps" in t_norm or "duree" in t_norm or "durée" in t_norm or "délai" in t_norm or "delai" in t_norm:
            return "LIVRAISON", 0.85, {"prefilter": "lexical_livraison_delai"}

    if any(k in t_norm for k in ["combien", "prix", "tarif", "coute", "coûte", "ça coûte", "ca coute"]):
        return "PRIX_PROMO", 0.85, {"prefilter": "lexical_prix_over_quantity"}

    if re.search(r"\b\d+\b", t_norm) and ("paquet" in t_norm or "paquets" in t_norm):
        return "ACHAT_COMMANDE", 0.85, {"prefilter": "lexical_achat_quantity"}

    if "paiement" in t_norm and "livraison" in t_norm:
        return "PAIEMENT", 0.88, {"prefilter": "lexical_paiement_livraison"}

    produit_markers = [
        "vous vendez",
        "tu vends",
        "vous avez quoi",
        "vous avez quoi comme",
        "qu'est-ce que vous vendez",
        "qu'est ce que vous vendez",
        "vous vendez quoi",
        "vous proposez quoi",
        "articles",
        "catalogue",
        "couches",
        "couche",
        "culotte",
    ]
    if any(k in t_norm for k in produit_markers):
        return "PRODUIT_GLOBAL", 0.86, {"prefilter": "lexical_produit"}

    more_info_markers = [
        "m en dire plus",
        "men dire plus",
        "en dire plus",
        "plus d infos",
        "plus d info",
        "plus d information",
        "plus d informations",
        "plus de detail",
        "plus de details",
        "plus de détail",
        "plus de détails",
        "plus de precisions",
        "plus de précision",
    ]
    if any(k in t_norm for k in more_info_markers):
        return "PRODUIT_GLOBAL", 0.82, {"prefilter": "lexical_more_info_to_produit"}

    livraison_sav_markers = [
        "ma commande",
        "mon colis",
        "numéro",
        "numero",
        "suivi",
        "tracking",
        "statut",
        "où est mon",
        "ou est mon",
    ]
    if "livraison" in t_norm or "livrer" in t_norm or "livrez" in t_norm or "livré" in t_norm or "delai" in t_norm or "délai" in t_norm:
        if not any(k in t_norm for k in livraison_sav_markers):
            return "LIVRAISON", 0.82, {"prefilter": "lexical_livraison"}

    if any(k in t_norm for k in ["commune", "quartier", "localisation", "localisation exacte", "adresse exacte", "position", "localiser", "localisez"]):
        return "INFO_GENERALE", 0.80, {"prefilter": "lexical_location"}

    phone_pattern = re.compile(r"\b(?:\+?225)?\s*(?:0[1-9])(?:[ .-]?\d){7,}\b")
    if phone_pattern.search(raw):
        return "CONTACT_COORDONNEES", 0.98, {"prefilter": "phone_regex"}

    if should_skip_preprocessing(raw) or _looks_like_social_only(raw):
        return "SALUT", 0.98, {"prefilter": "salut_rule"}

    try:
        processed = preprocess_for_routing(raw)
        if not processed and any(k in _normalize_text_basic(raw) for k in ["bonjour", "bonsoir", "salut", "hey", "hello", "yo", "wesh"]):
            return "SALUT", 0.90, {"prefilter": "salut_empty_after_preprocess"}
    except Exception:
        pass

    if _is_short_confirmation(raw):
        req = _infer_last_bot_request(conversation_history)
        if req == "tel":
            return "CONTACT_COORDONNEES", 0.85, {"prefilter": "short_confirm_after_tel_request"}
        if req == "zone":
            return "LIVRAISON", 0.75, {"prefilter": "short_confirm_after_zone_request"}
        if req == "paiement":
            return "PAIEMENT", 0.75, {"prefilter": "short_confirm_after_payment_request"}

    return None, None, {}


def _route_with_setfit(
    message: str,
    *,
    conversation_history: str = "",
    state_compact: Optional[Dict[str, Any]] = None,
) -> Tuple[str, float, Dict[str, Any]]:
    raw = (message or "").strip()
    if not raw:
        return "CLARIFICATION", 0.0, {"router": "setfit", "reason": "EMPTY"}

    def _preprocess_light(msg: str) -> str:
        t = (msg or "").strip().lower()
        t = re.sub(r"^(bonjour|bonsoir|salut|hello|hey|coucou|yo|wesh)[\s,\.!]+", "", t)
        t = " ".join(t.split())
        return t

    def _apply_setfit_guards(
        *,
        legacy_intent: str,
        legacy_top2_intent: str,
        conf: float,
        top2_prob: float,
        raw_message: str,
    ) -> Tuple[str, float, bool, Optional[str]]:
        guard_applied = False
        guard_reason: Optional[str] = None
        intent_out = legacy_intent
        conf_out = float(conf)

        if (legacy_intent or "").upper() == "PAIEMENT" and not _has_payment_signal(raw_message):
            if legacy_top2_intent and (legacy_top2_intent or "").upper() != "PAIEMENT":
                guard_applied = True
                guard_reason = "PAIEMENT_NO_SIGNAL_FALLBACK_TO_TOP2"
                intent_out = legacy_top2_intent
                conf_out = float(top2_prob)
            else:
                guard_applied = True
                guard_reason = "PAIEMENT_NO_SIGNAL_FALLBACK_TO_CLARIFICATION"
                intent_out = "CLARIFICATION"
                conf_out = float(min(float(conf), 0.40))

        if (intent_out or "").upper() == "COMMANDE_EXISTANTE":
            sav_keywords = [
                "commande",
                "ma commande",
                "colis",
                "livraison",
                "livré",
                "livreur",
                "suivi",
                "tracking",
                "retard",
                "modifier",
                "annuler",
                "changer",
                "où est",
                "quand arrive",
                "statut",
                "expédié",
                "pas reçu",
                "toujours pas",
            ]

            raw_lower = (raw_message or "").lower()
            has_sav_signal = any(k in raw_lower for k in sav_keywords)

            if not has_sav_signal:
                if float(conf_out) < 0.20:
                    lexical_intent = _lexical_fallback(raw_message)

                    if lexical_intent and lexical_intent != "COMMANDE_EXISTANTE":
                        guard_applied = True
                        guard_reason = f"CE_NO_SIGNAL_LOW_CONF_LEXICAL_FALLBACK_{lexical_intent}"
                        intent_out = lexical_intent
                        conf_out = 0.60
                    else:
                        guard_applied = True
                        guard_reason = "CE_NO_SIGNAL_LOW_CONF_CLARIFICATION"
                        intent_out = "CLARIFICATION"
                        conf_out = 0.40

                elif float(conf_out) < 0.50:
                    if legacy_top2_intent and (legacy_top2_intent or "").upper() != "COMMANDE_EXISTANTE":
                        guard_applied = True
                        guard_reason = "CE_NO_SIGNAL_MED_CONF_FALLBACK_TOP2"
                        intent_out = legacy_top2_intent
                        conf_out = float(top2_prob)
                    else:
                        lexical_intent = _lexical_fallback(raw_message)
                        if lexical_intent and lexical_intent != "COMMANDE_EXISTANTE":
                            guard_applied = True
                            guard_reason = f"CE_NO_SIGNAL_MED_CONF_LEXICAL_FALLBACK_{lexical_intent}"
                            intent_out = lexical_intent
                            conf_out = 0.60
                        else:
                            guard_applied = True
                            guard_reason = "CE_NO_SIGNAL_MED_CONF_CLARIFICATION"
                            intent_out = "CLARIFICATION"
                            conf_out = 0.40

                else:
                    if legacy_top2_intent and (legacy_top2_intent or "").upper() != "COMMANDE_EXISTANTE":
                        guard_applied = True
                        guard_reason = "CE_NO_SIGNAL_HIGH_CONF_FALLBACK_TOP2"
                        intent_out = legacy_top2_intent
                        conf_out = float(top2_prob)
                    else:
                        guard_applied = True
                        guard_reason = "CE_NO_SIGNAL_HIGH_CONF_CLARIFICATION"
                        intent_out = "CLARIFICATION"
                        conf_out = 0.50

        return intent_out, float(conf_out), bool(guard_applied), guard_reason

    try:
        model = _load_setfit_model()
    except Exception as e:
        return "CLARIFICATION", 0.0, {"router": "setfit", "reason": f"MODEL_ERROR:{e}"}

    variants: List[Dict[str, Any]] = []
    try:
        processed_full = raw if should_skip_preprocessing(raw) else preprocess_for_routing(raw)
        processed_light = _preprocess_light(raw)

        variant_specs = [
            ("RAW", raw, 1.0),
            ("LIGHT", processed_light, 1.2),
            ("FULL", processed_full, 0.8),
        ]

        for name, msg_v, weight in variant_specs:
            if not (msg_v or "").strip():
                continue

            setfit_input = _build_setfit_input(
                processed_message=msg_v,
                conversation_history=conversation_history or "",
                state_compact=state_compact or {},
            )

            probs_batch = model.predict_proba([setfit_input])
            probs = probs_batch[0]
            n = len(probs)
            if n <= 0:
                continue

            order = sorted(range(n), key=lambda i: float(probs[i]), reverse=True)
            intent_idx = int(order[0])
            label = str(model.labels[intent_idx])
            conf = float(probs[intent_idx])

            top2_idx = int(order[1]) if len(order) > 1 else intent_idx
            top2_label = str(model.labels[top2_idx]) if len(order) > 1 else label
            top2_prob = float(probs[top2_idx]) if len(order) > 1 else 0.0
            margin = float(max(0.0, conf - top2_prob))

            legacy_intent = _map_setfit_label_to_legacy_intent(label)
            legacy_top2_intent = _map_setfit_label_to_legacy_intent(top2_label)
            intent_after, conf_after, guard_applied, guard_reason = _apply_setfit_guards(
                legacy_intent=legacy_intent,
                legacy_top2_intent=legacy_top2_intent,
                conf=conf,
                top2_prob=top2_prob,
                raw_message=raw,
            )

            score = float(conf_after) * float(margin) * float(weight)

            variants.append(
                {
                    "name": name,
                    "weight": float(weight),
                    "processed_message": msg_v,
                    "setfit_input": setfit_input,
                    "setfit_label": label,
                    "setfit_confidence": conf,
                    "setfit_top2_label": top2_label,
                    "setfit_top2_confidence": top2_prob,
                    "setfit_margin": margin,
                    "legacy_top2_intent": legacy_top2_intent,
                    "intent_before_guard": legacy_intent,
                    "intent_after_guard": intent_after,
                    "confidence_after_guard": float(conf_after),
                    "payment_guard_applied": bool(guard_applied),
                    "payment_guard_reason": guard_reason,
                    "vote_score": score,
                }
            )
    except Exception as e:
        return "CLARIFICATION", 0.0, {"router": "setfit", "reason": f"PREDICT_ERROR:{e}"}

    if not variants:
        if _looks_like_social_only(raw):
            return "SALUT", 0.90, {"router": "setfit", "reason": "SOCIAL_ONLY_EMPTY_AFTER_PREPROCESS"}
        return "CLARIFICATION", 0.0, {"router": "setfit", "reason": "EMPTY_PROBS"}

    intent_votes: Dict[str, int] = {}
    for v in variants:
        intent_votes[str(v.get("intent_after_guard") or "")] = int(intent_votes.get(str(v.get("intent_after_guard") or ""), 0)) + 1

    consensus_intent: Optional[str] = None
    for k, cnt in intent_votes.items():
        if cnt >= 2 and k:
            consensus_intent = k
            break

    chosen = None
    used_consensus = False
    if consensus_intent:
        agreeing = [v for v in variants if str(v.get("intent_after_guard") or "") == consensus_intent]
        if agreeing:
            chosen = max(agreeing, key=lambda x: float(x.get("vote_score") or 0.0))
            used_consensus = True

    if chosen is None:
        chosen = max(variants, key=lambda x: float(x.get("vote_score") or 0.0))

    debug = {
        "router": "setfit_v4",
        "raw_message": raw,
        "model_dir": str(_MODEL_DIR),
        "ensemble_voting": True,
        "ensemble_consensus_intent": consensus_intent,
        "ensemble_used_consensus": bool(used_consensus),
        "ensemble_chosen_variant": str(chosen.get("name") or ""),
        "ensemble_variants": variants,
        "processed_message": str(chosen.get("processed_message") or ""),
        "setfit_input": chosen.get("setfit_input"),
        "preprocessing_used": str(chosen.get("name") or "") != "RAW",
        "setfit_label": str(chosen.get("setfit_label") or ""),
        "setfit_confidence": float(chosen.get("setfit_confidence") or 0.0),
        "setfit_top2_label": str(chosen.get("setfit_top2_label") or ""),
        "setfit_top2_confidence": float(chosen.get("setfit_top2_confidence") or 0.0),
        "setfit_margin": float(chosen.get("setfit_margin") or 0.0),
        "legacy_top2_intent": str(chosen.get("legacy_top2_intent") or ""),
        "intent_before_guard": str(chosen.get("intent_before_guard") or ""),
        "intent_after_guard": str(chosen.get("intent_after_guard") or ""),
        "payment_guard_applied": bool(chosen.get("payment_guard_applied")),
        "payment_guard_reason": chosen.get("payment_guard_reason"),
    }

    return str(chosen.get("intent_after_guard") or "CLARIFICATION"), float(chosen.get("confidence_after_guard") or 0.0), debug


def _post_validate_intent(
    *,
    intent: str,
    confidence: float,
    message: str,
    state_compact: Dict[str, Any],
) -> Tuple[str, float, Dict[str, Any]]:
    """Post-validation légère intent vs état.

    Objectif:
    - Détecter des contradictions évidentes (ex: intent CONTACT mais tel déjà validé sans signal dans le message).
    - En cas de contradiction: fallback vers CLARIFICATION (non destructif sur le state).
    """
    upper_intent = (intent or "").upper().strip() or "CLARIFICATION"
    conf = float(max(0.0, min(1.0, confidence)))

    raw = (message or "").strip()
    t = raw.lower()
    st = state_compact or {}

    debug: Dict[str, Any] = {
        "post_validation": True,
        "post_validation_applied": False,
        "post_validation_reason": None,
        "post_validation_intent_before": upper_intent,
    }

    tel_ok = bool(st.get("tel_valide", False))
    tel_collected = bool(st.get("tel_collected", False))
    is_complete = bool(st.get("is_complete", False))

    phone_pattern = re.compile(r"\b(?:\+?225)?\s*(?:0[1-9])(?:[ .-]?\d){7,}\b")
    has_phone = bool(phone_pattern.search(raw))
    has_contact_signal = (
        has_phone
        or "contact" in t
        or "numéro" in t
        or "numero" in t
        or "téléphone" in t
        or "telephone" in t
        or "whatsapp" in t
        or "joindre" in t
    )

    if upper_intent == "CONTACT_COORDONNEES" and tel_ok and tel_collected and not has_contact_signal:
        debug["post_validation_applied"] = True
        debug["post_validation_reason"] = "CONTACT_BUT_TEL_ALREADY_OK_NO_SIGNAL"
        return "CLARIFICATION", min(conf, 0.40), debug

    if upper_intent == "ACHAT_COMMANDE" and is_complete:
        debug["post_validation_applied"] = True
        debug["post_validation_reason"] = "ACHAT_COMMANDE_BUT_STATE_COMPLETE"
        return "CLARIFICATION", min(conf, 0.40), debug

    if is_complete and upper_intent in {"PAIEMENT", "LIVRAISON"}:
        payment_kw = any(k in t for k in ["paiement", "payer", "wave", "orange money", "mtn", "moov"])
        shipping_kw = any(k in t for k in ["livraison", "livrer", "délai", "delai", "frais", "zone"])
        if upper_intent == "PAIEMENT" and not payment_kw:
            debug["post_validation_applied"] = True
            debug["post_validation_reason"] = "PAIEMENT_BUT_STATE_COMPLETE_NO_SIGNAL"
            return "CLARIFICATION", min(conf, 0.40), debug
        if upper_intent == "LIVRAISON" and not shipping_kw:
            debug["post_validation_applied"] = True
            debug["post_validation_reason"] = "LIVRAISON_BUT_STATE_COMPLETE_NO_SIGNAL"
            return "CLARIFICATION", min(conf, 0.40), debug

    if upper_intent == "INFO_GENERALE":
        if any(k in t for k in ["zone", "couvrez", "secteur", "périmètre", "perimetre"]):
            debug["post_validation_applied"] = True
            debug["post_validation_reason"] = "ZONES_TO_LIVRAISON"
            return "LIVRAISON", 0.80, debug

    if upper_intent == "INFO_GENERALE":
        salut_patterns = [
            "bonjour",
            "bonsoir",
            "salut",
            "hey",
            "yo",
            "bjr",
            "bondjour",
            "bondjur",
            "bjour",
        ]
        smalltalk_patterns = [
            "j'espère",
            "j espere",
            "ça va",
            "ca va",
            "comment",
            "la forme",
            "tout va bien",
            "désolé",
            "desole",
            "pardon",
        ]
        has_salut = any(p in t for p in salut_patterns)
        has_smalltalk = any(p in t for p in smalltalk_patterns)

        info_keywords_present = bool(re.search(r"\b(?:ou|où)\b", t)) or any(
            k in t for k in ["adresse", "quartier", "situé", "horaire", "ouvert", "fermez"]
        )

        if (has_salut or has_smalltalk) and not info_keywords_present:
            debug["post_validation_applied"] = True
            debug["post_validation_reason"] = "SMALLTALK_TO_SALUT"
            return "SALUT", min(conf, 0.75), debug

    if upper_intent == "SALUT":
        has_where_word = bool(re.search(r"\b(?:ou|où)\b", t))
        has_location_kw = any(k in t for k in ["adresse", "situé", "quartier", "boutique"])
        if has_where_word or has_location_kw:
            debug["post_validation_applied"] = True
            debug["post_validation_reason"] = "SALUT_WITH_LOCATION_TO_INFO"
            return "INFO_GENERALE", conf, debug

    if upper_intent == "COMMANDE_EXISTANTE":
        modify_delivery = [
            "modifier adresse",
            "modifier l'adresse",
            "modifier l’adresse",
            "changer adresse",
            "changer l'adresse",
            "changer l’adresse",
            "changer date",
            "changer la date",
            "modifier date",
            "modifier la date",
        ]

        modify_actions = [
            "changer",
            "modifier",
            "déplacer",
            "deplacer",
            "reporter",
            "mettre à jour",
            "mettre a jour",
        ]
        delivery_objects = [
            "adresse",
            "date",
            "lieu",
            "endroit",
            "quartier",
            "zone",
            "localisation",
            "destination",
            "point",
        ]
        has_livraison_anchor = ("livraison" in t) or ("livrer" in t)
        has_action = any(a in t for a in modify_actions)
        has_delivery_obj = any(o in t for o in delivery_objects)

        sav_markers = [
            "ma commande",
            "mon colis",
            "ma livraison",
            "numéro",
            "numero",
            "suivi",
            "statut",
            "pas reçu",
            "pas recu",
            "où est mon",
            "ou est mon",
        ]
        has_modify_delivery = (any(k in t for k in modify_delivery) or (has_action and has_delivery_obj and has_livraison_anchor))
        has_sav_marker = any(k in t for k in sav_markers)
        if has_modify_delivery and not has_sav_marker:
            debug["post_validation_applied"] = True
            debug["post_validation_reason"] = "CE_TO_LIVRAISON_NO_SAV_MARKER"
            return "LIVRAISON", min(conf, 0.80), debug

        if any(
            k in t
            for k in [
                "je veux commander",
                "je veux acheter",
                "je prends",
                "passer commande",
                "envoie-moi",
            ]
        ):
            debug["post_validation_applied"] = True
            debug["post_validation_reason"] = "CE_WITH_ACHAT_VERB_TO_ACHAT"
            return "ACHAT_COMMANDE", conf, debug

    if upper_intent == "LIVRAISON":
        modify_delivery = [
            "modifier adresse",
            "modifier l'adresse",
            "modifier l’adresse",
            "changer adresse",
            "changer l'adresse",
            "changer l’adresse",
            "changer date",
            "changer la date",
            "modifier date",
            "modifier la date",
        ]

        modify_actions = [
            "changer",
            "modifier",
            "déplacer",
            "deplacer",
            "reporter",
            "mettre à jour",
            "mettre a jour",
        ]
        delivery_objects = [
            "adresse",
            "date",
            "lieu",
            "endroit",
            "quartier",
            "zone",
            "localisation",
            "destination",
            "point",
        ]
        has_livraison_anchor = ("livraison" in t) or ("livrer" in t)
        has_action = any(a in t for a in modify_actions)
        has_delivery_obj = any(o in t for o in delivery_objects)

        sav_markers = [
            "ma commande",
            "mon colis",
            "ma livraison",
            "numéro",
            "numero",
            "suivi",
            "statut",
            "pas reçu",
            "pas recu",
            "où est mon",
            "ou est mon",
        ]
        has_modify = (any(k in t for k in modify_delivery) or (has_action and has_delivery_obj and has_livraison_anchor))
        has_sav_marker = any(k in t for k in sav_markers)
        if has_modify and has_sav_marker:
            debug["post_validation_applied"] = True
            debug["post_validation_reason"] = "LIVRAISON_TO_CE_SAV"
            return "COMMANDE_EXISTANTE", conf, debug

    return upper_intent, conf, debug


async def route_botlive_intent(
    company_id: str,
    user_id: str,
    message: str,
    conversation_history: str,
    state_compact: Dict[str, Any],
    hyde_pre_enabled: bool | None = None,
) -> BotliveRoutingResult:
    ctx: Dict[str, Any] = {
        "conversation_history": conversation_history or "",
        "state_compact": state_compact or {},
    }

    original_message = message
    routed_message = message
    hyde_pre_used = False
    hyde_pre_reason = "NOT_TRIGGERED"

    forced_intent, forced_conf, prefilter_debug = _deterministic_prefilter(
        message=original_message,
        conversation_history=conversation_history or "",
    )

    if forced_intent:
        intent = forced_intent
        conf = float(forced_conf or 0.0)
        router_debug: Dict[str, Any] = {"router": "prefilter", **prefilter_debug}
        margin_val = 0.0
    else:
        intent, conf, router_debug = _route_with_setfit(
            routed_message,
            conversation_history=conversation_history or "",
            state_compact=state_compact or {},
        )
        margin_val = float(router_debug.get("setfit_margin") or 0.0)
        _HYDE_MARGIN_HISTORY.append(margin_val)

        safe_to_trust = is_safe_to_trust(intent, float(conf or 0.0), float(margin_val or 0.0))
        enforce_gate = _truthy_env("BOTLIVE_SAFETY_GATE_ENFORCE", "false")
        router_debug["safety_gate_applied"] = True
        router_debug["safety_gate_safe_to_trust"] = bool(safe_to_trust)
        if not safe_to_trust:
            router_debug["safety_gate_action"] = "NEEDS_LLM"
            router_debug["safety_gate_intent_before"] = (intent or "").upper()
            router_debug["safety_gate_enforced"] = bool(enforce_gate)
            if enforce_gate:
                intent = "CLARIFICATION"
                conf = float(min(float(conf or 0.0), 0.40))
        else:
            router_debug["safety_gate_action"] = "TRUST_SET_FIT"
            router_debug["safety_gate_enforced"] = bool(enforce_gate)

    try:
        effective_hyde_pre_enabled = hyde_pre_enabled
        if effective_hyde_pre_enabled is None:
            effective_hyde_pre_enabled = _truthy_env("BOTLIVE_HYDE_PRE_ENABLED", "true")

        if effective_hyde_pre_enabled and not forced_intent and not (router_debug.get("safety_gate_enforced") and router_debug.get("safety_gate_action") == "NEEDS_LLM"):
            thr, thr_source = _hyde_margin_threshold()
            router_debug["hyde_margin"] = margin_val
            router_debug["hyde_margin_threshold"] = thr
            router_debug["hyde_margin_threshold_source"] = thr_source
            router_debug["hyde_margin_history_size"] = len(_HYDE_MARGIN_HISTORY)

            should_use_hyde = margin_val <= float(thr)
            if should_use_hyde:
                hyde_pre_reason = f"LOW_MARGIN<=THR({thr_source})"
                try:
                    reformulator = HydeReformulator()
                    routed_message = await reformulator.reformulate(company_id, original_message, ctx)
                    hyde_pre_used = routed_message != original_message

                    intent2, conf2, router_debug2 = _route_with_setfit(
                        routed_message,
                        conversation_history=conversation_history or "",
                        state_compact=state_compact or {},
                    )
                    router_debug["hyde_routed_message"] = routed_message
                    router_debug["hyde_setfit_intent_before"] = (intent or "").upper()
                    router_debug["hyde_setfit_conf_before"] = float(conf or 0.0)
                    router_debug["hyde_setfit_intent_after"] = (intent2 or "").upper()
                    router_debug["hyde_setfit_conf_after"] = float(conf2 or 0.0)
                    router_debug.update({f"hyde_after_{k}": v for k, v in router_debug2.items()})
                    intent, conf = intent2, conf2
                except Exception as e:
                    router_debug["hyde_error"] = str(e)
            else:
                hyde_pre_reason = "MARGIN_OK"
        else:
            hyde_pre_reason = "HYDE_PRE_DISABLED" if not effective_hyde_pre_enabled else "SKIP_HYDE"
    except Exception as e:
        router_debug["hyde_gating_error"] = str(e)
        hyde_pre_reason = "HYDE_ERROR"

    sub_route, sub_route_reason = _apply_sub_routing(intent, original_message)
    if sub_route:
        router_debug["business_subroute"] = sub_route
    if sub_route_reason:
        router_debug["business_subroute_reason"] = sub_route_reason

    upper_intent, conf2, post_debug = _post_validate_intent(
        intent=intent,
        confidence=float(conf or 0.0),
        message=original_message,
        state_compact=state_compact or {},
    )
    router_debug.update(post_debug)

    confidence = float(max(0.0, min(1.0, conf2)))
    intent_group = _map_intent_to_group(upper_intent)

    collected_count = int((state_compact or {}).get("collected_count", 0) or 0)
    is_complete = bool((state_compact or {}).get("is_complete", False))
    mode = _determine_mode_from_intent(upper_intent, is_complete=is_complete, collected_count=collected_count)

    missing: List[str] = []
    if not (state_compact or {}).get("photo_collected", False):
        missing.append("photo")
    if not (state_compact or {}).get("paiement_collected", False):
        missing.append("paiement")
    if not (state_compact or {}).get("zone_collected", False):
        missing.append("zone")
    if not (state_compact or {}).get("tel_collected", False) or not (state_compact or {}).get("tel_valide", False):
        missing.append("tel")

    debug = {
        "company_id": company_id,
        "user_id": user_id,
        "raw_message": message,
        "conversation_history_sample": conversation_history[-300:] if conversation_history else "",
        "hyde_pre_used": hyde_pre_used,
        "hyde_pre_reason": hyde_pre_reason,
        "original_message": original_message,
        "routed_message": routed_message,
        **router_debug,
    }

    return BotliveRoutingResult(
        intent=upper_intent,
        confidence=confidence,
        intent_group=intent_group,
        mode=mode,
        missing_fields=missing,
        state=state_compact or {},
        debug=debug,
    )
