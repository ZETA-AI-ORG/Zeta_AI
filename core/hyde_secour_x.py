from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _extract_block(template: str, tag: str) -> str:
    """Extrait un bloc délimité par [[TAG_START]] / [[TAG_END]]."""
    start_token = f"[[{tag}_START]]"
    end_token = f"[[{tag}_END]]"
    start = template.find(start_token)
    end = template.find(end_token)
    if start == -1 or end == -1 or end <= start:
        return ""
    return template[start + len(start_token) : end].strip()


def build_hyde_secour_x_prompt(
    base_prompt_template: str,
    *,
    question: str,
    conversation_history: str,
    checklist: str,
    state: Any,
    intent: str,
    confidence: float,
    mode: str,
    missing_fields: List[str] | None,
    detected_objects: str,
    filtered_transactions: str,
    expected_deposit: str,
) -> str:
    """Construit le prompt HYDE SECOUR X à partir du template Supabase.

    Le texte du prompt doit être présent dans le template sous les balises :
      [[HYDE_SECOUR_X_START]] ... [[HYDE_SECOUR_X_END]]
    """

    hyde_block = _extract_block(base_prompt_template, "HYDE_SECOUR_X")
    if not hyde_block:
        raise ValueError("Aucun bloc HYDE_SECOUR_X trouvé dans le template Supabase (balises [[HYDE_SECOUR_X_START]] / [[HYDE_SECOUR_X_END]]).")

    # Normalisation des valeurs complexes
    if not isinstance(checklist, str):
        try:
            checklist_str = json.dumps(checklist, ensure_ascii=False)
        except Exception:
            checklist_str = str(checklist)
    else:
        checklist_str = checklist

    if not isinstance(state, str):
        try:
            state_str = json.dumps(state, ensure_ascii=False)
        except Exception:
            state_str = str(state)
    else:
        state_str = state

    if missing_fields is None:
        missing_fields = []

    try:
        missing_fields_str = json.dumps(missing_fields, ensure_ascii=False)
    except Exception:
        missing_fields_str = str(missing_fields)

    format_vars: Dict[str, Any] = {
        "question": question or "",
        "conversation_history": conversation_history or "",
        "checklist": checklist_str or "",
        "state": state_str or "",
        "intent": intent or "",
        "confidence": confidence,
        "mode": mode or "",
        "missing_fields": missing_fields_str,
        "detected_objects": detected_objects or "",
        "filtered_transactions": filtered_transactions or "",
        "expected_deposit": expected_deposit or "",
        "hyde_question": question or "",
    }

    # Sanitize des placeholders de type {var:...} vers {var} pour éviter les ValueError
    sanitized = re.sub(r"\{([^{}:]+):[^{}]+\}", r"{\1}", hyde_block)

    try:
        prompt = sanitized.format(**format_vars)
    except (KeyError, ValueError, IndexError) as exc:
        logger.warning("[BOTLIVE][HYDE_X] Erreur de formatage template HYDE_SECOUR_X: %s", exc)
        # Fallback simple : remplacements manuels des variables principales
        prompt = sanitized
        prompt = prompt.replace("{question}", format_vars["question"])
        prompt = prompt.replace("{conversation_history}", format_vars["conversation_history"])
        prompt = prompt.replace("{checklist}", format_vars["checklist"])
        prompt = prompt.replace("{state}", format_vars["state"])
        prompt = prompt.replace("{intent}", format_vars["intent"])
        prompt = prompt.replace("{mode}", format_vars["mode"])
        prompt = prompt.replace("{missing_fields}", format_vars["missing_fields"])
        prompt = prompt.replace("{detected_objects}", format_vars["detected_objects"])
        prompt = prompt.replace("{filtered_transactions}", format_vars["filtered_transactions"])
        prompt = prompt.replace("{expected_deposit}", format_vars["expected_deposit"])
        prompt = prompt.replace("{hyde_question}", format_vars.get("hyde_question", ""))

    logger.info("[BOTLIVE][HYDE_X] Prompt HYDE SECOUR X construit | len=%s chars", len(prompt))
    return prompt


async def run_hyde_secour_x(
    base_prompt_template: str,
    *,
    question: str,
    conversation_history: str,
    checklist: Any,
    state: Any,
    intent: str,
    confidence: float,
    mode: str,
    missing_fields: List[str] | None,
    detected_objects: str,
    filtered_transactions: str,
    expected_deposit: str,
) -> str:
    """Construit le prompt HYDE SECOUR X et appelle Groq (llama-3.1-8b-instant).

    Hyperparamètres figés pour stabilité JSON:
      - temperature = 0.0
      - max_tokens = 100
    """

    from core.llm_client import complete as llm_complete
    import os

    prompt = build_hyde_secour_x_prompt(
        base_prompt_template=base_prompt_template,
        question=question,
        conversation_history=conversation_history,
        checklist=checklist,
        state=state,
        intent=intent,
        confidence=confidence,
        mode=mode,
        missing_fields=missing_fields,
        detected_objects=detected_objects,
        filtered_transactions=filtered_transactions,
        expected_deposit=expected_deposit,
    )

    model_name = os.getenv("BOTLIVE_HYDE_X_MODEL", "llama-3.3-70b-versatile")
    temperature = float(os.getenv("BOTLIVE_HYDE_X_TEMPERATURE", "0.1"))
    max_tokens = int(os.getenv("BOTLIVE_HYDE_X_MAX_TOKENS", "30"))
    top_p = float(os.getenv("BOTLIVE_HYDE_X_TOP_P", "0.9"))

    # Appel LLM HYDE_X (par défaut 70B)
    response_text = await llm_complete(
        prompt,
        model_name=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
    )

    logger.info("[BOTLIVE][HYDE_X] Réponse HYDE SECOUR X reçue | len=%s chars", len(response_text or ""))
    return response_text or ""
