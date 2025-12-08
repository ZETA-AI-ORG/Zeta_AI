import argparse
import asyncio
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple

import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.shadow_recorder import record_user_message, record_operator_reply


def _is_company_jid(jid: str, company_suffix: str = "@c.us") -> bool:
    return isinstance(jid, str) and jid.endswith(company_suffix)


def _derive_user_id(chat: Dict[str, Any]) -> Tuple[str, str]:
    """Construit un user_id stable par conversation WhatsApp.

    - Utilise chatId (numéro client) comme base
    - Nettoie en slug simple: [a-z0-9_]
    """
    raw = str(chat.get("chatId") or chat.get("chatName") or "user_unknown")
    slug = re.sub(r"[^a-z0-9_]+", "_", raw.lower())
    slug = slug.strip("_") or "user_unknown"
    display = str(chat.get("chatName") or raw)
    return slug, display


async def ingest_whatsapp_json(path: Path, company_id: str) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("whatsapp_export JSON must be a list of chats")

    total_user = 0
    total_operator = 0
    conv_count = 0

    for chat in data:
        messages = chat.get("messages") or []
        if not messages:
            continue

        user_id, user_display = _derive_user_id(chat)
        conv_count += 1

        # Déterminer JID entreprise (souvent @c.us) et possibles opérateurs (lid)
        # Heuristique simple: le premier message 'from' avec suffixe @c.us est l'entreprise
        company_jids: List[str] = []
        for m in messages:
            frm = m.get("from") or ""
            if _is_company_jid(frm):
                if frm not in company_jids:
                    company_jids.append(frm)
        # Fallback: si vide, on considère que tous les @c.us sont entreprise

        for m in sorted(messages, key=lambda x: x.get("timestamp") or 0):
            body = (m.get("body") or "").strip()
            if not body:
                continue

            mtype = m.get("type") or ""
            if mtype not in ("chat", "automated_greeting_message"):
                # On ignore e2e_notification, etc.
                continue

            frm = m.get("from") or ""

            # Règle: si from est un client (non @c.us), c'est un message user
            # si from est l'entreprise ou un opérateur (company_jids ou suffixe @c.us), c'est opérateur
            is_company_side = _is_company_jid(frm) or (company_jids and frm in company_jids)

            if is_company_side:
                await record_operator_reply(company_id, user_id, body, operator_display_name=frm)
                total_operator += 1
            else:
                await record_user_message(company_id, user_id, body, user_display_name=user_display)
                total_user += 1

    return {
        "conversations": conv_count,
        "user_messages": total_user,
        "operator_messages": total_operator,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest WhatsApp JSON export into Shadow recorder")
    parser.add_argument("--input", required=True, help="Path to whatsapp_export_*.json")
    parser.add_argument("--company-id", required=True, help="Company ID for Shadow records")

    args = parser.parse_args()
    path = Path(args.input)

    if not path.exists():
        print(json.dumps({"error": f"Input file not found: {path}"}, ensure_ascii=False))
        return

    result = asyncio.run(ingest_whatsapp_json(path, args.company_id))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
