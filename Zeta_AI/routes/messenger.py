from fastapi import APIRouter, Request

router = APIRouter(prefix="/messenger", tags=["messenger"])


@router.get("/health")
async def messenger_health():
    """Lightweight health check for the messenger router."""
    return {"status": "ok", "service": "messenger"}


@router.post("/webhook")
async def messenger_webhook(request: Request):
    """
    Placeholder endpoint for Messenger webhooks.
    Accepts any JSON payload and returns 200 OK.
    Integrate platform verification and signature checks here later.
    """
    try:
        payload = await request.json()
    except Exception:
        payload = None
    return {"received": True, "payload_present": payload is not None}
