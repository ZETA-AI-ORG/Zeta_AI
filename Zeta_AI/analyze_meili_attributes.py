import requests
import json

# CONFIGURATION DIRECTE - CLÉS EN DUR POUR TEST
MEILI_URL = "http://localhost:7700"
API_KEY = "masterKey"

headers = {"Authorization": f"Bearer {API_KEY}"}

def get_indexes():
    """Récupère tous les index"""
    response = requests.get(f"{MEILI_URL}/indexes", headers=headers)
    return response.json()

def get_index_settings(index_name):
    """Récupère les settings d'un index"""
    response = requests.get(f"{MEILI_URL}/indexes/{index_name}/settings", headers=headers)
    return response.json()

def get_sample_documents(index_name, limit=2):
    """Récupère des échantillons de documents"""
    response = requests.post(
        f"{MEILI_URL}/indexes/{index_name}/search",
        headers={**headers, "Content-Type": "application/json"},
        json={"q": "", "limit": limit}
    )
    return response.json()

def analyze_all_indexes():
    """Analyse complète de tous les index"""
    print("🔍 ANALYSE COMPLÈTE DES INDEX MEILISEARCH")
    print("=" * 60)
    
    indexes = get_indexes()
    print(f"📊 Nombre d'index trouvés: {len(indexes.get('results', []))}")
    
    for index_info in indexes.get('results', []):
        index_name = index_info['uid']
        print(f"\n📁 INDEX: {index_name}")
        print("-" * 40)
        
        # Settings
        try:
            settings = get_index_settings(index_name)
            print("⚙️  SETTINGS:")
            print(f"  - searchableAttributes: {settings.get('searchableAttributes', 'N/A')}")
            print(f"  - filterableAttributes: {settings.get('filterableAttributes', 'N/A')}")
            print(f"  - sortableAttributes: {settings.get('sortableAttributes', 'N/A')}")
            print(f"  - displayedAttributes: {settings.get('displayedAttributes', 'N/A')}")
            print(f"  - rankingRules: {settings.get('rankingRules', 'N/A')}")
            print(f"  - synonyms: {settings.get('synonyms', 'N/A')}")
            print(f"  - stopWords: {settings.get('stopWords', 'N/A')}")
        except Exception as e:
            print(f"❌ Erreur settings: {e}")
        
        # Échantillons de documents
        try:
            docs = get_sample_documents(index_name)
            if docs.get('hits'):
                print("📄 CHAMPS DISPONIBLES (échantillon):")
                sample_doc = docs['hits'][0]
                for key in sorted(sample_doc.keys()):
                    value = sample_doc[key]
                    if isinstance(value, str) and len(value) > 50:
                        value = value[:50] + "..."
                    print(f"  - {key}: {value}")
            else:
                print("📄 Aucun document trouvé")
        except Exception as e:
            print(f"❌ Erreur documents: {e}")

if __name__ == "__main__":
    analyze_all_indexes()






