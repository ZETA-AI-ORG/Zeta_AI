"""
🛡️ SYSTÈME GUARDIAN HYBRIDE - VOTRE VISION OPTIMISÉE
Combine votre système rapide + mini-LLM sentinelle pour performance ET précision
"""

import hashlib
import time
import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from core.advanced_hallucination_guard import AdvancedHallucinationGuard
from core.llm_client import GroqLLMClient

logger = logging.getLogger(__name__)

@dataclass
class GuardianDecision:
    """Résultat de la décision du système guardian"""
    decision: str  # "ACCEPT" ou "REJECT"
    confidence: float
    method: str  # "fast_guard", "llm_judge", "consensus"
    reason: str
    latency_ms: float
    cost_estimate: float = 0.0

class MiniLLMJudge:
    """
    🧠 MINI-LLM SENTINELLE - VOTRE IDÉE ORIGINALE
    Juge intelligent pour les cas ambigus
    """
    
    def __init__(self):
        self.llm_client = GroqLLMClient()
        self.judgment_cache = {}
        self.cache_ttl = 3600  # 1 heure
        
    def create_judge_prompt(self, query: str, ai_response: str, context: str) -> str:
        """Prompt optimisé pour le juge LLM"""
        return f"""Tu es un détecteur d'hallucinations expert et sévère.

MISSION: Analyser si la réponse LLM est FIDÈLE aux documents fournis.

QUESTION UTILISATEUR:
{query}

RÉPONSE LLM À JUGER:
{ai_response}

DOCUMENTS DE RÉFÉRENCE:
{context[:800]}

ANALYSE REQUISE:
1. Les FAITS dans la réponse sont-ils dans les documents ?
2. Les CHIFFRES/PRIX sont-ils exacts ?
3. La réponse invente-t-elle des détails non mentionnés ?
4. Y a-t-il des affirmations non supportées ?

DÉCISION: Réponds UNIQUEMENT par:
- "ACCEPTER" si la réponse est fidèle aux documents
- "REJETER: [raison courte]" si elle contient des erreurs/inventions

Sois STRICT - en cas de doute, REJETER."""

    async def evaluate_response(self, query: str, ai_response: str, context: str) -> Dict[str, Any]:
        """Évaluation par mini-LLM juge"""
        start_time = time.time()
        
        # Vérifier le cache
        cache_key = hashlib.md5(f"{query}_{ai_response}_{context[:100]}".encode()).hexdigest()
        
        if cache_key in self.judgment_cache:
            cached = self.judgment_cache[cache_key]
            if time.time() - cached['timestamp'] < self.cache_ttl:
                logger.info("[LLM_JUDGE] 🎯 Cache hit")
                return cached['result']
        
        try:
            # Appel du juge LLM
            judge_prompt = self.create_judge_prompt(query, ai_response, context)
            judge_response = await self.llm_client.generate_response(judge_prompt)
            
            # Analyser la décision
            is_accepted = "ACCEPTER" in judge_response.upper()
            reason = judge_response.strip()
            
            latency = (time.time() - start_time) * 1000
            
            result = {
                'decision': 'ACCEPT' if is_accepted else 'REJECT',
                'confidence': 0.9 if is_accepted else 0.1,
                'reason': reason,
                'latency_ms': latency,
                'raw_response': judge_response
            }
            
            # Mise en cache
            self.judgment_cache[cache_key] = {
                'result': result,
                'timestamp': time.time()
            }
            
            logger.info(f"[LLM_JUDGE] Décision: {result['decision']} en {latency:.1f}ms")
            return result
            
        except Exception as e:
            logger.error(f"[LLM_JUDGE] Erreur: {e}")
            return {
                'decision': 'REJECT',
                'confidence': 0.0,
                'reason': f"Erreur juge LLM: {str(e)}",
                'latency_ms': (time.time() - start_time) * 1000
            }

class HybridGuardianSystem:
    """
    🛡️ SYSTÈME GUARDIAN HYBRIDE - VOTRE VISION OPTIMISÉE
    
    LOGIQUE:
    1. Système rapide filtre 80-90% des cas (5ms)
    2. Mini-LLM juge traite les cas ambigus (200ms)
    3. Performance moyenne: ~25ms
    """
    
    def __init__(self):
        self.fast_guard = AdvancedHallucinationGuard()
        self.llm_judge = MiniLLMJudge()
        
        # Seuils pour déclencher le juge LLM
        self.judge_trigger_thresholds = {
            'confidence_min': 0.3,  # En dessous = rejet direct
            'confidence_max': 0.8,  # Au dessus = acceptation directe
            'sensitive_domains': ['prix', 'coût', 'facture', 'promotion'],
            'number_detection': True  # Déclenche si chiffres détectés
        }
        
        # Métriques
        self.metrics = {
            'total_evaluations': 0,
            'fast_guard_decisions': 0,
            'llm_judge_calls': 0,
            'cache_hits': 0,
            'avg_latency': 0
        }
    
    def should_call_judge(self, fast_result: Dict, query: str, ai_response: str) -> bool:
        """Décider si le juge LLM doit être appelé"""
        confidence = fast_result.get('confidence_score', 0)
        
        # Cas clairs - pas besoin du juge
        if confidence >= self.judge_trigger_thresholds['confidence_max']:
            return False
        if confidence <= self.judge_trigger_thresholds['confidence_min']:
            return False
        
        # Domaines sensibles - toujours vérifier avec le juge
        query_lower = query.lower()
        if any(domain in query_lower for domain in self.judge_trigger_thresholds['sensitive_domains']):
            logger.info("[HYBRID_GUARDIAN] 🎯 Domaine sensible détecté - Appel du juge")
            return True
        
        # Détection de chiffres/prix dans la réponse
        if self.judge_trigger_thresholds['number_detection']:
            import re
            if re.search(r'\d+[.,]?\d*', ai_response):
                logger.info("[HYBRID_GUARDIAN] 🔢 Chiffres détectés - Appel du juge")
                return True
        
        # Cas ambigus
        if self.judge_trigger_thresholds['confidence_min'] < confidence < self.judge_trigger_thresholds['confidence_max']:
            logger.info("[HYBRID_GUARDIAN] ⚖️ Cas ambigu - Appel du juge")
            return True
        
        return False
    
    async def evaluate_response(
        self, 
        user_query: str, 
        ai_response: str, 
        supabase_results: List[Dict] = None,
        meili_results: List[Dict] = None,
        supabase_context: str = "",
        meili_context: str = ""
    ) -> GuardianDecision:
        """
        🎯 ÉVALUATION HYBRIDE - VOTRE SYSTÈME OPTIMISÉ
        """
        start_time = time.time()
        self.metrics['total_evaluations'] += 1
        
        logger.info("[HYBRID_GUARDIAN] 🛡️ Début évaluation hybride")
        
        # ÉTAPE 1: Système rapide (votre système actuel)
        fast_result = await self.fast_guard.check_response(
            user_query=user_query,
            ai_response=ai_response,
            supabase_results=supabase_results,
            meili_results=meili_results,
            supabase_context=supabase_context,
            meili_context=meili_context
        )
        
        # Décision rapide si cas clair
        if not self.should_call_judge(fast_result.__dict__, user_query, ai_response):
            self.metrics['fast_guard_decisions'] += 1
            latency = (time.time() - start_time) * 1000
            
            decision = "ACCEPT" if fast_result.is_safe else "REJECT"
            
            logger.info(f"[HYBRID_GUARDIAN] ⚡ Décision rapide: {decision} en {latency:.1f}ms")
            
            return GuardianDecision(
                decision=decision,
                confidence=fast_result.confidence_score,
                method="fast_guard",
                reason=fast_result.reason,
                latency_ms=latency,
                cost_estimate=0.0
            )
        
        # ÉTAPE 2: Appel du juge LLM pour cas ambigus
        self.metrics['llm_judge_calls'] += 1
        
        combined_context = f"{supabase_context}\n{meili_context}".strip()
        judge_result = await self.llm_judge.evaluate_response(
            user_query, ai_response, combined_context
        )
        
        total_latency = (time.time() - start_time) * 1000
        
        logger.info(f"[HYBRID_GUARDIAN] 🧠 Décision juge LLM: {judge_result['decision']} en {total_latency:.1f}ms")
        
        return GuardianDecision(
            decision=judge_result['decision'],
            confidence=judge_result['confidence'],
            method="llm_judge",
            reason=judge_result['reason'],
            latency_ms=total_latency,
            cost_estimate=0.001  # Estimation coût Groq
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Métriques de performance du système"""
        total = self.metrics['total_evaluations']
        if total == 0:
            return self.metrics
        
        return {
            **self.metrics,
            'fast_guard_percentage': (self.metrics['fast_guard_decisions'] / total) * 100,
            'llm_judge_percentage': (self.metrics['llm_judge_calls'] / total) * 100,
            'cache_hit_rate': (self.metrics['cache_hits'] / max(self.metrics['llm_judge_calls'], 1)) * 100
        }
