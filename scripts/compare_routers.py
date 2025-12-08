#!/usr/bin/env python3
"""Compare Botlive Router V1 vs V2 on the 120 gold test cases.

Usage:
    python scripts/compare_routers.py

Prerequisites:
    - V1 router: core.botlive_intent_router.route_botlive_intent
    - V2 router: core.botlive_intent_router_v2.route_botlive_intent
    - 120 test cases: tests.production_test_cases.PRODUCTION_TEST_CASES

The script prints:
    - Global accuracy for V1 and V2
    - Per-label accuracy (GREETING, PRICE, DELIVERY_INFO, ...)
    - Counts of cases where V1 is correct and V2 is wrong (V1_only),
      and V2 is correct and V1 is wrong (V2_only), by label.
"""

from __future__ import annotations

import asyncio
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple


# Assurer que le projet racine est sur sys.path pour pouvoir importer `tests` et `core.*`
ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from tests.production_test_cases import PRODUCTION_TEST_CASES
from core.botlive_intent_router import route_botlive_intent as route_v1
from core.botlive_intent_router_v2 import route_botlive_intent as route_v2


@dataclass
class CaseResult:
    question: str
    label: str
    expected_intent_id: int
    v1_intent: str
    v2_intent: str


INTENT_LABEL_TO_CANONICAL: Dict[str, str] = {
    "GREETING": "SALUT",
    "INFO_GENERAL": "INFO_GENERALE",
    "PRODUCT_INFO": "RECHERCHE_PRODUIT",
    "PRICE": "PRIX_PROMO",
    "STOCK": "DISPONIBILITE",
    "ORDER_CREATE": "ACHAT_COMMANDE",
    # ORDER_MODIFY, DELIVERY_MODIFY n'ont pas d'intent dédié → on les mappe sur "CLARIFICATION"
    "ORDER_MODIFY": "CLARIFICATION",
    "DELIVERY_MODIFY": "CLARIFICATION",
    "PAYMENT": "PAIEMENT",
    "DELIVERY_INFO": "LIVRAISON",
    "TRACKING": "SUIVI",
}


async def _run_single_case(idx: int, question: str, label: str, expected_id: int) -> CaseResult:
    """Run both routers on a single test case."""

    state: Dict[str, Any] = {}

    res_v1 = await route_v1(
        company_id="test-company",
        user_id=f"user-{idx}",
        message=question,
        conversation_history="",
        state_compact=state,
    )

    res_v2 = await route_v2(
        company_id="test-company",
        user_id=f"user-{idx}",
        message=question,
        conversation_history="",
        state_compact=state,
    )

    return CaseResult(
        question=question,
        label=label,
        expected_intent_id=expected_id,
        v1_intent=res_v1.intent.upper(),
        v2_intent=res_v2.intent.upper(),
    )


async def _run_all_cases() -> List[CaseResult]:
    tasks = []
    for idx, (question, label, expected_id) in enumerate(PRODUCTION_TEST_CASES, start=1):
        tasks.append(_run_single_case(idx, question, label, expected_id))

    results = await asyncio.gather(*tasks)
    return list(results)


def _canonical_from_label(label: str) -> str:
    canon = INTENT_LABEL_TO_CANONICAL.get(label)
    if not canon:
        return "CLARIFICATION"
    return canon


def _compute_stats(results: List[CaseResult]) -> None:
    total = len(results)

    global_v1_correct = 0
    global_v2_correct = 0

    per_label_counts: Dict[str, int] = defaultdict(int)
    per_label_v1_correct: Dict[str, int] = defaultdict(int)
    per_label_v2_correct: Dict[str, int] = defaultdict(int)
    per_label_v1_only: Dict[str, int] = defaultdict(int)
    per_label_v2_only: Dict[str, int] = defaultdict(int)

    for r in results:
        canon = _canonical_from_label(r.label)
        per_label_counts[r.label] += 1

        v1_ok = r.v1_intent == canon
        v2_ok = r.v2_intent == canon

        if v1_ok:
            global_v1_correct += 1
            per_label_v1_correct[r.label] += 1
        if v2_ok:
            global_v2_correct += 1
            per_label_v2_correct[r.label] += 1

        if v1_ok and not v2_ok:
            per_label_v1_only[r.label] += 1
        if v2_ok and not v1_ok:
            per_label_v2_only[r.label] += 1

    print("==================================================")
    print("COMPARAISON ROUTER V1 vs V2 SUR 120 CAS GOLD")
    print("==================================================\n")

    print(f"Total cases: {total}")
    print(f"V1 accuracy: {global_v1_correct}/{total} = {global_v1_correct/total*100:.1f}%")
    print(f"V2 accuracy: {global_v2_correct}/{total} = {global_v2_correct/total*100:.1f}%\n")

    header = (
        f"{'Label':<15} {'N':>3}  "
        f"{'V1%':>6} {'V2%':>6}  "
        f"{'Δ(V2-V1)':>8}  "
        f"{'V1_only':>8} {'V2_only':>8}"
    )
    print(header)
    print("-" * len(header))

    for label in sorted(per_label_counts.keys()):
        n = per_label_counts[label]
        v1_c = per_label_v1_correct[label]
        v2_c = per_label_v2_correct[label]
        v1_acc = (v1_c / n * 100.0) if n else 0.0
        v2_acc = (v2_c / n * 100.0) if n else 0.0
        delta = v2_acc - v1_acc
        v1_only = per_label_v1_only[label]
        v2_only = per_label_v2_only[label]

        print(
            f"{label:<15} {n:>3}  "
            f"{v1_acc:>6.1f} {v2_acc:>6.1f}  "
            f"{delta:>8.1f}  "
            f"{v1_only:>8} {v2_only:>8}"
        )

    print("\nLégende:")
    print("  V1_only: cas où V1 est correct et V2 est faux")
    print("  V2_only: cas où V2 est correct et V1 est faux")


def main() -> None:
    results = asyncio.run(_run_all_cases())
    _compute_stats(results)


if __name__ == "__main__":
    main()
