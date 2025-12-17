from __future__ import annotations

import os
import sys
import argparse
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np


_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from core.botlive_intent_router import _route_with_embeddings
from tests.production_test_cases import PRODUCTION_TEST_CASES


_ID_TO_INTENT = {
    # NOTE: PRODUCTION_TEST_CASES utilise encore des IDs historiques (V3-style).
    # Ici on les remappe vers les intents actuels renvoyés par _route_with_embeddings (V4).
    1: "SALUT",
    2: "INFO_GENERALE",
    3: "CLARIFICATION",
    4: "PRODUIT_GLOBAL",
    5: "PRODUIT_GLOBAL",
    6: "PRIX_PROMO",
    7: "PRODUIT_GLOBAL",
    8: "ACHAT_COMMANDE",
    9: "LIVRAISON",
    10: "PAIEMENT",
    11: "COMMANDE_EXISTANTE",
    12: "PROBLEME",
    13: "CONTACT_COORDONNEES",
}


@dataclass
class Row:
    text: str
    expected: str
    predicted: str
    score: float
    correct: bool


def _bin_stats(rows: List[Row], step: float = 0.05) -> List[Tuple[str, int, float]]:
    edges = np.arange(0.0, 1.0 + 1e-9, step)
    out: List[Tuple[str, int, float]] = []
    for i in range(len(edges) - 1):
        lo = float(edges[i])
        hi = float(edges[i + 1])
        bucket = [r for r in rows if lo <= r.score < hi]
        if not bucket:
            continue
        acc = sum(1 for r in bucket if r.correct) / len(bucket)
        out.append((f"[{lo:.2f},{hi:.2f})", len(bucket), float(acc)))
    return out


def _find_high_conf_threshold(rows: List[Row], target_precision: float) -> Tuple[float, float, float]:
    scores = sorted({round(r.score, 4) for r in rows})
    best = (1.0, 0.0, 0.0)

    for t in scores:
        subset = [r for r in rows if r.score >= t]
        if not subset:
            continue
        precision = sum(1 for r in subset if r.correct) / len(subset)
        coverage = len(subset) / len(rows)
        if precision >= target_precision:
            return float(t), float(precision), float(coverage)
        if precision > best[1]:
            best = (float(t), float(precision), float(coverage))

    return best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-precision", type=float, default=0.97)
    ap.add_argument("--bin-step", type=float, default=0.05)
    args = ap.parse_args()

    rows: List[Row] = []

    for question, _label, expected_id in PRODUCTION_TEST_CASES:
        expected = _ID_TO_INTENT.get(int(expected_id), "CLARIFICATION")
        predicted, score = _route_with_embeddings(question)
        predicted = (predicted or "").upper().strip()
        score = float(max(0.0, min(1.0, score)))
        rows.append(Row(text=question, expected=expected, predicted=predicted, score=score, correct=(expected == predicted)))

    overall_acc = sum(1 for r in rows if r.correct) / len(rows)
    correct_scores = [r.score for r in rows if r.correct]
    wrong_scores = [r.score for r in rows if not r.correct]

    print("==== OVERALL ====")
    print(f"cases={len(rows)}")
    print(f"accuracy={overall_acc:.3f}")

    if correct_scores:
        print(f"correct_score_p10/p50/p90={np.percentile(correct_scores,[10,50,90])}")
    if wrong_scores:
        print(f"wrong_score_p10/p50/p90={np.percentile(wrong_scores,[10,50,90])}")

    print("\n==== BINNED ACCURACY (by score) ====")
    for label, n, acc in _bin_stats(rows, step=float(args.bin_step)):
        print(f"{label}  n={n:<3d}  acc={acc:.3f}")

    print("\n==== HIGH CONF THRESHOLD ====")
    t, precision, coverage = _find_high_conf_threshold(rows, float(args.target_precision))
    print(f"target_precision={float(args.target_precision):.3f}")
    print(f"suggest_high_conf_threshold={t:.3f}")
    print(f"precision_at_threshold={precision:.3f}")
    print(f"coverage_at_threshold={coverage:.3f}")

    print("\n==== HARD CASES (lowest scores) ====")
    for r in sorted(rows, key=lambda x: x.score)[:20]:
        ok = "OK" if r.correct else "NO"
        print(f"{ok} score={r.score:.3f} expected={r.expected} predicted={r.predicted} text={r.text}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
