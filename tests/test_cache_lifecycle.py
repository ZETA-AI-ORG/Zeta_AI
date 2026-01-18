import asyncio
import httpx
import time
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

BASE_URL = "http://127.0.0.1:8000"
COMPANY_ID = "W27PwOPiblP8TlOrhPcjOtxd0cza"  # Rue du Grossiste (Test)

async def test_cache_lifecycle():
    print(f"🚀 Démarrage des tests de cache pour {COMPANY_ID}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Vérifier les stats initiales
        print("\n📊 1. Récupération des stats initiales...")
        try:
            resp = await client.get(f"{BASE_URL}/cache/stats")
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                stats = resp.json()
                print(f"Catalog Cache Hits: {stats.get('catalog_cache', {}).get('hits', 0)}")
                print(f"Catalog Cache Misses: {stats.get('catalog_cache', {}).get('misses', 0)}")
            else:
                print(f"Erreur stats: {resp.text}")
        except Exception as e:
            print(f"Erreur connexion: {e}")
            return

        # 2. Invalider le cache (avec pre-warm activé par défaut)
        print("\n🗑️ 2. Invalidation du cache (Trigger Pre-warm)...")
        try:
            resp = await client.delete(f"{BASE_URL}/cache/invalidate/{COMPANY_ID}")
            print(f"Status: {resp.status_code}")
            data = resp.json()
            print(f"Response: {data}")
            
            if data.get("catalog_prewarm_started"):
                print("✅ Pre-warm démarré avec succès !")
            else:
                print("❌ Pre-warm NON démarré (vérifier logs/env)")
        except Exception as e:
            print(f"Erreur invalidation: {e}")

        # 3. Attendre un peu que le pre-warm se termine (c'est asynchrone)
        print("\n⏳ 3. Attente du pre-warm (5s)...")
        await asyncio.sleep(5)

        # 4. Vérification via Preload
        print("\n🔄 4. Vérification via Preload...")
        try:
            resp = await client.post(f"{BASE_URL}/cache/preload/{COMPANY_ID}")
            print(f"Status: {resp.status_code}")
            preload_data = resp.json()
            print(f"Preload Result: {preload_data}")
        except Exception as e:
            print(f"Erreur preload: {e}")

        # 5. Vérifier les stats finales
        print("\n📊 5. Récupération des stats finales...")
        try:
            resp = await client.get(f"{BASE_URL}/cache/stats")
            if resp.status_code == 200:
                stats_final = resp.json()
                print(f"Catalog Cache Entries: {stats_final.get('catalog_cache', {}).get('current_size', 0)}")
                print(f"Catalog Cache Hits: {stats_final.get('catalog_cache', {}).get('hits', 0)}")
            else:
                print(f"Erreur stats: {resp.text}")
        except Exception as e:
            print(f"Erreur connexion: {e}")
        
        print("\n✅ Test terminé.")

if __name__ == "__main__":
    asyncio.run(test_cache_lifecycle())
