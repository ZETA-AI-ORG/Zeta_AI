"""
Operator Notification System
=============================
When bot_disabled=True (order confirmed + paid), all client messages
bypass Jessica and are routed to the human operator via Supabase notifications.

Table: operator_notifications
Columns: id (uuid), company_id, user_id, message, message_type, order_summary, created_at, read (bool)
"""

import os
import time
import logging
import httpx
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY", "")


def _supabase_headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


def save_operator_notification(
    *,
    company_id: str,
    user_id: str,
    message: str,
    message_type: str = "post_order",
    order_summary: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Save a notification for the human operator in Supabase.
    Returns True on success, False on failure.
    """
    try:
        payload = {
            "company_id": company_id,
            "user_id": user_id,
            "message": message,
            "message_type": message_type,
            "order_summary": order_summary or {},
            "read": False,
        }
        url = f"{SUPABASE_URL}/rest/v1/operator_notifications"
        resp = httpx.post(url, json=payload, headers=_supabase_headers(), timeout=5.0)
        if resp.status_code in (200, 201, 204):
            print(f"🔔 [OPERATOR_NOTIF] Saved for {user_id[:12]}... | type={message_type}")
            return True
        else:
            print(f"⚠️ [OPERATOR_NOTIF] Supabase error {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"⚠️ [OPERATOR_NOTIF] Exception: {e}")
        return False


def get_order_summary_for_notification(user_id: str) -> Dict[str, Any]:
    """
    Build a compact order summary dict from OrderStateTracker for the notification payload.
    """
    try:
        from core.order_state_tracker import order_tracker
        st = order_tracker.get_state(user_id)
        return {
            "produit": str(getattr(st, "produit", "") or ""),
            "produit_details": str(getattr(st, "produit_details", "") or ""),
            "quantite": str(getattr(st, "quantite", "") or ""),
            "zone": str(getattr(st, "zone", "") or ""),
            "numero": str(getattr(st, "numero", "") or ""),
            "paiement": str(getattr(st, "paiement", "") or ""),
        }
    except Exception as e:
        logger.warning(f"[OPERATOR_NOTIF] Error building summary: {e}")
        return {}


def get_notifications(
    company_id: str,
    *,
    unread_only: bool = True,
    limit: int = 50,
) -> list:
    """
    Fetch notifications for a company (used by the GET endpoint).
    """
    try:
        url = f"{SUPABASE_URL}/rest/v1/operator_notifications"
        params = {
            "company_id": f"eq.{company_id}",
            "order": "created_at.desc",
            "limit": str(limit),
            "select": "*",
        }
        if unread_only:
            params["read"] = "eq.false"
        headers = {**_supabase_headers(), "Prefer": "return=representation"}
        resp = httpx.get(url, params=params, headers=headers, timeout=5.0)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"⚠️ [OPERATOR_NOTIF] GET error {resp.status_code}: {resp.text[:200]}")
            return []
    except Exception as e:
        print(f"⚠️ [OPERATOR_NOTIF] GET exception: {e}")
        return []


def mark_notification_read(notification_id: str) -> bool:
    """Mark a single notification as read."""
    try:
        url = f"{SUPABASE_URL}/rest/v1/operator_notifications"
        params = {"id": f"eq.{notification_id}"}
        resp = httpx.patch(
            url,
            params=params,
            json={"read": True},
            headers=_supabase_headers(),
            timeout=5.0,
        )
        return resp.status_code in (200, 204)
    except Exception:
        return False


def mark_all_read(company_id: str, user_id: str) -> bool:
    """Mark all notifications for a user as read (operator opened the conversation)."""
    try:
        url = f"{SUPABASE_URL}/rest/v1/operator_notifications"
        params = {
            "company_id": f"eq.{company_id}",
            "user_id": f"eq.{user_id}",
            "read": "eq.false",
        }
        resp = httpx.patch(
            url,
            params=params,
            json={"read": True},
            headers=_supabase_headers(),
            timeout=5.0,
        )
        return resp.status_code in (200, 204)
    except Exception:
        return False
