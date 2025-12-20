from __future__ import annotations

import asyncio
import contextlib
import math
import json
import logging
import os
import re
import time
from collections import deque
from typing import Any, Dict, Optional, Tuple
from core.setfit_intent_router import route_botlive_intent, BotliveRoutingResult
from core.semantic_cache import semantic_cache_decorator, is_cache_enabled
from core.model_router import choose_model

logger = logging.getLogger(__name__)

_shadow_supabase_client = None
_shadow_supabase_queue = deque()
_shadow_supabase_lock: Optional[asyncio.Lock] = None
_shadow_supabase_worker_task: Optional[asyncio.Task] = None


def _get_shadow_supabase_client():
    global _shadow_supabase_client
    if _shadow_supabase_client is not None:
        return _shadow_supabase_client

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        return None

    try:
        from supabase import create_client

        _shadow_supabase_client = create_client(supabase_url, supabase_key)
        return _shadow_supabase_client
    except Exception:
        return None


async def _shadow_write_to_supabase(payload: Dict[str, Any]) -> None:
    row = {
        "company_id": payload.get("company_id"),
        "user_id": payload.get("user_id"),
        "conversation_id": payload.get("conversation_id"),
        "message": payload.get("message"),
        "final_intent": payload.get("final_intent"),
        "final_conf": payload.get("final_conf"),
        "mode": payload.get("mode"),
        "cache_hit": payload.get("cache_hit"),
        "latency_ms": payload.get("latency_ms"),
        "dual_router_mode": payload.get("dual_router_mode"),
        "dual_router_stage": payload.get("dual_router_stage"),
        "hyde_used": payload.get("hyde_used"),
        "hyde_stage": payload.get("hyde_stage"),
        "hyde_trigger_reason": payload.get("hyde_trigger_reason"),
        "hyde_message": payload.get("hyde_message"),
        "smart_hyde_checked": payload.get("smart_hyde_checked"),
        "smart_hyde_should_trigger": payload.get("smart_hyde_should_trigger"),
        "smart_hyde_trigger_reason": payload.get("smart_hyde_trigger_reason"),
        "guard_applied": payload.get("guard_applied"),
        "guard_reason": payload.get("guard_reason"),
        "post_validation_applied": payload.get("post_validation_applied"),
        "post_validation_reason": payload.get("post_validation_reason"),
        "human_handoff": payload.get("human_handoff"),
        "human_handoff_reason": payload.get("human_handoff_reason"),
        "raw": payload,
    }

    global _shadow_supabase_lock, _shadow_supabase_worker_task

    if _shadow_supabase_lock is None:
        _shadow_supabase_lock = asyncio.Lock()

    max_queue = int(os.getenv("BOTLIVE_SHADOW_SUPABASE_MAX_QUEUE", "2000") or 2000)
    if max_queue < 1:
        max_queue = 1

    try:
        async with _shadow_supabase_lock:
            if len(_shadow_supabase_queue) >= max_queue:
                _shadow_supabase_queue.popleft()
            _shadow_supabase_queue.append(row)

            if _shadow_supabase_worker_task is None or _shadow_supabase_worker_task.done():
                _shadow_supabase_worker_task = asyncio.create_task(_shadow_supabase_worker())
    except Exception:
        return


async def _shadow_supabase_worker() -> None:
    client = _get_shadow_supabase_client()
    if client is None:
        return

    batch_size = int(os.getenv("BOTLIVE_SHADOW_SUPABASE_BATCH_SIZE", "50") or 50)
    if batch_size < 1:
        batch_size = 1
    flush_interval_s = float(os.getenv("BOTLIVE_SHADOW_SUPABASE_FLUSH_INTERVAL_S", "2.0") or 2.0)
    flush_interval_s = max(0.1, flush_interval_s)
    max_retries = int(os.getenv("BOTLIVE_SHADOW_SUPABASE_MAX_RETRIES", "4") or 4)
    max_retries = max(0, max_retries)
    base_backoff_s = float(os.getenv("BOTLIVE_SHADOW_SUPABASE_BACKOFF_S", "0.4") or 0.4)
    base_backoff_s = max(0.05, base_backoff_s)

    last_flush = time.monotonic()
    while True:
        rows: list[Dict[str, Any]] = []
        try:
            if _shadow_supabase_lock is None:
                return

            async with _shadow_supabase_lock:
                now = time.monotonic()
                should_flush = (len(_shadow_supabase_queue) >= batch_size) or ((now - last_flush) >= flush_interval_s)
                if not should_flush:
                    pass
                else:
                    n = min(batch_size, len(_shadow_supabase_queue))
                    for _ in range(n):
                        rows.append(_shadow_supabase_queue.popleft())
                    last_flush = now

            if not rows:
                await asyncio.sleep(flush_interval_s)
                if _shadow_supabase_lock is None:
                    return
                async with _shadow_supabase_lock:
                    if len(_shadow_supabase_queue) == 0:
                        return
                continue

            attempt = 0
            while True:
                try:
                    await asyncio.to_thread(lambda: client.table("routing_events").insert(rows).execute())
                    break
                except Exception as e:
                    attempt += 1
                    if attempt > max_retries:
                        logger.warning("[SHADOW_SUPABASE] drop batch after retries: %s", str(e))
                        break
                    backoff = base_backoff_s * math.pow(2.0, float(attempt - 1))
                    await asyncio.sleep(backoff)
        except Exception:
            with contextlib.suppress(Exception):
                await asyncio.sleep(flush_interval_s)


def _truthy_env(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "y", "on"}


def _normalize_text_basic(text: str) -> str:
    raw = (text or "").strip().lower()
    raw = re.sub(r"\s+", " ", raw)
    return raw


def _missing_fields_from_state(state_compact: Optional[Dict[str, Any]]) -> list[str]:
    st = state_compact or {}
    missing: list[str] = []
    if not st.get("photo_collected", False):
        missing.append("photo")
    if not st.get("paiement_collected", False):
        missing.append("paiement")
    if not st.get("zone_collected", False):
        missing.append("zone")
    if not st.get("tel_collected", False) or not st.get("tel_valide", False):
        missing.append("tel")
    return missing


def _intent_to_group(intent: str) -> str:
    upper = (intent or "").upper()
    if upper in {"PRODUIT_GLOBAL", "PRIX_PROMO"}:
        return "PRODUIT"
    if upper in {"ACHAT_COMMANDE", "COMMANDE_EXISTANTE"}:
        return "COMMANDE"
    if upper in {"SALUT", "INFO_GENERALE", "CONTACT_COORDONNEES"}:
        return "INFO"
    if upper == "PAIEMENT":
        return "PAIEMENT"
    if upper == "LIVRAISON":
        return "LIVRAISON"
    return "AUTRE"


def _determine_mode(intent: str, state_compact: Optional[Dict[str, Any]]) -> str:
    upper = (intent or "").upper()
    st = state_compact or {}
    is_complete = bool(st.get("is_complete", False))
    collected_count = int(st.get("collected_count", 0) or 0)

    mode_mapping = {
        "ACHAT_COMMANDE": "COMMANDE",
        "CONFIRMATION_PAIEMENT": "COMMANDE",
        "CONTACT_COORDONNEES": "COMMANDE",
        "PRODUIT_GLOBAL": "GUIDEUR",
        "INFO_GENERALE": "GUIDEUR",
        "QUESTION_PAIEMENT": "GUIDEUR",
        "PAIEMENT": "GUIDEUR",
        "LIVRAISON": "GUIDEUR",
        "PRIX_PROMO": "GUIDEUR",
        "SALUT": "GUIDEUR",
        "CLARIFICATION": "GUIDEUR",
        "COMMANDE_EXISTANTE": "RECEPTION_SAV",
        "PROBLEME": "RECEPTION_SAV",
        "PROBLEME_LIVRAISON": "RECEPTION_SAV",
    }
    if upper in mode_mapping:
        return mode_mapping[upper]
    if is_complete:
        return "RECEPTION_SAV"
    return "GUIDEUR" if collected_count > 0 else "RECEPTION_SAV"


def _global_sav_handoff_if_needed(
    *,
    message: str,
    company_id: str,
    user_id: str,
    conversation_history: str,
    state_compact: Optional[Dict[str, Any]],
) -> Tuple[Optional[BotliveRoutingResult], Dict[str, Any]]:
    debug: Dict[str, Any] = {
        "human_handoff": False,
        "human_handoff_reason": None,
    }

    if not _truthy_env("BOTLIVE_HUMAN_HANDOFF_ENABLED", "false"):
        debug["human_handoff_reason"] = "DISABLED"
        return None, debug

    t_norm = _normalize_text_basic(message)
    sav_markers = [
        "sav",
        "service après vente",
        "service apres vente",
        "réclamation",
        "reclamation",
        "remboursement",
        "rembourser",
        "retour",
        "retourner",
        "échanger",
        "echanger",
        "annuler",
        "annulation",
        "problème",
        "probleme",
        "défectueux",
        "defectueux",
        "cassé",
        "casse",
        "abîmé",
        "abime",
        "mauvais",
        "pas bon",
        "je me plains",
        "plainte",
    ]

    if not any(k in t_norm for k in sav_markers):
        debug["human_handoff_reason"] = "NO_SAV_MARKER"
        return None, debug

    debug["human_handoff"] = True
    debug["human_handoff_reason"] = "SAV_RECLAMATION_OR_RETURN"

    intent = "COMMANDE_EXISTANTE"
    confidence = 0.95
    intent_group = _intent_to_group(intent)
    mode = _determine_mode(intent, state_compact)
    missing_fields = _missing_fields_from_state(state_compact)

    return (
        BotliveRoutingResult(
            intent=intent,
            confidence=confidence,
            intent_group=intent_group,
            mode=mode,
            missing_fields=missing_fields,
            state=state_compact or {},
            debug={
                "company_id": company_id,
                "user_id": user_id,
                "raw_message": message,
                "conversation_history_sample": (conversation_history or "")[-300:],
                "router": "global_handoff",
                **debug,
            },
        ),
        debug,
    )


def _should_trigger_smart_hyde(*, res: BotliveRoutingResult) -> Tuple[bool, Optional[str]]:
    """Option B trigger: CLARIFICATION OR guard/post_validation applied OR confidence<threshold."""

    try:
        intent = str(getattr(res, "intent", "") or "CLARIFICATION").upper()
    except Exception:
        intent = "CLARIFICATION"
    try:
        conf = float(getattr(res, "confidence", 0.0) or 0.0)
    except Exception:
        conf = 0.0

    dbg = getattr(res, "debug", None) or {}

    post_validation_applied = bool(dbg.get("post_validation_applied"))
    # Historical naming inside setfit_intent_router: payment_guard_applied + payment_guard_reason
    payment_guard_applied = bool(dbg.get("payment_guard_applied"))

    if intent == "CLARIFICATION":
        return True, "clarification"
    if post_validation_applied:
        return True, "post_validation_applied"
    if payment_guard_applied:
        return True, "guard_applied"

    conf_thr = float(os.environ.get("BOTLIVE_SMART_HYDE_CONF_THRESHOLD", "0.50"))
    if conf < conf_thr:
        return True, "low_confidence"

    return False, None


async def _route_botlive_intent_smart_hyde(*args, **kwargs) -> BotliveRoutingResult:
    from core.hyde_reformulator import HydeReformulator

    company_id = kwargs.get("company_id")
    message = kwargs.get("message")
    conversation_history = kwargs.get("conversation_history")
    state_compact = kwargs.get("state_compact")

    base_kwargs = dict(kwargs)
    base_kwargs.pop("hyde_pre_enabled", None)

    # Tier 1: Terrain only (disable internal HYDE_PRE to avoid double triggers)
    res_terrain = await route_botlive_intent(*args, **{**base_kwargs, "hyde_pre_enabled": False})
    should_hyde, reason = _should_trigger_smart_hyde(res=res_terrain)

    try:
        res_terrain.debug["smart_hyde_checked"] = True
        res_terrain.debug["smart_hyde_should_trigger"] = bool(should_hyde)
        res_terrain.debug["smart_hyde_trigger_reason"] = reason
    except Exception:
        pass

    if not should_hyde:
        try:
            res_terrain.debug["hyde_used"] = False
            res_terrain.debug["hyde_trigger_reason"] = None
        except Exception:
            pass
        return res_terrain

    # Tier 2: HYDE reformulation → re-route terrain once (max one pass)
    try:
        reformulator = HydeReformulator()
        ctx = {"conversation_history": str(conversation_history or ""), "state": state_compact or {}}
        hyde_message = await reformulator.reformulate(str(company_id or ""), str(message or ""), ctx)
        res_hyde = await route_botlive_intent(
            *args,
            **{**base_kwargs, "message": hyde_message, "hyde_pre_enabled": False},
        )

        try:
            # Preserve Smart HYDE observability on the returned result
            res_hyde.debug["smart_hyde_checked"] = True
            res_hyde.debug["smart_hyde_should_trigger"] = True
            res_hyde.debug["smart_hyde_trigger_reason"] = reason

            res_hyde.debug["hyde_used"] = True
            res_hyde.debug["hyde_trigger_reason"] = reason
            res_hyde.debug["hyde_original_message"] = str(message or "")
            res_hyde.debug["hyde_message"] = str(hyde_message or "")
            # propagate tier-1 uncertainty signals for observability
            res_hyde.debug["tier1_intent"] = str(getattr(res_terrain, "intent", "") or "")
            res_hyde.debug["tier1_confidence"] = float(getattr(res_terrain, "confidence", 0.0) or 0.0)
            res_hyde.debug["tier1_post_validation_applied"] = bool(res_terrain.debug.get("post_validation_applied"))
            res_hyde.debug["tier1_payment_guard_applied"] = bool(res_terrain.debug.get("payment_guard_applied"))
            res_hyde.debug["tier1_payment_guard_reason"] = res_terrain.debug.get("payment_guard_reason")
        except Exception:
            pass

        return res_hyde
    except Exception as e:
        try:
            res_terrain.debug["smart_hyde_checked"] = True
            res_terrain.debug["smart_hyde_should_trigger"] = True
            res_terrain.debug["smart_hyde_trigger_reason"] = reason
            res_terrain.debug["hyde_used"] = False
            res_terrain.debug["hyde_trigger_reason"] = reason
            res_terrain.debug["hyde_error"] = str(e)
        except Exception:
            pass
        return res_terrain


async def _route_botlive_intent_dual_inverted(*args, **kwargs) -> BotliveRoutingResult:
    from core.setfit_intent_router_academic import route_botlive_intent as route_academic

    terrain_accept_threshold = float(os.environ.get("BOTLIVE_INVERTED_TERRAIN_ACCEPT_THRESHOLD", "0.75"))

    res_academic = await route_academic(*args, **kwargs)

    academic_intent = str(getattr(res_academic, "intent", "") or "CLARIFICATION").upper()
    if academic_intent != "CLARIFICATION":
        try:
            res_academic.debug["dual_router_mode"] = "inverted"
            res_academic.debug["dual_router_used"] = True
            res_academic.debug["dual_router_stage"] = "ACADEMIC_ONLY"
        except Exception:
            pass
        return res_academic

    res_terrain = await route_botlive_intent(*args, **kwargs)
    terrain_intent = str(getattr(res_terrain, "intent", "") or "CLARIFICATION").upper()
    terrain_conf = float(getattr(res_terrain, "confidence", 0.0) or 0.0)

    choose_terrain = terrain_intent != "CLARIFICATION" and terrain_conf >= float(terrain_accept_threshold)
    chosen = res_terrain if choose_terrain else res_academic

    try:
        chosen.debug["dual_router_mode"] = "inverted"
        chosen.debug["dual_router_used"] = True
        chosen.debug["dual_router_stage"] = "TERRAIN_RESCUE" if choose_terrain else "KEEP_ACADEMIC"
        chosen.debug["dual_router_academic_intent"] = academic_intent
        chosen.debug["dual_router_academic_confidence"] = float(getattr(res_academic, "confidence", 0.0) or 0.0)
        chosen.debug["dual_router_terrain_intent"] = terrain_intent
        chosen.debug["dual_router_terrain_confidence"] = terrain_conf
        chosen.debug["dual_router_terrain_threshold"] = float(terrain_accept_threshold)
    except Exception:
        pass

    return chosen


async def _route_botlive_intent_inverted_hyde(*args, **kwargs) -> BotliveRoutingResult:
    from core.setfit_intent_router_academic import route_botlive_intent as route_academic
    from core.hyde_reformulator import HydeReformulator

    company_id = kwargs.get("company_id")
    message = kwargs.get("message")
    conversation_history = kwargs.get("conversation_history")
    state_compact = kwargs.get("state_compact")

    base_kwargs = dict(kwargs)
    base_kwargs.pop("hyde_pre_enabled", None)

    # Primary: Academic (disable HYDE_PRE to avoid double triggers)
    res_academic = await route_academic(*args, **{**base_kwargs, "hyde_pre_enabled": False})
    academic_intent = str(getattr(res_academic, "intent", "") or "CLARIFICATION").upper()

    if academic_intent != "CLARIFICATION":
        try:
            res_academic.debug["dual_router_mode"] = "inverted_hyde"
            res_academic.debug["dual_router_used"] = True
            res_academic.debug["dual_router_stage"] = "ACADEMIC_ONLY"
            res_academic.debug["hyde_used"] = False
            res_academic.debug["hyde_trigger_reason"] = None
        except Exception:
            pass
        return res_academic

    # Rescue: HYDE reformulation → re-route Academic once
    try:
        reformulator = HydeReformulator()
        ctx = {"conversation_history": str(conversation_history or ""), "state": state_compact or {}}
        hyde_message = await reformulator.reformulate(str(company_id or ""), str(message or ""), ctx)
        res_hyde = await route_academic(
            *args,
            **{**base_kwargs, "message": hyde_message, "hyde_pre_enabled": False},
        )

        try:
            res_hyde.debug["dual_router_mode"] = "inverted_hyde"
            res_hyde.debug["dual_router_used"] = True
            res_hyde.debug["dual_router_stage"] = "HYDE_RESCUE_ACADEMIC"

            res_hyde.debug["hyde_used"] = True
            res_hyde.debug["hyde_trigger_reason"] = "academic_clarification"
            res_hyde.debug["hyde_original_message"] = str(message or "")
            res_hyde.debug["hyde_message"] = str(hyde_message or "")
            res_hyde.debug["tier1_intent"] = academic_intent
            res_hyde.debug["tier1_confidence"] = float(getattr(res_academic, "confidence", 0.0) or 0.0)
        except Exception:
            pass

        return res_hyde
    except Exception as e:
        try:
            res_academic.debug["dual_router_mode"] = "inverted_hyde"
            res_academic.debug["dual_router_used"] = True
            res_academic.debug["dual_router_stage"] = "HYDE_ERROR_RETURN_ACADEMIC"
            res_academic.debug["hyde_used"] = False
            res_academic.debug["hyde_trigger_reason"] = "academic_clarification"
            res_academic.debug["hyde_error"] = str(e)
        except Exception:
            pass
        return res_academic


async def _route_botlive_intent_three_tier(*args, **kwargs) -> BotliveRoutingResult:
    from core.setfit_intent_router_academic import route_botlive_intent as route_academic
    from core.hyde_reformulator import HydeReformulator

    company_id = kwargs.get("company_id")
    user_id = kwargs.get("user_id")
    message = kwargs.get("message")
    conversation_history = kwargs.get("conversation_history")
    state_compact = kwargs.get("state_compact")

    base_kwargs = dict(kwargs)
    base_kwargs.pop("hyde_pre_enabled", None)

    handoff_res, handoff_debug = _global_sav_handoff_if_needed(
        message=str(message or ""),
        company_id=str(company_id or ""),
        user_id=str(user_id or ""),
        conversation_history=str(conversation_history or ""),
        state_compact=state_compact if isinstance(state_compact, dict) else {},
    )
    if handoff_res is not None:
        try:
            handoff_res.debug["dual_router_mode"] = "three_tier"
            handoff_res.debug["dual_router_used"] = True
            handoff_res.debug["dual_router_stage"] = "GLOBAL_HANDOFF"
        except Exception:
            pass
        return handoff_res

    terrain_accept_threshold = float(os.environ.get("BOTLIVE_THREE_TIER_TERRAIN_ACCEPT_THRESHOLD", "0.85"))
    terrain_to_academic_conf_threshold = float(os.environ.get("BOTLIVE_THREE_TIER_TERRAIN_TO_ACADEMIC_THRESHOLD", "0.70"))
    academic_accept_threshold = float(os.environ.get("BOTLIVE_THREE_TIER_ACADEMIC_ACCEPT_THRESHOLD", "0.75"))

    # Tier 1: Terrain (HYDE disabled here; HYDE is tier-3 only)
    res_terrain = await route_botlive_intent(*args, **{**base_kwargs, "hyde_pre_enabled": False})
    terrain_intent = str(getattr(res_terrain, "intent", "") or "CLARIFICATION").upper()
    terrain_conf = float(getattr(res_terrain, "confidence", 0.0) or 0.0)

    tier1_accept = terrain_intent != "CLARIFICATION" and terrain_conf >= float(terrain_accept_threshold)
    if tier1_accept:
        try:
            res_terrain.debug["dual_router_mode"] = "three_tier"
            res_terrain.debug["dual_router_used"] = True
            res_terrain.debug["dual_router_stage"] = "TIER1_TERRAIN_ACCEPT"
            res_terrain.debug["dual_router_threshold_terrain_accept"] = float(terrain_accept_threshold)
            res_terrain.debug["global_handoff_checked"] = True
            res_terrain.debug["global_handoff_result"] = handoff_debug
        except Exception:
            pass
        return res_terrain

    # Tier 2: Academic fallback if low-conf or clarification
    tier2_should_try = terrain_intent == "CLARIFICATION" or terrain_conf < float(terrain_to_academic_conf_threshold)

    res_academic: Optional[BotliveRoutingResult] = None
    if tier2_should_try:
        res_academic = await route_academic(*args, **{**base_kwargs, "hyde_pre_enabled": False})
        academic_intent = str(getattr(res_academic, "intent", "") or "CLARIFICATION").upper()
        academic_conf = float(getattr(res_academic, "confidence", 0.0) or 0.0)

        tier2_accept = academic_intent != "CLARIFICATION" and academic_conf >= float(academic_accept_threshold)
        if tier2_accept:
            try:
                res_academic.debug["dual_router_mode"] = "three_tier"
                res_academic.debug["dual_router_used"] = True
                res_academic.debug["dual_router_stage"] = "TIER2_ACADEMIC_ACCEPT"
                res_academic.debug["dual_router_terrain_intent"] = terrain_intent
                res_academic.debug["dual_router_terrain_confidence"] = terrain_conf
                res_academic.debug["dual_router_threshold_academic_accept"] = float(academic_accept_threshold)
                res_academic.debug["dual_router_threshold_terrain_to_academic"] = float(terrain_to_academic_conf_threshold)
                res_academic.debug["global_handoff_checked"] = True
                res_academic.debug["global_handoff_result"] = handoff_debug
            except Exception:
                pass
            return res_academic

    # Tier 3: HYDE only after double failure (both clarification)
    academic_intent_final = None
    if res_academic is not None:
        academic_intent_final = str(getattr(res_academic, "intent", "") or "CLARIFICATION").upper()

    both_clarification = terrain_intent == "CLARIFICATION" and (academic_intent_final or "CLARIFICATION") == "CLARIFICATION"
    if both_clarification and _truthy_env("BOTLIVE_THREE_TIER_HYDE_ENABLED", "true"):
        try:
            reformulator = HydeReformulator()
            ctx = {"conversation_history": str(conversation_history or ""), "state": state_compact or {}}
            hyde_message = await reformulator.reformulate(str(company_id or ""), str(message or ""), ctx)
            res_hyde = await route_botlive_intent(
                *args,
                **{**base_kwargs, "message": hyde_message, "hyde_pre_enabled": False},
            )

            try:
                res_hyde.debug["dual_router_mode"] = "three_tier"
                res_hyde.debug["dual_router_used"] = True
                res_hyde.debug["dual_router_stage"] = "TIER3_HYDE"
                res_hyde.debug["tier3_hyde_used"] = True
                res_hyde.debug["tier3_hyde_original_message"] = str(message or "")
                res_hyde.debug["tier3_hyde_message"] = str(hyde_message or "")
                res_hyde.debug["dual_router_terrain_intent"] = terrain_intent
                res_hyde.debug["dual_router_terrain_confidence"] = terrain_conf
                if res_academic is not None:
                    res_hyde.debug["dual_router_academic_confidence"] = float(getattr(res_academic, "confidence", 0.0) or 0.0)
                res_hyde.debug["global_handoff_checked"] = True
                res_hyde.debug["global_handoff_result"] = handoff_debug
            except Exception:
                pass
            return res_hyde
        except Exception as e:
            try:
                res_terrain.debug["dual_router_mode"] = "three_tier"
                res_terrain.debug["dual_router_used"] = True
                res_terrain.debug["dual_router_stage"] = "TIER3_HYDE_ERROR_RETURN_TERRAIN"
                res_terrain.debug["tier3_hyde_error"] = str(e)
            except Exception:
                pass
            return res_terrain

    # Default: Terrain baseline (even if low-conf)
    try:
        res_terrain.debug["dual_router_mode"] = "three_tier"
        res_terrain.debug["dual_router_used"] = True
        res_terrain.debug["dual_router_stage"] = "DEFAULT_RETURN_TERRAIN"
        res_terrain.debug["dual_router_terrain_confidence"] = terrain_conf
        if res_academic is not None:
            res_terrain.debug["dual_router_academic_confidence"] = float(getattr(res_academic, "confidence", 0.0) or 0.0)
        res_terrain.debug["global_handoff_checked"] = True
        res_terrain.debug["global_handoff_result"] = handoff_debug
    except Exception:
        pass
    return res_terrain

class ProductionPipeline:
    def __init__(self):
        self.cache_enabled = is_cache_enabled()
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "total": 0,
            "dual_router_total": 0,
            "dual_router_fallbacks": 0,
            "dual_router_terrain_saves": 0,
            "three_tier_total": 0,
            "three_tier_hyde_used": 0,
            "smart_hyde_total": 0,
            "smart_hyde_used": 0,
        }

    @semantic_cache_decorator
    async def route_with_cache(self, *args, **kwargs) -> BotliveRoutingResult:
        dual_mode = (os.environ.get("BOTLIVE_DUAL_ROUTER_MODE", "").strip().lower() or "")
        if dual_mode == "inverted":
            return await _route_botlive_intent_dual_inverted(*args, **kwargs)
        if dual_mode == "inverted_hyde":
            return await _route_botlive_intent_inverted_hyde(*args, **kwargs)
        if dual_mode == "three_tier":
            return await _route_botlive_intent_three_tier(*args, **kwargs)
        if _truthy_env("BOTLIVE_SMART_HYDE_ENABLED", "false"):
            return await _route_botlive_intent_smart_hyde(*args, **kwargs)
        return await route_botlive_intent(*args, **kwargs)

    async def route_message(self, *args, **kwargs) -> Dict[str, Any]:
        t0 = time.perf_counter()
        self.stats["total"] += 1
        cache_hit = False
        result: Optional[BotliveRoutingResult] = None

        # Normalize positional args to kwargs to avoid passing hyde_pre_enabled twice
        # Expected positional order: company_id, user_id, message, conversation_history, state_compact, hyde_pre_enabled
        if args:
            keys = [
                "company_id",
                "user_id",
                "message",
                "conversation_history",
                "state_compact",
                "hyde_pre_enabled",
            ]
            norm_kwargs = dict(kwargs)
            for idx, val in enumerate(args[: len(keys)]):
                if keys[idx] not in norm_kwargs:
                    norm_kwargs[keys[idx]] = val
            kwargs = norm_kwargs
            args = ()

        dual_mode = (os.environ.get("BOTLIVE_DUAL_ROUTER_MODE", "").strip().lower() or "")
        dual_enabled = dual_mode in {"inverted", "inverted_hyde", "three_tier"}
        if dual_enabled:
            self.stats["dual_router_total"] += 1
        if dual_mode == "three_tier":
            self.stats["three_tier_total"] += 1
        if (not dual_enabled) and _truthy_env("BOTLIVE_SMART_HYDE_ENABLED", "false"):
            self.stats["smart_hyde_total"] += 1

        if self.cache_enabled:
            try:
                result = await self.route_with_cache(**kwargs)
                # GPTCache sets a special attribute if hit; check via result.debug if needed
                cache_hit = getattr(result, "_from_cache", False) or result.debug.get("from_cache", False)
            except Exception as e:
                logger.error(f"[PRODUCTION_PIPELINE] Cache error: {e}")
                if dual_mode == "inverted":
                    result = await _route_botlive_intent_dual_inverted(**kwargs)
                elif dual_mode == "inverted_hyde":
                    result = await _route_botlive_intent_inverted_hyde(**kwargs)
                elif dual_mode == "three_tier":
                    result = await _route_botlive_intent_three_tier(**kwargs)
                elif _truthy_env("BOTLIVE_SMART_HYDE_ENABLED", "false"):
                    result = await _route_botlive_intent_smart_hyde(**kwargs)
                else:
                    result = await route_botlive_intent(**kwargs)
        else:
            if dual_mode == "inverted":
                result = await _route_botlive_intent_dual_inverted(**kwargs)
            elif dual_mode == "inverted_hyde":
                result = await _route_botlive_intent_inverted_hyde(**kwargs)
            elif dual_mode == "three_tier":
                result = await _route_botlive_intent_three_tier(**kwargs)
            elif _truthy_env("BOTLIVE_SMART_HYDE_ENABLED", "false"):
                result = await _route_botlive_intent_smart_hyde(**kwargs)
            else:
                result = await route_botlive_intent(**kwargs)
        if cache_hit:
            self.stats["cache_hits"] += 1
        else:
            self.stats["cache_misses"] += 1

        if dual_enabled and result is not None:
            try:
                stage = str(result.debug.get("dual_router_stage", ""))
                if stage in {"KEEP_ACADEMIC", "TERRAIN_RESCUE"}:
                    self.stats["dual_router_fallbacks"] += 1
                if stage == "TERRAIN_RESCUE":
                    self.stats["dual_router_terrain_saves"] += 1
            except Exception:
                pass

        if dual_mode == "three_tier" and result is not None:
            try:
                if bool(result.debug.get("tier3_hyde_used")):
                    self.stats["three_tier_hyde_used"] += 1
            except Exception:
                pass

        if (not dual_enabled) and _truthy_env("BOTLIVE_SMART_HYDE_ENABLED", "false") and result is not None:
            try:
                if bool(result.debug.get("hyde_used")):
                    self.stats["smart_hyde_used"] += 1
            except Exception:
                pass

        model_choice = choose_model(getattr(result, "intent", None), kwargs.get("complexity"))
        stats_out = self.stats.copy()
        try:
            total_3t = int(stats_out.get("three_tier_total", 0) or 0)
            used_3t = int(stats_out.get("three_tier_hyde_used", 0) or 0)
            stats_out["three_tier_hyde_used_pct"] = float(used_3t / total_3t) if total_3t > 0 else 0.0
        except Exception:
            pass
        try:
            total_sh = int(stats_out.get("smart_hyde_total", 0) or 0)
            used_sh = int(stats_out.get("smart_hyde_used", 0) or 0)
            stats_out["smart_hyde_used_pct"] = float(used_sh / total_sh) if total_sh > 0 else 0.0
        except Exception:
            pass
        out = {
            "result": result,
            "cache_hit": cache_hit,
            "llm_model": model_choice.model,
            "llm_routing_reason": model_choice.reason,
            "stats": stats_out,
        }

        if _truthy_env("BOTLIVE_SHADOW_MODE_ENABLED", "false"):
            try:
                latency_ms = float((time.perf_counter() - t0) * 1000.0)

                company_id = kwargs.get("company_id")
                user_id = kwargs.get("user_id")
                message = (kwargs.get("message") or "")
                conversation_id = kwargs.get("conversation_id")

                dbg = {}
                try:
                    if result is not None and isinstance(getattr(result, "debug", None), dict):
                        dbg = dict(result.debug)
                except Exception:
                    dbg = {}

                payload = {
                    "event": "botlive_shadow_routing",
                    "company_id": company_id,
                    "user_id": user_id,
                    "message": message,
                    "conversation_id": conversation_id,
                    "final_intent": (getattr(result, "intent", None) or "UNKNOWN"),
                    "final_conf": float(getattr(result, "confidence", 0.0) or 0.0) if result is not None else 0.0,
                    "mode": getattr(result, "mode", None),
                    "cache_hit": bool(cache_hit),
                    "latency_ms": latency_ms,
                    "dual_router_mode": dbg.get("dual_router_mode"),
                    "dual_router_stage": dbg.get("dual_router_stage"),
                    "hyde_used": bool(dbg.get("hyde_used")),
                    "hyde_stage": dbg.get("hyde_stage"),
                    "hyde_trigger_reason": dbg.get("hyde_trigger_reason"),
                    "hyde_message": dbg.get("hyde_message"),
                    "smart_hyde_checked": dbg.get("smart_hyde_checked"),
                    "smart_hyde_should_trigger": dbg.get("smart_hyde_should_trigger"),
                    "smart_hyde_trigger_reason": dbg.get("smart_hyde_trigger_reason"),
                    "guard_applied": dbg.get("guard_applied"),
                    "guard_reason": dbg.get("guard_reason"),
                    "post_validation_applied": dbg.get("post_validation_applied"),
                    "post_validation_reason": dbg.get("post_validation_reason"),
                    "human_handoff": dbg.get("human_handoff"),
                    "human_handoff_reason": dbg.get("human_handoff_reason"),
                }

                logger.info("BOTLIVE_SHADOW %s", json.dumps(payload, ensure_ascii=False))

                if _truthy_env("BOTLIVE_SHADOW_TO_SUPABASE_ENABLED", "false"):
                    try:
                        asyncio.create_task(_shadow_write_to_supabase(payload))
                    except Exception:
                        pass
            except Exception:
                pass

        return out

    def get_stats(self) -> Dict[str, Any]:
        stats_out = self.stats.copy()
        try:
            total_3t = int(stats_out.get("three_tier_total", 0) or 0)
            used_3t = int(stats_out.get("three_tier_hyde_used", 0) or 0)
            stats_out["three_tier_hyde_used_pct"] = float(used_3t / total_3t) if total_3t > 0 else 0.0
        except Exception:
            pass
        try:
            total_sh = int(stats_out.get("smart_hyde_total", 0) or 0)
            used_sh = int(stats_out.get("smart_hyde_used", 0) or 0)
            stats_out["smart_hyde_used_pct"] = float(used_sh / total_sh) if total_sh > 0 else 0.0
        except Exception:
            pass
        return stats_out
