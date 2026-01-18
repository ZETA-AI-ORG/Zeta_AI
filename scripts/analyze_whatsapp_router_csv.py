import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


_WORD_RE = re.compile(r"[a-zA-Z0-9àâäçéèêëîïôöùûüÿœæ'’]+")


_FR_STOPWORDS = {
    "a",
    "au",
    "aux",
    "avec",
    "ce",
    "ces",
    "cette",
    "de",
    "des",
    "du",
    "dans",
    "en",
    "et",
    "est",
    "il",
    "je",
    "j",
    "la",
    "le",
    "les",
    "leur",
    "lui",
    "ma",
    "mais",
    "me",
    "mes",
    "moi",
    "mon",
    "ne",
    "nos",
    "notre",
    "nous",
    "on",
    "ou",
    "pas",
    "pour",
    "que",
    "qui",
    "sa",
    "se",
    "ses",
    "si",
    "son",
    "sur",
    "ta",
    "te",
    "tes",
    "toi",
    "ton",
    "tu",
    "un",
    "une",
    "vos",
    "votre",
    "vous",
    "y",
}


_BUSINESS_STOPWORDS = {
    "ok",
    "okay",
    "d'accord",
    "merci",
    "stp",
    "svp",
    "pls",
    "plus",
    "puis",
    "savoir",
    "bjr",
    "bonjour",
    "bonsoir",
    "salut",
    "cc",
}


def _to_float(x: str, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _norm_text(s: str) -> str:
    s = (s or "").strip().lower()
    # Normaliser apostrophes typographiques
    s = s.replace("’", "'")
    s = re.sub(r"[\s\t\r\n]+", " ", s)
    return s


def _tokenize(s: str) -> List[str]:
    s = _norm_text(s)
    raw = [w for w in _WORD_RE.findall(s) if w]

    # Normalisation light: supprimer apostrophes en bord, conserver apostrophe interne
    tokens: List[str] = []
    for w in raw:
        w = w.strip("'")
        if not w:
            continue
        tokens.append(w)

    # Fusion d'expressions fréquentes: "quelqu un" => "quelqu'un"
    merged: List[str] = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in {"quelqu", "quelqu'"} and i + 1 < len(tokens) and tokens[i + 1] in {"un", "une"}:
            merged.append("quelqu'un" if tokens[i + 1] == "un" else "quelqu'une")
            i += 2
            continue
        merged.append(t)
        i += 1

    return merged


def _is_phone_token(t: str) -> bool:
    digits = re.sub(r"\D+", "", t)
    return len(digits) >= 8


def _filtered_tokens(tokens: List[str]) -> List[str]:
    out: List[str] = []
    for t in tokens:
        if len(t) <= 1:
            continue
        if t in _FR_STOPWORDS:
            continue
        if t in _BUSINESS_STOPWORDS:
            continue
        if _is_phone_token(t):
            continue
        if t.isdigit():
            continue
        out.append(t)
    return out


def _top_discriminative(
    intent_counter: Counter,
    global_counter: Counter,
    total_intent: int,
    total_global: int,
    top_k: int,
    min_intent_count: int,
) -> List[Dict[str, float]]:
    """Score tokens/bigrams par 'lift' vs global.

    lift = P(x|intent) / P(x|global)
    On retourne aussi count_intent/count_global pour inspection.
    """

    out: List[Dict[str, float]] = []
    if total_intent <= 0 or total_global <= 0:
        return out

    for item, c_intent in intent_counter.items():
        if c_intent < min_intent_count:
            continue
        c_global = int(global_counter.get(item, 0))
        if c_global <= 0:
            continue

        p_i = c_intent / total_intent
        p_g = c_global / total_global
        if p_g <= 0:
            continue

        lift = p_i / p_g
        out.append(
            {
                "item": item,
                "lift": float(lift),
                "count_intent": float(c_intent),
                "count_global": float(c_global),
                "p_intent": float(p_i),
                "p_global": float(p_g),
            }
        )

    out.sort(key=lambda d: (d["lift"], d["count_intent"]), reverse=True)
    return out[:top_k]


def _bigrams(tokens: List[str]) -> Iterable[Tuple[str, str]]:
    for i in range(len(tokens) - 1):
        yield tokens[i], tokens[i + 1]


@dataclass
class Example:
    message: str
    chat_id: str
    message_id: str
    conf: float


def analyze(csv_path: Path, top_k: int, min_conf: float, max_examples_per_intent: int) -> Dict:
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    intents = Counter()
    conf_sum = defaultdict(float)
    conf_count = defaultdict(int)

    token_counts = Counter()
    bigram_counts = Counter()

    intent_token_counts: Dict[str, Counter] = defaultdict(Counter)
    intent_bigram_counts: Dict[str, Counter] = defaultdict(Counter)

    examples_by_intent: Dict[str, List[Example]] = defaultdict(list)

    total_tokens_global = 0
    total_bigrams_global = 0

    total_tokens_per_intent: Dict[str, int] = defaultdict(int)
    total_bigrams_per_intent: Dict[str, int] = defaultdict(int)

    for r in rows:
        msg = (r.get("message") or "").strip()
        if not msg:
            continue

        intent = (r.get("intent_ctx") or r.get("intent_no_ctx") or "").strip() or "UNKNOWN"
        conf = _to_float(r.get("conf_ctx") or r.get("conf_no_ctx") or "0")

        intents[intent] += 1
        conf_sum[intent] += conf
        conf_count[intent] += 1

        toks_raw = _tokenize(msg)
        toks = _filtered_tokens(toks_raw)

        token_counts.update(toks)
        total_tokens_global += len(toks)

        bgs = list(_bigrams(toks))
        bigram_counts.update(bgs)
        total_bigrams_global += len(bgs)

        intent_token_counts[intent].update(toks)
        intent_bigram_counts[intent].update(bgs)
        total_tokens_per_intent[intent] += len(toks)
        total_bigrams_per_intent[intent] += len(bgs)

        if conf >= min_conf:
            examples_by_intent[intent].append(
                Example(
                    message=msg,
                    chat_id=str(r.get("chat_id") or ""),
                    message_id=str(r.get("message_id") or ""),
                    conf=conf,
                )
            )

    intent_stats = []
    for intent, n in intents.most_common():
        avg = conf_sum[intent] / conf_count[intent] if conf_count[intent] else 0.0
        intent_stats.append({"intent": intent, "count": n, "avg_conf": round(avg, 3)})

    def _top(counter: Counter) -> List[Tuple[str, int]]:
        return [(k, int(v)) for k, v in counter.most_common(top_k)]

    def _top_bigrams(counter: Counter) -> List[Tuple[str, int]]:
        out = []
        for (a, b), v in counter.most_common(top_k):
            out.append((f"{a} {b}", int(v)))
        return out

    per_intent = {}
    for intent, n in intents.items():
        toks_top = _top(intent_token_counts[intent])
        bigr_top = _top_bigrams(intent_bigram_counts[intent])
        discr_tokens = _top_discriminative(
            intent_counter=intent_token_counts[intent],
            global_counter=token_counts,
            total_intent=total_tokens_per_intent.get(intent, 0),
            total_global=total_tokens_global,
            top_k=min(25, top_k),
            min_intent_count=2,
        )
        discr_bigrams = _top_discriminative(
            intent_counter=intent_bigram_counts[intent],
            global_counter=bigram_counts,
            total_intent=total_bigrams_per_intent.get(intent, 0),
            total_global=total_bigrams_global,
            top_k=min(25, top_k),
            min_intent_count=2,
        )
        ex = sorted(examples_by_intent.get(intent, []), key=lambda e: e.conf, reverse=True)[:max_examples_per_intent]
        per_intent[intent] = {
            "count": int(n),
            "avg_conf": round(conf_sum[intent] / conf_count[intent], 3) if conf_count[intent] else 0.0,
            "top_tokens": toks_top,
            "top_bigrams": bigr_top,
            "guard_candidates_tokens": discr_tokens,
            "guard_candidates_bigrams": discr_bigrams,
            "examples_high_conf": [
                {
                    "conf": round(e.conf, 3),
                    "chat_id": e.chat_id,
                    "message_id": e.message_id,
                    "message": e.message,
                }
                for e in ex
            ],
        }

    report = {
        "input": str(csv_path).replace("\\", "/"),
        "rows": len(rows),
        "min_conf_examples": min_conf,
        "intent_stats": intent_stats,
        "top_tokens_global": _top(token_counts),
        "top_bigrams_global": _top_bigrams(bigram_counts),
        "stopwords_business": sorted(_BUSINESS_STOPWORDS),
        "per_intent": per_intent,
    }

    return report


def to_markdown(report: Dict, top_k_preview: int = 25) -> str:
    lines: List[str] = []
    lines.append("# WhatsApp Router Pattern Report")
    lines.append("")
    lines.append(f"- **Input**: `{report.get('input')}`")
    lines.append(f"- **Rows**: `{report.get('rows')}`")
    lines.append(f"- **High-conf threshold**: `{report.get('min_conf_examples')}`")
    lines.append(f"- **Business stopwords**: `{len(report.get('stopwords_business') or [])}`")
    lines.append("")

    lines.append("## Intent distribution")
    lines.append("")
    lines.append("| intent | count | avg_conf |")
    lines.append("|---|---:|---:|")
    for s in report.get("intent_stats", []):
        lines.append(f"| {s['intent']} | {s['count']} | {s['avg_conf']} |")

    lines.append("")
    lines.append("## Top tokens (global)")
    lines.append("")
    for w, c in (report.get("top_tokens_global") or [])[:top_k_preview]:
        lines.append(f"- **{w}**: {c}")

    lines.append("")
    lines.append("## Top bigrams (global)")
    lines.append("")
    for bg, c in (report.get("top_bigrams_global") or [])[:top_k_preview]:
        lines.append(f"- **{bg}**: {c}")

    lines.append("")
    lines.append("## Per intent")
    lines.append("")

    per_intent = report.get("per_intent") or {}
    for intent in sorted(per_intent.keys()):
        item = per_intent[intent]
        lines.append(f"### {intent}")
        lines.append("")
        lines.append(f"- **count**: {item.get('count')}")
        lines.append(f"- **avg_conf**: {item.get('avg_conf')}")
        lines.append("")

        lines.append("#### top tokens")
        for w, c in (item.get("top_tokens") or [])[:top_k_preview]:
            lines.append(f"- **{w}**: {c}")
        lines.append("")

        lines.append("#### top bigrams")
        for bg, c in (item.get("top_bigrams") or [])[:top_k_preview]:
            lines.append(f"- **{bg}**: {c}")
        lines.append("")

        lines.append("#### examples (high confidence)")
        ex = item.get("examples_high_conf") or []
        if not ex:
            lines.append("- **none**")
        else:
            for e in ex:
                conf = e.get("conf")
                msg = (e.get("message") or "").replace("\n", " ").strip()
                chat_id = e.get("chat_id")
                message_id = e.get("message_id")
                lines.append(f"- **{conf}** (`chat_id={chat_id}`, `message_id={message_id}`): {msg}")
        lines.append("")

        lines.append("#### candidats guard (discriminants vs global)")
        cand_toks = item.get("guard_candidates_tokens") or []
        cand_bgs = item.get("guard_candidates_bigrams") or []
        if not cand_toks and not cand_bgs:
            lines.append("- **none**")
            lines.append("")
            continue

        if cand_toks:
            lines.append("##### tokens")
            for d in cand_toks[:top_k_preview]:
                it = d.get("item")
                lift = d.get("lift")
                ci = int(d.get("count_intent") or 0)
                cg = int(d.get("count_global") or 0)
                lines.append(f"- **{it}**: lift={lift:.2f} (intent={ci}, global={cg})")
            lines.append("")

        if cand_bgs:
            lines.append("##### bigrams")
            for d in cand_bgs[:top_k_preview]:
                it = d.get("item")
                if isinstance(it, (list, tuple)) and len(it) == 2:
                    it_str = f"{it[0]} {it[1]}"
                else:
                    it_str = str(it)
                lift = d.get("lift")
                ci = int(d.get("count_intent") or 0)
                cg = int(d.get("count_global") or 0)
                lines.append(f"- **{it_str}**: lift={lift:.2f} (intent={ci}, global={cg})")
            lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze WhatsApp router CSV (tokens/bigrams + high-conf examples per intent)")
    parser.add_argument("--input", default=str(Path("results/router_eval_whatsapp_client_to_business.csv")), help="Input CSV path")
    parser.add_argument("--out-json", default=str(Path("results/whatsapp_router_patterns.json")), help="Output JSON path")
    parser.add_argument("--out-md", default=str(Path("results/whatsapp_router_patterns.md")), help="Output Markdown report path")
    parser.add_argument("--top-k", type=int, default=80, help="Top-K tokens/bigrams to keep")
    parser.add_argument("--min-conf", type=float, default=0.85, help="Min confidence to store examples")
    parser.add_argument("--max-examples", type=int, default=12, help="Max examples per intent")

    args = parser.parse_args()

    csv_path = Path(args.input)
    if not csv_path.exists():
        raise FileNotFoundError(f"Input not found: {csv_path}")

    report = analyze(csv_path, top_k=args.top_k, min_conf=args.min_conf, max_examples_per_intent=args.max_examples)

    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    out_md = Path(args.out_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(to_markdown(report), encoding="utf-8")

    print(f"Rows: {report.get('rows')}")
    print(f"Intents: {len(report.get('intent_stats') or [])}")
    print(f"Saved JSON: {out_json}")
    print(f"Saved MD: {out_md}")


if __name__ == "__main__":
    main()
