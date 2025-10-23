#!/usr/bin/env python3
"""
🧪 TEST AVEC CAPTURE LOGS - Lance le test et capture TOUS les logs serveur

Ce script:
1. Lit les logs serveur en temps réel depuis un fichier
2. Lance le test de conversation
3. Associe chaque log à son tour de conversation
4. Génère un rapport JSON COMPLET

Usage:
    # Terminal 1: Lancer le serveur avec capture
    python tests/capture_server_logs.py --output logs/current_server.log
    
    # Terminal 2: Lancer le test
    python tests/run_test_with_logs.py --scenario light --log-file logs/current_server.log
"""

import asyncio
import json
import time
import re
import os
from typing import List, Dict, Any
from datetime import datetime
import sys
from pathlib import Path

# Ajouter le path parent pour imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Configuration test
TEST_COMPANY_ID = "4OS4yFcf2LZwxhKojbAVbKuVuSdb"

# ✅ GÉNÉRER UN USER ID UNIQUE À CHAQUE EXÉCUTION
import uuid
TEST_USER_ID = f"test_simulator_{uuid.uuid4().hex[:8]}"
print(f"🆔 User ID unique généré: {TEST_USER_ID}")


class LogFileReader:
    """
    📖 Lecteur de fichier de logs en temps réel
    """
    
    def __init__(self, log_file: str):
        self.log_file = log_file
        self.logs = []
        self.last_position = 0
        
    def read_new_logs(self) -> List[str]:
        """Lit les nouvelles lignes depuis la dernière lecture"""
        new_logs = []
        
        if not os.path.exists(self.log_file):
            return new_logs
        
        try:
            with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(self.last_position)
                new_lines = f.readlines()
                self.last_position = f.tell()
                
                for line in new_lines:
                    line = line.strip()
                    if line:
                        log_entry = {
                            "timestamp": datetime.now().isoformat(),
                            "content": line
                        }
                        self.logs.append(log_entry)
                        new_logs.append(log_entry)
        
        except Exception as e:
            print(f"⚠️ Erreur lecture logs: {e}")
        
        return new_logs
    
    def get_logs_between(self, start_time: str, end_time: str) -> List[Dict]:
        """Récupère les logs entre deux timestamps"""
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)
        
        matching_logs = []
        for log in self.logs:
            log_dt = datetime.fromisoformat(log["timestamp"])
            if start_dt <= log_dt <= end_dt:
                matching_logs.append(log)
        
        return matching_logs


class FullLogTracker:
    """
    📊 Tracker COMPLET avec logs serveur
    """
    
    def __init__(self, scenario_name: str, log_reader: LogFileReader):
        self.scenario_name = scenario_name
        self.log_reader = log_reader
        self.turns = []
        self.total_time_ms = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        self.start_time = None
        self.end_time = None
        
    def start_conversation(self):
        """Démarre le tracking"""
        self.start_time = time.time()
        print("\n" + "="*80)
        print(f"🧪 DÉBUT TEST AVEC LOGS: {self.scenario_name}")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")
    
    def add_turn(
        self,
        turn_number: int,
        user_message: str,
        llm_response: str,
        full_api_response: Dict,
        turn_start_time: str,
        turn_end_time: str,
        execution_time_ms: int,
        tokens_used: Dict,
        cost: float
    ):
        """Enregistre un tour avec logs serveur"""
        
        # Récupérer les logs pour ce tour
        server_logs = self.log_reader.get_logs_between(turn_start_time, turn_end_time)
        
        turn_data = {
            "turn": turn_number,
            "timestamp": turn_end_time,
            "user_message": user_message,
            "llm_response": llm_response,
            "full_api_response": full_api_response,
            "server_logs": server_logs,
            "server_logs_count": len(server_logs),
            "execution_time_ms": execution_time_ms,
            "tokens": tokens_used,
            "cost_usd": cost
        }
        
        self.turns.append(turn_data)
        self.total_time_ms += execution_time_ms
        self.total_tokens += tokens_used.get('total', 0)
        self.total_cost += cost
        
        # Display
        self._print_turn_details(turn_data)
    
    def _print_turn_details(self, turn: dict):
        """Affiche les détails d'un tour"""
        tokens = turn.get('tokens', {})
        total_tokens = tokens.get('total', 0)
        log_count = turn.get('server_logs_count', 0)
        
        print(f"\n{'='*80}")
        print(f"🔄 TOUR {turn['turn']} | ⏱️ {turn['execution_time_ms']:.0f}ms | 🔤 {total_tokens}t | 💰 ${turn['cost_usd']:.4f} | 📋 {log_count} logs")
        print("="*80)
        print(f"👤 CLIENT: {turn['user_message'][:80]}")
        print(f"\n🤖 ASSISTANT: {turn['llm_response'][:200]}")
        
        # Afficher thinking
        api_resp = turn.get('full_api_response', {})
        thinking = api_resp.get('thinking', '')
        if thinking:
            print(f"\n🧠 THINKING: {len(thinking)} chars")
            print(f"   {thinking[:150]}...")
        else:
            print(f"\n⚠️ THINKING: VIDE")
        
        # Afficher quelques logs clés
        if log_count > 0:
            print(f"\n📋 LOGS SERVEUR (premiers 5):")
            for i, log in enumerate(turn['server_logs'][:5], 1):
                content = log['content'][:100]
                print(f"   {i}. {content}")
        
        print("\n" + "="*80 + "\n")
    
    def end_conversation(self):
        """Termine la conversation"""
        self.end_time = time.time()
    
    def save_full_report(self, output_path: str = None):
        """Sauvegarde le rapport COMPLET"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"tests/reports/FULL_{self.scenario_name}_{timestamp}.json"
        
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
            "total_server_logs": len(self.log_reader.logs),
            "turns": self.turns,
            "all_server_logs": self.log_reader.logs
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 RAPPORT COMPLET sauvegardé: {output_path}")
        print(f"📊 Taille: {os.path.getsize(output_path) / 1024:.1f} KB")
        print(f"📋 Logs capturés: {len(self.log_reader.logs)}")
        return output_path
    
    def print_summary(self):
        """Affiche le résumé"""
        print("\n" + "="*80)
        print(f"📊 RÉSUMÉ TEST: {self.scenario_name}")
        print("="*80 + "\n")
        
        duration_s = (self.end_time - self.start_time) if self.end_time else 0
        print(f"⏱️  TEMPS:")
        print(f"   Total: {duration_s:.1f}s")
        print(f"   Nombre de tours: {len(self.turns)}")
        
        print(f"\n💰 COÛTS:")
        print(f"   Tokens: {self.total_tokens}")
        print(f"   Coût: ${self.total_cost:.4f}")
        
        print(f"\n📋 LOGS:")
        print(f"   Logs serveur: {len(self.log_reader.logs)}")
        
        print("\n" + "="*80 + "\n")


async def execute_chat_turn(user_message, log_reader: LogFileReader) -> Dict[str, Any]:
    """Exécute un tour avec capture de logs"""
    try:
        import httpx
        
        turn_start_time = datetime.now().isoformat()
        start_time = time.time()
        
        # Lire les logs avant l'appel
        log_reader.read_new_logs()
        
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
        
        # Appel API
        payload = {
            "company_id": TEST_COMPANY_ID,
            "user_id": TEST_USER_ID,
            "message": message_text,
            "botlive_enabled": False
        }
        
        if images:
            payload["images"] = images
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "http://127.0.0.1:8002/chat",
                json=payload
            )
            full_api_response = response.json()
        
        execution_time_ms = (time.time() - start_time) * 1000
        turn_end_time = datetime.now().isoformat()
        
        # Lire les nouveaux logs après l'appel
        await asyncio.sleep(0.5)  # Attendre que les logs soient écrits
        log_reader.read_new_logs()
        
        # Extraire infos
        response_text = full_api_response.get('response', '')
        
        # Calculer tokens
        prompt_tokens = len(message_text.split())
        completion_tokens = len(response_text.split())
        total_tokens = prompt_tokens + completion_tokens
        cost = total_tokens * 0.00000079
        
        tokens_used = {
            "prompt": prompt_tokens,
            "completion": completion_tokens,
            "total": total_tokens
        }
        
        return {
            "response": response_text,
            "full_api_response": full_api_response,
            "turn_start_time": turn_start_time,
            "turn_end_time": turn_end_time,
            "execution_time_ms": execution_time_ms,
            "tokens": tokens_used,
            "cost": cost
        }
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return {
            "response": f"ERREUR: {str(e)}",
            "full_api_response": {"error": str(e)},
            "turn_start_time": datetime.now().isoformat(),
            "turn_end_time": datetime.now().isoformat(),
            "execution_time_ms": 0,
            "tokens": {"prompt": 0, "completion": 0, "total": 0},
            "cost": 0.0
        }


# Scénarios
SCENARIOS = {
    "light": {
        "name": "light_conversation_simple",
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


async def run_scenario(scenario_key: str, log_file: str):
    """Exécute un scénario avec capture de logs"""
    if scenario_key not in SCENARIOS:
        print(f"❌ Scénario inconnu: {scenario_key}")
        return
    
    # ✅ VIDER TOUS LES CACHES AVANT LE TEST
    clear_all_caches()
    
    scenario = SCENARIOS[scenario_key]
    log_reader = LogFileReader(log_file)
    tracker = FullLogTracker(scenario["name"], log_reader)
    
    tracker.start_conversation()
    
    for turn_num, message in enumerate(scenario["messages"], 1):
        print(f"⏳ Exécution tour {turn_num}...")
        
        result = await execute_chat_turn(message, log_reader)
        
        # Extraire message texte
        if isinstance(message, dict):
            message_text = message.get("text", "")
        else:
            message_text = message
        
        tracker.add_turn(
            turn_number=turn_num,
            user_message=message_text,
            llm_response=result["response"],
            full_api_response=result["full_api_response"],
            turn_start_time=result["turn_start_time"],
            turn_end_time=result["turn_end_time"],
            execution_time_ms=result["execution_time_ms"],
            tokens_used=result["tokens"],
            cost=result["cost"]
        )
        
        await asyncio.sleep(1)
    
    tracker.end_conversation()
    tracker.print_summary()
    tracker.save_full_report()
    
    print(f"\n✅ Test terminé!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test avec capture de logs serveur")
    parser.add_argument("--scenario", type=str, default="light", choices=list(SCENARIOS.keys()))
    parser.add_argument("--log-file", type=str, default="logs/current_server.log", help="Fichier de logs serveur")
    
    args = parser.parse_args()
    
    # Vérifier que le fichier de logs existe
    if not os.path.exists(args.log_file):
        print(f"⚠️ ATTENTION: Le fichier de logs n'existe pas encore: {args.log_file}")
        print(f"📝 Assurez-vous que le serveur est lancé avec:")
        print(f"   python tests/capture_server_logs.py --output {args.log_file}")
        print(f"\n🔄 Tentative de lecture quand même...\n")
    
    asyncio.run(run_scenario(args.scenario, args.log_file))
