"""
🔬 CACHE PROBE — Test isolé OpenRouter / Gemini implicit caching.

Objectif: valider l'hypothèse "messages=1 (all-in-user) bloque le cache implicit
chez Google AI Studio, alors que messages=2 (system + user) le débloque".

Le script appelle directement OpenRouter (sans aucun wrapper interne) avec
exactement le modèle `google/gemini-3.1-flash-lite-preview` via le provider
`google-ai-studio`, et compare les `cached_tokens` retournés sur 5 tours.

USAGE (VPS):
    cd ~/CHATBOT2.0/app
    source .venv/bin/activate
    export OPENROUTER_API_KEY=sk-or-v1-...
    python3 -m tests.cache_probe

USAGE (local):
    $env:OPENROUTER_API_KEY="sk-or-v1-..."
    python -m tests.cache_probe

SORTIE: tableau comparatif Run A (messages=1) vs Run B (messages=2).
"""

from __future__ import annotations

import json
import os
import sys
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import httpx


# ── Config ────────────────────────────────────────────────────────────────────
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = os.getenv("CACHE_PROBE_MODEL", "google/gemini-3.1-flash-lite-preview")
PROVIDER_ONLY = os.getenv("CACHE_PROBE_PROVIDER", "google-ai-studio")
N_TURNS = int(os.getenv("CACHE_PROBE_TURNS", "5"))
INTER_TURN_SLEEP_S = float(os.getenv("CACHE_PROBE_SLEEP", "1.0"))
TIMEOUT_S = float(os.getenv("CACHE_PROBE_TIMEOUT", "60"))
AUDIT_PATH = os.getenv("CACHE_PROBE_AUDIT_PATH", "results/cache_probe.jsonl")


# ── Prompts: ~6000 tokens de préfixe stable + suffixe variable ────────────────
def _build_static_prefix() -> str:
    """Préfixe stable de ~6000 tokens (>seuil 4096). Identique entre tous les tours."""
    header = (
        "Tu es Jessica, assistante commerciale WhatsApp d'une boutique en Côte d'Ivoire.\n"
        "Tu réponds en 1-2 phrases, ton WhatsApp ivoirien, vouvoiement obligatoire.\n"
        "Tu ne promets jamais un délai, un prix, un stock hors contexte fourni.\n\n"
        "## CATALOGUE PRODUITS\n"
    )
    products: List[str] = []
    for i in range(1, 121):
        products.append(
            f"### Produit #{i}\n"
            f"- Nom: Article série {i}\n"
            f"- Prix: {i * 1000} FCFA\n"
            f"- Description: Article de qualité référence A-{i:03d}, "
            f"disponible en plusieurs variantes (Pression, Culotte, Standard).\n"
            f"- Specs: taille S/M/L/XL, poids 5-25 kg selon spec.\n"
            f"- Ligne de remplissage déterministe pour stabiliser le préfixe cache.\n"
        )
    return header + "\n".join(products) + "\n## FIN CATALOGUE\n"


STATIC_PREFIX = _build_static_prefix()


def _build_dynamic_suffix(turn_idx: int, user_msg: str) -> str:
    """Suffixe volatile (change chaque tour)."""
    return (
        f"\n## SESSION (tour {turn_idx})\n"
        f"<historique></historique>\n"
        f"<message_actuel>{user_msg}</message_actuel>\n"
    )


USER_MESSAGES = [
    "bonsoir",
    "c'est combien ?",
    "je veux 1 lot",
    "je suis a Cocody",
    "mon numero c'est 0707070707",
]


# ── Helpers ──────────────────────────────────────────────────────────────────
def _hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]


def _extract_cache_metrics(usage: Dict[str, Any]) -> Tuple[int, int, int, int]:
    """(prompt_tokens, completion_tokens, cached_tokens, cache_write_tokens)"""
    pt = int(usage.get("prompt_tokens") or 0)
    ct = int(usage.get("completion_tokens") or 0)
    details = usage.get("prompt_tokens_details") or {}
    cached = int(details.get("cached_tokens") or 0)
    cwrite = int(details.get("cache_write_tokens") or 0)
    return pt, ct, cached, cwrite


def _call_openrouter(
    api_key: str,
    messages: List[Dict[str, str]],
    label: str,
    turn_idx: int,
) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://zeta-ai.local/cache-probe",
        "X-Title": "Zeta cache probe",
    }
    body: Dict[str, Any] = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.2,
        "top_p": 0.9,
        "max_tokens": 60,
        "stream": False,
        "usage": {"include": True},
        "provider": {"only": [PROVIDER_ONLY]},
    }

    t0 = time.perf_counter()
    with httpx.Client(timeout=TIMEOUT_S) as client:
        resp = client.post(OPENROUTER_URL, headers=headers, json=body)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    if resp.status_code != 200:
        return {
            "ok": False,
            "label": label,
            "turn": turn_idx,
            "status": resp.status_code,
            "error": resp.text[:500],
            "elapsed_ms": elapsed_ms,
        }
    data = resp.json()
    usage = data.get("usage") or {}
    pt, ct, cached, cwrite = _extract_cache_metrics(usage)

    # Hash des préfixes pour vérifier la stabilité entre tours
    msg_hashes = [(m["role"], _hash(m["content"])) for m in messages]

    return {
        "ok": True,
        "label": label,
        "turn": turn_idx,
        "elapsed_ms": elapsed_ms,
        "messages_count": len(messages),
        "msg_hashes": msg_hashes,
        "prompt_tokens": pt,
        "completion_tokens": ct,
        "cached_tokens": cached,
        "cache_write_tokens": cwrite,
        "raw_usage": usage,
        "response_excerpt": (
            (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        )[:80],
        "provider_used": (data.get("provider") or "?"),
        "id": data.get("id", ""),
    }


def _print_run_table(label: str, results: List[Dict[str, Any]]) -> None:
    print(f"\n{'=' * 78}")
    print(f"  RUN {label}")
    print("=" * 78)
    print(
        f"{'tour':<5} {'msgs':<5} {'prompt_tok':<12} {'cached_tok':<12} "
        f"{'cwrite_tok':<12} {'ms':<8} {'sys_hash':<14} {'usr_hash':<14}"
    )
    print("-" * 78)
    for r in results:
        if not r.get("ok"):
            print(f"  tour {r['turn']:>2} ❌ status={r.get('status')} err={r.get('error', '')[:60]}")
            continue
        sys_hash = next((h for role, h in r["msg_hashes"] if role == "system"), "—")
        usr_hash = next((h for role, h in r["msg_hashes"] if role == "user"), "—")
        print(
            f"{r['turn']:<5} {r['messages_count']:<5} "
            f"{r['prompt_tokens']:<12} {r['cached_tokens']:<12} "
            f"{r['cache_write_tokens']:<12} {r['elapsed_ms']:<8.0f} "
            f"{sys_hash:<14} {usr_hash:<14}"
        )
    total_cached = sum(r.get("cached_tokens", 0) for r in results if r.get("ok"))
    total_prompt = sum(r.get("prompt_tokens", 0) for r in results if r.get("ok"))
    hit_rate_pct = (100.0 * total_cached / total_prompt) if total_prompt else 0.0
    print("-" * 78)
    print(
        f"  TOTAL prompt_tokens={total_prompt}  cached_tokens={total_cached}  "
        f"hit_rate={hit_rate_pct:.1f}%"
    )


def _save_jsonl(results_a: List[Dict[str, Any]], results_b: List[Dict[str, Any]], path: str) -> None:
    try:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as fp:
            for r in results_a + results_b:
                fp.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"\n💾 Audit JSONL écrit: {target}")
    except Exception as e:
        print(f"⚠️ Impossible d'écrire {path}: {e}")


def _append_jsonl(row: Dict[str, Any], path: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(row)
    payload["logged_at"] = datetime.now(timezone.utc).isoformat()
    with open(target, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _save_summary(results_a: List[Dict[str, Any]], results_b: List[Dict[str, Any]], path: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    def _agg(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        ok_rows = [r for r in rows if r.get("ok")]
        prompt = sum(int(r.get("prompt_tokens", 0) or 0) for r in ok_rows)
        completion = sum(int(r.get("completion_tokens", 0) or 0) for r in ok_rows)
        cached = sum(int(r.get("cached_tokens", 0) or 0) for r in ok_rows)
        cwrite = sum(int(r.get("cache_write_tokens", 0) or 0) for r in ok_rows)
        hit_turns = sum(1 for r in ok_rows if int(r.get("cached_tokens", 0) or 0) > 0)
        return {
            "turns_total": len(rows),
            "turns_ok": len(ok_rows),
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "cached_tokens": cached,
            "cache_write_tokens": cwrite,
            "cache_hit_turns": hit_turns,
            "cache_hit_rate_turns": round(hit_turns / len(ok_rows), 4) if ok_rows else 0.0,
            "cache_hit_rate_tokens": round(cached / prompt, 4) if prompt else 0.0,
        }

    summary = {
        "logged_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "provider_only": PROVIDER_ONLY,
        "turns": N_TURNS,
        "mode_a": _agg(results_a),
        "mode_b": _agg(results_b),
    }
    with open(target, "w", encoding="utf-8") as fp:
        json.dump(summary, fp, ensure_ascii=False, indent=2)
    print(f"💾 Summary JSON écrit: {target}")


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> int:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY manquant dans l'environnement", file=sys.stderr)
        return 2

    print(f"🔬 CACHE PROBE")
    print(f"   model={MODEL}")
    print(f"   provider_only={PROVIDER_ONLY}")
    print(f"   turns={N_TURNS}")
    print(f"   static_prefix_chars={len(STATIC_PREFIX)} (≈{len(STATIC_PREFIX)//4} tokens)")
    print(f"   inter_turn_sleep_s={INTER_TURN_SLEEP_S}")
    print(f"   audit_path={AUDIT_PATH}")

    # ── RUN A: messages=1, tout dans user (mode actuel ZETA) ──
    results_a: List[Dict[str, Any]] = []
    print("\n▶ Lancement RUN A (messages=1, all-in-user)...")
    for i in range(N_TURNS):
        user_msg = USER_MESSAGES[i % len(USER_MESSAGES)]
        full = STATIC_PREFIX + _build_dynamic_suffix(i, user_msg)
        msgs = [{"role": "user", "content": full}]
        r = _call_openrouter(api_key, msgs, "A_messages=1", i)
        results_a.append(r)
        _append_jsonl(r, AUDIT_PATH)
        print(
            f"  A tour {i}: cached={r.get('cached_tokens', '?')} "
            f"prompt={r.get('prompt_tokens', '?')} ms={r.get('elapsed_ms', 0):.0f}"
        )
        if i < N_TURNS - 1:
            time.sleep(INTER_TURN_SLEEP_S)

    # ── RUN B: messages=2, system stable + user volatile ──
    results_b: List[Dict[str, Any]] = []
    print("\n▶ Lancement RUN B (messages=2, system+user split)...")
    for i in range(N_TURNS):
        user_msg = USER_MESSAGES[i % len(USER_MESSAGES)]
        msgs = [
            {"role": "system", "content": STATIC_PREFIX},
            {"role": "user", "content": _build_dynamic_suffix(i, user_msg)},
        ]
        r = _call_openrouter(api_key, msgs, "B_messages=2", i)
        results_b.append(r)
        _append_jsonl(r, AUDIT_PATH)
        print(
            f"  B tour {i}: cached={r.get('cached_tokens', '?')} "
            f"prompt={r.get('prompt_tokens', '?')} ms={r.get('elapsed_ms', 0):.0f}"
        )
        if i < N_TURNS - 1:
            time.sleep(INTER_TURN_SLEEP_S)

    # ── Tableaux ──
    _print_run_table("A — messages=1 (all-in-user)", results_a)
    _print_run_table("B — messages=2 (system + user)", results_b)

    # ── Verdict ──
    cached_a = sum(r.get("cached_tokens", 0) for r in results_a if r.get("ok"))
    cached_b = sum(r.get("cached_tokens", 0) for r in results_b if r.get("ok"))
    print("\n" + "=" * 78)
    print(f"  VERDICT: cached_total_A={cached_a}  cached_total_B={cached_b}")
    if cached_b > cached_a * 1.5 and cached_b > 1000:
        print("  ✅ HYPOTHÈSE CONFIRMÉE: split system/user débloque le cache implicit Gemini.")
    elif cached_a == 0 and cached_b == 0:
        print("  ❌ AUCUN cache hit dans les 2 modes → cause AUTRE (modèle preview, TTL, seuil réel).")
    elif cached_a > 0 and cached_b > 0:
        print("  🤔 Les 2 modes cachent → messages=1 n'était pas le bloqueur.")
    else:
        print("  ⚠️ Résultat ambigu, voir tableaux détaillés.")
    print("=" * 78)

    _save_jsonl(results_a, results_b, AUDIT_PATH)
    _save_summary(results_a, results_b, str(Path(AUDIT_PATH).with_suffix(".summary.json")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
