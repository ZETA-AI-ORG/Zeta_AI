import os
from typing import Optional, Dict, Any

import httpx

from config import (
    WHATSAPP_API_BASE,
    WHATSAPP_PHONE_NUMBER_ID,
    WHATSAPP_TOKEN,
)


async def send_text(to: str, body: str) -> Dict[str, Any]:
    """Envoie un message texte via WhatsApp Cloud API.
    Args:
        to: numéro du client (format international, ex: 2250700000000)
        body: contenu texte
    Returns: dict avec status/meta (ou erreur)
    """
    if not WHATSAPP_PHONE_NUMBER_ID or not WHATSAPP_TOKEN:
        return {"ok": False, "error": "WHATSAPP credentials missing"}

    url = f"{WHATSAPP_API_BASE.rstrip('/')}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body[:4096] if body else ""},
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, headers=headers, json=payload)
    try:
        data = resp.json()
    except Exception:
        data = {"text": resp.text}

    return {"ok": resp.status_code in (200, 201), "status": resp.status_code, "data": data}
