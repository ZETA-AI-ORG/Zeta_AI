#!/usr/bin/env python3
"""
Script de diagnostic et correction complète des attributs Meilisearch
Répare les attributs searchable, filterable, sortable pour tous les index
"""

import os
import meilisearch
import time
import json

# Configuration
MEILI_URL = os.environ.get("MEILI_URL", "http://127.0.0.1:7700")
MEILI_KEY = os.environ.get("MEILI_API_KEY") or os.environ.get("MEILI_MASTER_KEY", "")

# Configuration optimisée pour chaque type d'index
INDEX_CONFIGURATIONS = {
    "products": {
        "searchableAttributes": [
            "name", "product_name", "description", "content", "title", 
            "category", "subcategory", "color", "brand", "text", "searchable_text"
        ],
        "filterableAttributes": [
            "company_id", "category", "subcategory", "color", "brand", 
            "price", "min_price", "max_price", "currency", "stock", "type", "id"
        ],
        "sortableAttributes": [
            "price", "min_price", "max_price", "stock", "name", "category", "updated_at"
        ],
        "displayedAttributes": [
            "id", "name", "product_name", "description", "category", "subcategory", 
            "color", "brand", "price", "min_price", "max_price", "currency", "stock"
        ],
        "rankingRules": ["words", "typo", "proximity", "attribute", "sort", "exactness"],
        "stopWords": ["le", "la", "les", "de", "du", "des", "un", "une", "et", "à", "au", "aux"],
        "synonyms": {
            "couche": ["couches", "pampers"],
            "culotte": ["culottes"],
            "bebe": ["bébé", "enfant", "nourrisson"],
            "kg": ["kilo", "kilogramme"],
            "fcfa": ["f cfa", "franc cfa", "cfa"]
        }
    },
    "delivery": {
        "searchableAttributes": [
            "zone", "city", "area", "commune", "address", "content", 
            "text", "delivery_zone", "location_type"
        ],
        "filterableAttributes": [
            "company_id", "zone", "city", "area", "commune", "type", "id"
        ],
        "sortableAttributes": [
            "zone", "city", "price", "delay", "updated_at"
        ],
        "displayedAttributes": [
            "id", "zone", "city", "area", "commune", "address", "price", "delay"
        ],
        "rankingRules": ["words", "typo", "proximity", "attribute", "sort", "exactness"]
    },
    "support_paiement": {
        "searchableAttributes": [
            "type", "method", "payment_method", "payment_type", "phone", 
            "hours", "details", "store_type", "content", "text"
        ],
        "filterableAttributes": [
            "company_id", "type", "method", "payment_method", "payment_type", 
            "store_type", "id"
        ],
        "sortableAttributes": [
            "type", "method", "updated_at"
        ],
        "displayedAttributes": [
            "id", "type", "method", "payment_method", "phone", "hours", "details"
        ],
        "rankingRules": ["words", "typo", "proximity", "attribute", "sort", "exactness"]
    },
    "localisation": {
        "searchableAttributes": [
            "zone", "address", "city", "store_type", "delivery_zone", 
            "location_type", "content", "text"
        ],
        "filterableAttributes": [
            "company_id", "zone", "city", "store_type", "location_type", "id"
        ],
        "sortableAttributes": [
            "zone", "city", "store_type", "updated_at"
        ],
        "displayedAttributes": [
            "id", "zone", "address", "city", "store_type", "location_type"
        ],
        "rankingRules": ["words", "typo", "proximity", "attribute", "sort", "exactness"]
    },
    "company_docs": {
        "searchableAttributes": [
            "title", "content", "searchable_text", "category", "text", 
            "description", "file_name", "section"
        ],
        "filterableAttributes": [
            "company_id", "category", "type", "section", "language", 
            "file_name", "id"
        ],
        "sortableAttributes": [
            "title", "category", "section", "created_at", "updated_at"
        ],
        "displayedAttributes": [
            "id", "title", "content", "category", "section", "file_name"
        ],
        "rankingRules": ["words", "typo", "proximity", "attribute", "sort", "exactness"]
    }
}

def get_client():
    """Initialise le client Meilisearch"""
    try:
        client = meilisearch.Client(MEILI_URL, MEILI_KEY)
        # Test de connexion
        client.get_version()
        return client
    except Exception as e:
        print(f"❌ Erreur de connexion à Meilisearch: {e}")
        return None

def get_company_indexes(client):
    """Récupère tous les index d'entreprise"""
    try:
        indexes_result = client.get_indexes()
        company_indexes = []
        
        # Gérer différents formats de réponse de l'API Meilisearch
        if hasattr(indexes_result, 'results'):
            indexes_list = indexes_result.results
        elif isinstance(indexes_result, dict) and 'results' in indexes_result:
            indexes_list = indexes_result['results']
        elif isinstance(indexes_result, list):
            indexes_list = indexes_result
        else:
            print(f"⚠️ Format de réponse inattendu: {type(indexes_result)}")
            return []
        
        for index in indexes_list:
            # Gérer différents formats d'index
            if hasattr(index, 'uid'):
                uid = index.uid
                docs = getattr(index, 'numberOfDocuments', 0)
            elif isinstance(index, dict):
                uid = index.get("uid", "")
                docs = index.get("numberOfDocuments", 0)
            else:
                print(f"⚠️ Format d'index inattendu: {type(index)}")
                continue
            
            # Vérifier si c'est un index d'entreprise valide
            for index_type in INDEX_CONFIGURATIONS.keys():
                if uid.startswith(f"{index_type}_") and len(uid.split("_")) == 2:
                    company_indexes.append({
                        "uid": uid,
                        "type": index_type,
                        "company_id": uid.split("_", 1)[1],
                        "docs": docs
                    })
                    break
        
        return company_indexes
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des index: {e}")
        print(f"❌ Type d'erreur: {type(e).__name__}")
        import traceback
        print(f"❌ Détails: {traceback.format_exc()}")
        return []

def diagnose_index_settings(client, index_uid):
    """Diagnostique les paramètres d'un index"""
    try:
        index = client.index(index_uid)
        settings = index.get_settings()
        stats = index.get_stats()
        
        return {
            "uid": index_uid,
            "documents": stats.get("numberOfDocuments", 0),
            "searchableAttributes": settings.get("searchableAttributes", []),
            "filterableAttributes": settings.get("filterableAttributes", []),
            "sortableAttributes": settings.get("sortableAttributes", []),
            "displayedAttributes": settings.get("displayedAttributes", []),
            "rankingRules": settings.get("rankingRules", []),
            "synonyms": settings.get("synonyms", {}),
            "stopWords": settings.get("stopWords", [])
        }
    except Exception as e:
        print(f"❌ Erreur lors du diagnostic de {index_uid}: {e}")
        return None

def apply_index_configuration(client, index_uid, index_type):
    """Applique la configuration optimisée à un index"""
    try:
        if index_type not in INDEX_CONFIGURATIONS:
            print(f"⚠️ Type d'index non reconnu: {index_type}")
            return False
        
        config = INDEX_CONFIGURATIONS[index_type]
        index = client.index(index_uid)
        
        print(f"🔧 Application de la configuration pour {index_uid}...")
        
        # Appliquer la configuration
        task = index.update_settings(config)
        print(f"  ✅ Configuration appliquée (task: {task.get('taskUid', 'N/A')})")
        
        # Attendre que la tâche soit terminée
        time.sleep(2)
        
        # Vérifier que la configuration a été appliquée
        new_settings = index.get_settings()
        searchable_count = len(new_settings.get("searchableAttributes", []))
        filterable_count = len(new_settings.get("filterableAttributes", []))
        
        print(f"  📊 Attributs configurés: {searchable_count} searchable, {filterable_count} filterable")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la configuration de {index_uid}: {e}")
        return False

def test_search(client, index_uid, test_query="couches"):
    """Teste la recherche sur un index"""
    try:
        index = client.index(index_uid)
        result = index.search(test_query, {"limit": 3})
        
        hits = result.get("hits", [])
        total = result.get("estimatedTotalHits", 0)
        
        print(f"  🔍 Test de recherche '{test_query}': {len(hits)} résultats sur {total} total")
        
        if hits:
            for i, hit in enumerate(hits[:2], 1):
                title = hit.get("name") or hit.get("title") or hit.get("content", "")[:50] + "..."
                print(f"    {i}. {title}")
        
        return len(hits) > 0
        
    except Exception as e:
        print(f"❌ Erreur lors du test de recherche sur {index_uid}: {e}")
        return False

def main():
    """Fonction principale"""
    print("🔧 DIAGNOSTIC ET CORRECTION DES ATTRIBUTS MEILISEARCH")
    print("=" * 60)
    print(f"URL: {MEILI_URL}")
    print()
    
    # 1. Connexion
    client = get_client()
    if not client:
        return
    
    # 2. Récupération des index
    print("📋 Récupération des index d'entreprise...")
    indexes = get_company_indexes(client)
    
    if not indexes:
        print("❌ Aucun index d'entreprise trouvé")
        return
    
    print(f"✅ {len(indexes)} index trouvés")
    print()
    
    # 3. Diagnostic et correction
    for index_info in indexes:
        uid = index_info["uid"]
        index_type = index_info["type"]
        docs = index_info["docs"]
        
        print(f"🔍 DIAGNOSTIC: {uid}")
        print(f"  📊 Documents: {docs}")
        
        # Diagnostic des paramètres actuels
        current_settings = diagnose_index_settings(client, uid)
        if current_settings:
            searchable = len(current_settings["searchableAttributes"])
            filterable = len(current_settings["filterableAttributes"])
            sortable = len(current_settings["sortableAttributes"])
            
            print(f"  📋 Attributs actuels: {searchable} searchable, {filterable} filterable, {sortable} sortable")
            
            # Vérifier si la configuration est correcte
            expected_config = INDEX_CONFIGURATIONS[index_type]
            needs_update = (
                searchable < len(expected_config["searchableAttributes"]) or
                filterable < len(expected_config["filterableAttributes"])
            )
            
            if needs_update:
                print(f"  ⚠️ Configuration incomplète, correction nécessaire")
                
                # Appliquer la correction
                if apply_index_configuration(client, uid, index_type):
                    print(f"  ✅ Configuration corrigée")
                    
                    # Test de recherche
                    if docs > 0:
                        test_search(client, uid)
                else:
                    print(f"  ❌ Échec de la correction")
            else:
                print(f"  ✅ Configuration correcte")
                
                # Test de recherche même si la config est correcte
                if docs > 0:
                    test_search(client, uid)
        
        print()
    
    print("🎉 DIAGNOSTIC ET CORRECTION TERMINÉS")
    print()
    print("📋 RÉSUMÉ:")
    for index_info in indexes:
        uid = index_info["uid"]
        docs = index_info["docs"]
        print(f"  {uid}: {docs} documents")

if __name__ == "__main__":
    main()
