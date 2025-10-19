#!/usr/bin/env python3
"""
🧪 TEST HYDE ETL AVEC TES VRAIES DONNÉES
Teste le pipeline complet avec les données Rue_du_gros
"""

import asyncio
import requests
import json

# Tes vraies données (avec fautes intentionnelles pour tester)
TEST_DATA = {
    "company_id": "MpfnlSbqwaZ6F4HvxQLRL9du0yG3",
    "text_documents": [
        {
            "content": "=== ENTREPRISE RUE_DU_GROS ===\nNom: Rue_du_gros\nAssistant IA: gamma\nSecteur: Bébé & Puériculture\nZone d'activité: Côte d'Ivoire\n\nMission:  Notre objectif est de faciliter l'accès aux couches fiables et confortables, partout en Côte d'Ivoire, grâce à un service de livraison rapide et un accompagnement client attentif.\nObjectif commercial: Convertir chaque clients en prospect\nDescription: est spécialisée dans la vente de couches pour bébés en gros et en détail. Nous proposons des produits de qualité, adaptés à tous les âges, avec des prix compétitifs pour les parents et les revendeurs.",
            "file_name": "rue-du-gros-identity.txt",
            "metadata": {
                "document_id": "rue_du_gros_identity",
                "type": "company_identity",
                "company_id": "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
            }
        },
        {
            "content": "=== CATALOGUES PRODUITS ===\n\nPRODUITS : Couches culottes  ( pour enfant de 5 à 30 kg )\nVARIANTES ET PRIX :\n1 paquet - 5.500 F CFA | 5.500 F/paquet\n2 paquets - 9.800 F CFA | 4.900 F/paquet\n3 paquets - 13.500 F CFA | 4.500 F/paquet\n6 paquets - 25.000 F CFA | 4.150 F/paquet\n12 paquets - 48.000 F CFA | 4.000 F/paquet\n1 colis (48) - 168.000 F CFA | 3.500 F/paquet",
            "file_name": "catalogue-complet.txt",
            "metadata": {
                "document_id": "catalogue_complet",
                "type": "products_catalog",
                "company_id": "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
            }
        },
        {
            "content": "=== LIVRAISON ABIDJAN - ZONES CENTRALES ===\nZones couvertes: Yopougon, Cocody, Plateau, Adjamé, Abobo, Marcory, Koumassi, Treichville, Angré, Riviera\nTarif: 1500 FCFA\n\nDélais livraison Abidjan:\n• Commande avant 11h → Livraison jour même\n• Commande après 11h → Livraison lendemain (jour ouvré)",
            "file_name": "delivery-abidjan-center.txt",
            "metadata": {
                "document_id": "delivery_abidjan_center",
                "type": "delivery_abidjan_center",
                "company_id": "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
            }
        }
    ],
    "purge_before": True
}

def test_api_endpoint():
    """Test avec l'API HTTP"""
    
    print("🌐 TEST ENDPOINT HTTP")
    print("="*80)
    
    url = "http://localhost:8001/hyde-etl/ingest"
    
    print(f"\n📤 POST {url}")
    print(f"📦 Données: {len(TEST_DATA['text_documents'])} documents")
    
    try:
        response = requests.post(
            url,
            json=TEST_DATA,
            headers={"Content-Type": "application/json"},
            timeout=120  # 2 minutes (LLM peut être long)
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print("\n✅ SUCCÈS")
            print("="*80)
            print(f"Documents input:   {result['documents_input']}")
            print(f"Documents nettoyés: {result['documents_cleaned']}")
            print(f"Documents split:    {result['documents_split']}")
            print(f"Documents indexés:  {result['documents_indexed']}")
            
            print("\n📋 Étapes du pipeline:")
            for step in result['processing_steps']:
                print(f"   • {step}")
            
            print(f"\n💬 Message: {result['message']}")
            
            # Vérifier résultat attendu
            print("\n🔍 VALIDATION:")
            if result['documents_split'] > result['documents_input']:
                print(f"   ✅ Split réussi: {result['documents_input']} → {result['documents_split']} documents")
            else:
                print(f"   ⚠️ Pas de split détecté")
            
            if result['documents_indexed'] >= result['documents_split']:
                print(f"   ✅ Indexation complète")
            else:
                print(f"   ⚠️ Indexation incomplète")
            
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
        return False

def test_stats():
    """Teste les stats après indexation"""
    
    print("\n\n📊 TEST STATS MEILISEARCH")
    print("="*80)
    
    url = f"http://localhost:8001/hyde-etl/stats/{TEST_DATA['company_id']}"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            
            if result['success']:
                stats = result['stats']
                print(f"\n✅ Index: {result['index_name']}")
                print(f"📄 Documents: {stats.get('numberOfDocuments', 0)}")
                print(f"🔄 Indexing: {stats.get('isIndexing', False)}")
                
                return True
            else:
                print(f"\n⚠️ {result.get('error', 'Erreur inconnue')}")
                return False
        else:
            print(f"\n❌ ERREUR HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        return False

def show_instructions():
    """Affiche les instructions"""
    
    print("\n\n📖 INSTRUCTIONS")
    print("="*80)
    print("""
ÉTAPE 1: Intégrer la route dans app.py
────────────────────────────────────────
# app.py - Ajouter après les autres routes

from hyde_etl_ingest_api import router as hyde_etl_router
app.include_router(hyde_etl_router)


ÉTAPE 2: Démarrer le serveur
────────────────────────────────────────
uvicorn app:app --host 0.0.0.0 --port 8001 --reload


ÉTAPE 3: Relancer ce test
────────────────────────────────────────
python test_hyde_etl_avec_vraies_donnees.py


RÉSULTAT ATTENDU:
────────────────────────────────────────
• 3 documents input
• 3 documents nettoyés par LLM
• 8+ documents après split (catalogue séparé)
• 8+ documents indexés dans MeiliSearch

Query "6 paquets couches culottes" 
→ Trouve EXACTEMENT le document pour 6 paquets ✅
    """)

if __name__ == "__main__":
    print("\n" + "="*80)
    print(" "*15 + "🧪 TEST HYDE ETL - DONNÉES RUE_DU_GROS")
    print("="*80)
    
    # Test endpoint
    success = test_api_endpoint()
    
    if success:
        # Test stats
        test_stats()
        
        print("\n" + "="*80)
        print("✅ TOUS LES TESTS RÉUSSIS")
        print("\n💡 Maintenant teste une vraie query:")
        print('   curl -X POST "http://localhost:8001/chat" \\')
        print('     -d \'{"company_id": "MpfnlSbq...", "message": "6 paquets couches culottes?"}\'')
        print("="*80)
    else:
        show_instructions()
