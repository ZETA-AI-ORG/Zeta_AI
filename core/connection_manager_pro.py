"""
🔗 GESTIONNAIRE DE CONNEXIONS PROFESSIONNEL
Pool de connexions optimisé pour toutes les APIs
"""

import asyncio
import aiohttp
import aioredis
from typing import Dict, Any, Optional, List
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ConnectionStats:
    """Statistiques de connexion"""
    total_requests: int = 0
    active_connections: int = 0
    failed_connections: int = 0
    avg_response_time_ms: float = 0.0
    last_error: Optional[str] = None

class ConnectionManagerPro:
    """
    🎯 GESTIONNAIRE DE CONNEXIONS PROFESSIONNEL
    
    Fonctionnalités:
    - Pools de connexions réutilisables
    - Circuit breakers intégrés
    - Retry automatique avec backoff
    - Monitoring des performances
    - Load balancing simple
    - Connexions keepalive optimisées
    """
    
    def __init__(self):
        # Pools de connexions
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.redis_pool: Optional[aioredis.ConnectionPool] = None
        self.groq_session: Optional[aiohttp.ClientSession] = None
        
        # Configuration des pools
        self.http_config = {
            'connector': aiohttp.TCPConnector(
                limit=100,              # Max 100 connexions simultanées
                limit_per_host=20,      # Max 20 par host
                keepalive_timeout=300,  # Keepalive 5 minutes
                enable_cleanup_closed=True,
                use_dns_cache=True,
                ttl_dns_cache=300,
                family=0  # IPv4 et IPv6
            ),
            'timeout': aiohttp.ClientTimeout(
                total=30,       # Timeout total 30s
                connect=10,     # Connexion 10s
                sock_read=20    # Lecture 20s
            ),
            'headers': {
                'User-Agent': 'ChatbotRAG/1.0',
                'Connection': 'keep-alive'
            }
        }
        
        self.redis_config = {
            'max_connections': 50,
            'retry_on_timeout': True,
            'socket_keepalive': True,
            'socket_keepalive_options': {
                'TCP_KEEPIDLE': 60,
                'TCP_KEEPINTVL': 30,
                'TCP_KEEPCNT': 3
            }
        }
        
        # Circuit breakers
        self.circuit_breakers = {
            'supabase': {'failures': 0, 'last_failure': 0, 'threshold': 5},
            'meilisearch': {'failures': 0, 'last_failure': 0, 'threshold': 5},
            'groq': {'failures': 0, 'last_failure': 0, 'threshold': 3},
            'redis': {'failures': 0, 'last_failure': 0, 'threshold': 10}
        }
        
        # Statistiques
        self.stats: Dict[str, ConnectionStats] = {
            'supabase': ConnectionStats(),
            'meilisearch': ConnectionStats(),
            'groq': ConnectionStats(),
            'redis': ConnectionStats()
        }
        
        # État d'initialisation
        self.initialized = False
        
        logger.info("[CONNECTION_MANAGER] ✅ Gestionnaire de connexions initialisé")
    
    async def initialize(self):
        """Initialise tous les pools de connexions"""
        if self.initialized:
            return
        
        try:
            # Pool HTTP principal
            self.http_session = aiohttp.ClientSession(**self.http_config)
            
            # Pool spécialisé pour Groq (limites API différentes)
            groq_config = self.http_config.copy()
            groq_config['connector'] = aiohttp.TCPConnector(
                limit=20,  # Groq a des limites plus strictes
                limit_per_host=5,
                keepalive_timeout=120
            )
            self.groq_session = aiohttp.ClientSession(**groq_config)
            
            # Pool Redis
            try:
                self.redis_pool = aioredis.ConnectionPool.from_url(
                    "redis://localhost:6379",
                    **self.redis_config
                )
                
                # Test de connexion Redis
                redis = aioredis.Redis(connection_pool=self.redis_pool)
                await redis.ping()
                await redis.close()
                
                logger.info("[CONNECTION_MANAGER] ✅ Pool Redis connecté")
                
            except Exception as e:
                logger.warning(f"[CONNECTION_MANAGER] ⚠️ Redis non disponible: {e}")
                self.redis_pool = None
            
            self.initialized = True
            logger.info("[CONNECTION_MANAGER] ✅ Tous les pools initialisés")
            
        except Exception as e:
            logger.error(f"[CONNECTION_MANAGER] ❌ Erreur d'initialisation: {e}")
            raise
    
    async def cleanup(self):
        """Nettoie toutes les connexions"""
        if self.http_session:
            await self.http_session.close()
        
        if self.groq_session:
            await self.groq_session.close()
        
        if self.redis_pool:
            await self.redis_pool.disconnect()
        
        self.initialized = False
        logger.info("[CONNECTION_MANAGER] 🧹 Connexions fermées")
    
    @asynccontextmanager
    async def get_http_session(self, service: str = 'general'):
        """Context manager pour session HTTP"""
        await self.initialize()
        
        # Choisir la session appropriée
        if service == 'groq':
            session = self.groq_session
        else:
            session = self.http_session
        
        if not session:
            raise RuntimeError(f"Session HTTP non disponible pour {service}")
        
        # Vérifier circuit breaker
        if self._is_circuit_open(service):
            raise RuntimeError(f"Circuit breaker ouvert pour {service}")
        
        start_time = time.time()
        
        try:
            yield session
            
            # Succès - réinitialiser le circuit breaker
            self._reset_circuit_breaker(service)
            
        except Exception as e:
            # Échec - incrémenter le circuit breaker
            self._record_failure(service)
            raise
        
        finally:
            # Enregistrer les statistiques
            duration_ms = (time.time() - start_time) * 1000
            self._update_stats(service, duration_ms)
    
    @asynccontextmanager
    async def get_redis_connection(self):
        """Context manager pour connexion Redis"""
        await self.initialize()
        
        if not self.redis_pool:
            raise RuntimeError("Pool Redis non disponible")
        
        if self._is_circuit_open('redis'):
            raise RuntimeError("Circuit breaker Redis ouvert")
        
        start_time = time.time()
        redis = None
        
        try:
            redis = aioredis.Redis(connection_pool=self.redis_pool)
            yield redis
            
            # Succès
            self._reset_circuit_breaker('redis')
            
        except Exception as e:
            self._record_failure('redis')
            raise
        
        finally:
            if redis:
                await redis.close()
            
            duration_ms = (time.time() - start_time) * 1000
            self._update_stats('redis', duration_ms)
    
    async def request_with_retry(self, 
                                method: str, 
                                url: str, 
                                service: str = 'general',
                                max_retries: int = 3,
                                backoff_factor: float = 1.0,
                                **kwargs) -> aiohttp.ClientResponse:
        """
        Effectue une requête HTTP avec retry automatique
        """
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                async with self.get_http_session(service) as session:
                    async with session.request(method, url, **kwargs) as response:
                        # Vérifier le status code
                        if response.status >= 500:
                            # Erreur serveur, retry
                            raise aiohttp.ClientResponseError(
                                request_info=response.request_info,
                                history=response.history,
                                status=response.status
                            )
                        
                        return response
            
            except Exception as e:
                last_exception = e
                
                if attempt < max_retries:
                    # Calculer le délai de backoff
                    delay = backoff_factor * (2 ** attempt)
                    logger.warning(
                        f"[CONNECTION_MANAGER] Retry {attempt + 1}/{max_retries} "
                        f"pour {service} dans {delay}s: {str(e)}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"[CONNECTION_MANAGER] Échec final pour {service} après "
                        f"{max_retries} retries: {str(e)}"
                    )
        
        # Toutes les tentatives ont échoué
        raise last_exception
    
    def _is_circuit_open(self, service: str) -> bool:
        """Vérifie si le circuit breaker est ouvert"""
        breaker = self.circuit_breakers.get(service, {})
        
        if breaker.get('failures', 0) >= breaker.get('threshold', 5):
            # Circuit ouvert, vérifier si on peut le fermer
            time_since_failure = time.time() - breaker.get('last_failure', 0)
            if time_since_failure > 60:  # 1 minute de cooldown
                breaker['failures'] = 0
                return False
            return True
        
        return False
    
    def _record_failure(self, service: str):
        """Enregistre un échec pour le circuit breaker"""
        if service in self.circuit_breakers:
            self.circuit_breakers[service]['failures'] += 1
            self.circuit_breakers[service]['last_failure'] = time.time()
        
        if service in self.stats:
            self.stats[service].failed_connections += 1
    
    def _reset_circuit_breaker(self, service: str):
        """Réinitialise le circuit breaker après succès"""
        if service in self.circuit_breakers:
            self.circuit_breakers[service]['failures'] = 0
    
    def _update_stats(self, service: str, duration_ms: float):
        """Met à jour les statistiques de performance"""
        if service not in self.stats:
            return
        
        stats = self.stats[service]
        stats.total_requests += 1
        
        # Moyenne mobile de la latence
        if stats.avg_response_time_ms == 0:
            stats.avg_response_time_ms = duration_ms
        else:
            stats.avg_response_time_ms = (
                stats.avg_response_time_ms * 0.9 + duration_ms * 0.1
            )
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de connexion"""
        stats_dict = {}
        
        for service, stats in self.stats.items():
            circuit_breaker = self.circuit_breakers.get(service, {})
            
            stats_dict[service] = {
                'total_requests': stats.total_requests,
                'failed_connections': stats.failed_connections,
                'avg_response_time_ms': round(stats.avg_response_time_ms, 2),
                'success_rate_percent': round(
                    (1 - stats.failed_connections / max(stats.total_requests, 1)) * 100, 2
                ),
                'circuit_breaker_failures': circuit_breaker.get('failures', 0),
                'circuit_breaker_open': self._is_circuit_open(service)
            }
        
        return {
            'services': stats_dict,
            'pools_initialized': self.initialized,
            'redis_available': self.redis_pool is not None
        }

# Instance globale
connection_manager = ConnectionManagerPro()




