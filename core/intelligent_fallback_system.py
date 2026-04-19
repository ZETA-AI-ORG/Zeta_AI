#!/usr/bin/env python3
"""
🔄 SYSTÈME DE FALLBACK INTELLIGENT 2024
Gestion intelligente des échecs et des réponses de secours
"""

import asyncio
import time
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime

from .advanced_intent_classifier import IntentType, IntentResult
from .llm_client import get_llm_client
from .message_registry import get_system_response, get_company_tone

logger = logging.getLogger(__name__)

class FallbackType(Enum):
    """Types de fallback"""
    NO_DOCUMENTS = "no_documents"
    LOW_CONFIDENCE = "low_confidence"
    VALIDATION_FAILED = "validation_failed"
    LLM_ERROR = "llm_error"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    UNKNOWN_ERROR = "unknown_error"

@dataclass
class FallbackResponse:
    """Réponse de fallback intelligente"""
    response: str
    fallback_type: FallbackType
    confidence: float
    is_helpful: bool
    suggested_actions: List[str]
    escalation_required: bool
    processing_time_ms: float

class IntelligentFallbackSystem:
    """
    🔄 SYSTÈME DE FALLBACK INTELLIGENT 2024
    
    Fonctionnalités avancées :
    1. Détection intelligente des types d'échec
    2. Réponses contextuelles adaptatives
    3. Escalation automatique
    4. Apprentissage des patterns d'échec
    5. Suggestions d'actions utilisateur
    """
    
    def __init__(self):
        # V2.0 : plus d'usage direct de Groq — on passe par le client centralisé (OpenRouter / famille Gemma-Gemini)
        self.llm_client = get_llm_client()
        self.start_time = datetime.now()
        
        # Le dictionnaire statique est conservé uniquement comme ultime repli interne
        self._legacy_templates = self._build_fallback_templates()
        
        # Patterns d'échec
        self.failure_patterns = self._build_failure_patterns()
        
        # Cache des fallbacks
        self.fallback_cache = {}
        self.cache_ttl = 3600  # 1 heure
        
        # Statistiques d'échec
        self.failure_stats = {}
        
        logger.info("[FALLBACK_SYSTEM] Système de fallback intelligent initialisé")
    
    def _build_fallback_templates(self) -> Dict[FallbackType, Dict[str, str]]:
        """Construit les templates de réponses de fallback"""
        return {
            FallbackType.NO_DOCUMENTS: {
                'social': "Bonjour ! Je suis là pour vous aider. Que puis-je faire pour vous ?",
                'business': "Je n'ai pas trouvé d'informations spécifiques sur votre demande. Pouvez-vous me donner plus de détails ?",
                'critical': "Pour cette question technique, je recommande de contacter directement notre service client qui pourra vous donner une réponse précise."
            },
            FallbackType.LOW_CONFIDENCE: {
                'social': "Je ne suis pas sûr de bien comprendre. Pouvez-vous reformuler votre question ?",
                'business': "Je voudrais m'assurer de bien répondre à votre question. Pouvez-vous me donner plus de contexte ?",
                'critical': "Cette question nécessite une expertise technique. Je vous recommande de contacter notre équipe spécialisée."
            },
            FallbackType.VALIDATION_FAILED: {
                'social': "Je ne peux pas répondre à cette question de manière appropriée. Comment puis-je vous aider autrement ?",
                'business': "Je ne peux pas confirmer cette information. Pouvez-vous contacter notre service client ?",
                'critical': "Pour des informations techniques précises, je recommande de contacter directement nos experts."
            },
            FallbackType.LLM_ERROR: {
                'social': "Je rencontre une difficulté technique. Pouvez-vous reformuler votre question ?",
                'business': "Je rencontre un problème technique. Pouvez-vous réessayer dans quelques instants ?",
                'critical': "Système temporairement indisponible. Veuillez contacter notre support technique."
            },
            FallbackType.TIMEOUT: {
                'social': "Je prends un peu plus de temps à répondre. Pouvez-vous patienter ?",
                'business': "Le traitement de votre demande prend plus de temps que prévu. Pouvez-vous réessayer ?",
                'critical': "Système surchargé. Veuillez contacter notre support pour une assistance immédiate."
            },
            FallbackType.RATE_LIMIT: {
                'social': "Je reçois beaucoup de demandes en ce moment. Pouvez-vous réessayer dans quelques minutes ?",
                'business': "Système temporairement surchargé. Veuillez réessayer dans quelques instants.",
                'critical': "Trafic élevé détecté. Pour une assistance prioritaire, contactez notre support."
            },
            FallbackType.UNKNOWN_ERROR: {
                'social': "Je rencontre une difficulté inattendue. Comment puis-je vous aider autrement ?",
                'business': "Une erreur inattendue s'est produite. Pouvez-vous réessayer ?",
                'critical': "Erreur système détectée. Veuillez contacter notre support technique."
            }
        }
    
    def _build_failure_patterns(self) -> Dict[str, List[str]]:
        """Construit les patterns de détection d'échec"""
        return {
            'no_documents': [
                'aucun document trouvé',
                'no documents found',
                'aucun résultat',
                'no results'
            ],
            'low_confidence': [
                'confidence too low',
                'confiance trop faible',
                'uncertain',
                'incertain'
            ],
            'validation_failed': [
                'validation failed',
                'validation échouée',
                'rejected',
                'rejeté'
            ],
            'llm_error': [
                'llm error',
                'erreur llm',
                'model error',
                'erreur modèle'
            ],
            'timeout': [
                'timeout',
                'délai dépassé',
                'time limit exceeded',
                'limite de temps'
            ],
            'rate_limit': [
                'rate limit',
                'limite de taux',
                'too many requests',
                'trop de requêtes'
            ]
        }
    
    async def generate_fallback_response(
        self,
        user_query: str,
        intent_result: IntentResult,
        error_context: Dict[str, Any] = None,
        company_context: Dict[str, Any] = None
    ) -> FallbackResponse:
        """
        🔄 GÉNÉRATION DE RÉPONSE DE FALLBACK INTELLIGENTE
        
        Args:
            user_query: Question utilisateur
            intent_result: Résultat de classification d'intention
            error_context: Contexte de l'erreur
            company_context: Contexte de l'entreprise
            
        Returns:
            FallbackResponse: Réponse de fallback intelligente
        """
        start_time = time.time()
        
        # Détection du type de fallback
        fallback_type = self._detect_fallback_type(error_context)
        
        # Détermination du niveau de criticité
        criticality_level = self._determine_criticality_level(intent_result, fallback_type)
        
        # Génération de la réponse adaptative
        response = await self._generate_adaptive_response(
            user_query, intent_result, fallback_type, criticality_level, company_context
        )
        
        # Génération des suggestions d'actions
        suggested_actions = self._generate_suggested_actions(
            intent_result, fallback_type, criticality_level
        )
        
        # Détermination de l'escalation
        escalation_required = self._requires_escalation(fallback_type, criticality_level)
        
        # Calcul de la confiance
        confidence = self._calculate_fallback_confidence(intent_result, fallback_type)
        
        # Mise à jour des statistiques
        self._update_failure_stats(fallback_type, intent_result.primary_intent)
        
        result = FallbackResponse(
            response=response,
            fallback_type=fallback_type,
            confidence=confidence,
            is_helpful=True,
            suggested_actions=suggested_actions,
            escalation_required=escalation_required,
            processing_time_ms=(time.time() - start_time) * 1000
        )
        
        logger.info(f"[FALLBACK_SYSTEM] Fallback généré: {fallback_type.value} (conf: {confidence:.2f})")
        
        return result
    
    def _detect_fallback_type(self, error_context: Dict[str, Any] = None) -> FallbackType:
        """Détecte le type de fallback basé sur le contexte d'erreur"""
        if not error_context:
            return FallbackType.UNKNOWN_ERROR
        
        error_message = str(error_context.get('error', '')).lower()
        
        # Détection par patterns
        for fallback_type, patterns in self.failure_patterns.items():
            if any(pattern in error_message for pattern in patterns):
                return FallbackType(fallback_type)
        
        # Détection par type d'erreur
        error_type = error_context.get('error_type', '')
        if 'timeout' in error_type.lower():
            return FallbackType.TIMEOUT
        elif 'rate_limit' in error_type.lower():
            return FallbackType.RATE_LIMIT
        elif 'llm' in error_type.lower():
            return FallbackType.LLM_ERROR
        elif 'validation' in error_type.lower():
            return FallbackType.VALIDATION_FAILED
        elif 'no_documents' in error_message:
            return FallbackType.NO_DOCUMENTS
        elif 'confidence' in error_message:
            return FallbackType.LOW_CONFIDENCE
        
        return FallbackType.UNKNOWN_ERROR
    
    def _determine_criticality_level(self, intent_result: IntentResult, fallback_type: FallbackType) -> str:
        """Détermine le niveau de criticité"""
        # Intentions critiques
        if intent_result.primary_intent in [IntentType.TECHNICAL_SPECS, IntentType.MEDICAL_ADVICE]:
            return 'critical'
        
        # Intentions métier
        if intent_result.primary_intent in [IntentType.PRODUCT_INQUIRY, IntentType.PRICING_INFO, IntentType.DELIVERY_INFO]:
            return 'business'
        
        # Intentions sociales
        if intent_result.primary_intent in [IntentType.SOCIAL_GREETING, IntentType.POLITENESS, IntentType.GENERAL_CONVERSATION]:
            return 'social'
        
        return 'business'
    
    async def _generate_adaptive_response(
        self,
        user_query: str,
        intent_result: IntentResult,
        fallback_type: FallbackType,
        criticality_level: str,
        company_context: Dict[str, Any] = None
    ) -> str:
        """Génère une réponse adaptative basée sur le contexte"""
        
        # Détermination de la catégorie du registre
        category = "fallback_search"
        if fallback_type in [FallbackType.LLM_ERROR, FallbackType.TIMEOUT, FallbackType.RATE_LIMIT]:
            category = "error_tech"
            
        # Préparation du ton et des variables
        tone = get_company_tone(company_context.get('company_id') if company_context else None)
        kwargs = {
            'company_name': company_context.get('company_name', 'notre entreprise') if company_context else 'notre entreprise',
            'ai_name': company_context.get('ai_name', 'votre assistant') if company_context else 'votre assistant'
        }
        
        # Appel au registre dynamique (Niveau 1)
        template = get_system_response(category, tone=tone, **kwargs)
        
        # Fallback de secours si le registre échoue (ne devrait pas arriver)
        if "[ERREUR SYSTEME" in template:
            template = self._legacy_templates.get(fallback_type, {}).get(criticality_level, "Une erreur est survenue.")
        
        # Personnalisation basée sur l'intention
        if intent_result.primary_intent == IntentType.SOCIAL_GREETING:
            template = f"Bonjour ! {template}"
        elif intent_result.primary_intent == IntentType.POLITENESS:
            template = f"Merci pour votre patience. {template}"
        
        # Génération de réponse LLM si nécessaire
        if fallback_type in [FallbackType.LLM_ERROR, FallbackType.UNKNOWN_ERROR]:
            try:
                llm_response = await self._generate_llm_fallback_response(
                    user_query, intent_result, template, company_context
                )
                if llm_response:
                    return llm_response
            except Exception as e:
                logger.warning(f"[FALLBACK_SYSTEM] Erreur génération LLM: {e}")
        
        return template
    
    async def _generate_llm_fallback_response(
        self,
        user_query: str,
        intent_result: IntentResult,
        base_template: str,
        company_context: Dict[str, Any] = None
    ) -> Optional[str]:
        """Génère une réponse de fallback via LLM"""
        
        prompt = f"""Tu es un assistant client professionnel. Génère une réponse de fallback appropriée.

CONTEXTE:
- Question utilisateur: "{user_query}"
- Intention détectée: {intent_result.primary_intent.value}
- Template de base: "{base_template}"

CONTEXTE ENTREPRISE:
{json.dumps(company_context, ensure_ascii=False) if company_context else "Non disponible"}

RÈGLES:
1. Sois professionnel et empathique
2. Reste dans le contexte de l'intention détectée
3. Propose des alternatives utiles
4. Garde la réponse concise (max 100 mots)

RÉPONSE:"""
        
        try:
            response = await asyncio.wait_for(
                self.llm_client.complete(prompt, temperature=0.7, max_tokens=150),
                timeout=5.0
            )
            return response.strip()
        except Exception as e:
            logger.warning(f"[FALLBACK_SYSTEM] Erreur LLM fallback: {e}")
            return None
    
    def _generate_suggested_actions(
        self,
        intent_result: IntentResult,
        fallback_type: FallbackType,
        criticality_level: str
    ) -> List[str]:
        """Génère des suggestions d'actions pour l'utilisateur"""
        
        suggestions = []
        
        # Suggestions basées sur l'intention
        if intent_result.primary_intent == IntentType.PRODUCT_INQUIRY:
            suggestions.extend([
                "Consultez notre catalogue en ligne",
                "Contactez notre service commercial",
                "Visitez notre magasin"
            ])
        elif intent_result.primary_intent == IntentType.PRICING_INFO:
            suggestions.extend([
                "Demandez un devis personnalisé",
                "Contactez notre service commercial",
                "Consultez nos offres promotionnelles"
            ])
        elif intent_result.primary_intent == IntentType.DELIVERY_INFO:
            suggestions.extend([
                "Vérifiez les zones de livraison",
                "Contactez notre service logistique",
                "Consultez nos conditions de livraison"
            ])
        elif intent_result.primary_intent == IntentType.SUPPORT_CONTACT:
            suggestions.extend([
                "Appelez notre service client",
                "Envoyez un email de support",
                "Utilisez notre chat en direct"
            ])
        
        # Suggestions basées sur le type de fallback
        if fallback_type == FallbackType.NO_DOCUMENTS:
            suggestions.extend([
                "Reformulez votre question",
                "Donnez plus de détails",
                "Contactez notre support"
            ])
        elif fallback_type == FallbackType.LLM_ERROR:
            suggestions.extend([
                "Réessayez dans quelques instants",
                "Contactez notre support technique",
                "Utilisez un autre canal de communication"
            ])
        elif fallback_type == FallbackType.TIMEOUT:
            suggestions.extend([
                "Réessayez plus tard",
                "Contactez notre support",
                "Utilisez notre site web"
            ])
        
        # Suggestions basées sur la criticité
        if criticality_level == 'critical':
            suggestions.extend([
                "Contactez immédiatement notre support",
                "Appelez notre numéro d'urgence",
                "Demandez à parler à un expert"
            ])
        
        return suggestions[:5]  # Limiter à 5 suggestions
    
    def _requires_escalation(self, fallback_type: FallbackType, criticality_level: str) -> bool:
        """Détermine si une escalation est nécessaire"""
        
        # Escalation pour les erreurs critiques
        if fallback_type in [FallbackType.LLM_ERROR, FallbackType.UNKNOWN_ERROR]:
            return True
        
        # Escalation pour les intentions critiques
        if criticality_level == 'critical':
            return True
        
        # Escalation pour les erreurs répétées
        if self._is_repeated_failure(fallback_type):
            return True
        
        return False
    
    def _is_repeated_failure(self, fallback_type: FallbackType) -> bool:
        """Vérifie si c'est un échec répété"""
        key = f"{fallback_type.value}_count"
        count = self.failure_stats.get(key, 0)
        return count >= 3  # Seuil de 3 échecs consécutifs
    
    def _calculate_fallback_confidence(
        self,
        intent_result: IntentResult,
        fallback_type: FallbackType
    ) -> float:
        """Calcule la confiance de la réponse de fallback"""
        
        base_confidence = 0.5
        
        # Ajustement basé sur l'intention
        if intent_result.primary_intent in [IntentType.SOCIAL_GREETING, IntentType.POLITENESS]:
            base_confidence += 0.3
        elif intent_result.primary_intent in [IntentType.PRODUCT_INQUIRY, IntentType.PRICING_INFO]:
            base_confidence += 0.2
        
        # Ajustement basé sur le type de fallback
        if fallback_type == FallbackType.NO_DOCUMENTS:
            base_confidence += 0.2
        elif fallback_type == FallbackType.LOW_CONFIDENCE:
            base_confidence += 0.1
        elif fallback_type in [FallbackType.LLM_ERROR, FallbackType.UNKNOWN_ERROR]:
            base_confidence -= 0.2
        
        return max(0.0, min(1.0, base_confidence))
    
    def _update_failure_stats(self, fallback_type: FallbackType, intent: IntentType):
        """Met à jour les statistiques d'échec"""
        key = f"{fallback_type.value}_count"
        self.failure_stats[key] = self.failure_stats.get(key, 0) + 1
        
        # Reset périodique des compteurs
        if self.failure_stats[key] > 10:
            self.failure_stats[key] = 0
    
    def get_failure_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques d'échec"""
        return {
            'stats': self.failure_stats.copy(),
            'total_failures': sum(self.failure_stats.values()),
            'most_common_failure': max(self.failure_stats.items(), key=lambda x: x[1])[0] if self.failure_stats else None
        }
    
    def clear_cache(self):
        """Vide le cache de fallback"""
        self.fallback_cache.clear()
        logger.info("[FALLBACK_SYSTEM] Cache de fallback vidé")

# Instance globale
fallback_system = IntelligentFallbackSystem()

# Fonction d'interface pour compatibilité
async def generate_intelligent_fallback(
    user_query: str,
    intent_result: IntentResult,
    error_context: Dict[str, Any] = None,
    company_context: Dict[str, Any] = None
) -> FallbackResponse:
    """Interface simplifiée pour la génération de fallback"""
    return await fallback_system.generate_fallback_response(
        user_query, intent_result, error_context, company_context
    )

if __name__ == "__main__":
    # Test du système de fallback
    async def test_fallback():
        from .advanced_intent_classifier import IntentType, IntentResult
        
        # Test avec intention sociale
        social_intent = IntentResult(
            primary_intent=IntentType.SOCIAL_GREETING,
            confidence=0.9,
            all_intents={},
            requires_documents=False,
            is_critical=False,
            fallback_required=False,
            context_hints=[],
            processing_time_ms=0.0
        )
        
        result = await generate_intelligent_fallback(
            "Comment tu t'appelles ?",
            social_intent,
            {'error': 'no_documents found'},
            {'company_name': 'Rue du Gros', 'ai_name': 'Gamma'}
        )
        
        print(f"Fallback: {result.response}")
        print(f"Actions suggérées: {result.suggested_actions}")
    
    asyncio.run(test_fallback())
