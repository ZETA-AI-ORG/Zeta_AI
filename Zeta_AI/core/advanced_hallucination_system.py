#!/usr/bin/env python3
"""
🛡️ SYSTÈME ANTI-HALLUCINATION AVANCÉ 2024
Architecture renforcée avec validation granulaire multi-niveaux
"""

import re
import logging
import time
import json
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class InformationType(Enum):
    """Types d'informations pour validation différenciée"""
    HARD_FACTS = "hard_facts"          # Prix, dates, specs → Validation stricte 100%
    SOFT_FACTS = "soft_facts"          # Délais "généralement", processus → Validation souple
    POLICIES = "policies"              # Conditions générales → Supabase priorité absolue
    DYNAMIC_DATA = "dynamic_data"      # Stock, disponibilité → Validation temps réel

class ValidationLevel(Enum):
    """Niveaux de validation"""
    CRITICAL = "critical"              # Infos critiques (prix, légal) : Score > 0.95
    GENERAL = "general"                # Infos générales : Score > 0.85
    DESCRIPTIVE = "descriptive"        # Infos descriptives : Score > 0.75

class FallbackType(Enum):
    """Types de fallback"""
    TRIANGLE_COMPLETE = "triangle_complete"
    SIMPLIFIED_RAG = "simplified_rag"
    TEMPLATE_SECURE = "template_secure"

@dataclass
class ValidationResult:
    """Résultat de validation granulaire"""
    is_valid: bool
    confidence_score: float
    validation_level: ValidationLevel
    information_type: InformationType
    phrase_validations: List[Dict[str, Any]]
    global_coherence: float
    source_accuracy: float
    completeness: float
    rejection_reasons: List[str]
    fallback_suggestions: List[str]

@dataclass
class ValidationCache:
    """Cache de validation contextuel"""
    session_id: str
    validated_info: Dict[str, Any]
    timestamp: datetime
    source_version: str

class AdvancedHallucinationGuard:
    """
    🛡️ GARDE-FOU ANTI-HALLUCINATION AVANCÉ
    
    Fonctionnalités :
    1. Validation granulaire multi-niveaux
    2. Classification intelligente des informations
    3. Système de fallback intelligent
    4. Cache de validation contextuel
    5. Scoring avancé du triangle
    6. Mode dégradé gracieux
    """
    
    def __init__(self):
        self.validation_cache = {}
        self.performance_metrics = {
            'total_validations': 0,
            'average_validation_time': 0.0,
            'cache_hits': 0,
            'fallback_activations': 0
        }
        
        # Patterns pour classification des informations
        self.information_patterns = {
            InformationType.HARD_FACTS: [
                r'\d+[€$£¥]',                    # Prix
                r'\d{1,2}[/-]\d{1,2}[/-]\d{4}', # Dates
                r'\d+\s*(kg|g|ml|l|cm|m)',      # Spécifications
                r'\d+\s*(euros?|dollars?)',     # Prix en mots
            ],
            InformationType.SOFT_FACTS: [
                r'(généralement|habituellement|souvent|parfois)',
                r'(environ|approximativement|vers)',
                r'(dans la plupart des cas|la plupart du temps)',
            ],
            InformationType.POLICIES: [
                r'(conditions générales|CGV|politique)',
                r'(garantie|retour|remboursement)',
                r'(livraison gratuite|frais de port)',
            ],
            InformationType.DYNAMIC_DATA: [
                r'(disponible|en stock|rupture)',
                r'(actuellement|maintenant|aujourd\'hui)',
                r'(cette semaine|cette période)',
            ]
        }
        
        # Seuils de validation adaptatifs
        self.validation_thresholds = {
            ValidationLevel.CRITICAL: 0.95,
            ValidationLevel.GENERAL: 0.85,
            ValidationLevel.DESCRIPTIVE: 0.75
        }
    
    def classify_information_type(self, text: str) -> Tuple[InformationType, float]:
        """Classifie le type d'information avec score de confiance"""
        max_score = 0.0
        best_type = InformationType.DESCRIPTIVE
        
        for info_type, patterns in self.information_patterns.items():
            score = 0.0
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                score += matches * 0.2
            
            if score > max_score:
                max_score = score
                best_type = info_type
        
        return best_type, min(max_score, 1.0)
    
    def determine_validation_level(self, information_type: InformationType, 
                                 query_context: str) -> ValidationLevel:
        """Détermine le niveau de validation requis"""
        if information_type == InformationType.HARD_FACTS:
            return ValidationLevel.CRITICAL
        elif information_type == InformationType.POLICIES:
            return ValidationLevel.CRITICAL
        elif information_type == InformationType.DYNAMIC_DATA:
            return ValidationLevel.GENERAL
        else:
            return ValidationLevel.DESCRIPTIVE
    
    def validate_phrase_by_phrase(self, response: str, sources: List[str]) -> List[Dict[str, Any]]:
        """Validation phrase par phrase"""
        phrases = self._split_into_phrases(response)
        phrase_validations = []
        
        for phrase in phrases:
            validation = {
                'phrase': phrase,
                'is_factual': self._contains_factual_information(phrase),
                'source_matches': [],
                'confidence': 0.0,
                'is_valid': False
            }
            
            if validation['is_factual']:
                validation['source_matches'] = self._find_source_matches(phrase, sources)
                validation['confidence'] = self._calculate_phrase_confidence(phrase, sources)
                validation['is_valid'] = validation['confidence'] > 0.7
            
            phrase_validations.append(validation)
        
        return phrase_validations
    
    def calculate_advanced_score(self, phrase_validations: List[Dict[str, Any]], 
                               sources: List[str]) -> Dict[str, float]:
        """Calcul du score avancé du triangle"""
        if not phrase_validations:
            return {'coherence': 0.0, 'accuracy': 0.0, 'completeness': 0.0, 'overall': 0.0}
        
        # Cohérence Question-Réponse × 0.3
        coherence = sum(pv['confidence'] for pv in phrase_validations) / len(phrase_validations)
        
        # Exactitude Source-Réponse × 0.5
        accuracy = sum(1.0 for pv in phrase_validations if pv['is_valid']) / len(phrase_validations)
        
        # Complétude Information × 0.2
        completeness = min(1.0, len(sources) / 3.0)  # Normalisé sur 3 sources
        
        # Score composite
        overall = (coherence * 0.3) + (accuracy * 0.5) + (completeness * 0.2)
        
        return {
            'coherence': coherence,
            'accuracy': accuracy,
            'completeness': completeness,
            'overall': overall
        }
    
    def check_cache(self, session_id: str, query_hash: str) -> Optional[ValidationResult]:
        """Vérifie le cache de validation contextuel"""
        cache_key = f"{session_id}_{query_hash}"
        
        if cache_key in self.validation_cache:
            cache_entry = self.validation_cache[cache_key]
            # Vérifier si le cache est encore valide (1 heure)
            if datetime.now() - cache_entry.timestamp < timedelta(hours=1):
                self.performance_metrics['cache_hits'] += 1
                return cache_entry.validated_info
        
        return None
    
    def update_cache(self, session_id: str, query_hash: str, result: ValidationResult):
        """Met à jour le cache de validation"""
        cache_key = f"{session_id}_{query_hash}"
        self.validation_cache[cache_key] = ValidationCache(
            session_id=session_id,
            validated_info=result,
            timestamp=datetime.now(),
            source_version="1.0"
        )
    
    def generate_intelligent_fallback(self, validation_result: ValidationResult, 
                                   query: str) -> Dict[str, Any]:
        """Génère un fallback intelligent selon le type d'échec"""
        fallback_type = self._determine_fallback_type(validation_result)
        
        if fallback_type == FallbackType.TRIANGLE_COMPLETE:
            return {
                'type': 'triangle_complete',
                'message': 'Je vais rechercher des informations plus précises pour vous.',
                'action': 'retry_with_enhanced_search'
            }
        elif fallback_type == FallbackType.SIMPLIFIED_RAG:
            return {
                'type': 'simplified_rag',
                'message': 'Je peux vous donner une réponse générale sur ce sujet.',
                'action': 'provide_general_info'
            }
        else:  # TEMPLATE_SECURE
            return {
                'type': 'template_secure',
                'message': 'Je n\'ai pas d\'informations suffisamment fiables pour répondre à votre question. Pouvez-vous contacter notre service client ?',
                'action': 'suggest_contact',
                'contact_info': 'Service client disponible du lundi au vendredi 9h-18h'
            }
    
    def activate_degraded_mode(self) -> Dict[str, Any]:
        """Active le mode dégradé gracieux"""
        return {
            'mode': 'degraded',
            'message': 'Système en mode de validation simplifiée. Informations sous réserve de vérification.',
            'validation_level': 'simplified',
            'disclaimer': 'Les informations fournies sont sous réserve de vérification.'
        }
    
    def validate_advanced(self, query: str, response: str, sources: List[str] = None,
                        session_id: str = None) -> ValidationResult:
        """
        Validation avancée avec toutes les fonctionnalités
        """
        start_time = time.time()
        
        try:
            # 1. Vérifier le cache
            query_hash = hash(query + response)
            if session_id:
                cached_result = self.check_cache(session_id, str(query_hash))
                if cached_result:
                    return cached_result
            
            # 2. Classification des informations
            info_type, type_confidence = self.classify_information_type(response)
            validation_level = self.determine_validation_level(info_type, query)
            
            # 3. Validation granulaire phrase par phrase
            phrase_validations = self.validate_phrase_by_phrase(response, sources or [])
            
            # 4. Calcul du score avancé
            scores = self.calculate_advanced_score(phrase_validations, sources or [])
            
            # 5. Détermination de la validité
            threshold = self.validation_thresholds[validation_level]
            is_valid = scores['overall'] >= threshold
            
            # 6. Génération des raisons de rejet
            rejection_reasons = []
            if not is_valid:
                if scores['coherence'] < 0.7:
                    rejection_reasons.append("Cohérence insuffisante entre question et réponse")
                if scores['accuracy'] < 0.8:
                    rejection_reasons.append("Exactitude des sources insuffisante")
                if scores['completeness'] < 0.6:
                    rejection_reasons.append("Complétude de l'information insuffisante")
            
            # 7. Génération des suggestions de fallback
            fallback_suggestions = []
            if not is_valid:
                fallback_suggestions.append("Reformuler la question de manière plus spécifique")
                fallback_suggestions.append("Vérifier les sources de données")
                fallback_suggestions.append("Contacter le service client pour assistance")
            
            # 8. Création du résultat
            result = ValidationResult(
                is_valid=is_valid,
                confidence_score=scores['overall'],
                validation_level=validation_level,
                information_type=info_type,
                phrase_validations=phrase_validations,
                global_coherence=scores['coherence'],
                source_accuracy=scores['accuracy'],
                completeness=scores['completeness'],
                rejection_reasons=rejection_reasons,
                fallback_suggestions=fallback_suggestions
            )
            
            # 9. Mise à jour du cache
            if session_id:
                self.update_cache(session_id, str(query_hash), result)
            
            # 10. Mise à jour des métriques
            validation_time = time.time() - start_time
            self.performance_metrics['total_validations'] += 1
            self.performance_metrics['average_validation_time'] = (
                (self.performance_metrics['average_validation_time'] * 
                 (self.performance_metrics['total_validations'] - 1) + validation_time) /
                self.performance_metrics['total_validations']
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur validation avancée: {e}")
            # Mode dégradé en cas d'erreur
            return ValidationResult(
                is_valid=False,
                confidence_score=0.0,
                validation_level=ValidationLevel.CRITICAL,
                information_type=InformationType.HARD_FACTS,
                phrase_validations=[],
                global_coherence=0.0,
                source_accuracy=0.0,
                completeness=0.0,
                rejection_reasons=[f"Erreur système: {str(e)}"],
                fallback_suggestions=["Activation du mode dégradé"]
            )
    
    def _split_into_phrases(self, text: str) -> List[str]:
        """Divise le texte en phrases"""
        # Séparation par points, points d'exclamation, points d'interrogation
        phrases = re.split(r'[.!?]+', text)
        return [phrase.strip() for phrase in phrases if phrase.strip()]
    
    def _contains_factual_information(self, phrase: str) -> bool:
        """Détermine si une phrase contient des informations factuelles"""
        factual_indicators = [
            r'\d+',  # Chiffres
            r'(prix|coût|tarif)',  # Mots liés aux prix
            r'(adresse|téléphone|email)',  # Informations de contact
            r'(disponible|en stock|rupture)',  # Disponibilité
        ]
        
        for pattern in factual_indicators:
            if re.search(pattern, phrase, re.IGNORECASE):
                return True
        return False
    
    def _find_source_matches(self, phrase: str, sources: List[str]) -> List[str]:
        """Trouve les correspondances dans les sources"""
        matches = []
        phrase_lower = phrase.lower()
        
        for source in sources:
            source_lower = source.lower()
            # Recherche de correspondances partielles
            if any(word in source_lower for word in phrase_lower.split() if len(word) > 3):
                matches.append(source)
        
        return matches
    
    def _calculate_phrase_confidence(self, phrase: str, sources: List[str]) -> float:
        """Calcule la confiance d'une phrase"""
        if not sources:
            return 0.0
        
        matches = self._find_source_matches(phrase, sources)
        return len(matches) / len(sources) if sources else 0.0
    
    def _determine_fallback_type(self, validation_result: ValidationResult) -> FallbackType:
        """Détermine le type de fallback approprié"""
        if validation_result.confidence_score > 0.5:
            return FallbackType.TRIANGLE_COMPLETE
        elif validation_result.confidence_score > 0.3:
            return FallbackType.SIMPLIFIED_RAG
        else:
            return FallbackType.TEMPLATE_SECURE
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Retourne les métriques de performance"""
        return self.performance_metrics.copy()

# Instance globale
advanced_hallucination_guard = AdvancedHallucinationGuard()

# Fonction d'interface
def validate_advanced_hallucination(query: str, response: str, sources: List[str] = None,
                                  session_id: str = None) -> Dict[str, Any]:
    """
    🛡️ INTERFACE POUR VALIDATION ANTI-HALLUCINATION AVANCÉE
    
    Usage:
    result = validate_advanced_hallucination("Quel est le prix ?", "Le prix est de 25€", ["Prix: 25€"])
    if result['is_valid']:
        print("Réponse validée")
    else:
        print(f"Rejeté: {result['rejection_reasons']}")
    """
    
    validation_result = advanced_hallucination_guard.validate_advanced(
        query, response, sources, session_id
    )
    
    return {
        'is_valid': validation_result.is_valid,
        'confidence_score': validation_result.confidence_score,
        'validation_level': validation_result.validation_level.value,
        'information_type': validation_result.information_type.value,
        'phrase_validations': validation_result.phrase_validations,
        'global_coherence': validation_result.global_coherence,
        'source_accuracy': validation_result.source_accuracy,
        'completeness': validation_result.completeness,
        'rejection_reasons': validation_result.rejection_reasons,
        'fallback_suggestions': validation_result.fallback_suggestions
    }

if __name__ == "__main__":
    # Test du système avancé
    test_cases = [
        ("Quel est le prix ?", "Le prix est de 25€", ["Prix: 25€"]),
        ("Où êtes-vous ?", "Nous sommes au 123 rue de la Paix", ["Adresse: 123 rue de la Paix"]),
        ("Quel est le prix ?", "Le prix est de 50€", ["Prix: 25€"]),  # Incohérent
    ]
    
    for query, response, sources in test_cases:
        result = validate_advanced_hallucination(query, response, sources)
        print(f"Q: {query}")
        print(f"R: {response}")
        print(f"Valide: {result['is_valid']} (conf: {result['confidence_score']:.3f})")
        print(f"Niveau: {result['validation_level']}")
        print(f"Type: {result['information_type']}")
        if not result['is_valid']:
            print(f"Raisons: {result['rejection_reasons']}")
        print("-" * 50)
