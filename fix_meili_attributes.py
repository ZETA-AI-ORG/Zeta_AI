#!/usr/bin/env python3
"""
URGENT: Restaurer les attributs MeiliSearch supprimés
"""

import meilisearch
import os

# Configuration MeiliSearch
MEILI_URL = "http://localhost:7700"
MEILI_API_KEY = "Bac2018mado@2066"

client = meilisearch.Client(MEILI_URL, MEILI_API_KEY)

def fix_index_attributes(index_name: str):
    """Restaurer les attributs de recherche pour un index"""
    print(f"🔧 Réparation de l'index: {index_name}")
    
    try:
        index = client.index(index_name)
        
        # Vérifier l'état actuel
        settings = index.get_settings()
        print(f"  📊 Attributs actuels:")
        print(f"    - Searchable: {settings.get('searchableAttributes', [])}")
        print(f"    - Filterable: {settings.get('filterableAttributes', [])}")
        print(f"    - Sortable: {settings.get('sortableAttributes', [])}")
        
        # Configuration selon le type d'index
        if index_name.startswith("company_docs_"):
            # Index documents d'entreprise
            searchable_attrs = ["content", "title", "file_name", "id"]
            filterable_attrs = ["company_id", "file_name", "id"]
            sortable_attrs = ["id"]
            displayed_attrs = ["id", "content", "title", "file_name"]
            
        elif index_name.startswith("products_"):
            # Index produits
            searchable_attrs = ["content", "name", "title", "description", "product_name", "category"]
            filterable_attrs = ["company_id", "category", "type", "id"]
            sortable_attrs = ["id", "name"]
            displayed_attrs = ["id", "content", "name", "title", "description"]
            
        elif index_name.startswith("delivery_"):
            # Index livraison
            searchable_attrs = ["content", "zone", "city", "area", "commune"]
            filterable_attrs = ["company_id", "zone", "city", "id"]
            sortable_attrs = ["id", "zone"]
            displayed_attrs = ["id", "content", "zone", "city"]
            
        elif index_name.startswith("support_"):
            # Index support
            searchable_attrs = ["content", "title", "question", "answer"]
            filterable_attrs = ["company_id", "type", "id"]
            sortable_attrs = ["id"]
            displayed_attrs = ["id", "content", "title"]
            
        elif index_name.startswith("localisation_"):
            # Index localisation
            searchable_attrs = ["content", "zone", "address", "city"]
            filterable_attrs = ["company_id", "zone", "id"]
            sortable_attrs = ["id", "zone"]
            displayed_attrs = ["id", "content", "zone", "address"]
            
        else:
            # Configuration par défaut
            searchable_attrs = ["content", "title", "name", "description"]
            filterable_attrs = ["company_id", "id"]
            sortable_attrs = ["id"]
            displayed_attrs = ["id", "content", "title"]
        
        # Appliquer les nouveaux attributs
        print(f"  🔄 Application des nouveaux attributs...")
        
        # Searchable attributes
        index.update_searchable_attributes(searchable_attrs)
        print(f"    ✅ Searchable: {searchable_attrs}")
        
        # Filterable attributes  
        index.update_filterable_attributes(filterable_attrs)
        print(f"    ✅ Filterable: {filterable_attrs}")
        
        # Sortable attributes
        index.update_sortable_attributes(sortable_attrs)
        print(f"    ✅ Sortable: {sortable_attrs}")
        
        # Displayed attributes
        index.update_displayed_attributes(displayed_attrs)
        print(f"    ✅ Displayed: {displayed_attrs}")
        
        # Ranking rules
        ranking_rules = ["words", "typo", "proximity", "attribute", "exactness"]
        index.update_ranking_rules(ranking_rules)
        print(f"    ✅ Ranking: {ranking_rules}")
        
        print(f"  ✅ Index {index_name} réparé avec succès!")
        
    except Exception as e:
        print(f"  ❌ Erreur sur {index_name}: {e}")

def main():
    print("🚨 RÉPARATION URGENTE DES ATTRIBUTS MEILISEARCH")
    print("=" * 60)
    
    # Liste des indexes à réparer
    company_id = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
    indexes_to_fix = [
        f"company_docs_{company_id}",
        f"products_{company_id}",
        f"delivery_{company_id}",
        f"support_paiement_{company_id}",
        f"localisation_{company_id}",
        f"COMPANY_DOCS_{company_id}",
        f"PRODUCTS_{company_id}",
        f"DELIVERY_{company_id}",
        f"SUPPORT_PAIEMENT_{company_id}",
        f"LOCALISATION_{company_id}"
    ]
    
    for index_name in indexes_to_fix:
        try:
            # Vérifier si l'index existe
            stats = client.index(index_name).get_stats()
            doc_count = stats.get('numberOfDocuments', 0)
            print(f"\n📊 Index {index_name}: {doc_count} documents")
            
            if doc_count > 0:
                fix_index_attributes(index_name)
            else:
                print(f"  ⚠️ Index vide, ignoré")
                
        except Exception as e:
            print(f"  ❌ Index {index_name} n'existe pas ou erreur: {e}")
    
    print("\n🎉 RÉPARATION TERMINÉE!")
    print("Testez maintenant votre recherche MeiliSearch")

if __name__ == "__main__":
    main()






