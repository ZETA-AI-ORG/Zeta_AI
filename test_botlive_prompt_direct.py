#!/usr/bin/env python3
"""
🔍 TEST DIRECT PROMPT BOTLIVE
Teste la récupération du prompt_botlive_groq_70b pour company_id spécifique
"""

import asyncio
import httpx
import time

async def test_botlive_prompt_direct():
    """Test direct du chargement prompt Botlive"""
    
    print("🔍 TEST DIRECT PROMPT BOTLIVE")
    print("=" * 60)
    
    # Configuration Supabase
    supabase_url = "https://ilbihprkxcgsigvueeme.supabase.co"
    supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlsYmlocHJreGNnc2lndnVlZW1lIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTEzMTQwNCwiZXhwIjoyMDY0NzA3NDA0fQ.Zf0EJbmP5ePGBZL5cY1tFP9FDRvJXDZ3x98zUS993GA"
    
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json"
    }
    
    # Company ID Botlive réel
    company_id = "W27PwOPiblP8TlOrhPcjOtxd0cza"
    
    url = f"{supabase_url}/rest/v1/company_rag_configs"
    params = {
        "company_id": f"eq.{company_id}",
        "select": "prompt_botlive_groq_70b"
    }
    
    print(f"🎯 Company ID: {company_id}")
    print(f"🔗 URL: {url}")
    print(f"📋 Params: {params}")
    print()
    
    # Test avec timeout normal (5s)
    print("📊 TEST 1: Timeout normal (5s)")
    start_time = time.time()
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, headers=headers, params=params)
            elapsed = (time.time() - start_time) * 1000
            
            print(f"✅ Status: {response.status_code}")
            print(f"⏱️ Temps: {elapsed:.0f}ms")
            
            if response.status_code == 200:
                data = response.json() or []
                print(f"📄 Lignes trouvées: {len(data)}")
                
                if data:
                    prompt = data[0].get("prompt_botlive_groq_70b", "")
                    print(f"📝 Taille prompt: {len(prompt)} chars")
                    print(f"🔍 Contient 'JESSICA': {'JESSICA' in prompt}")
                    print(f"🔍 Contient '15 mots': {'15 mots' in prompt}")
                    print(f"🔍 Premiers 200 chars: {prompt[:200]}...")
                else:
                    print("❌ Aucune donnée trouvée pour ce company_id")
            else:
                print(f"❌ Erreur HTTP: {response.status_code}")
                print(f"📄 Response: {response.text}")
                
    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        print(f"❌ ERREUR après {elapsed:.0f}ms: {type(e).__name__}: {e}")
    
    print()
    
    # Test avec timeout très court (1s) pour forcer l'erreur
    print("📊 TEST 2: Timeout court (1s) - Test de robustesse")
    start_time = time.time()
    
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            response = await client.get(url, headers=headers, params=params)
            elapsed = (time.time() - start_time) * 1000
            print(f"✅ Succès inattendu en {elapsed:.0f}ms")
            
    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        print(f"❌ Timeout attendu après {elapsed:.0f}ms: {type(e).__name__}")
    
    print()
    
    # Test avec timeout très long (30s) 
    print("📊 TEST 3: Timeout long (30s) - Performance maximale")
    start_time = time.time()
    
    try:
        timeout_config = httpx.Timeout(connect=30.0, read=30.0, write=30.0, pool=30.0)
        async with httpx.AsyncClient(timeout=timeout_config) as client:
            response = await client.get(url, headers=headers, params=params)
            elapsed = (time.time() - start_time) * 1000
            
            print(f"✅ Status: {response.status_code}")
            print(f"⏱️ Temps: {elapsed:.0f}ms")
            
            if elapsed > 5000:
                print("🚨 PROBLÈME: Requête > 5s pour un SELECT simple!")
                print("🔧 CAUSES POSSIBLES:")
                print("   - Base de données surchargée")
                print("   - Région Supabase éloignée")
                print("   - Index manquant sur company_id")
                print("   - Plan gratuit bridé")
            elif elapsed > 1000:
                print("⚠️ LENT: Requête > 1s (acceptable mais pas optimal)")
            else:
                print("🚀 RAPIDE: Requête < 1s (performance correcte)")
                
    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        print(f"❌ ERREUR après {elapsed:.0f}ms: {type(e).__name__}: {e}")

if __name__ == "__main__":
    print("🚀 Démarrage du test prompt Botlive...")
    asyncio.run(test_botlive_prompt_direct())
    print("\n🏁 Test terminé !")
