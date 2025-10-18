#!/usr/bin/env python3
"""
RESTAURATION URGENTE des attributs MeiliSearch supprimés
"""

try:
    import meilisearch
except ImportError:
    meilisearch = None
import time

# Configuration MeiliSearch
MEILI_URL = "http://localhost:7700"
MEILI_API_KEY = "Bac2018mado@2066"

client = meilisearch.Client(MEILI_URL, MEILI_API_KEY)

def force_restore_attributes():
    """Force la restauration des attributs pour tous les indexes"""
    
    company_id = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
    
    # Configuration spécifique pour company_docs
    company_docs_config = {
        "searchableAttributes": ["content", "title", "file_name", "id", "text", "description"],
        "filterableAttributes": ["company_id", "file_name", "id", "section", "language"],
        "sortableAttributes": ["id", "file_name"],
        "displayedAttributes": ["id", "content", "title", "file_name"],
        "rankingRules": ["words", "typo", "proximity", "attribute", "exactness"]
    }
    
    # Configuration pour products
    products_config = {
        "searchableAttributes": ["content", "name", "title", "description", "product_name", "category", "text"],
        "filterableAttributes": ["company_id", "category", "type", "id", "brand", "color"],
        "sortableAttributes": ["id", "name", "category"],
        "displayedAttributes": ["id", "content", "name", "title", "description", "category"],
        "rankingRules": ["words", "typo", "proximity", "attribute", "exactness"]
    }
    
    # Configuration pour delivery
    delivery_config = {
        "searchableAttributes": ["content", "zone", "city", "area", "commune", "text"],
        "filterableAttributes": ["company_id", "zone", "city", "id", "area"],
        "sortableAttributes": ["id", "zone", "city"],
        "displayedAttributes": ["id", "content", "zone", "city", "area"],
        "rankingRules": ["words", "typo", "proximity", "attribute", "exactness"]
    }
    
    # Configuration pour support
    support_config = {
        "searchableAttributes": ["content", "title", "question", "answer", "text"],
        "filterableAttributes": ["company_id", "type", "id", "tags"],
        "sortableAttributes": ["id", "title"],
        "displayedAttributes": ["id", "content", "title", "question", "answer"],
        "rankingRules": ["words", "typo", "proximity", "attribute", "exactness"]
    }
    
    # Configuration pour localisation
    localisation_config = {
        "searchableAttributes": ["content", "zone", "address", "city", "text"],
        "filterableAttributes": ["company_id", "zone", "id", "city"],
        "sortableAttributes": ["id", "zone", "city"],
        "displayedAttributes": ["id", "content", "zone", "address", "city"],
        "rankingRules": ["words", "typo", "proximity", "attribute", "exactness"]
    }
    
    # Indexes à réparer
    indexes_config = {
        f"company_docs_{company_id}": company_docs_config,
        f"products_{company_id}": products_config,
        f"delivery_{company_id}": delivery_config,
        f"support_paiement_{company_id}": support_config,
        f"localisation_{company_id}": localisation_config,
        f"COMPANY_DOCS_{company_id}": company_docs_config,
        f"PRODUCTS_{company_id}": products_config,
        f"DELIVERY_{company_id}": delivery_config,
        f"SUPPORT_PAIEMENT_{company_id}": support_config,
        f"LOCALISATION_{company_id}": localisation_config
    }
    
    print("🚨 RESTAURATION URGENTE DES ATTRIBUTS MEILISEARCH")
    print("=" * 60)
    
    for index_name, config in indexes_config.items():
        try:
            print(f"\n🔧 Réparation de: {index_name}")
            
            # Vérifier si l'index existe
            stats = client.index(index_name).get_stats()
            doc_count = stats.get('numberOfDocuments', 0)
            print(f"  📊 Documents: {doc_count}")
            
            if doc_count > 0:
                index = client.index(index_name)
                
                # Appliquer la configuration complète
                print(f"  🔄 Application des attributs...")
                index.update_settings(config)
                
                # Attendre que les settings soient appliqués
                time.sleep(1)
                
                # Vérifier les nouveaux attributs
                new_settings = index.get_settings()
                print(f"  ✅ Searchable: {len(new_settings.get('searchableAttributes', []))} attributs")
                print(f"  ✅ Filterable: {len(new_settings.get('filterableAttributes', []))} attributs")
                print(f"  ✅ Sortable: {len(new_settings.get('sortableAttributes', []))} attributs")
                
            else:
                print(f"  ⚠️ Index vide, ignoré")
                
        except Exception as e:
            print(f"  ❌ Erreur: {e}")
    
    print("\n🎉 RESTAURATION TERMINÉE!")
    print("Testez maintenant votre recherche MeiliSearch")

if __name__ == "__main__":
    force_restore_attributes()


