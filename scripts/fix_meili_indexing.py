#!/usr/bin/env python3
"""
Script pour corriger l'indexation MeiliSearch
Problème identifié: Les produits se retrouvent dans company_docs au lieu de products
"""

import os
import sys
from pathlib import Path
import asyncio

sys.path.append(str(Path(__file__).parent.parent))

from database.meili_client import MeiliHelper
from utils import log3

async def fix_product_indexing():
    """Corriger l'indexation des produits dans MeiliSearch"""
    
    company_id = "XkCn8fjNWEWwqiiKMgJX7OcQrUJ3"  # RUEDUGROSSISTE
    
    print("🔧 CORRECTION DE L'INDEXATION MEILISEARCH")
    print("=" * 60)
    
    # Initialiser le client MeiliSearch avec les bonnes variables d'environnement
    import os
    os.environ['MEILI_URL'] = os.environ.get('MEILI_URL', 'http://localhost:7700')
    os.environ['MEILI_API_KEY'] = os.environ.get('MEILI_MASTER_KEY', 'Bac2018mado@2066')
    
    meili_helper = MeiliHelper()
    
    # 1. Vérifier l'état actuel des index
    indexes_to_check = [
        f"products_{company_id}",
        f"company_docs_{company_id}",
        f"delivery_{company_id}",
        f"support_{company_id}"
    ]
    
    for index_name in indexes_to_check:
        try:
            stats = meili_helper.client.index(index_name).get_stats()
            doc_count = stats.get('numberOfDocuments', 0)
            print(f"📊 {index_name}: {doc_count} documents")
            
            # Échantillon de documents pour diagnostic
            if doc_count > 0:
                sample = meili_helper.client.index(index_name).get_documents(limit=2)
                for doc in sample.get('results', []):
                    print(f"   - {doc.get('title', doc.get('name', 'Sans titre'))[:50]}...")
                    
        except Exception as e:
            print(f"❌ Erreur sur {index_name}: {e}")
    
    # 2. Configurer les attributs de recherche pour products
    products_index = f"products_{company_id}"
    try:
        print(f"\n🔧 Configuration de l'index {products_index}")
        
        # Attributs de recherche optimisés pour les produits
        search_attributes = [
            "name",
            "title", 
            "description",
            "brand",
            "category",
            "color",
            "sku",
            "searchable_text"
        ]
        
        # Attributs filtrables
        filterable_attributes = [
            "brand",
            "category", 
            "color",
            "price_range",
            "availability",
            "company_id"
        ]
        
        # Attributs triables
        sortable_attributes = [
            "price",
            "created_at",
            "popularity"
        ]
        
        # Appliquer la configuration
        meili_helper.client.index(products_index).update_searchable_attributes(search_attributes)
        meili_helper.client.index(products_index).update_filterable_attributes(filterable_attributes)
        meili_helper.client.index(products_index).update_sortable_attributes(sortable_attributes)
        
        # Synonymes pour améliorer la recherche
        synonyms = {
            "casque": ["helmet", "casque moto"],
            "rouge": ["red", "rougeâtre"],
            "prix": ["coût", "tarif", "montant"],
            "livraison": ["transport", "expédition"],
            "disponible": ["stock", "dispo"]
        }
        
        meili_helper.client.index(products_index).update_synonyms(synonyms)
        
        print("✅ Configuration appliquée avec succès")
        
    except Exception as e:
        print(f"❌ Erreur configuration: {e}")
    
    # 3. Test de recherche après configuration
    print(f"\n🔍 Test de recherche sur {products_index}")
    test_queries = ["casque rouge", "prix casque", "moto rouge"]
    
    for query in test_queries:
        try:
            results = meili_helper.client.index(products_index).search(query, {"limit": 3})
            hits = results.get('hits', [])
            print(f"   '{query}': {len(hits)} résultats")
            
        except Exception as e:
            print(f"   '{query}': Erreur - {e}")

def optimize_meili_settings():
    """Optimiser les paramètres MeiliSearch pour réduire la latence"""
    
    print("\n⚡ OPTIMISATION DES PARAMÈTRES MEILISEARCH")
    print("=" * 60)
    
    company_id = "XkCn8fjNWEWwqiiKMgJX7OcQrUJ3"
    
    # Assurer la configuration des variables d'environnement
    import os
    os.environ['MEILI_URL'] = os.environ.get('MEILI_URL', 'http://localhost:7700')
    os.environ['MEILI_API_KEY'] = os.environ.get('MEILI_MASTER_KEY', 'Bac2018mado@2066')
    
    meili_helper = MeiliHelper()
    
    # Paramètres d'optimisation
    optimization_settings = {
        # Réduire le nombre de typos autorisées pour accélérer
        "typoTolerance": {
            "enabled": True,
            "minWordSizeForTypos": {
                "oneTypo": 4,
                "twoTypos": 8
            }
        },
        
        # Optimiser la pagination
        "pagination": {
            "maxTotalHits": 1000
        },
        
        # Réduire les facettes pour accélérer
        "faceting": {
            "maxValuesPerFacet": 100
        }
    }
    
    indexes = [f"products_{company_id}", f"support_{company_id}", f"delivery_{company_id}"]
    
    for index_name in indexes:
        try:
            print(f"🔧 Optimisation de {index_name}")
            
            # Appliquer les paramètres d'optimisation
            meili_helper.client.index(index_name).update_typo_tolerance(optimization_settings["typoTolerance"])
            meili_helper.client.index(index_name).update_pagination(optimization_settings["pagination"])
            meili_helper.client.index(index_name).update_faceting(optimization_settings["faceting"])
            
            print(f"✅ {index_name} optimisé")
            
        except Exception as e:
            print(f"❌ Erreur sur {index_name}: {e}")

if __name__ == "__main__":
    asyncio.run(fix_product_indexing())
    optimize_meili_settings()
    
    print("\n🎉 CORRECTION DE L'INDEXATION TERMINÉE")
    print("Redémarrez l'application et testez les requêtes problématiques.")
