#!/usr/bin/env python3
"""
🧮 TEST DU CALCULATEUR DE PRIX RUE DU GROS
Script de test pour valider le système de calcul de prix automatique
"""

import requests
import json
import time
from datetime import datetime

# Configuration du test
API_URL = "http://127.0.0.1:8001/chat"
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
USER_ID = "testuser126"

def test_price_calculation():
    """Test du système de calcul de prix"""
    
    print("🧮 TEST DU CALCULATEUR DE PRIX RUE DU GROS")
    print("=" * 60)
    print(f"🕐 Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 URL API: {API_URL}")
    print(f"🏢 Company ID: {COMPANY_ID}")
    print(f"👤 User ID: {USER_ID}")
    print()
    
    # Tests de calcul de prix
    test_cases = [
        {
            "name": "Test 1: Couches culottes simples",
            "message": "Je veux commander 2 paquets de couches culottes, combien ça coûte ?",
            "expected": "Prix calculé automatiquement"
        },
        {
            "name": "Test 2: Couches à pression avec taille",
            "message": "Mon bébé fait 8kg, je veux des couches taille 3, combien pour 3 paquets ?",
            "expected": "Prix calculé avec taille spécifique"
        },
        {
            "name": "Test 3: Avec zone de livraison",
            "message": "Je veux 6 paquets de couches culottes, je suis à Cocody, combien au total ?",
            "expected": "Prix + frais de livraison Cocody"
        },
        {
            "name": "Test 4: Demande de récapitulatif",
            "message": "Pouvez-vous me faire un récapitulatif de ma commande de 12 paquets de couches culottes ?",
            "expected": "Récapitulatif structuré complet"
        },
        {
            "name": "Test 5: Couches adultes",
            "message": "Je veux 3 paquets de couches adultes, combien ça coûte ?",
            "expected": "Prix des couches adultes"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"🔥 {test_case['name']}")
        print(f"📤 Message: {test_case['message']}")
        print(f"🎯 Attendu: {test_case['expected']}")
        print("-" * 40)
        
        try:
            # Envoyer la requête
            payload = {
                "message": test_case["message"],
                "company_id": COMPANY_ID,
                "user_id": USER_ID
            }
            
            start_time = time.time()
            response = requests.post(API_URL, json=payload, timeout=30)
            end_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                response_time = end_time - start_time
                
                print(f"✅ Succès - Temps: {response_time:.2f}s")
                
                # Vérifier si le prix a été calculé
                price_calculated = data.get("price_calculated", False)
                price_info = data.get("price_info")
                
                if price_calculated and price_info:
                    print(f"🧮 Prix calculé: {price_info.get('total', 0):,.0f} FCFA")
                    print(f"📦 Produits: {len(price_info.get('products', []))}")
                    print(f"🚚 Livraison: {price_info.get('delivery_cost', 0):,.0f} FCFA")
                    
                    # Afficher un aperçu de la réponse
                    response_text = data.get("response", "")
                    print(f"📝 Aperçu réponse: {response_text[:200]}...")
                    
                    results.append({
                        "test": test_case["name"],
                        "status": "SUCCESS",
                        "price_calculated": True,
                        "total_price": price_info.get('total', 0),
                        "response_time": response_time,
                        "response_length": len(response_text)
                    })
                else:
                    print(f"⚠️ Aucun prix calculé")
                    print(f"📝 Réponse: {data.get('response', '')[:200]}...")
                    
                    results.append({
                        "test": test_case["name"],
                        "status": "NO_PRICE",
                        "price_calculated": False,
                        "response_time": response_time,
                        "response_length": len(data.get('response', ''))
                    })
                
            else:
                print(f"❌ Erreur HTTP {response.status_code}: {response.text}")
                results.append({
                    "test": test_case["name"],
                    "status": "ERROR",
                    "error": f"HTTP {response.status_code}"
                })
                
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
            results.append({
                "test": test_case["name"],
                "status": "EXCEPTION",
                "error": str(e)
            })
        
        print()
        time.sleep(1)  # Pause entre les tests
    
    # Analyse des résultats
    print("📊 ANALYSE DES RÉSULTATS")
    print("=" * 60)
    
    total_tests = len(results)
    successful_tests = len([r for r in results if r["status"] == "SUCCESS"])
    price_calculated_tests = len([r for r in results if r.get("price_calculated", False)])
    
    print(f"📈 Statistiques:")
    print(f"   • Tests exécutés: {total_tests}")
    print(f"   • Tests réussis: {successful_tests}")
    print(f"   • Prix calculés: {price_calculated_tests}")
    print(f"   • Taux de succès: {(successful_tests/total_tests)*100:.1f}%")
    print(f"   • Taux de calcul prix: {(price_calculated_tests/total_tests)*100:.1f}%")
    
    print(f"\n📋 Détail par test:")
    for result in results:
        status_emoji = "✅" if result["status"] == "SUCCESS" else "❌" if result["status"] == "ERROR" else "⚠️"
        print(f"   {status_emoji} {result['test']}: {result['status']}")
        if result.get("price_calculated"):
            print(f"      💰 Prix: {result.get('total_price', 0):,.0f} FCFA")
        if result.get("response_time"):
            print(f"      ⏱️ Temps: {result['response_time']:.2f}s")
    
    print(f"\n🎉 TEST TERMINÉ!")
    
    return results

if __name__ == "__main__":
    test_price_calculation()



