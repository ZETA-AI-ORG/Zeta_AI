from __future__ import annotations

import hashlib
import os
import re
import time
from typing import Any, Dict, Optional, Tuple


_RULES_CACHE: Dict[tuple[str, str], dict] = {}
_RULES_CACHE_TTL_S = float(os.getenv("BOTLIVE_DEPLOYED_RULES_CACHE_TTL_S", "60") or 60)
_DEBUG = (os.getenv("BOTLIVE_RULE_OVERRIDES_DEBUG", "false") or "false").strip().lower() == "true"


def _stable_pct(key: str) -> float:
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()
    # 0..1
    return int(h[:8], 16) / float(0xFFFFFFFF)


def _get_ctx_value(ctx: Any, name: str, default: Any = None) -> Any:
    if ctx is None:
        return default
    if isinstance(ctx, dict):
        return ctx.get(name, default)
    return getattr(ctx, name, default)


def _load_active_deployed_rules(company_id: str, environment: str) -> list[dict]:
    """Loads the latest active deployed_rules row (activated_at set, not deactivated).

    Expected JSON shape in deployed_rules.rules (MVP):
      [{"type":"direct_response","pattern":"...","match":"contains|regex","response":"...","rollout_pct":10}]
    """

    from database.supabase_client import get_supabase_client

    client = get_supabase_client()
    # supabase-py null filtering differs by version. Prefer None; fallback to "null".
    q = (
        client.table("deployed_rules")
        .select("id,company_id,environment,version,rules,metrics,activated_at,deactivated_at")
        .eq("company_id", company_id)
        .eq("environment", environment)
        .order("activated_at", desc=True)
        .limit(1)
    )

    try:
        res = q.is_("deactivated_at", None).execute()
    except Exception:
        res = q.is_("deactivated_at", "null").execute()

    row = (getattr(res, "data", None) or [None])[0]
    if not row:
        if _DEBUG:
            print(f"[RULE_OVERRIDE][DEBUG] No active deployed_rules for company_id={company_id} env={environment}")
        return []

    rules = row.get("rules") or []
    if isinstance(rules, list):
        return rules
    return []


def _get_rules_cached(company_id: str, environment: str) -> list[dict]:
    key = (company_id, environment)
    now = time.time()
    cached = _RULES_CACHE.get(key)
    if cached and (now - cached["ts"]) < _RULES_CACHE_TTL_S:
        return cached["rules"]

    try:
        rules = _load_active_deployed_rules(company_id, environment)
    except Exception as e:
        if _DEBUG:
            print(f"[RULE_OVERRIDE][DEBUG] Failed to load deployed_rules company_id={company_id} env={environment}: {e}")
        rules = []

    _RULES_CACHE[key] = {"ts": now, "rules": rules}
    return rules


def _match_rule(message: str, rule: dict) -> bool:
    pattern = (rule.get("pattern") or "").strip()
    if not pattern:
        return False

    mode = (rule.get("match") or "contains").strip().lower()
    msg = message or ""

    if mode == "regex":
        try:
            return re.search(pattern, msg, flags=re.IGNORECASE) is not None
        except re.error:
            return False

    # default: contains (case-insensitive)
    return pattern.lower() in msg.lower()


def _rule_rollout_ok(*, company_id: str, user_id: str, idx: int, rule: dict) -> bool:
    rollout_pct = rule.get("rollout_pct")
    if rollout_pct is None:
        rollout_pct = (rule.get("metrics") or {}).get("rollout_pct")
    try:
        rollout_pct_f = float(rollout_pct) if rollout_pct is not None else 100.0
    except Exception:
        rollout_pct_f = 100.0
    if rollout_pct_f >= 100.0:
        return True
    pct = _stable_pct(f"{company_id}:{user_id}:{idx}:{rule.get('type','')}:{rule.get('pattern','')}")
    return pct <= (rollout_pct_f / 100.0)

class RuleOverrides:
    @staticmethod
    def should_trigger_before_router(message: str, ctx) -> tuple[bool, str]:
        company_id = str(_get_ctx_value(ctx, "company_id", "") or "").strip()
        if not company_id:
            return False, ""

        environment = (os.getenv("ACTIVE_LEARNING_ENV", "staging") or "staging").strip().lower()
        rules = _get_rules_cached(company_id, environment)
        if not rules:
            if _DEBUG:
                print(f"[RULE_OVERRIDE][DEBUG] No rules loaded for company_id={company_id} env={environment}")
            return False, ""

        user_id = str(_get_ctx_value(ctx, "user_id", "") or "").strip()

        for idx, rule in enumerate(rules):
            rtype = (rule.get("type") or "").strip().lower()
            if rtype not in {"direct_response", "force_intent"}:
                continue

            if not _match_rule(message, rule):
                continue

            if not _rule_rollout_ok(company_id=company_id, user_id=user_id, idx=idx, rule=rule):
                continue

            if rtype == "direct_response":
                if _DEBUG:
                    print(
                        f"[RULE_OVERRIDE][DEBUG] Matched rule idx={idx} env={environment} pattern={rule.get('pattern','')} rollout={rule.get('rollout_pct', 100.0)}"
                    )
                return True, f"deployed_rule:{environment}:{idx}"

            # force_intent
            forced_intent = str(rule.get("intent") or "").strip().upper()
            if not forced_intent:
                continue
            if _DEBUG:
                print(
                    f"[RULE_OVERRIDE][DEBUG] Matched force_intent idx={idx} env={environment} intent={forced_intent} pattern={rule.get('pattern','')}"
                )
            return True, f"deployed_rule_force_intent:{environment}:{idx}:{forced_intent}"

        return False, ""

    @staticmethod
    def get_override_action(reason: str, message: str, ctx):
        if not reason:
            return None

        # force_intent doesn't return a direct action
        if reason.startswith("deployed_rule_force_intent:"):
            return None

        if not reason.startswith("deployed_rule:"):
            return None

        company_id = str(_get_ctx_value(ctx, "company_id", "") or "").strip()
        if not company_id:
            return None

        try:
            _, env, idx_s = reason.split(":", 2)
            idx = int(idx_s)
        except Exception:
            return None

        rules = _get_rules_cached(company_id, env)
        if idx < 0 or idx >= len(rules):
            return None

        rule = rules[idx]
        response = (rule.get("response") or "").strip()
        return response or None
