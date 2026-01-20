#!/usr/bin/env python3
"""
🔍 DIAGNOSTIC MEILISEARCH COMPLET
"""
import os
import meilisearch
from database.vector_store_clean_v2 import get_meilisearch_client, _generate_ngrams

def debug_meilisearch():
    """Diagnostic complet MeiliSearch"""
    
    print("=" * 60)
    print("🔍 DIAGNOSTIC MEILISEARCH COMPLET")
    print("=" * 60)
    
    # 1. Test connexion
    print("\n1️⃣ TEST CONNEXION")
    client = get_meilisearch_client()
    if not client:
        print("❌ Client MeiliSearch non créé")
        return
    
    try:
        health = client.health()
        print(f"✅ MeiliSearch health: {health}")
    except Exception as e:
        print(f"❌ Erreur health: {e}")
        return
    
    # 2. Lister les index
    print("\n2️⃣ INDEX DISPONIBLES")
    try:
        indexes = client.get_indexes()
        print(f"📦 Nombre d'index: {len(indexes['results'])}")
        for idx in indexes['results']:
            print(f"   - {idx.uid} ({getattr(idx, 'primary_key', 'N/A')})")
    except Exception as e:
        print(f"❌ Erreur listing index: {e}")
        # Continuer malgré l'erreur
        pass
    
    # 3. Test recherche sur index spécifique
    print("\n3️⃣ TEST RECHERCHE DIRECTE")
    company_id = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
    test_indexes = [
        f"products_{company_id}",
        f"delivery_{company_id}",
        f"support_paiement_{company_id}",
        f"localisation_{company_id}",
        f"company_docs_{company_id}"
    ]
    
    for index_name in test_indexes:
        try:
            index = client.index(index_name)
            # Test recherche simple
            result = index.search("couches", {'limit': 3})
            print(f"✅ {index_name}: {len(result.get('hits', []))} résultats")
            
            # Afficher premier résultat si existe
            if result.get('hits'):
                first_hit = result['hits'][0]
                content = first_hit.get('content', '')[:100]
                print(f"   Premier: {content}...")
                
        except Exception as e:
            print(f"❌ {index_name}: {e}")
    
    # 4. Test n-grammes
    print("\n4️⃣ TEST N-GRAMMES")
    query = "QUELS SONT LES TAILLES DISPONIBLES EN PRESSION ET AUSSI EN CULOTTES?"
    ngrams = _generate_ngrams(query.lower(), max_n=3, min_n=1)
    print(f"📝 Query: {query}")
    print(f"🔤 N-grammes générés: {len(ngrams)}")
    for i, ngram in enumerate(ngrams[:5]):  # Premiers 5
        print(f"   {i+1}. '{ngram}'")
    
    # 5. Test recherche avec n-grammes
    print("\n5️⃣ TEST RECHERCHE AVEC N-GRAMMES")
    index_name = f"products_{company_id}"
    try:
        index = client.index(index_name)
        for ngram in ngrams[:3]:  # Tester premiers 3 n-grammes
            result = index.search(ngram, {'limit': 2})
            hits_count = len(result.get('hits', []))
            print(f"   '{ngram}': {hits_count} résultats")
            
    except Exception as e:
        print(f"❌ Erreur test n-grammes: {e}")
    
    print("\n" + "=" * 60)
    print("✅ DIAGNOSTIC TERMINÉ")
    print("=" * 60)

if __name__ == "__main__":
    debug_meilisearch()
