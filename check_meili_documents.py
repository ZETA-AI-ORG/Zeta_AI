#!/usr/bin/env python3
"""
🔍 VÉRIFICATION DOCUMENTS MEILISEARCH
Vérifie le nombre réel de documents dans l'index products
"""

import requests
import os
import json

def check_documents():
    """Vérifie les documents dans l'index products"""
    print("🔍 VÉRIFICATION DOCUMENTS MEILISEARCH")
    print("=" * 50)
    
    meili_url = os.getenv("MEILISEARCH_URL", "http://localhost:7700")
    meili_key = os.getenv("MEILISEARCH_MASTER_KEY", "")
    company_id = "XkCn8fjNWEWwqiiKMgJX7OcQrUJ3"
    index_name = f"products_{company_id}"
    
    headers = {
        "Authorization": f"Bearer {meili_key}",
        "Content-Type": "application/json"
    }
    
    print(f"🗂️ Index: {index_name}")
    
    try:
        # 1. Vérifier les stats de l'index
        response = requests.get(f"{meili_url}/indexes/{index_name}/stats", headers=headers)
        if response.status_code == 200:
            stats = response.json()
            print(f"📊 Stats index:")
            print(f"   → Documents: {stats.get('numberOfDocuments', 0)}")
            print(f"   → Indexing: {stats.get('isIndexing', False)}")
            print(f"   → Taille: {stats.get('fieldDistribution', {})}")
        
        # 2. Lister quelques documents
        response = requests.get(f"{meili_url}/indexes/{index_name}/documents?limit=5", headers=headers)
        if response.status_code == 200:
            docs = response.json()
            print(f"\n📄 Documents trouvés: {len(docs.get('results', []))}")
            
            for i, doc in enumerate(docs.get('results', [])[:3]):
                print(f"\n📋 Document {i+1}:")
                print(f"   → ID: {doc.get('id', 'N/A')}")
                print(f"   → Product Name: {doc.get('product_name', 'N/A')}")
                print(f"   → Color: {doc.get('color', 'N/A')}")
                print(f"   → Price: {doc.get('price', 'N/A')}")
        else:
            print(f"❌ Erreur documents: {response.status_code}")
            print(f"📝 Réponse: {response.text}")
        
        # 3. Vérifier les settings actuels
        response = requests.get(f"{meili_url}/indexes/{index_name}/settings", headers=headers)
        if response.status_code == 200:
            settings = response.json()
            searchable = settings.get('searchableAttributes', [])
            print(f"\n🔍 Attributs recherchables configurés: {len(searchable)}")
            print(f"   → {searchable}")
        
        # 4. Test de recherche simple
        print(f"\n🧪 Test recherche simple:")
        test_queries = ["*", "casque", "rouge"]
        
        for query in test_queries:
            response = requests.post(
                f"{meili_url}/indexes/{index_name}/search",
                headers=headers,
                json={"q": query, "limit": 3}
            )
            
            if response.status_code == 200:
                results = response.json()
                hits = len(results.get("hits", []))
                print(f"   → '{query}': {hits} résultats")
            else:
                print(f"   → '{query}': Erreur {response.status_code}")
                print(f"     Réponse: {response.text}")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    check_documents()
