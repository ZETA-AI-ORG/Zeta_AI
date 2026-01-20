#!/usr/bin/env python3
"""
Analyse directe complète de Meilisearch
Recherche directe du contenu, settings, attributs de tous les index
"""

import os
import requests
import json
from typing import Dict, Any

# Configuration
MEILI_URL = os.environ.get("MEILI_URL", "http://127.0.0.1:7700")
MEILI_KEY = os.environ.get("MEILI_API_KEY") or os.environ.get("MEILI_MASTER_KEY", "")
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"

def make_request(endpoint: str, method: str = "GET", data: Dict = None) -> Dict[str, Any]:
    """Fait une requête HTTP directe à Meilisearch"""
    url = f"{MEILI_URL}{endpoint}"
    headers = {
        "Authorization": f"Bearer {MEILI_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Erreur requête {endpoint}: {e}")
        return {}

def analyze_index_direct(index_uid: str):
    """Analyse complète d'un index via requêtes HTTP directes"""
    print(f"\n🔍 ANALYSE DIRECTE: {index_uid}")
    print("=" * 70)
    
    # 1. Statistiques de l'index
    stats = make_request(f"/indexes/{index_uid}/stats")
    if stats:
        docs_count = stats.get("numberOfDocuments", 0)
        indexing = stats.get("isIndexing", False)
        print(f"📊 Documents: {docs_count}")
        print(f"📊 En cours d'indexation: {indexing}")
        
        if docs_count == 0:
            print("⚠️ INDEX VIDE selon les stats")
    
    # 2. Settings complets
    print(f"\n⚙️ SETTINGS COMPLETS:")
    settings = make_request(f"/indexes/{index_uid}/settings")
    if settings:
        for key, value in settings.items():
            if isinstance(value, list):
                print(f"  {key}: {len(value)} éléments")
                if value:
                    print(f"    {value}")
            elif isinstance(value, dict):
                print(f"  {key}: {len(value)} entrées")
                if value:
                    for k, v in list(value.items())[:3]:  # Première 3 entrées
                        print(f"    {k}: {v}")
            else:
                print(f"  {key}: {value}")
    
    # 3. Documents via GET direct (même si stats dit 0)
    print(f"\n📄 RÉCUPÉRATION DIRECTE DES DOCUMENTS:")
    docs_response = make_request(f"/indexes/{index_uid}/documents?limit=20")
    if docs_response:
        docs = docs_response.get("results", [])
        total = docs_response.get("total", 0)
        print(f"📋 Documents trouvés via GET direct: {len(docs)} sur {total} total")
        
        if docs:
            print(f"\n📄 ÉCHANTILLON DES DOCUMENTS:")
            for i, doc in enumerate(docs[:3], 1):
                print(f"\n  📄 Document {i}:")
                for key, value in doc.items():
                    if isinstance(value, str) and len(value) > 150:
                        value = value[:150] + "..."
                    print(f"    {key}: {value}")
        else:
            print("📭 Aucun document trouvé via GET direct")
    
    # 4. Test de recherche directe avec différents termes
    print(f"\n🔍 TESTS DE RECHERCHE DIRECTE:")
    test_queries = ["", "couches", "pression", "culottes", "enfant", "bebe", "*"]
    
    for query in test_queries:
        search_data = {
            "q": query,
            "limit": 5,
            "attributesToRetrieve": ["*"],
            "attributesToSearchOn": ["*"]
        }
        
        result = make_request(f"/indexes/{index_uid}/search", "POST", search_data)
        if result:
            hits = result.get("hits", [])
            total = result.get("estimatedTotalHits", 0)
            processing_time = result.get("processingTimeMs", 0)
            
            print(f"  Query '{query}': {len(hits)} hits sur {total} total ({processing_time}ms)")
            
            if hits:
                for hit in hits[:2]:
                    # Essayer de trouver un champ identifiant
                    identifier = (hit.get("name") or 
                                hit.get("title") or 
                                hit.get("id") or 
                                str(hit.get("content", ""))[:50])
                    print(f"    → {identifier}")
    
    # 5. Recherche avec query vide pour tout récupérer
    print(f"\n🌟 RECHERCHE EXHAUSTIVE (query vide):")
    exhaustive_search = make_request(f"/indexes/{index_uid}/search", "POST", {
        "q": "",
        "limit": 100,
        "attributesToRetrieve": ["*"]
    })
    
    if exhaustive_search:
        all_hits = exhaustive_search.get("hits", [])
        total_estimated = exhaustive_search.get("estimatedTotalHits", 0)
        print(f"📊 Recherche exhaustive: {len(all_hits)} documents récupérés sur {total_estimated} estimés")
        
        if all_hits:
            # Analyser la structure des documents
            print(f"\n📋 ANALYSE DE LA STRUCTURE:")
            first_doc = all_hits[0]
            print(f"  Champs disponibles: {list(first_doc.keys())}")
            
            # Compter les types de contenu
            content_types = {}
            for doc in all_hits[:10]:  # Analyser les 10 premiers
                doc_type = doc.get("type", "unknown")
                content_types[doc_type] = content_types.get(doc_type, 0) + 1
            
            print(f"  Types de documents: {content_types}")

def main():
    """Fonction principale"""
    print("🔧 ANALYSE DIRECTE COMPLÈTE MEILISEARCH")
    print("=" * 70)
    print(f"URL: {MEILI_URL}")
    print(f"Company ID: {COMPANY_ID}")
    
    # Test de connexion
    version = make_request("/version")
    if version:
        print(f"✅ Connecté à Meilisearch v{version.get('pkgVersion', 'unknown')}")
    else:
        print("❌ Impossible de se connecter")
        return
    
    # Liste de tous les index
    print(f"\n📋 LISTE DE TOUS LES INDEX:")
    indexes = make_request("/indexes")
    if indexes:
        all_indexes = indexes.get("results", [])
        print(f"Total des index: {len(all_indexes)}")
        
        for idx in all_indexes:
            uid = idx.get("uid", "")
            docs = idx.get("numberOfDocuments", 0)
            print(f"  {uid}: {docs} documents")
    
    # Analyse détaillée des index de l'entreprise
    target_indexes = [
        f"products_{COMPANY_ID}",
        f"delivery_{COMPANY_ID}",
        f"support_paiement_{COMPANY_ID}",
        f"localisation_{COMPANY_ID}",
        f"company_docs_{COMPANY_ID}"
    ]
    
    for index_uid in target_indexes:
        analyze_index_direct(index_uid)
    
    print(f"\n🎉 ANALYSE DIRECTE TERMINÉE")
    print(f"\n📋 RÉSUMÉ:")
    print(f"- Cette analyse montre le contenu RÉEL de chaque index")
    print(f"- Les settings et attributs configurés")
    print(f"- Les résultats de recherche directe")
    print(f"- La structure des documents")

if __name__ == "__main__":
    main()
