#!/usr/bin/env python3
"""
Test et correction de la recherche Meilisearch
Compare la recherche directe vs le code de l'application
"""

import os
import requests
import meilisearch

# Configuration
MEILI_URL = os.environ.get("MEILI_URL", "http://127.0.0.1:7700")
MEILI_KEY = os.environ.get("MEILI_API_KEY") or os.environ.get("MEILI_MASTER_KEY", "")
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"

def test_direct_http(query: str):
    """Test avec requête HTTP directe (qui fonctionne)"""
    url = f"{MEILI_URL}/indexes/products_{COMPANY_ID}/search"
    headers = {
        "Authorization": f"Bearer {MEILI_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "q": query,
        "limit": 10
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        
        hits = result.get("hits", [])
        total = result.get("estimatedTotalHits", 0)
        
        print(f"🌐 HTTP Direct '{query}': {len(hits)} hits sur {total} total")
        for hit in hits[:2]:
            content = hit.get("content", "")[:100] + "..."
            print(f"    → {content}")
        
        return len(hits) > 0
        
    except Exception as e:
        print(f"❌ Erreur HTTP: {e}")
        return False

def test_python_api(query: str):
    """Test avec l'API Python Meilisearch (qui ne fonctionne pas)"""
    try:
        client = meilisearch.Client(MEILI_URL, MEILI_KEY)
        index = client.index(f"products_{COMPANY_ID}")
        
        result = index.search(query, {"limit": 10})
        
        hits = getattr(result, 'hits', [])
        total = getattr(result, 'estimatedTotalHits', 0)
        
        print(f"🐍 Python API '{query}': {len(hits)} hits sur {total} total")
        for hit in hits[:2]:
            if hasattr(hit, 'content'):
                content = hit.content[:100] + "..."
                print(f"    → {content}")
        
        return len(hits) > 0
        
    except Exception as e:
        print(f"❌ Erreur Python API: {e}")
        return False

def test_filtered_query():
    """Test avec la query filtrée de votre application"""
    problematic_query = "recherche couches pression culottes enfant 13kg"
    
    print(f"\n🧪 TEST DE LA QUERY PROBLÉMATIQUE:")
    print(f"Query: '{problematic_query}'")
    
    # Test HTTP direct
    http_works = test_direct_http(problematic_query)
    
    # Test Python API
    python_works = test_python_api(problematic_query)
    
    print(f"\n📊 RÉSULTATS:")
    print(f"  HTTP Direct: {'✅ FONCTIONNE' if http_works else '❌ ÉCHEC'}")
    print(f"  Python API: {'✅ FONCTIONNE' if python_works else '❌ ÉCHEC'}")
    
    if http_works and not python_works:
        print(f"\n🔧 PROBLÈME IDENTIFIÉ: L'API Python Meilisearch a un problème")
        print(f"   SOLUTION: Utiliser des requêtes HTTP directes dans votre code")

def test_simple_queries():
    """Test avec des queries simples"""
    print(f"\n🔍 TESTS AVEC QUERIES SIMPLES:")
    
    simple_queries = ["couches", "pression", "culottes", "enfant"]
    
    for query in simple_queries:
        print(f"\n  Query: '{query}'")
        http_works = test_direct_http(query)
        python_works = test_python_api(query)
        
        if http_works != python_works:
            print(f"    ⚠️ INCOHÉRENCE: HTTP={http_works}, Python={python_works}")

def suggest_fix():
    """Suggère une correction pour le code"""
    print(f"\n🔧 SUGGESTION DE CORRECTION:")
    print(f"""
Pour corriger votre code de recherche, remplacez l'utilisation de l'API Python par des requêtes HTTP directes :

```python
import requests

def search_products_fixed(company_id: str, query: str):
    url = f"{MEILI_URL}/indexes/products_{company_id}/search"
    headers = {
        "Authorization": f"Bearer {MEILI_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "q": query,
        "limit": 10,
        "attributesToRetrieve": ["*"]
    }
    
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()
```

Cette méthode utilise les mêmes requêtes HTTP que votre interface web qui fonctionne.
""")

def main():
    """Fonction principale"""
    print("🔧 TEST ET CORRECTION DE LA RECHERCHE MEILISEARCH")
    print("=" * 60)
    print(f"URL: {MEILI_URL}")
    print(f"Index: products_{COMPANY_ID}")
    
    # Tests
    test_simple_queries()
    test_filtered_query()
    suggest_fix()
    
    print(f"\n🎉 TESTS TERMINÉS")
    print(f"\nLe problème est probablement dans l'API Python Meilisearch.")
    print(f"La solution est d'utiliser des requêtes HTTP directes comme votre interface web.")

if __name__ == "__main__":
    main()
