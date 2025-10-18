#!/usr/bin/env python3
"""
Script simplifié pour corriger les attributs Meilisearch
Version directe avec les index connus
"""

import os
import meilisearch
import time

# Configuration
MEILI_URL = os.environ.get("MEILI_URL", "http://127.0.0.1:7700")
MEILI_KEY = os.environ.get("MEILI_API_KEY") or os.environ.get("MEILI_MASTER_KEY", "")

# Index à corriger (basés sur l'image)
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
INDEXES_TO_FIX = [
    f"products_{COMPANY_ID}",
    f"delivery_{COMPANY_ID}",
    f"support_paiement_{COMPANY_ID}",
    f"localisation_{COMPANY_ID}",
    f"company_docs_{COMPANY_ID}"
]

# Configuration pour products (le plus important)
PRODUCTS_CONFIG = {
    "searchableAttributes": [
        "name", "product_name", "description", "content", "title", 
        "category", "subcategory", "color", "brand", "text", "searchable_text",
        "variantes", "prix", "taille"
    ],
    "filterableAttributes": [
        "company_id", "category", "subcategory", "color", "brand", 
        "price", "min_price", "max_price", "currency", "stock", "type", "id"
    ],
    "sortableAttributes": [
        "price", "min_price", "max_price", "stock", "name", "category"
    ],
    "rankingRules": ["words", "typo", "proximity", "attribute", "sort", "exactness"],
    "synonyms": {
        "couche": ["couches", "pampers", "pamper"],
        "culotte": ["culottes"],
        "bebe": ["bébé", "enfant", "nourrisson", "baby"],
        "kg": ["kilo", "kilogramme", "kilos"],
        "fcfa": ["f cfa", "franc cfa", "cfa", "francs"]
    },
    "stopWords": ["le", "la", "les", "de", "du", "des", "un", "une", "et", "à", "au", "aux"]
}

# Configuration générale pour les autres index
GENERAL_CONFIG = {
    "searchableAttributes": ["*"],
    "filterableAttributes": ["company_id", "type", "id"],
    "sortableAttributes": ["id"],
    "rankingRules": ["words", "typo", "proximity", "attribute", "sort", "exactness"]
}

def fix_index(client, index_uid, config):
    """Corrige un index spécifique"""
    try:
        print(f"🔧 Correction de {index_uid}...")
        
        # Vérifier que l'index existe
        index = client.index(index_uid)
        stats = index.get_stats()
        docs = stats.numberOfDocuments if hasattr(stats, 'numberOfDocuments') else 0
        
        print(f"  📊 Documents: {docs}")
        
        # Appliquer la configuration
        task = index.update_settings(config)
        print(f"  ✅ Configuration appliquée")
        
        # Attendre un peu
        time.sleep(1)
        
        # Vérifier la nouvelle configuration
        new_settings = index.get_settings()
        searchable = new_settings.searchableAttributes if hasattr(new_settings, 'searchableAttributes') else []
        filterable = new_settings.filterableAttributes if hasattr(new_settings, 'filterableAttributes') else []
        
        print(f"  📋 Nouveaux attributs: {len(searchable)} searchable, {len(filterable)} filterable")
        
        # Test de recherche si l'index a des documents
        if docs > 0:
            try:
                result = index.search("couches", {"limit": 2})
                hits = result.hits if hasattr(result, 'hits') else []
                print(f"  🔍 Test recherche 'couches': {len(hits)} résultats")
                
                if hits:
                    for hit in hits[:1]:
                        name = getattr(hit, 'name', None) or getattr(hit, 'title', None) or str(hit)[:50]
                        print(f"    - {name}")
            except Exception as e:
                print(f"  ⚠️ Test de recherche échoué: {e}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False

def main():
    """Fonction principale"""
    print("🔧 CORRECTION SIMPLIFIÉE DES ATTRIBUTS MEILISEARCH")
    print("=" * 60)
    print(f"URL: {MEILI_URL}")
    print(f"Company ID: {COMPANY_ID}")
    print()
    
    # Connexion
    try:
        client = meilisearch.Client(MEILI_URL, MEILI_KEY)
        version = client.get_version()
        print(f"✅ Connecté à Meilisearch v{version.pkgVersion if hasattr(version, 'pkgVersion') else 'unknown'}")
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        return
    
    print()
    
    # Correction des index
    success_count = 0
    
    for index_uid in INDEXES_TO_FIX:
        if "products_" in index_uid:
            # Configuration spéciale pour products
            if fix_index(client, index_uid, PRODUCTS_CONFIG):
                success_count += 1
        else:
            # Configuration générale pour les autres
            if fix_index(client, index_uid, GENERAL_CONFIG):
                success_count += 1
        print()
    
    print(f"🎉 CORRECTION TERMINÉE: {success_count}/{len(INDEXES_TO_FIX)} index corrigés")
    print()
    print("📋 PROCHAINES ÉTAPES:")
    print("1. Testez une recherche de couches dans votre application")
    print("2. Vérifiez que Meilisearch retourne des résultats")
    print("3. Si ça ne fonctionne toujours pas, vérifiez le contenu des documents")

if __name__ == "__main__":
    main()
