import os
import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}

# Permet de désactiver complètement les logs Supabase en cas de contraintes DB trop strictes
ENABLE_CONVERSATION_LOGS = os.getenv("ENABLE_INTERVENTION_LOGGER", "true").strip().lower() in {"1", "true", "yes", "y", "on"}

async def log_intervention_in_conversation_logs(
    company_id_text: str,
    user_id: str,
    message: str,
    metadata: Dict[str, Any],
    *,
    channel: str = "botlive",
    direction: str = "assistant",
    conversation_id: Optional[str] = None,
    source: str = "backend",
) -> bool:
    if not ENABLE_CONVERSATION_LOGS:
        return False
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("[INTERVENTION_LOGGER] Missing Supabase configuration")
        return False

    # Normaliser le message: éviter les valeurs nulles/vides et tronquer à 2000 caractères
    base_message = message or ""
    if not base_message.strip():
        base_message = "[Message vide]"
    truncated_message = base_message[:2000]

    url = f"{SUPABASE_URL}/rest/v1/conversation_logs"
    payload: Dict[str, Any] = {
        "company_id_text": company_id_text,
        "channel": channel,
        "user_id": user_id,
        "direction": direction,
        "message": truncated_message,
        "content": truncated_message,
        "source": source,
        "status": "active",
        "metadata": metadata or {},
    }
    if conversation_id:
        payload["conversation_id"] = conversation_id

    try:
        logger.info(
            "[INTERVENTION_LOGGER] Insert intervention conversation_log | company=%s user=%s source=%s needs_intervention=%s reason=%s priority=%s",
            company_id_text,
            user_id,
            source,
            (metadata or {}).get("needs_intervention"),
            (metadata or {}).get("reason"),
            (metadata or {}).get("priority"),
        )
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, headers=HEADERS, json=payload)
        if resp.status_code not in (200, 201):
            none_fields = [k for k, v in payload.items() if v is None]
            logger.error(
                "[INTERVENTION_LOGGER] Failed to insert into conversation_logs: %s %s | none_fields=%s | message_len=%s | message_preview=%r",
                resp.status_code,
                resp.text[:800],
                none_fields,
                len(str(payload.get("message") or "")),
                (str(payload.get("message") or "")[:160]),
            )
            return False
        logger.info(
            "[INTERVENTION_LOGGER] Intervention conversation_log inserted successfully | status=%s",
            resp.status_code,
        )

        # Fire push notification to operator(s)
        try:
            from routes.notifications import create_notification_and_push
            import asyncio

            reason = (metadata or {}).get("reason", "intervention")
            push_message = truncated_message[:200]
            asyncio.ensure_future(
                create_notification_and_push(
                    company_id=company_id_text,
                    user_id=user_id,
                    message=push_message,
                    message_type=reason,
                )
            )
        except Exception as push_err:
            logger.warning("[INTERVENTION_LOGGER] Push notification failed (non-blocking): %s", push_err)

        return True
    except Exception as e:
        logger.error("[INTERVENTION_LOGGER] Exception while inserting conversation_log: %s", e)
        return False


async def upsert_required_intervention(
    company_id: str,
    user_id: str,
    *,
    channel: str = "whatsapp",
    intervention_type: str = "explicit_handoff",
    priority: str = "normal",
    detected_by: str = "rule_based",
    source_bot: str = "botlive",
    confidence: float = None,
    reason: str = "",
    signals: dict = None,
    user_message: str = "",
    bot_response: str = "",
    conversation_snippet: str = "",
    order_state: dict = None,
) -> bool:
    """Insert or update an intervention in the required_interventions table via Supabase RPC."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("[INTERVENTION_LOGGER] Missing Supabase config for upsert_required_intervention")
        return False

    # Map detected_by to valid DB enum values
    valid_detected_by = {
        "rule_based", "intervention_guardian_v1", "cooperative_mode",
        "post_recap", "system", "manual",
    }
    if detected_by not in valid_detected_by:
        detected_by = "rule_based"  # fallback for context_rules etc.

    # Map source_bot to valid DB enum
    valid_source_bot = {"botlive", "ragbot", "botliveandrag"}
    if source_bot not in valid_source_bot:
        source_bot = "botliveandrag"

    url = f"{SUPABASE_URL}/rest/v1/rpc/upsert_required_intervention"
    payload = {
        "p_company_id": company_id,
        "p_user_id": user_id,
        "p_channel": channel or "whatsapp",
        "p_type": intervention_type,
        "p_priority": priority or "normal",
        "p_detected_by": detected_by,
        "p_source_bot": source_bot,
        "p_confidence": confidence,
        "p_reason": (reason or "")[:2000],
        "p_signals": signals or {},
        "p_user_message": (user_message or "")[:2000],
        "p_bot_response": (bot_response or "")[:2000],
        "p_conversation_snippet": (conversation_snippet or "")[:2000],
        "p_order_state": order_state or {},
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, headers=HEADERS, json=payload)
        if resp.status_code not in (200, 201):
            logger.error(
                "[INTERVENTION_LOGGER] upsert_required_intervention failed: %s %s",
                resp.status_code, resp.text[:500],
            )
            return False
        logger.info(
            "[INTERVENTION_LOGGER] ✅ required_intervention upserted | company=%s user=%s type=%s priority=%s",
            company_id, user_id, intervention_type, priority,
        )
        return True
    except Exception as e:
        logger.error("[INTERVENTION_LOGGER] Exception in upsert_required_intervention: %s", e)
        return False


async def log_message_in_conversation_logs(
    company_id_text: str,
    user_id: str,
    message: str,
    *,
    channel: str = "botlive",
    direction: str = "user",
    conversation_id: Optional[str] = None,
    source: str = "botlive",
    status: str = "active",
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("[INTERVENTION_LOGGER] Missing Supabase configuration for log_message")
        return False

    # Align direction with DB constraint (user/assistant)
    if direction not in {"user", "assistant"}:
        direction = "assistant" if str(direction).strip().lower() != "user" else "user"

    # Normaliser le message utilisateur aussi pour éviter les contraintes côté DB
    base_message = message or ""
    if not base_message.strip():
        base_message = "[Message vide]"
    truncated_message = base_message[:2000]

    url = f"{SUPABASE_URL}/rest/v1/conversation_logs"
    payload: Dict[str, Any] = {
        "company_id_text": company_id_text,
        "channel": channel,
        "user_id": user_id,
        "direction": direction,
        "message": truncated_message,
        "content": truncated_message,
        "source": source,
        "status": status,
        "metadata": metadata or {},
    }
    if conversation_id:
        payload["conversation_id"] = conversation_id

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, headers=HEADERS, json=payload)
        if resp.status_code not in (200, 201):
            none_fields = [k for k, v in payload.items() if v is None]
            logger.error(
                "[INTERVENTION_LOGGER] Failed to insert message into conversation_logs: %s %s | none_fields=%s | message_len=%s | message_preview=%r",
                resp.status_code,
                resp.text[:800],
                none_fields,
                len(str(payload.get("message") or "")),
                (str(payload.get("message") or "")[:160]),
            )
            return False
        return True
    except Exception as e:
        logger.error("[INTERVENTION_LOGGER] Exception while inserting message log: %s", e)
        return False
