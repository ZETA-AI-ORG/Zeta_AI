#!/usr/bin/env python3
"""
🛡️ GARDE-FOU ANTI-HALLUCINATION SIMPLE ET ADAPTATIF
Système simple qui s'adapte à n'importe quelle question et entreprise
"""

import re
import logging
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class QuestionType(Enum):
    """Types de questions simples"""
    REQUIRES_DOCUMENTS = "requires_documents"  # Besoin de documents
    SOCIAL_CONVERSATION = "social_conversation"  # Conversation sociale
    GENERAL_QUESTION = "general_question"  # Question générale

@dataclass
class HallucinationCheck:
    """Résultat de vérification anti-hallucination"""
    is_safe: bool
    confidence: float
    question_type: QuestionType
    requires_documents: bool
    documents_found: bool
    rejection_reason: str = None
    suggested_action: str = None

class SimpleAdaptiveHallucinationGuard:
    """
    🛡️ GARDE-FOU ANTI-HALLUCINATION SIMPLE ET ADAPTATIF
    
    Principe :
    1. Détection simple et robuste des types de questions
    2. Validation adaptative selon le contexte
    3. Pas de blocage inutile
    4. Fonctionne pour n'importe quelle entreprise
    """
    
    def __init__(self):
        # Patterns simples et universels
        self.document_required_patterns = [
            # Questions sur les produits/services
            r'(?i)(que\s+vendez|what\s+do\s+you\s+sell)',
            r'(?i)(quels?\s+produits?|what\s+products?)',
            r'(?i)(que\s+proposez|what\s+do\s+you\s+offer)',
            r'(?i)(catalogue|catalog)',
            r'(?i)(gamme|range)',
            r'(?i)(services?|services?)',
            
            # Questions sur les prix
            r'(?i)(prix|price|coût|cost)',
            r'(?i)(combien|how\s+much)',
            r'(?i)(tarif|rate)',
            
            # Questions sur la livraison
            r'(?i)(livraison|delivery)',
            r'(?i)(expédition|shipping)',
            r'(?i)(délai|delay)',
            
            # Questions sur l'entreprise
            r'(?i)(qui\s+êtes-vous|who\s+are\s+you)',
            r'(?i)(entreprise|company)',
            r'(?i)(adresse|address)',
            r'(?i)(téléphone|phone)',
            
            # Questions techniques
            r'(?i)(comment\s+ça\s+marche|how\s+does\s+it\s+work)',
            r'(?i)(spécifications?|specifications?)',
            r'(?i)(caractéristiques?|features?)',
        ]
        
        self.social_patterns = [
            r'(?i)(bonjour|hello|salut|hi)',
            r'(?i)(comment\s+allez-vous|how\s+are\s+you)',
            r'(?i)(merci|thank\s+you|thanks)',
            r'(?i)(au\s+revoir|goodbye|bye)',
            r'(?i)(ça\s+va|are\s+you\s+ok)',
        ]
        
        self.general_patterns = [
            r'(?i)(quoi|what)',
            r'(?i)(comment|how)',
            r'(?i)(pourquoi|why)',
            r'(?i)(quand|when)',
            r'(?i)(où|where)',
        ]
    
    def classify_question_type(self, query: str) -> Tuple[QuestionType, float]:
        """
        Classifie le type de question de manière simple et robuste
        """
        query_lower = query.lower().strip()
        
        # Vérifier les patterns de documents requis
        for pattern in self.document_required_patterns:
            if re.search(pattern, query_lower):
                return QuestionType.REQUIRES_DOCUMENTS, 0.9
        
        # Vérifier les patterns sociaux
        for pattern in self.social_patterns:
            if re.search(pattern, query_lower):
                return QuestionType.SOCIAL_CONVERSATION, 0.8
        
        # Vérifier les patterns généraux
        for pattern in self.general_patterns:
            if re.search(pattern, query_lower):
                return QuestionType.GENERAL_QUESTION, 0.6
        
        # Par défaut, considérer comme question générale
        return QuestionType.GENERAL_QUESTION, 0.5
    
    def check_hallucination_risk(self, query: str, ai_response: str, documents_found: bool = False) -> HallucinationCheck:
        """
        Vérifie le risque d'hallucination de manière simple et adaptative
        """
        try:
            # 1. Classification du type de question
            question_type, confidence = self.classify_question_type(query)
            
            # 2. Vérifications adaptatives
            if question_type == QuestionType.SOCIAL_CONVERSATION:
                # Questions sociales : toujours sûres
                return HallucinationCheck(
                    is_safe=True,
                    confidence=0.9,
                    question_type=question_type,
                    requires_documents=False,
                    documents_found=documents_found,
                    suggested_action="Réponse sociale autorisée"
                )
            
            elif question_type == QuestionType.REQUIRES_DOCUMENTS:
                # Questions nécessitant des documents
                if documents_found:
                    # Documents trouvés : vérifier la cohérence
                    if self._is_response_coherent_with_documents(ai_response, documents_found):
                        return HallucinationCheck(
                            is_safe=True,
                            confidence=0.8,
                            question_type=question_type,
                            requires_documents=True,
                            documents_found=True,
                            suggested_action="Réponse basée sur documents"
                        )
                    else:
                        return HallucinationCheck(
                            is_safe=False,
                            confidence=0.3,
                            question_type=question_type,
                            requires_documents=True,
                            documents_found=True,
                            rejection_reason="Réponse incohérente avec les documents",
                            suggested_action="Reformuler la réponse"
                        )
                else:
                    # Pas de documents : vérifier si la réponse est appropriée
                    if self._is_response_appropriate_without_documents(ai_response):
                        return HallucinationCheck(
                            is_safe=True,
                            confidence=0.6,
                            question_type=question_type,
                            requires_documents=True,
                            documents_found=False,
                            suggested_action="Réponse appropriée sans documents"
                        )
                    else:
                        return HallucinationCheck(
                            is_safe=False,
                            confidence=0.2,
                            question_type=question_type,
                            requires_documents=True,
                            documents_found=False,
                            rejection_reason="Réponse inappropriée sans documents",
                            suggested_action="Rechercher des documents ou dire qu'on n'a pas l'info"
                        )
            
            else:
                # Questions générales : validation basique
                if self._is_response_reasonable(ai_response):
                    return HallucinationCheck(
                        is_safe=True,
                        confidence=0.7,
                        question_type=question_type,
                        requires_documents=False,
                        documents_found=documents_found,
                        suggested_action="Réponse générale autorisée"
                    )
                else:
                    return HallucinationCheck(
                        is_safe=False,
                        confidence=0.3,
                        question_type=question_type,
                        requires_documents=False,
                        documents_found=documents_found,
                        rejection_reason="Réponse déraisonnable",
                        suggested_action="Améliorer la réponse"
                    )
        
        except Exception as e:
            logger.error(f"❌ Erreur vérification hallucination: {e}")
            # En cas d'erreur, être permissif
            return HallucinationCheck(
                is_safe=True,
                confidence=0.5,
                question_type=QuestionType.GENERAL_QUESTION,
                requires_documents=False,
                documents_found=documents_found,
                suggested_action="Validation par défaut"
            )
    
    def _is_response_coherent_with_documents(self, response: str, documents_found: bool) -> bool:
        """Vérifie si la réponse est cohérente avec les documents"""
        if not documents_found:
            return False
        
        # Vérifications basiques
        response_lower = response.lower()
        
        # Ne doit pas dire qu'il n'a pas d'informations
        negative_phrases = [
            "je n'ai pas d'informations",
            "aucun contexte",
            "pas d'informations disponibles",
            "je ne sais pas"
        ]
        
        for phrase in negative_phrases:
            if phrase in response_lower:
                return False
        
        return True
    
    def _is_response_appropriate_without_documents(self, response: str) -> bool:
        """Vérifie si la réponse est appropriée sans documents"""
        response_lower = response.lower()
        
        # Phrases appropriées sans documents
        appropriate_phrases = [
            "je n'ai pas d'informations",
            "aucun contexte disponible",
            "je ne peux pas répondre",
            "contactez notre service",
            "je n'ai pas accès"
        ]
        
        for phrase in appropriate_phrases:
            if phrase in response_lower:
                return True
        
        return False
    
    def _is_response_reasonable(self, response: str) -> bool:
        """Vérifie si la réponse est raisonnable"""
        if not response or len(response.strip()) < 10:
            return False
        
        # Vérifications basiques
        response_lower = response.lower()
        
        # Ne doit pas contenir de contenu inapproprié
        inappropriate_phrases = [
            "je ne peux pas vous aider",
            "c'est impossible",
            "je refuse",
            "je ne veux pas"
        ]
        
        for phrase in inappropriate_phrases:
            if phrase in response_lower:
                return False
        
        return True

# Instance globale
simple_hallucination_guard = SimpleAdaptiveHallucinationGuard()

# Fonction d'interface simple
def check_hallucination_simple(query: str, ai_response: str, documents_found: bool = False) -> Dict[str, Any]:
    """
    🛡️ INTERFACE SIMPLE POUR VÉRIFICATION ANTI-HALLUCINATION
    
    Usage:
    result = check_hallucination_simple("Que vendez-vous?", "Nous vendons...", True)
    if result['is_safe']:
        print("Réponse sûre")
    else:
        print(f"Rejeté: {result['rejection_reason']}")
    """
    
    check = simple_hallucination_guard.check_hallucination_risk(query, ai_response, documents_found)
    
    return {
        'is_safe': check.is_safe,
        'confidence': check.confidence,
        'question_type': check.question_type.value,
        'requires_documents': check.requires_documents,
        'documents_found': check.documents_found,
        'rejection_reason': check.rejection_reason,
        'suggested_action': check.suggested_action
    }

if __name__ == "__main__":
    # Test simple
    test_cases = [
        ("Que vendez-vous?", "Nous vendons des produits de qualité", True),
        ("Que vendez-vous?", "Je n'ai pas d'informations", False),
        ("Bonjour", "Bonjour ! Comment puis-je vous aider ?", False),
        ("Comment allez-vous?", "Très bien, merci !", False),
    ]
    
    for query, response, docs_found in test_cases:
        result = check_hallucination_simple(query, response, docs_found)
        print(f"Q: {query}")
        print(f"R: {response}")
        print(f"Sûr: {result['is_safe']} (conf: {result['confidence']:.2f})")
        print(f"Type: {result['question_type']}")
        if not result['is_safe']:
            print(f"Raison: {result['rejection_reason']}")
        print("-" * 50)
