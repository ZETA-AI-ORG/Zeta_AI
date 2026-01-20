"""
🧪 TEST DES 4 ENDPOINTS DASHBOARD BOTLIVE
Script pour tester les endpoints prioritaires
"""

import asyncio
import httpx
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
COMPANY_ID = "4OS4yFcf2LZwxhKojbAVbKuVuSdb"

async def test_endpoint(name: str, url: str):
    """Teste un endpoint et affiche le résultat"""
    print(f"\n{'='*80}")
    print(f"🧪 TEST: {name}")
    print(f"{'='*80}")
    print(f"URL: {url}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Succès!")
                print(f"\nRéponse:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
            else:
                print(f"❌ Erreur: {response.text}")
                
    except Exception as e:
        print(f"❌ Exception: {e}")

async def main():
    """Teste les 4 endpoints dashboard"""
    
    print("\n" + "="*80)
    print("🚀 TEST DES ENDPOINTS DASHBOARD BOTLIVE")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Company ID: {COMPANY_ID}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Stats
    await test_endpoint(
        "GET /botlive/stats/{company_id}",
        f"{BASE_URL}/botlive/stats/{COMPANY_ID}?time_range=today"
    )
    
    # Test 2: Commandes actives
    await test_endpoint(
        "GET /botlive/orders/active/{company_id}",
        f"{BASE_URL}/botlive/orders/active/{COMPANY_ID}?limit=10"
    )
    
    # Test 3: Interventions
    await test_endpoint(
        "GET /botlive/interventions/{company_id}",
        f"{BASE_URL}/botlive/interventions/{COMPANY_ID}"
    )
    
    # Test 4: Activité
    await test_endpoint(
        "GET /botlive/activity/{company_id}",
        f"{BASE_URL}/botlive/activity/{COMPANY_ID}?limit=10"
    )
    
    # Test 5: Health check
    await test_endpoint(
        "GET /botlive/health",
        f"{BASE_URL}/botlive/health"
    )
    
    print("\n" + "="*80)
    print("✅ TESTS TERMINÉS")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(main())
