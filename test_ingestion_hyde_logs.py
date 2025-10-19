#!/usr/bin/env python3
"""
Test d'ingestion réelle pour vérifier les nouveaux logs HyDE détaillés
"""

import requests
import json
import time

def test_ingestion_with_hyde_logs():
    """Lance une ingestion réelle pour tester les logs HyDE"""
    
    # URL de l'endpoint d'ingestion
    url = "http://localhost:8000/ingestion/ingest-structured"
    
    # Données de test avec nombres pour vérifier le scoring
    test_data = {
        "company_id": "TEST_HYDE_LOGS_123",
        "documents": [
            {
                "id": "test_product_hyde_1",
                "content": "=== PRODUIT === CASQUE MOTO ROUGE Prix 3500 FCFA Stock 25",
                "metadata": {
                    "type": "product",
                    "product_name": "CASQUE MOTO",
                    "color": "ROUGE", 
                    "price": 3500,
                    "currency": "FCFA",
                    "stock": 25,
                    "searchable_text": "CASQUE MOTO ROUGE Prix 3500 FCFA Stock 25 disponible livraison rapide"
                }
            },
            {
                "id": "test_delivery_hyde_2", 
                "content": "=== LIVRAISON === Livraison Cocody 1500 FCFA délai 24h",
                "metadata": {
                    "type": "delivery",
                    "zone": "Cocody",
                    "price": 1500,
                    "currency": "FCFA",
                    "delay": "24h",
                    "searchable_text": "Livraison Cocody 1500 FCFA délai 24h transport rapide"
                }
            }
        ]
    }
    
    print("🚀 LANCEMENT INGESTION TEST HYDE LOGS")
    print("=" * 60)
    print(f"URL: {url}")
    print(f"Company ID: {test_data['company_id']}")
    print(f"Documents: {len(test_data['documents'])}")
    
    try:
        # Lancer l'ingestion
        response = requests.post(url, json=test_data, timeout=30)
        
        print(f"\n📊 RÉSULTAT INGESTION:")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ INGESTION RÉUSSIE")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("❌ ERREUR INGESTION")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ ERREUR REQUÊTE: {e}")
    
    print("\n" + "=" * 60)
    print("🔍 VÉRIFIEZ LES LOGS SERVEUR POUR:")
    print("- [HYDE_SCORER_DETAILED] avec classement par score")
    print("- Nombres (3500, 1500) scorés à 0")
    print("- Mots métier (casque, rouge, livraison, cocody) scorés haut")
    print("- Liste complète triée par score")

if __name__ == "__main__":
    test_ingestion_with_hyde_logs()
