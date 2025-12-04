import os
import json
import re
import time
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

_last_user: Dict[Tuple[str, str], Dict[str, Any]] = {}
_router = None

EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF\U0001F1E6-\U0001F1FF]")

async def record_user_message(company_id: str, user_id: str, text: str, user_display_name: Optional[str] = None) -> None:
    key = (company_id or "", user_id or "")
    _last_user[key] = {
        "ts": int(time.time()),
        "text": text or "",
        "user_display_name": user_display_name or None,
    }
    _append_jsonl({
        "type": "user_message",
        "company_id": company_id,
        "user_id": user_id,
        "text": text or "",
        "ts": int(time.time()),
    })

async def record_operator_reply(company_id: str, user_id: str, text: str, operator_display_name: Optional[str] = None) -> None:
    key = (company_id or "", user_id or "")
    user_ctx = _last_user.get(key) or {}
    pair = {
        "type": "pair",
        "company_id": company_id,
        "user_id": user_id,
        "ts": int(time.time()),
        "message_client": user_ctx.get("text") or "",
        "response_operateur": text or "",
        "client_display_name": user_ctx.get("user_display_name"),
        "operateur_display_name": operator_display_name or None,
    }
    intent = _classify_intent(pair["message_client"]) or {}
    style = _analyze_style(pair["response_operateur"]) or {}
    pair["intent_pred"] = intent
    pair["style_features"] = style
    _append_jsonl(pair)

def _analyze_style(text: str) -> Dict[str, Any]:
    t = text or ""
    emojis = len(EMOJI_RE.findall(t))
    exclam = t.count("!")
    quest = t.count("?")
    length = len(t)
    lower = t.lower()
    nouchi_hits = 0
    for kw in ("oh", "ow", "inchallah", "ma chere", "mon frere", "on va faire comment", "c'est dû"):
        if kw in lower:
            nouchi_hits += 1
    formel_hits = 0
    for kw in ("bonjour", "svp", "s'il vous plait", "merci", "cordialement"):
        if kw in lower:
            formel_hits += 1
    return {
        "len": length,
        "emojis": emojis,
        "exclam": exclam,
        "quest": quest,
        "nouchi_hits": nouchi_hits,
        "formel_hits": formel_hits,
    }

def _classify_intent(text: str) -> Optional[Dict[str, Any]]:
    global _router
    msg = (text or "").strip()
    if not msg:
        return None
    try:
        if _router is None:
            from core.centroid_router import CentroidRouter
            _router = CentroidRouter(use_cache=True)
        res = _router.route(msg, top_k=2)
        return {
            "best_id": res.get("intent_id"),
            "best_name": res.get("intent_name"),
            "confidence": res.get("confidence"),
            "top_k": res.get("top_k_intents"),
        }
    except Exception:
        return None

def _append_jsonl(obj: Dict[str, Any]) -> None:
    base = Path("data/shadow")
    base.mkdir(parents=True, exist_ok=True)
    path = base / "shadow_pairs.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
