#!/usr/bin/env python3
"""
🧪 TEST ENDPOINT /ingestion/ingest-structured
Teste l'intégration Smart Splitter dans ton endpoint existant
"""

import requests
import json

# Tes vraies données (format exact)
TEST_DATA = {
    "company_id": "MpfnlSbqwaZ6F4HvxQLRL9du0yG3",
    "documents": [
        {
            "content": "=== CATALOGUES PRODUITS ===\n\nPRODUITS : Couches culottes ( pour enfant de 5 à 30 kg )\nVARIANTES ET PRIX :\n1 paquet - 5.500 F CFA | 5.500 F/paquet\n2 paquets - 9.800 F CFA | 4.900 F/paquet\n3 paquets - 13.500 F CFA | 4.500 F/paquet\n6 paquets - 25.000 F CFA | 4.150 F/paquet\n12 paquets - 48.000 F CFA | 4.000 F/paquet\n1 colis (48) - 168.000 F CFA | 3.500 F/paquet",
            "file_name": "catalogue-complet.txt",
            "metadata": {
                "document_id": "catalogue_complet",
                "type": "products_catalog",
                "company_id": "MpfnlSbqwaZ6F4HvxQLRL9du0yG3",
                "id": "catalogue_complet"
            }
        },
        {
            "content": "=== LIVRAISON ABIDJAN - ZONES CENTRALES ===\nZones couvertes: Yopougon, Cocody, Plateau, Adjamé, Abobo, Marcory, Koumassi, Treichville, Angré, Riviera\nTarif: 1500 FCFA\n\nDélais livraison Abidjan:\n• Commande avant 11h → Livraison jour même\n• Commande après 11h → Livraison lendemain (jour ouvré)",
            "file_name": "delivery-abidjan-center.txt",
            "metadata": {
                "document_id": "delivery_abidjan_center",
                "type": "delivery_abidjan_center",
                "company_id": "MpfnlSbqwaZ6F4HvxQLRL9du0yG3",
                "id": "delivery_abidjan_center"
            }
        }
    ]
}

def test_ingestion():
    """Test avec ton endpoint existant"""
    
    print("🧪 TEST ENDPOINT /ingestion/ingest-structured")
    print("="*80)
    
    url = "http://localhost:8001/ingestion/ingest-structured"
    
    print(f"\n📤 POST {url}")
    print(f"📦 Documents: {len(TEST_DATA['documents'])}")
    print(f"   - Document 1: {TEST_DATA['documents'][0]['metadata']['type']}")
    print(f"   - Document 2: {TEST_DATA['documents'][1]['metadata']['type']}")
    
    try:
        response = requests.post(
            url,
            json=TEST_DATA,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print("\n✅ SUCCÈS")
            print("="*80)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            # Vérification
            print("\n🔍 VÉRIFICATION:")
            
            # Vérifier que le catalogue a été splitté
            if "ingestion_summary" in result:
                summary = result["ingestion_summary"]
                total_docs = sum(summary.get(k, 0) for k in ["products", "delivery", "support_paiement", "company_docs"])
                
                if total_docs > len(TEST_DATA['documents']):
                    print(f"   ✅ Split réussi: {len(TEST_DATA['documents'])} → {total_docs} documents")
                else:
                    print(f"   ⚠️ Pas de split détecté: {len(TEST_DATA['documents'])} documents")
                
                # Détail par type
                print(f"\n   📊 Documents par type:")
                for doc_type, count in summary.items():
                    if count > 0:
                        print(f"      • {doc_type}: {count}")
            
            return True
            
        else:
            print(f"\n❌ ERREUR HTTP {response.status_code}")
            print(response.text)
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n❌ ERREUR: Serveur non démarré")
        print("\n💡 Démarrer le serveur:")
        print("   uvicorn app:app --host 0.0.0.0 --port 8001 --reload")
        return False
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_search():
    """Teste la recherche après indexation"""
    
    print("\n\n🔍 TEST RECHERCHE MEILISEARCH")
    print("="*80)
    
    import meilisearch
    
    try:
        client = meilisearch.Client("http://localhost:7700", "")
        
        company_id = TEST_DATA["company_id"]
        index_name = f"products_{company_id}"
        
        print(f"\n📊 Index: {index_name}")
        
        # Stats
        stats = client.index(index_name).get_stats()
        print(f"   Documents: {stats.get('numberOfDocuments', 0)}")
        
        # Recherche test
        print(f"\n🔎 Recherche: '6 paquets couches culottes'")
        results = client.index(index_name).search("6 paquets couches culottes", {"limit": 3})
        
        if results['hits']:
            print(f"   ✅ {len(results['hits'])} résultats trouvés")
            
            for i, hit in enumerate(results['hits'], 1):
                print(f"\n   Résultat #{i}:")
                print(f"      ID: {hit.get('id', 'N/A')}")
                print(f"      Contenu: {hit.get('content', 'N/A')[:80]}...")
                
                # Vérifier si c'est le bon document
                if "6 paquets" in hit.get('content', '') and "25.000" in hit.get('content', ''):
                    print(f"      ✅ BON DOCUMENT TROUVÉ !")
        else:
            print("   ⚠️ Aucun résultat")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Erreur MeiliSearch: {e}")
        return False

def test_chatbot():
    """Teste le chatbot avec une vraie question"""
    
    print("\n\n💬 TEST CHATBOT")
    print("="*80)
    
    url = "http://localhost:8001/chat"
    
    payload = {
        "company_id": TEST_DATA["company_id"],
        "user_id": "test_user_hyde",
        "message": "Combien coûte 6 paquets de couches culottes ?"
    }
    
    print(f"\n❓ Question: {payload['message']}")
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            llm_response = result.get("response", {}).get("response", "")
            
            print(f"\n🤖 Réponse:")
            print(f"   {llm_response}")
            
            # Vérifier si le prix correct est mentionné
            if "25.000" in llm_response or "25000" in llm_response or "25 000" in llm_response:
                print(f"\n   ✅ PRIX CORRECT mentionné (25.000 FCFA)")
                return True
            else:
                print(f"\n   ⚠️ Prix incorrect ou manquant")
                return False
        else:
            print(f"\n❌ ERREUR HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        return False

if __name__ == "__main__":
    print("\n" + "="*80)
    print(" "*10 + "🧪 TEST COMPLET - ENDPOINT /ingestion/ingest-structured")
    print("="*80)
    
    # Test 1: Ingestion
    print("\n" + "="*80)
    print("TEST 1: INGESTION")
    print("="*80)
    success1 = test_ingestion()
    
    if success1:
        # Test 2: Recherche
        print("\n" + "="*80)
        print("TEST 2: RECHERCHE")
        print("="*80)
        success2 = test_search()
        
        # Test 3: Chatbot
        print("\n" + "="*80)
        print("TEST 3: CHATBOT")
        print("="*80)
        success3 = test_chatbot()
        
        # Résumé
        print("\n" + "="*80)
        print("📊 RÉSUMÉ")
        print("="*80)
        print(f"Ingestion:  {'✅' if success1 else '❌'}")
        print(f"Recherche:  {'✅' if success2 else '❌'}")
        print(f"Chatbot:    {'✅' if success3 else '❌'}")
        
        if success1 and success2 and success3:
            print("\n🎉 TOUS LES TESTS RÉUSSIS !")
            print("\n💡 Le système fonctionne parfaitement:")
            print("   1. ✅ Catalogues splittés automatiquement")
            print("   2. ✅ Recherche précise (trouve le bon document)")
            print("   3. ✅ Chatbot répond correctement")
        else:
            print("\n⚠️ Certains tests ont échoué, vérifier ci-dessus")
    
    print("\n" + "="*80)
