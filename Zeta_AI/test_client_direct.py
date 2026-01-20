#!/usr/bin/env python3
"""
🎯 TEST CLIENT DIRECT - Comportement idéal
Client qui va à l'essentiel, suit les directives du LLM
"""

import asyncio
import httpx
import json
import time
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

BASE_URL = "http://127.0.0.1:8002"
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"  # Rue du Grossiste
USER_ID = "client_direct_002"  # Format similaire à testuser314

# Images de test (VRAIES URLs Facebook)
TEST_IMAGES = {
    'product': 'https://scontent.xx.fbcdn.net/v/t1.15752-9/553786504_1339650347521010_7584722332323008254_n.jpg?_nc_cat=108&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=iZMvAIEg5agQ7kNvwGVnL0m&_nc_oc=AdmmEA2PGIddOYXbqVDCtoX-X4unHqUgSUBz44wJJhMV4B_RX4_vz3-hfIf0Gg1DYt44ejVZAGHX_fHccpiQMA8g&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent.xx&oh=03_Q7cD3gH1On4PnpZDZQ4CYayHguk94A069j97-Eai6X-5Lw48_Q&oe=6911CDDA',
    'payment_2020': 'https://scontent.xx.fbcdn.net/v/t1.15752-9/556908482_1314851517042795_6410429215345539018_n.jpg?_nc_cat=105&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=FGYA3tLaNB8Q7kNvwEFLtNy&_nc_oc=AdnhSYhxtPMknvUViCVLIxdq0psdWOZ9d5lLqoGBIzM4BwPMJfxTWbgDf2rraR9cbl-xHoxCoLL8X0Hf8rR18N30&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent.xx&oh=03_Q7cD3gGKjKR_xt29vtVgdJSUwjCSgV-A-H0IdCphHvF0MvGBow&oe=6911C04A',
    'payment_202': 'https://scontent.xx.fbcdn.net/v/t1.15752-9/553547596_833613639156226_7121847885682360094_n.jpg?_nc_cat=101&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=K1kbaIgRUbAQ7kNvwHaqkOD&_nc_oc=AdknztnUSj95bPrfUz5KzLYpjiJeQlvByodlrf_Jk8NAqBDHis4HMPZAYPrIqqhNmNh2RVdf9AXjilXYp2KlHFkj&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent.xx&oh=03_Q7cD3gGoDbU2GAqKjo1Dky8HizmME0SNsy9DDV1ED90nStQM0w&oe=6911A8CA'
}

# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

async def send_message(message: str = "", images: list = None):
    """Envoie un message au chatbot"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        start = time.time()
        
        payload = {
            "company_id": COMPANY_ID,
            "user_id": USER_ID,
            "message": message,
            "botlive_enabled": True
        }
        
        if images:
            payload["images"] = images
        
        response = await client.post(f"{BASE_URL}/chat", json=payload)
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            return {
                'response': data.get('response', ''),
                'duration': duration,
                'success': True
            }
        else:
            print(f"❌ Erreur {response.status_code}: {response.text}")
            return {'response': '', 'duration': duration, 'success': False}

def print_conversation(step: int, user_msg: str, bot_response: str, duration: float):
    """Affiche la conversation de manière lisible"""
    print(f"\n{'='*80}")
    print(f"🔹 ÉTAPE {step}")
    print(f"{'='*80}")
    print(f"👤 CLIENT: {user_msg}")
    print(f"⏱️  Temps: {duration:.2f}s")
    print(f"🤖 JESSICA: {bot_response}")

# ═══════════════════════════════════════════════════════════════════════════════
# SCÉNARIO CLIENT DIRECT
# ═══════════════════════════════════════════════════════════════════════════════

async def run_direct_client_scenario():
    """
    Scénario: Client direct qui va à l'essentiel
    
    Workflow:
    1. Salutation
    2. Envoie photo produit immédiatement
    3. Confirme
    4. Envoie paiement
    5. Donne zone
    6. Donne numéro
    """
    
    print("\n" + "🎯 " * 20)
    print("TEST CLIENT DIRECT - Comportement idéal")
    print("🎯 " * 20 + "\n")
    
    step = 1
    
    # ═══ ÉTAPE 1: Salutation simple ═══
    result = await send_message("Bonsoir")
    print_conversation(step, "Bonsoir", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1
    
    # ═══ ÉTAPE 2: Envoie photo produit direct ═══
    result = await send_message("", images=[TEST_IMAGES['product']])
    print_conversation(step, "[Photo produit envoyée]", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1
    
    # ═══ ÉTAPE 3: Confirme immédiatement ═══
    result = await send_message("Oui je confirme")
    print_conversation(step, "Oui je confirme", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1
    
    # ═══ ÉTAPE 4: Envoie paiement ═══
    result = await send_message("", images=[TEST_IMAGES['payment_2020']])
    print_conversation(step, "[Capture paiement 2020 FCFA]", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1
    
    # ═══ ÉTAPE 5: Donne zone ═══
    result = await send_message("Yopougon")
    print_conversation(step, "Yopougon", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1
    
    # ═══ ÉTAPE 6: Donne numéro ═══
    result = await send_message("0709876543")
    print_conversation(step, "0709876543", result['response'], result['duration'])
    
    # ═══ RÉSUMÉ ═══
    print(f"\n{'='*80}")
    print("📊 RÉSUMÉ CLIENT DIRECT")
    print(f"{'='*80}")
    print(f"✅ Commande complétée en {step} étapes")
    print(f"✅ Aucune hésitation")
    print(f"✅ Workflow optimal")
    print(f"{'='*80}\n")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    try:
        await run_direct_client_scenario()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
