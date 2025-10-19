#!/usr/bin/env python3
"""
Script de test pour vérifier l'application automatique de la configuration Meilisearch optimisée
lors de l'ingestion de nouvelles données d'entreprise.
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

import requests
import meilisearch

# Configuration
FASTAPI_BASE_URL = "http://localhost:8001"
MEILI_URL = os.environ.get("MEILI_URL", "http://127.0.0.1:7700")
MEILI_KEY = os.environ.get("MEILISEARCH_KEY", "")

# Test company data
TEST_COMPANY_ID = f"test_company_{uuid.uuid4().hex[:8]}"
TEST_DATA = {
    "company_id": TEST_COMPANY_ID,
    "purge_before": True,
    "company_identity": """
    Nom: TechStore Pro
    Secteur: Électronique et Informatique
    Mission: Fournir des solutions technologiques innovantes
    Contact: +225 07 12 34 56 78
    """,
    "products_catalog": """
    Produit: Smartphone Galaxy S24
    Couleur: Noir, Bleu, Argent
    Prix: 450000 FCFA
    Stock: 25 unités
    
    Produit: Laptop Dell XPS 13
    Couleur: Argent
    Prix: 850000 FCFA
    Stock: 10 unités
    """,
    "delivery_info": """
    Zone: Abidjan (Cocody, Yopougon, Plateau)
    Délai: 24-48h
    Frais: 2000 FCFA
    Paiement: Wave, Orange Money, COD
    """,
    "support_info": """
    Support: WhatsApp +225 07 12 34 56 78
    Horaires: 8h-18h du lundi au samedi
    Email: support@techstore.ci
    """
}

async def test_ingestion_and_config():
    """Test l'ingestion et vérifie que la configuration optimisée est appliquée."""
    print(f"🧪 Test de configuration automatique pour company_id: {TEST_COMPANY_ID}")
    
    # 1. Test d'ingestion via l'API
    print("\n📤 1. Ingestion des données de test...")
    try:
        # Convertir les données au format structured pour l'endpoint /ingest-structured
        structured_data = {
            "company_id": TEST_DATA["company_id"],
            "documents": []
        }
        
        # Convertir chaque section en document structuré
        for key, content in TEST_DATA.items():
            if key not in ["company_id", "purge_before"]:
                structured_data["documents"].append({
                    "id": f"{key}_{uuid.uuid4().hex[:8]}",
                    "company_id": TEST_DATA["company_id"],
                    "type": key,
                    "content_fr": content.strip(),
                    "searchable_text": content.strip(),
                    "created_at": datetime.now(timezone.utc).isoformat()
                })
        
        response = requests.post(
            f"{FASTAPI_BASE_URL}/ingestion/ingest-structured",
            json=structured_data,
            timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            indexed_count = result.get('indexed', 0)
            print(f"✅ Ingestion réussie: {indexed_count} documents indexés")
            print(f"📋 Résultat complet: {result}")
            if indexed_count == 0:
                print("⚠️ Aucun document indexé - vérification des données...")
                return False
        else:
            print(f"❌ Erreur ingestion: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erreur connexion API: {e}")
        return False
    
    # 2. Vérification de la configuration Meilisearch
    print("\n🔍 2. Vérification de la configuration Meilisearch...")
    try:
        client = meilisearch.Client(MEILI_URL, MEILI_KEY)
        index_name = f"company_docs_{TEST_COMPANY_ID}"
        
        # Vérifier que l'index existe
        try:
            stats = client.index(index_name).get_stats()
            doc_count = stats.numberOfDocuments if hasattr(stats, 'numberOfDocuments') else stats.get('numberOfDocuments', 0)
            print(f"✅ Index {index_name} créé avec {doc_count} documents")
            if doc_count == 0:
                print("⚠️ Index vide - vérification en cours...")
                return False
        except Exception as e:
            print(f"❌ Index non trouvé: {e}")
            return False
        
        # Vérifier la configuration des attributs
        settings = client.index(index_name).get_settings()
        
        # Vérifier les attributs de recherche optimisés
        searchable = settings.get("searchableAttributes", [])
        expected_searchable = ["searchable_text", "content_fr", "product_name", "color", "tags"]
        
        print(f"📋 Attributs de recherche configurés: {searchable[:5]}...")
        
        config_ok = True
        for attr in expected_searchable:
            if attr not in searchable:
                print(f"❌ Attribut manquant: {attr}")
                config_ok = False
        
        if config_ok:
            print("✅ Configuration des attributs de recherche correcte")
        
        # Vérifier la tolérance aux fautes de frappe
        typo_config = settings.get("typoTolerance", {})
        if typo_config.get("enabled"):
            print("✅ Tolérance aux fautes de frappe activée")
        else:
            print("⚠️ Tolérance aux fautes de frappe non configurée")
        
        return config_ok
        
    except Exception as e:
        print(f"❌ Erreur vérification Meilisearch: {e}")
        return False

async def test_search_functionality():
    """Test la fonctionnalité de recherche avec la nouvelle configuration."""
    print("\n🔍 3. Test de la fonctionnalité de recherche...")
    
    try:
        client = meilisearch.Client(MEILI_URL, MEILI_KEY)
        index_name = f"company_docs_{TEST_COMPANY_ID}"
        index = client.index(index_name)
        
        # Tests de recherche
        test_queries = [
            ("smartphone", "Recherche produit"),
            ("galaxy", "Recherche marque"),
            ("noir", "Recherche couleur"),
            ("cocody", "Recherche zone livraison"),
            ("wave", "Recherche paiement"),
            ("whatsapp", "Recherche support"),
            ("techstore", "Recherche entreprise")
        ]
        
        search_results = {}
        for query, description in test_queries:
            try:
                result = index.search(query, {"limit": 3})
                hits = result.get("hits", [])
                search_results[query] = {
                    "description": description,
                    "hits": len(hits),
                    "time_ms": result.get("processingTimeMs", 0),
                    "success": len(hits) > 0
                }
                status = "✅" if len(hits) > 0 else "❌"
                print(f"{status} {description} '{query}': {len(hits)} résultats en {result.get('processingTimeMs', 0)}ms")
            except Exception as e:
                search_results[query] = {
                    "description": description,
                    "error": str(e),
                    "success": False
                }
                print(f"❌ Erreur recherche '{query}': {e}")
        
        # Calcul du taux de réussite
        successful_searches = sum(1 for r in search_results.values() if r.get("success", False))
        success_rate = (successful_searches / len(test_queries)) * 100
        
        print(f"\n📊 Taux de réussite des recherches: {success_rate:.1f}% ({successful_searches}/{len(test_queries)})")
        
        return search_results, success_rate >= 70  # Seuil de réussite à 70%
        
    except Exception as e:
        print(f"❌ Erreur test de recherche: {e}")
        return {}, False

async def cleanup_test_data():
    """Nettoie les données de test."""
    print(f"\n🧹 4. Nettoyage des données de test...")
    try:
        client = meilisearch.Client(MEILI_URL, MEILI_KEY)
        index_name = f"company_docs_{TEST_COMPANY_ID}"
        
        # Supprimer l'index de test
        client.delete_index(index_name)
        print(f"✅ Index de test {index_name} supprimé")
        
    except Exception as e:
        print(f"⚠️ Erreur nettoyage: {e}")

async def main():
    """Fonction principale de test."""
    print("🚀 Test de Configuration Automatique Meilisearch")
    print("=" * 60)
    
    # Test d'ingestion et configuration
    config_success = await test_ingestion_and_config()
    
    if not config_success:
        print("\n❌ Test échoué: Configuration non appliquée correctement")
        return False
    
    # Attendre un peu pour que l'indexation soit terminée
    print("\n⏳ Attente de l'indexation (5 secondes)...")
    await asyncio.sleep(5)
    
    # Test de recherche
    search_results, search_success = await test_search_functionality()
    
    # Nettoyage
    await cleanup_test_data()
    
    # Résumé final
    print("\n" + "=" * 60)
    print("📋 RÉSUMÉ DU TEST")
    print("=" * 60)
    
    if config_success and search_success:
        print("✅ SUCCÈS: Configuration automatique fonctionnelle")
        print("✅ La configuration optimisée est appliquée automatiquement")
        print("✅ Les recherches fonctionnent avec la nouvelle configuration")
    else:
        print("❌ ÉCHEC: Problèmes détectés")
        if not config_success:
            print("❌ Configuration non appliquée correctement")
        if not search_success:
            print("❌ Recherches non fonctionnelles")
    
    return config_success and search_success

if __name__ == "__main__":
    # Vérifier les variables d'environnement
    if not MEILI_KEY:
        print("❌ ERREUR: Variable MEILISEARCH_KEY non définie")
        sys.exit(1)
    
    # Lancer le test
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
