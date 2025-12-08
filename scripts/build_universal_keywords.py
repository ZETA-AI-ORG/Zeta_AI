import json
import os
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, Set

import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.botlive_stopwords import extract_botlive_keywords

SHADOW_PATH = Path(os.getenv("SHADOW_PAIRS_PATH", "data/shadow/shadow_pairs.jsonl"))
OUT_PATH = Path(os.getenv("INTENT_UNIVERSAL_KEYWORDS_OUT", "intents/keywords/universal_keywords.json"))

# Reuse same quality filters
MIN_LEN = int(os.getenv("INTENT_AUGMENT_MIN_LEN", "6"))
MIN_CONFIDENCE = float(os.getenv("INTENT_AUGMENT_MIN_CONFIDENCE", "0.0"))
WINDOW_DAYS = int(os.getenv("INTENT_AUGMENT_WINDOW_DAYS", "0"))
MIN_WORDS = int(os.getenv("INTENT_AUGMENT_MIN_WORDS", "0"))
MAX_WORDS = int(os.getenv("INTENT_AUGMENT_MAX_WORDS", "0"))
MAX_SPECIAL_RATIO = float(os.getenv("INTENT_AUGMENT_MAX_SPECIAL_RATIO", "0.0"))

# Thresholds for universal extraction
MIN_GLOBAL_FREQ = int(os.getenv("INTENT_UNIVERSAL_MIN_FREQ", "5"))
MIN_COMPANY_SUPPORT = int(os.getenv("INTENT_UNIVERSAL_MIN_COMPANY_SUPPORT", "2"))


def _clean_text(s: str) -> str:
    s = (s or "").strip()
    s = s.replace("\r", " ").replace("\n", " ")
    while "  " in s:
        s = s.replace("  ", " ")
    return s


def _iter_shadow_user_messages() -> List[Dict]:
    if not SHADOW_PATH.exists():
        return []
    now_ts = int(time.time())
    out: List[Dict] = []
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
            company_id = rec.get("company_id") or "unknown"
            out.append({
                "intent_id": str(iid),
                "company_id": str(company_id),
                "text": msg,
            })
    return out


def build_universal_keywords() -> Dict[str, dict]:
    msgs = _iter_shadow_user_messages()
    if not msgs:
        return {}

    # Per intent counts of keywords and per-company support
    per_intent_counts: Dict[str, Counter] = {}
    per_intent_company_support: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))

    for rec in msgs:
        iid = rec["intent_id"]
        cid = rec["company_id"]
        kw = extract_botlive_keywords(rec["text"]) or []
        if not kw:
            continue
        if iid not in per_intent_counts:
            per_intent_counts[iid] = Counter()
        counter = per_intent_counts[iid]
        for w in kw:
            counter[w] += 1
            per_intent_company_support[iid][w].add(cid)

    result: Dict[str, dict] = {}
    for iid, counter in per_intent_counts.items():
        entries: List[dict] = []
        for w, freq in counter.items():
            companies = per_intent_company_support[iid].get(w, set())
            support = len(companies)
            if freq < MIN_GLOBAL_FREQ or support < MIN_COMPANY_SUPPORT:
                continue
            entries.append({
                "word": w,
                "global_frequency": int(freq),
                "company_support": int(support),
            })
        if not entries:
            continue
        # Sort by support then frequency
        entries.sort(key=lambda x: (x["company_support"], x["global_frequency"]), reverse=True)
        result[iid] = {"keywords": entries}

    return result


def main() -> None:
    mapping = build_universal_keywords()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    total_kw = sum(len(v.get("keywords", [])) for v in mapping.values())
    print(f"Wrote {total_kw} universal keywords across {len(mapping)} intents -> {OUT_PATH}")


if __name__ == "__main__":
    main()
