import json
import os
import time
from pathlib import Path
from typing import Dict, List

SHADOW_PATH = Path(os.getenv("SHADOW_PAIRS_PATH", "data/shadow/shadow_pairs.jsonl"))
AUGMENT_OUT = Path(os.getenv("INTENT_AUGMENT_OUT", "intents/augment/shadow_augment.json"))
MIN_LEN = int(os.getenv("INTENT_AUGMENT_MIN_LEN", "6"))  # minimal tokens/chars heuristic
MAX_PER_INTENT = int(os.getenv("INTENT_AUGMENT_MAX_PER_INTENT", "80"))
MIN_CONFIDENCE = float(os.getenv("INTENT_AUGMENT_MIN_CONFIDENCE", "0.0"))
WINDOW_DAYS = int(os.getenv("INTENT_AUGMENT_WINDOW_DAYS", "0"))
MIN_WORDS = int(os.getenv("INTENT_AUGMENT_MIN_WORDS", "0"))
MAX_WORDS = int(os.getenv("INTENT_AUGMENT_MAX_WORDS", "0"))
MAX_SPECIAL_RATIO = float(os.getenv("INTENT_AUGMENT_MAX_SPECIAL_RATIO", "0.0"))


def _clean_text(s: str) -> str:
    s = (s or "").strip()
    # light clean
    s = s.replace("\r", " ").replace("\n", " ")
    while "  " in s:
        s = s.replace("  ", " ")
    return s


def build_from_shadow() -> Dict[str, List[str]]:
    if not SHADOW_PATH.exists():
        raise FileNotFoundError(f"Shadow pairs not found: {SHADOW_PATH}")

    out: Dict[str, List[str]] = {}
    seen: Dict[str, set] = {}

    now_ts = int(time.time())

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

            ts = rec.get("ts")
            if WINDOW_DAYS > 0 and isinstance(ts, (int, float)):
                if now_ts - int(ts) > WINDOW_DAYS * 86400:
                    continue

            msg = _clean_text(rec.get("text") or rec.get("message") or "")
            if not msg or len(msg) < MIN_LEN:
                continue

            words = msg.split()
            if MIN_WORDS > 0 and len(words) < MIN_WORDS:
                continue
            if MAX_WORDS > 0 and len(words) > MAX_WORDS:
                continue
            if MAX_SPECIAL_RATIO > 0.0:
                total_chars = len(msg)
                if total_chars > 0:
                    special_chars = sum(1 for ch in msg if not ch.isalnum() and not ch.isspace())
                    if special_chars / float(total_chars) > MAX_SPECIAL_RATIO:
                        continue

            intent = rec.get("intent_pred") or {}
            if MIN_CONFIDENCE > 0.0:
                conf_val = intent.get("confidence")
                try:
                    if conf_val is None or float(conf_val) < MIN_CONFIDENCE:
                        continue
                except (TypeError, ValueError):
                    continue

            iid = intent.get("best_id")
            if iid is None:
                continue
            key = str(iid)

            if key not in out:
                out[key] = []
                seen[key] = set()

            # Dedup per intent
            if msg.lower() in seen[key]:
                continue
            seen[key].add(msg.lower())
            out[key].append(msg)

    # Truncate per intent to cap size
    for k, arr in out.items():
        out[k] = arr[:MAX_PER_INTENT]

    return out


def main() -> None:
    mapping = build_from_shadow()
    AUGMENT_OUT.parent.mkdir(parents=True, exist_ok=True)
    with AUGMENT_OUT.open("w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    print(f"Wrote {sum(len(v) for v in mapping.values())} examples across {len(mapping)} intents -> {AUGMENT_OUT}")


if __name__ == "__main__":
    main()
