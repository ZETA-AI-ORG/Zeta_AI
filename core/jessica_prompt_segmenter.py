import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def build_jessica_prompt_segment(
    base_prompt_template: str,
    hyde_result: Dict[str, Any],
    *,
    question_with_context: str,
    conversation_history: str,
    detected_objects_str: str,
    filtered_transactions_str: str,
    expected_deposit_str: str,
    enriched_checklist: str,
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

    # 1) Sélection du bloc de prompt: priorité aux nouveaux tags A/B/C/D
    raw_intent = str(hyde_result.get("intent") or "").upper()

    def _intent_to_group_letter(intent: str, mode_val: str) -> str:
        group_a = {"SALUT", "INFO_GENERALE", "CLARIFICATION"}
        group_b = {"CATALOGUE", "RECHERCHE_PRODUIT", "PRIX_PROMO", "DISPONIBILITE"}
        group_c = {"ACHAT_COMMANDE", "LIVRAISON", "PAIEMENT"}
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

    letter = _intent_to_group_letter(raw_intent, mode)
    prompt_tag_letter = f"JESSICA_PROMPT_{letter}"
    letter_block = _extract_block(base_prompt_template, prompt_tag_letter)

    if letter_block:
        reduced_template = letter_block
    else:
        # Fallback legacy: blocs commun + spécifique MODE
        common_block = _extract_block(base_prompt_template, "JESSICA_COMMON")
        mode_tag = f"JESSICA_{mode}"
        mode_block = _extract_block(base_prompt_template, mode_tag)

        if not common_block and not mode_block:
            raise ValueError(
                f"Aucun bloc Jessica trouvé pour intent={raw_intent} letter={letter} ni pour mode={mode} (balises [[{prompt_tag_letter}_*]] / [[JESSICA_COMMON_*]] / [[{mode_tag}_*]])"
            )

        fragments = []
        if common_block:
            fragments.append(common_block)
        if mode_block:
            fragments.append(mode_block)

        reduced_template = "\n\n".join(fragments)

    # 2) Construire un checklist humain compact
    lines = ["📋 CHECKLIST HUMAIN (basé sur état Python):"]

    def _flag(ok: bool) -> str:
        return "✅" if ok else "❌"

    state = hyde_result.get("state") or {}
    photo_ok = bool(state.get("photo_collected"))
    pay_ok = bool(state.get("paiement_collected"))
    zone_ok = bool(state.get("zone_collected"))
    tel_ok = bool(state.get("tel_collected") and state.get("tel_valide"))

    lines.append(f"- PHOTO PRODUIT : {_flag(photo_ok)}")
    lines.append(f"- PAIEMENT / ACOMPTE : {_flag(pay_ok)}")
    lines.append(f"- ZONE LIVRAISON : {_flag(zone_ok)}")
    lines.append(f"- NUMÉRO TÉLÉPHONE : {_flag(tel_ok)}")

    if missing_fields:
        lines.append("")
        lines.append("Champs à demander / vérifier en priorité :")
        for f in missing_fields:
            if f == "photo":
                lines.append("- PHOTO PRODUIT nette du pack ou du produit")
            elif f == "paiement":
                lines.append("- PREUVE DE PAIEMENT claire (capture ou reçu)")
            elif f == "zone":
                lines.append("- ZONE DE LIVRAISON précise (quartier, commune)")
            elif f == "tel":
                lines.append("- NUMÉRO DE TÉLÉPHONE valide (format CI 10 chiffres)")

    checklist_text = "\n".join(lines)

    # 3) Préparer les variables pour formatage
    question_text = question_with_context or ""
    history_text = conversation_history or ""

    format_vars = {
        "question": question_text,
        "conversation_history": history_text,
        "detected_objects": detected_objects_str or "",
        "filtered_transactions": filtered_transactions_str or "[AUCUNE TRANSACTION VALIDE]",
        "expected_deposit": expected_deposit_str or "2000 FCFA",
        "checklist": checklist_text or enriched_checklist or "",
    }

    reduced_template_formatted: str
    try:
        reduced_template_formatted = base_prompt_template  # just for type
        prompt = (reduced_template).format(**format_vars)
    except KeyError as ke:
        logger.warning("[BOTLIVE][PROMPT] Variable manquante dans template réduit: %s", ke)
        prompt = reduced_template
        prompt = prompt.replace("{question}", question_text)
        prompt = prompt.replace("{conversation_history}", history_text)
        prompt = prompt.replace("{detected_objects}", format_vars["detected_objects"])
        prompt = prompt.replace("{filtered_transactions}", format_vars["filtered_transactions"])
        prompt = prompt.replace("{expected_deposit}", format_vars["expected_deposit"])
        prompt = prompt.replace("{checklist}", format_vars["checklist"])

    logger.info("[BOTLIVE][PROMPT] Segment A/B/C/D construit | len=%s chars", len(prompt))

    return {
        "prompt": prompt,
        "checklist_human": checklist_text,
        "mode": mode,
        "missing_fields": missing_fields,
        "state": state,
        "hyde": hyde_result,
    }
