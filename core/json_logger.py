#!/usr/bin/env python3
"""
📊 JSON LOGGER - Capture automatique des métriques en JSON
Intercepte les logs formatés et les structure en JSON pour analyse
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class JSONRequestLogger:
    """Logger qui capture et structure les requêtes en JSON"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Fichier JSON pour les métriques
        today = datetime.now().strftime('%Y%m%d')
        self.json_file = self.log_dir / f"requests_metrics_{today}.jsonl"
        
        # Buffer pour construire la requête en cours
        self.current_request = None
        self.capturing = False
    
    def start_request(self, company_id: str, user_id: str, message: str):
        """Démarre la capture d'une nouvelle requête"""
        self.current_request = {
            'timestamp': datetime.now().isoformat(),
            'company_id': company_id,
            'user_id': user_id,
            'question': message,
            'thinking': '',
            'response': '',
            'model': '',
            'routing_reason': '',
            'metrics': {
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'total_tokens': 0,
                'llm_cost': 0.0,
                'router_cost': 0.0,
                'total_cost': 0.0,
                'router_tokens': 0
            },
            'timings': {
                'routing': 0.0,
                'prompt_generation': 0.0,
                'llm_call': 0.0,
                'tools_execution': 0.0,
                'total': 0.0
            }
        }
        self.capturing = True
    
    def add_thinking(self, thinking: str):
        """Ajoute le raisonnement"""
        if self.current_request:
            self.current_request['thinking'] = thinking
    
    def add_response(self, response: str):
        """Ajoute la réponse"""
        if self.current_request:
            self.current_request['response'] = response
    
    def add_metrics(self, 
                   model: str,
                   prompt_tokens: int,
                   completion_tokens: int,
                   llm_cost: float,
                   router_cost: float = 0.0,
                   router_tokens: int = 0,
                   routing_reason: str = ''):
        """Ajoute les métriques"""
        if self.current_request:
            self.current_request['model'] = model
            self.current_request['routing_reason'] = routing_reason
            self.current_request['metrics'] = {
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'total_tokens': prompt_tokens + completion_tokens,
                'llm_cost': llm_cost,
                'router_cost': router_cost,
                'total_cost': llm_cost + router_cost,
                'router_tokens': router_tokens
            }
    
    def add_timings(self,
                   routing: float = 0.0,
                   prompt_generation: float = 0.0,
                   llm_call: float = 0.0,
                   tools_execution: float = 0.0,
                   total: float = 0.0):
        """Ajoute les timings"""
        if self.current_request:
            self.current_request['timings'] = {
                'routing': routing,
                'prompt_generation': prompt_generation,
                'llm_call': llm_call,
                'tools_execution': tools_execution,
                'total': total
            }
    
    def save_request(self):
        """Sauvegarde la requête en cours dans le fichier JSON"""
        if not self.current_request or not self.capturing:
            return
        
        try:
            # Écrire en JSONL (une ligne = un objet JSON)
            with open(self.json_file, 'a', encoding='utf-8') as f:
                json.dump(self.current_request, f, ensure_ascii=False)
                f.write('\n')
            
            logger.info(f"📊 Métriques JSON sauvegardées: {self.json_file}")
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde JSON: {e}")
        finally:
            self.current_request = None
            self.capturing = False

# Instance globale
json_logger = JSONRequestLogger()

def log_request_metrics(question: str, thinking: str, response: str, 
                        model: str, prompt_tokens: int, completion_tokens: int,
                        llm_cost: float, router_cost: float, router_tokens: int,
                        routing_reason: str, timings: Dict[str, float],
                        company_id: str, user_id: str):
    """
    Fonction helper pour logger une requête complète
    
    Usage:
        log_request_metrics(
            question="Bonjour",
            thinking="TYPE: salutation...",
            response="Salut ! 👋",
            model="deepseek-v3",
            prompt_tokens=855,
            completion_tokens=52,
            llm_cost=0.000300,
            router_cost=0.000017,
            router_tokens=306,
            routing_reason="Cas simple",
            timings={'routing': 830.58, 'llm_call': 672.45, 'total': 1504.97},
            company_id="xyz",
            user_id="user123"
        )
    """
    try:
        json_logger.start_request(company_id, user_id, question)
        json_logger.add_thinking(thinking)
        json_logger.add_response(response)
        json_logger.add_metrics(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            llm_cost=llm_cost,
            router_cost=router_cost,
            router_tokens=router_tokens,
            routing_reason=routing_reason
        )
        json_logger.add_timings(
            routing=timings.get('routing', 0.0),
            prompt_generation=timings.get('prompt_generation', 0.0),
            llm_call=timings.get('llm_call', 0.0),
            tools_execution=timings.get('tools_execution', 0.0),
            total=timings.get('total', 0.0)
        )
        json_logger.save_request()
    except Exception as e:
        logger.error(f"❌ Erreur log_request_metrics: {e}")
