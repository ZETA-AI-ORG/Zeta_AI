import argparse
import asyncio
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Tuple


# Ensure project root is importable when running as `python scripts/...`
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


_WORD_RE = re.compile(r"[a-zA-ZÀ-ÖØ-öø-ÿ0-9']+", re.UNICODE)


def _normalize_text(text: str) -> str:
    t = (text or "").strip().lower()
    t = re.sub(r"\s+", " ", t)
    return t


def _tokens(text: str) -> List[str]:
    return [m.group(0) for m in _WORD_RE.finditer(_normalize_text(text))]


def _ngrams(tokens: List[str], n: int) -> Iterable[str]:
    if n <= 0:
        return []
    if len(tokens) < n:
        return []
    return (" ".join(tokens[i : i + n]) for i in range(0, len(tokens) - n + 1))


@dataclass
class Candidate:
    company_id: str
    pattern: str
    intent: str
    support: int
    avg_conf: float
    examples: List[str]


async def _fetch_routing_events(*, since_iso: str, company_id: str | None, limit: int) -> List[Dict[str, Any]]:
    from database.supabase_client import get_supabase_client

    client = get_supabase_client()

    def _run():
        q = client.table("routing_events").select("company_id,message,final_intent,final_conf,created_at")
        q = q.gte("created_at", since_iso)
        if company_id:
            q = q.eq("company_id", company_id)
        if limit and limit > 0:
            q = q.limit(limit)
        return q.execute()

    res = await asyncio.to_thread(_run)
    return getattr(res, "data", None) or []


def _build_candidates(
    rows: List[Dict[str, Any]],
    *,
    min_support: int,
    top_k_per_company: int,
    max_examples: int,
    ngram_min: int,
    ngram_max: int,
) -> List[Candidate]:
    # group by company
    by_company: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        cid = (r.get("company_id") or "").strip()
        if not cid:
            continue
        by_company[cid].append(r)

    out: List[Candidate] = []

    for cid, events in by_company.items():
        # phrase -> intent -> counts/conf/examples
        phrase_intent_counts: Dict[str, Counter] = defaultdict(Counter)
        phrase_conf_sum: Dict[Tuple[str, str], float] = defaultdict(float)
        phrase_examples: Dict[Tuple[str, str], List[str]] = defaultdict(list)
        phrase_total: Counter = Counter()

        for ev in events:
            msg = (ev.get("message") or "").strip()
            if not msg:
                continue
            intent = (ev.get("final_intent") or "").strip().upper() or "UNKNOWN"
            conf = float(ev.get("final_conf") or 0.0)

            toks = _tokens(msg)
            if not toks:
                continue

            seen_phrases = set()
            for n in range(ngram_min, ngram_max + 1):
                for ph in _ngrams(toks, n):
                    if len(ph) < 5:
                        continue
                    if ph in seen_phrases:
                        continue
                    seen_phrases.add(ph)
                    phrase_total[ph] += 1
                    phrase_intent_counts[ph][intent] += 1
                    phrase_conf_sum[(ph, intent)] += conf
                    ex_key = (ph, intent)
                    if len(phrase_examples[ex_key]) < max_examples:
                        phrase_examples[ex_key].append(msg)

        # score phrases by support and pick dominant intent
        scored: List[Tuple[int, str, str]] = []
        for ph, total in phrase_total.items():
            if total < min_support:
                continue
            dominant_intent, dominant_count = phrase_intent_counts[ph].most_common(1)[0]
            # require dominance (avoid noisy phrases)
            if dominant_count / float(total) < 0.7:
                continue
            scored.append((dominant_count, ph, dominant_intent))

        scored.sort(reverse=True)
        for dominant_count, ph, dominant_intent in scored[:top_k_per_company]:
            conf_sum = phrase_conf_sum.get((ph, dominant_intent), 0.0)
            avg_conf = conf_sum / float(dominant_count) if dominant_count > 0 else 0.0
            examples = phrase_examples.get((ph, dominant_intent), [])[:max_examples]
            out.append(
                Candidate(
                    company_id=cid,
                    pattern=ph,
                    intent=dominant_intent,
                    support=int(dominant_count),
                    avg_conf=float(avg_conf),
                    examples=examples,
                )
            )

    return out


async def _insert_rule_candidates(cands: List[Candidate]) -> int:
    if not cands:
        return 0

    from database.supabase_client import get_supabase_client

    client = get_supabase_client()

    rows = []
    for c in cands:
        rows.append(
            {
                "company_id": c.company_id,
                "rule_type": "lexical_guard",
                "pattern": c.pattern,
                "intent": c.intent,
                "confidence": c.avg_conf,
                "support": c.support,
                "examples": c.examples,
                "counter_examples": [],
                "status": "proposed",
                "proposed_by": "nightly_active_learning",
                "metrics": {"support": c.support, "avg_conf": c.avg_conf},
                "raw": {"source": "routing_events"},
            }
        )

    def _run():
        return client.table("rule_candidates").insert(rows).execute()

    res = await asyncio.to_thread(_run)
    data = getattr(res, "data", None) or []
    return len(data)


def _iso_z(dt: datetime) -> str:
    # Supabase PostgREST accepts ISO strings; keep timezone explicit
    return dt.astimezone(timezone.utc).isoformat()


async def main_async(args: argparse.Namespace) -> int:
    hours = float(args.hours)
    if args.days is not None:
        hours = float(args.days) * 24.0
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    since_iso = _iso_z(since)

    rows = await _fetch_routing_events(since_iso=since_iso, company_id=args.company_id, limit=args.limit)
    print(f"[nightly_active_learning] fetched_rows={len(rows)} since={since_iso}")

    cands = _build_candidates(
        rows,
        min_support=int(args.min_support),
        top_k_per_company=int(args.top_k_per_company),
        max_examples=int(args.max_examples),
        ngram_min=int(args.ngram_min),
        ngram_max=int(args.ngram_max),
    )

    print(f"[nightly_active_learning] candidates={len(cands)}")
    for c in cands[: min(10, len(cands))]:
        print(f"  - company={c.company_id} support={c.support} intent={c.intent} pattern='{c.pattern}'")

    if args.dry_run:
        print("[nightly_active_learning] dry_run=true, skipping insert")
        return 0

    inserted = await _insert_rule_candidates(cands)
    print(f"[nightly_active_learning] inserted_rule_candidates={inserted}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Nightly active learning (MVP): routing_events -> rule_candidates")
    p.add_argument("--hours", type=float, default=24.0 * 30.0, help="Lookback window in hours (default: 720 = 30 days)")
    p.add_argument("--days", type=float, default=None, help="Lookback window in days (overrides --hours)")
    p.add_argument("--company-id", type=str, default=None, help="Optional company_id filter")
    p.add_argument("--limit", type=int, default=5000, help="Max events to fetch (default: 5000)")
    p.add_argument("--min-support", type=int, default=6, help="Minimum support for a phrase within a company")
    p.add_argument("--top-k-per-company", type=int, default=25, help="Max candidates per company")
    p.add_argument("--max-examples", type=int, default=5, help="Max examples stored per candidate")
    p.add_argument("--ngram-min", type=int, default=2, help="Min ngram size")
    p.add_argument("--ngram-max", type=int, default=3, help="Max ngram size")
    p.add_argument("--dry-run", action="store_true", help="Compute candidates but do not insert")

    args = p.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
