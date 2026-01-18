from __future__ import annotations

import asyncio
import os
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

os.environ.setdefault("BOTLIVE_ROUTER_EMBEDDINGS_ENABLED", "false")
os.environ.setdefault("BOTLIVE_HYDE_PRE_ENABLED", "false")
os.environ.setdefault("BOTLIVE_EVAL_ENABLE_HYDE_PRE", "false")

from tests.production_test_cases import PRODUCTION_TEST_CASES
from core.setfit_intent_router import route_botlive_intent as route_terrain
from core.setfit_intent_router_academic import route_botlive_intent as route_academic


@dataclass
class Row:
    idx: int
    question: str
    expected_label: str
    expected_id: int


@dataclass
class ModeOut:
    intent: str
    confidence: float


def _expected_label_to_internal_intent(expected_label: str, expected_intent_id: int) -> str:
    label = (expected_label or "").strip().upper()

    mapping = {
        "GREETING": "SALUT",
        "INFO_GENERAL": "INFO_GENERALE",
        "CONTACT_COORDONNEES": "CONTACT_COORDONNEES",
        "PRODUCT_INFO": "PRODUIT_GLOBAL",
        "PRICE": "PRIX_PROMO",
        "STOCK": "PRODUIT_GLOBAL",
        "ORDER_CREATE": "ACHAT_COMMANDE",
        "ORDER_MODIFY": "COMMANDE_EXISTANTE",
        "PAYMENT": "PAIEMENT",
        "DELIVERY_INFO": "LIVRAISON",
        "DELIVERY_MODIFY": "LIVRAISON",
        "TRACKING": "COMMANDE_EXISTANTE",
        "PROBLEME": "COMMANDE_EXISTANTE",
    }

    if label in mapping:
        return mapping[label]

    id_map = {
        1: "SALUT",
        2: "INFO_GENERALE",
        3: "INFO_GENERALE",
        4: "PRODUIT_GLOBAL",
        5: "PRODUIT_GLOBAL",
        6: "PRIX_PROMO",
        7: "PRODUIT_GLOBAL",
        8: "ACHAT_COMMANDE",
        9: "LIVRAISON",
        10: "PAIEMENT",
        11: "COMMANDE_EXISTANTE",
        12: "COMMANDE_EXISTANTE",
        13: "CONTACT_COORDONNEES",
    }

    return id_map.get(int(expected_intent_id), "INFO_GENERALE")


async def _predict_one(
    *,
    idx: int,
    question: str,
    mode: str,
) -> ModeOut:
    state: Dict[str, Any] = {}
    fn = route_terrain if mode == "terrain" else route_academic

    res = await fn(
        company_id="test-company",
        user_id=f"eval-{idx}",
        message=question,
        conversation_history="",
        state_compact=state,
    )

    return ModeOut(intent=str(res.intent or "CLARIFICATION").upper(), confidence=float(res.confidence or 0.0))


async def _run_all(threshold: float = 0.70) -> None:
    rows: List[Row] = [
        Row(idx=i, question=q, expected_label=lab, expected_id=eid)
        for i, (q, lab, eid) in enumerate(PRODUCTION_TEST_CASES, start=1)
    ]

    terrain_tasks = [
        _predict_one(idx=r.idx, question=r.question, mode="terrain")
        for r in rows
    ]
    academic_tasks = [
        _predict_one(idx=r.idx, question=r.question, mode="academic")
        for r in rows
    ]

    terrain_out = await asyncio.gather(*terrain_tasks)
    academic_out = await asyncio.gather(*academic_tasks)

    total = len(rows)

    acc = {"terrain": 0, "academic": 0, "dual": 0, "inverted": 0}
    per_label = defaultdict(lambda: {"n": 0, "terrain": 0, "academic": 0, "dual": 0})

    inv_per_label = defaultdict(lambda: {"n": 0, "inverted": 0})

    dual_fallback_count = 0
    inverted_fallback_count = 0
    disagreement_t_a = 0
    disagreement_dual_terrain = 0

    academic_primary_threshold = float(os.environ.get("BOTLIVE_INVERTED_ACADEMIC_PRIMARY_THRESHOLD", "0.85"))
    academic_fallback_threshold = float(os.environ.get("BOTLIVE_INVERTED_ACADEMIC_FALLBACK_THRESHOLD", "0.70"))
    terrain_accept_threshold = float(os.environ.get("BOTLIVE_INVERTED_TERRAIN_ACCEPT_THRESHOLD", "0.75"))
    inverted_fallback_on_low_conf = (
        os.environ.get("BOTLIVE_INVERTED_FALLBACK_ON_LOW_CONF", "true").strip().lower() in {"1", "true", "yes", "y", "on"}
    )

    academic_conf = []
    terrain_conf = []
    academic_clarif = 0
    terrain_clarif = 0

    probleme_rows: List[Tuple[int, str, str, str, str]] = []

    for r, t, a in zip(rows, terrain_out, academic_out):
        expected = _expected_label_to_internal_intent(r.expected_label, r.expected_id)

        academic_conf.append(float(a.confidence))
        terrain_conf.append(float(t.confidence))
        if a.intent == "CLARIFICATION":
            academic_clarif += 1
        if t.intent == "CLARIFICATION":
            terrain_clarif += 1

        dual = t
        used_fallback = False
        if not (t.confidence >= float(threshold) and (t.intent or "").upper() != "CLARIFICATION"):
            dual = a
            used_fallback = True

        if used_fallback:
            dual_fallback_count += 1

        inverted = a
        inv_used_fallback = False
        if not (a.confidence >= float(academic_primary_threshold)):
            should_fallback = a.intent == "CLARIFICATION"
            if inverted_fallback_on_low_conf:
                should_fallback = should_fallback or (a.confidence < float(academic_fallback_threshold))

            if should_fallback:
                inv_used_fallback = True
                if t.confidence >= float(terrain_accept_threshold) and t.intent != "CLARIFICATION":
                    inverted = t

        if inv_used_fallback:
            inverted_fallback_count += 1

        if t.intent != a.intent:
            disagreement_t_a += 1

        if dual.intent != t.intent:
            disagreement_dual_terrain += 1

        ok_t = t.intent == expected
        ok_a = a.intent == expected
        ok_d = dual.intent == expected
        ok_i = inverted.intent == expected

        if (r.expected_label or "").strip().upper() == "PROBLEME":
            probleme_rows.append(
                (
                    r.idx,
                    r.question,
                    expected,
                    f"{t.intent}({t.confidence:.2f})",
                    f"{a.intent}({a.confidence:.2f})",
                )
            )

        if ok_t:
            acc["terrain"] += 1
        if ok_a:
            acc["academic"] += 1
        if ok_d:
            acc["dual"] += 1
        if ok_i:
            acc["inverted"] += 1

        label_key = (r.expected_label or "").strip().upper() or "UNKNOWN"
        per_label[label_key]["n"] += 1
        per_label[label_key]["terrain"] += int(ok_t)
        per_label[label_key]["academic"] += int(ok_a)
        per_label[label_key]["dual"] += int(ok_d)

        inv_per_label[label_key]["n"] += 1
        inv_per_label[label_key]["inverted"] += int(ok_i)

    fallback_rate = (dual_fallback_count / total * 100.0) if total else 0.0
    approx_calls_per_msg = 1.0 + (dual_fallback_count / total if total else 0.0)

    inverted_fallback_rate = (inverted_fallback_count / total * 100.0) if total else 0.0
    inverted_approx_calls = 1.0 + (inverted_fallback_count / total if total else 0.0)

    print("==================================================")
    print("SETFIT DUAL-SEFTY: TERRAIN vs ACADEMIC vs DUAL")
    print("==================================================")
    print(f"Total cases: {total}")
    print(f"Threshold: {threshold:.2f} (early-exit if conf>=threshold and intent!=CLARIFICATION)")
    inverted_fallback_str = (
        f"fallback=(CLARIFICATION or conf<{academic_fallback_threshold:.2f}), "
        if inverted_fallback_on_low_conf
        else "fallback=(CLARIFICATION only), "
    )
    print(
        "Inverted thresholds: "
        f"academic_primary={academic_primary_threshold:.2f}, "
        f"{inverted_fallback_str}"
        f"terrain_accept>={terrain_accept_threshold:.2f} and intent!=CLARIFICATION"
    )
    print("")

    if academic_conf:
        academic_low_070 = sum(1 for x in academic_conf if x < 0.70)
        academic_high_085 = sum(1 for x in academic_conf if x >= 0.85)
        terrain_low_070 = sum(1 for x in terrain_conf if x < 0.70)
        terrain_high_075 = sum(1 for x in terrain_conf if x >= 0.75)
        print("Confidence distribution:")
        print(f"  academic: <0.70={academic_low_070}/{total}, >=0.85={academic_high_085}/{total}, CLARIFICATION={academic_clarif}/{total}")
        print(f"  terrain : <0.70={terrain_low_070}/{total}, >=0.75={terrain_high_075}/{total}, CLARIFICATION={terrain_clarif}/{total}")
        print("")

    print("Accuracy:")
    print(f"  terrain : {acc['terrain']}/{total} = {acc['terrain']/total*100:.1f}%")
    print(f"  academic: {acc['academic']}/{total} = {acc['academic']/total*100:.1f}%")
    print(f"  dual    : {acc['dual']}/{total} = {acc['dual']/total*100:.1f}%")
    print(f"  inverted: {acc['inverted']}/{total} = {acc['inverted']/total*100:.1f}%")
    print("")

    print("Dual fallback:")
    print(f"  fallback_count: {dual_fallback_count}/{total} = {fallback_rate:.1f}%")
    print(f"  approx_calls_per_msg: {approx_calls_per_msg:.2f} (1.00=pas de fallback, 2.00=100% fallback)")
    print("")

    print("Inverted fallback:")
    print(f"  fallback_count: {inverted_fallback_count}/{total} = {inverted_fallback_rate:.1f}%")
    print(f"  approx_calls_per_msg: {inverted_approx_calls:.2f} (1.00=pas de fallback, 2.00=100% fallback)")
    print("")

    print("Disagreements:")
    print(f"  terrain_vs_academic: {disagreement_t_a}/{total} = {disagreement_t_a/total*100:.1f}%")
    print(f"  dual_vs_terrain    : {disagreement_dual_terrain}/{total} = {disagreement_dual_terrain/total*100:.1f}%")
    print("")

    print("Per-label accuracy (%):")
    header = f"{'LABEL':<20} {'N':>4} {'T%':>6} {'A%':>6} {'D%':>6} {'I%':>6}"
    print(header)
    print("-" * len(header))
    for label in sorted(per_label.keys()):
        n = per_label[label]["n"]
        t_ok = per_label[label]["terrain"]
        a_ok = per_label[label]["academic"]
        d_ok = per_label[label]["dual"]
        i_ok = inv_per_label[label]["inverted"]
        t_p = (t_ok / n * 100.0) if n else 0.0
        a_p = (a_ok / n * 100.0) if n else 0.0
        d_p = (d_ok / n * 100.0) if n else 0.0
        i_p = (i_ok / n * 100.0) if n else 0.0
        print(f"{label:<20} {n:>4} {t_p:>6.1f} {a_p:>6.1f} {d_p:>6.1f} {i_p:>6.1f}")

    if probleme_rows:
        print("\nPROBLEME cases (debug):")
        for idx, q, exp, t_str, a_str in probleme_rows:
            print(f"  [{idx:03d}] expected={exp:<12} | terrain={t_str:<18} | academic={a_str:<18} | q={q}")


def main() -> None:
    threshold = float(os.environ.get("BOTLIVE_DUAL_TERRAIN_THRESHOLD", "0.70"))
    asyncio.run(_run_all(threshold=threshold))


if __name__ == "__main__":
    main()
