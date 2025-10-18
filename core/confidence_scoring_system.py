#!/usr/bin/env python3
"""
📊 SYSTÈME DE SCORING DE CONFIANCE 2024
Système de scoring de confiance avancé basé sur les meilleures pratiques
"""

import asyncio
import time
import json
import re
import math
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime

from .advanced_intent_classifier import IntentType, IntentResult

logger = logging.getLogger(__name__)

class ConfidenceLevel(Enum):
    """Niveaux de confiance"""
    VERY_HIGH = "very_high"    # 0.9-1.0
    HIGH = "high"              # 0.8-0.9
    MEDIUM = "medium"          # 0.6-0.8
    LOW = "low"                # 0.4-0.6
    VERY_LOW = "very_low"      # 0.0-0.4

@dataclass
class ConfidenceScore:
    """Score de confiance détaillé"""
    overall_confidence: float
    confidence_level: ConfidenceLevel
    intent_confidence: float
    document_confidence: float
    context_confidence: float
    factual_confidence: float
    safety_confidence: float
    reliability_score: float
    risk_level: str
    recommendations: List[str]
    processing_time_ms: float

class ConfidenceScoringSystem:
    """
    📊 SYSTÈME DE SCORING DE CONFIANCE 2024
    
    Fonctionnalités avancées :
    1. Scoring multi-dimensionnel
    2. Pondération adaptative
    3. Détection des risques
    4. Recommandations automatiques
    5. Apprentissage des patterns
    """
    
    def __init__(self):
        self.start_time = datetime.now()
        
        # Poids des différents facteurs
        self.confidence_weights = {
            'intent': 0.25,      # Confiance de l'intention
            'documents': 0.30,   # Présence et qualité des documents
            'context': 0.20,     # Pertinence contextuelle
            'factual': 0.15,     # Exactitude factuelle
            'safety': 0.10       # Score de sécurité
        }
        
        # Seuils de confiance
        self.confidence_thresholds = {
            ConfidenceLevel.VERY_HIGH: 0.9,
            ConfidenceLevel.HIGH: 0.8,
            ConfidenceLevel.MEDIUM: 0.6,
            ConfidenceLevel.LOW: 0.4,
            ConfidenceLevel.VERY_LOW: 0.0
        }
        
        # Patterns de risque
        self.risk_patterns = self._build_risk_patterns()
        
        # Cache des scores
        self.score_cache = {}
        self.cache_ttl = 1800  # 30 minutes
        
        logger.info("[CONFIDENCE_SCORING] Système de scoring de confiance initialisé")
    
    def _build_risk_patterns(self) -> Dict[str, List[str]]:
        """Construit les patterns de détection de risque"""
        return {
            'high_risk': [
                r'(?i)(garantie|warranty)\s+(\d+)\s+(ans|years)',
                r'(?i)(prix|price)\s+(\d+)\s+(euros?|€)',
                r'(?i)(livraison|delivery)\s+(\d+)\s+(heures?|hours)',
                r'(?i)(stock|inventory)\s+(\d+)\s+(unités?|units)',
                r'(?i)(promotion|discount)\s+(\d+)%'
            ],
            'medium_risk': [
                r'(?i)(nous\s+recommandons|we\s+recommend)',
                r'(?i)(le\s+meilleur|the\s+best)',
                r'(?i)(exclusif|exclusive)',
                r'(?i)(limité|limited)',
                r'(?i)(spécial|special)'
            ],
            'low_risk': [
                r'(?i)(peut-être|maybe)',
                r'(?i)(probablement|probably)',
                r'(?i)(semble|seems)',
                r'(?i)(je\s+pense|i\s+think)',
                r'(?i)(il\s+est\s+possible|it\'s\s+possible)'
            ]
        }
    
    async def calculate_confidence_score(
        self,
        user_query: str,
        ai_response: str,
        intent_result: IntentResult,
        supabase_results: List[Dict] = None,
        meili_results: List[Dict] = None,
        supabase_context: str = "",
        meili_context: str = "",
        validation_result: Dict[str, Any] = None
    ) -> ConfidenceScore:
        """
        📊 CALCUL DE SCORE DE CONFIANCE MULTI-DIMENSIONNEL
        
        Args:
            user_query: Question utilisateur
            ai_response: Réponse générée
            intent_result: Résultat de classification d'intention
            supabase_results: Résultats Supabase
            meili_results: Résultats MeiliSearch
            supabase_context: Contexte Supabase
            meili_context: Contexte MeiliSearch
            validation_result: Résultat de validation
            
        Returns:
            ConfidenceScore: Score de confiance détaillé
        """
        start_time = time.time()
        
        # Vérification du cache
        cache_key = self._generate_cache_key(user_query, ai_response, intent_result.primary_intent)
        if cache_key in self.score_cache:
            cached_result = self.score_cache[cache_key]
            if (datetime.now() - cached_result['timestamp']).seconds < self.cache_ttl:
                return cached_result['result']
        
        # Calcul des scores individuels
        intent_confidence = self._calculate_intent_confidence(intent_result)
        document_confidence = self._calculate_document_confidence(
            supabase_results, meili_results, supabase_context, meili_context
        )
        context_confidence = self._calculate_context_confidence(
            user_query, ai_response, intent_result
        )
        factual_confidence = self._calculate_factual_confidence(
            ai_response, supabase_context, meili_context
        )
        safety_confidence = self._calculate_safety_confidence(
            ai_response, validation_result
        )
        
        # Calcul du score global pondéré
        overall_confidence = (
            intent_confidence * self.confidence_weights['intent'] +
            document_confidence * self.confidence_weights['documents'] +
            context_confidence * self.confidence_weights['context'] +
            factual_confidence * self.confidence_weights['factual'] +
            safety_confidence * self.confidence_weights['safety']
        )
        
        # Détermination du niveau de confiance
        confidence_level = self._determine_confidence_level(overall_confidence)
        
        # Calcul du score de fiabilité
        reliability_score = self._calculate_reliability_score(
            overall_confidence, intent_result, document_confidence
        )
        
        # Détermination du niveau de risque
        risk_level = self._determine_risk_level(ai_response, overall_confidence)
        
        # Génération des recommandations
        recommendations = self._generate_recommendations(
            overall_confidence, confidence_level, risk_level, intent_result
        )
        
        # Création du résultat
        result = ConfidenceScore(
            overall_confidence=overall_confidence,
            confidence_level=confidence_level,
            intent_confidence=intent_confidence,
            document_confidence=document_confidence,
            context_confidence=context_confidence,
            factual_confidence=factual_confidence,
            safety_confidence=safety_confidence,
            reliability_score=reliability_score,
            risk_level=risk_level,
            recommendations=recommendations,
            processing_time_ms=(time.time() - start_time) * 1000
        )
        
        # Mise en cache
        self.score_cache[cache_key] = {
            'result': result,
            'timestamp': datetime.now()
        }
        
        logger.info(f"[CONFIDENCE_SCORING] Score calculé: {overall_confidence:.3f} ({confidence_level.value})")
        
        return result
    
    def _calculate_intent_confidence(self, intent_result: IntentResult) -> float:
        """Calcule la confiance basée sur l'intention"""
        base_confidence = intent_result.confidence
        
        # Bonus pour les intentions bien définies
        if intent_result.primary_intent in [IntentType.SOCIAL_GREETING, IntentType.POLITENESS]:
            base_confidence += 0.1
        
        # Malus pour les intentions ambiguës
        if intent_result.fallback_required:
            base_confidence -= 0.2
        
        # Bonus pour les indices contextuels
        if intent_result.context_hints:
            base_confidence += 0.05 * len(intent_result.context_hints)
        
        return max(0.0, min(1.0, base_confidence))
    
    def _calculate_document_confidence(
        self,
        supabase_results: List[Dict],
        meili_results: List[Dict],
        supabase_context: str,
        meili_context: str
    ) -> float:
        """Calcule la confiance basée sur les documents"""
        
        # Vérification de la présence de documents
        has_supabase = bool(supabase_results and len(supabase_results) > 0)
        has_meili = bool(meili_results and len(meili_results) > 0)
        has_context = bool(supabase_context or meili_context)
        
        if not (has_supabase or has_meili or has_context):
            return 0.0
        
        # Score de base
        confidence = 0.5
        
        # Bonus pour la présence de documents
        if has_supabase:
            confidence += 0.2
        if has_meili:
            confidence += 0.2
        if has_context:
            confidence += 0.1
        
        # Bonus pour la qualité du contexte
        context_length = len(supabase_context) + len(meili_context)
        if context_length > 1000:
            confidence += 0.1
        elif context_length > 500:
            confidence += 0.05
        
        # Bonus pour la diversité des sources
        source_count = sum([has_supabase, has_meili, has_context])
        if source_count > 1:
            confidence += 0.1
        
        return max(0.0, min(1.0, confidence))
    
    def _calculate_context_confidence(
        self,
        user_query: str,
        ai_response: str,
        intent_result: IntentResult
    ) -> float:
        """Calcule la confiance basée sur la pertinence contextuelle"""
        
        # Vérification de la cohérence sémantique
        semantic_coherence = self._calculate_semantic_coherence(user_query, ai_response)
        
        # Vérification de la pertinence à l'intention
        intent_relevance = self._calculate_intent_relevance(user_query, ai_response, intent_result)
        
        # Vérification de la complétude de la réponse
        completeness = self._calculate_response_completeness(user_query, ai_response)
        
        # Score combiné
        context_confidence = (
            semantic_coherence * 0.4 +
            intent_relevance * 0.4 +
            completeness * 0.2
        )
        
        return max(0.0, min(1.0, context_confidence))
    
    def _calculate_semantic_coherence(self, user_query: str, ai_response: str) -> float:
        """Calcule la cohérence sémantique entre la question et la réponse"""
        
        # Extraction des mots-clés de la question
        query_words = set(re.findall(r'\w+', user_query.lower()))
        
        # Extraction des mots-clés de la réponse
        response_words = set(re.findall(r'\w+', ai_response.lower()))
        
        # Calcul de l'intersection
        common_words = query_words.intersection(response_words)
        
        if not query_words:
            return 0.5
        
        # Score de cohérence
        coherence_score = len(common_words) / len(query_words)
        
        return min(1.0, coherence_score)
    
    def _calculate_intent_relevance(
        self,
        user_query: str,
        ai_response: str,
        intent_result: IntentResult
    ) -> float:
        """Calcule la pertinence de la réponse à l'intention détectée"""
        
        intent = intent_result.primary_intent
        
        # Patterns de pertinence par intention
        relevance_patterns = {
            IntentType.SOCIAL_GREETING: [
                r'(?i)(bonjour|hello|salut|hi)',
                r'(?i)(comment\s+allez-vous|how\s+are\s+you)',
                r'(?i)(je\s+m\'appelle|my\s+name\s+is)'
            ],
            IntentType.PRODUCT_INQUIRY: [
                r'(?i)(produit|product)',
                r'(?i)(catalogue|catalog)',
                r'(?i)(disponible|available)',
                r'(?i)(stock|inventory)'
            ],
            IntentType.PRICING_INFO: [
                r'(?i)(prix|price)',
                r'(?i)(coût|cost)',
                r'(?i)(tarif|rate)',
                r'(?i)(euros?|€)'
            ],
            IntentType.DELIVERY_INFO: [
                r'(?i)(livraison|delivery)',
                r'(?i)(expédition|shipping)',
                r'(?i)(délai|delay)',
                r'(?i)(zone|area)'
            ]
        }
        
        if intent not in relevance_patterns:
            return 0.5
        
        # Vérification des patterns de pertinence
        patterns = relevance_patterns[intent]
        matches = sum(1 for pattern in patterns if re.search(pattern, ai_response))
        
        # Score de pertinence
        relevance_score = matches / len(patterns) if patterns else 0.5
        
        return min(1.0, relevance_score)
    
    def _calculate_response_completeness(self, user_query: str, ai_response: str) -> float:
        """Calcule la complétude de la réponse"""
        
        # Vérification de la présence de questions
        has_question = '?' in user_query
        
        # Vérification de la longueur de la réponse
        response_length = len(ai_response)
        
        # Score de complétude basé sur la longueur
        if response_length < 20:
            completeness = 0.3
        elif response_length < 50:
            completeness = 0.6
        elif response_length < 100:
            completeness = 0.8
        else:
            completeness = 1.0
        
        # Malus si la réponse est trop courte pour une question
        if has_question and response_length < 30:
            completeness *= 0.7
        
        return max(0.0, min(1.0, completeness))
    
    def _calculate_factual_confidence(
        self,
        ai_response: str,
        supabase_context: str,
        meili_context: str
    ) -> float:
        """Calcule la confiance factuelle de la réponse"""
        
        # Vérification de la présence de contexte
        has_context = bool(supabase_context or meili_context)
        
        if not has_context:
            return 0.3
        
        # Vérification des patterns de risque
        risk_score = self._calculate_risk_score(ai_response)
        
        # Score de confiance factuelle
        factual_confidence = 0.7 if has_context else 0.3
        factual_confidence -= risk_score * 0.3
        
        return max(0.0, min(1.0, factual_confidence))
    
    def _calculate_risk_score(self, ai_response: str) -> float:
        """Calcule le score de risque de la réponse"""
        
        risk_score = 0.0
        
        # Vérification des patterns de risque
        for risk_level, patterns in self.risk_patterns.items():
            for pattern in patterns:
                if re.search(pattern, ai_response):
                    if risk_level == 'high_risk':
                        risk_score += 0.3
                    elif risk_level == 'medium_risk':
                        risk_score += 0.2
                    elif risk_level == 'low_risk':
                        risk_score += 0.1
        
        return min(1.0, risk_score)
    
    def _calculate_safety_confidence(
        self,
        ai_response: str,
        validation_result: Dict[str, Any] = None
    ) -> float:
        """Calcule la confiance de sécurité de la réponse"""
        
        # Score de base
        safety_confidence = 0.8
        
        # Ajustement basé sur le résultat de validation
        if validation_result:
            if validation_result.get('is_safe', True):
                safety_confidence += 0.1
            else:
                safety_confidence -= 0.3
        
        # Vérification des patterns dangereux
        dangerous_patterns = [
            r'(?i)(garantie|warranty)\s+(\d+)\s+(ans|years)(?!\s+(selon|d\'après))',
            r'(?i)(prix|price)\s+(\d+)\s+(euros?|€)(?!\s+(selon|d\'après))',
            r'(?i)(livraison|delivery)\s+(\d+)\s+(heures?|hours)(?!\s+(selon|d\'après))'
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, ai_response):
                safety_confidence -= 0.2
        
        return max(0.0, min(1.0, safety_confidence))
    
    def _calculate_reliability_score(
        self,
        overall_confidence: float,
        intent_result: IntentResult,
        document_confidence: float
    ) -> float:
        """Calcule le score de fiabilité global"""
        
        # Score de base
        reliability = overall_confidence
        
        # Bonus pour les intentions bien définies
        if intent_result.confidence > 0.8:
            reliability += 0.1
        
        # Bonus pour la présence de documents
        if document_confidence > 0.7:
            reliability += 0.1
        
        # Malus pour les fallbacks
        if intent_result.fallback_required:
            reliability -= 0.2
        
        return max(0.0, min(1.0, reliability))
    
    def _determine_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Détermine le niveau de confiance"""
        
        if confidence >= self.confidence_thresholds[ConfidenceLevel.VERY_HIGH]:
            return ConfidenceLevel.VERY_HIGH
        elif confidence >= self.confidence_thresholds[ConfidenceLevel.HIGH]:
            return ConfidenceLevel.HIGH
        elif confidence >= self.confidence_thresholds[ConfidenceLevel.MEDIUM]:
            return ConfidenceLevel.MEDIUM
        elif confidence >= self.confidence_thresholds[ConfidenceLevel.LOW]:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW
    
    def _determine_risk_level(self, ai_response: str, confidence: float) -> str:
        """Détermine le niveau de risque"""
        
        risk_score = self._calculate_risk_score(ai_response)
        
        if risk_score > 0.5 or confidence < 0.4:
            return 'high'
        elif risk_score > 0.3 or confidence < 0.6:
            return 'medium'
        else:
            return 'low'
    
    def _generate_recommendations(
        self,
        confidence: float,
        confidence_level: ConfidenceLevel,
        risk_level: str,
        intent_result: IntentResult
    ) -> List[str]:
        """Génère des recommandations basées sur le score de confiance"""
        
        recommendations = []
        
        # Recommandations basées sur le niveau de confiance
        if confidence_level == ConfidenceLevel.VERY_LOW:
            recommendations.extend([
                "Vérifiez la classification d'intention",
                "Améliorez la qualité des documents",
                "Considérez un fallback manuel"
            ])
        elif confidence_level == ConfidenceLevel.LOW:
            recommendations.extend([
                "Augmentez le nombre de documents de référence",
                "Améliorez la pertinence contextuelle",
                "Vérifiez la cohérence sémantique"
            ])
        elif confidence_level == ConfidenceLevel.MEDIUM:
            recommendations.extend([
                "Optimisez la classification d'intention",
                "Améliorez la qualité du contexte",
                "Vérifiez la complétude de la réponse"
            ])
        
        # Recommandations basées sur le niveau de risque
        if risk_level == 'high':
            recommendations.extend([
                "Validation manuelle requise",
                "Vérification factuelle nécessaire",
                "Escalation vers un expert"
            ])
        elif risk_level == 'medium':
            recommendations.extend([
                "Surveillance renforcée",
                "Vérification périodique",
                "Amélioration des patterns de validation"
            ])
        
        # Recommandations spécifiques à l'intention
        if intent_result.primary_intent in [IntentType.TECHNICAL_SPECS, IntentType.MEDICAL_ADVICE]:
            recommendations.extend([
                "Validation experte obligatoire",
                "Vérification des sources techniques",
                "Documentation des décisions"
            ])
        
        return recommendations[:5]  # Limiter à 5 recommandations
    
    def _generate_cache_key(self, user_query: str, ai_response: str, intent: IntentType) -> str:
        """Génère une clé de cache"""
        import hashlib
        key_data = f"{user_query}_{ai_response}_{intent.value}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def clear_cache(self):
        """Vide le cache de scores"""
        self.score_cache.clear()
        logger.info("[CONFIDENCE_SCORING] Cache de scores vidé")
    
    def get_confidence_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de confiance"""
        if not self.score_cache:
            return {'message': 'Aucune donnée disponible'}
        
        scores = [result['result'].overall_confidence for result in self.score_cache.values()]
        
        return {
            'total_scores': len(scores),
            'average_confidence': sum(scores) / len(scores) if scores else 0,
            'min_confidence': min(scores) if scores else 0,
            'max_confidence': max(scores) if scores else 0,
            'confidence_distribution': {
                'very_high': len([s for s in scores if s >= 0.9]),
                'high': len([s for s in scores if 0.8 <= s < 0.9]),
                'medium': len([s for s in scores if 0.6 <= s < 0.8]),
                'low': len([s for s in scores if 0.4 <= s < 0.6]),
                'very_low': len([s for s in scores if s < 0.4])
            }
        }

# Instance globale
confidence_scoring = ConfidenceScoringSystem()

# Fonction d'interface pour compatibilité
async def calculate_confidence_score(
    user_query: str,
    ai_response: str,
    intent_result: IntentResult,
    supabase_results: List[Dict] = None,
    meili_results: List[Dict] = None,
    supabase_context: str = "",
    meili_context: str = "",
    validation_result: Dict[str, Any] = None
) -> ConfidenceScore:
    """Interface simplifiée pour le calcul de score de confiance"""
    return await confidence_scoring.calculate_confidence_score(
        user_query, ai_response, intent_result,
        supabase_results, meili_results, supabase_context, meili_context, validation_result
    )

if __name__ == "__main__":
    # Test du système de scoring
    async def test_scoring():
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
        
        result = await calculate_confidence_score(
            "Comment tu t'appelles ?",
            "Je m'appelle Gamma, votre assistant client.",
            social_intent
        )
        
        print(f"Score de confiance: {result.overall_confidence:.3f}")
        print(f"Niveau: {result.confidence_level.value}")
        print(f"Recommandations: {result.recommendations}")
    
    asyncio.run(test_scoring())
