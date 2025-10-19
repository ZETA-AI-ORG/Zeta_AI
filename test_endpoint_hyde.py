#!/usr/bin/env python3
"""
🎯 TEST ENDPOINT CHAT - SYSTÈME HYDE EN CONDITIONS RÉELLES
Teste l'intelligence du scoring HyDE via l'API /chat
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

# Configuration
ENDPOINT_URL = "http://127.0.0.1:8001/chat"
COMPANY_ID = "XkCn8fjNWEWwqiiKMgJX7OcQrUJ3"  # RueduGrossiste

# Requêtes de test variées pour évaluer le HyDE dynamique
TEST_QUERIES = [
    # Tests basiques e-commerce
    {
        "query": "bonsoir je veux le casque rouge combien ça coûte",
        "expected_intent": "PRIX",
        "critical_words": ["combien", "casque", "rouge", "coûte"]
    },
    {
        "query": "samsung galaxy s24 disponible en stock plateau",
        "expected_intent": "STOCK", 
        "critical_words": ["samsung", "galaxy", "s24", "disponible", "stock", "plateau"]
    },
    {
        "query": "livraison cocody paiement wave possible aujourd'hui",
        "expected_intent": "LIVRAISON",
        "critical_words": ["livraison", "cocody", "paiement", "wave"]
    },
    {
        "query": "contact whatsapp pour commander iphone 15 pro",
        "expected_intent": "CONTACT",
        "critical_words": ["contact", "whatsapp", "commander", "iphone"]
    },
    {
        "query": "yamaha mt 125 prix moov money riviera golf",
        "expected_intent": "PRIX",
        "critical_words": ["yamaha", "mt", "125", "prix", "moov", "money", "riviera", "golf"]
    },
    # Tests avec mots parasites
    {
        "query": "euh bon alors je voudrais savoir le prix du casque rouge s'il vous plaît",
        "expected_intent": "PRIX",
        "critical_words": ["prix", "casque", "rouge"],
        "noise_words": ["euh", "bon", "alors", "voudrais", "savoir", "plaît"]
    },
    {
        "query": "salut moi c'est jean je cherche un samsung galaxy disponible à yopougon",
        "expected_intent": "STOCK",
        "critical_words": ["samsung", "galaxy", "disponible", "yopougon"],
        "noise_words": ["salut", "moi", "jean", "cherche"]
    }
]

def log_test(message, data=None):
    """Log formaté pour les tests"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[TEST][{timestamp}] {message}")
    if data:
        print(f"  📊 {json.dumps(data, indent=2, ensure_ascii=False)}")

async def test_chat_endpoint(session, test_case, test_num):
    """Teste une requête via l'endpoint /chat"""
    print(f"\n{'='*60}")
    print(f"📝 TEST {test_num}: '{test_case['query']}'")
    print(f"🎯 Intention attendue: {test_case['expected_intent']}")
    print(f"🔑 Mots critiques: {test_case['critical_words']}")
    
    payload = {
        "message": test_case["query"],
        "company_id": COMPANY_ID,
        "conversation_id": f"test_hyde_{test_num}_{int(time.time())}"
    }
    
    try:
        start_time = time.time()
        
        async with session.post(ENDPOINT_URL, json=payload) as response:
            end_time = time.time()
            duration = (end_time - start_time) * 1000
            
            if response.status == 200:
                result = await response.json()
                
                print(f"✅ SUCCÈS ({duration:.1f}ms)")
                print(f"📤 Réponse: {result.get('response', 'N/A')[:100]}...")
                
                # Analyser les logs de scoring si disponibles
                if 'debug_info' in result:
                    debug = result['debug_info']
                    if 'hyde_scoring' in debug:
                        scoring = debug['hyde_scoring']
                        print(f"🧠 SCORING HYDE DÉTECTÉ:")
                        print(f"  🎯 Intention: {scoring.get('intention', 'N/A')}")
                        print(f"  📊 Scores: {scoring.get('scores_detailles', {})}")
                        print(f"  🔍 Query filtrée: {scoring.get('query_filtree', 'N/A')}")
                        print(f"  ⚡ Efficacité: {scoring.get('efficacite', 'N/A')}")
                        
                        # Vérifier si les mots critiques ont de bons scores
                        scores = scoring.get('scores_detailles', {})
                        critical_analysis = []
                        for word in test_case['critical_words']:
                            if word in scores:
                                score = scores[word]
                                status = "✅" if score >= 7 else "⚠️" if score >= 5 else "❌"
                                critical_analysis.append(f"{status} '{word}': {score}")
                            else:
                                critical_analysis.append(f"❓ '{word}': absent")
                        
                        print(f"  🎯 Analyse mots critiques:")
                        for analysis in critical_analysis:
                            print(f"    {analysis}")
                
                return True
                
            else:
                print(f"❌ ERREUR HTTP {response.status}")
                error_text = await response.text()
                print(f"  💥 Détails: {error_text[:200]}")
                return False
                
    except Exception as e:
        print(f"💥 EXCEPTION: {str(e)}")
        return False

async def run_endpoint_tests():
    """Lance tous les tests d'endpoint"""
    print("🚀 DÉMARRAGE DES TESTS ENDPOINT HYDE")
    print(f"🎯 URL: {ENDPOINT_URL}")
    print(f"🏢 Company ID: {COMPANY_ID}")
    
    async with aiohttp.ClientSession() as session:
        success_count = 0
        total_tests = len(TEST_QUERIES)
        
        for i, test_case in enumerate(TEST_QUERIES, 1):
            success = await test_chat_endpoint(session, test_case, i)
            if success:
                success_count += 1
            
            # Pause entre les tests pour éviter la surcharge
            await asyncio.sleep(1)
        
        print(f"\n{'='*60}")
        print(f"🎉 RÉSULTATS FINAUX")
        print(f"✅ Succès: {success_count}/{total_tests}")
        print(f"📊 Taux de réussite: {(success_count/total_tests)*100:.1f}%")
        
        if success_count == total_tests:
            print("🏆 TOUS LES TESTS RÉUSSIS - SYSTÈME HYDE OPÉRATIONNEL!")
        else:
            print("⚠️ Certains tests ont échoué - Vérifier la configuration")

if __name__ == "__main__":
    print("🎯 TEST DU SYSTÈME HYDE EN CONDITIONS RÉELLES")
    print("=" * 60)
    asyncio.run(run_endpoint_tests())
