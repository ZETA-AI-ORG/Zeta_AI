#!/usr/bin/env python3
"""
🛡️ GESTIONNAIRE D'ERREURS AVANCÉ
Gestion centralisée des erreurs avec fallback et récupération automatique
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum
import traceback

class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ErrorResponse:
    """Réponse standardisée d'erreur"""
    success: bool
    error_type: str
    error_message: str
    severity: ErrorSeverity
    fallback_response: Optional[str] = None
    retry_suggested: bool = False
    details: Optional[Dict[str, Any]] = None

class ErrorHandler:
    """
    Gestionnaire d'erreurs centralisé avec fallback automatique
    """
    
    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.fallback_responses = {
            "groq_api": "Je rencontre des difficultés techniques. Veuillez réessayer dans quelques instants.",
            "supabase": "Problème de connexion à la base de données. Les données peuvent être temporairement indisponibles.",
            "meilisearch": "Service de recherche temporairement indisponible. Recherche basique activée.",
            "rate_limit": "Trop de requêtes simultanées. Veuillez patienter quelques secondes.",
            "validation": "Votre demande ne peut pas être traitée pour des raisons de sécurité.",
            "hallucination": "Réponse non fiable détectée. Reformulez votre question pour plus de précision.",
            "generic": "Une erreur technique s'est produite. Notre équipe travaille à la résoudre."
        }
    
    def _classify_error(self, error: Exception, context: str = "") -> ErrorResponse:
        """Classifie une erreur et détermine la réponse appropriée"""
        error_str = str(error).lower()
        error_type = type(error).__name__
        
        # Classification par type d'erreur
        if "429" in error_str or "too many requests" in error_str:
            return ErrorResponse(
                success=False,
                error_type="rate_limit",
                error_message="Limite de requêtes atteinte",
                severity=ErrorSeverity.MEDIUM,
                fallback_response=self.fallback_responses["rate_limit"],
                retry_suggested=True
            )
        
        elif "timeout" in error_str or "asyncio.timeout" in error_type.lower():
            return ErrorResponse(
                success=False,
                error_type="timeout",
                error_message="Délai d'attente dépassé",
                severity=ErrorSeverity.MEDIUM,
                fallback_response=self.fallback_responses["generic"],
                retry_suggested=True
            )
        
        elif "connection" in error_str or "network" in error_str:
            service = self._detect_service_from_context(context, error_str)
            return ErrorResponse(
                success=False,
                error_type="connection",
                error_message=f"Problème de connexion: {service}",
                severity=ErrorSeverity.HIGH,
                fallback_response=self.fallback_responses.get(service, self.fallback_responses["generic"]),
                retry_suggested=True
            )
        
        elif "401" in error_str or "unauthorized" in error_str:
            return ErrorResponse(
                success=False,
                error_type="authentication",
                error_message="Erreur d'authentification",
                severity=ErrorSeverity.CRITICAL,
                fallback_response="Problème d'authentification du service. Contactez l'administrateur.",
                retry_suggested=False
            )
        
        elif "500" in error_str or "internal server error" in error_str:
            return ErrorResponse(
                success=False,
                error_type="server_error",
                error_message="Erreur serveur interne",
                severity=ErrorSeverity.HIGH,
                fallback_response=self.fallback_responses["generic"],
                retry_suggested=True
            )
        
        else:
            return ErrorResponse(
                success=False,
                error_type="unknown",
                error_message=str(error),
                severity=ErrorSeverity.MEDIUM,
                fallback_response=self.fallback_responses["generic"],
                retry_suggested=False
            )
    
    def _detect_service_from_context(self, context: str, error_str: str) -> str:
        """Détecte le service concerné par l'erreur"""
        context_lower = context.lower()
        error_lower = error_str.lower()
        
        if "groq" in context_lower or "groq" in error_lower:
            return "groq_api"
        elif "supabase" in context_lower or "supabase" in error_lower:
            return "supabase"
        elif "meili" in context_lower or "meilisearch" in error_lower:
            return "meilisearch"
        else:
            return "generic"
    
    async def handle_error(self, 
                          error: Exception, 
                          context: str = "",
                          fallback_func: Optional[Callable] = None) -> ErrorResponse:
        """
        Gère une erreur avec classification et fallback automatique
        """
        # Incrémenter le compteur d'erreurs
        error_key = f"{context}_{type(error).__name__}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Classifier l'erreur
        error_response = self._classify_error(error, context)
        
        # Logger l'erreur avec détails
        logging.error(f"[ERROR_HANDLER] {context}: {error_response.error_type} - {error_response.error_message}")
        logging.error(f"[ERROR_HANDLER] Détails: {str(error)}")
        logging.error(f"[ERROR_HANDLER] Traceback: {traceback.format_exc()}")
        
        # Exécuter fallback si disponible
        if fallback_func and callable(fallback_func):
            try:
                fallback_result = await fallback_func()
                error_response.fallback_response = fallback_result
                logging.info(f"[ERROR_HANDLER] Fallback exécuté avec succès pour {context}")
            except Exception as fallback_error:
                logging.error(f"[ERROR_HANDLER] Échec du fallback: {str(fallback_error)}")
        
        # Ajouter détails pour debugging
        error_response.details = {
            "context": context,
            "error_count": self.error_counts[error_key],
            "original_error": str(error),
            "error_type_class": type(error).__name__
        }
        
        return error_response
    
    async def safe_execute(self, 
                          func: Callable,
                          context: str = "",
                          fallback_func: Optional[Callable] = None,
                          max_retries: int = 3,
                          retry_delay: float = 1.0) -> Union[Any, ErrorResponse]:
        """
        Exécute une fonction de manière sécurisée avec retry et fallback
        """
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    logging.info(f"[ERROR_HANDLER] Tentative {attempt + 1}/{max_retries + 1} pour {context}")
                    await asyncio.sleep(retry_delay * attempt)
                
                result = await func()
                
                if attempt > 0:
                    logging.info(f"[ERROR_HANDLER] Succès après {attempt} retry(s) pour {context}")
                
                return result
                
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    logging.warning(f"[ERROR_HANDLER] Tentative {attempt + 1} échouée pour {context}: {str(e)}")
                else:
                    logging.error(f"[ERROR_HANDLER] Toutes les tentatives échouées pour {context}")
        
        # Toutes les tentatives ont échoué, gérer l'erreur
        return await self.handle_error(last_error, context, fallback_func)
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques d'erreurs"""
        return {
            "total_errors": sum(self.error_counts.values()),
            "error_breakdown": dict(self.error_counts),
            "most_common_errors": sorted(
                self.error_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5]
        }

# Instance globale du gestionnaire d'erreurs
global_error_handler = ErrorHandler()

async def safe_api_call(func: Callable, 
                       context: str = "",
                       fallback_func: Optional[Callable] = None,
                       max_retries: int = 3) -> Union[Any, ErrorResponse]:
    """
    Wrapper pour appels API sécurisés
    """
    return await global_error_handler.safe_execute(
        func, context, fallback_func, max_retries
    )
