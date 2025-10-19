#!/usr/bin/env python3
"""
🧨 TEST CLIENT ULTIME - Scénario extrême, réaliste, ultra-digressif, multitâche, hésitant, changeant d’avis, interruptions, hors-sujet, stress, etc.
Le but est de pousser le LLM dans ses retranchements tout en restant crédible.
"""
import asyncio
import httpx
import time
from datetime import datetime

BASE_URL = "http://127.0.0.1:8002"
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
# USER_ID unique basé sur timestamp pour éviter mélange avec anciens tests
USER_ID = f"client_ultime_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

TEST_IMAGES = {
    'product': 'https://scontent.xx.fbcdn.net/v/t1.15752-9/553786504_1339650347521010_7584722332323008254_n.jpg?_nc_cat=108&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=iZMvAIEg5agQ7kNvwGVnL0m&_nc_oc=AdmmEA2PGIddOYXbqVDCtoX-X4unHqUgSUBz44wJJhMV4B_RX4_vz3-hfIf0Gg1DYt44ejVZAGHX_fHccpiQMA8g&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent.xx&oh=03_Q7cD3gH1On4PnpZDZQ4CYayHguk94A069j97-Eai6X-5Lw48_Q&oe=6911CDDA',
    'payment_202': 'https://scontent.xx.fbcdn.net/v/t1.15752-9/553547596_833613639156226_7121847885682360094_n.jpg?_nc_cat=101&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=K1kbaIgRUbAQ7kNvwHaqkOD&_nc_oc=AdknztnUSj95bPrfUz5KzLYpjiJeQlvByodlrf_Jk8NAqBDHis4HMPZAYPrIqqhNmNh2RVdf9AXjilXYp2KlHFkj&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent.xx&oh=03_Q7cD3gGoDbU2GAqKjo1Dky8HizmME0SNsy9DDV1ED90nStQM0w&oe=6911A8CA',
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

async def run_ultimate_client_scenario():
    print("\n" + "🧨 " * 20)
    print("TEST CLIENT ULTIME - Scénario extrême, réaliste, multitâche, digressif")
    print("🧨 " * 20 + "\n")
    step = 1
    # 1. Salutation hésitante
    result = await send_message("Salut, euh... j'ai une question, mais je sais pas si c'est le bon endroit...")
    print_conversation(step, "Salut, euh... j'ai une question, mais je sais pas si c'est le bon endroit...", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1

    # 2. Hors-sujet direct
    result = await send_message("Tu peux me donner la recette des crêpes ?")
    print_conversation(step, "Tu peux me donner la recette des crêpes ?", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1

    # 3. Retour au sujet, puis digression
    result = await send_message("Bon, en fait je veux commander, mais c'est pour offrir. Tu crois que c'est une bonne idée ?")
    print_conversation(step, "Bon, en fait je veux commander, mais c'est pour offrir. Tu crois que c'est une bonne idée ?", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1

    # 4. Pause, multitâche
    result = await send_message("Attends, je réponds à un appel. Je reviens.")
    print_conversation(step, "Attends, je réponds à un appel. Je reviens.", result['response'], result['duration'])
    await asyncio.sleep(2)
    step += 1

    # 5. Reprise, demande info produit
    result = await send_message("C'est quoi le produit le plus populaire chez vous ?")
    print_conversation(step, "C'est quoi le produit le plus populaire chez vous ?", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1

    # 6. Hésitation puis envoi photo, puis annulation
    result = await send_message("Bon, je t'envoie une photo, mais je ne suis pas sûr...")
    print_conversation(step, "Bon, je t'envoie une photo, mais je ne suis pas sûr...", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1
    result = await send_message("", images=[TEST_IMAGES['product']])
    print_conversation(step, "[Photo produit envoyée]", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1
    result = await send_message("Non, attends, laisse tomber, je crois que je me suis trompé de produit.")
    print_conversation(step, "Non, attends, laisse tomber, je crois que je me suis trompé de produit.", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1

    # 7. Re-envoi d'une autre photo (même image, simule changement d'avis)
    result = await send_message("En fait, c'est cette photo qu'il faut.", images=[TEST_IMAGES['product']])
    print_conversation(step, "En fait, c'est cette photo qu'il faut.", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1

    # 8. Hésitation paiement
    result = await send_message("Je dois payer maintenant ? Et si je change d'avis après ?")
    print_conversation(step, "Je dois payer maintenant ? Et si je change d'avis après ?", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1

    # 9. Paiement partiel puis complet
    result = await send_message("Je peux payer une partie d'abord ?")
    print_conversation(step, "Je peux payer une partie d'abord ?", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1
    result = await send_message("", images=[TEST_IMAGES['payment_2020']])
    print_conversation(step, "[Capture paiement 2020 FCFA]", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1
    result = await send_message("Finalement, je veux payer tout d'un coup.")
    print_conversation(step, "Finalement, je veux payer tout d'un coup.", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1

    # 10. Zone, puis changement d'avis
    result = await send_message("Yopougon")
    print_conversation(step, "Yopougon", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1
    result = await send_message("Non, en fait, c'est Cocody.")
    print_conversation(step, "Non, en fait, c'est Cocody.", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1

    # 11. Numéro, puis erreur, puis correction
    result = await send_message("079999999")
    print_conversation(step, "079999999", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1
    result = await send_message("Oups, j'ai oublié un chiffre : 0709876543")
    print_conversation(step, "Oups, j'ai oublié un chiffre : 0709876543", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1

    # 12. Interruption, retour, question support
    result = await send_message("Attends, j'ai une question sur la garantie.")
    print_conversation(step, "Attends, j'ai une question sur la garantie.", result['response'], result['duration'])
    await asyncio.sleep(1)
    step += 1
    result = await send_message("Ok, c'est bon, je veux finaliser la commande.")
    print_conversation(step, "Ok, c'est bon, je veux finaliser la commande.", result['response'], result['duration'])

    print(f"\n{'='*80}")
    print("📊 RÉSUMÉ CLIENT ULTIME")
    print(f"{'='*80}")
    print(f"✅ Commande complétée en {step} étapes (client ultime)")
    print(f"✅ Recadrage, multitâche, corrections, interruptions, digressions testés")
    print(f"{'='*80}\n")

async def main():
    try:
        await run_ultimate_client_scenario()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print(f"\n🆔 USER_ID pour ce test: {USER_ID}")
    print(f"📌 Pour vérifier l'état: python3 check_state.py {USER_ID}\n")
    asyncio.run(main())
    print(f"\n✅ Test terminé. Vérifier l'état avec: python3 check_state.py {USER_ID}\n")
