#!/usr/bin/env python3
"""
Script de diagnostic pour analyser les index MeiliSearch et leurs données
"""
import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.vector_store_clean import get_meilisearch_client, get_available_indexes

def debug_meili_indexes(company_id: str):
    """Analyse complète des index MeiliSearch pour une entreprise"""
    
    print(f"🔍 === DIAGNOSTIC MEILISEARCH POUR {company_id} ===\n")
    
    # 1. Connexion client
    client = get_meilisearch_client()
    if not client:
        print("❌ Impossible de se connecter à MeiliSearch")
        return
    
    print("✅ Connexion MeiliSearch OK\n")
    
    # 2. Lister tous les index disponibles
    print("📋 INDEX DISPONIBLES:")
    print("=" * 50)
    
    try:
        all_indexes = client.get_indexes()
        
        # Debugging: voir ce qu'on reçoit vraiment
        print(f"🔍 Type retourné: {type(all_indexes)}")
        print(f"🔍 Attributs: {dir(all_indexes)}")
        
        # Extraire la vraie liste d'index
        if hasattr(all_indexes, 'results') and isinstance(all_indexes.results, list):
            indexes_list = all_indexes.results
        elif isinstance(all_indexes, list):
            indexes_list = all_indexes
        else:
            # Utiliser l'API HTTP directe
            import requests
            response = requests.get("http://localhost:7700/indexes", 
                                  headers={"Authorization": "Bearer Bac2018mado@2066"})
            if response.status_code == 200:
                data = response.json()
                indexes_list = data.get('results', [])
            else:
                print(f"❌ Erreur API HTTP: {response.status_code}")
                return
            
        print(f"🔍 Nombre d'index trouvés: {len(indexes_list)}")
        
        company_indexes = []
        for idx in indexes_list:
            # Extraire l'UID selon le format
            if isinstance(idx, dict):
                idx_uid = idx.get('uid', '')
            else:
                idx_uid = getattr(idx, 'uid', str(idx))
            
            print(f"🔍 Index trouvé: {idx_uid}")
            
            # Filtrer par company_id et ignorer les MAJUSCULES
            if company_id in idx_uid and not idx_uid.split('_')[0].isupper():
                company_indexes.append(idx_uid)
                print(f"✅ {idx_uid} (sélectionné)")
        
        if not company_indexes:
            print(f"❌ Aucun index trouvé pour {company_id}")
            return
            
    except Exception as e:
        print(f"❌ Erreur listage index: {e}")
        return
    
    print(f"\n📊 Total: {len(company_indexes)} index trouvés\n")
    
    # 3. Analyser chaque index
    for idx_name in company_indexes:
        print(f"🔍 ANALYSE INDEX: {idx_name}")
        print("=" * 60)
        
        try:
            index = client.index(idx_name)
            
            # Stats de l'index
            stats = index.get_stats()
            print(f"📊 Nombre de documents: {stats.get('numberOfDocuments', 'N/A')}")
            print(f"📊 Taille index: {stats.get('indexSize', 'N/A')} bytes")
            print(f"📊 En cours d'indexation: {stats.get('isIndexing', 'N/A')}")
            
            # Settings de l'index
            settings = index.get_settings()
            print(f"🔧 Attributs searchable: {settings.get('searchableAttributes', [])}")
            print(f"🔧 Attributs filterable: {settings.get('filterableAttributes', [])}")
            
            # Échantillon de documents
            docs = index.get_documents({'limit': 3})
            if hasattr(docs, 'results'):
                docs_list = docs.results
            else:
                docs_list = docs
            
            print(f"📄 Échantillon documents ({len(docs_list)}):")
            for i, doc in enumerate(docs_list, 1):
                # Convertir l'objet Document
                if hasattr(doc, '__dict__'):
                    doc_dict = doc.__dict__
                else:
                    doc_dict = {
                        'id': getattr(doc, 'id', None),
                        'content': getattr(doc, 'content', '')[:100] + '...',
                        'company_id': getattr(doc, 'company_id', None),
                        'type': getattr(doc, 'type', None)
                    }
                
                print(f"  Doc {i}:")
                print(f"    ID: {doc_dict.get('id', 'N/A')}")
                print(f"    Company ID: {doc_dict.get('company_id', 'N/A')}")
                print(f"    Type: {doc_dict.get('type', 'N/A')}")
                print(f"    Contenu: {str(doc_dict.get('content', ''))[:80]}...")
                print(f"    Attributs: {list(doc_dict.keys())}")
                print()
                
        except Exception as e:
            print(f"❌ Erreur analyse {idx_name}: {e}")
        
        print("\n" + "-" * 60 + "\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_meili_indexes.py <company_id>")
        sys.exit(1)
    
    company_id = sys.argv[1]
    debug_meili_indexes(company_id)
