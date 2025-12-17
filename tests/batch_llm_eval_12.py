import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

# Assurer l'import des modules du projet
_THIS_DIR = os.path.dirname(__file__)
_ROOT_DIR = os.path.abspath(os.path.join(_THIS_DIR, ".."))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

os.environ.setdefault("BOTLIVE_ROUTER_EMBEDDINGS_ENABLED", "true")
os.environ.setdefault("BOTLIVE_V18_ENABLED", "false")

from core.botlive_intent_router import route_botlive_intent
from core.jessica_prompt_segmenter import build_jessica_prompt_segment
from database.supabase_client import get_botlive_prompt
from core.llm_health_check import complete as llm_complete
from tests.production_test_cases import PRODUCTION_TEST_CASES

TEST_COMPANY_ID = "W27PwOPiblP8TlOrhPcjOtxd0cza"
TEST_USER_ID = "botlive_llm_eval_12"


def _intent_to_group_letter(intent: str, mode_val: str) -> str:
    intent = (intent or "").upper()
    mode_val = (mode_val or "").upper()
    group_a = {"SALUT", "INFO_GENERALE", "CLARIFICATION"}
    group_b = {"PRODUIT_GLOBAL", "PRIX_PROMO"}
    group_c = {"ACHAT_COMMANDE", "LIVRAISON", "PAIEMENT", "CONTACT_COORDONNEES"}
    group_d = {"COMMANDE_EXISTANTE", "PROBLEME"}

    if intent in group_a:
        return "A"
    if intent in group_b:
        return "B"
    if intent in group_c:
        return "C"
    if intent in group_d:
        return "D"

    if mode_val == "COMMANDE":
        return "C"
    if mode_val == "RECEPTION_SAV":
        return "D"
    return "A"


def _extract_xml_parts(llm_text: str) -> Dict[str, Any]:
    import re

    if not llm_text:
        return {"thinking": None, "answer": None}

    thinking = None
    answer = None

    thinking_match = re.search(r"<thinking>(.*?)</thinking>", llm_text, re.DOTALL)
    if thinking_match:
        thinking = thinking_match.group(1).strip()

    response_match = re.search(r"<response>(.*?)</response>", llm_text, re.DOTALL)
    if response_match:
        body = response_match.group(1)
        ans_match = re.search(r"<answer>(.*?)</answer>", body or "", re.DOTALL)
        if ans_match and ans_match.group(1).strip():
            answer = ans_match.group(1).strip()
        else:
            answer = (body or "").strip()

    return {"thinking": thinking, "answer": answer}


def _is_valid_xml(llm_text: str) -> bool:
    import re
    if not llm_text:
        return False
    m = re.search(r"<response>(.*?)</response>", llm_text, re.DOTALL)
    if not m:
        return False
    body = m.group(1) or ""
    return bool(
        re.search(r"<thinking>.*?</thinking>", body, re.DOTALL)
        and re.search(r"<answer>.*?</answer>", body, re.DOTALL)
    )


async def run_batch(limit: int = 120) -> List[Dict[str, Any]]:
    # Prendre seulement les N premiers cas (par défaut: 120 = tous les cas de production)
    cases = PRODUCTION_TEST_CASES[:limit]

    # Charger et assainir le prompt Botlive pour éviter les format specifiers invalides
    raw_template = await get_botlive_prompt(TEST_COMPANY_ID)
    import re as _re
    # Supprimer les spécificateurs de format du type {var:...} -> {var}
    botlive_prompt_template = _re.sub(r"\{([^{}:]+):[^{}]+\}", r"{\1}", raw_template or "")

    results: List[Dict[str, Any]] = []

    base_state = {
        "photo_collected": False,
        "paiement_collected": False,
        "zone_collected": False,
        "tel_collected": False,
        "tel_valide": False,
        "collected_count": 0,
        "is_complete": False,
    }

    for idx, (question, expected_label, expected_id) in enumerate(cases, 1):
        print("\n" + "=" * 80)
        print(f"CASE {idx}/{len(cases)} - QUESTION: {question}")

        routing = await route_botlive_intent(
            company_id=TEST_COMPANY_ID,
            user_id=TEST_USER_ID,
            message=question,
            conversation_history="",
            state_compact=base_state,
        )

        segment_letter = _intent_to_group_letter(routing.intent, routing.mode)

        hyde_like_result = {
            "success": True,
            "intent": routing.intent,
            "confidence": routing.confidence,
            "mode": routing.mode,
            "missing_fields": routing.missing_fields,
            "state": routing.state,
            "raw": routing.debug.get("raw_message", ""),
            "token_info": {
                "source": "router_embeddings",
                "intent_score": routing.debug.get("intent_score"),
            },
        }

        try:
            print(f"ROUTER: score={float(routing.confidence):.3f} intent={routing.intent} mode={routing.mode}")
        except Exception:
            pass

        segment = build_jessica_prompt_segment(
            base_prompt_template=botlive_prompt_template,
            hyde_result=hyde_like_result,
            question_with_context=question,
            conversation_history="",
            detected_objects_str="",
            filtered_transactions_str="[AUCUNE TRANSACTION VALIDE]",
            expected_deposit_str="2000 FCFA",
            enriched_checklist="[CHECKLIST TEST]",
            routing=routing,
        )

        format_block = """

FORMAT DE RÉPONSE OBLIGATOIRE - NE PAS IGNORER

Tu DOIS ABSOLUMENT répondre en utilisant EXACTEMENT ce format XML STRICT (un seul bloc):

<response>
  <thinking>intent=[NOM_INTENT] | etat=[X/4] | action=[VERBE_ACTION]</thinking>
  <answer>[1-2 phrases en français]</answer>
</response>

RÈGLE ABSOLUE: Aucun texte en dehors des balises. Un seul bloc <response>.
"""

        prompt_to_use = segment["prompt"] + format_block

        llm_text, token_usage = await llm_complete(
            prompt_to_use,
            "llama-3.3-70b-versatile",
        )

        xml_parts = _extract_xml_parts(llm_text or "")

        used_light = bool(segment.get("used_light"))
        if used_light and not _is_valid_xml(llm_text or ""):
            hyde_like_result_base = dict(hyde_like_result)
            hyde_like_result_base["confidence"] = 0.0
            segment_base = build_jessica_prompt_segment(
                base_prompt_template=botlive_prompt_template,
                hyde_result=hyde_like_result_base,
                question_with_context=question,
                conversation_history="",
                detected_objects_str="",
                filtered_transactions_str="[AUCUNE TRANSACTION VALIDE]",
                expected_deposit_str="2000 FCFA",
                enriched_checklist="[CHECKLIST TEST]",
                routing=routing,
            )
            prompt_to_use = segment_base["prompt"] + format_block
            llm_text, token_usage = await llm_complete(
                prompt_to_use,
                "llama-3.3-70b-versatile",
            )
            xml_parts = _extract_xml_parts(llm_text or "")
            segment = segment_base

        prompt_tokens = token_usage.get("prompt_tokens", 0) or 0
        completion_tokens = token_usage.get("completion_tokens", 0) or 0
        total_tokens = token_usage.get("total_tokens", 0) or (prompt_tokens + completion_tokens)

        input_cost = prompt_tokens * 0.00000059
        output_cost = completion_tokens * 0.00000079
        total_cost = input_cost + output_cost

        result: Dict[str, Any] = {
            "index": idx,
            "question": question,
            "expected_label": expected_label,
            "expected_intent_id": expected_id,
            "router": {
                "intent_internal": routing.intent,
                "mode": routing.mode,
                "missing_fields": routing.missing_fields,
                "confidence": float(routing.confidence),
                "segment_letter": segment_letter,
            },
            "prompt": {
                "length_chars": len(prompt_to_use),
                "segment_excerpt": segment["prompt"][:300],
            },
            "llm": {
                "raw": llm_text,
                "thinking": xml_parts["thinking"],
                "answer": xml_parts["answer"],
            },
            "tokens": {
                "provider": token_usage.get("provider", "groq"),
                "model": token_usage.get("model", "llama-3.3-70b-versatile"),
                "health_check": token_usage.get("health_check", False),
                "fallback_used": token_usage.get("fallback_used", False),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "cost": {
                    "input": input_cost,
                    "output": output_cost,
                    "total": total_cost,
                },
            },
        }

        results.append(result)

    return results


async def main() -> None:
    os.makedirs(os.path.join(_ROOT_DIR, "results"), exist_ok=True)
    results = await run_batch(limit=120)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(_ROOT_DIR, "results", f"botlive_llm_eval_12_{timestamp}.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n=== BATCH TERMINÉ ===")
    print(f"Fichier JSON généré: {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
