#!/usr/bin/env python3
"""
Script de test pour vérifier l'intégrité des données après découpage intelligent
Vérifie que les vraies données d'entreprise sont correctement préservées
"""

import requests
import json
from typing import Dict, Any, List

def test_data_integrity():
    """Test l'intégrité des données après ingestion avec découpage intelligent"""
    
    # Données de test réelles (simulant N8N)
    test_payload = {
        "company_id": "XkCn8fjNWEWwqiiKMgJX7OcQrUJ3",
        "documents": [
            {
                "content": "Casque moto rouge disponible en stock, prix 6500 FCFA",
                "metadata": {
                    "type": "product",
                    "document_id": "prod_001",
                    "product_name": "Casque Moto Rouge",
                    "category": "casques",
                    "color": "rouge",
                    "price": 6500,
                    "stock": 80,
                    "currency": "FCFA",
                    "searchable_text": "Casque moto rouge disponible en stock, prix 6500 FCFA"
                }
            },
            {
                "content": "Livraison Yopougon 1000 FCFA, délai 24h",
                "metadata": {
                    "type": "delivery",
                    "document_id": "delivery_001",
                    "zone": "Yopougon",
                    "city": "Abidjan",
                    "price_min": 1000,
                    "price_max": 1000,
                    "currency": "FCFA",
                    "sla_hours_min": 24,
                    "sla_hours_max": 24,
                    "searchable_text": "Livraison Yopougon 1000 FCFA, délai 24h"
                }
            },
            {
                "content": "Support WhatsApp +2250787360757",
                "metadata": {
                    "type": "support",
                    "document_id": "support_001",
                    "method": "whatsapp",
                    "phone_e164": "+2250787360757",
                    "channels": ["whatsapp"],
                    "searchable_text": "Support WhatsApp +2250787360757"
                }
            },
            {
                "content": "Paiement Wave disponible",
                "metadata": {
                    "type": "payment",
                    "document_id": "payment_001",
                    "method": "wave",
                    "searchable_text": "Paiement Wave disponible"
                }
            },
            {
                "content": "Boutique située à Cocody",
                "metadata": {
                    "type": "location",
                    "document_id": "location_001",
                    "zone": "Cocody",
                    "location_type": "boutique",
                    "searchable_text": "Boutique située à Cocody"
                }
            }
        ]
    }
    
    print("🔍 Test d'intégrité des données après découpage intelligent")
    print("=" * 60)
    
    # 1. Ingestion des données
    print("1️⃣ Ingestion des données...")
    try:
        response = requests.post(
            "http://localhost:8001/ingestion/ingest-structured",
            json=test_payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Ingestion réussie: {result}")
        else:
            print(f"❌ Erreur ingestion: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur connexion: {e}")
        return False
    
    # 2. Vérification des index créés
    print("\n2️⃣ Vérification des index MeiliSearch...")
    
    company_id = test_payload["company_id"]
    expected_indexes = [
        f"products_{company_id}",
        f"delivery_{company_id}", 
        f"support_paiement_{company_id}",
        f"localisation_{company_id}",
        f"company_docs_{company_id}"
    ]
    
    try:
        # Vérifier via API MeiliSearch
        meili_response = requests.get("http://localhost:7700/indexes")
        if meili_response.status_code == 200:
            indexes = meili_response.json()
            existing_uids = [idx["uid"] for idx in indexes["results"]]
            
            for expected in expected_indexes:
                if expected in existing_uids:
                    print(f"✅ Index trouvé: {expected}")
                else:
                    print(f"❌ Index manquant: {expected}")
        else:
            print(f"❌ Erreur MeiliSearch: {meili_response.status_code}")
            
    except Exception as e:
        print(f"❌ Erreur vérification index: {e}")
    
    # 3. Vérification du contenu des index
    print("\n3️⃣ Vérification du contenu des index...")
    
    test_cases = [
        {
            "index": f"products_{company_id}",
            "search": "casque rouge",
            "expected_fields": ["name", "color", "price", "searchable_text"],
            "expected_values": {"color": "rouge", "price": 6500}
        },
        {
            "index": f"delivery_{company_id}",
            "search": "yopougon",
            "expected_fields": ["zone", "price_min", "searchable_text"],
            "expected_values": {"zone": "Yopougon", "price_min": 1000}
        },
        {
            "index": f"support_paiement_{company_id}",
            "search": "whatsapp",
            "expected_fields": ["method", "phone", "searchable_text"],
            "expected_values": {"method": "whatsapp", "phone": "+2250787360757"}
        }
    ]
    
    for test_case in test_cases:
        try:
            search_url = f"http://localhost:7700/indexes/{test_case['index']}/search"
            search_response = requests.post(
                search_url,
                json={"q": test_case["search"], "limit": 10}
            )
            
            if search_response.status_code == 200:
                results = search_response.json()
                hits = results.get("hits", [])
                
                if hits:
                    hit = hits[0]
                    print(f"✅ {test_case['index']}: {len(hits)} résultat(s) trouvé(s)")
                    
                    # Vérifier les champs attendus
                    for field in test_case["expected_fields"]:
                        if field in hit:
                            print(f"   ✅ Champ '{field}': {hit[field]}")
                        else:
                            print(f"   ❌ Champ manquant: {field}")
                    
                    # Vérifier les valeurs attendues
                    for field, expected_value in test_case["expected_values"].items():
                        actual_value = hit.get(field)
                        if actual_value == expected_value:
                            print(f"   ✅ Valeur '{field}': {actual_value} ✓")
                        else:
                            print(f"   ❌ Valeur '{field}': attendu {expected_value}, trouvé {actual_value}")
                    
                    # Vérifier searchable_text préservé
                    if "searchable_text" in hit and hit["searchable_text"]:
                        print(f"   ✅ searchable_text préservé: {hit['searchable_text'][:50]}...")
                    else:
                        print(f"   ❌ searchable_text manquant ou vide")
                        
                else:
                    print(f"❌ {test_case['index']}: Aucun résultat pour '{test_case['search']}'")
                    
            else:
                print(f"❌ Erreur recherche {test_case['index']}: {search_response.status_code}")
                
        except Exception as e:
            print(f"❌ Erreur test {test_case['index']}: {e}")
    
    print("\n" + "=" * 60)
    print("🏁 Test d'intégrité terminé")
    
    return True

if __name__ == "__main__":
    test_data_integrity()
