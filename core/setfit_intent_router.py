from __future__ import annotations

from dataclasses import dataclass
from collections import deque
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    COLORS_ENABLED = True
except ImportError:
    COLORS_ENABLED = False
    class Fore:
        GREEN = RED = YELLOW = CYAN = MAGENTA = BLUE = ""
    class Style:
        RESET_ALL = BRIGHT = ""

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

_MODEL_DIR = Path(__file__).resolve().parents[1] / "models" / "setfit-intent-classifier-v5"
_SET_FIT_MODEL: Any | None = None
_HYDE_MARGIN_HISTORY: deque[float] = deque(maxlen=500)
_MODEL_VERSION: str | None = None  # "V4" ou "V5"


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
    global _SET_FIT_MODEL, _MODEL_VERSION, SetFitModel

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
    
    # Detect model version from labels
    _MODEL_VERSION = _detect_model_version(_SET_FIT_MODEL)
    logger.info(f"[SETFIT] Modèle chargé: version={_MODEL_VERSION}, labels={_SET_FIT_MODEL.labels}")
    
    return _SET_FIT_MODEL


def _detect_model_version(model: Any) -> str:
    """
    Détecte la version du modèle SetFit selon les labels.
    
    V4: 10 intents (SALUT, INFO_GENERALE, PRODUIT_GLOBAL, PRIX_PROMO, ...)
    V5: 4 pôles (REASSURANCE, SHOPPING, ACQUISITION, SAV_SUIVI)
    
    Returns:
        "V5" si 4 pôles détectés, "V4" sinon
    """
    try:
        labels = [str(lbl).upper() for lbl in model.labels]
        v5_poles = {"REASSURANCE", "SHOPPING", "ACQUISITION", "SAV_SUIVI"}
        
        if v5_poles.issubset(set(labels)):
            return "V5"
        return "V4"
    except Exception as e:
        logger.warning(f"[SETFIT] Erreur détection version: {e}, assume V4")
        return "V4"


def _map_v4_intent_to_v5_pole(intent: str) -> str:
    """
    Mapping V4 intent → V5 pôle (fallback si modèle V4 chargé).
    
    Utilise POLE_MAPPING_V4_TO_V5 de universal_corpus.py.
    """
    from core.universal_corpus import INTENT_DEFINITIONS_V4, POLE_MAPPING_V4_TO_V5
    
    upper_intent = (intent or "").upper()
    
    # Trouver l'ID V4 de l'intent
    intent_id = None
    for iid, idef in INTENT_DEFINITIONS_V4.items():
        if idef["name"].upper() == upper_intent:
            intent_id = iid
            break
    
    if intent_id is None:
        logger.warning(f"[V4→V5] Intent V4 inconnu: {intent}, fallback REASSURANCE")
        return "REASSURANCE"
    
    pole = POLE_MAPPING_V4_TO_V5.get(intent_id)
    if not pole:
        logger.warning(f"[V4→V5] Pas de mapping pour intent_id={intent_id}, fallback REASSURANCE")
        return "REASSURANCE"
    
    return pole


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
    V5: 4 pôles (REASSURANCE, SHOPPING, ACQUISITION, SAV_SUIVI)
    """
    upper_intent = (intent or "").upper()

    # V5 poles
    if upper_intent in {"REASSURANCE", "SHOPPING", "ACQUISITION", "SAV_SUIVI"}:
        return upper_intent

    # V4 intents
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
    Détermine le mode Jessica selon intent V4 ou pôle V5.
    
    PATCH V2 (2025-12-16): Mode basé sur l'INTENT d'abord, puis le state.
    V5 (2025-12-26): Mode = Pôle directement (REASSURANCE, SHOPPING, ACQUISITION, SAV_SUIVI)
    
    Action #4: En V5, JAMAIS retourner GUIDEUR - utiliser le pôle V5 directement.
    """
    upper_intent = (intent or "").upper()

    # V5: Mode = Pôle (priorité absolue)
    if upper_intent in {"REASSURANCE", "SHOPPING", "ACQUISITION", "SAV_SUIVI"}:
        return upper_intent

    # ==========================================================================
    # Action #4: En V5, mapper les intents legacy vers les pôles V5
    # JAMAIS retourner GUIDEUR en V5
    # ==========================================================================
    if _MODEL_VERSION == "V5":
        # Mapping intents legacy V4 → pôles V5
        v5_mode_mapping = {
            # Intents d'achat → ACQUISITION
            "ACHAT_COMMANDE": "ACQUISITION",
            "CONFIRMATION_PAIEMENT": "ACQUISITION",
            "CONTACT_COORDONNEES": "ACQUISITION",
            
            # Intents produit/info → SHOPPING
            "PRODUIT_GLOBAL": "SHOPPING",
            "INFO_GENERALE": "REASSURANCE",
            "QUESTION_PAIEMENT": "REASSURANCE",
            "PAIEMENT": "ACQUISITION",
            "LIVRAISON": "SHOPPING",
            "PRIX_PROMO": "SHOPPING",
            
            # Intents smalltalk/clarification → REASSURANCE
            "SALUT": "REASSURANCE",
            "CLARIFICATION": "REASSURANCE",  # ← Plus jamais GUIDEUR!
            
            # Intents SAV → SAV_SUIVI
            "COMMANDE_EXISTANTE": "SAV_SUIVI",
            "PROBLEME": "SAV_SUIVI",
            "PROBLEME_LIVRAISON": "SAV_SUIVI",
        }
        
        if upper_intent in v5_mode_mapping:
            return v5_mode_mapping[upper_intent]
        
        # Fallback V5: REASSURANCE (jamais GUIDEUR)
        if is_complete:
            return "SAV_SUIVI"
        return "REASSURANCE"

    # V4: PRIORITÉ 1: Intent prime sur state (comportement legacy)
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
    }
    return t in confirm


def _normalize_text_basic(text: str) -> str:
    raw = (text or "").strip().lower()
    raw = re.sub(r"\s+", " ", raw)
    return raw


def should_skip_preprocessing(text: str) -> bool:
    raw = (text or "").strip()
    if not raw:
        return True

    t_norm = _normalize_text_basic(raw)
    tokens = [t for t in t_norm.split(" ") if t]

    # Messages très courts: on évite de les dégrader via preprocessing.
    if len(tokens) < 3:
        return True

    # Petits messages de politesse / salutations uniquement.
    smalltalk_only = {
        "salut",
        "bonjour",
        "bonsoir",
        "coucou",
        "hello",
        "hey",
        "yo",
        "wesh",
        "merci",
    }
    if len(tokens) <= 4 and all(tok in smalltalk_only for tok in tokens):
        return True

    return False


def _looks_like_social_only(message: str) -> bool:
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

    has_greeting = any(tok in greetings for tok in tokens)
    if not has_greeting:
        return False

    action_verbs = {
        "commander",
        "acheter",
        "prendre",
        "reserver",
        "réserver",
        "livrer",
        "livraison",
        "payer",
        "paie",
        "paiement",
        "modifier",
        "annuler",
        "changer",
        "prix",
        "combien",
        "adresse",
        "ou",
        "où",
        "whatsapp",
        "numero",
        "numéro",
    }
    if any(tok in action_verbs for tok in tokens):
        return False

    return len(tokens) <= 5


def _looks_like_media_url(raw: str) -> bool:
    try:
        s = (raw or "").strip().lower()
        if not s:
            return False
        if not (s.startswith("http://") or s.startswith("https://")):
            return False
        if any(x in s for x in ["fbcdn.net/", "scontent."]):
            return True
        if re.search(r"\.(jpg|jpeg|png|webp|gif)(\?|$)", s):
            return True
        return False
    except Exception:
        return False


def _deterministic_prefilter(message: str, *, conversation_history: str = "") -> Tuple[Optional[str], Optional[float], Dict[str, Any]]:
    raw = (message or "").strip()
    if not raw:
        return None, None, {}

    # IMPORTANT: une URL d'image ne doit jamais être classée comme SALUT/REASSURANCE par heuristique.
    # Elle sera traitée via le pipeline vision + l'état (photo/paiement/etc.).
    is_media_url = _looks_like_media_url(raw)

    # Le prefilter est appelé avant le premier appel SetFit dans route_botlive_intent.
    # Donc _MODEL_VERSION peut être None ici: on charge le modèle pour détecter V4/V5.
    try:
        global _MODEL_VERSION
        if _MODEL_VERSION is None:
            _load_setfit_model()
    except Exception as e:
        # Si le modèle n'est pas dispo, on force un fallback déterministe V5.
        # L'objectif est de garder les prefilters V5/V6 actifs même si SetFit est indisponible.
        try:
            if _MODEL_VERSION is None:
                _MODEL_VERSION = "V5"
        except Exception:
            _MODEL_VERSION = "V5"
        logger.warning(f"[SETFIT][PREFILTER] SetFit indisponible, fallback _MODEL_VERSION=V5 (err={e})")

    print(f"\n🔥 [PREFILTER][DEBUG] message='{raw}' | _MODEL_VERSION={_MODEL_VERSION}")

    t_norm = _normalize_text_basic(raw)

    # V5: small-talk pur (salut + comment ça va) doit rester en REASSURANCE (Prompt A)
    # même si SetFit se trompe avec une confiance élevée.
    print(f"🔥 [PREFILTER][DEBUG] t_norm='{t_norm}'")
    try:
        print(f"🔥 [PREFILTER][DEBUG] Checking V5 block, _MODEL_VERSION={_MODEL_VERSION}")
        if _MODEL_VERSION == "V5" and (not is_media_url):
            smalltalk_markers = [
                "salut",
                "bonjour",
                "bonsoir",
                "coucou",
                "hello",
                "hey",
                "comment allez vous",
                "comment allez-vous",
                "comment ca va",
                "comment ça va",
                "ca va",
                "ça va",
                "la forme",
                "tout va bien",
                # Action #3: Ajouter merci/politesse au prefilter REASSURANCE
                "merci",
                "merci beaucoup",
                "ok merci",
                "grand merci",
                "de rien",
                "avec plaisir",
                "c'est gentil",
                "c est gentil",
                "super merci",
                "parfait merci",
                "ok parfait",
                "ok super",
                "ok d'accord",
                "ok d accord",
                "d'accord merci",
                "d accord merci",
                "bien recu",
                "bien reçu",
                "c'est note",
                "c est note",
                "c'est noté",
                "c est noté",
            ]
            has_smalltalk = any(k in t_norm for k in smalltalk_markers)

            # Si présence de verbes d'achat/produit/prix, ce n'est plus du small-talk pur.
            shopping_or_buy_markers = [
                "prix",
                "combien",
                "tarif",
                "coute",
                "coût",
                "cout",
                "dispo",
                "disponible",
                "stock",
                "rupture",
                "catalogue",
                "produit",
                "couche",
                "couches",
                "commander",
                "commande",
                "acheter",
                "payer",
                "livraison",
            ]
            has_shopping_or_buy = any(k in t_norm for k in shopping_or_buy_markers)

            print(f"🔥 [PREFILTER][V5] has_smalltalk={has_smalltalk} | has_shopping_or_buy={has_shopping_or_buy}")
            if has_smalltalk and not has_shopping_or_buy:
                print("🔥 [PREFILTER][V5] ✅ Small-talk pur détecté → REASSURANCE forcé")
                logger.info(
                    f"{Fore.GREEN}✅ [SETFIT][PREFILTER][V5_SMALLTALK] Détecté: small-talk pur sans signal achat → REASSURANCE forcé{Style.RESET_ALL}"
                )
                return "REASSURANCE", 0.98, {"prefilter": "v5_smalltalk_override"}
    except Exception:
        pass

    # ==========================================================================
    # PREFILTER V6 (V5): Paiement / Contact → REASSURANCE (Prompt A)
    # Objectif: éviter les conf=0.30 sur Wave/Orange/Mtn + demandes de numéro.
    # ==========================================================================
    if _MODEL_VERSION == "V5" and (not is_media_url):
        pay_keywords = [
            "wave",
            "orange",
            "mtn",
            "moov",
            "money",
            "especes",
            "espèces",
            "payer",
            "paie",
            "paiement",
            "versement",
            "depot",
            "dépôt",
            "acceptez",
        ]
        if any(k in t_norm for k in pay_keywords):
            print("🔥 [PREFILTER][V6_PAIEMENT] ✅ Paiement détecté → REASSURANCE forcé")
            logger.info(f"{Fore.GREEN}✅ [SETFIT][PREFILTER][V6_PAIEMENT] Paiement → REASSURANCE{Style.RESET_ALL}")
            return "REASSURANCE", 0.95, {"prefilter": "v6_paiement"}

        contact_keywords = [
            "numero",
            "numéro",
            "appeler",
            "appel",
            "contact",
            "coordonnees",
            "coordonnées",
            "joindre",
            "joignable",
            "telephone",
            "téléphone",
            "tel",
            "whatsapp",
        ]
        has_contact_kw = any(k in t_norm for k in contact_keywords)
        has_ci_07 = ("07" in t_norm) and any(k in t_norm for k in ["ton", "votre", "numero", "numéro"])
        if has_contact_kw or has_ci_07:
            print("🔥 [PREFILTER][V6_CONTACT] ✅ Demande contact détectée → REASSURANCE forcé")
            logger.info(f"{Fore.GREEN}✅ [SETFIT][PREFILTER][V6_CONTACT] Contact → REASSURANCE{Style.RESET_ALL}")
            return "REASSURANCE", 0.93, {"prefilter": "v6_contact"}

    # ==========================================================================
    # PREFILTER V6 (V5): Tracking / Problèmes → SAV_SUIVI (Disjoncteur)
    # Objectif: escalade immédiate, éviter réponses IA risquées.
    # ==========================================================================
    if _MODEL_VERSION == "V5" and (not is_media_url):
        tracking_keywords = [
            "mon colis",
            "ma commande",
            "arrive quand",
            "a quel niveau",
            "à quel niveau",
            "au niveau",
            "quel niveau",
            "pas encore recu",
            "pas encore reçu",
            "retard",
        ]
        if any(k in t_norm for k in tracking_keywords):
            print("🔥 [PREFILTER][V6_TRACKING] ✅ Tracking détecté → SAV_SUIVI forcé")
            logger.info(f"{Fore.GREEN}✅ [SETFIT][PREFILTER][V6_TRACKING] Tracking → SAV_SUIVI{Style.RESET_ALL}")
            return "SAV_SUIVI", 0.97, {"prefilter": "v6_tracking"}

        probleme_keywords = [
            "abime",
            "abîmé",
            "casse",
            "cassé",
            "probleme",
            "problème",
            "defectueux",
            "défectueux",
            "endommage",
            "endommagé",
            "manque",
        ]
        if any(k in t_norm for k in probleme_keywords):
            print("🔥 [PREFILTER][V6_PROBLEME] ✅ Problème détecté → SAV_SUIVI forcé")
            logger.info(f"{Fore.GREEN}✅ [SETFIT][PREFILTER][V6_PROBLEME] Problème → SAV_SUIVI{Style.RESET_ALL}")
            return "SAV_SUIVI", 0.98, {"prefilter": "v6_probleme"}

    has_commande_existante_guard = any(
        [
            (("ou en est" in t_norm or "où en est" in t_norm) and "commande" in t_norm),
            "ma commande" in t_norm,
            (("mon colis" in t_norm) and any(k in t_norm for k in ["arrive quand", "a quel niveau", "au niveau", "quel niveau"])),
            "suivi" in t_norm,
            "livreur" in t_norm,
            "pas encore recu" in t_norm,
            "pas encore reçu" in t_norm,
        ]
    )
    if has_commande_existante_guard:
        intent = "SAV_SUIVI" if _MODEL_VERSION == "V5" else "COMMANDE_EXISTANTE"
        return intent, 0.97, {"prefilter": "guard_commande_existante_tracking"}

    has_paiement_modalites_guard = ("paiement" in t_norm) and any(
        k in t_norm for k in ["obligatoire", "autre", "options", "especes", "espece"]
    )
    if has_paiement_modalites_guard:
        intent = "REASSURANCE" if _MODEL_VERSION == "V5" else "PAIEMENT"
        return intent, 0.95, {"prefilter": "guard_paiement_modalites"}

    # OVERRIDE V5: Questions de localisation → REASSURANCE (IN-SCOPE, jamais TRANSMISSIONXXX)
    # Patterns: "où êtes-vous", "vous êtes où", "votre adresse", "vous situez où"
    location_patterns = [
        "ou etes vous",
        "où etes vous",
        "ou êtes vous",
        "où êtes vous",
        "vous etes ou",
        "vous êtes ou",
        "vous etes où",
        "vous êtes où",
        "vous etes situes ou",
        "vous etes situes où",
        "vous êtes situes ou",
        "vous êtes situes où",
        "vous etes situés ou",
        "vous etes situés où",
        "vous êtes situés ou",
        "vous êtes situés où",
        "vous etes situe ou",
        "vous etes situe où",
        "vous êtes situe ou",
        "vous êtes situe où",
        "vous etes situé ou",
        "vous etes situé où",
        "vous êtes situé ou",
        "vous êtes situé où",
        "vous etes située ou",
        "vous etes située où",
        "vous êtes située ou",
        "vous êtes située où",
        "ou se trouve",
        "où se trouve",
        "ou vous trouvez",
        "où vous trouvez",
        "vous situez ou",
        "vous situez où",
        "c'est ou",
        "c'est où",
        "votre adresse",
        "votre localisation",
        "votre boutique",
        "votre magasin",
        "votre emplacement",
        "vos locaux",
        "votre local",
        "votre position",
    ]
    
    has_location_question = any(pattern in t_norm for pattern in location_patterns)
    sav_context = [
        "commande",
        "colis",
        "livreur",
        "livraison",
        "suivi",
        "tracking",
        "arrive",
        "arrivé",
        "pas recu",
        "pas reçu",
        "retard",
        "expedie",
        "expédié",
    ]
    has_sav_context = any(kw in t_norm for kw in sav_context)
    words_count = len([w for w in t_norm.split() if w])
    
    # Vérifier aussi les patterns avec "?" (questions directes)
    if not has_location_question and "?" in raw:
        location_keywords = [
            "ou",
            "où",
            "adresse",
            "situé",
            "situe",
            "située",
            "situes",
            "situés",
            "situez",
            "trouve",
            "localisation",
            "emplacement",
            "position",
            "locaux",
        ]
        business_keywords = ["vous", "votre", "boutique", "magasin", "shop", "entreprise"]
        has_where = any(k in t_norm for k in location_keywords)
        has_business = any(k in t_norm for k in business_keywords)
        if has_where and has_business:
            has_location_question = True
    
    if has_location_question and (not has_sav_context) and words_count <= 10:
        # V5: REASSURANCE, V4: INFO_GENERALE
        intent_label = "REASSURANCE" if _MODEL_VERSION == "V5" else "INFO_GENERALE"
        return intent_label, 0.95, {"prefilter": "location_question_override", "v5_override": True}

    # Horaires / ouverture (doit router vers Prompt A, pas clarification)
    horaires_markers = [
        "horaire",
        "horaires",
        "ouvert",
        "ouverte",
        "ouvrez",
        "ouvrez-vous",
        "fermez",
        "fermeture",
        "dimanche",
        "aujourd",
        "24h",
        "24 h",
        "7j",
        "7 j",
        "7/7",
        "7j/7",
        "7 j/7",
        "7jours",
        "7 jours",
        "7 jours sur 7",
    ]
    if any(k in t_norm for k in horaires_markers):
        # Éviter de capturer les demandes purement livraison (traitées ailleurs)
        if not any(k in t_norm for k in ["livraison", "livrer", "livrez", "livré", "delai", "délai"]):
            intent = "REASSURANCE" if _MODEL_VERSION == "V5" else "INFO_GENERALE"
            return intent, 0.90, {"prefilter": "lexical_horaires"}
        acquisition_question_patterns = [
            "comment commander",
            "comment passer commande",
            "comment faire pour commander",
            "comment ça se passe pour commander",
            "comment ca se passe pour commander",
            "ça se passe comment pour commander",
            "ca se passe comment pour commander",
            "je fais comment pour commander",
            "pour commander c'est comment",
            "pour commander c est comment",
        ]
        if any(p in t_norm for p in acquisition_question_patterns):
            print("🔥 [PREFILTER][V5_ACQUISITION_QUESTION] ✅ Question 'comment commander' → ACQUISITION forcé")
            logger.info(
                f"{Fore.GREEN}✅ [SETFIT][PREFILTER][V5_ACQUISITION_QUESTION] Question 'comment commander' détectée → ACQUISITION{Style.RESET_ALL}"
            )
            return "ACQUISITION", 0.92, {"prefilter": "v5_acquisition_question"}

        # Verbes d'achat explicites
        achat_verbs_explicit = [
            "je veux commander",
            "je veux acheter",
            "je veux prendre",
            "je voudrais commander",
            "je voudrais acheter",
            "je voudrais prendre",
            "je commande",
            "je prends",
            "je prend",
            "j'achete",
            "j'achète",
            "j achete",
            "j achète",
            "passer commande",
            "faire une commande",
            "envoie-moi",
            "envoie moi",
            "envoyez-moi",
            "envoyez moi",
            "mets-moi",
            "mets moi",
            "mettez-moi",
            "mettez moi",
            "garde-moi",
            "garde moi",
            "gardez-moi",
            "gardez moi",
            "reserve-moi",
            "reserve moi",
            "réserve-moi",
            "réserve moi",
            "reservez-moi",
            "reservez moi",
            "réservez-moi",
            "réservez moi",
            "j'en veux",
            "j en veux",
            "j'en prends",
            "j en prends",
        ]
        
        # Verbes d'achat simples (nécessitent contexte produit/quantité)
        achat_verbs_simple = [
            "je veux",
            "je voudrais",
            "commander",
            "commande",
            "acheter",
            "prendre",
            "reserver",
            "réserver",
        ]
        
        qty_markers = [
            "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
            "un", "une", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix",
            "quelques", "plusieurs", "des",
        ]
        pack_markers = ["paquet", "paquets", "pack", "packs", "carton", "cartons", "boite", "boîte", "boites", "boîtes"]
        product_markers = ["couche", "couches", "culotte", "culottes", "produit", "produits", "article", "articles"]
        
        # Questions générales à exclure ("comment commander" = question, pas achat)
        question_markers = ["comment", "quoi", "quel", "quelle", "quels", "quelles", "est-ce que", "est ce que", "c'est quoi", "c est quoi"]
        has_question = any(q in t_norm for q in question_markers)
        
        # Cas 1: Verbe d'achat explicite (ex: "je veux commander") → ACQUISITION direct
        has_explicit_achat = any(v in t_norm for v in achat_verbs_explicit)
        if has_explicit_achat and not has_question:
            print("🔥 [PREFILTER][V5_ACQUISITION] ✅ Verbe achat explicite → ACQUISITION forcé")
            logger.info(f"{Fore.GREEN}✅ [SETFIT][PREFILTER][V5_ACQUISITION] Verbe achat explicite détecté → ACQUISITION{Style.RESET_ALL}")
            return "ACQUISITION", 0.95, {"prefilter": "lexical_achat_explicit_v5"}
        
        # Cas 2: Verbe simple + produit/quantité (ex: "je veux 3 paquets de couches")
        has_simple_achat = any(v in t_norm for v in achat_verbs_simple)
        has_qty = any(q in t_norm.split() for q in qty_markers) or bool(re.search(r"\b\d+\b", t_norm))
        has_pack = any(p in t_norm for p in pack_markers)
        has_product = any(p in t_norm for p in product_markers)
        
        if has_simple_achat and not has_question:
            # Avec produit ET (quantité OU pack)
            if has_product and (has_qty or has_pack):
                print("🔥 [PREFILTER][V5_ACQUISITION] ✅ Verbe + produit + qty/pack → ACQUISITION forcé")
                logger.info(f"{Fore.GREEN}✅ [SETFIT][PREFILTER][V5_ACQUISITION] Verbe + produit + quantité → ACQUISITION{Style.RESET_ALL}")
                return "ACQUISITION", 0.92, {"prefilter": "lexical_achat_product_qty_v5"}
            # Avec juste quantité + pack (ex: "je veux 3 paquets")
            if has_qty and has_pack:
                print("🔥 [PREFILTER][V5_ACQUISITION] ✅ Verbe + qty + pack → ACQUISITION forcé")
                logger.info(f"{Fore.GREEN}✅ [SETFIT][PREFILTER][V5_ACQUISITION] Verbe + quantité + pack → ACQUISITION{Style.RESET_ALL}")
                return "ACQUISITION", 0.90, {"prefilter": "lexical_achat_qty_pack_v5"}

    # ==========================================================================
    # PREFILTER V5: Questions CATALOGUE/PRODUITS → SHOPPING (Prompt B)
    # Objectif: capturer "vous vendez quoi", "vous avez quoi", "catalogue", "marque".
    # ==========================================================================
    if _MODEL_VERSION == "V5" and (not is_media_url):
        catalogue_markers = [
            "catalogue",
            "catalogues",
            "produits",
            "produit",
            "articles",
            "article",
            "liste",
            "menu",
            "gamme",
            "collection",
            "qu'est-ce que vous avez",
            "qu est ce que vous avez",
            "vous avez quoi",
            "avez quoi",
            "montrez-moi",
            "montrez moi",
            "dites-moi",
            "dites moi",
            "vendez quoi",
            "vous vendez",
            "presentez",
            "présentez",
            "aimerais voir",
            "aimerais connaitre",
            "aimerais connaître",
            "en dire plus",
            "m'en dire plus",
            "m en dire plus",
        ]
        marque_markers = ["marque", "marques", "pampers", "huggies"]

        has_catalogue = any(marker in t_norm for marker in catalogue_markers)
        has_marque = any(marker in t_norm for marker in marque_markers)

        sav_context_catalogue = ["ma commande", "mon colis", "le livreur", "ma livraison", "mon livreur"]
        has_sav_catalogue = any(kw in t_norm for kw in sav_context_catalogue)

        if (has_catalogue or has_marque) and not has_sav_catalogue:
            print("🔥 [PREFILTER][V5_SHOPPING_CATALOGUE] ✅ Question catalogue → SHOPPING forcé")
            logger.info(f"{Fore.GREEN}✅ [SETFIT][PREFILTER][V5_SHOPPING_CATALOGUE] Question catalogue/marque → SHOPPING{Style.RESET_ALL}")
            return "SHOPPING", 0.92, {"prefilter": "v5_shopping_catalogue"}

    # ==========================================================================
    # PREFILTER V5: Questions LIVRAISON → REASSURANCE (Prompt A)
    # Objectif: capturer "vous livrez où", "frais de livraison", communes, délais.
    # ==========================================================================
    if _MODEL_VERSION == "V5" and (not is_media_url):
        livraison_markers = [
            "livrez",
            "livrer",
            "livraison",
            "livré",
            "livre",
            "vous livrez",
            "peut livrer",
            "livrez dans",
            "livrez à",
            "frais de livraison",
            "frais livraison",
            "se passe la livraison",
            "comment livraison",
            "delai",
            "délai",
        ]
        commune_markers = [
            "yopougon",
            "cocody",
            "abobo",
            "adjame",
            "adjamé",
            "marcory",
            "plateau",
            "treichville",
            "koumassi",
            "port-bouet",
            "port bouet",
            "zone",
            "commune",
            "quartier",
        ]

        has_livraison = any(marker in t_norm for marker in livraison_markers)
        has_commune = any(marker in t_norm for marker in commune_markers)

        sav_livraison = [
            "le livreur",
            "livreur est",
            "livreur ne",
            "ma livraison",
            "mon livreur",
            "pas encore recu",
            "pas encore reçu",
            "retard",
            "suivi",
        ]
        has_sav_livraison = any(kw in t_norm for kw in sav_livraison)

        if (has_livraison or (has_commune and "livr" in t_norm)) and not has_sav_livraison:
            print("🔥 [PREFILTER][V5_LIVRAISON] ✅ Question livraison → REASSURANCE forcé")
            logger.info(f"{Fore.GREEN}✅ [SETFIT][PREFILTER][V5_LIVRAISON] Question livraison → REASSURANCE{Style.RESET_ALL}")
            return "REASSURANCE", 0.92, {"prefilter": "v5_livraison"}

    # ==========================================================================
    # PREFILTER V5: ACQUISITION (questions "comment" + déclarations commande)
    # Objectif: capturer "comment passer commande", "comment acheter" + phrases type
    # "je passe commande" qui sont parfois mal classées.
    # ==========================================================================
    if _MODEL_VERSION == "V5" and (not is_media_url):
        comment_achat_patterns = [
            "comment commander",
            "comment passer commande",
            "comment acheter",
            "comment faire pour acheter",
            "comment pour commander",
            "comment je commande",
            "je vais prendre ça",
            "je vais prendre",
            "je passe commande",
            "je passe une commande",
            "je reviens pour commander",
            "je passe commander",
        ]
        has_comment_achat = any(pattern in t_norm for pattern in comment_achat_patterns)

        if has_comment_achat:
            print("🔥 [PREFILTER][V5_ACQUISITION_COMMENT] ✅ Intention achat → ACQUISITION forcé")
            logger.info(f"{Fore.GREEN}✅ [SETFIT][PREFILTER][V5_ACQUISITION_COMMENT] Comment/phrase achat → ACQUISITION{Style.RESET_ALL}")
            return "ACQUISITION", 0.92, {"prefilter": "v5_acquisition_comment"}

    # ==========================================================================
    # PREFILTER V5: Questions de PRIX → SHOPPING (Prompt B)
    # Objectif: capturer "combien", "prix", "tarif" avant SetFit
    # ==========================================================================
    if _MODEL_VERSION == "V5" and (not is_media_url):
        prix_markers = [
            "combien",
            "prix",
            "tarif",
            "coute",
            "coûte",
            "cout",
            "coût",
            "c'est à combien",
            "c est a combien",
            "ça coûte combien",
            "ca coute combien",
            "le prix",
            "quel prix",
            "prix de",
            "prix du",
            "prix des",
            "prix en gros",
            "prix gros",
            "tarif de",
            "tarif du",
            "tarif des",
            "promotion",
            "promotions",
            "promo",
            "promos",
            "réduction",
            "reduction",
            "réductions",
            "reductions",
            "remise",
            "remises",
            "offre",
            "offres",
        ]
        has_prix = any(p in t_norm for p in prix_markers)
        # Exclure les questions SAV (prix remboursement, etc.)
        sav_context_prix = ["remboursement", "rembourser", "réclamation", "reclamation", "retour"]
        has_sav_prix = any(s in t_norm for s in sav_context_prix)
        
        if has_prix and not has_sav_prix:
            print("🔥 [PREFILTER][V5_PRIX] ✅ Question prix détectée → SHOPPING forcé")
            logger.info(f"{Fore.GREEN}✅ [SETFIT][PREFILTER][V5_PRIX] Question prix → SHOPPING{Style.RESET_ALL}")
            return "SHOPPING", 0.92, {"prefilter": "lexical_prix_v5"}

    # ==========================================================================
    # PREFILTER V5: Questions de LOCALISATION étendu → REASSURANCE (Prompt A)
    # Objectif: capturer "quartier", "zone", "commune", "boutique", "point de vente"
    # ==========================================================================
    if _MODEL_VERSION == "V5" and (not is_media_url):
        localisation_markers = [
            "quartier",
            "zone",
            "commune",
            "secteur",
            "boutique",
            "magasin",
            "point de vente",
            "point vente",
            "showroom",
            "abidjan",
            "cocody",
            "yopougon",
            "marcory",
            "plateau",
            "treichville",
            "adjame",
            "adjamé",
            "abobo",
            "bingerville",
            "vous êtes où",
            "vous etes ou",
            "vous êtes situé",
            "vous etes situe",
            "c'est où",
            "c est ou",
            "en ligne seulement",
            "ligne seulement",
            "venir à la boutique",
            "venir a la boutique",
            "passer à la boutique",
            "passer a la boutique",
        ]
        has_localisation = any(loc in t_norm for loc in localisation_markers)
        # Exclure les questions de livraison (zone de livraison)
        livraison_context = ["livraison", "livrer", "livrez", "livré"]
        has_livraison_context = any(l in t_norm for l in livraison_context)
        
        if has_localisation and not has_livraison_context:
            print("🔥 [PREFILTER][V5_LOCALISATION] ✅ Question localisation détectée → REASSURANCE forcé")
            logger.info(f"{Fore.GREEN}✅ [SETFIT][PREFILTER][V5_LOCALISATION] Question localisation → REASSURANCE{Style.RESET_ALL}")
            return "REASSURANCE", 0.92, {"prefilter": "lexical_localisation_v5"}

    # Questions produit précises (doit router vers Prompt B, pas Prompt C)
    produit_markers = [
        "couche",
        "couches",
        "culotte",
        "taille",
        "tailles",
        "bébé",
        "bebe",
        "1 an",
        "un an",
        "12 mois",
        "dispo",
        "disponible",
        "stock",
        "rupture",
        "en rupture",
        "il en reste",
        "reste combien",
        "modèle",
        "modele",
        "modèles",
        "modeles",
    ]
    if any(k in t_norm for k in produit_markers):
        # V5: Attention à ne pas voler l'intent ACQUISITION ("je veux commander des couches")
        if _MODEL_VERSION == "V5":
            # Si intention de commande explicite, laisser SetFit gérer (ACQUISITION)
            acquisition_verbs = ["commander", "acheter", "prendre", "réserver", "reserver", "commande", "achat"]
            if any(v in t_norm for v in acquisition_verbs):
                pass # Laisser passer vers SetFit
            else:
                return "SHOPPING", 0.90, {"prefilter": "lexical_produit_v5"}
        else:
            return "PRODUIT_GLOBAL", 0.90, {"prefilter": "lexical_produit"}

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
            intent = "SAV_SUIVI" if _MODEL_VERSION == "V5" else "COMMANDE_EXISTANTE"
            return (
                intent,
                0.95,
                {
                    "prefilter": "human_handoff_sav_marker",
                    "human_handoff": True,
                    "human_handoff_reason": "SAV_RECLAMATION_OR_RETURN",
                },
            )

    phone_pattern = re.compile(r"\b(?:\+?225)?\s*(?:0[1-9])(?:[ .-]?\d){7,}\b")
    if phone_pattern.search(raw):
        intent = "ACQUISITION" if _MODEL_VERSION == "V5" else "CONTACT_COORDONNEES"
        return intent, 0.98, {"prefilter": "phone_regex"}

    exclusion_salut = [
        "merci",
        "gentil",
        "ok",
        "d'accord",
        "daccord",
        "top",
        "super",
        "bien reçu",
        "bien recu",
    ]

    def _assistant_recently_greeted(hist: str) -> bool:
        try:
            lines = [ln.strip() for ln in (hist or "").split("\n") if ln.strip()]
            tail = lines[-6:]
            tail_text = "\n".join(tail).lower()
            if "assistant:" not in tail_text:
                return False
            return any(k in tail_text for k in ["assistant: bonjour", "assistant: bonsoir", "assistant: salut", "assistant: hello"]) 
        except Exception:
            return False

    raw_lc = raw.lower()
    if (not is_media_url) and (should_skip_preprocessing(raw) or _looks_like_social_only(raw)):
        if any(w in raw_lc for w in exclusion_salut):
            return None, None, {}
        
        intent_salut = "REASSURANCE" if _MODEL_VERSION == "V5" else "SALUT"
        intent_info = "REASSURANCE" if _MODEL_VERSION == "V5" else "INFO_GENERALE"
        
        if _assistant_recently_greeted(conversation_history):
            return intent_info, 0.75, {"prefilter": "salut_repeat_degraded"}
        return intent_salut, 0.98, {"prefilter": "salut_rule"}

    try:
        processed = preprocess_for_routing(raw)
        if not processed and any(
            k in _normalize_text_basic(raw)
            for k in ["bonjour", "bonsoir", "salut", "hey", "hello", "yo", "wesh"]
        ):
            if is_media_url:
                return None, None, {}
            if any(w in raw_lc for w in exclusion_salut):
                return None, None, {}
            
            intent_salut = "REASSURANCE" if _MODEL_VERSION == "V5" else "SALUT"
            intent_info = "REASSURANCE" if _MODEL_VERSION == "V5" else "INFO_GENERALE"
            
            if _assistant_recently_greeted(conversation_history):
                return intent_info, 0.70, {"prefilter": "salut_empty_repeat_degraded"}
            return intent_salut, 0.90, {"prefilter": "salut_empty_after_preprocess"}
    except Exception:
        pass

    if _is_short_confirmation(raw):
        req = _infer_last_bot_request(conversation_history)
        if req == "tel":
            intent = "ACQUISITION" if _MODEL_VERSION == "V5" else "CONTACT_COORDONNEES"
            return intent, 0.85, {"prefilter": "short_confirm_after_tel_request"}
        if req == "zone":
            intent = "ACQUISITION" if _MODEL_VERSION == "V5" else "LIVRAISON"
            return intent, 0.75, {"prefilter": "short_confirm_after_zone_request"}
        if req == "paiement":
            intent = "ACQUISITION" if _MODEL_VERSION == "V5" else "PAIEMENT"
            return intent, 0.75, {"prefilter": "short_confirm_after_payment_request"}

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

            # V5: labels are poles directly, V4: map to legacy intents
            if _MODEL_VERSION == "V5":
                legacy_intent = label.upper()  # REASSURANCE, SHOPPING, etc.
                legacy_top2_intent = top2_label.upper()
                # V5: no guards needed (poles are stable)
                intent_after, conf_after, guard_applied, guard_reason = legacy_intent, conf, False, None
            else:
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
        # Action #1: V5 fallback vers REASSURANCE au lieu de CLARIFICATION
        fallback_intent = "REASSURANCE" if _MODEL_VERSION == "V5" else "CLARIFICATION"
        return fallback_intent, 0.30, {"router": "setfit", "reason": f"PREDICT_ERROR:{e}", "v5_fallback": _MODEL_VERSION == "V5"}

    if not variants:
        if _looks_like_social_only(raw):
            # V5: Retourne REASSURANCE au lieu de SALUT
            return_intent = "REASSURANCE" if _MODEL_VERSION == "V5" else "SALUT"
            return return_intent, 0.90, {"router": "setfit", "reason": "SOCIAL_ONLY_EMPTY_AFTER_PREPROCESS"}
        # Action #1: V5 fallback vers REASSURANCE au lieu de CLARIFICATION
        fallback_intent = "REASSURANCE" if _MODEL_VERSION == "V5" else "CLARIFICATION"
        return fallback_intent, 0.30, {"router": "setfit", "reason": "EMPTY_PROBS", "v5_fallback": _MODEL_VERSION == "V5"}

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
        "router_source": "setfit",
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

    # Action #1: V5 - si confiance < 0.5, forcer REASSURANCE au lieu de CLARIFICATION
    final_intent = str(chosen.get("intent_after_guard") or "")
    final_conf = float(chosen.get("confidence_after_guard") or 0.0)
    
    if _MODEL_VERSION == "V5":
        # Fallback sécurisé V5: si intent vide ou CLARIFICATION avec faible confiance
        if not final_intent or final_intent.upper() == "CLARIFICATION":
            final_intent = "REASSURANCE"
            final_conf = max(final_conf, 0.30)
            debug["v5_fallback_applied"] = True
            debug["v5_fallback_reason"] = "clarification_to_reassurance"
        # Si confiance très faible (<0.5), forcer REASSURANCE comme filet de sécurité
        elif final_conf < 0.5:
            debug["v5_low_conf_original_intent"] = final_intent
            debug["v5_low_conf_original_conf"] = final_conf
            final_intent = "REASSURANCE"
            final_conf = 0.30
            debug["v5_fallback_applied"] = True
            debug["v5_fallback_reason"] = "low_confidence_fallback"
    else:
        # V4: comportement legacy
        if not final_intent:
            final_intent = "CLARIFICATION"
    
    return final_intent, final_conf, debug


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
            debug["post_validation_reason"] = "SMALLTALK_TO_REASSURANCE"
            # V5: Retourne REASSURANCE au lieu de SALUT
            return_intent = "REASSURANCE" if _MODEL_VERSION == "V5" else "SALUT"
            return return_intent, min(conf, 0.75), debug

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
                "je commande",
                "je commande maintenant",
                "je passe commande",
                "je passe la commande",
                "je veux passer commande",
                "je prends",
                "passer commande",
                "passe commande",
                "envoie-moi",
                "envoie moi",
                "mets-moi",
                "mets moi",
                "je reviens pour commander",
                "commander maintenant",
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


def _apply_delivery_price_guard(*, message: str, intent: str, confidence: float) -> Tuple[str, float, Dict[str, Any]]:
    t = _normalize_text_basic(message)
    debug: Dict[str, Any] = {
        "delivery_price_guard_applied": False,
        "delivery_price_guard_reason": None,
    }

    if not t:
        return (intent or "CLARIFICATION"), float(confidence or 0.0), debug

    has_combien = "combien" in t
    has_delivery_anchor = any(k in t for k in ["livraison", "livrer", "frais", "frais de livraison", "livré", "delai", "délai"])

    if has_combien and has_delivery_anchor:
        debug["delivery_price_guard_applied"] = True
        debug["delivery_price_guard_reason"] = "COMBIEN_WITH_LIVRAISON_OR_FRAIS"
        return "LIVRAISON", max(float(confidence or 0.0), 0.80), debug

    return (intent or "CLARIFICATION"), float(confidence or 0.0), debug


def _get_human_required_intents_from_env() -> List[str]:
    raw = (os.getenv("HUMAN_REQUIRED_INTENTS", "COMMANDE_EXISTANTE,PRIX_PROMO") or "").strip()
    if not raw:
        return []
    return [x.strip().upper() for x in raw.split(",") if x.strip()]


def _get_human_bypass_intents_from_env() -> List[str]:
    # Intents/pôles qui doivent court-circuiter le LLM en mode coopératif.
    # Par défaut en V5: SAV_SUIVI (disjoncteur humain).
    raw = (os.getenv("HUMAN_BYPASS_INTENTS", "SAV_SUIVI") or "").strip()
    if not raw:
        return []
    return [x.strip().upper() for x in raw.split(",") if x.strip()]


def _message_requires_human_for_intent(*, intent: str, message: str) -> bool:
    upper_intent = (intent or "").upper().strip()
    if not upper_intent:
        return False

    required = set(_get_human_required_intents_from_env())
    if upper_intent not in required:
        return False

    if upper_intent == "PRODUIT_GLOBAL":
        t = _normalize_text_basic(message)
        stock_markers = [
            "dispo",
            "disponible",
            "rupture",
            "en rupture",
            "stock",
            "il en reste",
            "reste",
        ]
        return any(k in t for k in stock_markers)

    return True


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

    try:
        if _looks_like_media_url(original_message):
            st = state_compact or {}
            has_any_state = bool(
                st.get("photo_collected")
                or st.get("paiement_collected")
                or st.get("zone_collected")
                or st.get("tel_collected")
            )
            if has_any_state and (not bool(st.get("is_complete"))):
                forced_intent = "ACQUISITION"
                forced_conf = 0.98
                prefilter_debug = {
                    "prefilter": "media_url_force_acquisition",
                    "media_url": True,
                    "state_photo": bool(st.get("photo_collected")),
                    "state_paiement": bool(st.get("paiement_collected")),
                    "state_zone": bool(st.get("zone_collected")),
                    "state_tel": bool(st.get("tel_collected")),
                }
            else:
                forced_intent, forced_conf, prefilter_debug = _deterministic_prefilter(
                    message=original_message,
                    conversation_history=conversation_history or "",
                )
        else:
            forced_intent, forced_conf, prefilter_debug = _deterministic_prefilter(
                message=original_message,
                conversation_history=conversation_history or "",
            )
    except Exception:
        forced_intent, forced_conf, prefilter_debug = _deterministic_prefilter(
            message=original_message,
            conversation_history=conversation_history or "",
        )

    # 🔍 LOG COULEUR: Prefilter check
    if forced_intent:
        prefilter_name = prefilter_debug.get("prefilter", "unknown")
        logger.info(
            f"{Fore.GREEN}🔍 [SETFIT][PREFILTER] Activé: {prefilter_name} | intent={forced_intent} | conf={forced_conf:.3f}{Style.RESET_ALL}"
        )
    else:
        enable_emb_v65 = os.getenv("ENABLE_EMBEDDINGS_V65", "false").lower() == "true"
        if enable_emb_v65:
            logger.info(f"{Fore.CYAN}🔍 [SETFIT][PREFILTER] Aucun prefilter appliqué, passage à Layer 3 Embeddings{Style.RESET_ALL}")
        else:
            logger.info(f"{Fore.CYAN}🔍 [SETFIT][PREFILTER] Aucun prefilter appliqué, Embeddings V6.5 désactivé → passage SetFit ML{Style.RESET_ALL}")

    if forced_intent:
        intent = forced_intent
        conf = float(forced_conf or 0.0)
        prefilter_name = (prefilter_debug or {}).get("prefilter")
        routing_layer = "prefilter_v6" if isinstance(prefilter_name, str) and prefilter_name.lower().startswith("v6_") else "prefilter_v5"
        router_debug: Dict[str, Any] = {
            "router": "prefilter",
            "router_source": "setfit_prefilter",
            "routing_layer": routing_layer,
            **prefilter_debug,
        }
        if "prefilter" in prefilter_debug:
            router_debug["router_metrics.prefilter"] = prefilter_debug.get("prefilter")
        margin_val = 0.0
    else:
        # =====================================================================
        # LAYER 3 : Embeddings V6.5 (Filet de sécurité)
        # Activé uniquement si V6/V5 prefilters n'ont pas matché
        # Seuil conservateur : 0.75 min, 0.88 max
        # =====================================================================
        emb_intent, emb_conf, emb_proto, emb_debug = None, 0.0, None, {}
        enable_emb_v65 = os.getenv("ENABLE_EMBEDDINGS_V65", "false").lower() == "true"
        if enable_emb_v65:
            try:
                from core.embeddings_v6_5 import SemanticFilterV65, SuggestionLoggerV65

                # Lazy singleton pour éviter rechargement à chaque requête
                if not hasattr(route_botlive_intent, "_semantic_filter_v65"):
                    route_botlive_intent._semantic_filter_v65 = SemanticFilterV65()
                    route_botlive_intent._suggestion_logger_v65 = SuggestionLoggerV65()

                semantic_filter = route_botlive_intent._semantic_filter_v65
                suggestion_logger = route_botlive_intent._suggestion_logger_v65

                emb_intent, emb_conf, emb_proto, emb_debug = semantic_filter.detect(routed_message)

                if emb_intent and emb_conf >= 0.75:
                    logger.info(
                        f"{Fore.BLUE}🧠 [EMBEDDINGS_V6.5] Match: intent={emb_intent} | conf={emb_conf:.3f} | proto='{emb_proto[:40] if emb_proto else ''}...'{Style.RESET_ALL}"
                    )

                    # Log suggestion si confiance >= 0.82
                    if emb_conf >= 0.82 and emb_proto:
                        suggestion_logger.log_high_confidence_case(
                            message=routed_message,
                            intent=emb_intent,
                            similarity=emb_conf,
                            matched_prototype=emb_proto,
                            v6_checked=True,
                            v5_checked=True,
                        )
            except ImportError:
                # sentence-transformers non installé, Layer 3 désactivé
                pass
            except Exception as e:
                logger.warning(f"[EMBEDDINGS_V6.5] Erreur: {e}")
        
        # Si Layer 3 a matché avec confiance suffisante, utiliser son résultat
        if emb_intent and emb_conf >= 0.75:
            intent = emb_intent
            conf = emb_conf
            router_debug = {
                "router": "embeddings_v6_5",
                "router_source": "semantic_filter_v6_5",
                "routing_layer": "embeddings_v6_5",
                "embeddings_similarity": emb_conf,
                "embeddings_prototype": emb_proto,
                **emb_debug,
            }
            margin_val = 0.0
            
            logger.info(
                f"{Fore.BLUE}🧠 [EMBEDDINGS_V6.5] Utilisé comme fallback: intent={intent} | conf={conf:.3f}{Style.RESET_ALL}"
            )
        else:
            # LAYER 4 : SetFit ML (Fallback ultime)
            intent, conf, router_debug = _route_with_setfit(
                routed_message,
                conversation_history=conversation_history or "",
                state_compact=state_compact or {},
            )
            if isinstance(router_debug, dict) and not router_debug.get("routing_layer"):
                router_debug["routing_layer"] = "setfit"
            margin_val = float(router_debug.get("setfit_margin") or 0.0)
            _HYDE_MARGIN_HISTORY.append(margin_val)
            
            # 🔍 LOG COULEUR: SetFit prediction
            logger.info(
                f"{Fore.MAGENTA}🤖 [SETFIT][PREDICT] intent={intent} | conf={conf:.3f} | margin={margin_val:.3f} | version={_MODEL_VERSION}{Style.RESET_ALL}"
            )

        pf = router_debug.get("prefilter")
        if pf:
            router_debug["router_metrics.prefilter"] = pf

    # Post-validation (non destructif) + garde livraison/prix
    # ⚠️ IMPORTANT: Si le prefilter a forcé l'intent (V5), on NE PAS appeler _post_validate_intent
    # car il pourrait changer REASSURANCE en SALUT (label V4)
    upper_intent = (intent or "").upper().strip() or "CLARIFICATION"
    conf2, post_debug = conf, {}
    
    # Skip post-validation si prefilter V5 a déjà décidé
    prefilter_forced = bool(forced_intent and prefilter_debug.get("prefilter"))
    if prefilter_forced:
        print(f"🔥 [ROUTER][DEBUG] Prefilter a forcé intent={upper_intent}, skip post_validate_intent")
        post_debug = {"post_validation_skipped": True, "reason": "prefilter_forced"}
    else:
        try:
            intent2, conf2, post_debug = _post_validate_intent(
                intent=upper_intent,
                confidence=float(conf or 0.0),
                message=original_message,
                state_compact=state_compact or {},
            )
            upper_intent = (intent2 or "").upper().strip() or upper_intent
        except Exception as e:
            post_debug = {"post_validation": True, "post_validation_error": str(e)}

    try:
        intent3, conf3, delivery_debug = _apply_delivery_price_guard(
            message=original_message,
            intent=upper_intent,
            confidence=float(conf2 or 0.0),
        )
        upper_intent = (intent3 or "").upper().strip() or upper_intent
        conf2 = float(conf3 or conf2 or 0.0)
        post_debug.update(delivery_debug or {})
    except Exception:
        pass

    router_debug.update(post_debug)

    confidence = float(max(0.0, min(1.0, conf2)))
    intent_group = _map_intent_to_group(upper_intent)

    try:
        layer_used = (router_debug or {}).get("routing_layer") or (router_debug or {}).get("router") or "unknown"
        logger.info(
            "[ROUTER][LAYER] layer=%s intent=%s conf=%.3f",
            layer_used,
            upper_intent,
            confidence,
        )
    except Exception:
        pass

    collected_count = int((state_compact or {}).get("collected_count", 0) or 0)
    is_complete = bool((state_compact or {}).get("is_complete", False))
    mode = _determine_mode_from_intent(upper_intent, is_complete=is_complete, collected_count=collected_count)
    
    # 🔍 LOG COULEUR: Mode computation
    logger.info(
        f"{Fore.YELLOW}📋 [SETFIT][MODE] intent={upper_intent} → mode={mode} | complete={is_complete} | collected={collected_count}/5{Style.RESET_ALL}"
    )
    
    # Initialiser la liste missing_fields (ordre strict: photo → specs → zone → tel → paiement)
    missing = []
    if not (state_compact or {}).get("photo_collected", False):
        missing.append("photo")
    if not (state_compact or {}).get("specs_collected", False):
        missing.append("specs")
    if not (state_compact or {}).get("zone_collected", False):
        missing.append("zone")
    if not (state_compact or {}).get("tel_collected", False) or not (state_compact or {}).get("tel_valide", False):
        missing.append("tel")
    if not (state_compact or {}).get("paiement_collected", False):
        missing.append("paiement")

    debug = {
        "company_id": company_id,
        "user_id": user_id,
        "raw_message": message,
        "conversation_history_sample": conversation_history[-300:] if conversation_history else "",
        "model_version": _MODEL_VERSION or "UNKNOWN",
        "hyde_pre_used": hyde_pre_used,
        "hyde_pre_reason": hyde_pre_reason,
        "original_message": original_message,
        "routed_message": routed_message,
        **router_debug,
    }

    try:
        cooperative = _truthy_env("BOTLIVE_COOPERATIVE_HUMAN_MODE", "false")
        human_required = cooperative and _message_requires_human_for_intent(intent=upper_intent, message=original_message)
        debug["cooperative_mode"] = bool(cooperative)
        debug["human_required"] = bool(human_required)
        # Par défaut, bypass_llm est piloté par une liste dédiée (pas identique à human_required).
        bypass_intents = set(_get_human_bypass_intents_from_env())
        debug["bypass_llm"] = bool(cooperative and upper_intent in bypass_intents)
    except Exception:
        pass

    # V5 SEMI-AUTO: si SHOPPING, on notifie l'humain mais on laisse le LLM répondre via Prompt B.
    try:
        if _MODEL_VERSION == "V5" and upper_intent == "SHOPPING":
            if _truthy_env("BOTLIVE_SEMI_AUTO_SHOPPING_HANDOFF", "true"):
                debug["human_required"] = True
                debug.setdefault("handoff_reason", "semi_auto_shopping")
                debug["bypass_llm"] = False
    except Exception:
        pass

    return BotliveRoutingResult(
        intent=upper_intent,
        confidence=confidence,
        intent_group=intent_group,
        mode=mode,
        missing_fields=missing,
        state=state_compact or {},
        debug=debug,
    )
