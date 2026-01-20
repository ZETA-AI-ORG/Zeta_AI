#!/usr/bin/env python3
"""
🧪 TEST COMPLET DU CACHE REDIS INTÉGRÉ
Vérifie que le cache fonctionne parfaitement avec le système RAG
"""

import asyncio
import time
import requests
import json
from datetime import datetime

# Configuration du test
API_URL = "http://127.0.0.1:8001/chat"
TEST_QUERY = "BJR mme ou mr HUM VOILA dite je veux des couches culottes quels sont vos tarifs et combien la livraison a Angre?"
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
USER_ID = "testuser124"

def test_request(query_suffix=""):
    """Envoie une requête au chatbot et mesure le temps de réponse"""
    payload = {
        "message": TEST_QUERY + query_suffix,
        "company_id": COMPANY_ID,
        "user_id": USER_ID
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    print(f"📤 Envoi requête: {payload['message'][:50]}...")
    start_time = time.time()
    
    try:
        response = requests.post(API_URL, json=payload, headers=headers, timeout=30)
        end_time = time.time()
        
        if response.status_code == 200:
            data = response.json()
            elapsed = end_time - start_time
            
            return {
                "success": True,
                "response": data,
                "elapsed_time": elapsed,
                "cached": data.get("cached", False),
                "response_length": len(data.get("response", "")),
                "cache_hit_time": data.get("cache_hit_time", "N/A")
            }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}",
                "elapsed_time": end_time - start_time
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "elapsed_time": time.time() - start_time
        }

def print_test_result(test_name, result):
    """Affiche les résultats d'un test de manière formatée"""
    print(f"\n{'='*60}")
    print(f"🧪 {test_name}")
    print(f"{'='*60}")
    
    if result["success"]:
        print(f"✅ Succès!")
        print(f"⏱️  Temps de réponse: {result['elapsed_time']:.2f}s")
        print(f"🎯 Réponse mise en cache: {'✅ OUI' if result['cached'] else '❌ NON'}")
        if result["cached"]:
            print(f"⚡ Temps cache hit: {result['cache_hit_time']}")
        print(f"📝 Longueur réponse: {result['response_length']} caractères")
        
        # Afficher un aperçu de la réponse
        response_preview = result["response"].get("response", "")[:200]
        print(f"📄 Aperçu réponse: {response_preview}...")
        
        if result["cached"]:
            print(f"🚀 CACHE HIT DÉTECTÉ - Performance optimale!")
        else:
            print(f"⏳ Cache miss - Première requête ou expiration cache")
            
    else:
        print(f"❌ Échec!")
        print(f"🔴 Erreur: {result['error']}")
        print(f"⏱️  Temps avant échec: {result['elapsed_time']:.2f}s")

def main():
    """Test principal du cache Redis"""
    print(f"🚀 DÉBUT DU TEST CACHE REDIS INTÉGRÉ")
    print(f"🕐 Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 URL API: {API_URL}")
    print(f"🏢 Company ID: {COMPANY_ID}")
    print(f"👤 User ID: {USER_ID}")
    
    # TEST 1: Première requête (devrait être sans cache)
    print(f"\n🔥 TEST 1: Première requête (cache miss attendu)")
    result1 = test_request()
    print_test_result("Première requête", result1)
    
    if not result1["success"]:
        print(f"❌ ARRÊT: La première requête a échoué")
        return
    
    # Attendre un peu pour s'assurer que la sauvegarde cache est terminée
    print(f"\n⏳ Attente 2 secondes pour finalisation cache...")
    time.sleep(2)
    
    # TEST 2: Requête identique (devrait utiliser le cache)
    print(f"\n🔥 TEST 2: Requête identique (cache hit attendu)")
    result2 = test_request()
    print_test_result("Requête identique (cache attendu)", result2)
    
    # TEST 3: Requête légèrement différente (devrait être sans cache)
    print(f"\n🔥 TEST 3: Requête différente (cache miss attendu)")
    result3 = test_request(" merci beaucoup")
    print_test_result("Requête différente", result3)
    
    # ANALYSE COMPARATIVE
    print(f"\n{'='*60}")
    print(f"📊 ANALYSE COMPARATIVE DES PERFORMANCES")
    print(f"{'='*60}")
    
    if result1["success"] and result2["success"]:
        improvement = ((result1["elapsed_time"] - result2["elapsed_time"]) / result1["elapsed_time"]) * 100
        
        print(f"🎯 Requête 1 (sans cache): {result1['elapsed_time']:.2f}s")
        print(f"⚡ Requête 2 (avec cache): {result2['elapsed_time']:.2f}s")
        
        if result2["cached"]:
            print(f"🚀 AMÉLIORATION: {improvement:.1f}% plus rapide avec cache!")
            print(f"✅ CACHE REDIS: FONCTIONNEL")
            
            if improvement > 80:
                print(f"🏆 EXCELLENT: Cache très efficace (>80% d'amélioration)")
            elif improvement > 50:
                print(f"🎉 BON: Cache efficace (>50% d'amélioration)")
            else:
                print(f"⚠️  MODÉRÉ: Cache fonctionne mais amélioration <50%")
        else:
            print(f"❌ PROBLÈME: Requête identique pas mise en cache!")
            print(f"🔍 Vérifiez la configuration Redis et les logs")
    
    # TEST DE COHÉRENCE
    if result1["success"] and result2["success"]:
        response1 = result1["response"].get("response", "")
        response2 = result2["response"].get("response", "")
        
        print(f"\n📋 TEST DE COHÉRENCE DES RÉPONSES:")
        if response1 == response2:
            print(f"✅ Les réponses sont identiques (cache cohérent)")
        else:
            print(f"⚠️  Les réponses diffèrent légèrement (normal pour LLM)")
            print(f"📏 Longueur réponse 1: {len(response1)} caractères")
            print(f"📏 Longueur réponse 2: {len(response2)} caractères")
    
    print(f"\n🎉 TEST CACHE REDIS TERMINÉ!")

if __name__ == "__main__":
    main()



