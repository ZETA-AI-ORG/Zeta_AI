import logging
import os
from typing import Dict, Any, Optional
import re

logger = logging.getLogger(__name__)

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

    def _intent_to_group_letter(intent: str, mode_val: str) -> str:
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

    letter = forced_letter or _intent_to_group_letter(raw_intent, mode)
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
        "[BOTLIVE][PROMPT] Gating path=%s | confidence=%.2f | letter=%s",
        gating_path,
        confidence,
        letter,
    )

    reduced_template = ""
    used_light_block = False
    used_prompt_x_block = False

    # Prompt UNIQUE (si fourni dans Supabase) :
    # - utilisé pour tous les chemins hors PROMPT_X
    # - le mode (accueil/collecte) est géré par la checklist et le contenu du prompt.
    unique_block = _extract_block(base_prompt_template, "JESSICA_PROMPT_UNIQUE")
    unique_light_block = _extract_block(base_prompt_template, "JESSICA_PROMPT_LIGHT_UNIQUE")

    if gating_path == "prompt_x":
        x_block = _extract_block(base_prompt_template, "JESSICA_PROMPT_X")
        if x_block:
            logger.info("[BOTLIVE][PROMPT] Segment PROMPT_X sélectionné | confidence=%.2f", confidence)
            reduced_template = x_block
            used_prompt_x_block = True

    # Si le score impose PROMPT_X mais le bloc n'existe pas, ne pas dégrader vers A/B/C/D
    if gating_path == "prompt_x" and not reduced_template:
        logger.error(
            "[BOTLIVE][PROMPT] Bloc PROMPT_X manquant. Fallback sur prompt global complet."
        )
        reduced_template = base_prompt_template

    if not reduced_template and unique_block:
        if gating_path == "light" and unique_light_block:
            logger.info("[BOTLIVE][PROMPT] Segment UNIQUE LIGHT sélectionné | confidence=%.2f", confidence)
            reduced_template = unique_light_block
            used_light_block = True
            letter = "U"
        else:
            logger.info("[BOTLIVE][PROMPT] Segment UNIQUE sélectionné | confidence=%.2f", confidence)
            reduced_template = unique_block
            letter = "U"

    if not reduced_template:
        prompt_tag_letter = f"JESSICA_PROMPT_{letter}"
        letter_block = _extract_block(base_prompt_template, prompt_tag_letter)
        if letter_block:
            reduced_template = letter_block

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
    pay_ok = bool(state.get("paiement_collected"))
    zone_ok = bool(state.get("zone_collected"))
    tel_ok = bool(state.get("tel_collected") and state.get("tel_valide"))

    # Checklist humain compact (fallback si enriched_checklist vide)
    lines = ["📋 CHECKLIST HUMAIN (basé sur état Python):"]
    lines.append(f"- PHOTO PRODUIT : {_flag(photo_ok)}")
    lines.append(f"- ZONE LIVRAISON : {_flag(zone_ok)}")
    lines.append(f"- NUMÉRO TÉLÉPHONE : {_flag(tel_ok)}")
    lines.append(f"- PAIEMENT / ACOMPTE : {_flag(pay_ok)}")

    if missing_fields:
        lines.append("")
        lines.append("Champs à demander / vérifier en priorité :")
        for f in missing_fields:
            if f == "photo":
                lines.append("- PHOTO PRODUIT nette du pack ou du produit")
            elif f == "zone":
                lines.append("- ZONE DE LIVRAISON précise (quartier, commune)")
            elif f == "tel":
                lines.append("- NUMÉRO DE TÉLÉPHONE valide (format CI 10 chiffres)")
            elif f == "paiement":
                lines.append("- PREUVE DE PAIEMENT claire (capture ou reçu)")

    checklist_text = "\n".join(lines)

    # 3) Préparer les variables pour formatage
    question_text = (question_with_context or "").strip()
    history_text = (conversation_history or "").strip()
    summary_text = (resume_faits_saillants or "").strip()

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
        "detected_objects": detected_objects_str or "",
        "filtered_transactions": filtered_transactions_str or "[AUCUNE TRANSACTION VALIDE]",
        "expected_deposit": expected_deposit_str or "2000 FCFA",
        "checklist": enriched_checklist or checklist_text or "",
        "routing_score": f"{routing_conf:.2f}",
        "delai_message": delai_message or "",
        "routing_intent": raw_intent or "",
        "routing_confidence": f"{routing_conf:.2f}",
        "routing_group": letter or "",
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

    reduced_template_formatted: str
    try:
        reduced_template_formatted = base_prompt_template
        sanitized = re.sub(r"\{([^{}:]+):[^{}]+\}", r"{\1}", reduced_template)
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
        "segment_letter": letter,
        "confidence": confidence,
        "gating_path": gating_path,
    }
