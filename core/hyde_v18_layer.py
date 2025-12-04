import logging
import re
from typing import Dict, Any

from core.order_state_tracker import order_tracker

logger = logging.getLogger(__name__)


def _compute_missing_fields(state: Dict[str, Any]) -> list:
    """Calcule les champs manquants à partir de l'état Python.

    state attendu :
        {
            "photo_collected": bool,
            "paiement_collected": bool,
            "zone_collected": bool,
            "tel_collected": bool,
            "tel_valide": bool,
            "is_order_context": bool,
            "is_complete": bool,
            "collected_count": int,
        }
    """
    missing = []

    if not state.get("photo_collected", False):
        missing.append("photo")

    if not state.get("paiement_collected", False):
        missing.append("paiement")

    if not state.get("zone_collected", False):
        missing.append("zone")

    if not state.get("tel_collected", False) or not state.get("tel_valide", False):
        missing.append("tel")

    return missing


def _decide_mode(intent: str, state: Dict[str, Any]) -> str:
    """Décide le MODE Jessica à partir de l'intent HYDE + état.

    Retourne : "COMMANDE" | "GUIDEUR" | "RECEPTION_SAV"
    """
    collected_count = int(state.get("collected_count", 0))
    is_complete = bool(state.get("is_complete", False))
    is_order_context = bool(state.get("is_order_context", False))

    # RÈGLE #2: Commande complète → RECEPTION_SAV
    if is_complete:
        return "RECEPTION_SAV"

    # RÈGLE #5: Intent achat explicite → COMMANDE
    if intent == "INTENT_ACHAT":
        return "COMMANDE"

    # RÈGLE #4: Question info 0/4 sans contexte → RECEPTION_SAV
    if intent == "QUESTION_INFO" and collected_count == 0 and not is_order_context:
        return "RECEPTION_SAV"

    # Message flou/hors-piste EN CONTEXTE commande → GUIDEUR
    if intent in ["MESSAGE_FLOU", "HORS_PISTE"] and (is_order_context or collected_count >= 1):
        return "GUIDEUR"

    # Salutation 0/4 → RECEPTION_SAV
    if intent == "SALUTATION" and collected_count == 0:
        return "RECEPTION_SAV"

    # Suivi post-commande → RECEPTION_SAV
    if intent == "SUIVI_COMMANDE":
        return "RECEPTION_SAV"

    # DÉFAUT
    return "GUIDEUR" if collected_count >= 1 else "RECEPTION_SAV"


async def run_hyde_v18(company_id: str, user_id: str, message: str, conversation_history: str) -> Dict[str, Any]:
    """HYDE v18 parallèle : LLM → intent JSON, Python → mode + missing_fields.

    Cette fonction NE TOUCHE PAS au flux existant. Elle est conçue pour être
    appelée en parallèle (logs, métriques) lorsque le feature flag est activé.
    """
    from core.llm_client_groq import complete

    start_state = order_tracker.get_state(user_id)

    # Construire un état compact pour HYDE v18
    digits = "".join(ch for ch in (start_state.numero or "") if ch.isdigit()) if getattr(start_state, "numero", None) else ""
    tel_valide = len(digits) == 10

    state_compact: Dict[str, Any] = {
        "photo_collected": bool(getattr(start_state, "produit", None)),
        "paiement_collected": bool(getattr(start_state, "paiement", None)),
        "zone_collected": bool(getattr(start_state, "zone", None)),
        "tel_collected": bool(getattr(start_state, "numero", None)),
        "tel_valide": tel_valide,
    }
    collected_count = int(state_compact["photo_collected"]) + int(state_compact["paiement_collected"]) + int(state_compact["zone_collected"]) + int(state_compact["tel_collected"] and state_compact["tel_valide"])
    state_compact["collected_count"] = collected_count
    state_compact["is_complete"] = bool(getattr(start_state, "is_complete", lambda: False)()) if hasattr(start_state, "is_complete") else False

    lower_msg = (message or "").lower()
    is_order_context = any(k in lower_msg for k in [
        "photo", "paiement", "acompte", "zone", "livraison", "téléphone", "telephone", "numéro", "recap", "récap", "commande"
    ]) or collected_count > 0
    state_compact["is_order_context"] = is_order_context

    # Prompt HYDE v18 minimal (local, indépendant du prompt global)
    hyde_prompt = (
        "Tu es un routeur d'intention. "
        "Analyse le message client et renvoie UNIQUEMENT un objet JSON brut, "
        "sans ```json, sans texte avant ou après, sans explication.\n\n"
        "Format attendu :\n"
        "{\n"
        "  \"intent\": \"TYPE\",\n"
        "  \"confidence\": 0.0-1.0\n"
        "}\n\n"
        "TYPES POSSIBLES :\n"
        "- INTENT_ACHAT : veut commander (\"je veux commander\", \"j'ai besoin de couches\")\n"
        "- QUESTION_INFO : demande d'information (\"comment on paye ?\", \"vous livrez où ?\")\n"
        "- MESSAGE_FLOU : message peu clair (\"???\", \"ok\", \"hein\")\n"
        "- SALUTATION : politesse (\"bonjour\", \"merci\", \"salut\")\n"
        "- SUIVI_COMMANDE : suivi de commande (\"où est ma commande ?\")\n"
        "- HORS_PISTE : hors sujet (promos, marques, etc.)\n\n"
        f"MESSAGE_CLIENT : {message}\n"
        f"ETAT_CHECKLIST : {state_compact['collected_count']}/4 complété\n"
        f"HISTORIQUE_BRIEF : {conversation_history[:200]}\n"
        "\nNe renvoie STRICTEMENT que l'objet JSON décrit ci-dessus. Pas de balises, pas de ```json, pas de texte en plus."
    )

    logger.info("[BOTLIVE_V18][HYDE] Prompt longueur=%s chars", len(hyde_prompt))

    try:
        content, token_info = await complete(
            prompt=hyde_prompt,
            model_name="llama-3.3-70b-versatile",
            max_tokens=80,
            temperature=0.0,
            top_p=0.1,
        )
    except Exception as e:
        logger.error("[BOTLIVE_V18][HYDE] Erreur appel Groq: %s", e, exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "state": state_compact,
        }

    logger.info("[BOTLIVE_V18][HYDE] Réponse brute: %s", content[:300])

    import json as _json

    intent = "MESSAGE_FLOU"
    confidence = 0.5

    def _extract_json_object(text: str) -> str:
        """Tente d'extraire un objet JSON même si la réponse est entourée de ```json ... ``` ou de texte parasite."""
        s = (text or "").strip()

        # Cas 1 : réponse dans un bloc ```json ... ```
        if s.startswith("```"):
            lines = s.splitlines()
            body_lines = []
            for line in lines[1:]:
                if line.strip().startswith("```"):
                    break
                body_lines.append(line)
            s = "\n".join(body_lines).strip()

        # Cas 2 : essayer directement
        try:
            _json.loads(s)
            return s
        except Exception:
            pass

        # Cas 3 : extraire le premier bloc {...} via regex
        match = re.search(r"\{[\s\S]*\}", s)
        if match:
            candidate = match.group(0).strip()
            try:
                _json.loads(candidate)
                return candidate
            except Exception:
                pass

        # Fallback : renvoyer le texte brut pour logging / debug
        return s

    try:
        cleaned = _extract_json_object(content)
        data = _json.loads(cleaned)
        intent = str(data.get("intent") or "MESSAGE_FLOU").upper()
        confidence = float(data.get("confidence") or 0.5)
    except Exception as parse_err:
        logger.warning("[BOTLIVE_V18][HYDE] Erreur parsing JSON: %s | content=%s", parse_err, content[:300])

    missing_fields = _compute_missing_fields(state_compact)
    mode = _decide_mode(intent, state_compact)

    logger.info(
        "[BOTLIVE_V18][HYDE] intent=%s confidence=%.2f mode=%s missing=%s state=%s",
        intent,
        confidence,
        mode,
        missing_fields,
        state_compact,
    )

    return {
        "success": True,
        "intent": intent,
        "confidence": confidence,
        "mode": mode,
        "missing_fields": missing_fields,
        "state": state_compact,
        "raw": content,
        "token_info": token_info,
    }


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
    """Construit un prompt Jessica RÉDUIT à partir du prompt global.

    - Utilise les blocs [[JESSICA_COMMON_*]] + [[JESSICA_<MODE>_*]]
      où MODE ∈ {COMMANDE, GUIDEUR, RECEPTION_SAV} issu de HYDE v18.
    - Injecte un checklist humain basé sur missing_fields (Python).

    En cas de problème (balises manquantes, formatage), l'appelant doit
    gérer le fallback et réutiliser le prompt global complet.
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
        "[BOTLIVE_V18][PROMPT] Construction Jessica segmentée | mode=%s missing=%s",
        mode,
        missing_fields,
    )

    # 1) Extraire les blocs commun + spécifique MODE (comportement legacy HYDE v18)
    common_block = _extract_block(base_prompt_template, "JESSICA_COMMON")
    mode_tag = f"JESSICA_{mode}"
    mode_block = _extract_block(base_prompt_template, mode_tag)

    if not common_block and not mode_block:
        raise ValueError(
            f"Aucun bloc Jessica trouvé pour mode={mode} (balises [[JESSICA_COMMON_*]] / [[{mode_tag}_*]])"
        )

    fragments = []
    if common_block:
        fragments.append(common_block)
    if mode_block:
        fragments.append(mode_block)

    reduced_template = "\n\n".join(fragments)

    # 2) Construire un checklist humain compact
    lines = ["📋 CHECKLIST HUMAIN (basé sur état Python + HYDE):"]

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

    # 3) Préparer les variables pour formatage (mêmes noms que le prompt global)
    question_text = question_with_context or ""
    history_text = conversation_history or ""

    # Si le template réduit contient {context_text}, fournir une valeur neutre
    format_vars = {
        "question": question_text,
        "conversation_history": history_text,
        "detected_objects": detected_objects_str or "",
        "filtered_transactions": filtered_transactions_str or "[AUCUNE TRANSACTION VALIDE]",
        "expected_deposit": expected_deposit_str or "2000 FCFA",
        "checklist": checklist_text or enriched_checklist or "",
    }

    if "{context_text}" in reduced_template:
        format_vars["context_text"] = ""

    # 4) Formater le prompt réduit avec gestion d'erreur type .format
    try:
        prompt = reduced_template.format(**format_vars)
    except KeyError as ke:
        logger.warning("[BOTLIVE_V18][PROMPT] Variable manquante dans template réduit: %s", ke)
        prompt = reduced_template
        prompt = prompt.replace("{question}", question_text)
        prompt = prompt.replace("{conversation_history}", history_text)
        prompt = prompt.replace("{detected_objects}", format_vars["detected_objects"])
        prompt = prompt.replace("{filtered_transactions}", format_vars["filtered_transactions"])
        prompt = prompt.replace("{expected_deposit}", format_vars["expected_deposit"])
        prompt = prompt.replace("{checklist}", format_vars["checklist"])
        if "context_text" in prompt:
            prompt = prompt.replace("{context_text}", "")

    logger.info(
        "[BOTLIVE_V18][PROMPT] Prompt Jessica réduit construit | len=%s chars",
        len(prompt),
    )

    return {
        "prompt": prompt,
        "checklist_human": checklist_text,
        "mode": mode,
        "missing_fields": missing_fields,
        "state": state,
        "hyde": hyde_result,
    }
