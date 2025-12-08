import json
import os
from pathlib import Path
from typing import Dict, List

import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.centroid_router import CentroidRouter

CANON_PATH = Path(os.getenv("CANONICAL_QA_PATH", "data/shadow/canonical_qa.jsonl"))
OUT_PATH = Path(os.getenv("INTENT_AUGMENT_OUT", "intents/augment/shadow_augment.json"))
MAX_PER_INTENT = int(os.getenv("INTENT_AUGMENT_MAX_PER_INTENT", "80"))
MERGE_EXISTING = os.getenv("INTENT_AUGMENT_MERGE", "1") not in ("0", "false", "False")


def load_canonicals() -> List[Dict]:
    items: List[Dict] = []
    if not CANON_PATH.exists():
        return items
    with CANON_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            # Expected keys: questions_examples (list), canonical_answer, ...
            if isinstance(obj.get("questions_examples"), list) and obj.get("questions_examples"):
                items.append(obj)
    return items


def build_augment_from_clusters(router: CentroidRouter) -> Dict[str, List[str]]:
    data = load_canonicals()
    out: Dict[str, List[str]] = {}
    seen: Dict[str, set] = {}

    for it in data:
        qlist = it.get("questions_examples") or []
        if not qlist:
            continue
        # Use the first example as canonical question (top similar to medoid)
        q = str(qlist[0]).strip()
        if not q:
            continue
        try:
            res = router.route(q, top_k=3)
            iid = res.get("intent_id")
        except Exception:
            iid = None
        if iid is None:
            continue
        key = str(int(iid))
        if key not in out:
            out[key] = []
            seen[key] = set()
        q_norm = q.lower()
        if q_norm in seen[key]:
            continue
        seen[key].add(q_norm)
        out[key].append(q)

    # Cap per intent
    for k in list(out.keys()):
        out[k] = out[k][:MAX_PER_INTENT]

    return out


def merge_with_existing(new_map: Dict[str, List[str]]) -> Dict[str, List[str]]:
    if not OUT_PATH.exists():
        return new_map
    try:
        with OUT_PATH.open("r", encoding="utf-8") as f:
            old = json.load(f) or {}
    except Exception:
        return new_map
    merged: Dict[str, List[str]] = {}
    for k in set(list(new_map.keys()) + list(old.keys())):
        arr = []
        seen = set()
        for s in (old.get(k) or []) + (new_map.get(k) or []):
            if not isinstance(s, str):
                continue
            t = s.strip()
            if not t:
                continue
            n = t.lower()
            if n in seen:
                continue
            seen.add(n)
            arr.append(t)
        merged[k] = arr[:MAX_PER_INTENT]
    return merged


def main() -> None:
    router = CentroidRouter(use_cache=True)
    new_map = build_augment_from_clusters(router)
    if MERGE_EXISTING:
        final_map = merge_with_existing(new_map)
    else:
        final_map = new_map
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(final_map, f, ensure_ascii=False, indent=2)
    total = sum(len(v) for v in final_map.values())
    print(f"Cluster augment wrote {total} examples across {len(final_map)} intents -> {OUT_PATH}")


if __name__ == "__main__":
    main()
