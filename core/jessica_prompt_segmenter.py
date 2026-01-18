import logging
import os
import re
from typing import Any, Dict, List, Optional

from core.question_detector import QuestionDetector

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

_FRONTEND_TAXONOMY_TOKENS: Optional[set[str]] = None
_QUESTION_DETECTOR: Optional[QuestionDetector] = None


def _get_question_detector() -> QuestionDetector:
    global _QUESTION_DETECTOR
    if _QUESTION_DETECTOR is None:
        _QUESTION_DETECTOR = QuestionDetector()
    return _QUESTION_DETECTOR


def _truthy_env(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "y", "on"}


def _strip_accents_basic(text: str) -> str:
    t = (text or "")
    t = (
        t.replace("à", "a")
        .replace("â", "a")
        .replace("ä", "a")
        .replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("ë", "e")
        .replace("î", "i")
        .replace("ï", "i")
        .replace("ô", "o")
        .replace("ö", "o")
        .replace("ù", "u")
        .replace("û", "u")
        .replace("ü", "u")
        .replace("ç", "c")
    )
    return t


def _normalize_token(text: str) -> str:
    t = (text or "").strip().lower()
    t = _strip_accents_basic(t)
    t = re.sub(r"[^a-z0-9\s\-]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _extract_strings_from_ts_object(ts_source: str) -> List[str]:
    if not ts_source:
        return []
    return re.findall(r"\"([^\"\\]*(?:\\.[^\"\\]*)*)\"", ts_source)


def _load_frontend_taxonomy_tokens() -> set[str]:
    global _FRONTEND_TAXONOMY_TOKENS
    if _FRONTEND_TAXONOMY_TOKENS is not None:
        return _FRONTEND_TAXONOMY_TOKENS

    tokens: set[str] = set()
    if not _truthy_env("BOTLIVE_USE_FRONTEND_TAXONOMY", "true"):
        _FRONTEND_TAXONOMY_TOKENS = tokens
        return tokens

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    ts_path = os.path.join(base_dir, "frontend", "zeta-ai", "src", "data", "categories.ts")

    try:
        if os.path.exists(ts_path):
            with open(ts_path, "r", encoding="utf-8", errors="replace") as f:
                raw = f.read()
            strings = _extract_strings_from_ts_object(raw)
            for s in strings:
                norm = _normalize_token(s)
                if not norm:
                    continue
                tokens.add(norm)
                for chunk in re.split(r"\s*[-&/()]\s*", norm):
                    c = _normalize_token(chunk)
                    if c and len(c) >= 3:
                        tokens.add(c)

                words = [w for w in norm.split() if len(w) >= 3]
                for i in range(len(words)):
                    tokens.add(words[i])
                    if i + 1 < len(words):
                        tokens.add(f"{words[i]} {words[i+1]}")
                    if i + 2 < len(words):
                        tokens.add(f"{words[i]} {words[i+1]} {words[i+2]}")
        else:
            logger.warning("[SEGMENTER][TAXONOMY] categories.ts introuvable: %s", ts_path)
    except Exception as e:
        logger.warning("[SEGMENTER][TAXONOMY] Failed to load categories.ts: %s", e)

    _FRONTEND_TAXONOMY_TOKENS = tokens
    try:
        logger.info("[SEGMENTER][TAXONOMY] tokens=%s from_frontend=%s", len(tokens), bool(tokens))
    except Exception:
        pass
    return tokens

def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return float(default)
    try:
        return float(str(raw).strip())
    except Exception:
        return float(default)


BOTLIVE_PROMPT_LIGHT_THRESHOLD = _env_float("JESSICA_GATE_LIGHT_MIN", 0.90)
BOTLIVE_STANDARD_MIN = _env_float("JESSICA_GATE_STANDARD_MIN", 0.70)
BOTLIVE_HYDE_MIN = _env_float("JESSICA_GATE_HYDE_MIN", 0.55)
BOTLIVE_PROMPT_X_MAX = _env_float("JESSICA_GATE_PROMPTX_MAX", 0.55)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return bool(default)
    return str(raw).strip().lower() in {"1", "true", "yes", "y", "on"}

if not (0.0 <= BOTLIVE_PROMPT_X_MAX <= BOTLIVE_HYDE_MIN <= BOTLIVE_STANDARD_MIN <= BOTLIVE_PROMPT_LIGHT_THRESHOLD <= 1.0):
    BOTLIVE_PROMPT_LIGHT_THRESHOLD = 0.90
    BOTLIVE_STANDARD_MIN = 0.70
    BOTLIVE_HYDE_MIN = 0.55
    BOTLIVE_PROMPT_X_MAX = 0.55

def build_jessica_prompt_segment(
    base_prompt_template: str,
    hyde_result: Dict[str, Any],
    *,
    question_with_context: str,
    conversation_history: str,
    resume_faits_saillants: str = "",
    detected_objects_str: str,
    filtered_transactions_str: str,
    expected_deposit_str: str,
    enriched_checklist: str,
    routing: Optional[Dict[str, Any]] = None,
    delai_message: str = "",
) -> Dict[str, Any]:
    """Construit un prompt Jessica RÉDUIT en utilisant les nouveaux tags A/B/C/D.

    - Priorité: [[JESSICA_PROMPT_A/B/C/D_START]] ... [[..._END]]
    - Fallback legacy: [[JESSICA_COMMON_*]] + [[JESSICA_<MODE>_*]]
    - Injecte un checklist humain compact (état Python)
    """

    def _extract_block(template: str, tag: str) -> str:
        start_token = f"[[{tag}_START]]"
        end_token = f"[[{tag}_END]]"
        start = template.find(start_token)
        end = template.find(end_token)
        if start == -1 or end == -1 or end <= start:
            return ""
        return template[start + len(start_token) : end].strip()

    mode = str(hyde_result.get("mode") or "GUIDEUR").upper()
    missing_fields = list(hyde_result.get("missing_fields") or [])

    logger.info(
        "[BOTLIVE][PROMPT] Construction segment A/B/C/D | mode=%s missing=%s",
        mode,
        missing_fields,
    )

    # 1) Sélection du bloc de prompt: priorité au prompt UNIQUE si présent,
    # sinon fallback A/B/C/D legacy.
    raw_intent = str(hyde_result.get("intent") or "").upper()
    state_for_letter = hyde_result.get("state") or {}

    def _anti_fuite_override_letter(
        *,
        intent: str,
        confidence_val: float,
        message: str,
        history: str,
    ) -> Optional[str]:
        try:
            msg_lc = (message or "").strip().lower()
            hist_lc = (history or "").strip().lower()

            sav_keywords = [
                "reçu",
                "recu",
                "colis",
                "abîmé",
                "abime",
                "mauvais",
                "livreur",
                "problème",
                "probleme",
                "plainte",
                "remboursement",
                "retour",
                "échanger",
                "echanger",
            ]
            if (intent or "") == "COMMANDE_EXISTANTE" or any(w in msg_lc for w in sav_keywords):
                return "D"

            # INFOS & CONTACT: rester en A si pas de signal d'achat explicite
            if (intent or "") in {"CONTACT_COORDONNEES", "PRIX_PROMO", "LIVRAISON"}:
                buy_markers = ["commander", "acheter", "je prends", "je prend", "prends", "je veux", "payer"]
                if not any(w in msg_lc for w in buy_markers):
                    return "A"

            # VENTE: uniquement si intention claire d'achat
            achat_keywords = ["commander", "achat", "payer", "prix de gros", "combien pour", "je prends", "je prend"]
            if (intent or "") == "ACHAT_COMMANDE" and (
                float(confidence_val or 0.0) > 0.85 or any(w in msg_lc for w in achat_keywords)
            ):
                return "C"

            # Anti-répétition bonjour: si déjà salué récemment, ne pas retomber en A sur un faux SALUT
            if (intent or "") == "SALUT":
                try:
                    tail = "\n".join([ln.strip() for ln in hist_lc.split("\n") if ln.strip()][-6:])
                except Exception:
                    tail = hist_lc[-400:]
                if any(k in tail for k in ["assistant: bonjour", "assistant: bonsoir", "assistant: salut", "assistant: hello"]):
                    return "A"

            return None
        except Exception:
            return None

    def _is_continuation_of_payment_flow(*, message: str, history: str) -> bool:
        try:
            msg_lc = (message or "").strip().lower()

            # On verrouille uniquement si on est réellement en tunnel commande (paiement manquant).
            missing = [str(x or "").strip().lower() for x in (missing_fields or [])]
            only_payment_missing = (len(missing) == 1 and missing[0] == "paiement")
            if not only_payment_missing:
                return False

            # État compact attendu: photo/specs/zone/tel collectés.
            try:
                if not (
                    bool(state_for_letter.get("photo_collected"))
                    and bool(state_for_letter.get("specs_collected"))
                    and bool(state_for_letter.get("zone_collected"))
                    and bool(state_for_letter.get("tel_collected"))
                    and bool(state_for_letter.get("tel_valide"))
                    and not bool(state_for_letter.get("paiement_collected"))
                ):
                    return False
            except Exception:
                return False

            # Dernier message assistant: doit parler de dépôt/avance/Wave.
            hist_lc = (history or "").strip().lower()
            last_ai = ""
            try:
                for ln in reversed([l.strip() for l in hist_lc.split("\n") if l.strip()]):
                    if ln.startswith("assistant:") or ln.startswith("ia:") or ln.startswith("bot:"):
                        last_ai = ln
                        break
            except Exception:
                last_ai = hist_lc[-400:]

            payment_keywords = [
                "avance",
                "dépôt",
                "depot",
                "acompte",
                "engagement",
                "wave",
                "0787360757",
                "preuve",
                "capture",
            ]
            ai_talked_about_payment = bool(last_ai) and any(k in last_ai for k in payment_keywords)
            if not ai_talked_about_payment:
                return False

            # Question courte type "de combien ?".
            short_markers = [
                "combien",
                "de combien",
                "c'est combien",
                "quel montant",
                "montant",
                "minimum",
            ]
            is_short = (len((message or "").strip().split()) <= 5) and any(m in msg_lc for m in short_markers)
            if not is_short:
                return False

            logger.info("🔒 [SEGMENTER][LOCK] continuation_paiement=True → FORCE letter=C")
            return True
        except Exception:
            return False

    def _intent_to_group_letter(intent: str, mode_val: str, message_text: str = "") -> str:
        print(f"\n🔥 [SEGMENTER][DEBUG] _intent_to_group_letter(intent='{intent}', mode_val='{mode_val}')")

        if intent in {"REASSURANCE", "ACQUISITION", "SAV_SUIVI"}:
            letter = {
                "REASSURANCE": "A",
                "ACQUISITION": "C",
                "SAV_SUIVI": "D",
            }[intent]
            print(f"🔥 [SEGMENTER][V5] ✅ Mapping V5: {intent} → letter={letter}")
            logger.info(
                f"{Fore.CYAN}🔤 [SEGMENTER][V5_MAPPING] intent={intent} → letter={letter} (priorité V5){Style.RESET_ALL}"
            )
            return letter

        if intent == "SHOPPING":
            msg = (message_text or "").strip().lower()
            msg = re.sub(r"\s+", " ", msg)

            try:
                if _is_continuation_of_payment_flow(message=message_text or "", history=conversation_history or ""):
                    print("🔥 [SEGMENTER][LOCK] Continuation paiement détectée → letter=C")
                    return "C"
            except Exception:
                pass

            # Garde-fou commande: si le message ressemble à un détail de commande (taille/couleur/quantité)
            # on NE doit pas basculer vers le prompt B (semi-auto) mais rester en C.
            # Ce cas arrive typiquement après une photo produit validée.
            try:
                in_progress = bool(state_for_letter.get("photo_collected")) and not bool(state_for_letter.get("is_complete"))
                looks_like_specs = any(k in msg for k in [
                    "taille",
                    "pointure",
                    "couleur",
                    "quantite",
                    "quantité",
                    "j'en veux",
                    "j en veux",
                    "x",
                ]) and not any(k in msg for k in ["combien", "prix", "dispo", "disponible", "stock"])
                if in_progress and looks_like_specs:
                    print("🔥 [SEGMENTER][OVERRIDE] Détail commande détecté (SPECS) → letter=C")
                    return "C"
            except Exception:
                pass

            qd = _get_question_detector()
            q_analysis = qd.analyze(message_text or "")
            is_question = bool(q_analysis.get("is_question"))
            question_reason = str(q_analysis.get("question_reason") or "")
            is_prix = bool(q_analysis.get("is_prix"))
            is_stock = bool(q_analysis.get("is_stock"))
            is_carac = bool(q_analysis.get("is_caracteristiques"))
            is_info_technique = bool(q_analysis.get("is_info_technique"))

            prix_keywords = [
                "combien",
                "prix",
                "coute",
                "coûte",
                "tarif",
                "a combien",
                "à combien",
                "c'est combien",
                "quel est le prix",
                "ca fait combien",
                "ça fait combien",
                "prix de gros",
                "gros",
            ]
            stock_keywords = [
                "disponible",
                "dispo",
                "en stock",
                "stock",
                "reste",
                "encore",
                "toujours",
                "avez-vous",
                "avez vous",
                "vous avez",
                "y a",
                "il y a",
            ]
            carac_keywords = [
                "taille",
                "couleur",
                "marque",
                "âge",
                "age",
                "poids",
                "composition",
                "ingrédients",
                "ingredients",
                "caractéristiques",
                "caracteristiques",
                "c'est quoi",
                "difference",
                "différence",
                "quelle taille",
                "quel modele",
                "quel modèle",
                "quelle version",
            ]
            product_keywords_fallback = [
                "couche",
                "couches",
                "pampers",
                "huggies",
                "molfix",
                "culotte",
                "culottes",
                "lait",
                "savon",
                "shampoing",
                "pack",
            ]

            def _first_hit(keys: List[str]) -> Optional[str]:
                for k in keys:
                    if k and k in msg:
                        return k
                return None

            def _first_taxonomy_hit(message: str) -> Optional[str]:
                try:
                    tokens = _load_frontend_taxonomy_tokens()
                    if not tokens:
                        return None

                    norm_msg = _normalize_token(message)
                    if not norm_msg:
                        return None

                    words = [w for w in norm_msg.split() if len(w) >= 3]
                    if not words:
                        return None

                    max_words = int(os.getenv("BOTLIVE_TAXONOMY_NGRAM_WORDS", "36").strip() or "36")
                    if len(words) > max_words:
                        words = words[:max_words]

                    for i in range(len(words)):
                        g1 = words[i]
                        if g1 in tokens:
                            return g1
                        if i + 1 < len(words):
                            g2 = f"{words[i]} {words[i+1]}"
                            if g2 in tokens:
                                return g2
                        if i + 2 < len(words):
                            g3 = f"{words[i]} {words[i+1]} {words[i+2]}"
                            if g3 in tokens:
                                return g3
                    return None
                except Exception:
                    return None

            hit_product_fallback = _first_hit(product_keywords_fallback)
            hit_product_frontend = _first_taxonomy_hit(message_text or "")
            hit_product = hit_product_frontend or hit_product_fallback
            has_product = bool(hit_product)
            hit_prix = _first_hit(prix_keywords)
            hit_stock = _first_hit(stock_keywords)
            hit_carac = _first_hit(carac_keywords)

            if not is_prix:
                is_prix = bool(hit_prix)
            if not is_stock:
                is_stock = bool(hit_stock)
            if not is_carac:
                is_carac = bool(hit_carac)
            is_info_technique = bool(is_info_technique or is_prix or is_stock or is_carac)

            print(f"🔥 [SEGMENTER][SHOPPING] message='{(message_text or '')[:120]}'")
            print(
                f"🔥 [SEGMENTER][DETECT] has_product={has_product} keyword={hit_product} frontend={bool(hit_product_frontend)} fallback={bool(hit_product_fallback)}"
            )
            print(
                f"🔥 [SEGMENTER][QUESTION] is_question={is_question} reason={question_reason} is_prix={is_prix} is_stock={is_stock} is_carac={is_carac}"
            )
            print(f"🔥 [SEGMENTER][DETECT] is_prix_question={is_prix} keyword={hit_prix}")
            print(f"🔥 [SEGMENTER][DETECT] is_stock_question={is_stock} keyword={hit_stock}")
            print(f"🔥 [SEGMENTER][DETECT] is_caracteristiques_question={is_carac} keyword={hit_carac}")

            if is_info_technique:
                letter = "B"
                print("🔥 [SEGMENTER][DECISION] is_info_technique=True → letter=B")
                logger.info(
                    f"{Fore.CYAN}🔤 [SEGMENTER][V5_MAPPING] intent=SHOPPING → letter=B (info_technique){Style.RESET_ALL}"
                )
                return letter

            if has_product:
                letter = "C"
                print("🔥 [SEGMENTER][DECISION] has_product=True + no_tech_question → letter=C")
                logger.info(
                    f"{Fore.CYAN}🔤 [SEGMENTER][V5_MAPPING] intent=SHOPPING → letter=C (produit_sans_tech){Style.RESET_ALL}"
                )
                return letter

            letter = "B"
            print("🔥 [SEGMENTER][DECISION] default → letter=B")
            logger.info(
                f"{Fore.CYAN}🔤 [SEGMENTER][V5_MAPPING] intent=SHOPPING → letter=B (default){Style.RESET_ALL}"
            )
            return letter

        group_a = {"SALUT", "INFO_GENERALE", "CLARIFICATION"}
        group_b = {
            "PRODUIT_GLOBAL",
            "CATALOGUE",
            "RECHERCHE_PRODUIT",
            "PRIX_PROMO",
            "PRIX",
            "DISPONIBILITE",
            "STOCK",
            "DETAILS_PRODUIT",
        }
        group_c = {"ACHAT_COMMANDE", "LIVRAISON", "PAIEMENT", "CONTACT_COORDONNEES"}
        group_d = {"SUIVI", "PROBLEME"}

        if intent in group_a:
            return "A"
        if intent in group_b:
            return "B"
        if intent in group_c:
            return "C"
        if intent in group_d:
            return "D"

        # Compat HYDE v18 legacy
        hyde_a = {"SALUTATION", "QUESTION_INFO", "MESSAGE_FLOU", "HORS_PISTE"}
        hyde_c = {"INTENT_ACHAT"}
        hyde_d = {"SUIVI_COMMANDE"}
        if intent in hyde_a:
            return "A"
        if intent in hyde_c:
            return "C"
        if intent in hyde_d:
            return "D"

        # Fallback par mode si intent inconnu
        if mode_val == "COMMANDE":
            return "C"
        if mode_val == "RECEPTION_SAV":
            return "D"
        return "A"  # GUIDEUR par défaut → A

    confidence = float(hyde_result.get("confidence") or 0.0)
    forced_letter = _anti_fuite_override_letter(
        intent=raw_intent,
        confidence_val=confidence,
        message=question_with_context,
        history=conversation_history,
    )

    letter = forced_letter or _intent_to_group_letter(raw_intent, mode, question_with_context)
    gating_path = "standard"

    # Ranges attendues:
    # - confidence >= 0.90       -> "light"
    # - confidence < 0.55        -> "prompt_x"
    # - 0.55 <= confidence < 0.70 -> "hyde"
    # - sinon                     -> "standard" (prompts dynamiques A/B/C/D normaux)
    if confidence >= BOTLIVE_PROMPT_LIGHT_THRESHOLD:
        gating_path = "light"
    elif confidence <= BOTLIVE_PROMPT_X_MAX or confidence < BOTLIVE_HYDE_MIN:
        gating_path = "prompt_x"
    elif confidence < BOTLIVE_STANDARD_MIN:
        gating_path = "hyde"

    logger.info(
        f"{Fore.BLUE}🎯 [SEGMENTER][GATING] path={gating_path} | conf={confidence:.2f} | letter={letter} | intent={raw_intent}{Style.RESET_ALL}"
    )

    reduced_template = ""
    used_light_block = False
    used_prompt_x_block = False
    selected_letter = letter

    # IMPORTANT (V5): on ne doit PAS envoyer un prompt global (UNIQUE) si les blocs
    # A/B/C/D existent. Sinon la segmentation est contournée et les tokens explosent.
    # Le mode UNIQUE ne doit être activé que volontairement.
    allow_unique_prompt = _env_bool("BOTLIVE_JESSICA_USE_UNIQUE_PROMPT", False)

    unique_block = _extract_block(base_prompt_template, "JESSICA_PROMPT_UNIQUE")
    unique_light_block = _extract_block(base_prompt_template, "JESSICA_PROMPT_LIGHT_UNIQUE")

    # Si le template ne contient aucun tag de segmentation, on le traite comme un prompt UNIQUE implicite.
    # Ça évite des logs trompeurs (ex: prompt_used_key=JESSICA_PROMPT_C) et évite le fallback "erreur".
    try:
        has_any_segment_tag = "[[JESSICA_PROMPT_" in (base_prompt_template or "")
    except Exception:
        has_any_segment_tag = False

    if not has_any_segment_tag:
        reduced_template = base_prompt_template
        selected_letter = "U"
        logger.info("[BOTLIVE][PROMPT] Aucun tag de segmentation détecté. Mode UNIQUE implicite.")

    if gating_path == "prompt_x":
        x_block = _extract_block(base_prompt_template, "JESSICA_PROMPT_X")
        if x_block:
            logger.info("[BOTLIVE][PROMPT] Segment PROMPT_X sélectionné | confidence=%.2f", confidence)
            reduced_template = x_block
            used_prompt_x_block = True

    # Si le score impose PROMPT_X mais le bloc n'existe pas, NE PAS basculer sur le prompt global complet.
    # On revient sur le chemin standard A/B/C/D (et on garde l'intent->lettre) pour éviter l'explosion tokens.
    if gating_path == "prompt_x" and not reduced_template:
        logger.error(
            "[BOTLIVE][PROMPT] Bloc PROMPT_X manquant. Fallback vers segmentation standard A/B/C/D."
        )
        gating_path = "standard"

    # 1) PRIORITÉ: blocs A/B/C/D (ou LIGHT_A/B/C/D si gating light)
    if not reduced_template:
        if gating_path == "light":
            prompt_tag_letter = f"JESSICA_PROMPT_LIGHT_{letter}"
            letter_block = _extract_block(base_prompt_template, prompt_tag_letter)
            if letter_block:
                reduced_template = letter_block
                used_light_block = True
                logger.info(
                    f"{Fore.GREEN}✅ [SEGMENTER][PROMPT_SELECTED] JESSICA_PROMPT_LIGHT_{letter} | taille={len(letter_block)} chars{Style.RESET_ALL}"
                )
        if not reduced_template:
            prompt_tag_letter = f"JESSICA_PROMPT_{letter}"
            letter_block = _extract_block(base_prompt_template, prompt_tag_letter)
            if letter_block:
                reduced_template = letter_block

        # Si le bloc demandé n'existe pas, éviter le fallback global.
        # On préfère retomber sur A si disponible (cas fréquent: seul A est fourni).
        if not reduced_template and letter != "A":
            fallback_a_light = ""
            if gating_path == "light":
                fallback_a_light = _extract_block(base_prompt_template, "JESSICA_PROMPT_LIGHT_A")

            fallback_a = _extract_block(base_prompt_template, "JESSICA_PROMPT_A")
            if fallback_a_light:
                reduced_template = fallback_a_light
                used_light_block = True
                selected_letter = "A"
                logger.warning(
                    "[BOTLIVE][PROMPT] Bloc %s manquant. Fallback vers JESSICA_PROMPT_LIGHT_A.",
                    f"JESSICA_PROMPT_LIGHT_{letter}",
                )
            elif fallback_a:
                reduced_template = fallback_a
                selected_letter = "A"
                logger.warning(
                    "[BOTLIVE][PROMPT] Bloc %s manquant. Fallback vers JESSICA_PROMPT_A.",
                    f"JESSICA_PROMPT_{letter}",
                )

        # Sinon, tenter n'importe quel bloc A/B/C/D disponible avant legacy/global.
        if not reduced_template:
            for candidate in ["A", "B", "C", "D"]:
                tag = f"JESSICA_PROMPT_{candidate}"
                blk = _extract_block(base_prompt_template, tag)
                if blk:
                    reduced_template = blk
                    selected_letter = candidate
                    logger.warning(
                        "[BOTLIVE][PROMPT] Aucun bloc %s trouvé. Fallback vers %s.",
                        f"JESSICA_PROMPT_{letter}",
                        tag,
                    )
                    break

    # 2) UNIQUE seulement si explicitement autorisé (env) OU si A/B/C/D absent
    if not reduced_template and unique_block and allow_unique_prompt:
        if gating_path == "light" and unique_light_block:
            logger.info("[BOTLIVE][PROMPT] Segment UNIQUE LIGHT sélectionné | confidence=%.2f", confidence)
            reduced_template = unique_light_block
            used_light_block = True
            letter = "U"
            selected_letter = "U"
        else:
            logger.info("[BOTLIVE][PROMPT] Segment UNIQUE sélectionné | confidence=%.2f", confidence)
            reduced_template = unique_block
            letter = "U"
            selected_letter = "U"

    if not reduced_template:
        # Fallback legacy: blocs commun + spécifique MODE
        common_block = _extract_block(base_prompt_template, "JESSICA_COMMON")
        mode_tag = f"JESSICA_{mode}"
        mode_block = _extract_block(base_prompt_template, mode_tag)

        if not common_block and not mode_block:
            # Dernier recours : utiliser le prompt global complet fourni par Supabase
            logger.error(
                "[BOTLIVE][PROMPT] Aucun bloc Jessica trouvé pour intent=%s letter=%s mode=%s. Fallback sur le prompt global complet.",
                raw_intent,
                letter,
                mode,
            )
            reduced_template = base_prompt_template
        else:
            fragments = []
            if common_block:
                fragments.append(common_block)
            if mode_block:
                fragments.append(mode_block)

            reduced_template = "\n\n".join(fragments)

    # 2) Construire un état/checklist ultra-compact (économie tokens)
    def _flag(ok: bool) -> str:
        return "✅" if ok else "❌"

    state = hyde_result.get("state") or {}
    photo_ok = bool(state.get("photo_collected"))
    specs_ok = bool(state.get("specs_collected"))
    pay_ok = bool(state.get("paiement_collected"))
    zone_ok = bool(state.get("zone_collected"))
    tel_ok = bool(state.get("tel_collected") and state.get("tel_valide"))

    # Checklist humain compact (fallback si enriched_checklist vide)
    lines = ["📋 CHECKLIST HUMAIN (basé sur état Python):"]
    lines.append(f"- PHOTO PRODUIT : {_flag(photo_ok)}")
    lines.append(f"- SPECS (TAILLE/COULEUR/QUANTITÉ) : {_flag(specs_ok)}")
    lines.append(f"- ZONE LIVRAISON : {_flag(zone_ok)}")
    lines.append(f"- NUMÉRO TÉLÉPHONE : {_flag(tel_ok)}")
    lines.append(f"- PAIEMENT / ACOMPTE : {_flag(pay_ok)}")

    if missing_fields:
        lines.append("")
        lines.append("Champs à demander / vérifier en priorité :")
        for f in missing_fields:
            if f == "photo":
                lines.append("- PHOTO PRODUIT nette du pack ou du produit")
            elif f == "specs":
                lines.append("- SPECS: quantité + taille/couleur/pointure (si applicable)")
            elif f == "zone":
                lines.append("- ZONE DE LIVRAISON précise (quartier, commune)")
            elif f == "tel":
                lines.append("- NUMÉRO DE TÉLÉPHONE valide (format CI 10 chiffres)")
            elif f == "paiement":
                lines.append("- PREUVE DE PAIEMENT claire (capture ou reçu)")

    checklist_text = "\n".join(lines)

    def _looks_like_media_url(text: str) -> bool:
        try:
            t = (text or "").strip().lower()
            if not t.startswith("http"):
                return False
            media_ext = (".jpg", ".jpeg", ".png", ".webp", ".gif")
            if any(ext in t for ext in media_ext):
                return True
            if any(host in t for host in ["fbcdn.net", "scontent", "cloudfront", "cdn", "imgur"]):
                return True
            return False
        except Exception:
            return False

    def _build_checklist_system_state_from_state() -> str:
        try:
            def _sym(flag: bool) -> str:
                return "✅" if flag else "∅"

            # NEXT déterministe basé sur missing_fields
            next_step = "COLLECT_PHOTO"
            if missing_fields:
                first = str(missing_fields[0] or "").strip().lower()
                next_step = {
                    "photo": "COLLECT_PHOTO",
                    "specs": "COLLECT_SPECS",
                    "zone": "COLLECT_ZONE",
                    "tel": "COLLECT_TEL",
                    "paiement": "COLLECT_PAY",
                }.get(first, "COLLECT_PHOTO")

            return (
                "CHECKLIST_SYSTEM_STATE\n"
                f"PHOTO: {_sym(photo_ok)}\n"
                f"SPECS: {_sym(specs_ok)}\n"
                f"ZONE: {_sym(zone_ok)}\n"
                f"TEL: {_sym(tel_ok)}\n"
                f"PAY: {_sym(pay_ok)}\n"
                f"NEXT: {next_step}\n"
            )
        except Exception:
            return ""

    # 3) Préparer les variables pour formatage
    question_text = (question_with_context or "").strip()
    
    # [FIX] Injection Avertissement Gemini (Non-Produit)
    gemini_warning = ""
    try:
        detected_objs = hyde_result.get("detected_objects", []) or []
        for obj in detected_objs:
            if isinstance(obj, dict) and obj.get("source") == "gemini" and obj.get("is_product_image") is False:
                gemini_warning = "\n[ATTENTION SYSTEME: L'image reçue a été analysée par l'IA Vision. Ce N'EST PAS une photo de produit (probablement un texte, un reçu ou un selfie). NE VALIDE PAS LA PHOTO PRODUIT.]"
                break
    except Exception:
        pass

    if _looks_like_media_url(question_text):
        question_text = f"Envoi média : [IMAGE]{gemini_warning}"
    else:
        question_text += gemini_warning

    history_text = (conversation_history or "").strip()
    summary_text = (resume_faits_saillants or "").strip()

    # Extraire le dernier message assistant depuis l'historique (évite que le LLM "devine" son dernier tour).
    last_assistant_message = ""
    try:
        for ln in reversed([l.strip() for l in history_text.split("\n") if l.strip()]):
            if ln.lower().startswith("assistant:") or ln.lower().startswith("ia:") or ln.lower().startswith("bot:"):
                last_assistant_message = ln.split(":", 1)[-1].strip()
                break
    except Exception:
        last_assistant_message = ""

    media_tag = "[IMAGE/AUDIO]" if "[IMAGE" in question_text else ""

    try:
        routing_conf = float(
            (routing or {}).get("confidence")
            if isinstance(routing, dict)
            else (hyde_result.get("confidence") or 0.0)
        )
    except Exception:
        routing_conf = float(hyde_result.get("confidence") or 0.0)

    format_vars = {
        "question": question_text,
        "conversation_history": history_text,
        "resume_faits_saillants": summary_text,
        "last_assistant_message": last_assistant_message,
        "media_tag": media_tag,
        "detected_objects": detected_objects_str or "",
        "filtered_transactions": filtered_transactions_str or "[AUCUNE TRANSACTION VALIDE]",
        "expected_deposit": expected_deposit_str or "2000 FCFA",
        "checklist": enriched_checklist or checklist_text or "",
        "checklist_system_state": _build_checklist_system_state_from_state(),
        "completion_rate": str(state.get("collected_count") or state.get("completion_rate") or ""),
        "routing_score": f"{routing_conf:.2f}",
        "delai_message": delai_message or "",
        "routing_intent": raw_intent or "",
        "routing_confidence": f"{routing_conf:.2f}",
        "routing_group": selected_letter or "",
    }
    try:
        m = re.search(r"(\d+)", str(expected_deposit_str or ""))
        format_vars["expected_deposit_amount"] = m.group(1) if m else ""
    except Exception:
        format_vars["expected_deposit_amount"] = ""

    format_vars.setdefault(
        "routing_group_name",
        {
            "A": "INFO",
            "B": "PRODUIT",
            "C": "COMMANDE",
            "D": "SAV",
        }.get(letter or "", "INFO"),
    )


    # Prevents noisy KeyError warnings for unused variables like {dict}
    format_vars.setdefault("dict", "")
    # Defaults for occasional placeholders seen in remote templates
    format_vars.setdefault("salut", "")
    # Certains templates distants peuvent contenir {exp}
    format_vars.setdefault("exp", "")
    # Templates distants peuvent aussi contenir {prix}, {clarif} ou {technique}
    format_vars.setdefault("prix", "")
    format_vars.setdefault("clarif", "")
    format_vars.setdefault("technique", "")
    # Et parfois {info_ref}
    format_vars.setdefault("info_ref", "")
    if "{context_text}" in reduced_template:
        format_vars.setdefault("context_text", "")

    # Alias pour éviter les KeyError sur templates distants.
    # Certains templates utilisent {numero} et d'autres {numéro} (accent).
    format_vars.setdefault("numero", str(state.get("tel") or state.get("numero") or ""))
    format_vars.setdefault("commune", str(state.get("zone") or ""))

    reduced_template_formatted: str
    try:
        reduced_template_formatted = base_prompt_template
        # Normaliser les placeholders accentués les plus fréquents avant format()
        reduced_template_norm = reduced_template.replace("{numéro}", "{numero}")
        # Les templates Supabase peuvent contenir des "expressions" non supportées par str.format()
        # ex: {last_assistant_message if not media else "[IMAGE/AUDIO]"}
        reduced_template_norm = re.sub(
            r"\{last_assistant_message[^{}]*\}",
            "{last_assistant_message}",
            reduced_template_norm,
        )
        reduced_template_norm = reduced_template_norm.replace("{media}", "{media_tag}")
        sanitized = re.sub(r"\{([^{}:]+):[^{}]+\}", r"{\1}", reduced_template_norm)
        allowed_keys = set(format_vars.keys())

        def _escape_unknown_placeholder(m: re.Match[str]) -> str:
            key = (m.group(1) or "").strip()
            if key in allowed_keys:
                return m.group(0)
            return "{{" + key + "}}"

        sanitized_safe = re.sub(
            r"(?<!\{)\{([a-zA-Z_][a-zA-Z0-9_]*)\}(?!\})",
            _escape_unknown_placeholder,
            sanitized,
        )

        prompt = sanitized_safe.format(**format_vars)
    except (KeyError, ValueError) as ke:
        logger.warning("[BOTLIVE][PROMPT] Variable/format manquant dans template réduit: %s", ke)
        prompt = re.sub(r"\{([^{}:]+):[^{}]+\}", r"{\1}", reduced_template)
        prompt = prompt.replace("{question}", question_text)
        prompt = prompt.replace("{conversation_history}", history_text)
        prompt = prompt.replace("{resume_faits_saillants}", summary_text)
        prompt = prompt.replace("{detected_objects}", format_vars["detected_objects"])
        prompt = prompt.replace("{filtered_transactions}", format_vars["filtered_transactions"])
        prompt = prompt.replace("{expected_deposit}", format_vars["expected_deposit"])
        prompt = prompt.replace("{checklist}", format_vars["checklist"])
        prompt = prompt.replace("{exp}", format_vars.get("exp", ""))
        prompt = prompt.replace("{routing_score}", format_vars.get("routing_score", "0.0"))
        prompt = prompt.replace("{delai_message}", format_vars.get("delai_message", ""))

    logger.info("[BOTLIVE][PROMPT] Segment A/B/C/D construit | len=%s chars", len(prompt))

    return {
        "prompt": prompt,
        "checklist_human": checklist_text,
        "mode": mode,
        "missing_fields": missing_fields,
        "state": state,
        "hyde": hyde_result,
        "used_light": used_light_block,
        "used_prompt_x": used_prompt_x_block,
        "segment_letter": selected_letter,
        "confidence": confidence,
        "gating_path": gating_path,
    }
