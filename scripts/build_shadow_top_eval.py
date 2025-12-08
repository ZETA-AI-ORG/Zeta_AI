import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict

# Ce script construit un set d'évaluation à partir des messages Shadow
# en prenant les messages clients les plus fréquents.
# Il lit data/shadow/shadow_pairs.jsonl (ou SHADOW_PAIRS_PATH) et écrit
# un fichier JSONL utilisable par scripts/score_routing_eval.py.

SHADOW_PATH = Path(os.getenv("SHADOW_PAIRS_PATH", "data/shadow/shadow_pairs.jsonl"))
OUT_PATH = Path(os.getenv("SHADOW_TOP_EVAL_OUT", "data/eval/routing_eval_shadow_top100.jsonl"))
TOP_N = int(os.getenv("SHADOW_TOP_N", "100"))
MIN_CONFIDENCE = float(os.getenv("SHADOW_TOP_MIN_CONFIDENCE", "0.0"))
FILTER_COMPANY_ID = os.getenv("SHADOW_TOP_FILTER_COMPANY_ID", "").strip()


def main() -> None:
    if not SHADOW_PATH.exists():
        print(f"Shadow pairs not found: {SHADOW_PATH}")
        return

    # Comptage des messages par texte et par intent
    text_counts: Counter[str] = Counter()
    labels_per_text: Dict[str, Counter[int]] = defaultdict(Counter)

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

            if FILTER_COMPANY_ID and rec.get("company_id") != FILTER_COMPANY_ID:
                continue

            msg = str(rec.get("text") or rec.get("message") or "").strip()
            if not msg:
                continue

            intent = rec.get("intent_pred") or {}
            best_id = intent.get("best_id")
            conf = intent.get("confidence")

            if best_id is None:
                continue

            if MIN_CONFIDENCE > 0.0:
                try:
                    if conf is None or float(conf) < MIN_CONFIDENCE:
                        continue
                except Exception:
                    continue

            # On agrège par texte exact (trimmed). Si le même texte a reçu plusieurs intents,
            # on comptera les labels pour choisir le plus fréquent plus tard.
            key = msg
            text_counts[key] += 1
            try:
                labels_per_text[key][int(best_id)] += 1
            except Exception:
                continue

    if not text_counts:
        print("No shadow user messages found after filtering.")
        return

    # Top N textes les plus fréquents
    top_texts = [txt for txt, _ in text_counts.most_common(TOP_N)]

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT_PATH.open("w", encoding="utf-8") as out:
        for txt in top_texts:
            label_counter = labels_per_text.get(txt)
            if not label_counter:
                continue
            best_label, votes = label_counter.most_common(1)[0]
            count = text_counts[txt]
            obj = {
                "text": txt,
                "intent_id": int(best_label),
                "count": int(count),
                "label_votes": int(votes),
            }
            out.write(json.dumps(obj, ensure_ascii=False) + "\n")
            written += 1

    print(
        f"Built eval set with {written} unique texts (top {TOP_N}) "
        f"from {sum(text_counts.values())} shadow messages -> {OUT_PATH}"
    )


if __name__ == "__main__":
    main()
