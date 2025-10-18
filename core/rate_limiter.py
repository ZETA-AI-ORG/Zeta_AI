#!/usr/bin/env python3
"""
🚦 RATE LIMITER POUR GROQ API
Prévention des erreurs 429 (Too Many Requests)
"""

import asyncio
import time
from typing import Dict, Optional
from dataclasses import dataclass
import logging

@dataclass
class RateLimitConfig:
    """Configuration du rate limiting"""
    requests_per_minute: int = 60  # Augmenté pour meilleure performance
    requests_per_hour: int = 2000  # Augmenté pour tests de charge
    burst_limit: int = 10  # Plus de requêtes simultanées
    retry_delay: float = 0.5  # Délai réduit entre retries
    max_retries: int = 5  # Plus de retries
    adaptive_backoff: bool = True  # Backoff adaptatif

class RateLimiter:
    """
    Rate limiter intelligent pour API Groq
    Prévient les erreurs 429 avec backoff exponentiel
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.request_times: Dict[str, list] = {}
        self.active_requests = 0
        self.semaphore = asyncio.Semaphore(self.config.burst_limit)
        self.consecutive_429_errors = 0
        self.last_429_time = 0
        
    def _clean_old_requests(self, key: str, window_seconds: int):
        """Nettoie les anciennes requêtes hors fenêtre"""
        now = time.time()
        if key not in self.request_times:
            self.request_times[key] = []
        
        # Garde seulement les requêtes dans la fenêtre
        self.request_times[key] = [
            req_time for req_time in self.request_times[key]
            if now - req_time < window_seconds
        ]
    
    def _can_make_request(self, key: str, limit: int, window_seconds: int) -> bool:
        """Vérifie si on peut faire une requête"""
        self._clean_old_requests(key, window_seconds)
        return len(self.request_times[key]) < limit
    
    def _record_request(self, key: str):
        """Enregistre une nouvelle requête"""
        if key not in self.request_times:
            self.request_times[key] = []
        self.request_times[key].append(time.time())
    
    async def wait_for_slot(self, user_id: str = "default") -> None:
        """
        Attend qu'un slot soit disponible selon les limites avec backoff adaptatif
        """
        # Backoff adaptatif si erreurs 429 récentes
        if self.consecutive_429_errors > 0 and time.time() - self.last_429_time < 30:
            adaptive_delay = self.config.retry_delay * (2 ** min(self.consecutive_429_errors, 4))
            logging.warning(f"[RATE_LIMIT] Backoff adaptatif: {adaptive_delay:.1f}s après {self.consecutive_429_errors} erreurs 429")
            await asyncio.sleep(adaptive_delay)
        
        # Vérification limite par minute avec délai réduit
        while not self._can_make_request(f"{user_id}_minute", self.config.requests_per_minute, 60):
            logging.warning(f"[RATE_LIMIT] Limite par minute atteinte pour {user_id}, attente...")
            await asyncio.sleep(self.config.retry_delay)
        
        # Vérification limite par heure avec délai optimisé
        while not self._can_make_request(f"{user_id}_hour", self.config.requests_per_hour, 3600):
            logging.warning(f"[RATE_LIMIT] Limite par heure atteinte pour {user_id}, attente...")
            await asyncio.sleep(10)  # Délai réduit de 60s à 10s
        
        # Acquisition du semaphore pour limiter les requêtes simultanées
        await self.semaphore.acquire()
        
        # Enregistrer la requête
        self._record_request(f"{user_id}_minute")
        self._record_request(f"{user_id}_hour")
        
        self.active_requests += 1
        # Log réduit - seulement si debug nécessaire
        if self.active_requests > 3:
            logging.info(f"[RATE_LIMIT] {self.active_requests} slots actifs")
    
    def release_slot(self, user_id: str = "default"):
        """Libère un slot après requête"""
        self.semaphore.release()
        self.active_requests = max(0, self.active_requests - 1)
        # Log réduit - seulement si debug nécessaire
        if self.active_requests > 3:
            logging.info(f"[RATE_LIMIT] {self.active_requests} slots restants")
    
    async def execute_with_rate_limit(self, func, *args, user_id: str = "default", **kwargs):
        """
        Exécute une fonction avec rate limiting automatique et gestion d'erreurs améliorée
        """
        await self.wait_for_slot(user_id)
        
        try:
            result = await func(*args, **kwargs)
            # Reset compteur d'erreurs 429 en cas de succès
            if self.consecutive_429_errors > 0:
                logging.info(f"[RATE_LIMIT] Succès après {self.consecutive_429_errors} erreurs 429, reset compteur")
                self.consecutive_429_errors = 0
            return result
        except Exception as e:
            # Gestion intelligente des erreurs 429
            if "429" in str(e) or "Too Many Requests" in str(e):
                self.consecutive_429_errors += 1
                self.last_429_time = time.time()
                backoff_time = self.config.retry_delay * (2 ** min(self.consecutive_429_errors, 4))
                logging.error(f"[RATE_LIMIT] Erreur 429 #{self.consecutive_429_errors}, backoff: {backoff_time:.1f}s")
                await asyncio.sleep(backoff_time)
            raise
        finally:
            self.release_slot(user_id)

# Instance globale du rate limiter
global_rate_limiter = RateLimiter()

async def rate_limited_llm_call(llm_func, *args, user_id: str = "default", **kwargs):
    """
    Wrapper pour appels LLM avec rate limiting
    """
    return await global_rate_limiter.execute_with_rate_limit(
        llm_func, *args, user_id=user_id, **kwargs
    )
