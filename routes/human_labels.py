import os
import asyncio
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

router = APIRouter()


class HumanLabelCreateRequest(BaseModel):
    company_id: str
    conversation_id: str
    original_message: str
    true_intent: str
    message_id: str | None = None
    resolution_action: str | None = None
    notes: str | None = None
    agent_id: str | None = None
    resolved: bool | None = None
    resolution_time_ms: int | None = None
    satisfaction_score: int | None = None


def _require_api_key(x_api_key: str | None) -> None:
    expected = (os.getenv("HUMAN_LABELS_API_KEY") or "").strip()
    if not expected:
        raise HTTPException(status_code=500, detail="HUMAN_LABELS_API_KEY not configured")
    if (x_api_key or "").strip() != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.get("/human-labels/health")
async def human_labels_health():
    return {"ok": True, "router": "human_labels"}


@router.get("/human-labels/whoami")
async def human_labels_whoami():
    expected = (os.getenv("HUMAN_LABELS_API_KEY") or "").strip()
    return {"api_key_configured": bool(expected)}


@router.post("/human-labels")
async def create_human_label(payload: HumanLabelCreateRequest, x_api_key: str | None = Header(default=None, alias="X-API-KEY")):
    _require_api_key(x_api_key)

    from database.supabase_client import get_supabase_client

    client = get_supabase_client()

    row = {
        "company_id": payload.company_id,
        "conversation_id": payload.conversation_id,
        "message_id": payload.message_id,
        "original_message": payload.original_message,
        "true_intent": payload.true_intent,
        "resolution_action": payload.resolution_action,
        "notes": payload.notes,
        "agent_id": payload.agent_id,
        "resolved": payload.resolved,
        "resolution_time_ms": payload.resolution_time_ms,
        "satisfaction_score": payload.satisfaction_score,
    }

    try:
        res = await asyncio.to_thread(lambda: client.table("human_labels").insert(row).execute())
        data = getattr(res, "data", None)
        return {"ok": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/human-labels/form", response_class=HTMLResponse)
async def human_labels_form(x_api_key: str | None = None):
    html = """
<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
  <title>Human Label</title>
</head>
<body>
  <h3>Human Label</h3>
  <form id=\"f\">
    <label>Company ID<br><input name=\"company_id\" required></label><br><br>
    <label>Conversation ID<br><input name=\"conversation_id\" required></label><br><br>
    <label>Message ID<br><input name=\"message_id\"></label><br><br>
    <label>Original message<br><textarea name=\"original_message\" required rows=\"3\" cols=\"60\"></textarea></label><br><br>
    <label>True intent<br><input name=\"true_intent\" required></label><br><br>
    <label>Resolution action<br><input name=\"resolution_action\"></label><br><br>
    <label>Notes<br><textarea name=\"notes\" rows=\"3\" cols=\"60\"></textarea></label><br><br>
    <label>Agent ID<br><input name=\"agent_id\"></label><br><br>
    <label>Satisfaction score (1-5)<br><input name=\"satisfaction_score\" type=\"number\" min=\"1\" max=\"5\"></label><br><br>
    <button type=\"submit\">Submit</button>
  </form>
  <pre id=\"out\"></pre>
  <script>
  const apiKey = new URLSearchParams(window.location.search).get('key') || '';
  const form = document.getElementById('f');
  const out = document.getElementById('out');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    const obj = Object.fromEntries(fd.entries());
    if (obj.satisfaction_score === '') delete obj.satisfaction_score;
    else obj.satisfaction_score = Number(obj.satisfaction_score);
    const res = await fetch('/api/human-labels', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-KEY': apiKey,
      },
      body: JSON.stringify(obj),
    });
    out.textContent = await res.text();
  });
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html)
