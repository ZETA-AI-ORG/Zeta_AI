"""
🔔 NOTIFICATIONS API - Push Notifications + CRUD
Handles operator notifications and Web Push subscriptions
"""

import os
import json
import logging
import asyncio
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# ─── VAPID Config ───────────────────────────────────────────────
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_CLAIMS_EMAIL = os.getenv("VAPID_CLAIMS_EMAIL", "mailto:admin@zeta-ai.com")


def _get_supabase_headers():
    """Return Supabase REST headers using service key."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    return url, headers


# ─── Pydantic Models ────────────────────────────────────────────

class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscriptionRequest(BaseModel):
    company_id: str
    operator_id: Optional[str] = None
    endpoint: str
    keys: PushSubscriptionKeys


class MarkReadRequest(BaseModel):
    notification_id: str


class MarkAllReadRequest(BaseModel):
    user_id: str


class ReactivateBotRequest(BaseModel):
    company_id: str
    user_id: str


class SendTestPushRequest(BaseModel):
    company_id: str
    title: Optional[str] = "Test Notification"
    body: Optional[str] = "Push notifications are working!"


# ─── GET /api/notifications/{company_id} ────────────────────────

@router.get("/api/notifications/{company_id}")
async def get_notifications(
    company_id: str,
    unread_only: bool = False,
    limit: int = 50,
):
    """Fetch operator notifications for a company."""
    import httpx

    url, headers = _get_supabase_headers()
    rest_url = f"{url}/rest/v1/operator_notifications"

    params = {
        "company_id": f"eq.{company_id}",
        "order": "created_at.desc",
        "limit": str(limit),
        "select": "*",
    }
    if unread_only:
        params["read"] = "eq.false"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(rest_url, headers=headers, params=params)

        if resp.status_code == 200:
            data = resp.json() or []
            unread = sum(1 for n in data if not n.get("read", False))
            return {"notifications": data, "count": unread, "total": len(data)}
        else:
            logger.error(f"[NOTIF] Supabase error {resp.status_code}: {resp.text}")
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
    except httpx.HTTPError as e:
        logger.exception("[NOTIF] HTTP error fetching notifications")
        raise HTTPException(status_code=502, detail=str(e))


# ─── PATCH /api/notifications/read ──────────────────────────────

@router.patch("/api/notifications/read")
async def mark_notification_read(req: MarkReadRequest):
    """Mark a single notification as read."""
    import httpx

    url, headers = _get_supabase_headers()
    rest_url = f"{url}/rest/v1/operator_notifications"
    params = {"id": f"eq.{req.notification_id}"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.patch(
                rest_url,
                headers=headers,
                params=params,
                json={"read": True},
            )

        if resp.status_code in (200, 204):
            return {"status": "ok", "notification_id": req.notification_id}
        else:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e))


# ─── POST /api/notifications/{company_id}/read_all ──────────────

@router.post("/api/notifications/{company_id}/read_all")
async def mark_all_read(company_id: str, req: MarkAllReadRequest):
    """Mark all notifications for a user as read."""
    import httpx

    url, headers = _get_supabase_headers()
    rest_url = f"{url}/rest/v1/operator_notifications"
    params = {
        "company_id": f"eq.{company_id}",
        "user_id": f"eq.{req.user_id}",
        "read": "eq.false",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.patch(
                rest_url,
                headers=headers,
                params=params,
                json={"read": True},
            )

        if resp.status_code in (200, 204):
            return {"status": "ok", "company_id": company_id, "user_id": req.user_id}
        else:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e))


# ─── POST /api/bot/reactivate ───────────────────────────────────

@router.post("/api/bot/reactivate")
async def reactivate_bot(req: ReactivateBotRequest):
    """Reactivate the RAG bot for a user (unpause)."""
    try:
        from core.order_state_tracker import order_tracker

        order_tracker.set_flag(req.user_id, "bot_paused", False)
        return {
            "status": "ok",
            "company_id": req.company_id,
            "user_id": req.user_id,
            "bot_active": True,
        }
    except Exception as e:
        logger.exception("[NOTIF] Error reactivating bot")
        raise HTTPException(status_code=500, detail=str(e))


# ─── GET /api/push/vapid-public-key ─────────────────────────────

@router.get("/api/push/vapid-public-key")
async def get_vapid_public_key():
    """Return the VAPID public key so the frontend can subscribe."""
    if not VAPID_PUBLIC_KEY:
        raise HTTPException(status_code=500, detail="VAPID keys not configured")
    return {"publicKey": VAPID_PUBLIC_KEY}


# ─── POST /api/push/subscribe ───────────────────────────────────

@router.post("/api/push/subscribe")
async def subscribe_push(req: PushSubscriptionRequest):
    """Store a push subscription for an operator."""
    import httpx

    url, headers = _get_supabase_headers()
    rest_url = f"{url}/rest/v1/push_subscriptions"

    subscription_data = {
        "company_id": req.company_id,
        "operator_id": req.operator_id or "default",
        "endpoint": req.endpoint,
        "p256dh": req.keys.p256dh,
        "auth": req.keys.auth,
        "created_at": datetime.utcnow().isoformat(),
        "active": True,
    }

    try:
        # Upsert by endpoint (one device = one subscription)
        headers_upsert = {**headers, "Prefer": "resolution=merge-duplicates,return=representation"}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                rest_url,
                headers=headers_upsert,
                json=subscription_data,
            )

        if resp.status_code in (200, 201):
            logger.info(f"[PUSH] Subscription stored for company={req.company_id}")
            return {"status": "ok", "message": "Subscription saved"}
        else:
            logger.error(f"[PUSH] Supabase error {resp.status_code}: {resp.text}")
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e))


# ─── POST /api/push/unsubscribe ─────────────────────────────────

@router.post("/api/push/unsubscribe")
async def unsubscribe_push(req: PushSubscriptionRequest):
    """Remove a push subscription."""
    import httpx

    url, headers = _get_supabase_headers()
    rest_url = f"{url}/rest/v1/push_subscriptions"
    params = {"endpoint": f"eq.{req.endpoint}"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.delete(rest_url, headers=headers, params=params)

        return {"status": "ok", "message": "Subscription removed"}
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e))


# ─── Internal: send push to all subscribers of a company ────────

async def send_push_to_company(company_id: str, title: str, body: str, data: dict = None, icon: str = "/favicon.ico"):
    """
    Send a Web Push notification to ALL subscribers of a company.
    Called internally when a new operator_notification is created.
    """
    if not VAPID_PRIVATE_KEY or not VAPID_PUBLIC_KEY:
        logger.warning("[PUSH] VAPID keys not configured, skipping push")
        return 0

    import httpx

    url, headers = _get_supabase_headers()
    rest_url = f"{url}/rest/v1/push_subscriptions"
    params = {
        "company_id": f"eq.{company_id}",
        "active": "eq.true",
        "select": "endpoint,p256dh,auth",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(rest_url, headers=headers, params=params)

        if resp.status_code != 200:
            logger.error(f"[PUSH] Failed to fetch subscriptions: {resp.status_code}")
            return 0

        subscriptions = resp.json() or []
        if not subscriptions:
            logger.info(f"[PUSH] No active subscriptions for company={company_id}")
            return 0

        sent = 0
        payload = json.dumps({
            "title": title,
            "body": body,
            "icon": icon,
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat(),
        })

        from pywebpush import webpush, WebPushException

        for sub in subscriptions:
            try:
                subscription_info = {
                    "endpoint": sub["endpoint"],
                    "keys": {
                        "p256dh": sub["p256dh"],
                        "auth": sub["auth"],
                    },
                }
                webpush(
                    subscription_info=subscription_info,
                    data=payload,
                    vapid_private_key=VAPID_PRIVATE_KEY,
                    vapid_claims={"sub": VAPID_CLAIMS_EMAIL},
                )
                sent += 1
            except WebPushException as e:
                logger.warning(f"[PUSH] Failed to send to {sub['endpoint'][:50]}...: {e}")
                # If subscription expired (410 Gone), deactivate it
                if "410" in str(e) or "404" in str(e):
                    await _deactivate_subscription(sub["endpoint"])
            except Exception as e:
                logger.warning(f"[PUSH] Unexpected error: {e}")

        logger.info(f"[PUSH] Sent {sent}/{len(subscriptions)} push notifications for company={company_id}")
        return sent

    except Exception as e:
        logger.exception(f"[PUSH] Error sending push notifications: {e}")
        return 0


async def _deactivate_subscription(endpoint: str):
    """Mark a subscription as inactive (expired/unsubscribed)."""
    import httpx

    url, headers = _get_supabase_headers()
    rest_url = f"{url}/rest/v1/push_subscriptions"
    params = {"endpoint": f"eq.{endpoint}"}

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.patch(
                rest_url, headers=headers, params=params, json={"active": False}
            )
    except Exception:
        pass


# ─── POST /api/push/test ────────────────────────────────────────

@router.post("/api/push/test")
async def test_push(req: SendTestPushRequest):
    """Send a test push notification to all subscribers of a company."""
    sent = await send_push_to_company(
        company_id=req.company_id,
        title=req.title,
        body=req.body,
        data={"type": "test"},
    )
    return {"status": "ok", "sent": sent}


# ─── Helper: create notification + trigger push ─────────────────

async def create_notification_and_push(
    company_id: str,
    user_id: str,
    message: str,
    message_type: str = "operator_needed",
    order_summary: dict = None,
):
    """
    Insert a new operator_notification in Supabase AND send a push notification.
    Call this from botlive or any backend code that needs to alert operators.
    """
    import httpx
    import uuid

    url, headers = _get_supabase_headers()
    rest_url = f"{url}/rest/v1/operator_notifications"

    notification = {
        "id": str(uuid.uuid4()),
        "company_id": company_id,
        "user_id": user_id,
        "message": message,
        "message_type": message_type,
        "order_summary": json.dumps(order_summary) if order_summary else None,
        "read": False,
        "created_at": datetime.utcnow().isoformat(),
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(rest_url, headers=headers, json=notification)

        if resp.status_code in (200, 201):
            logger.info(f"[NOTIF] Created notification for company={company_id} user={user_id}")
        else:
            logger.error(f"[NOTIF] Failed to create notification: {resp.status_code} {resp.text}")

        # Fire push notification in background
        asyncio.create_task(
            send_push_to_company(
                company_id=company_id,
                title="Nouvelle intervention requise",
                body=message[:200],
                data={
                    "type": "operator_needed",
                    "user_id": user_id,
                    "notification_id": notification["id"],
                },
            )
        )

        return notification

    except Exception as e:
        logger.exception(f"[NOTIF] Error creating notification: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# INCOMING MESSAGE SIGNAL — called by N8N HTTP node
# ═══════════════════════════════════════════════════════════════

class IncomingSignalRequest(BaseModel):
    company_id: str
    user_id: str
    channel: Optional[str] = "messenger"
    display_name: Optional[str] = None
    message_preview: Optional[str] = None
    message_preview_image: Optional[str] = None


@router.post("/api/incoming-signal")
async def incoming_signal(req: IncomingSignalRequest):
    """
    Called by N8N right after the webhook receives a customer message.
    Stores/increments unread count for this user so the operator dashboard
    can show the orange unread badge.
    """
    import httpx

    url, headers = _get_supabase_headers()
    rest_url = f"{url}/rest/v1/incoming_signals"

    preview = (req.message_preview or "").strip()
    if not preview and (req.message_preview_image or "").strip():
        preview = "📎 Image reçue"
    if not preview:
        preview = "Nouveau message"

    try:
        # Preferred: atomic DB-side upsert (no race condition, scalable)
        rpc_url = f"{url}/rest/v1/rpc/incoming_signal_upsert"
        rpc_payload = {
            "p_company_id": req.company_id,
            "p_user_id": req.user_id,
            "p_channel": req.channel or "messenger",
            "p_display_name": req.display_name or "",
            "p_message_preview": preview[:200],
        }

        async with httpx.AsyncClient(timeout=8) as client:
            rpc_resp = await client.post(rpc_url, headers=headers, json=rpc_payload)

        if rpc_resp.status_code in (200, 201):
            data = rpc_resp.json() or []
            unread = None
            if isinstance(data, list) and data:
                unread = data[0].get("unread_count")
            elif isinstance(data, dict):
                unread = data.get("unread_count")

            # Best-effort: also create an operator notification so the operator UI
            # can show a list of recent incoming messages.
            async def _best_effort_create_operator_notification():
                try:
                    op_url = f"{url}/rest/v1/operator_notifications"
                    msg = preview.strip()[:500]
                    payload = {
                        "company_id": req.company_id,
                        "user_id": req.user_id,
                        "message": msg or "Nouveau message",
                        "message_type": "incoming_message",
                        "read": False,
                    }
                    async with httpx.AsyncClient(timeout=5) as client:
                        await client.post(op_url, headers=headers, json=payload)
                except Exception:
                    return

            asyncio.create_task(_best_effort_create_operator_notification())

            logger.info(
                "[INCOMING] Signal upserted (rpc): company=%s user=%s unread=%s",
                req.company_id,
                req.user_id,
                unread,
            )

            # ── Fire push notification to all subscribed devices ──────────
            # This is what makes the OS banner appear when the app is closed.
            display = req.display_name or f"Client {req.user_id[-4:]}"
            asyncio.create_task(
                send_push_to_company(
                    company_id=req.company_id,
                    title=display,
                    body=preview,
                    data={
                        "type": "incoming_message",
                        "user_id": req.user_id,
                        "channel": req.channel or "messenger",
                        "category": "message",
                    },
                )
            )

            return {"status": "ok", "unread_count": unread}

        # If RPC is missing/blocked, fallback to REST upsert (may still race but avoids 409)
        if rpc_resp.status_code in (404, 400):
            upsert_headers = {**headers, "Prefer": "resolution=merge-duplicates,return=representation"}
            payload = {
                "company_id": req.company_id,
                "user_id": req.user_id,
                "channel": req.channel or "messenger",
                "display_name": req.display_name or "",
                "message_preview": preview[:200],
                "is_typing": True,
                "last_message_at": datetime.utcnow().isoformat(),
            }
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.post(rest_url, headers=upsert_headers, json=payload)
            if resp.status_code in (200, 201):
                display = req.display_name or f"Client {req.user_id[-4:]}"
                asyncio.create_task(
                    send_push_to_company(
                        company_id=req.company_id,
                        title=display,
                        body=preview,
                        data={
                            "type": "incoming_message",
                            "user_id": req.user_id,
                            "channel": req.channel or "messenger",
                            "category": "message",
                        },
                    )
                )
                return {"status": "ok"}

        logger.error("[INCOMING] Supabase RPC error %s: %s", rpc_resp.status_code, rpc_resp.text)
        raise HTTPException(status_code=rpc_resp.status_code, detail=rpc_resp.text)

    except httpx.HTTPError as e:
        logger.exception("[INCOMING] HTTP error")
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/api/incoming-signals/{company_id}")
async def get_incoming_signals(company_id: str):
    """
    Returns all unread signals for a company (unread_count > 0).
    Frontend polls this to show orange badges on conversation list.
    """
    import httpx

    url, headers = _get_supabase_headers()
    rest_url = f"{url}/rest/v1/incoming_signals"

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(
                rest_url,
                headers=headers,
                params={
                    "company_id": f"eq.{company_id}",
                    "unread_count": "gt.0",
                    "select": "user_id,unread_count,last_message_at,is_typing,channel,display_name,message_preview",
                },
            )

        if resp.status_code == 200:
            data = resp.json() or []
            return {"signals": data}
        else:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/api/incoming-signals/{company_id}/clear/{user_id}")
async def clear_unread(company_id: str, user_id: str):
    """
    Called when operator opens a conversation — resets unread count to 0
    and clears typing indicator.
    """
    import httpx

    url, headers = _get_supabase_headers()
    rest_url = f"{url}/rest/v1/incoming_signals"

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.patch(
                rest_url,
                headers=headers,
                params={
                    "company_id": f"eq.{company_id}",
                    "user_id": f"eq.{user_id}",
                },
                json={"unread_count": 0, "is_typing": False},
            )

        return {"status": "ok"}
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/api/incoming-signals/clear-typing")
async def clear_typing(req: IncomingSignalRequest):
    """
    Called after bot responds — clears the typing indicator.
    """
    import httpx

    url, headers = _get_supabase_headers()
    rest_url = f"{url}/rest/v1/incoming_signals"

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.patch(
                rest_url,
                headers=headers,
                params={
                    "company_id": f"eq.{req.company_id}",
                    "user_id": f"eq.{req.user_id}",
                },
                json={"is_typing": False},
            )
        return {"status": "ok"}
    except Exception:
        return {"status": "ok"}
