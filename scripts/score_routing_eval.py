import json
import os
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List

import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.centroid_router import CentroidRouter

EVAL_PATH = Path(os.getenv("EVAL_SET_PATH", "data/eval/routing_eval.jsonl"))
ONLY_INTENTS = os.getenv("EVAL_ONLY_INTENTS", "").strip()  # e.g. "9,11"
TOP_K = int(os.getenv("EVAL_TOP_K", "3"))


def load_eval() -> List[Dict]:
    items: List[Dict] = []
    if not EVAL_PATH.exists():
        print(f"Eval set not found: {EVAL_PATH}")
        return items
    with EVAL_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            text = (obj.get("text") or "").strip()
            iid = obj.get("intent_id")
            if not text or iid is None:
                continue
            try:
                iid = int(iid)
            except Exception:
                continue
            items.append({"text": text, "intent_id": iid})
    return items


def main() -> None:
    eval_items = load_eval()
    if not eval_items:
        print("No eval items to score.")
        return

    if ONLY_INTENTS:
        wh = set(int(x.strip()) for x in ONLY_INTENTS.split(",") if x.strip())
        eval_items = [it for it in eval_items if it["intent_id"] in wh]
        if not eval_items:
            print("No eval items left after filtering.")
            return

    router = CentroidRouter(use_cache=True)

    total = 0
    correct = 0
    confusions: Dict[str, int] = defaultdict(int)
    cmatrix: Dict[int, Counter] = defaultdict(Counter)
    errors: List[Dict] = []

    for it in eval_items:
        total += 1
        gt = int(it["intent_id"])
        res = router.route(it["text"], top_k=TOP_K)
        pred = int(res.get("intent_id"))
        if pred == gt:
            correct += 1
        else:
            key = f"{gt}->{pred}"
            confusions[key] += 1
            errors.append(
                {
                    "gt": gt,
                    "pred": pred,
                    "text": it["text"],
                    "top_k": res.get("top_k_intents", []),
                }
            )
        cmatrix[gt][pred] += 1

    acc = correct / total if total else 0.0
    print(f"Scored {total} examples. Accuracy: {acc:.3f}")

    # 9<->11 focus
    c_9_11 = 0
    c_9_11_ok = 0
    for it in eval_items:
        if it["intent_id"] in (9, 11):
            c_9_11 += 1
            res = router.route(it["text"], top_k=TOP_K)
            if int(res.get("intent_id")) == it["intent_id"]:
                c_9_11_ok += 1
    if c_9_11:
        print(f"9/11 subset: {c_9_11_ok}/{c_9_11} = {c_9_11_ok/c_9_11:.3f}")

    if confusions:
        print("Top confusions:")
        for k, v in sorted(confusions.items(), key=lambda x: -x[1])[:10]:
            print(" ", k, ":", v)

    if errors:
        print("\nError details (gt->pred):")
        for err in errors:
            gt = err["gt"]
            pred = err["pred"]
            text = err["text"]
            top_k = err["top_k"]
            print("-")
            print(f"[{gt}->{pred}] text=", text)
            if top_k:
                print("  top_k:")
                for rank, item in enumerate(top_k, start=1):
                    iid = item.get("intent_id")
                    name = item.get("intent_name")
                    conf = item.get("confidence")
                    print(f"    {rank}. {iid} ({name}) conf={conf:.3f}")


if __name__ == "__main__":
    main()
