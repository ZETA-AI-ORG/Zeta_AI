import os
import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ilbihprkxcgsigvueeme.supabase.co")
SUPABASE_KEY = os.getenv(
    "SUPABASE_SERVICE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlsYmlocHJreGNnc2lndnVlZW1lIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTEzMTQwNCwiZXhwIjoyMDY0NzA3NDA0fQ.Zf0EJbmP5ePGBZL5cY1tFP9FDRvJXDZ3x98zUS993GA",
)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}


async def log_intervention_in_conversation_logs(
    company_id_text: str,
    user_id: str,
    message: str,
    metadata: Dict[str, Any],
    *,
    channel: str = "botlive",
    direction: str = "system",
    conversation_id: Optional[str] = None,
    source: str = "backend",
) -> bool:
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("[INTERVENTION_LOGGER] Missing Supabase configuration")
        return False

    url = f"{SUPABASE_URL}/rest/v1/conversation_logs"
    payload: Dict[str, Any] = {
        "company_id_text": company_id_text,
        "channel": channel,
        "user_id": user_id,
        "direction": direction,
        "message": message,
        "source": source,
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
            logger.error(
                "[INTERVENTION_LOGGER] Failed to insert into conversation_logs: %s %s",
                resp.status_code,
                resp.text[:200],
            )
            return False
        logger.info(
            "[INTERVENTION_LOGGER] Intervention conversation_log inserted successfully | status=%s",
            resp.status_code,
        )
        return True
    except Exception as e:
        logger.error("[INTERVENTION_LOGGER] Exception while inserting conversation_log: %s", e)
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

    url = f"{SUPABASE_URL}/rest/v1/conversation_logs"
    payload: Dict[str, Any] = {
        "company_id_text": company_id_text,
        "channel": channel,
        "user_id": user_id,
        "direction": direction,
        "message": message,
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
            logger.error(
                "[INTERVENTION_LOGGER] Failed to insert message into conversation_logs: %s %s",
                resp.status_code,
                resp.text[:200],
            )
            return False
        return True
    except Exception as e:
        logger.error("[INTERVENTION_LOGGER] Exception while inserting message log: %s", e)
        return False
