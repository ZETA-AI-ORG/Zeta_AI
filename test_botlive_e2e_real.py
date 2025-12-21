#!/usr/bin/env python3
"""
Test E2E réel qui appelle l'endpoint de l'application Botlive
avec les vraies URLs d'images et affiche tous les logs.
"""

import asyncio
import json
import os
import sys
import requests
import uuid
from datetime import datetime

# Configuration
BASE_URL = os.getenv("BOTLIVE_E2E_BASE_URL", "http://localhost:8002")  # backend sur port 8002
USER_ID = os.getenv("BOTLIVE_E2E_USER_ID", f"test_user_e2e_{uuid.uuid4().hex[:6]}")
COMPANY_ID = os.getenv("BOTLIVE_E2E_COMPANY_ID", "W27PwOPiblP8TlOrhPcjOtxd0cza")

def log_section(title):
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80)

def log_response(resp, title="Réponse"):
    print(f"\n--- {title} ---")
    print(f"Status: {resp.status_code}")
    try:
        data = resp.json()
        print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")

        expected_intent = (os.getenv("BOTLIVE_E2E_EXPECT_INTENT") or "").strip()
        if expected_intent:
            got_intent = (data.get("intent") or "").strip()
            if got_intent != expected_intent:
                raise SystemExit(
                    f"E2E intent assertion failed: expected '{expected_intent}' got '{got_intent}'"
                )
    except Exception:
        print(f"Raw body: {resp.text}")

async def test_botlive_real():
    log_section("TEST E2E BOTLIVE RÉEL")
    
    session = requests.Session()
    
    # 1. Message texte simple via /botlive/message
    log_section("1. Message texte (/botlive/message)")
    payload1 = {
        "company_id": COMPANY_ID,
        "user_id": USER_ID,
        "message": "salut",
        "images": [],
        "conversation_history": "",
        "user_display_name": "E2E",
    }
    resp1 = session.post(f"{BASE_URL}/botlive/message", json=payload1, timeout=90)
    log_response(resp1, "1. /botlive/message")

    log_section("FIN DU TEST E2E")

if __name__ == "__main__":
    asyncio.run(test_botlive_real())
