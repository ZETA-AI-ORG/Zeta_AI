#!/usr/bin/env python3
"""
Script de diagnostic approfondi des attributs Meilisearch
Vérifie la configuration réelle et teste les recherches
"""

import os
import meilisearch
import json

# Configuration
MEILI_URL = os.environ.get("MEILI_URL", "http://127.0.0.1:7700")
MEILI_KEY = os.environ.get("MEILI_API_KEY") or os.environ.get("MEILI_MASTER_KEY", "")
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"

def debug_index_complete(client, index_uid):
    """Diagnostic complet d'un index"""
    print(f"\n🔍 DIAGNOSTIC COMPLET: {index_uid}")
    print("=" * 60)
    
    try:
        index = client.index(index_uid)
        
        # 1. Statistiques
        stats = index.get_stats()
        docs_count = getattr(stats, 'numberOfDocuments', 0)
        print(f"📊 Documents: {docs_count}")
        
        if docs_count == 0:
            print("⚠️ INDEX VIDE - Aucun document à analyser")
            return
        
        # 2. Configuration actuelle
        settings = index.get_settings()
        searchable = getattr(settings, 'searchableAttributes', [])
        filterable = getattr(settings, 'filterableAttributes', [])
        sortable = getattr(settings, 'sortableAttributes', [])
        
        print(f"📋 Attributs searchable: {len(searchable)}")
        print(f"   {searchable}")
        print(f"📋 Attributs filterable: {len(filterable)}")
        print(f"   {filterable}")
        print(f"📋 Attributs sortable: {len(sortable)}")
        print(f"   {sortable}")
        
        # 3. Échantillon de documents
        print(f"\n📄 ÉCHANTILLON DE DOCUMENTS:")
        docs = index.get_documents({"limit": 2})
        docs_list = getattr(docs, 'results', [])
        
        for i, doc in enumerate(docs_list, 1):
            print(f"\n  📄 Document {i}:")
            if hasattr(doc, '__dict__'):
                for key, value in doc.__dict__.items():
                    if isinstance(value, str) and len(value) > 100:
                        value = value[:100] + "..."
                    print(f"    {key}: {value}")
            else:
                print(f"    {doc}")
        
        # 4. Tests de recherche avec différents termes
        print(f"\n🔍 TESTS DE RECHERCHE:")
        test_queries = ["couches", "pression", "culottes", "enfant", "13kg", "bebe", "taille"]
        
        for query in test_queries:
            try:
                result = index.search(query, {"limit": 3})
                hits = getattr(result, 'hits', [])
                total = getattr(result, 'estimatedTotalHits', 0)
                print(f"  '{query}': {len(hits)} résultats sur {total} total")
                
                if hits:
                    for hit in hits[:1]:
                        if hasattr(hit, 'name'):
                            print(f"    → {hit.name}")
                        elif hasattr(hit, 'content'):
                            content = hit.content[:50] + "..." if len(hit.content) > 50 else hit.content
                            print(f"    → {content}")
            except Exception as e:
                print(f"  '{query}': ERREUR - {e}")
        
        # 5. Test de recherche avec attributs spécifiques
        print(f"\n🎯 TEST RECHERCHE AVEC ATTRIBUTS:")
        try:
            result = index.search("couches", {
                "attributesToSearchOn": ["*"],
                "limit": 2,
                "attributesToRetrieve": ["*"]
            })
            hits = getattr(result, 'hits', [])
            print(f"  Recherche avec attributesToSearchOn=['*']: {len(hits)} résultats")
        except Exception as e:
            print(f"  Erreur avec attributesToSearchOn: {e}")
        
    except Exception as e:
        print(f"❌ Erreur lors du diagnostic: {e}")

def main():
    """Fonction principale"""
    print("🔧 DIAGNOSTIC APPROFONDI MEILISEARCH")
    print("=" * 60)
    print(f"URL: {MEILI_URL}")
    print(f"Company ID: {COMPANY_ID}")
    
    # Connexion
    try:
        client = meilisearch.Client(MEILI_URL, MEILI_KEY)
        version = client.get_version()
        print(f"✅ Connecté à Meilisearch")
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        return
    
    # Liste des index à diagnostiquer
    indexes_to_check = [
        f"products_{COMPANY_ID}",
        f"company_docs_{COMPANY_ID}",  # Pour comparaison
        f"delivery_{COMPANY_ID}",
        f"support_paiement_{COMPANY_ID}",
        f"localisation_{COMPANY_ID}"
    ]
    
    # Diagnostic de chaque index
    for index_uid in indexes_to_check:
        debug_index_complete(client, index_uid)
    
    print(f"\n🎉 DIAGNOSTIC TERMINÉ")
    print(f"\n📋 ACTIONS RECOMMANDÉES:")
    print(f"1. Si les attributs searchable sont vides ou incorrects → Reconfigurer")
    print(f"2. Si les documents n'ont pas les bons champs → Réindexer")
    print(f"3. Si la recherche ne fonctionne pas → Vérifier les synonymes")

if __name__ == "__main__":
    main()
