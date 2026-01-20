import requests
import json

# CONFIGURATION DIRECTE - CLÉS EN DUR POUR TEST
MEILI_URL = "http://localhost:7700"
API_KEY = "Bac2018mado@2066"

headers = {"Authorization": f"Bearer {API_KEY}"}

def test_connection():
    """Test de connexion MeiliSearch"""
    print("🔍 TEST DE CONNEXION MEILISEARCH")
    print("=" * 50)
    
    try:
        # Test health
        response = requests.get(f"{MEILI_URL}/health", headers=headers)
        print(f"✅ Health: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Erreur health: {e}")
    
    try:
        # Test stats
        response = requests.get(f"{MEILI_URL}/stats", headers=headers)
        print(f"✅ Stats: {response.status_code}")
        if response.status_code == 200:
            stats = response.json()
            print(f"📊 Stats: {json.dumps(stats, indent=2)}")
    except Exception as e:
        print(f"❌ Erreur stats: {e}")
    
    try:
        # Test indexes
        response = requests.get(f"{MEILI_URL}/indexes", headers=headers)
        print(f"✅ Indexes: {response.status_code}")
        if response.status_code == 200:
            indexes = response.json()
            print(f"📁 Indexes: {json.dumps(indexes, indent=2)}")
        else:
            print(f"❌ Erreur indexes: {response.text}")
    except Exception as e:
        print(f"❌ Erreur indexes: {e}")

def test_specific_indexes():
    """Test des index spécifiques"""
    print("\n🔍 TEST DES INDEX SPÉCIFIQUES")
    print("=" * 50)
    
    # Index spécifiques à tester
    test_indexes = [
        "products_MpfnlSbqwaZ6F4HvxQLRL9du0yG3",
        "delivery_MpfnlSbqwaZ6F4HvxQLRL9du0yG3",
        "support_paiement_MpfnlSbqwaZ6F4HvxQLRL9du0yG3",
        "company_docs_MpfnlSbqwaZ6F4HvxQLRL9du0yG3",
        "localisation_MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
    ]
    
    for index_name in test_indexes:
        try:
            # Test settings
            response = requests.get(f"{MEILI_URL}/indexes/{index_name}/settings", headers=headers)
            print(f"📁 {index_name}: {response.status_code}")
            if response.status_code == 200:
                settings = response.json()
                print(f"  ⚙️  Settings: {json.dumps(settings, indent=4)}")
            else:
                print(f"  ❌ Erreur: {response.text}")
        except Exception as e:
            print(f"  ❌ Exception: {e}")

if __name__ == "__main__":
    test_connection()
    test_specific_indexes()
