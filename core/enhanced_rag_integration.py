"""
🔧 INTÉGRATION ENHANCED RAG - WRAPPER INTELLIGENT
Intègre tous les nouveaux systèmes avec l'existant SANS casser
"""

import asyncio
import time
from typing import Dict, Any, Optional
import logging
from core.rag_engine_simplified_fixed import get_rag_response_advanced
from core.apm_monitoring import apm_monitor, RequestMetrics
from core.unified_cache_pro import unified_cache
from core.token_optimizer_pro import token_optimizer
from core.connection_manager_pro import connection_manager

logger = logging.getLogger(__name__)

class EnhancedRAGIntegration:
    """
    🎯 WRAPPER INTELLIGENT POUR RAG ENHANCED
    
    Fonctionnalités:
    - Intégration transparente avec l'existant
    - Monitoring automatique de toutes les requêtes
    - Cache intelligent global
    - Optimisation des tokens automatique
    - Gestion des connexions optimisée
    - Fallback vers l'ancien système si erreur
    """
    
    def __init__(self):
        self.enabled = True
        self.fallback_to_original = True
        
        logger.info("[ENHANCED_RAG] ✅ Wrapper intelligent initialisé")
    
    async def process_request_enhanced(self, 
                                     message: str, 
                                     user_id: str, 
                                     company_id: str, 
                                     conversation_id: str = None,
                                     use_streaming: bool = False) -> Dict[str, Any]:
        """
        Traitement de requête avec tous les systèmes enhanced
        
        Args:
            message: Question utilisateur
            user_id: ID utilisateur  
            company_id: ID entreprise
            conversation_id: ID conversation
            use_streaming: Utiliser le streaming ou pas
            
        Returns:
            Réponse avec métriques enhanced
        """
        
        request_id = f"req_{int(time.time() * 1000)}"
        start_time = time.time()
        
        logger.info(f"[ENHANCED_RAG] 🚀 Début requête enhanced: {request_id}")
        
        try:
            # 1. Vérifier le cache intelligent d'abord
            cache_key = self._generate_cache_key(message, company_id)
            cached_response = await unified_cache.get(cache_key)
            
            if cached_response:
                logger.info(f"[ENHANCED_RAG] ✅ Cache hit: {request_id}")
                
                # Enregistrer les métriques de cache hit
                await self._record_cache_hit_metrics(
                    request_id, message, user_id, company_id, 
                    cached_response, start_time
                )
                
                return {
                    'response': cached_response['response'],
                    'request_id': request_id,
                    'source': 'Cache',
                    'processing_time_ms': (time.time() - start_time) * 1000,
                    'enhanced': True,
                    'cached': True
                }
            
            # 2. Pas de cache, traitement complet
            logger.info(f"[ENHANCED_RAG] 🔍 Cache miss, traitement complet: {request_id}")
            
            # Initialiser les connexions si pas fait
            await connection_manager.initialize()
            
            # 3. Appeler le RAG existant (SANS MODIFICATION)
            rag_response = await get_rag_response_advanced(
                message=message,
                user_id=user_id,
                company_id=company_id,
                conversation_id=conversation_id,
                use_hyde=True,
                debug=False
            )
            
            # 4. Post-traitement enhanced
            enhanced_response = await self._enhance_response(
                rag_response, message, request_id
            )
            
            # 5. Mise en cache de la réponse optimisée
            await self._cache_response(cache_key, enhanced_response, rag_response)
            
            # 6. Enregistrer les métriques complètes
            await self._record_full_metrics(
                request_id, message, user_id, company_id,
                rag_response, enhanced_response, start_time
            )
            
            logger.info(f"[ENHANCED_RAG] ✅ Requête enhanced terminée: {request_id}")
            
            return enhanced_response
            
        except Exception as e:
            logger.error(f"[ENHANCED_RAG] ❌ Erreur enhanced: {request_id} - {e}")
            
            # Fallback vers l'ancien système
            if self.fallback_to_original:
                logger.info(f"[ENHANCED_RAG] 🔄 Fallback vers système original: {request_id}")
                
                try:
                    original_response = await get_rag_response_advanced(
                        message=message,
                        user_id=user_id,
                        company_id=company_id,
                        conversation_id=conversation_id,
                        use_hyde=True,
                        debug=False
                    )
                    
                    # Enregistrer l'erreur mais retourner la réponse originale
                    await self._record_error_metrics(
                        request_id, message, user_id, company_id, str(e), start_time
                    )
                    
                    return {
                        'response': original_response.get('ai_response', 'Erreur de traitement'),
                        'request_id': request_id,
                        'source': 'Original (Fallback)',
                        'processing_time_ms': (time.time() - start_time) * 1000,
                        'enhanced': False,
                        'fallback_used': True,
                        'error': str(e)
                    }
                    
                except Exception as fallback_error:
                    logger.error(f"[ENHANCED_RAG] ❌ Erreur fallback: {request_id} - {fallback_error}")
                    
                    await self._record_error_metrics(
                        request_id, message, user_id, company_id, 
                        f"Enhanced: {e}, Fallback: {fallback_error}", start_time
                    )
                    
                    return {
                        'response': 'Je rencontre des difficultés techniques. Veuillez réessayer.',
                        'request_id': request_id,
                        'source': 'Error',
                        'processing_time_ms': (time.time() - start_time) * 1000,
                        'enhanced': False,
                        'error': True
                    }
            else:
                raise
    
    async def _enhance_response(self, rag_response: Dict, original_query: str, request_id: str) -> Dict[str, Any]:
        """Post-traitement enhanced de la réponse RAG"""
        
        ai_response = rag_response.get('ai_response', '')
        context = rag_response.get('context', '')
        
        # 1. Optimisation des tokens du contexte (pour les métriques)
        if context:
            optimization_result = token_optimizer.optimize_context(
                context=context,
                target_tokens=2000,
                query=original_query
            )
            
            logger.info(
                f"[ENHANCED_RAG] Token optimization: "
                f"{optimization_result['compression_ratio']:.1%} compression"
            )
        else:
            optimization_result = {'compression_ratio': 0, 'savings_cost_estimate_usd': 0}
        
        # 2. Analyser la qualité de la réponse
        response_quality = self._analyze_response_quality(ai_response, original_query)
        
        # 3. Construire la réponse enhanced
        enhanced_response = {
            'response': ai_response,
            'request_id': request_id,
            'source': rag_response.get('search_source', 'Unknown'),
            'processing_time_ms': rag_response.get('processing_time_ms', 0),
            'enhanced': True,
            'cached': False,
            'quality_score': response_quality['score'],
            'token_optimization': {
                'compression_ratio': optimization_result['compression_ratio'],
                'cost_savings_usd': optimization_result.get('savings_cost_estimate_usd', 0)
            },
            'original_rag_data': {
                'confidence': rag_response.get('confidence', 0),
                'validation_safe': rag_response.get('validation_safe', True),
                'documents_found': rag_response.get('documents_found', False)
            }
        }
        
        return enhanced_response
    
    def _analyze_response_quality(self, response: str, query: str) -> Dict[str, Any]:
        """Analyse la qualité de la réponse"""
        
        if not response or len(response.strip()) < 10:
            return {'score': 0.0, 'issues': ['Response too short']}
        
        issues = []
        score = 1.0
        
        # Vérifications basiques
        if 'erreur' in response.lower() or 'error' in response.lower():
            score -= 0.3
            issues.append('Contains error message')
        
        if len(response) < 50:
            score -= 0.2
            issues.append('Response quite short')
        
        if response.count('.') < 1:
            score -= 0.1
            issues.append('No complete sentences')
        
        # Vérifier si la réponse semble pertinente
        query_words = set(query.lower().split())
        response_words = set(response.lower().split())
        
        word_overlap = len(query_words.intersection(response_words))
        if word_overlap < len(query_words) * 0.2:
            score -= 0.2
            issues.append('Low query-response relevance')
        
        return {
            'score': max(score, 0.0),
            'issues': issues
        }
    
    def _generate_cache_key(self, message: str, company_id: str) -> str:
        """Génère une clé de cache intelligente"""
        import hashlib
        
        # Normaliser la requête pour le cache
        normalized_query = message.lower().strip()
        
        # Créer la clé
        cache_data = f"enhanced_rag:{company_id}:{normalized_query}"
        cache_key = hashlib.md5(cache_data.encode()).hexdigest()
        
        return cache_key
    
    async def _cache_response(self, cache_key: str, enhanced_response: Dict, rag_response: Dict):
        """Met en cache la réponse enhanced"""
        
        try:
            cache_data = {
                'response': enhanced_response['response'],
                'source': enhanced_response['source'],
                'quality_score': enhanced_response['quality_score'],
                'timestamp': time.time()
            }
            
            # Cache pour 1 heure par défaut, plus si qualité élevée
            ttl_seconds = 3600
            if enhanced_response['quality_score'] > 0.8:
                ttl_seconds = 7200  # 2 heures pour réponses de qualité
            
            await unified_cache.set(cache_key, cache_data, ttl_seconds)
            
            logger.debug(f"[ENHANCED_RAG] Response cached: {cache_key}")
            
        except Exception as e:
            logger.warning(f"[ENHANCED_RAG] Cache error: {e}")
    
    async def _record_cache_hit_metrics(self, request_id: str, message: str, user_id: str, 
                                       company_id: str, cached_response: Dict, start_time: float):
        """Enregistre les métriques de cache hit"""
        
        duration_ms = (time.time() - start_time) * 1000
        
        metrics = RequestMetrics(
            request_id=request_id,
            query=message,
            company_id=company_id,
            user_id=user_id,
            start_time=start_time,
            end_time=time.time(),
            duration_ms=duration_ms,
            search_source="Cache",
            search_time_ms=0,  # Cache instantané
            generation_time_ms=0,
            context_length=0,
            response_length=len(cached_response['response']),
            tokens_estimated=len(cached_response['response']) // 4,
            cost_estimated_usd=0.0,  # Cache gratuit
            cache_hit=True
        )
        
        await apm_monitor.track_request(metrics)
    
    async def _record_full_metrics(self, request_id: str, message: str, user_id: str,
                                  company_id: str, rag_response: Dict, enhanced_response: Dict, 
                                  start_time: float):
        """Enregistre les métriques complètes"""
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Estimer les coûts
        response_length = len(enhanced_response['response'])
        estimated_tokens = response_length // 4
        estimated_cost = estimated_tokens * 0.00002  # ~$0.02/1K tokens
        
        metrics = RequestMetrics(
            request_id=request_id,
            query=message,
            company_id=company_id,
            user_id=user_id,
            start_time=start_time,
            end_time=time.time(),
            duration_ms=duration_ms,
            search_source=enhanced_response['source'],
            search_time_ms=rag_response.get('processing_time_ms', 0) * 0.6,  # Estimation
            generation_time_ms=rag_response.get('processing_time_ms', 0) * 0.4,
            context_length=len(rag_response.get('context', '')),
            response_length=response_length,
            tokens_estimated=estimated_tokens,
            cost_estimated_usd=estimated_cost,
            cache_hit=False
        )
        
        await apm_monitor.track_request(metrics)
    
    async def _record_error_metrics(self, request_id: str, message: str, user_id: str,
                                   company_id: str, error: str, start_time: float):
        """Enregistre les métriques d'erreur"""
        
        duration_ms = (time.time() - start_time) * 1000
        
        metrics = RequestMetrics(
            request_id=request_id,
            query=message,
            company_id=company_id,
            user_id=user_id,
            start_time=start_time,
            end_time=time.time(),
            duration_ms=duration_ms,
            search_source="Error",
            search_time_ms=0,
            generation_time_ms=0,
            context_length=0,
            response_length=0,
            tokens_estimated=0,
            cost_estimated_usd=0.0,
            error=error,
            cache_hit=False
        )
        
        await apm_monitor.track_request(metrics)

# Instance globale
enhanced_rag = EnhancedRAGIntegration()




