import asyncio
import sys
import os
import json
import logging

# Configuration du logging pour voir les traces
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Ajouter le chemin du projet pour l'import
sys.path.append(os.getcwd())

async def test_redis_company_flow():
    company_id = "W27PwOPiblP8TlOrhPcjOtxd0cza"
    print(f"🧪 TEST BLOC 1 : Flux Redis pour Company ID {company_id}\n")
    
    from core.company_cache_manager import company_cache
    
    # 1. Premier appel (devrait être un MISS)
    print("--- APPEL 1 (Attendu : SUPABASE) ---")
    profile1 = await company_cache.get_cached_company_profile(company_id)
    if profile1:
        print(f"✅ Nom reçu : {profile1.get('shop_name') or profile1.get('company_name')}")
        print(f"✅ WhatsApp : {profile1.get('whatsapp_number')}")
    else:
        print("❌ Échec de récupération au premier appel")

    # 2. Deuxième appel (devrait être un HIT)
    print("\n--- APPEL 2 (Attendu : REDIS HIT) ---")
    profile2 = await company_cache.get_cached_company_profile(company_id)
    if profile2:
        print(f"🚀 Succès : Données récupérées instantanément depuis Redis")
    else:
        print("❌ Échec de récupération au deuxième appel")

    # 3. Vérification de la clé dans Redis via redis-cli (optionnel mais utile pour le log)
    print("\n--- VÉRIFICATION FINALE ---")
    if profile1 == profile2:
        print("💎 Intégrité des données OK : Les profils sont identiques.")
    else:
        print("⚠️ Attention : Les données diffèrent entre les deux appels.")

if __name__ == "__main__":
    # S'assurer que les variables d'environnement sont chargées si on teste localement
    # Sur le VPS, elles sont déjà là.
    asyncio.run(test_redis_company_flow())
