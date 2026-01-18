import sys
import os
import time
from fastapi.testclient import TestClient

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set env vars
os.environ["ZETA_BOTLIVE_ONLY"] = "true"
os.environ["SERVER_JSON_LOGGER_ENABLED"] = "false"
os.environ["BOTLIVE_CATALOG_PREWARM_ON_INVALIDATE"] = "true"

print("⏳ Importation de l'application (peut prendre quelques secondes)...")
try:
    from Zeta_AI.app import app
except Exception as e:
    print(f"❌ Erreur import app: {e}")
    sys.exit(1)

print("✅ App importée. Initialisation TestClient...")
client = TestClient(app)

COMPANY_ID = "W27PwOPiblP8TlOrhPcjOtxd0cza"

def test_cache_lifecycle():
    print(f"🚀 Démarrage des tests de cache pour {COMPANY_ID} via TestClient")

    # 1. Stats initiales
    print("\n📊 1. Récupération des stats initiales...")
    try:
        resp = client.get("/api/cache/stats")
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            stats = resp.json()
            cat_stats = stats.get('catalog_cache', {})
            print(f"Catalog Cache - Size: {cat_stats.get('current_size', 0)}")
            print(f"Catalog Cache - Hits: {cat_stats.get('hits', 0)}")
            print(f"Catalog Cache - Misses: {cat_stats.get('misses', 0)}")
        else:
            print(f"Error: {resp.text}")
    except Exception as e:
        print(f"❌ Erreur appel stats: {e}")

    # 2. Invalider le cache
    print("\n🗑️ 2. Invalidation du cache (Trigger Pre-warm)...")
    try:
        resp = client.delete(f"/api/cache/invalidate/{COMPANY_ID}")
        print(f"Status: {resp.status_code}")
        data = resp.json()
        print(f"Response: {data}")
        
        if data.get("catalog_prewarm_started"):
            print("✅ Pre-warm marqué comme DÉMARRÉ.")
        else:
            print("⚠️ Pre-warm NON démarré.")
    except Exception as e:
        print(f"❌ Erreur invalidation: {e}")

    # 3. Preload (Test manuel de l'endpoint preload)
    print("\n🔄 3. Vérification via Preload...")
    try:
        resp = client.post(f"/api/cache/preload/{COMPANY_ID}")
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")
    except Exception as e:
        print(f"❌ Erreur preload: {e}")

    print("\n✅ Test terminé.")

if __name__ == "__main__":
    test_cache_lifecycle()
