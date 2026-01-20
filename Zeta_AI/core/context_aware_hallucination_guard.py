#!/usr/bin/env python3
"""
🛡️ GARDE-FOU ANTI-HALLUCINATION CONTEXTUEL 2024
Système de validation avancé basé sur les meilleures pratiques enterprise
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
from .llm_client import GroqLLMClient

logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    """Niveaux de validation"""
    STRICT = "strict"        # Validation stricte (intentions critiques)
    MODERATE = "moderate"    # Validation modérée (intentions métier)
    LENIENT = "lenient"      # Validation permissive (intentions sociales)
    BYPASS = "bypass"        # Pas de validation (conversations générales)

@dataclass
class ValidationResult:
    """Résultat de validation contextuelle"""
    is_safe: bool
    confidence_score: float
    validation_level: ValidationLevel
    intent_detected: IntentType
    requires_documents: bool
    documents_found: bool
    context_relevance: float
    factual_accuracy: float
    safety_score: float
    suggested_response: Optional[str] = None
    rejection_reason: Optional[str] = None
    processing_time_ms: float = 0.0
    validation_details: Dict[str, Any] = None

class ContextAwareHallucinationGuard:
    """
    🛡️ GARDE-FOU ANTI-HALLUCINATION CONTEXTUEL 2024
    
    Fonctionnalités avancées :
    1. Validation contextuelle intelligente
    2. Seuils de confiance adaptatifs
    3. Gestion des intentions sociales vs métier
    4. Validation factuelle multi-niveaux
    5. Système de fallback intelligent
    """
    
    def __init__(self):
        self.llm_client = GroqLLMClient()
        self.start_time = datetime.now()
        
        # Seuils de validation adaptatifs
        self.validation_thresholds = {
            ValidationLevel.STRICT: {
                'min_confidence': 0.9,
                'min_documents': 1,
                'min_relevance': 0.8,
                'min_factual': 0.9
            },
            ValidationLevel.MODERATE: {
                'min_confidence': 0.7,
                'min_documents': 1,
                'min_relevance': 0.6,
                'min_factual': 0.7
            },
            ValidationLevel.LENIENT: {
                'min_confidence': 0.5,
                'min_documents': 0,
                'min_relevance': 0.4,
                'min_factual': 0.5
            },
            ValidationLevel.BYPASS: {
                'min_confidence': 0.0,
                'min_documents': 0,
                'min_relevance': 0.0,
                'min_factual': 0.0
            }
        }
        
        # Patterns de validation
        self.validation_patterns = self._build_validation_patterns()
        
        # Cache des validations
        self.validation_cache = {}
        self.cache_ttl = 1800  # 30 minutes
        
        logger.info("[CONTEXT_GUARD] Système de validation contextuel initialisé")
    
    def _build_validation_patterns(self) -> Dict[str, List[str]]:
        """Construit les patterns de validation"""
        return {
            'dangerous_claims': [
                r'(?i)(nous\s+garantissons|we\s+guarantee)(?!\s+(selon|d\'après))',
                r'(?i)(prix\s+fixe|fixed\s+price)(?!\s+(mentionné|indiqué))',
                r'(?i)(disponible\s+immédiatement|available\s+now)(?!\s+(selon))',
                r'(?i)(livraison\s+gratuite|free\s+shipping)(?!\s+(dans|pour))',
                r'(?i)(promotion\s+exclusive|exclusive\s+offer)(?!\s+(valable))'
            ],
            'factual_claims': [
                r'(?i)(prix|price)\s+est\s+(\d+)',
                r'(?i)(stock|inventory)\s+est\s+(\d+)',
                r'(?i)(livraison|delivery)\s+en\s+(\d+)\s+jours',
                r'(?i)(garantie|warranty)\s+de\s+(\d+)\s+ans',
                r'(?i)(dimensions|size)\s+sont\s+(\d+)'
            ],
            'social_responses': [
                r'(?i)(je\s+m\'appelle|my\s+name\s+is)',
                r'(?i)(bonjour|hello|hi)',
                r'(?i)(merci|thank\s+you)',
                r'(?i)(comment\s+allez-vous|how\s+are\s+you)',
                r'(?i)(de\s+rien|you\'re\s+welcome)'
            ]
        }
    
    async def validate_response(
        self,
        user_query: str,
        ai_response: str,
        intent_result: IntentResult,
        supabase_results: List[Dict] = None,
        meili_results: List[Dict] = None,
        supabase_context: str = "",
        meili_context: str = "",
        company_id: str = ""
    ) -> ValidationResult:
        """
        🎯 VALIDATION CONTEXTUELLE AVANCÉE
        
        Pipeline de validation adaptatif basé sur l'intention détectée
        """
        start_time = time.time()
        
        logger.info(f"[CONTEXT_GUARD] Validation: '{ai_response[:50]}...' (intent: {intent_result.primary_intent.value})")
        
        # Détermination du niveau de validation
        validation_level = self._determine_validation_level(intent_result)
        
        # Vérification du cache
        cache_key = self._generate_cache_key(user_query, ai_response, intent_result.primary_intent)
        if cache_key in self.validation_cache:
            cached_result = self.validation_cache[cache_key]
            if (datetime.now() - cached_result['timestamp']).seconds < self.cache_ttl:
                return cached_result['result']
        
        # Pipeline de validation adaptatif
        if validation_level == ValidationLevel.BYPASS:
            result = self._bypass_validation(intent_result, ai_response)
        elif validation_level == ValidationLevel.LENIENT:
            result = await self._lenient_validation(
                user_query, ai_response, intent_result, 
                supabase_results, meili_results, supabase_context, meili_context
            )
        elif validation_level == ValidationLevel.MODERATE:
            result = await self._moderate_validation(
                user_query, ai_response, intent_result,
                supabase_results, meili_results, supabase_context, meili_context
            )
        else:  # STRICT
            result = await self._strict_validation(
                user_query, ai_response, intent_result,
                supabase_results, meili_results, supabase_context, meili_context
            )
        
        # Calcul du temps de traitement
        result.processing_time_ms = (time.time() - start_time) * 1000
        
        # Mise en cache
        self.validation_cache[cache_key] = {
            'result': result,
            'timestamp': datetime.now()
        }
        
        logger.info(f"[CONTEXT_GUARD] Validation terminée: {result.is_safe} (conf: {result.confidence_score:.2f})")
        
        return result
    
    def _determine_validation_level(self, intent_result: IntentResult) -> ValidationLevel:
        """Détermine le niveau de validation basé sur l'intention"""
        intent = intent_result.primary_intent
        confidence = intent_result.confidence
        
        # Intentions critiques → Validation stricte
        if intent in [IntentType.TECHNICAL_SPECS, IntentType.MEDICAL_ADVICE, IntentType.FINANCIAL_ADVICE]:
            return ValidationLevel.STRICT
        
        # Intentions métier avec confiance élevée → Validation modérée
        if intent in [IntentType.PRODUCT_INQUIRY, IntentType.PRICING_INFO, IntentType.DELIVERY_INFO]:
            if confidence >= 0.7:
                return ValidationLevel.MODERATE
            else:
                return ValidationLevel.STRICT
        
        # Intentions sociales avec confiance élevée → Validation permissive
        if intent in [IntentType.SOCIAL_GREETING, IntentType.POLITENESS, IntentType.GENERAL_CONVERSATION]:
            if confidence >= 0.6:
                return ValidationLevel.LENIENT
            else:
                return ValidationLevel.BYPASS
        
        # Intentions hors-sujet → Pas de validation
        if intent == IntentType.OFF_TOPIC:
            return ValidationLevel.BYPASS
        
        # Fallback → Validation permissive
        return ValidationLevel.LENIENT
    
    def _bypass_validation(self, intent_result: IntentResult, ai_response: str) -> ValidationResult:
        """Validation bypass pour les conversations sociales"""
        return ValidationResult(
            is_safe=True,
            confidence_score=0.9,
            validation_level=ValidationLevel.BYPASS,
            intent_detected=intent_result.primary_intent,
            requires_documents=False,
            documents_found=False,
            context_relevance=0.8,
            factual_accuracy=0.7,
            safety_score=0.9,
            processing_time_ms=0.0,
            validation_details={'bypass_reason': 'social_conversation'}
        )
    
    async def _lenient_validation(
        self, user_query: str, ai_response: str, intent_result: IntentResult,
        supabase_results: List[Dict], meili_results: List[Dict], 
        supabase_context: str, meili_context: str
    ) -> ValidationResult:
        """Validation permissive pour les intentions sociales"""
        
        # Vérification des patterns dangereux
        dangerous_patterns = self.validation_patterns['dangerous_claims']
        has_dangerous_claims = any(re.search(pattern, ai_response) for pattern in dangerous_patterns)
        
        # Vérification des patterns sociaux
        social_patterns = self.validation_patterns['social_responses']
        has_social_patterns = any(re.search(pattern, ai_response) for pattern in social_patterns)
        
        # Score de sécurité basé sur les patterns
        safety_score = 0.8 if has_social_patterns else 0.6
        if has_dangerous_claims:
            safety_score = 0.2
        
        is_safe = safety_score >= 0.5 and not has_dangerous_claims
        
        return ValidationResult(
            is_safe=is_safe,
            confidence_score=0.7,
            validation_level=ValidationLevel.LENIENT,
            intent_detected=intent_result.primary_intent,
            requires_documents=False,
            documents_found=False,
            context_relevance=0.6,
            factual_accuracy=0.6,
            safety_score=safety_score,
            suggested_response=None if is_safe else "Je ne peux pas répondre à cette question de manière appropriée.",
            rejection_reason=None if is_safe else "Patterns dangereux détectés",
            validation_details={
                'has_dangerous_claims': has_dangerous_claims,
                'has_social_patterns': has_social_patterns,
                'safety_score': safety_score
            }
        )
    
    async def _moderate_validation(
        self, user_query: str, ai_response: str, intent_result: IntentResult,
        supabase_results: List[Dict], meili_results: List[Dict], 
        supabase_context: str, meili_context: str
    ) -> ValidationResult:
        """Validation modérée pour les intentions métier"""
        
        # Vérification de la présence de documents
        documents_found = bool(
            (supabase_results and len(supabase_results) > 0) or
            (meili_results and len(meili_results) > 0) or
            (supabase_context and len(supabase_context.strip()) > 10) or
            (meili_context and len(meili_context.strip()) > 10)
        )
        
        # Validation LLM simplifiée
        llm_validation = await self._llm_validation(user_query, ai_response, supabase_context, meili_context, "moderate")
        
        # Score de confiance combiné
        confidence_score = 0.6
        if documents_found:
            confidence_score += 0.2
        if llm_validation['is_safe']:
            confidence_score += 0.2
        
        is_safe = confidence_score >= 0.7 and llm_validation['is_safe']
        
        return ValidationResult(
            is_safe=is_safe,
            confidence_score=confidence_score,
            validation_level=ValidationLevel.MODERATE,
            intent_detected=intent_result.primary_intent,
            requires_documents=True,
            documents_found=documents_found,
            context_relevance=0.7,
            factual_accuracy=0.7,
            safety_score=0.7,
            suggested_response=llm_validation.get('suggested_response'),
            rejection_reason=llm_validation.get('rejection_reason'),
            validation_details={
                'documents_found': documents_found,
                'llm_validation': llm_validation
            }
        )
    
    async def _strict_validation(
        self, user_query: str, ai_response: str, intent_result: IntentResult,
        supabase_results: List[Dict], meili_results: List[Dict], 
        supabase_context: str, meili_context: str
    ) -> ValidationResult:
        """Validation stricte pour les intentions critiques"""
        
        # Vérification de la présence de documents
        documents_found = bool(
            (supabase_results and len(supabase_results) > 0) or
            (meili_results and len(meili_results) > 0) or
            (supabase_context and len(supabase_context.strip()) > 10) or
            (meili_context and len(meili_context.strip()) > 10)
        )
        
        # Validation LLM stricte
        llm_validation = await self._llm_validation(user_query, ai_response, supabase_context, meili_context, "strict")
        
        # Score de confiance strict
        confidence_score = 0.3
        if documents_found:
            confidence_score += 0.3
        if llm_validation['is_safe']:
            confidence_score += 0.4
        
        is_safe = confidence_score >= 0.8 and llm_validation['is_safe'] and documents_found
        
        return ValidationResult(
            is_safe=is_safe,
            confidence_score=confidence_score,
            validation_level=ValidationLevel.STRICT,
            intent_detected=intent_result.primary_intent,
            requires_documents=True,
            documents_found=documents_found,
            context_relevance=0.8,
            factual_accuracy=0.8,
            safety_score=0.8,
            suggested_response=llm_validation.get('suggested_response'),
            rejection_reason=llm_validation.get('rejection_reason'),
            validation_details={
                'documents_found': documents_found,
                'llm_validation': llm_validation,
                'strict_mode': True
            }
        )
    
    async def _llm_validation(
        self, user_query: str, ai_response: str, context: str, meili_context: str, mode: str
    ) -> Dict[str, Any]:
        """Validation par LLM"""
        
        # Prompt adaptatif selon le mode
        if mode == "strict":
            prompt = self._create_strict_validation_prompt(user_query, ai_response, context, meili_context)
        else:
            prompt = self._create_moderate_validation_prompt(user_query, ai_response, context, meili_context)
        
        try:
            # Appel LLM avec timeout
            judge_response = await asyncio.wait_for(
                self.llm_client.complete(prompt, temperature=0.0, max_tokens=200),
                timeout=10.0
            )
            
            # Analyse de la réponse
            is_accepted = "ACCEPTER" in judge_response.upper()
            
            return {
                'is_safe': is_accepted,
                'judge_response': judge_response,
                'suggested_response': None if is_accepted else self._generate_safe_response(user_query),
                'rejection_reason': None if is_accepted else "Validation LLM échouée"
            }
            
        except asyncio.TimeoutError:
            logger.warning("[CONTEXT_GUARD] Timeout validation LLM")
            return {
                'is_safe': False,
                'judge_response': "TIMEOUT",
                'suggested_response': "Je ne peux pas valider cette réponse actuellement.",
                'rejection_reason': "Timeout validation LLM"
            }
        except Exception as e:
            logger.error(f"[CONTEXT_GUARD] Erreur validation LLM: {e}")
            return {
                'is_safe': False,
                'judge_response': f"ERROR: {str(e)}",
                'suggested_response': "Erreur de validation.",
                'rejection_reason': f"Erreur LLM: {str(e)}"
            }
    
    def _create_strict_validation_prompt(self, user_query: str, ai_response: str, context: str, meili_context: str) -> str:
        """Crée un prompt de validation stricte"""
        return f"""Tu es un juge expert anti-hallucination TRÈS STRICT.

CONTEXTE:
- Question utilisateur: "{user_query}"
- Status documents: {"DOCUMENTS TROUVÉS" if context or meili_context else "AUCUN DOCUMENT TROUVÉ"}
- Mode: VALIDATION STRICTE

RÉPONSE À JUGER:
{ai_response}

DOCUMENTS DE RÉFÉRENCE:
{context[:1000] if context else "AUCUN CONTEXTE DISPONIBLE"}

RÈGLES STRICTES:
1. Si AUCUN DOCUMENT: REJETER immédiatement
2. Tous les faits doivent être dans les documents
3. AUCUNE invention de prix, stock, ou détails techniques
4. Les chiffres doivent être exacts

DÉCISION: Réponds UNIQUEMENT par:
- "ACCEPTER" si la réponse est fidèle aux documents
- "REJETER: [raison précise]" si elle invente ou déforme des informations

Sois IMPITOYABLE - en cas de doute, REJETER."""
    
    def _create_moderate_validation_prompt(self, user_query: str, ai_response: str, context: str, meili_context: str) -> str:
        """Crée un prompt de validation modérée"""
        return f"""Tu es un juge expert anti-hallucination MODÉRÉ.

CONTEXTE:
- Question utilisateur: "{user_query}"
- Status documents: {"DOCUMENTS TROUVÉS" if context or meili_context else "AUCUN DOCUMENT TROUVÉ"}

RÉPONSE À JUGER:
{ai_response}

DOCUMENTS DE RÉFÉRENCE:
{context[:500] if context else "AUCUN CONTEXTE DISPONIBLE"}

RÈGLES MODÉRÉES:
1. Si documents disponibles: vérifier la cohérence
2. Si pas de documents: permettre réponse générale
3. Rejeter seulement les affirmations manifestement fausses

DÉCISION: Réponds UNIQUEMENT par:
- "ACCEPTER" si la réponse est appropriée
- "REJETER: [raison précise]" si elle contient des erreurs flagrantes"""
    
    def _generate_safe_response(self, user_query: str) -> str:
        """Génère une réponse sécurisée de fallback"""
        safe_responses = {
            "greeting": "Bonjour ! Comment puis-je vous aider aujourd'hui ?",
            "question": "Je ne peux pas répondre à cette question avec certitude. Pouvez-vous contacter notre service client ?",
            "general": "Je ne suis pas sûr de la réponse. Pouvez-vous reformuler votre question ?"
        }
        
        # Détection simple du type de question
        if any(word in user_query.lower() for word in ['bonjour', 'salut', 'hello']):
            return safe_responses['greeting']
        elif '?' in user_query:
            return safe_responses['question']
        else:
            return safe_responses['general']
    
    def _generate_cache_key(self, user_query: str, ai_response: str, intent: IntentType) -> str:
        """Génère une clé de cache"""
        import hashlib
        key_data = f"{user_query}_{ai_response}_{intent.value}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def clear_cache(self):
        """Vide le cache de validation"""
        self.validation_cache.clear()
        logger.info("[CONTEXT_GUARD] Cache de validation vidé")

# Instance globale
context_guard = ContextAwareHallucinationGuard()

# Fonction d'interface pour compatibilité
async def validate_response_contextual(
    user_query: str,
    ai_response: str,
    intent_result: IntentResult,
    supabase_results: List[Dict] = None,
    meili_results: List[Dict] = None,
    supabase_context: str = "",
    meili_context: str = "",
    company_id: str = ""
) -> ValidationResult:
    """Interface simplifiée pour la validation contextuelle"""
    return await context_guard.validate_response(
        user_query, ai_response, intent_result,
        supabase_results, meili_results, supabase_context, meili_context, company_id
    )

if __name__ == "__main__":
    # Test du garde-fou contextuel
    async def test_guard():
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
        
        result = await validate_response_contextual(
            "Comment tu t'appelles ?",
            "Je m'appelle Gamma, votre assistant client.",
            social_intent
        )
        
        print(f"Validation sociale: {result.is_safe} (conf: {result.confidence_score:.2f})")
    
    asyncio.run(test_guard())
