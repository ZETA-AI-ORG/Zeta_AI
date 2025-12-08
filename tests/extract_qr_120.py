import json
import os

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
RESULTS_DIR = os.path.join(ROOT_DIR, "results")

# À adapter si tu veux pointer un autre fichier plus tard
INPUT_JSON = os.path.join(RESULTS_DIR, "botlive_llm_eval_12_20251207_191019.json")
OUTPUT_TXT = os.path.join(RESULTS_DIR, "questions_reponses_120_full.txt")


def main() -> None:
    print(f"[EXTRACT] Lecture JSON: {INPUT_JSON}")
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    lines = []
    for item in data:
        idx = item.get("index")
        q = item.get("question", "").replace("\n", " ")
        llm = item.get("llm") or {}
        ans = llm.get("answer", "")
        ans = (ans or "").replace("\n", " ")
        line = f"{idx}. {q} -> {ans}"
        lines.append(line)

    text = "\n".join(lines) + "\n"
    with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
        f.write(text)

    print("[EXTRACT] Fichier généré:")
    print(OUTPUT_TXT)


if __name__ == "__main__":
    main()
