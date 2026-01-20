#!/usr/bin/env python3
"""
🧪 TEST PROPRE - Version simplifiée sans capture de logs

Lance un test avec:
- User ID unique
- Nettoyage complet des caches
- Rapport JSON détaillé

Usage:
    python tests/test_clean.py light
    python tests/test_clean.py hardcore
"""

import asyncio
import json
import time
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import httpx

load_dotenv()

# Ajouter le path parent
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
TEST_COMPANY_ID = "4OS4yFcf2LZwxhKojbAVbKuVuSdb"

# ✅ USER ID UNIQUE
import uuid
TEST_USER_ID = f"test_simulator_{uuid.uuid4().hex[:8]}"


def clear_all_caches():
    """🧹 Nettoyage complet"""
    print("\n" + "="*80)
    print("🧹 NETTOYAGE COMPLET DES CACHES")
    print("="*80)
    
    # Redis
    try:
        import redis
        redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=0,
            decode_responses=True
        )
        redis_client.flushall()
        print("✅ Redis: FLUSHALL exécuté")
    except Exception as e:
        print(f"⚠️ Redis: {e}")
    
    # Supabase
    try:
        from supabase import create_client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if supabase_url and supabase_key:
            supabase = create_client(supabase_url, supabase_key)
            result = supabase.table("conversations").delete().like("user_id", "test_simulator_%").execute()
            print(f"✅ Supabase: {len(result.data) if result.data else 0} conversations supprimées")
    except Exception as e:
        print(f"⚠️ Supabase: {e}")
    
    print("="*80 + "\n")
    time.sleep(2)


async def execute_turn(message):
    """Exécute un tour avec retry"""
    import httpx
    
    start = time.time()
    
    # Gérer image
    if isinstance(message, dict):
        text = message.get("text", "")
        image_url = message.get("image_url")
        images = [image_url] if image_url else []
    else:
        text = message
        images = []
    
    # Appel API
    payload = {
        "company_id": TEST_COMPANY_ID,
        "user_id": TEST_USER_ID,
        "message": text,
        "botlive_enabled": False
    }
    
    if images:
        payload["images"] = images
    
    # Retry avec timeout augmenté
    max_retries = 3
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # Timeout progressif: 180s, 240s, 300s
            timeout_seconds = 180 + (attempt * 60)
            
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                print(f"   Tentative {attempt + 1}/{max_retries} (timeout: {timeout_seconds}s)...")
                response = await client.post("http://127.0.0.1:8002/chat", json=payload)
                result = response.json()
                break  # Succès
                
        except (httpx.ReadTimeout, httpx.ConnectError) as e:
            last_error = e
            if attempt < max_retries - 1:
                print(f"   ⚠️ Timeout, retry dans 2s...")
                await asyncio.sleep(2)
            else:
                print(f"   ❌ Échec après {max_retries} tentatives")
                raise
    
    exec_time = (time.time() - start) * 1000
    
    return {
        "message": text,
        "response": result.get("response", ""),
        "thinking": result.get("thinking", ""),
        "full_result": result,
        "exec_time_ms": exec_time
    }


SCENARIOS = {
    "light": [
        "Bonjour",
        "Je cherche des couches pour bébé",
        "Mon bébé a 6 mois et pèse 8kg",
        "Je veux 300 couches",
        "Je suis à Yopougon",
        "Mon numéro: 0708123456",
        {"text": "Voilà mon paiement", "image_url": "https://scontent.xx.fbcdn.net/v/t1.15752-9/462578107_1092842449209959_3654924410750827275_n.jpg?_nc_cat=109&ccb=1-7&_nc_sid=9f807c&_nc_ohc=_rvqGnI_0bQQ7kNvgGCCxrm&_nc_zt=23&_nc_ht=scontent.xx&oh=03_Q7cD1QGdXWPNxEBQcHJQQKJNKcLfQUQrGDxqgHhPWGVMlVELqQ&oe=67C0F8D6"},
        "Oui je confirme"
    ],
    "hardcore": [
        "Yo",
        "Vous vendez aussi des biberons?",
        "Ah ok. Bon euh... mon bébé a 5 mois, il fait 7kg je crois... ou 8... j'sais plus. Vous avez quoi?",
        "QUOI 22.900???? C'est du vol! Sur Internet c'est 15.000!",
        "Et c'est même pas des vraies marques! C'est chinois vos trucs non?",
        "Bon laissez tomber. Parlez-moi plutôt des culottes",
        "Attendez c'est 150 ou 300? Je comprends rien à vos prix",
        "Je suis à Anyama. 2500 FCFA??? Non mais c'est abusé!",
        "Et si je viens chercher moi-même? Vous êtes où exactement?",
        "Wave seulement? J'ai pas Wave moi! Vous prenez pas MTN Money?",
        "Vous savez quoi, je vais plutôt prendre les couches à pression finalement",
        "Taille 4 ça va pour 7kg c'est bon? Parce que taille 3 c'est jusqu'à 11kg vous avez dit",
        "2000 FCFA d'acompte?! Et si vous disparaissez avec mon argent? Comment je suis sûr?",
        "Vous avez une garantie? Genre si mon bébé fait une allergie je peux retourner?",
        "Et si je prends 10 lots là, vous me faites 50% de réduction?",
        "Parce que chez Carrefour ils font des promos à -30%...",
        "Vous livrez au Ghana? Mon cousin habite là-bas",
        "Bon ok forget. Recapitulez-moi TOUT pour taille 3, 300 couches, Anyama",
        "Hmm... Et je peux payer moitié maintenant moitié à la livraison?",
        "Bon ok... Je vais faire le dépôt. C'est quoi déjà le numéro Wave?",
        {"text": "Voilà j'ai envoyé", "image_url": "https://scontent.xx.fbcdn.net/v/t1.15752-9/553547596_833613639156226_7121847885677551127_n.jpg?stp=dst-jpg_s2048x2048&_nc_cat=107&ccb=1-7&_nc_sid=9f807c&_nc_ohc=Kd9lnTBXOxYQ7kNvgGNJRJM&_nc_zt=23&_nc_ht=scontent.xx&_nc_gid=AqVxlPx_-xqCYNVSJWwzTBh&oh=03_Q7cD1QEqLjJnPvnNZFJGLYCqTUxUXZNFLqYLCBqQvxhTCjUfUQ&oe=67C0F0A7"},
        "Ah merde j'ai envoyé que 202. Attends je renvoie le bon montant",
        {"text": "Voilà maintenant c'est bon, 2020 FCFA", "image_url": "https://scontent.xx.fbcdn.net/v/t1.15752-9/556908482_1314851517042795_6410429215433068876_n.jpg?stp=dst-jpg_s2048x2048&_nc_cat=107&ccb=1-7&_nc_sid=9f807c&_nc_ohc=yrKxBHVPPGQQ7kNvgGBXJYs&_nc_zt=23&_nc_ht=scontent.xx&_nc_gid=AqVxlPx_-xqCYNVSJWwzTBh&oh=03_Q7cD1QFGKdCxZrZFxN_Yw_Hs-HZqPKPGRLRHWGwUBUjqVHvA9Q&oe=67C0E9F5"},
        "Ok c'est validé? Mon numéro: 0701234567",
        "Bon récapitule-moi TOUT avant que je valide définitivement",
        "Ok c'est bon, je confirme la commande. Livraison demain possible?"
    ]
}


async def run_test(scenario_name: str):
    """Lance le test"""
    if scenario_name not in SCENARIOS:
        print(f"❌ Scénario inconnu: {scenario_name}")
        return
    
    print(f"\n🆔 User ID: {TEST_USER_ID}")
    
    # Nettoyage
    clear_all_caches()
    
    # Test
    print("="*80)
    print(f"🧪 TEST: {scenario_name}")
    print("="*80 + "\n")
    
    messages = SCENARIOS[scenario_name]
    turns = []
    start_time = time.time()
    
    for i, msg in enumerate(messages, 1):
        print(f"⏳ Tour {i}/{len(messages)}...")
        result = await execute_turn(msg)
        turns.append(result)
        
        # Affichage
        print(f"\n{'='*80}")
        print(f"🔄 TOUR {i} | ⏱️ {result['exec_time_ms']:.0f}ms")
        print(f"👤 CLIENT: {result['message'][:80]}")
        print(f"🤖 ASSISTANT: {result['response'][:200]}")
        
        thinking = result.get('thinking', '')
        if thinking:
            print(f"🧠 THINKING: {len(thinking)} chars")
        else:
            print(f"⚠️ THINKING: VIDE")
        
        print("="*80 + "\n")
        
        await asyncio.sleep(1)
    
    total_time = time.time() - start_time
    
    # Rapport
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = f"tests/reports/CLEAN_{scenario_name}_{timestamp}.json"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    report = {
        "scenario": scenario_name,
        "user_id": TEST_USER_ID,
        "timestamp": datetime.now().isoformat(),
        "total_time_s": total_time,
        "total_turns": len(turns),
        "turns": turns
    }
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 Rapport: {report_path}")
    print(f"⏱️ Temps total: {total_time:.1f}s")
    print(f"✅ Test terminé!\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tests/test_clean.py [light|hardcore]")
        sys.exit(1)
    
    scenario = sys.argv[1]
    asyncio.run(run_test(scenario))
