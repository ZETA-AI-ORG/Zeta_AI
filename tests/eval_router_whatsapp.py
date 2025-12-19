import argparse
import asyncio
import csv
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple
import sys

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

os.environ.setdefault("BOTLIVE_HYDE_PRE_ENABLED", "false")

# Ensure project root on path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.botlive_intent_router import route_botlive_intent


def _is_company_jid(jid: str, company_suffix: str = "@c.us") -> bool:
    return isinstance(jid, str) and jid.endswith(company_suffix)


def _is_client_to_business_message(
    m: Dict[str, Any],
    business_jid: str,
    extra_business_jids: List[str],
    include_lid_to: bool,
) -> bool:
    if not isinstance(m, dict):
        return False
    if (m.get("type") or "") != "chat":
        return False

    frm = str(m.get("from") or "")
    to = str(m.get("to") or "")

    # côté client = tout ce qui n'est pas le JID business principal
    if frm == business_jid:
        return False

    to_is_business = (to == business_jid) or (to in set(extra_business_jids or []))
    to_is_operator = bool(include_lid_to) and isinstance(to, str) and to.endswith("@lid")
    if not (to_is_business or to_is_operator):
        return False

    body = (m.get("body") or "").strip()
    return bool(body)


def _derive_user_id(chat: Dict[str, Any]) -> Tuple[str, str]:
    raw = str(chat.get("chatId") or chat.get("chatName") or "user_unknown")
    import re
    slug = re.sub(r"[^a-z0-9_]+", "_", raw.lower())
    slug = slug.strip("_") or "user_unknown"
    display = str(chat.get("chatName") or raw)
    return slug, display


def _build_history_and_state(messages: List[Dict[str, Any]], idx: int, max_lines: int = 12) -> (str, dict):
    """
    Reconstruit l'historique bot+user (Jessica:/User:) et un state tunnel progressif jusqu'à messages[idx].
    À chaque question bot typique, on avance dans le tunnel (photo, paiement, zone, tel).
    """
    lines: List[str] = []
    state = {
        "photo_collected": False,
        "paiement_collected": False,
        "zone_collected": False,
        "tel_collected": False,
        "tel_valide": False,
        "collected_count": 0,
        "is_complete": False,
    }
    checklist = ["photo_collected", "paiement_collected", "zone_collected", "tel_collected"]
    step = 0
    start = max(0, idx - max_lines)
    for m in messages[start:idx]:
        body = (m.get("body") or "").strip()
        if not body:
            continue
        frm = m.get("from") or ""
        if _is_company_jid(frm):
            lines.append(f"Jessica: {body}")
            # Heuristique : chaque question bot fait progresser le tunnel
            if step < len(checklist):
                state[checklist[step]] = True
                step += 1
        else:
            lines.append(f"User: {body}")
    state["collected_count"] = sum(1 for k in checklist if state[k])
    state["is_complete"] = state["collected_count"] == 4
    return "\n".join(lines), state


async def eval_chat(
    chat: Dict[str, Any],
    company_id: str,
    business_jid: str,
    extra_business_jids: List[str],
    include_lid_to: bool,
    limit: int,
) -> List[Dict[str, Any]]:
    messages = sorted(chat.get("messages") or [], key=lambda x: x.get("timestamp") or 0)
    user_id, _ = _derive_user_id(chat)

    results: List[Dict[str, Any]] = []
    count = 0

    for i, m in enumerate(messages):
        if not _is_client_to_business_message(m, business_jid, extra_business_jids, include_lid_to):
            continue

        body = (m.get("body") or "").strip()
        timestamp = int(m.get("timestamp") or 0)
        msg_id = str(m.get("_id") or "")
        frm = str(m.get("from") or "")
        to = str(m.get("to") or "")

        history, state_compact = _build_history_and_state(messages, i)

        # Baseline: WITHOUT context (empty history/state)
        r0 = await route_botlive_intent(
            company_id=company_id,
            user_id=user_id,
            message=body,
            conversation_history="",
            state_compact={
                "photo_collected": False,
                "paiement_collected": False,
                "zone_collected": False,
                "tel_collected": False,
                "tel_valide": False,
                "collected_count": 0,
                "is_complete": False,
            },
        )

        # Contextual: WITH history & progressive state
        r1 = await route_botlive_intent(
            company_id=company_id,
            user_id=user_id,
            message=body,
            conversation_history=history,
            state_compact=state_compact,
        )

        results.append(
            {
                "chat_id": str(chat.get("chatId") or ""),
                "chat_name": str(chat.get("chatName") or ""),
                "timestamp": timestamp,
                "message_id": msg_id,
                "from": frm,
                "to": to,
                "message": body,
                "len": len(body.split()),
                "intent_no_ctx": r0.intent,
                "conf_no_ctx": f"{r0.confidence:.3f}",
                "intent_ctx": r1.intent,
                "conf_ctx": f"{r1.confidence:.3f}",
                "changed": r0.intent != r1.intent,
                "delta": f"{(r1.confidence - r0.confidence):.3f}",
                "state_ctx": state_compact.copy(),
                "history_ctx": history,
            }
        )

        count += 1
        if limit and count >= limit:
            break

    return results


async def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate router on WhatsApp export (with/without context)")
    parser.add_argument("--input", default=str(Path("data/imports/whatsapp-export/whatsapp_export_2025-12-05.json")), help="Path to whatsapp export JSON")
    parser.add_argument("--company-id", default="ZETADEV", help="Company ID")
    parser.add_argument("--business-jid", default="2250160924560@c.us", help="Business WhatsApp JID (messages with to==business_jid are treated as client messages)")
    parser.add_argument(
        "--extra-business-jids",
        default="",
        help="Comma-separated extra business JIDs to treat as business recipients (optional)",
    )
    parser.add_argument(
        "--include-lid-to",
        action="store_true",
        help="If set, also treat messages with to ending in @lid as client-to-business (operator) messages",
    )
    parser.add_argument("--limit", type=int, default=200, help="Max user messages to evaluate")
    parser.add_argument("--out", default=str(Path("tests/router_eval_results.csv")), help="CSV output path")

    args = parser.parse_args()
    path = Path(args.input)
    if not path.exists():
        alt = Path("whatsapp-export/whatsapp_export.json")
        if alt.exists():
            path = alt
        else:
            print(f"Input not found: {args.input}")
            return

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        print("Invalid JSON format (expected list of chats)")
        return

    rows: List[Dict[str, Any]] = []
    total = 0

    extra_business_jids = [x.strip() for x in (args.extra_business_jids or "").split(",") if x.strip()]
    for chat in data:
        part = await eval_chat(
            chat,
            args.company_id,
            args.business_jid,
            extra_business_jids,
            bool(args.include_lid_to),
            max(0, args.limit - total),
        )
        rows.extend(part)
        total += len(part)
        if total >= args.limit:
            break

    # Write CSV (inclut contexte pour debug)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "chat_id",
                "chat_name",
                "timestamp",
                "message_id",
                "from",
                "to",
                "message",
                "len",
                "intent_no_ctx",
                "conf_no_ctx",
                "intent_ctx",
                "conf_ctx",
                "changed",
                "delta",
                "state_ctx",
                "history_ctx",
            ],
        )
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # Summary
    changed = sum(1 for r in rows if r["changed"]) if rows else 0
    pct_changed = (changed / len(rows) * 100.0) if rows else 0.0
    avg_no = sum(float(r["conf_no_ctx"]) for r in rows) / len(rows) if rows else 0.0
    avg_ctx = sum(float(r["conf_ctx"]) for r in rows) / len(rows) if rows else 0.0

    print("=== Router Evaluation ===")
    print(f"Samples: {len(rows)} | Changed intents: {changed} ({pct_changed:.1f}%)")
    print(f"Avg confidence: no_ctx={avg_no:.3f} vs ctx={avg_ctx:.3f} (Δ={(avg_ctx-avg_no):.3f})")
    print(f"CSV saved: {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
