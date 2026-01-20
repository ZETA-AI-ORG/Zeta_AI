#!/usr/bin/env python3
"""
🤔 TEST CLIENT HÉSITANT - Pose beaucoup de questions
Client qui hésite, pose des questions spécifiques sur les produits, finit par commander
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
USER_ID = "client_hesitant_002"  # Format similaire à testuser314

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
# SCÉNARIO CLIENT HÉSITANT
# ═══════════════════════════════════════════════════════════════════════════════

async def run_hesitant_client_scenario():
    """
    Scénario: Client hésitant qui pose beaucoup de questions
    
    Workflow:
    1. Salutation
    2. Demande info sur produits
    3. Question sur tailles
    4. Question sur prix
    5. Question sur livraison
    6. Question sur paiement
    7. Finalement envoie photo
    8. Hésite sur la confirmation
    9. Confirme
    10. Envoie paiement
    11. Demande précision sur zone
    12. Donne zone
    13. Donne numéro
    """
    
    print("\n" + "🤔 " * 20)
    print("TEST CLIENT HÉSITANT - Pose beaucoup de questions")
    print("🤔 " * 20 + "\n")
    
    step = 1
    
    # ═══ ÉTAPE 1: Salutation ═══
    result = await send_message("Bonjour, je cherche des couches pour bébé")
    print_conversation(step, "Bonjour, je cherche des couches pour bébé", result['response'], result['duration'])
    await asyncio.sleep(1.5)
    step += 1
    
    # ═══ ÉTAPE 2: Question sur tailles ═══
    result = await send_message("Vous avez quelles tailles disponibles ?")
    print_conversation(step, "Vous avez quelles tailles disponibles ?", result['response'], result['duration'])
    await asyncio.sleep(1.5)
    step += 1
    
    # ═══ ÉTAPE 3: Question sur prix ═══
    result = await send_message("C'est combien le lot de 150 couches taille 4 ?")
    print_conversation(step, "C'est combien le lot de 150 couches taille 4 ?", result['response'], result['duration'])
    await asyncio.sleep(1.5)
    step += 1
    
    # ═══ ÉTAPE 4: Question sur qualité ═══
    result = await send_message("C'est de bonne qualité ? Mon bébé a la peau sensible")
    print_conversation(step, "C'est de bonne qualité ? Mon bébé a la peau sensible", result['response'], result['duration'])
    await asyncio.sleep(1.5)
    step += 1
    
    # ═══ ÉTAPE 5: Question sur livraison ═══
    result = await send_message("Vous livrez à Cocody ? C'est combien la livraison ?")
    print_conversation(step, "Vous livrez à Cocody ? C'est combien la livraison ?", result['response'], result['duration'])
    await asyncio.sleep(1.5)
    step += 1
    
    # ═══ ÉTAPE 6: Question sur délai ═══
    result = await send_message("Et la livraison c'est en combien de temps ?")
    print_conversation(step, "Et la livraison c'est en combien de temps ?", result['response'], result['duration'])
    await asyncio.sleep(1.5)
    step += 1
    
    # ═══ ÉTAPE 7: Question sur paiement ═══
    result = await send_message("Je peux payer comment ? Wave ou Orange Money ?")
    print_conversation(step, "Je peux payer comment ? Wave ou Orange Money ?", result['response'], result['duration'])
    await asyncio.sleep(1.5)
    step += 1
    
    # ═══ ÉTAPE 8: Finalement envoie photo ═══
    result = await send_message("Ok je vais envoyer la photo", images=[TEST_IMAGES['product']])
    print_conversation(step, "Ok je vais envoyer la photo [Photo]", result['response'], result['duration'])
    await asyncio.sleep(1.5)
    step += 1
    
    # ═══ ÉTAPE 9: Hésite encore ═══
    result = await send_message("Attendez, je peux avoir combien de paquets avec ça ?")
    print_conversation(step, "Attendez, je peux avoir combien de paquets avec ça ?", result['response'], result['duration'])
    await asyncio.sleep(1.5)
    step += 1
    
    # ═══ ÉTAPE 10: Confirme enfin ═══
    result = await send_message("Ok d'accord, je confirme la commande")
    print_conversation(step, "Ok d'accord, je confirme la commande", result['response'], result['duration'])
    await asyncio.sleep(1.5)
    step += 1
    
    # ═══ ÉTAPE 11: Envoie paiement ═══
    result = await send_message("Voilà le paiement", images=[TEST_IMAGES['payment_2020']])
    print_conversation(step, "Voilà le paiement [Capture 2020 FCFA]", result['response'], result['duration'])
    await asyncio.sleep(1.5)
    step += 1
    
    # ═══ ÉTAPE 12: Demande précision zone ═══
    result = await send_message("C'est Cocody précisément Rivera 3")
    print_conversation(step, "C'est Cocody précisément Rivera 3", result['response'], result['duration'])
    await asyncio.sleep(1.5)
    step += 1
    
    # ═══ ÉTAPE 13: Question sur contact ═══
    result = await send_message("Le numéro c'est celui avec lequel je vous parle ?")
    print_conversation(step, "Le numéro c'est celui avec lequel je vous parle ?", result['response'], result['duration'])
    await asyncio.sleep(1.5)
    step += 1
    
    # ═══ ÉTAPE 14: Donne numéro ═══
    result = await send_message("0708765432")
    print_conversation(step, "0708765432", result['response'], result['duration'])
    
    # ═══ RÉSUMÉ ═══
    print(f"\n{'='*80}")
    print("📊 RÉSUMÉ CLIENT HÉSITANT")
    print(f"{'='*80}")
    print(f"✅ Commande complétée en {step} étapes")
    print(f"🤔 Nombreuses questions posées")
    print(f"⏱️  Workflow plus long mais abouti")
    print(f"{'='*80}\n")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    try:
        await run_hesitant_client_scenario()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
