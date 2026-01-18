#!/usr/bin/env python3
"""Test rapide extraction URL image"""

import asyncio
import sys
import os

# Ajouter le path parent
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

async def test_url_extraction():
    # Désactiver le cache pour ce test
    os.environ["DISABLE_RAG_CACHE"] = "true"
    
    from core.models import ChatRequest
    from starlette.requests import Request as StarletteRequest
    from Zeta_AI.app import chat_endpoint
    import uuid
    
    # Ajouter un suffix unique pour éviter le cache
    test_message = f"je veux deux paquets de culottes en taille XL voici le wave : https://scontent.xx.fbcdn.net/v/t1.15752-9/582949854_1524325675515592_1712402945374325664_n.jpg?_nc_cat=107&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=brNHcmG2PkUQ7kNvwG9c3oX&_nc_oc=AdnFlJc_jyF9Svs8lkVKjOtaM2w99-edoFB14QuA7OTcTqezTahqQfHaB0yxRYMSF0DJXVFghjZUGqjmoO8FUWgr&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent.xx&oh=03_Q7cD4QFS1LYSpryUlFPSRH4fSJA9CKhwQiMoJTnt49ER_ba4Yg&oe=697E1A12 [test_{uuid.uuid4().hex[:6]}]"
    
    payload = {
        "company_id": "W27PwOPiblP8TlOrhPcjOtxd0cza",
        "user_id": "test_url_extraction",
        "message": test_message,
        "images": [],
        "botlive_enabled": False,
        "conversation_history": "",
        "user_display_name": "Test",
    }
    
    print("="*80)
    print("TEST EXTRACTION URL IMAGE")
    print("="*80)
    print(f"Message original: {test_message[:100]}...")
    print(f"Images array: {payload['images']}")
    print()
    
    req = ChatRequest(**payload)
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "path": "/chat",
        "headers": [],
    }
    fake_request = StarletteRequest(scope)
    
    print("Appel chat_endpoint...")
    result = await chat_endpoint(req, fake_request)
    
    print()
    print("="*80)
    print("RÉSULTAT")
    print("="*80)
    
    if hasattr(result, "body"):
        import json
        raw_body = result.body
        if isinstance(raw_body, (bytes, bytearray)):
            raw_body = raw_body.decode("utf-8", errors="ignore")
        else:
            raw_body = str(raw_body)
        result = json.loads(raw_body) if raw_body else {}
    
    response_text = result.get("response", "") if isinstance(result, dict) else ""
    print(f"Réponse: {response_text}")
    print()

if __name__ == "__main__":
    asyncio.run(test_url_extraction())
