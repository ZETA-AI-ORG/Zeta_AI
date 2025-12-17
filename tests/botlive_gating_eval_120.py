import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Tuple

# Assurer l'import des modules du projet
_THIS_DIR = os.path.dirname(__file__)
_ROOT_DIR = os.path.abspath(os.path.join(_THIS_DIR, ".."))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

# Forcer le mode routeur embeddings uniquement (pas d'appel LLM final Jessica)
os.environ.setdefault("BOTLIVE_ROUTER_EMBEDDINGS_ENABLED", "true")
os.environ.setdefault("BOTLIVE_V18_ENABLED", "false")
os.environ.setdefault("BOTLIVE_HYDE_PRE_ENABLED", "false")

from core.botlive_intent_router import route_botlive_intent
from core.jessica_prompt_segmenter import build_jessica_prompt_segment
from core.hyde_secour_x import run_hyde_secour_x
from database.supabase_client import get_botlive_prompt
from tests.production_test_cases import PRODUCTION_TEST_CASES


TEST_COMPANY_ID = "W27PwOPiblP8TlOrhPcjOtxd0cza"
TEST_USER_ID = "gating_eval_120"

# Questions supplémentaires volontairement floues / hors distribution
AMBIGUOUS_QUESTIONS: List[Tuple[str, str]] = [
    ("ok", "AMBIGU"),
    ("d'accord", "AMBIGU"),
    ("hein", "AMBIGU"),
    ("????", "AMBIGU"),
    ("je veux ça", "AMBIGU"),
    ("et demain ?", "AMBIGU"),
    ("et pour ça là", "AMBIGU"),
    ("c'est comment là-bas", "AMBIGU"),
    ("et sinon", "AMBIGU"),
    ("vous voyez non", "AMBIGU"),
]


async def run_gating_eval(limit: int | None = None) -> List[Dict[str, Any]]:
    cases = PRODUCTION_TEST_CASES if limit is None else PRODUCTION_TEST_CASES[:limit]

    # On ajoute ensuite les questions ambiguës
    extended_cases: List[Tuple[str, str]] = [(q, label) for (q, label, _id) in cases]
    extended_cases += AMBIGUOUS_QUESTIONS

    base_state = {
        "photo_collected": False,
        "paiement_collected": False,
        "zone_collected": False,
        "tel_collected": False,
        "tel_valide": False,
        "collected_count": 0,
        "is_complete": False,
    }

    results: List[Dict[str, Any]] = []

    print(f"\n================= BOTLIVE GATING EVAL ({len(cases)} + AMBIGUS) =================\n")

    # Charger le template une seule fois
    base_prompt_template = await get_botlive_prompt(TEST_COMPANY_ID)
    if not base_prompt_template:
        base_prompt_template = ""
        print("[PROMPT] Template Botlive indisponible → template vide (eval gating sans prompts Supabase)")
    else:
        print(f"[PROMPT] Template Botlive chargé (len={len(base_prompt_template)})")

    has_hyde_secour_x = (
        "[[HYDE_SECOUR_X_START]]" in base_prompt_template
        and "[[HYDE_SECOUR_X_END]]" in base_prompt_template
    )

    counts = {"light": 0, "standard": 0, "hyde": 0, "prompt_x": 0}

    for idx, (question, label) in enumerate(extended_cases, 1):
        routing = await route_botlive_intent(
            company_id=TEST_COMPANY_ID,
            user_id=TEST_USER_ID,
            message=question,
            conversation_history="",
            state_compact=base_state,
        )

        # Construire hyde_result pour le segmenter Jessica
        hyde_result = {
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

        segment = build_jessica_prompt_segment(
            base_prompt_template=base_prompt_template,
            hyde_result=hyde_result,
            question_with_context=question,
            conversation_history="",
            detected_objects_str="",
            filtered_transactions_str="[AUCUNE TRANSACTION VALIDE]",
            expected_deposit_str="2000 FCFA",
            enriched_checklist="[CHECKLIST TEST]",
            routing=routing,
        )

        gating_path = segment.get("gating_path", "standard")
        letter = segment.get("segment_letter")
        used_light = segment.get("used_light")
        used_prompt_x = segment.get("used_prompt_x")
        confidence = float(segment.get("confidence") or 0.0)

        if gating_path in counts:
            counts[gating_path] += 1

        print(
            f"[{idx:03d}] score={confidence:.3f} | gating={gating_path:<8} | letter={letter} | "
            f"intent={routing.intent:<15} | mode={routing.mode:<14} | label={label:<9} | q={question}"
        )

        entry: Dict[str, Any] = {
            "index": idx,
            "question": question,
            "label": label,
            "router": {
                "intent_internal": routing.intent,
                "mode": routing.mode,
                "missing_fields": routing.missing_fields,
                "confidence": confidence,
                "state": routing.state,
            },
            "segment": {
                "gating_path": gating_path,
                "segment_letter": letter,
                "used_light": used_light,
                "used_prompt_x": used_prompt_x,
            },
        }

        # Si HYDE doit intervenir, on teste aussi HYDE SECOUR X
        if gating_path == "hyde" and has_hyde_secour_x:
            try:
                hyde_raw = await run_hyde_secour_x(
                    base_prompt_template=base_prompt_template,
                    question=question,
                    conversation_history="",
                    checklist=routing.state,
                    state=routing.state,
                    intent=routing.intent,
                    confidence=routing.confidence,
                    mode=routing.mode,
                    missing_fields=routing.missing_fields,
                    detected_objects="",
                    filtered_transactions="",
                    expected_deposit="2000",
                )
                entry["hyde_raw"] = hyde_raw
            except Exception as e:
                entry["hyde_error"] = str(e)
        elif gating_path == "hyde" and not has_hyde_secour_x:
            entry["hyde_error"] = "HYDE_SECOUR_X bloc absent du template (skip)"

        results.append(entry)

    print("\n================= RÉSUMÉ GATING =================")
    print(f"LIGHT   (>=0.90):      {counts['light']} questions")
    print(f"STANDARD(0.70-0.89):  {counts['standard']} questions")
    print(f"HYDE    (0.55-0.69):  {counts['hyde']} questions")
    print(f"PROMPT_X(<=0.55):     {counts['prompt_x']} questions")

    return results


async def main() -> None:
    os.makedirs(os.path.join(_ROOT_DIR, "results"), exist_ok=True)
    results = await run_gating_eval(limit=None)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(_ROOT_DIR, "results", f"botlive_gating_{len(results)}_{timestamp}.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n=== GATING BATCH TERMINÉ ===")
    print(f"Fichier JSON généré: {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
