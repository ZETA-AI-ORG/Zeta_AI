#!/usr/bin/env python3
"""
🧨 TEST CLIENT ULTIME avec vérification intégrée de finalisation
"""
import asyncio
import httpx
import time

BASE_URL = "http://127.0.0.1:8002"
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
USER_ID = "test_finalisation_001"

TEST_IMAGES = {
    'product': 'https://scontent.xx.fbcdn.net/v/t1.15752-9/553786504_1339650347521010_7584722332323008254_n.jpg?_nc_cat=108&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=iZMvAIEg5agQ7kNvwGVnL0m&_nc_oc=AdmmEA2PGIddOYXbqVDCtoX-X4unHqUgSUBz44wJJhMV4B_RX4_vz3-hfIf0Gg1DYt44ejVZAGHX_fHccpiQMA8g&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent.xx&oh=03_Q7cD3gH1On4PnpZDZQ4CYayHguk94A069j97-Eai6X-5Lw48_Q&oe=6911CDDA',
    'payment_2020': 'https://scontent.xx.fbcdn.net/v/t1.15752-9/556908482_1314851517042795_6410429215345539018_n.jpg?_nc_cat=105&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=FGYA3tLaNB8Q7kNvwEFLtNy&_nc_oc=AdnhSYhxtPMknvUViCVLIxdq0psdWOZ9d5lLqoGBIzM4BwPMJfxTWbgDf2rraR9cbl-xHoxCoLL8X0Hf8rR18N30&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent.xx&oh=03_Q7cD3gGKjKR_xt29vtVgdJSUwjCSgV-A-H0IdCphHvF0MvGBow&oe=6911C04A',
}

async def send_message(message: str = "", images: list = None):
    async with httpx.AsyncClient(timeout=60.0) as client:
        payload = {
            "company_id": COMPANY_ID,
            "user_id": USER_ID,
            "message": message
        }
        if images:
            payload["images"] = images
        
        start = time.time()
        response = await client.post(f"{BASE_URL}/chat", json=payload)
        duration = time.time() - start
        
        return response.json(), duration

def check_response(response: dict, expected_keywords: list = None, should_finalize: bool = False):
    """Vérifie si la réponse contient les éléments attendus"""
    response_text = response.get('response', '').lower()
    
    if should_finalize:
        if "commande ok" in response_text or "ne réponds pas" in response_text:
            print("✅ FINALISATION DÉTECTÉE")
            return True
        else:
            print(f"❌ FINALISATION MANQUANTE - Réponse: {response['response']}")
            return False
    
    if expected_keywords:
        for keyword in expected_keywords:
            if keyword.lower() in response_text:
                print(f"✅ Keyword trouvé: {keyword}")
                return True
        print(f"❌ Aucun keyword trouvé parmi: {expected_keywords}")
        return False
    
    return True

async def run_test():
    print("\n" + "="*80)
    print("🎯 TEST FINALISATION RAPIDE")
    print("="*80 + "\n")
    
    finalization_success = False
    
    # 1. Photo produit
    print("📸 Étape 1: Envoi photo produit")
    result, duration = await send_message("Voici le produit", images=[TEST_IMAGES['product']])
    print(f"⏱️  {duration:.2f}s - {result['response']}")
    check_response(result, expected_keywords=["paiement"])
    await asyncio.sleep(1)
    
    # 2. Photo paiement
    print("\n💳 Étape 2: Envoi capture paiement 2020F")
    result, duration = await send_message("Voici mon paiement", images=[TEST_IMAGES['payment_2020']])
    print(f"⏱️  {duration:.2f}s - {result['response']}")
    check_response(result, expected_keywords=["zone", "numéro"])
    await asyncio.sleep(1)
    
    # 3. Zone
    print("\n📍 Étape 3: Zone Cocody")
    result, duration = await send_message("Cocody")
    print(f"⏱️  {duration:.2f}s - {result['response']}")
    check_response(result, expected_keywords=["numéro"])
    await asyncio.sleep(1)
    
    # 4. Numéro - DOIT FINALISER ICI
    print("\n📞 Étape 4: Numéro (DEVRAIT FINALISER)")
    result, duration = await send_message("0709876543")
    print(f"⏱️  {duration:.2f}s - {result['response']}")
    finalization_success = check_response(result, should_finalize=True)
    
    print("\n" + "="*80)
    if finalization_success:
        print("🎉 SUCCÈS TOTAL : Finalisation fonctionne !")
        print("="*80)
        return True
    else:
        print("❌ ÉCHEC : Finalisation ne fonctionne pas")
        print("="*80)
        return False

async def main():
    try:
        success = await run_test()
        exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
