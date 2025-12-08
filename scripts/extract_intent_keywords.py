import json
import os
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.botlive_stopwords import extract_botlive_keywords

SHADOW_PATH = Path(os.getenv("SHADOW_PAIRS_PATH", "data/shadow/shadow_pairs.jsonl"))
OUT_PATH = Path(os.getenv("INTENT_KEYWORDS_OUT", "intents/keywords/intent_keywords.json"))
CORPUS_PATH = Path(os.getenv("INTENT_CORPUS_PATH", "intents/ecommerce_intents_full.json"))

# On réutilise les mêmes filtres que pour les augmentations shadow
MIN_LEN = int(os.getenv("INTENT_AUGMENT_MIN_LEN", "6"))
MIN_CONFIDENCE = float(os.getenv("INTENT_AUGMENT_MIN_CONFIDENCE", "0.0"))
WINDOW_DAYS = int(os.getenv("INTENT_AUGMENT_WINDOW_DAYS", "0"))
MIN_WORDS = int(os.getenv("INTENT_AUGMENT_MIN_WORDS", "0"))
MAX_WORDS = int(os.getenv("INTENT_AUGMENT_MAX_WORDS", "0"))
MAX_SPECIAL_RATIO = float(os.getenv("INTENT_AUGMENT_MAX_SPECIAL_RATIO", "0.0"))

MIN_KEYWORD_FREQ = int(os.getenv("INTENT_KEYWORDS_MIN_FREQ", "3"))
MAX_PER_INTENT = int(os.getenv("INTENT_KEYWORDS_MAX_PER_INTENT", "40"))


def _clean_text(s: str) -> str:
    s = (s or "").strip()
    s = s.replace("\r", " ").replace("\n", " ")
    while "  " in s:
        s = s.replace("  ", " ")
    return s


def _iter_shadow_messages() -> List[Tuple[str, str]]:
    """Retourne une liste de (intent_id_str, message) filtrés."""
    if not SHADOW_PATH.exists():
        return []

    now_ts = int(time.time())
    items: List[Tuple[str, str]] = []

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

            items.append((str(iid), msg))

    return items


def _load_intent_names() -> Dict[str, str]:
    """Charge le nom d'intent depuis le corpus principal (optionnel)."""
    if not CORPUS_PATH.exists():
        return {}
    try:
        with CORPUS_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f) or {}
        mapping: Dict[str, str] = {}
        for intent in data.get("intents", []) or []:
            try:
                iid = str(int(intent.get("id")))
            except Exception:
                continue
            name = str(intent.get("name") or "").strip()
            if not name:
                continue
            mapping[iid] = name
        return mapping
    except Exception:
        return {}


def build_intent_keywords() -> Dict[str, dict]:
    messages = _iter_shadow_messages()
    if not messages:
        return {}

    # Compteurs par intent et globaux
    per_intent: Dict[str, Counter] = {}
    global_counts: Counter = Counter()

    for iid, msg in messages:
        kw = extract_botlive_keywords(msg)
        if not kw:
            continue
        if iid not in per_intent:
            per_intent[iid] = Counter()
        c = per_intent[iid]
        for w in kw:
            c[w] += 1
            global_counts[w] += 1

    # Construire la structure finale
    intent_names = _load_intent_names()
    result: Dict[str, dict] = {}

    for iid, counter in per_intent.items():
        # Filtrer mots trop rares
        filtered_items = [
            (word, freq)
            for word, freq in counter.items()
            if freq >= MIN_KEYWORD_FREQ
        ]
        if not filtered_items:
            continue

        entries = []
        for word, freq in filtered_items:
            total = global_counts.get(word, freq)
            freq_other = max(total - freq, 0)
            # Spécificité simple: plus le mot est concentré sur cet intent, plus le score est élevé
            specificity = freq / float(freq_other + 1)
            entries.append({
                "word": word,
                "frequency": int(freq),
                "specificity": float(round(specificity, 3)),
            })

        # Trier par spécificité puis fréquence
        entries.sort(key=lambda x: (x["specificity"], x["frequency"]), reverse=True)
        if MAX_PER_INTENT > 0:
            entries = entries[:MAX_PER_INTENT]

        result[iid] = {
            "intent_name": intent_names.get(iid, ""),
            "keywords": entries,
        }

    return result


def main() -> None:
    mapping = build_intent_keywords()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    total_kw = sum(len(v.get("keywords", [])) for v in mapping.values())
    print(f"Wrote {total_kw} keywords across {len(mapping)} intents -> {OUT_PATH}")


if __name__ == "__main__":
    main()
