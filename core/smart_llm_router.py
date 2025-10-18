#!/usr/bin/env python3
"""
🧠 SMART LLM ROUTER - Système hybride DeepSeek V3 + Groq 70B
Routage intelligent basé sur la complexité des requêtes
"""

import re
import logging
from typing import Dict, Any, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SmartLLMRouter:
    def __init__(self):
        self.failure_cache = {}  # Cache échecs par user_id
        self.performance_stats = {}
        self.complexity_threshold = 20  # Seuil adaptatif
        
    def route_request(self, user_id: str, message: str, context: Dict, history: str) -> Tuple[str, str]:
        """
        Détermine quel LLM utiliser et retourne (llm_choice, reason)
        
        Returns:
            Tuple[str, str]: ("groq-70b" | "deepseek-v3", "raison")
        """
        try:
            # Calcul score de complexité
            complexity_score = self._calculate_complexity_score(message, context, history)
            
            # Historique échecs utilisateur
            user_failures = self.failure_cache.get(user_id, 0)
            
            # Décision finale
            if complexity_score >= self.complexity_threshold or user_failures >= 2:
                reason = f"Complexité: {complexity_score} (seuil: {self.complexity_threshold})"
                if user_failures >= 2:
                    reason += f" + Échecs récents: {user_failures}"
                return "groq-70b", reason
            else:
                return "deepseek-v3", f"Cas simple (score: {complexity_score})"
                
        except Exception as e:
            logger.error(f"Erreur routage: {e}")
            return "groq-70b", "Erreur - Fallback sécurisé"
    
    def _calculate_complexity_score(self, message: str, context: Dict, history: str) -> int:
        """Calcule le score de complexité d'une requête"""
        score = 0
        message_lower = message.lower()
        
        # ═══ FACTEURS AUGMENTANT COMPLEXITÉ ═══
        
        # 1. Calculs mathématiques (CRITIQUE)
        if self._has_money_calculations(context, message):
            score += 40
            logger.debug("Calculs détectés: +40")
        
        # 2. Workflow progression
        if self._is_workflow_progression(history):
            score += 30
            logger.debug("Workflow progression: +30")
        
        # 3. Images avec données financières
        if self._requires_image_analysis(context):
            score += 25
            logger.debug("Analyse image complexe: +25")
        
        # 4. Contexte ambigu
        if self._has_ambiguous_words(message):
            score += 20
            logger.debug("Contexte ambigu: +20")
        
        # 5. Première interaction critique
        if self._is_critical_first_contact(message, history):
            score += 15
            logger.debug("Premier contact critique: +15")
        
        # ═══ FACTEURS RÉDUISANT COMPLEXITÉ ═══
        
        # 1. Salutations simples
        if self._is_simple_greeting(message):
            score -= 30
            logger.debug("Salutation simple: -30")
        
        # 2. Hors domaine évident
        if self._is_clearly_out_of_domain(message):
            score -= 25
            logger.debug("Hors domaine: -25")
        
        # 3. Zones géographiques connues
        if self._is_known_location(message):
            score -= 20
            logger.debug("Zone géographique: -20")
        
        # 4. Confirmations simples
        if self._is_yes_no_response(message):
            score -= 15
            logger.debug("Confirmation simple: -15")
        
        logger.debug(f"Score complexité final: {score}")
        return score
    
    def _has_money_calculations(self, context: Dict, message: str) -> bool:
        """Détecte si des calculs financiers sont nécessaires"""
        # Transactions détectées
        if context.get('filtered_transactions'):
            return True
        
        # Montants dans le message
        if re.search(r'\d+\s*(fcfa|f)', message.lower()):
            return True
        
        # Comparaisons nécessaires
        if context.get('expected_deposit'):
            return True
        
        return False
    
    def _is_workflow_progression(self, history: str) -> bool:
        """Détecte si on est dans une progression workflow"""
        critical_keywords = [
            r"photo reçue",
            r"confirmes",
            r"validé.*fcfa",
            r"commune",
            r"numéro",
            r"commande ok"
        ]
        
        return any(re.search(keyword, history, re.IGNORECASE) 
                  for keyword in critical_keywords)
    
    def _requires_image_analysis(self, context: Dict) -> bool:
        """Détecte si analyse d'image complexe nécessaire"""
        detected_objects = context.get('detected_objects', [])
        
        # Images avec montants
        if any('montant:' in str(obj) for obj in detected_objects):
            return True
        
        # Images produits avec validation paiement
        if detected_objects and context.get('expected_deposit'):
            return True
        
        return False
    
    def _has_ambiguous_words(self, message: str) -> bool:
        """Détecte des mots indiquant un contexte ambigu"""
        ambiguous_patterns = [
            r'(changer|modifier|plutôt|finalement)',
            r'(correction|erreur|problème)',
            r'(je veux|je préfère)',
            r'(annuler|remplacer)'
        ]
        
        return any(re.search(pattern, message.lower()) 
                  for pattern in ambiguous_patterns)
    
    def _is_critical_first_contact(self, message: str, history: str) -> bool:
        """Détecte si c'est un premier contact critique"""
        return len(history.strip()) == 0 and len(message) > 20
    
    def _is_simple_greeting(self, message: str) -> bool:
        """Détecte les salutations simples"""
        simple_greetings = [
            r'^(salut|bonjour|hello|hi)$',
            r'^(bonsoir|bonne nuit)$'
        ]
        
        return any(re.search(pattern, message.lower()) 
                  for pattern in simple_greetings)
    
    def _is_clearly_out_of_domain(self, message: str) -> bool:
        """Détecte les questions hors domaine évidentes"""
        out_of_domain_patterns = [
            r'(temps|météo|climat)',
            r'(président|politique|gouvernement)',
            r'(sport|football|basket)',
            r'(actualité|news|journal)',
            r'(santé|médecin|maladie)',
            r'(école|université|étude)'
        ]
        
        return any(re.search(pattern, message.lower()) 
                  for pattern in out_of_domain_patterns)
    
    def _is_known_location(self, message: str) -> bool:
        """Détecte les zones géographiques connues"""
        known_locations = [
            r'(yopougon|cocody|plateau|adjamé)',
            r'(abobo|marcory|koumassi|treichville)',
            r'(angré|riviera|andokoua)',
            r'(port-bouët|attécoubé)',
            r'(bingerville|songon|anyama)',
            r'(brofodoumé|grand-bassam|dabou)'
        ]
        
        return any(re.search(location, message.lower()) 
                  for location in known_locations)
    
    def _is_yes_no_response(self, message: str) -> bool:
        """Détecte les réponses simples oui/non"""
        simple_responses = [
            r'^(oui|non|ok|okay)$',
            r'^(merci|thanks)$',
            r'^(d\'accord|dacord)$'
        ]
        
        return any(re.search(pattern, message.lower()) 
                  for pattern in simple_responses)
    
    def record_success(self, user_id: str, llm_used: str):
        """Enregistre un succès"""
        if llm_used == "deepseek-v3":
            # Reset échecs si DeepSeek réussit
            self.failure_cache[user_id] = 0
        
        # Mise à jour stats
        if user_id not in self.performance_stats:
            self.performance_stats[user_id] = {
                'deepseek_v3_successes': 0,
                'groq_70b_successes': 0,
                'deepseek_v3_failures': 0,
                'groq_70b_failures': 0,
                'total_requests': 0
            }
        
        # Normaliser le nom du LLM pour la clé
        llm_key = llm_used.replace("-", "_")
        success_key = f'{llm_key}_successes'
        
        # S'assurer que la clé existe
        if success_key not in self.performance_stats[user_id]:
            self.performance_stats[user_id][success_key] = 0
        
        self.performance_stats[user_id][success_key] += 1
        self.performance_stats[user_id]['total_requests'] += 1
    
    def record_failure(self, user_id: str, llm_used: str):
        """Enregistre un échec"""
        if llm_used == "deepseek-v3":
            # Incrémenter échecs DeepSeek
            self.failure_cache[user_id] = self.failure_cache.get(user_id, 0) + 1
            logger.warning(f"Échec DeepSeek pour {user_id}: {self.failure_cache[user_id]}")
        
        # Mise à jour stats
        if user_id not in self.performance_stats:
            self.performance_stats[user_id] = {
                'deepseek_v3_successes': 0,
                'groq_70b_successes': 0,
                'deepseek_v3_failures': 0,
                'groq_70b_failures': 0,
                'total_requests': 0
            }
        
        # Normaliser le nom du LLM pour la clé
        llm_key = llm_used.replace("-", "_")
        failure_key = f'{llm_key}_failures'
        
        # S'assurer que la clé existe
        if failure_key not in self.performance_stats[user_id]:
            self.performance_stats[user_id][failure_key] = 0
        
        self.performance_stats[user_id][failure_key] += 1
        self.performance_stats[user_id]['total_requests'] += 1
    
    def get_stats(self) -> Dict:
        """Retourne les statistiques de performance"""
        total_stats = {
            'total_users': len(self.performance_stats),
            'deepseek_success_rate': 0,
            'groq_success_rate': 0,
            'cost_savings': 0
        }
        
        if self.performance_stats:
            deepseek_successes = sum(stats.get('deepseek_successes', 0) 
                                   for stats in self.performance_stats.values())
            deepseek_total = sum(stats.get('deepseek_successes', 0) + stats.get('deepseek_failures', 0)
                               for stats in self.performance_stats.values())
            
            if deepseek_total > 0:
                total_stats['deepseek_success_rate'] = deepseek_successes / deepseek_total
        
        return total_stats

# Instance globale
smart_router = SmartLLMRouter()
