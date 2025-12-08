import re
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional
import asyncio

# Ensure project root on path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.shadow_recorder import record_user_message, record_operator_reply

LINE_RE = re.compile(r"^\[(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2}:\d{2})\]\s(.+?):\s?(.*)$")

SYSTEM_PATTERNS = [
    "Les messages et les appels sont chiffrés de bout en bout",
    "utilise une durée des messages éphémères",
    "a désactivé les messages éphémères",
]


def parse_log(path: Path, operator_names: List[str]) -> List[Dict]:
    msgs: List[Dict] = []
    last = None

    def is_operator(name: str) -> bool:
        n = (name or "").strip().lower()
        for op in operator_names:
            if n == op.strip().lower():
                return True
        return False

    with path.open("r", encoding="utf-8-sig") as f:
        for raw in f:
            line = raw.rstrip("\n")
            m = LINE_RE.match(line)
            if m:
                date, hour, speaker, content = m.group(1), m.group(2), m.group(3), m.group(4)
                content = (content or "").strip()

                if any(pat.lower() in content.lower() for pat in SYSTEM_PATTERNS):
                    last = None
                    continue

                entry = {
                    "ts": f"{date} {hour}",
                    "speaker": speaker.strip(),
                    "message": content,
                    "is_operator": is_operator(speaker),
                }
                msgs.append(entry)
                last = entry
            else:
                # Continuation line (append to last message)
                if last is not None:
                    if line.strip():
                        last["message"] = (last["message"] + "\n" + line).strip()
    return [m for m in msgs if m.get("message")]  # drop empties


def derive_user_identity(msgs: List[Dict], operator_names: List[str], fallback_user_id: Optional[str]) -> (str, Optional[str]):
    if fallback_user_id:
        return fallback_user_id, None
    for m in msgs:
        name = m.get("speaker") or ""
        if name and name.strip() and name.strip().lower() not in [op.strip().lower() for op in operator_names]:
            user_id = re.sub(r"[^a-z0-9_]+", "_", name.lower())
            return user_id, name
    return "user_unknown", None


async def ingest(path: Path, company_id: str, operator_names: List[str], user_id: Optional[str]) -> Dict:
    msgs = parse_log(path, operator_names)
    if not msgs:
        return {"ingested": 0, "user": 0, "operator": 0}

    user_id_final, user_display = derive_user_identity(msgs, operator_names, user_id)

    ingested = 0
    u_count = 0
    o_count = 0

    for m in msgs:
        text = m["message"]
        if m["is_operator"]:
            await record_operator_reply(company_id, user_id_final, text, m.get("speaker"))
            o_count += 1
        else:
            await record_user_message(company_id, user_id_final, text, user_display)
            u_count += 1
        ingested += 1

    return {"ingested": ingested, "user": u_count, "operator": o_count, "user_id": user_id_final}


def main() -> None:
    parser = argparse.ArgumentParser(prog="ingest_shadow_from_text", description="Ingest WhatsApp-like chat logs into Shadow recorder")
    parser.add_argument("--input", required=True, help="Path to text log file")
    parser.add_argument("--company-id", required=True, help="Company ID")
    parser.add_argument("--operator-names", default="Centre de réception de demandes et d’infos", help="Comma-separated operator display names")
    parser.add_argument("--user-id", default=None, help="Override user_id (otherwise derived from first non-operator speaker)")

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(json.dumps({"error": f"Input file not found: {input_path}"}, ensure_ascii=False))
        sys.exit(1)

    operator_names = [s for s in (args.operator_names or "").split(",") if s.strip()]

    result = asyncio.run(ingest(input_path, args.company_id, operator_names, args.user_id))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
