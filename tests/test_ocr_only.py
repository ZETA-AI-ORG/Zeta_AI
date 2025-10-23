#!/usr/bin/env python3
"""
🧪 TEST OCR BOTLIVE ISOLÉ
========================

Teste uniquement la validation OCR des paiements SANS le LLM
pour vérifier que la détection fonctionne correctement.
"""

import asyncio
import httpx
import time

# Configuration
BASE_URL = "http://127.0.0.1:8002"
COMPANY_ID = "4OS4yFcf2LZwxhKojbAVbKuVuSdb"
USER_ID = "test_ocr_" + str(int(time.time()))

# URLs des images de test (screenshots Wave)
IMAGE_INSUFFISANT = "https://scontent.xx.fbcdn.net/v/t1.15752-9/553547596_833613639156226_7121847885682360094_n.jpg?_nc_cat=101&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=DamxAq1f9OwQ7kNvwFSbPlg&_nc_oc=AdlYZF2Q2WyPz7SoP6HFp7gZCnmgAysN4ZCziXM2nHv8itrZrced2lMSff1szWQ9V-7WRbl3vV_-uJ9l3-Uxq7ha&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent.xx&oh=03_Q7cD3gFO-SvfS03vBW39la32NGTcsXuPEGNsnVA6mSvUHOResw&oe=691D864A"
IMAGE_CORRECT = "https://scontent.xx.fbcdn.net/v/t1.15752-9/556908482_1314851517042795_6410429215345539018_n.jpg?_nc_cat=105&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=7oeAkz1vXk4Q7kNvwHsBEm8&_nc_oc=AdkRG6vf8C7mCWK6G0223SycGhXGPZ9S5mn8iK369aoCBNGNFLGSYK0R-yFITkJ-uro_BO7rcX9W2ximO0S4l25C&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent.xx&oh=03_Q7cD3gFy4KBx2MWFGHs3HzwWsG7vQiUcM4NU3IBpkP2B5ZoWAQ&oe=691D9DCA"


async def send_image(image_url: str, message: str = "") -> dict:
    """Envoie une image au chatbot"""
    payload = {
        "company_id": COMPANY_ID,
        "user_id": USER_ID,
        "message": message,
        "images": [image_url],
        "botlive_enabled": True
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(f"{BASE_URL}/chat", json=payload)
        return response.json()


def print_separator(title: str):
    """Affiche un séparateur visuel"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


async def main():
    print_separator("🧪 TEST OCR BOTLIVE ISOLÉ")
    
    print(f"📋 Configuration:")
    print(f"   - Company ID: {COMPANY_ID}")
    print(f"   - User ID: {USER_ID}")
    print(f"   - Server: {BASE_URL}")
    print()
    
    # ═══════════════════════════════════════════════════════════════
    # TEST 1: Image avec montant INSUFFISANT (1000 FCFA < 2000)
    # ═══════════════════════════════════════════════════════════════
    print_separator("TEST 1: Screenshot INSUFFISANT (1000 FCFA)")
    
    print(f"📸 Envoi image: {IMAGE_INSUFFISANT[:80]}...")
    print(f"💬 Message: 'Voilà j'ai envoyé le paiement'")
    print()
    
    start_time = time.time()
    result1 = await send_image(IMAGE_INSUFFISANT, "Voilà j'ai envoyé le paiement")
    duration1 = time.time() - start_time
    
    print(f"⏱️  Temps de réponse: {duration1:.2f}s")
    print()
    print(f"🤖 Réponse LLM:")
    print(f"   {result1.get('response', 'ERREUR: Pas de réponse')}")
    print()
    
    # Vérifier si le rejet est détecté
    response_text = result1.get('response', '').lower()
    if 'insuffisant' in response_text or '1000' in response_text or 'rejete' in response_text:
        print("✅ SUCCÈS: OCR a détecté le montant insuffisant!")
    else:
        print("❌ ÉCHEC: OCR n'a PAS détecté le problème!")
    
    print()
    input("⏸️  Appuyez sur ENTRÉE pour continuer au test 2...")
    
    # ═══════════════════════════════════════════════════════════════
    # TEST 2: Image avec montant CORRECT (2000 FCFA)
    # ═══════════════════════════════════════════════════════════════
    print_separator("TEST 2: Screenshot CORRECT (2000 FCFA)")
    
    print(f"📸 Envoi image: {IMAGE_CORRECT[:80]}...")
    print(f"💬 Message: 'Voilà maintenant c'est bon, 2000 FCFA'")
    print()
    
    start_time = time.time()
    result2 = await send_image(IMAGE_CORRECT, "Voilà maintenant c'est bon, 2000 FCFA")
    duration2 = time.time() - start_time
    
    print(f"⏱️  Temps de réponse: {duration2:.2f}s")
    print()
    print(f"🤖 Réponse LLM:")
    print(f"   {result2.get('response', 'ERREUR: Pas de réponse')}")
    print()
    
    # Vérifier si la validation est détectée
    response_text = result2.get('response', '').lower()
    if 'validé' in response_text or 'confirmé' in response_text or '2000' in response_text:
        print("✅ SUCCÈS: OCR a validé le paiement!")
    else:
        print("❌ ÉCHEC: OCR n'a PAS validé le paiement!")
    
    # ═══════════════════════════════════════════════════════════════
    # RÉSUMÉ FINAL
    # ═══════════════════════════════════════════════════════════════
    print_separator("📊 RÉSUMÉ DES TESTS OCR")
    
    print(f"Test 1 (Insuffisant): {duration1:.2f}s")
    print(f"Test 2 (Correct): {duration2:.2f}s")
    print(f"Temps total: {duration1 + duration2:.2f}s")
    print()
    
    print("🎯 Prochaine étape:")
    print("   Si les 2 tests sont ✅, lance le test HARDCORE complet:")
    print("   python tests/conversation_simulator.py --scenario hardcore")
    print()


if __name__ == "__main__":
    asyncio.run(main())
