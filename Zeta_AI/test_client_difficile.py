#!/usr/bin/env python3
"""
😤 TEST CLIENT DIFFICILE - Change d'avis, sujets hors domaine
Client qui change d'intention 3+ fois, étale la conversation avec détails inutiles et hors domaine
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
USER_ID = "client_difficile_003"  # Format similaire à testuser314

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
# SCÉNARIO CLIENT DIFFICILE
# ═══════════════════════════════════════════════════════════════════════════════

async def run_difficult_client_scenario():
    """
    Scénario: Client difficile qui change d'avis et part hors sujet
    
    Workflow chaotique:
    1. Salutation bizarre
    2. Question hors domaine (météo)
    3. Demande produit
    4. CHANGEMENT D'AVIS #1 - veut autre chose
    5. Sujet hors domaine (politique)
    6. Retour produit initial
    7. Envoie photo
    8. CHANGEMENT D'AVIS #2 - veut annuler
    9. Question hors domaine (football)
    10. Finalement confirme
    11. CHANGEMENT D'AVIS #3 - veut modifier quantité
    12. Envoie paiement
    13. Histoire personnelle longue
    14. Donne zone
    15. Sujet inutile
    16. Donne numéro
    """
    
    print("\n" + "😤 " * 20)
    print("TEST CLIENT DIFFICILE - Change d'avis et hors domaine")
    print("😤 " * 20 + "\n")
    
    step = 1
    changements_avis = 0
    sujets_hors_domaine = 0
    
    # ═══ ÉTAPE 1: Salutation bizarre ═══
    result = await send_message("Yo c'est moi hein tu me reconnais ?")
    print_conversation(step, "Yo c'est moi hein tu me reconnais ?", result['response'], result['duration'])
    await asyncio.sleep(1.5)
    step += 1
    
    # ═══ ÉTAPE 2: Question hors domaine - MÉTÉO ═══
    sujets_hors_domaine += 1
    result = await send_message("Il fait combien de degrés aujourd'hui à Abidjan ?")
    print_conversation(step, "Il fait combien de degrés aujourd'hui à Abidjan ?", result['response'], result['duration'])
    await asyncio.sleep(1.5)
    step += 1
    
    # ═══ ÉTAPE 3: Demande produit ═══
    result = await send_message("Bon sinon tu vends des couches là ou quoi ?")
    print_conversation(step, "Bon sinon tu vends des couches là ou quoi ?", result['response'], result['duration'])
    await asyncio.sleep(1.5)
    step += 1
    
    # ═══ ÉTAPE 4: CHANGEMENT D'AVIS #1 ═══
    changements_avis += 1
    result = await send_message("Ah non attends en fait je veux du lait pour bébé plutôt")
    print_conversation(step, f"[CHANGEMENT #{changements_avis}] Ah non attends en fait je veux du lait pour bébé plutôt", result['response'], result['duration'])
    await asyncio.sleep(1.5)
    step += 1
    
    # ═══ ÉTAPE 5: Hors domaine - POLITIQUE ═══
    sujets_hors_domaine += 1
    result = await send_message("Tu as suivi les élections hier ? C'était chaud non ?")
    print_conversation(step, f"[HORS DOMAINE #{sujets_hors_domaine}] Tu as suivi les élections hier ?", result['response'], result['duration'])
    await asyncio.sleep(1.5)
    step += 1
    
    # ═══ ÉTAPE 6: Retour produit initial ═══
    result = await send_message("Bon laisse, je vais prendre les couches finalement")
    print_conversation(step, "Bon laisse, je vais prendre les couches finalement", result['response'], result['duration'])
    await asyncio.sleep(1.5)
    step += 1
    
    # ═══ ÉTAPE 7: Envoie photo avec commentaire inutile ═══
    result = await send_message("Tiens la photo mais désolé c'est flou mon téléphone est vieux", images=[TEST_IMAGES['product']])
    print_conversation(step, "Tiens la photo mais désolé c'est flou [Photo]", result['response'], result['duration'])
    await asyncio.sleep(1.5)
    step += 1
    
    # ═══ ÉTAPE 8: CHANGEMENT D'AVIS #2 - Veut annuler ═══
    changements_avis += 1
    result = await send_message("Attends je sais pas si j'ai assez d'argent, laisse tomber")
    print_conversation(step, f"[CHANGEMENT #{changements_avis}] Attends je sais pas si j'ai assez d'argent, laisse tomber", result['response'], result['duration'])
    await asyncio.sleep(1.5)
    step += 1
    
    # ═══ ÉTAPE 9: Hors domaine - FOOTBALL ═══
    sujets_hors_domaine += 1
    result = await send_message("Tu as vu le match des Éléphants hier ? On a gagné 3-0 !")
    print_conversation(step, f"[HORS DOMAINE #{sujets_hors_domaine}] Tu as vu le match des Éléphants ?", result['response'], result['duration'])
    await asyncio.sleep(1.5)
    step += 1
    
    # ═══ ÉTAPE 10: Histoire personnelle longue ═══
    result = await send_message("Bon en fait mon bébé pleure trop la nuit, sa mère dit que c'est les couches qui le grattent tu vois, donc je me dis que je vais essayer vos couches là peut-être c'est mieux")
    print_conversation(step, "Bon en fait mon bébé pleure trop la nuit...", result['response'], result['duration'])
    await asyncio.sleep(1.5)
    step += 1
    
    # ═══ ÉTAPE 11: Finalement confirme ═══
    result = await send_message("Ok je confirme")
    print_conversation(step, "Ok je confirme", result['response'], result['duration'])
    await asyncio.sleep(1.5)
    step += 1
    
    # ═══ ÉTAPE 12: CHANGEMENT D'AVIS #3 - Quantité ═══
    changements_avis += 1
    result = await send_message("Attends en fait je veux 2 paquets pas 1")
    print_conversation(step, f"[CHANGEMENT #{changements_avis}] Attends en fait je veux 2 paquets pas 1", result['response'], result['duration'])
    await asyncio.sleep(1.5)
    step += 1
    
    # ═══ ÉTAPE 13: Détail inutile sur paiement ═══
    result = await send_message("Bon je vais payer avec le téléphone de ma femme parce que moi j'ai plus de crédit")
    print_conversation(step, "Bon je vais payer avec le téléphone de ma femme...", result['response'], result['duration'])
    await asyncio.sleep(1.5)
    step += 1
    
    # ═══ ÉTAPE 14: Envoie paiement ═══
    result = await send_message("Voilà", images=[TEST_IMAGES['payment_2020']])
    print_conversation(step, "Voilà [Paiement 2020 FCFA]", result['response'], result['duration'])
    await asyncio.sleep(1.5)
    step += 1
    
    # ═══ ÉTAPE 15: Hors domaine - SANTÉ ═══
    sujets_hors_domaine += 1
    result = await send_message("Au fait tu connais un bon pédiatre à Abidjan ?")
    print_conversation(step, f"[HORS DOMAINE #{sujets_hors_domaine}] Au fait tu connais un bon pédiatre ?", result['response'], result['duration'])
    await asyncio.sleep(1.5)
    step += 1
    
    # ═══ ÉTAPE 16: Donne zone avec détails inutiles ═══
    result = await send_message("Je suis à Yopougon, pas loin du marché là-bas tu vois, à côté de l'école primaire")
    print_conversation(step, "Je suis à Yopougon, pas loin du marché...", result['response'], result['duration'])
    await asyncio.sleep(1.5)
    step += 1
    
    # ═══ ÉTAPE 17: Question philosophique ═══
    sujets_hors_domaine += 1
    result = await send_message("Mais franchement pourquoi les bébés pleurent autant la nuit ?")
    print_conversation(step, f"[HORS DOMAINE #{sujets_hors_domaine}] Pourquoi les bébés pleurent autant ?", result['response'], result['duration'])
    await asyncio.sleep(1.5)
    step += 1
    
    # ═══ ÉTAPE 18: Donne numéro avec détail inutile ═══
    result = await send_message("Mon numéro c'est 0707654321 mais des fois ça sonne pas faut insister")
    print_conversation(step, "Mon numéro c'est 0707654321 mais des fois ça sonne pas", result['response'], result['duration'])
    
    # ═══ RÉSUMÉ ═══
    print(f"\n{'='*80}")
    print("📊 RÉSUMÉ CLIENT DIFFICILE")
    print(f"{'='*80}")
    print(f"✅ Commande finalement complétée en {step} étapes")
    print(f"🔄 Changements d'avis: {changements_avis}")
    print(f"🚫 Sujets hors domaine: {sujets_hors_domaine}")
    print(f"😤 Workflow très chaotique mais géré")
    print(f"🎯 Test de robustesse du système")
    print(f"{'='*80}\n")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    try:
        await run_difficult_client_scenario()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
