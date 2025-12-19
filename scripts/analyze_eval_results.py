import argparse
import os
from collections import Counter, defaultdict
from typing import Any, Dict, List

import pandas as pd


def _as_bool(x: Any) -> bool:
    if isinstance(x, bool):
        return x
    if x is None:
        return False
    if isinstance(x, (int, float)):
        return bool(x)
    if isinstance(x, str):
        return x.strip().lower() in {"1", "true", "yes", "y", "on"}
    return False


def _pct(x: float) -> str:
    return f"{(100.0 * float(x)):.2f}%"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="Path to eval CSV (e.g. results/prod_eval_120_*.csv)")
    args = ap.parse_args()

    p = args.csv
    if not os.path.exists(p):
        raise SystemExit(f"CSV not found: {p}")

    df = pd.read_csv(p)
    if "final_ok" not in df.columns:
        raise SystemExit("CSV missing final_ok column")

    n = len(df)
    correct = int(df["final_ok"].fillna(False).astype(bool).sum())
    acc = correct / n if n else 0.0

    clarification_rate = (df["final_intent"].fillna("").astype(str).str.upper() == "CLARIFICATION").mean() if n else 0.0

    hyde_rate = None
    if "hyde_used" in df.columns:
        hyde_rate = df["hyde_used"].map(_as_bool).mean() if n else 0.0
    hyde_candidate_rate = None
    if "hyde_candidate" in df.columns:
        hyde_candidate_rate = df["hyde_candidate"].map(_as_bool).mean() if n else 0.0

    print("\n================= PROD EVAL SUMMARY =================")
    print(f"CSV: {p}")
    print(f"Total: {n}")
    print(f"Correct: {correct}")
    print(f"Accuracy: {_pct(acc)}")
    print(f"CLARIFICATION rate: {_pct(clarification_rate)}")
    if hyde_rate is not None:
        print(f"HYDE used rate: {_pct(hyde_rate)}")
    if hyde_candidate_rate is not None:
        print(f"HYDE candidate rate: {_pct(hyde_candidate_rate)}")

    # Errors
    errs = df[df["final_ok"].fillna(False).astype(bool) == False].copy()  # noqa: E712
    print("\n================= ERRORS =================")
    print(f"Errors: {len(errs)}")
    if len(errs):
        cols = [c for c in [
            "idx",
            "question",
            "expected_internal",
            "final_intent",
            "final_conf",
            "mode",
            "hyde_candidate",
            "hyde_used",
            "hyde_stage",
            "hyde_trigger_reason",
            "human_handoff",
            "human_handoff_reason",
        ] if c in errs.columns]
        print(errs[cols].to_string(index=False))

    # Top confusions
    if all(c in df.columns for c in ["expected_internal", "final_intent"]):
        conf_pairs: Counter = Counter()
        for _, row in df.iterrows():
            exp = str(row.get("expected_internal") or "").upper()
            got = str(row.get("final_intent") or "").upper()
            if exp and got and exp != got:
                conf_pairs[(exp, got)] += 1

        print("\n================= TOP CONFUSIONS =================")
        for (exp, got), cnt in conf_pairs.most_common(15):
            print(f"{cnt:>3}  {exp} -> {got}")

    # Distributions
    print("\n================= DISTRIBUTIONS =================")
    if "expected_internal" in df.columns:
        print("\nExpected intents:")
        print(df["expected_internal"].fillna("NA").value_counts().to_string())
    if "final_intent" in df.columns:
        print("\nFinal intents:")
        print(df["final_intent"].fillna("NA").value_counts().to_string())

    if "hyde_trigger_reason" in df.columns and "hyde_candidate" in df.columns:
        mask = df["hyde_candidate"].map(_as_bool)
        if mask.any():
            print("\nHYDE trigger reasons (candidates):")
            print(df.loc[mask, "hyde_trigger_reason"].fillna("NA").value_counts().to_string())


if __name__ == "__main__":
    main()
