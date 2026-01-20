#!/usr/bin/env python3
"""
🧠 HYDE SMART ROUTER - Routage intelligent avec mini-LLM (Groq 8B)
Décide rapidement entre DeepSeek V3 (économique) et Groq 70B (puissant)
"""

import logging
from typing import Tuple, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class HydeSmartRouter:
    """Routeur intelligent utilisant Groq 8B pour décider du LLM optimal"""
    
    def __init__(self):
        self.stats = {
            'total_decisions': 0,
            'deepseek_selected': 0,
            'groq_selected': 0,
            'avg_decision_time': 0.0
        }
        self.failure_cache = {}  # Cache échecs par user
    
    async def route_request(self, 
                           user_id: str, 
                           message: str, 
                           context: Dict[str, Any], 
                           history: str) -> Tuple[str, str, Dict[str, Any]]:
        """
        Décide intelligemment quel LLM utiliser via Groq 8B
        
        Args:
            user_id: ID utilisateur
            message: Message utilisateur
            context: Contexte (vision, transactions, etc.)
            history: Historique conversation
        
        Returns:
            Tuple[str, str, Dict]: ("groq-70b" | "deepseek-v3", "raison", {"tokens": ..., "cost": ..., "time": ...})
        """
        start_time = datetime.now()
        router_metrics = {'tokens': 0, 'cost': 0.0, 'time': 0.0}
        
        try:
            # Échecs récents → Groq 70B direct
            user_failures = self.failure_cache.get(user_id, 0)
            if user_failures >= 2:
                reason = f"Échecs récents DeepSeek: {user_failures}"
                logger.info(f"🎯 Routage: groq-70b (fallback) - {reason}")
                router_metrics['time'] = (datetime.now() - start_time).total_seconds()
                return "groq-70b", reason, router_metrics
            
            # Construire prompt de décision
            decision_prompt = self._build_decision_prompt(message, context, history)
            
            # Appel Groq 8B ultra-rapide
            decision, reasoning, tokens = await self._call_groq_8b_router(decision_prompt)
            
            # Calculer métriques
            elapsed = (datetime.now() - start_time).total_seconds()
            cost = self._calculate_routing_cost(tokens)
            
            router_metrics = {
                'tokens': tokens,
                'cost': cost,
                'time': elapsed
            }
            
            # Stats
            self._update_stats(decision, elapsed)
            
            logger.info(f"🎯 Routage: {decision} - Raison: {reasoning}")
            return decision, reasoning, router_metrics
            
        except Exception as e:
            logger.error(f"❌ Erreur routage HYDE: {e}")
            # Fallback sécurisé
            router_metrics['time'] = (datetime.now() - start_time).total_seconds()
            return "groq-70b", f"Erreur routage: {str(e)}", router_metrics
    
    def _build_decision_prompt(self, message: str, context: Dict, history: str) -> str:
        """Construit un prompt ultra-court pour la décision"""
        
        # Analyser contexte
        has_transactions = bool(context.get('filtered_transactions'))
        has_images = bool(context.get('detected_objects'))
        has_history = len(history.strip()) > 50
        
        prompt = f"""Tu es un routeur intelligent. Choisis le LLM optimal.

MESSAGE: "{message}"
TRANSACTIONS: {"OUI" if has_transactions else "NON"}
IMAGES: {"OUI" if has_images else "NON"}
HISTORIQUE: {"OUI" if has_history else "NON"}

LLMS:
- deepseek-v3: Économique, rapide, pour cas SIMPLES (salutations, zones, hors domaine)
- groq-70b: Puissant, coûteux, pour cas COMPLEXES (calculs, workflow, transactions)

RÈGLES STRICTES:
1. Calculs/transactions/paiements → groq-70b
2. Workflow multi-étapes (commande) → groq-70b
3. Salutations simples (Bonjour, Salut) → deepseek-v3
4. Questions zones géographiques → deepseek-v3
5. Hors domaine (météo, politique) → deepseek-v3
6. Première question commande → groq-70b
7. Contexte ambigu → groq-70b

Réponds SEULEMENT:
CHOIX: [deepseek-v3 OU groq-70b]
RAISON: [explication courte]"""

        return prompt
    
    async def _call_groq_8b_router(self, prompt: str) -> Tuple[str, str, int]:
        """Appel Groq 8B pour décision rapide"""
        try:
            from core.llm_client_groq import complete
            
            # Ancien affichage verbeux du prompt HYDE (désactivé pour éviter le bruit console)
            # MAGENTA = '\033[95m'
            # BOLD = '\033[1m'
            # RESET = '\033[0m'
            # print(f"\n{MAGENTA}{BOLD}{'='*100}{RESET}")
            # print(f"{MAGENTA}{BOLD}🌸 PROMPT ROUTEUR HYDE (LLAMA-3.1-8B-INSTANT) ({len(prompt)} caractères, ~{len(prompt)//4} tokens){RESET}")
            # print(f"{MAGENTA}{BOLD}{'='*100}{RESET}")
            # print(f"{MAGENTA}{prompt}{RESET}")
            # print(f"{MAGENTA}{BOLD}{'='*100}{RESET}\n")
            
            # Appel ultra-rapide Groq 8B
            content, token_info = await complete(
                prompt=prompt,
                model_name="llama-3.1-8b-instant",  # Le plus rapide
                max_tokens=100,
                temperature=0.0  # Déterministe
            )
            
            # Parser réponse
            decision = "groq-70b"  # Défaut sécurisé
            reasoning = "Décision par défaut"
            total_tokens = token_info.get('total_tokens', 0)
            
            lines = content.strip().split('\n')
            for line in lines:
                if line.startswith("CHOIX:"):
                    choice_text = line.replace("CHOIX:", "").strip().lower()
                    if "deepseek" in choice_text:
                        decision = "deepseek-v3"
                    elif "groq" in choice_text or "70b" in choice_text:
                        decision = "groq-70b"
                
                elif line.startswith("RAISON:"):
                    reasoning = line.replace("RAISON:", "").strip()
            
            return decision, reasoning, total_tokens
            
        except Exception as e:
            logger.error(f"❌ Erreur appel Groq 8B router: {e}")
            return "groq-70b", f"Erreur décision: {str(e)}", 0
    
    def record_success(self, user_id: str, llm_used: str):
        """Enregistre un succès"""
        if llm_used == "deepseek-v3":
            self.failure_cache[user_id] = 0  # Reset échecs
    
    def record_failure(self, user_id: str, llm_used: str):
        """Enregistre un échec"""
        if llm_used == "deepseek-v3":
            self.failure_cache[user_id] = self.failure_cache.get(user_id, 0) + 1
            logger.warning(f"⚠️ Échec DeepSeek #{self.failure_cache[user_id]} pour {user_id}")
    
    def _calculate_routing_cost(self, total_tokens: int) -> float:
        """Calcule le coût du routage avec Groq 8B"""
        # Tarifs Groq 8B (llama-3.1-8b-instant)
        # Input: $0.05 / 1M tokens
        # Output: $0.08 / 1M tokens
        # Approximation: 80% input, 20% output
        prompt_tokens = int(total_tokens * 0.8)
        completion_tokens = int(total_tokens * 0.2)
        
        input_cost = (prompt_tokens / 1_000_000) * 0.05
        output_cost = (completion_tokens / 1_000_000) * 0.08
        
        return input_cost + output_cost
    
    def _update_stats(self, decision: str, elapsed: float):
        """Met à jour les statistiques"""
        self.stats['total_decisions'] += 1
        
        if decision == "deepseek-v3":
            self.stats['deepseek_selected'] += 1
        else:
            self.stats['groq_selected'] += 1
        
        # Moyenne glissante
        total = self.stats['total_decisions']
        old_avg = self.stats['avg_decision_time']
        self.stats['avg_decision_time'] = (old_avg * (total - 1) + elapsed) / total
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du routeur"""
        total = self.stats['total_decisions']
        if total == 0:
            return self.stats
        
        return {
            **self.stats,
            'deepseek_percentage': (self.stats['deepseek_selected'] / total) * 100,
            'groq_percentage': (self.stats['groq_selected'] / total) * 100
        }

# Instance globale
hyde_router = HydeSmartRouter()
