#!/usr/bin/env python3
"""
🧪 CONVERSATION SIMULATOR - Test Système Chatbot Complet

Simule des conversations client réelles pour évaluer:
- Capacité de qualification
- Gestion des objections
- Orientation vers l'achat
- Performance (temps, coûts)
- Qualité du thinking LLM

Usage:
    python tests/conversation_simulator.py --scenario light
    python tests/conversation_simulator.py --scenario medium
    python tests/conversation_simulator.py --scenario hardcore
"""

import asyncio
import json
import time
import re
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
TEST_USER_ID = "test_client_simulator"
TEST_COMPANY_NAME = "Rue du Grossiste"


class ConversationTracker:
    """
    📊 Tracker complet d'une conversation de test
    """
    
    def __init__(self, scenario_name: str):
        self.scenario_name = scenario_name
        self.turns = []
        self.total_time_ms = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        self.start_time = None
        self.end_time = None
        
    def start_conversation(self):
        """Démarre le tracking de conversation"""
        self.start_time = time.time()
        print("\n" + "="*80)
        print(f"🧪 DÉBUT TEST: {self.scenario_name}")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")
    
    def add_turn(
        self,
        turn_number: int,
        user_message: str,
        llm_response: str,
        thinking_data: Dict,
        contexts_sent: List[Dict],
        execution_time_ms: int,
        tokens_used: Dict,
        cost: float
    ):
        """
        Enregistre un tour de conversation
        """
        turn_data = {
            "turn": turn_number,
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "llm_response": llm_response,
            "thinking": thinking_data,
            "contexts": contexts_sent,
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
        """Affiche les détails d'un tour de conversation (VERSION COMPACTE + VALIDATION)"""
        tokens = turn.get('tokens', {})
        total_tokens = tokens.get('total', 0) if isinstance(tokens, dict) else tokens
        print(f"\n{'='*80}")
        print(f"🔄 TOUR {turn['turn']} | ⏱️ {turn['execution_time_ms']:.0f}ms | 🔤 {total_tokens}t | 💰 ${turn['cost_usd']:.4f}")
        print(f"{'='*80}")
        
        # 1. Question Client (compacte)
        user_msg = turn['user_message']
        if isinstance(user_msg, dict):
            user_msg = user_msg.get('text', str(user_msg))
        print(f"👤 CLIENT: {user_msg[:100]}{'...' if len(str(user_msg)) > 100 else ''}")
        
        # 2. Thinking LLM (DÉTAILLÉ)
        thinking = turn['thinking']
        if thinking and thinking.get('has_thinking'):
            print(f"\n🧠 THINKING LLM:")
            
            # Données collectées
            deja_collecte = thinking.get('deja_collecte')
            if deja_collecte:
                print(f"   📋 Données collectées:")
                for line in deja_collecte.split('\n')[:5]:
                    if line.strip():
                        print(f"      {line.strip()}")
            
            # Confiance + Complétude
            confiance = thinking.get('confiance_globale')
            completude = thinking.get('completude')
            if confiance or completude:
                print(f"   📊 Confiance: {confiance}% | Complétude: {completude}")
            
            # Prochaine étape
            prochaine_etape = thinking.get('prochaine_etape')
            if prochaine_etape:
                print(f"   ➡️ Prochaine: {prochaine_etape}")
        
        # 3. Réponse LLM (COMPLÈTE)
        llm_response = turn.get('llm_response', '')
        # Gérer si dict ou string
        if isinstance(llm_response, dict):
            llm_response = llm_response.get('response', str(llm_response))
        response_clean = self._clean_response(llm_response)
        print(f"\n🤖 ASSISTANT: {response_clean}")
        
        # 4. VALIDATION ANTI-HALLUCINATION (NOUVEAU)
        validation = turn.get('validation')
        if validation:
            print(f"\n🛡️ VALIDATION:")
            if validation.get('valid'):
                print(f"   ✅ Aucune hallucination détectée")
            else:
                print(f"   ❌ HALLUCINATIONS DÉTECTÉES:")
                for error in validation.get('errors', []):
                    print(f"      • {error}")
                if validation.get('should_regenerate'):
                    print(f"   🔄 Régénération effectuée")
        
        # 5. Méthode de recherche
        print(f"\n🔍 Méthode: {turn.get('search_method', 'N/A')}")
    
    def _clean_response(self, response: str) -> str:
        """Nettoie la réponse des balises <thinking> et <response>"""
        # Supprimer <thinking>...</thinking>
        response = re.sub(r'<thinking>.*?</thinking>', '', response, flags=re.DOTALL)
        
        # Extraire <response> si présent
        response_match = re.search(r'<response>(.*?)</response>', response, re.DOTALL)
        if response_match:
            response = response_match.group(1)
        
        return response.strip()
    
    def end_conversation(self):
        """Termine le tracking et affiche le résumé"""
        self.end_time = time.time()
        total_duration = (self.end_time - self.start_time) * 1000
        
        print("\n" + "="*80)
        print(f"📊 RÉSUMÉ TEST: {self.scenario_name}")
        print("="*80)
        
        print(f"\n⏱️  TEMPS:")
        print(f"   Total conversation: {total_duration:.0f}ms ({total_duration/1000:.1f}s)")
        print(f"   Temps RAG cumulé: {self.total_time_ms}ms")
        print(f"   Nombre de tours: {len(self.turns)}")
        print(f"   Temps moyen/tour: {self.total_time_ms/len(self.turns) if self.turns else 0:.0f}ms")
        
        print(f"\n💰 COÛTS:")
        print(f"   Tokens totaux: {self.total_tokens}")
        print(f"   Coût total: ${self.total_cost:.4f}")
        print(f"   Coût moyen/tour: ${self.total_cost/len(self.turns) if self.turns else 0:.4f}")
        
        print(f"\n📈 QUALIFICATION:")
        if self.turns:
            last_turn = self.turns[-1]
            last_thinking = last_turn.get('thinking', {})
            
            confiance = last_thinking.get('confiance', {})
            print(f"   Confiance finale: {confiance.get('score', 0)}%")
            
            progression = last_thinking.get('progression', {})
            print(f"   Complétude: {progression.get('completude', 'N/A')}")
            
            deja_collecte = last_thinking.get('deja_collecte', {})
            collecte_count = sum(1 for v in deja_collecte.values() if v not in [None, 'null', ''])
            print(f"   Données collectées: {collecte_count}/5")
        
        print("\n" + "="*80 + "\n")
    
    def save_report(self, output_path: str = None):
        """
        Sauvegarde le rapport complet en JSON
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"tests/reports/{self.scenario_name}_{timestamp}.json"
        
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
            "turns": self.turns
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"📄 Rapport sauvegardé: {output_path}")
        return output_path


async def execute_chat_turn(user_message) -> Dict[str, Any]:
    """
    Exécute un tour de conversation et retourne les métriques
    
    Args:
        user_message: str OU dict {"text": "...", "image_url": "..."}
    """
    try:
        import httpx
        
        start_time = time.time()
        
        # Gérer message avec ou sans image
        if isinstance(user_message, dict):
            message_text = user_message.get("text", "")
            image_url = user_message.get("image_url")
            
            # Utiliser l'URL directement
            images = [image_url] if image_url else []
            if image_url:
                print(f"📸 [IMAGE_URL] {image_url[:80]}...")
        else:
            message_text = user_message
            images = []
        
        # Appel API HTTP (comme en production)
        payload = {
            "company_id": TEST_COMPANY_ID,
            "user_id": TEST_USER_ID,
            "message": message_text,
            "botlive_enabled": False  # Désactiver Botlive, laisser le RAG gérer automatiquement
        }
        
        if images:
            payload["images"] = images
        
        # Appel HTTP au serveur local avec retry
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:  # Augmenté à 120s
                    response = await client.post(
                        "http://127.0.0.1:8002/chat",
                        json=payload
                    )
                    result = response.json()
                    print(f"🔍 [DEBUG] Clés dans result: {list(result.keys())}")
                    print(f"🔍 [DEBUG] Thinking présent: {'thinking' in result}")
                    if 'thinking' in result:
                        print(f"🔍 [DEBUG] Taille thinking: {len(result['thinking'])} chars")
                    break  # Succès, sortir de la boucle
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ Tentative {attempt + 1}/{max_retries} échouée: {e}")
                    print(f"⏳ Retry dans {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Backoff exponentiel
                else:
                    raise  # Dernière tentative, propager l'erreur
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        # Extraire thinking
        thinking_data = {}
        response_text = result.get('response', '')
        
        # S'assurer que response_text est une chaîne
        if not isinstance(response_text, str):
            response_text = str(response_text) if response_text else ''
        
        thinking_match = re.search(r'<thinking>(.*?)</thinking>', response_text, re.DOTALL)
        if thinking_match:
            thinking_raw = thinking_match.group(1).strip()
            # Parser le thinking YAML (pas JSON)
            try:
                # Extraire sections clés du thinking
                thinking_data = {
                    "raw": thinking_raw[:1000],  # Garder plus de texte
                    "has_thinking": True
                }
                
                # Extraire deja_collecte (PHASE 2)
                deja_match = re.search(r'deja_collecte:\s*\n(.*?)(?=nouvelles_donnees:|PHASE|$)', thinking_raw, re.DOTALL)
                if deja_match:
                    deja_text = deja_match.group(1).strip()
                    thinking_data["deja_collecte"] = deja_text
                
                # Extraire confiance_globale (PHASE 3)
                confiance_match = re.search(r'confiance_globale:\s*(\d+)', thinking_raw)
                if confiance_match:
                    thinking_data["confiance_globale"] = int(confiance_match.group(1))
                
                # Extraire completude (PHASE 5)
                completude_match = re.search(r'completude:\s*["\']?(\d+/\d+)["\']?', thinking_raw)
                if completude_match:
                    thinking_data["completude"] = completude_match.group(1)
                
                # Extraire prochaine_etape (PHASE 5)
                etape_match = re.search(r'prochaine_etape:\s*["\']([^"\']+)["\']', thinking_raw)
                if etape_match:
                    thinking_data["prochaine_etape"] = etape_match.group(1)
                
            except Exception as e:
                # Fallback si parsing échoue
                thinking_data = {
                    "raw": thinking_raw[:500],
                    "parse_error": str(e),
                    "has_thinking": True
                }
        else:
            thinking_data = {"has_thinking": False}
        
        # Extraire contextes (approximatif depuis result)
        contexts_sent = []
        context_used = result.get('context_used', '')
        if context_used:
            # Simuler extraction de contextes
            contexts_sent.append({
                "type": "context",
                "content": context_used[:200]
            })
        
        # Estimation tokens (approximatif)
        # Gérer user_message dict ou str
        if isinstance(user_message, dict):
            user_text = user_message.get("text", "")
        else:
            user_text = user_message
        
        prompt_tokens = len(user_text.split()) * 1.3 + len(context_used.split()) * 1.3
        completion_tokens = len(response_text.split()) * 1.3
        total_tokens = int(prompt_tokens + completion_tokens)
        
        tokens_used = {
            "prompt": int(prompt_tokens),
            "completion": int(completion_tokens),
            "total": total_tokens
        }
        
        # Estimation coût (Groq Llama 70B: $0.79/1M tokens)
        cost = (total_tokens / 1_000_000) * 0.79
        
        # Extraire validation si présente
        validation_data = result.get('validation', {})
        
        return {
            "response": result.get('response', ''),
            "thinking": thinking_data,
            "contexts": contexts_sent,
            "execution_time_ms": execution_time_ms,
            "tokens": tokens_used,
            "cost": cost,
            "search_method": result.get('search_method', 'unknown'),
            "validation": validation_data,  
            "success": True
        }
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return {
            "response": f"[ERREUR: {str(e)}]",
            "thinking": {},
            "contexts": [],
            "execution_time_ms": 0,
            "tokens": {"total": 0},
            "cost": 0.0,
            "success": False
        }


async def run_scenario(scenario: Dict[str, Any]):
    """
    Exécute un scénario de test complet
    """
    tracker = ConversationTracker(scenario['name'])
    tracker.start_conversation()
    
    for turn_num, user_message in enumerate(scenario['messages'], 1):
        print(f"⏳ Exécution tour {turn_num}...")
        
        result = await execute_chat_turn(user_message)
        
        if not result['success']:
            print(f"❌ Tour {turn_num} échoué, arrêt du test")
            break
        
        # Formater user_message pour affichage
        display_message = user_message
        if isinstance(user_message, dict):
            display_message = user_message.get("text", "")
            if user_message.get("image"):
                display_message += f" [📸 Image: {os.path.basename(user_message['image'])}]"
        
        tracker.add_turn(
            turn_number=turn_num,
            user_message=display_message,
            llm_response=result['response'],
            thinking_data=result['thinking'],
            contexts_sent=result['contexts'],
            execution_time_ms=result['execution_time_ms'],
            tokens_used=result['tokens'],
            cost=result['cost']
        )
        
        # Pause entre tours (simulation temps de réflexion client)
        await asyncio.sleep(1)
    
    tracker.end_conversation()
    report_path = tracker.save_report()
    
    return tracker, report_path


# ============================================================================
# SCENARIOS DE TEST
# ============================================================================

# Sera chargé depuis fichier externe
SCENARIOS = {}


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="🧪 Simulateur de conversations client")
    parser.add_argument("--scenario", type=str, required=True, 
                        choices=["micro", "light", "medium", "hardcore"],
                        help="Type de scénario à exécuter")
    parser.add_argument("--save-report", action="store_true",
                        help="Sauvegarder rapport JSON")
    
    args = parser.parse_args()
    
    # Charger scénarios
    from tests.test_scenarios import SCENARIOS
    
    scenario = SCENARIOS.get(args.scenario)
    
    if not scenario:
        print(f"❌ Scénario '{args.scenario}' non trouvé")
        sys.exit(1)
    
    # Run
    tracker, report_path = asyncio.run(run_scenario(scenario))
    
    print(f"\n✅ Test terminé!")
    if args.save_report:
        print(f"📄 Rapport: {report_path}")
