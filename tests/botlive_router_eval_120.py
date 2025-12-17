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

# Forcer le mode routeur embeddings uniquement (pas d'appel LLM)
os.environ.setdefault("BOTLIVE_ROUTER_EMBEDDINGS_ENABLED", "true")
os.environ.setdefault("BOTLIVE_V18_ENABLED", "false")
os.environ.setdefault("BOTLIVE_HYDE_PRE_ENABLED", "false")

from core.botlive_intent_router import route_botlive_intent
from tests.production_test_cases import PRODUCTION_TEST_CASES

TEST_COMPANY_ID = "W27PwOPiblP8TlOrhPcjOtxd0cza"
TEST_USER_ID = "router_only_eval_120"


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


async def run_router_only(limit: int | None = None) -> List[Dict[str, Any]]:
    cases = PRODUCTION_TEST_CASES if limit is None else PRODUCTION_TEST_CASES[:limit]

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

    print(f"\n================= ROUTER-ONLY EVAL ({len(cases)}) =================\n")

    for idx, (question, expected_label, expected_id) in enumerate(cases, 1):
        routing = await route_botlive_intent(
            company_id=TEST_COMPANY_ID,
            user_id=TEST_USER_ID,
            message=question,
            conversation_history="",
            state_compact=base_state,
        )

        letter = _intent_to_group_letter(routing.intent, routing.mode)
        score = float(routing.confidence or 0.0)

        print(
            f"[{idx:03d}] score={score:.3f} | intent={routing.intent:<15} | mode={routing.mode:<14} | letter={letter} | q={question}"
        )

        result: Dict[str, Any] = {
            "index": idx,
            "question": question,
            "expected_label": expected_label,
            "expected_intent_id": expected_id,
            "router": {
                "intent_internal": routing.intent,
                "mode": routing.mode,
                "missing_fields": routing.missing_fields,
                "confidence": score,
                "segment_letter": letter,
                "debug": routing.debug,
            },
        }
        results.append(result)

    high_90 = [r for r in results if r["router"]["confidence"] >= 0.90]
    mid_70_90 = [r for r in results if 0.70 <= r["router"]["confidence"] < 0.90]
    low_70 = [r for r in results if r["router"]["confidence"] < 0.70]

    print("\n================= RÉSUMÉ SCORES =================")
    print(f"High (>=0.90):  {len(high_90)} questions")
    print(f"Medium (0.70-0.90): {len(mid_70_90)} questions")
    print(f"Low (<0.70):    {len(low_70)} questions")

    return results


async def main() -> None:
    os.makedirs(os.path.join(_ROOT_DIR, "results"), exist_ok=True)
    results = await run_router_only(limit=None)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(_ROOT_DIR, "results", f"botlive_router_only_{len(results)}_{timestamp}.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n=== ROUTER BATCH TERMINÉ ===")
    print(f"Fichier JSON généré: {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
