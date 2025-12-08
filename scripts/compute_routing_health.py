import json
import os
import time
from pathlib import Path
from typing import Dict, Any

SHADOW_PATH = Path(os.getenv("SHADOW_PAIRS_PATH", "data/shadow/shadow_pairs.jsonl"))
AUGMENT_PATH = Path(os.getenv("INTENT_AUGMENT_OUT", "intents/augment/shadow_augment.json"))
OUT_PATH = Path("data/routing_health.json")


def _load_shadow_counts() -> Dict[str, int]:
    counts: Dict[str, int] = {}
    if not SHADOW_PATH.exists():
        return counts
    try:
        with SHADOW_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("type") != "user_message":
                    continue
                intent = (rec.get("intent_pred") or {}).get("best_id")
                if intent is None:
                    continue
                key = str(intent)
                counts[key] = counts.get(key, 0) + 1
    except Exception:
        return counts
    return counts


def _load_augment_counts() -> Dict[str, int]:
    if not AUGMENT_PATH.exists():
        return {}
    try:
        with AUGMENT_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f) or {}
        return {str(k): len(v or []) for k, v in data.items() if isinstance(v, list)}
    except Exception:
        return {}


def main() -> None:
    shadow_counts = _load_shadow_counts()
    augment_counts = _load_augment_counts()

    intents: Dict[str, Any] = {}
    all_ids = set(shadow_counts) | set(augment_counts)
    for iid in sorted(all_ids, key=lambda x: int(x)):
        intents[iid] = {
            "shadow_messages": int(shadow_counts.get(iid, 0)),
            "augment_examples": int(augment_counts.get(iid, 0)),
        }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "intents": intents,
    }
    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Routing health written to {OUT_PATH}")


if __name__ == "__main__":
    main()
