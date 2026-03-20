from fastapi import APIRouter, Request, HTTPException
from typing import Dict, Any, Optional
import logging
import httpx

from config import (
    WHATSAPP_VERIFY_TOKEN,
    WHATSAPP_DEFAULT_COMPANY_ID,
    WHATSAPP_AUTO_REPLY_ENABLED,
    N8N_API_KEY,
    N8N_DEBUG_MODE,
    N8N_PRODUCTION_WEBHOOK_URL_FIXE,
    N8N_TEST_WEBHOOK_URL_FIXE,
)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])
logger = logging.getLogger(__name__)

DEFAULT_N8N_PRODUCTION_WEBHOOK_URL = "https://n8n.zetaapp.xyz/webhook/whatsapp-inbound"
DEFAULT_N8N_TEST_WEBHOOK_URL = "https://n8n.zetaapp.xyz/webhook-test/whatsapp-inbound"


def _get_n8n_inbound_webhook_url() -> Optional[str]:
    test_url = N8N_TEST_WEBHOOK_URL_FIXE or DEFAULT_N8N_TEST_WEBHOOK_URL
    prod_url = N8N_PRODUCTION_WEBHOOK_URL_FIXE or DEFAULT_N8N_PRODUCTION_WEBHOOK_URL
    if N8N_DEBUG_MODE:
        return test_url
    return prod_url or test_url


@router.get("/webhook")
async def whatsapp_verify(request: Request):
    """Vérification webhook (Meta)"""
    # Meta envoie: hub.mode, hub.verify_token, hub.challenge
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN and challenge:
        try:
            return int(challenge)
        except Exception:
            return challenge
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def whatsapp_webhook(request: Request):
    """Réception des messages WhatsApp Cloud API.
    - Shadow Mode: enregistre les messages client
    - Option: auto-reply via LLM, puis envoi via WhatsApp
    """
    try:
        payload: Dict[str, Any] = await request.json()
    except Exception as e:
        logger.error(f"[WHATSAPP] Invalid JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    entries = (payload or {}).get("entry") or []
    if not entries:
        return {"received": True}

    # company_id peut être passé en query (?company_id=...) sinon défaut
    company_id = request.query_params.get("company_id") or WHATSAPP_DEFAULT_COMPANY_ID

    # Parcourir tous les messages
    for entry in entries:
        for change in (entry.get("changes") or []):
            value = change.get("value") or {}
            messages = value.get("messages") or []
            for m in messages:
                user_id = m.get("from")  # numéro international
                if not user_id:
                    continue
                text = (m.get("text") or {}).get("body") or ""
                # Extra metadata
                client_id = request.query_params.get("clientId")
                phone_number_id = (value.get("metadata") or {}).get("phone_number_id")
                contacts = value.get("contacts") or []
                user_display_name = None
                if contacts:
                    user_display_name = (contacts[0].get("profile") or {}).get("name")

                # Shadow Mode capture
                try:
                    from core.shadow_recorder import record_user_message
                    await record_user_message(company_id, user_id, text, user_display_name=user_display_name)
                except Exception as rec_err:
                    logger.warning(f"[WHATSAPP] Shadow record failed: {rec_err}")

                # Log conversation/message for operator UI
                try:
                    from core.conversations_manager import get_or_create_conversation, insert_message
                    conv_id = await get_or_create_conversation(company_id, user_id)
                    if conv_id:
                        await insert_message(
                            conv_id,
                            "user",
                            text or "",
                            {
                                "source": "whatsapp",
                                "channel": "whatsapp",
                                "author_name": (user_display_name or user_id[-4:]),
                            },
                        )
                except Exception as log_err:
                    logger.warning(f"[WHATSAPP] conv log failed: {log_err}")

                # Log also in conversation_logs for unified frontend inbox
                try:
                    from core.intervention_logger import log_message_in_conversation_logs
                    meta: Dict[str, Any] = {
                        "trigger": "user_message",
                        "client_id": client_id,
                        "phone_number_id": phone_number_id,
                        "wa_message_id": m.get("id"),
                    }
                    if user_display_name:
                        meta["user_display_name"] = user_display_name
                    await log_message_in_conversation_logs(
                        company_id_text=company_id,
                        user_id=user_id,
                        message=text or "",
                        channel="whatsapp",
                        direction="user",
                        conversation_id=locals().get("conv_id"),
                        source="whatsapp_webhook",
                        status="active",
                        metadata=meta,
                    )
                except Exception as clog_err:
                    logger.warning(f"[WHATSAPP] conversation_logs insert failed: {clog_err}")

                # Forward inbound WhatsApp event to n8n workflow if configured
                try:
                    n8n_webhook_url = _get_n8n_inbound_webhook_url()
                    if n8n_webhook_url:
                        n8n_payload: Dict[str, Any] = {
                            "merchant_id": company_id,
                            "clientId": client_id,
                            "phone_number_id": phone_number_id,
                            "from": user_id,
                            "name": user_display_name or "Client",
                            "body": text,
                            "timestamp": m.get("timestamp"),
                            "message_id": m.get("id"),
                            "type": m.get("type") or "text",
                            "raw": m,
                        }

                        headers: Dict[str, str] = {}
                        if N8N_API_KEY:
                            headers["X-N8N-API-KEY"] = N8N_API_KEY

                        async with httpx.AsyncClient(timeout=10.0) as client:
                            n8n_response = await client.post(
                                n8n_webhook_url,
                                json=n8n_payload,
                                headers=headers,
                            )

                        if n8n_response.status_code not in (200, 201, 202, 204):
                            logger.warning(
                                "[WHATSAPP] n8n inbound webhook returned status=%s body=%s",
                                n8n_response.status_code,
                                n8n_response.text[:500],
                            )
                    else:
                        logger.info("[WHATSAPP] n8n inbound webhook not configured; skipping forward")
                except Exception as n8n_err:
                    logger.warning(f"[WHATSAPP] n8n forward failed: {n8n_err}")

                # Auto-reply optionnel
                if WHATSAPP_AUTO_REPLY_ENABLED and text:
                    try:
                        # Appeler le moteur botlive pour générer une réponse
                        from app import _botlive_handle
                        # Conversation history vide pour v1 (le handler est robuste)
                        bot_reply = await _botlive_handle(company_id=company_id, user_id=user_id, message=text, images=[], conversation_history="")

                        # Envoyer via WhatsApp
                        if isinstance(bot_reply, str) and bot_reply:
                            try:
                                from core.meta_whatsapp import send_text
                                await send_text(user_id, bot_reply)
                            except Exception as send_err:
                                logger.error(f"[WHATSAPP] Send error: {send_err}")
                    except Exception as gen_err:
                        logger.error(f"[WHATSAPP] Auto-reply error: {gen_err}")

    return {"received": True}
