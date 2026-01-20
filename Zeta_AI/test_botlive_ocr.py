#!/usr/bin/env python3
"""
Test Botlive avec OCR - Vérification système complet
"""
import requests
import json

# Configuration
API_URL = "http://localhost:8000/chat"
COMPANY_ID = "4OS4yFcf2LZwxhKojbAVbKuVuSdb"
USER_ID = "test_ocr_user_001"

# URL d'une image de test (capture de paiement Wave)
# Remplace par une vraie URL d'image si disponible
TEST_IMAGE_URL = "https://example.com/test_payment.jpg"  # À remplacer

def test_botlive_with_image():
    """Test complet : salutation + envoi image paiement"""
    
    print("="*80)
    print("🧪 TEST BOTLIVE OCR - SYSTÈME HYBRIDE")
    print("="*80)
    print(f"Company ID: {COMPANY_ID}")
    print(f"User ID: {USER_ID}")
    print(f"API URL: {API_URL}")
    print("="*80)
    
    # Test 1: Salutation
    print("\n📝 TEST 1: Salutation initiale")
    print("-"*80)
    
    payload1 = {
        "company_id": COMPANY_ID,
        "user_id": USER_ID,
        "message": "Bonjour, je veux commander",
        "images": [],
        "conversation_history": ""
    }
    
    try:
        response1 = requests.post(API_URL, json=payload1, timeout=30)
        response1.raise_for_status()
        data1 = response1.json()
        
        print(f"✅ Statut: {response1.status_code}")
        print(f"📤 Réponse IA: {data1.get('response', 'N/A')[:200]}...")
        print(f"🤖 LLM utilisé: {data1.get('llm_used', 'N/A')}")
        print(f"⏱️  Temps: {data1.get('processing_time', 0):.2f}s")
        
    except Exception as e:
        print(f"❌ Erreur Test 1: {e}")
        return
    
    # Test 2: Envoi image paiement
    print("\n📝 TEST 2: Envoi capture paiement")
    print("-"*80)
    print(f"⚠️  ATTENTION: Remplace TEST_IMAGE_URL par une vraie URL d'image")
    print(f"Image URL: {TEST_IMAGE_URL}")
    
    payload2 = {
        "company_id": COMPANY_ID,
        "user_id": USER_ID,
        "message": "Voici mon paiement",
        "images": [TEST_IMAGE_URL],
        "conversation_history": f"user: Bonjour, je veux commander\nIA: {data1.get('response', '')}"
    }
    
    try:
        response2 = requests.post(API_URL, json=payload2, timeout=60)
        response2.raise_for_status()
        data2 = response2.json()
        
        print(f"✅ Statut: {response2.status_code}")
        print(f"📤 Réponse IA: {data2.get('response', 'N/A')[:300]}...")
        print(f"🤖 LLM utilisé: {data2.get('llm_used', 'N/A')}")
        print(f"⏱️  Temps: {data2.get('processing_time', 0):.2f}s")
        
        # Afficher métadonnées OCR si présentes
        if 'context' in data2:
            context = data2['context']
            if 'filtered_transactions' in context:
                print(f"\n💰 Transactions détectées:")
                for trans in context['filtered_transactions']:
                    print(f"   - {trans.get('amount', 'N/A')} {trans.get('currency', 'FCFA')}")
        
    except Exception as e:
        print(f"❌ Erreur Test 2: {e}")
        return
    
    print("\n" + "="*80)
    print("✅ TESTS TERMINÉS")
    print("="*80)

if __name__ == "__main__":
    print("\n⚠️  INSTRUCTIONS:")
    print("1. Assure-toi que le serveur tourne (uvicorn app:app --reload)")
    print("2. Remplace TEST_IMAGE_URL par une vraie URL d'image de paiement")
    print("3. Lance ce script: python test_botlive_ocr.py")
    print()
    
    input("Appuie sur ENTRÉE pour lancer les tests...")
    test_botlive_with_image()
