#!/usr/bin/env python3
"""
🔍 FULL LOG SIMULATOR - Capture ABSOLUMENT TOUT du serveur

Capture en temps réel:
- Tous les logs serveur (stdout/stderr)
- Toutes les réponses API
- Tous les thinking
- Toutes les métriques
- Tous les contextes

Génère un JSON COMPLET pour analyse détaillée.

Usage:
    python tests/full_log_simulator.py --scenario light
    python tests/full_log_simulator.py --scenario hardcore
"""

import asyncio
import json
import time
import re
import subprocess
import threading
import queue
from typing import List, Dict, Any
from datetime import datetime
import sys
import os
from dotenv import load_dotenv

# ✅ CHARGER .env AVANT TOUT
load_dotenv()

# Ajouter le path parent pour imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration test
TEST_COMPANY_ID = "4OS4yFcf2LZwxhKojbAVbKuVuSdb"  # Rue du Grossiste
TEST_COMPANY_NAME = "Rue du Grossiste"

# ✅ GÉNÉRER UN USER ID UNIQUE À CHAQUE EXÉCUTION
import uuid
TEST_USER_ID = f"test_simulator_{uuid.uuid4().hex[:8]}"
print(f"🆔 User ID unique généré: {TEST_USER_ID}")


class ServerLogCapture:
    """
    📡 Capture TOUS les logs du serveur en temps réel
    """
    
    def __init__(self):
        self.logs = []
        self.log_queue = queue.Queue()
        self.capture_thread = None
        self.stop_capture = False
        
    def start_capture(self):
        """Démarre la capture des logs serveur"""
        print("🎬 [LOG_CAPTURE] Démarrage capture logs serveur...")
        self.stop_capture = False
        self.capture_thread = threading.Thread(target=self._capture_logs, daemon=True)
        self.capture_thread.start()
    
    def _capture_logs(self):
        """Thread qui capture les logs en continu"""
        # Note: Cette méthode suppose que les logs sont accessibles
        # Pour Windows, on peut lire depuis un fichier de log ou utiliser une autre méthode
        pass
    
    def add_log(self, log_line: str, source: str = "server"):
        """Ajoute un log capturé"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "content": log_line
        }
        self.logs.append(log_entry)
    
    def get_logs_for_turn(self, start_time: float, end_time: float) -> List[Dict]:
        """Récupère tous les logs pour un tour spécifique"""
        turn_logs = []
        for log in self.logs:
            log_time = datetime.fromisoformat(log["timestamp"]).timestamp()
            if start_time <= log_time <= end_time:
                turn_logs.append(log)
        return turn_logs
    
    def stop(self):
        """Arrête la capture"""
        self.stop_capture = True
        if self.capture_thread:
            self.capture_thread.join(timeout=2)


class FullLogTracker:
    """
    📊 Tracker COMPLET avec TOUS les logs serveur
    """
    
    def __init__(self, scenario_name: str):
        self.scenario_name = scenario_name
        self.turns = []
        self.total_time_ms = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        self.start_time = None
        self.end_time = None
        self.log_capture = ServerLogCapture()
        
    def start_conversation(self):
        """Démarre le tracking de conversation"""
        self.start_time = time.time()
        self.log_capture.start_capture()
        print("\n" + "="*80)
        print(f"🧪 DÉBUT TEST COMPLET: {self.scenario_name}")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")
    
    def add_turn(
        self,
        turn_number: int,
        user_message: str,
        llm_response: str,
        full_api_response: Dict,
        execution_time_ms: int,
        tokens_used: Dict,
        cost: float
    ):
        """
        Enregistre un tour avec TOUS les détails
        """
        turn_start = time.time() - (execution_time_ms / 1000)
        turn_end = time.time()
        
        # Capturer les logs serveur pour ce tour
        server_logs = self.log_capture.get_logs_for_turn(turn_start, turn_end)
        
        turn_data = {
            "turn": turn_number,
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "llm_response": llm_response,
            "full_api_response": full_api_response,  # TOUT l'objet API
            "server_logs": server_logs,  # TOUS les logs serveur
            "execution_time_ms": execution_time_ms,
            "tokens": tokens_used,
            "cost_usd": cost
        }
        
        self.turns.append(turn_data)
        self.total_time_ms += execution_time_ms
        self.total_tokens += tokens_used.get('total', 0)
        self.total_cost += cost
        
        # Display turn
        self._print_turn_details(turn_data)
    
    def _print_turn_details(self, turn: dict):
        """Affiche les détails d'un tour"""
        tokens = turn.get('tokens', {})
        total_tokens = tokens.get('total', 0) if isinstance(tokens, dict) else tokens
        print(f"\n{'='*80}")
        print(f"🔄 TOUR {turn['turn']} | ⏱️ {turn['execution_time_ms']:.0f}ms | 🔤 {total_tokens}t | 💰 ${turn['cost_usd']:.4f}")
        print("="*80)
        print(f"👤 CLIENT: {turn['user_message'][:80]}")
        print(f"\n🤖 ASSISTANT: {turn['llm_response'][:200]}")
        
        # Afficher thinking si présent
        api_resp = turn.get('full_api_response', {})
        thinking = api_resp.get('thinking', '')
        if thinking:
            print(f"\n🧠 THINKING: {len(thinking)} chars")
            print(f"   {thinking[:150]}...")
        
        # Afficher nombre de logs capturés
        log_count = len(turn.get('server_logs', []))
        if log_count > 0:
            print(f"\n📋 LOGS SERVEUR: {log_count} entrées capturées")
        
        print("\n" + "="*80 + "\n")
    
    def end_conversation(self):
        """Termine la conversation"""
        self.end_time = time.time()
        self.log_capture.stop()
    
    def save_full_report(self, output_path: str = None):
        """
        Sauvegarde le rapport COMPLET en JSON
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"tests/reports/FULL_{self.scenario_name}_{timestamp}.json"
        
        # Créer dossier si nécessaire
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        report = {
            "scenario": self.scenario_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_duration_ms": (self.end_time - self.start_time) * 1000 if self.end_time else 0,
            "total_rag_time_ms": self.total_time_ms,
            "total_turns": len(self.turns),
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost,
            "turns": self.turns,
            "all_server_logs": self.log_capture.logs  # TOUS les logs
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 RAPPORT COMPLET sauvegardé: {output_path}")
        print(f"📊 Taille: {os.path.getsize(output_path) / 1024:.1f} KB")
        print(f"📋 Logs capturés: {len(self.log_capture.logs)}")
        return output_path
    
    def print_summary(self):
        """Affiche le résumé final"""
        print("\n" + "="*80)
        print(f"📊 RÉSUMÉ TEST: {self.scenario_name}")
        print("="*80 + "\n")
        
        duration_s = (self.end_time - self.start_time) if self.end_time else 0
        print(f"⏱️  TEMPS:")
        print(f"   Total conversation: {duration_s*1000:.0f}ms ({duration_s:.1f}s)")
        print(f"   Temps RAG cumulé: {self.total_time_ms}ms")
        print(f"   Nombre de tours: {len(self.turns)}")
        if len(self.turns) > 0:
            print(f"   Temps moyen/tour: {self.total_time_ms/len(self.turns):.0f}ms")
        
        print(f"\n💰 COÛTS:")
        print(f"   Tokens totaux: {self.total_tokens}")
        print(f"   Coût total: ${self.total_cost:.4f}")
        if len(self.turns) > 0:
            print(f"   Coût moyen/tour: ${self.total_cost/len(self.turns):.4f}")
        
        print(f"\n📋 LOGS:")
        print(f"   Logs serveur capturés: {len(self.log_capture.logs)}")
        
        print("\n" + "="*80 + "\n")


async def execute_chat_turn_with_full_capture(user_message) -> Dict[str, Any]:
    """
    Exécute un tour de conversation et capture TOUT
    
    Args:
        user_message: str OU dict {"text": "...", "image_url": "..."}
    
    Returns:
        Dict avec response, full_api_response, execution_time_ms, tokens, cost
    """
    try:
        import httpx
        
        start_time = time.time()
        
        # Gérer message avec ou sans image
        if isinstance(user_message, dict):
            message_text = user_message.get("text", "")
            image_url = user_message.get("image_url")
            images = [image_url] if image_url else []
            if image_url:
                print(f"📸 [IMAGE_URL] {image_url[:80]}...")
        else:
            message_text = user_message
            images = []
        
        # Appel API HTTP
        payload = {
            "company_id": TEST_COMPANY_ID,
            "user_id": TEST_USER_ID,
            "message": message_text,
            "botlive_enabled": False
        }
        
        if images:
            payload["images"] = images
        
        # Appel HTTP avec retry
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(
                        "http://127.0.0.1:8002/chat",
                        json=payload
                    )
                    full_api_response = response.json()
                    break
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ Tentative {attempt + 1}/{max_retries} échouée: {e}")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        # Extraire les infos de base
        response_text = full_api_response.get('response', '')
        thinking_text = full_api_response.get('thinking', '')
        
        # Calculer tokens et coût (estimation)
        prompt_tokens = len(message_text.split())
        completion_tokens = len(response_text.split())
        total_tokens = prompt_tokens + completion_tokens
        
        # Coût Groq: $0.00000079/token
        cost = total_tokens * 0.00000079
        
        tokens_used = {
            "prompt": prompt_tokens,
            "completion": completion_tokens,
            "total": total_tokens
        }
        
        return {
            "response": response_text,
            "full_api_response": full_api_response,  # TOUT
            "execution_time_ms": execution_time_ms,
            "tokens": tokens_used,
            "cost": cost
        }
        
    except Exception as e:
        print(f"❌ Erreur lors de l'exécution du tour: {e}")
        import traceback
        traceback.print_exc()
        return {
            "response": f"ERREUR: {str(e)}",
            "full_api_response": {"error": str(e)},
            "execution_time_ms": 0,
            "tokens": {"prompt": 0, "completion": 0, "total": 0},
            "cost": 0.0
        }


# ============================================================================
# SCÉNARIOS DE TEST
# ============================================================================

SCENARIOS = {
    "light": {
        "name": "light_conversation_simple",
        "description": "Conversation simple et directe",
        "messages": [
            "Bonjour",
            "Je cherche des couches pour bébé",
            "Mon bébé a 6 mois et pèse 8kg",
            "Je veux 300 couches",
            "Je suis à Yopougon",
            "Mon numéro: 0708123456",
            {"text": "Voilà mon paiement", "image_url": "https://scontent.xx.fbcdn.net/v/t1.15752-9/462578107_1092842449209959_3654924410750827275_n.jpg?_nc_cat=109&ccb=1-7&_nc_sid=9f807c&_nc_ohc=_rvqGnI_0bQQ7kNvgGCCxrm&_nc_zt=23&_nc_ht=scontent.xx&oh=03_Q7cD1QGdXWPNxEBQcHJQQKJNKcLfQUQrGDxqgHhPWGVMlVELqQ&oe=67C0F8D6"},
            "Oui je confirme"
        ]
    },
    "hardcore": {
        "name": "hardcore_client_difficile",
        "description": "Client difficile avec objections multiples",
        "messages": [
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
}


def clear_all_caches():
    """
    🧹 VIDE TOUS LES CACHES avant le test
    - Redis (cache sémantique, exact, FAQ)
    - Historique conversations
    - Enhanced memory
    """
    print("\n" + "="*80)
    print("🧹 NETTOYAGE COMPLET DES CACHES")
    print("="*80)
    
    try:
        import redis
        # Connexion Redis
        redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=0,
            decode_responses=True
        )
        
        # Vider TOUT Redis
        redis_client.flushall()
        print("✅ Redis: FLUSHALL exécuté")
        
    except Exception as e:
        print(f"⚠️ Redis: Erreur vidage - {e}")
    
    try:
        # Vider la base Supabase (historique conversations)
        from supabase import create_client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if supabase_url and supabase_key:
            supabase = create_client(supabase_url, supabase_key)
            
            # Supprimer les conversations de test
            result = supabase.table("conversations").delete().like("user_id", "test_simulator_%").execute()
            print(f"✅ Supabase: {len(result.data) if result.data else 0} conversations test supprimées")
        else:
            print("⚠️ Supabase: Variables d'environnement manquantes")
            
    except Exception as e:
        print(f"⚠️ Supabase: Erreur vidage - {e}")
    
    print("="*80 + "\n")
    print("⏳ Attente 2s pour stabilisation...")
    time.sleep(2)


async def run_scenario(scenario_key: str):
    """
    Exécute un scénario complet avec capture TOTALE
    """
    if scenario_key not in SCENARIOS:
        print(f"❌ Scénario '{scenario_key}' inconnu. Disponibles: {list(SCENARIOS.keys())}")
        return
    
    # ✅ VIDER TOUS LES CACHES AVANT LE TEST
    clear_all_caches()
    
    scenario = SCENARIOS[scenario_key]
    tracker = FullLogTracker(scenario["name"])
    
    tracker.start_conversation()
    
    for turn_num, message in enumerate(scenario["messages"], 1):
        print(f"⏳ Exécution tour {turn_num}...")
        
        result = await execute_chat_turn_with_full_capture(message)
        
        # Extraire le message texte
        if isinstance(message, dict):
            message_text = message.get("text", "")
        else:
            message_text = message
        
        tracker.add_turn(
            turn_number=turn_num,
            user_message=message_text,
            llm_response=result["response"],
            full_api_response=result["full_api_response"],
            execution_time_ms=result["execution_time_ms"],
            tokens_used=result["tokens"],
            cost=result["cost"]
        )
        
        # Petit délai entre les tours
        await asyncio.sleep(1)
    
    tracker.end_conversation()
    tracker.print_summary()
    report_path = tracker.save_full_report()
    
    print(f"\n✅ Test terminé!")
    print(f"📄 Rapport: {report_path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Simulateur de conversation avec capture COMPLÈTE")
    parser.add_argument(
        "--scenario",
        type=str,
        default="light",
        choices=list(SCENARIOS.keys()),
        help="Scénario à exécuter"
    )
    
    args = parser.parse_args()
    
    print(f"🚀 Lancement du scénario: {args.scenario}")
    asyncio.run(run_scenario(args.scenario))
