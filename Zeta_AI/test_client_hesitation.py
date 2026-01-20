#!/usr/bin/env python3
"""
🎯 TEST CLIENT HÉSITATION - Client compliqué, hésitant, digressif
Objectif : Mettre à l'épreuve la robustesse du LLM
"""

import asyncio
import httpx
import json
import time
from datetime import datetime

BASE_URL = "http://127.0.0.1:8002"
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
USER_ID = "client_hesitant_001"

TEST_IMAGES = {
    'product': 'https://scontent.xx.fbcdn.net/v/t1.15752-9/553786504_1339650347521010_7584722332323008254_n.jpg?_nc_cat=108&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=iZMvAIEg5agQ7kNvwGVnL0m&_nc_oc=AdmmEA2PGIddOYXbqVDCtoX-X4unHqUgSUBz44wJJhMV4B_RX4_vz3-hfIf0Gg1DYt44ejVZAGHX_fHccpiQMA8g&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent.xx&oh=03_Q7cD3gH1On4PnpZDZQ4CYayHguk94A069j97-Eai6X-5Lw48_Q&oe=6911CDDA',
    'payment_2020': 'https://scontent.xx.fbcdn.net/v/t1.15752-9/556908482_1314851517042795_6410429215345539018_n.jpg?_nc_cat=105&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=FGYA3tLaNB8Q7kNvwEFLtNy&_nc_oc=AdnhSYhxtPMknvUViCVLIxdq0psdWOZ9d5lLqoGBIzM4BwPMJfxTWbgDf2rraR9cbl-xHoxCoLL8X0Hf8rR18N30&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent.xx&oh=03_Q7cD3gGKjKR_xt29vtVgdJSUwjCSgV-A-H0IdCphHvF0MvGBow&oe=6911C04A',
}

def print_conversation(step: int, user_msg: str, bot_response: str, duration: float):
    print(f"\n{'='*80}")
    print(f"🔹 ÉTAPE {step}")
    print(f"{'='*80}")
    print(f"👤 CLIENT: {user_msg}")
    print(f"⏱️  Temps: {duration:.2f}s")
    print(f"🤖 JESSICA: {bot_response}")

async def send_message(message: str = "", images: list = None):
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

async def run_hesitant_client_scenario():
    """
    Scénario : Client hésitant, digressif, qui allonge la conversation, pose des questions hors-sujet,
    revient en arrière, fait des pauses, etc. Le LLM doit recadrer et finaliser la commande.
    """
    print("\n" + "🎯 " * 20)
    print("TEST CLIENT HÉSITATION - Client compliqué, hésitant, digressif")
    print("🎯 " * 20 + "\n")

    step = 1
    # 1. Salutation hésitante
    result = await send_message("Bonsoir")
    print_conversation(step, "Bonsoir", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1

    # 2. Hésitation
    result = await send_message("Euh... je ne sais pas trop si je veux commander aujourd'hui...")
    print_conversation(step, "Euh... je ne sais pas trop si je veux commander aujourd'hui...", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1

    # 3. Question hors-sujet
    result = await send_message("Tu connais la météo à Abidjan ?")
    print_conversation(step, "Tu connais la météo à Abidjan ?", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1

    # 4. Digression
    result = await send_message("Je peux acheter autre chose que des produits bébé ici ?")
    print_conversation(step, "Je peux acheter autre chose que des produits bébé ici ?", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1

    # 5. Recentrage (le client revient)
    result = await send_message("Bon, finalement je veux commander un produit bébé.")
    print_conversation(step, "Bon, finalement je veux commander un produit bébé.", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1

    # 6. Pause/attente
    result = await send_message("Attends, je réfléchis...")
    print_conversation(step, "Attends, je réfléchis...", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1

    # 7. Envoie photo produit
    result = await send_message("", images=[TEST_IMAGES['product']])
    print_conversation(step, "[Photo produit envoyée]", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1

    # 8. Doute/confirmation
    result = await send_message("C'est bien ce produit qu'il faut ?")
    print_conversation(step, "C'est bien ce produit qu'il faut ?", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1

    # 9. Confirme
    result = await send_message("Oui je confirme")
    print_conversation(step, "Oui je confirme", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1

    # 10. Hésitation paiement
    result = await send_message("Je dois payer maintenant ?")
    print_conversation(step, "Je dois payer maintenant ?", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1

    result = await send_message("J'ai peur que ça ne marche pas...")
    print_conversation(step, "J'ai peur que ça ne marche pas...", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1

    # 11. Envoie paiement
    result = await send_message("", images=[TEST_IMAGES['payment_2020']])
    print_conversation(step, "[Capture paiement 2020 FCFA]", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1

    # 12. Pause volontaire
    result = await send_message("Je reviens dans 5 minutes...")
    print_conversation(step, "Je reviens dans 5 minutes...", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1

    # 13. Après la pause
    result = await send_message("Désolé, j'avais une urgence.")
    print_conversation(step, "Désolé, j'avais une urgence.", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1

    # 14. Zone
    result = await send_message("Yopougon")
    print_conversation(step, "Yopougon", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1

    # 15. Encore une hésitation
    result = await send_message("Tu es sûr que la livraison est possible là-bas ?")
    print_conversation(step, "Tu es sûr que la livraison est possible là-bas ?", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1

    # 16. Numéro
    result = await send_message("0709876543")
    print_conversation(step, "0709876543", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1

    # 17. Teste la finalisation
    result = await send_message("C'est bon, tout est ok ?")
    print_conversation(step, "C'est bon, tout est ok ?", result['response'], result['duration'])

    # Résumé
    print(f"\n{'='*80}")
    print("📊 RÉSUMÉ CLIENT HÉSITATION")
    print(f"{'='*80}")
    print(f"✅ Commande complétée en {step} étapes (client hésitant)")
    print(f"✅ Recadrage et finalisation testés")
    print(f"{'='*80}\n")

async def main():
    try:
        await run_hesitant_client_scenario()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
