#!/usr/bin/env python3
"""
🔌 CIRCUIT BREAKER POUR RÉSILIENCE SYSTÈME
Prévention des cascades d'erreurs et amélioration de la disponibilité
"""

import asyncio
import time
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
import logging

class CircuitState(Enum):
    CLOSED = "closed"      # Fonctionnement normal
    OPEN = "open"          # Circuit ouvert, requêtes bloquées
    HALF_OPEN = "half_open"  # Test de récupération

@dataclass
class CircuitBreakerConfig:
    """Configuration du circuit breaker"""
    failure_threshold: int = 5  # Nombre d'échecs avant ouverture
    recovery_timeout: float = 30.0  # Temps avant test de récupération (secondes)
    success_threshold: int = 3  # Succès requis pour fermer le circuit
    timeout: float = 10.0  # Timeout des requêtes (secondes)

class CircuitBreaker:
    """
    Circuit breaker pour services externes (Groq, Supabase, MeiliSearch)
    Prévient les cascades d'erreurs et améliore la résilience
    """
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.last_success_time = 0
        
    def _should_attempt_reset(self) -> bool:
        """Vérifie si on peut tenter une récupération"""
        return (
            self.state == CircuitState.OPEN and
            time.time() - self.last_failure_time >= self.config.recovery_timeout
        )
    
    def _record_success(self):
        """Enregistre un succès"""
        self.last_success_time = time.time()
        self.failure_count = 0
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.success_count = 0
                logging.info(f"[CIRCUIT_BREAKER] {self.name}: Circuit fermé après récupération")
        
    def _record_failure(self):
        """Enregistre un échec"""
        self.last_failure_time = time.time()
        self.failure_count += 1
        self.success_count = 0
        
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                logging.error(f"[CIRCUIT_BREAKER] {self.name}: Circuit ouvert après {self.failure_count} échecs")
        elif self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logging.warning(f"[CIRCUIT_BREAKER] {self.name}: Retour en circuit ouvert")
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Exécute une fonction avec protection circuit breaker
        """
        # Vérifier l'état du circuit
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logging.info(f"[CIRCUIT_BREAKER] {self.name}: Test de récupération")
            else:
                raise Exception(f"Circuit breaker {self.name} ouvert - service indisponible")
        
        try:
            # Exécuter avec timeout
            result = await asyncio.wait_for(func(*args, **kwargs), timeout=self.config.timeout)
            self._record_success()
            return result
            
        except asyncio.TimeoutError:
            logging.error(f"[CIRCUIT_BREAKER] {self.name}: Timeout après {self.config.timeout}s")
            self._record_failure()
            raise Exception(f"Timeout du service {self.name}")
            
        except Exception as e:
            logging.error(f"[CIRCUIT_BREAKER] {self.name}: Erreur - {str(e)}")
            self._record_failure()
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """Retourne le statut du circuit breaker"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "last_success_time": self.last_success_time
        }

# Instances globales pour les services principaux
groq_circuit_breaker = CircuitBreaker("groq_api")
supabase_circuit_breaker = CircuitBreaker("supabase")
meilisearch_circuit_breaker = CircuitBreaker("meilisearch")

async def protected_groq_call(func: Callable, *args, **kwargs):
    """Appel Groq protégé par circuit breaker"""
    return await groq_circuit_breaker.call(func, *args, **kwargs)

async def protected_supabase_call(func: Callable, *args, **kwargs):
    """Appel Supabase protégé par circuit breaker"""
    return await supabase_circuit_breaker.call(func, *args, **kwargs)

async def protected_meilisearch_call(func: Callable, *args, **kwargs):
    """Appel MeiliSearch protégé par circuit breaker"""
    return await meilisearch_circuit_breaker.call(func, *args, **kwargs)
