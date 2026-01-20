#!/usr/bin/env python3
"""
🛡️ GARDE-FOU ANTI-HALLUCINATION ADAPTATIF
Système en 2 modes : conversations simples + informations factuelles
"""

import re
import logging
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ValidationMode(Enum):
    """Modes de validation"""
    SIMPLE_CONVERSATION = "simple_conversation"  # Mode 1
    FACTUAL_INFORMATION = "factual_information"   # Mode 2

class ValidationResult(Enum):
    """Résultats de validation"""
    VALID = "valid"                    # ✅ Réponse valide
    INVALID = "invalid"                # ❌ Réponse invalide
    NEEDS_FACTUAL_CHECK = "needs_factual_check"  # 🔍 Nécessite vérification factuelle

@dataclass
class HallucinationCheck:
    """Résultat de vérification anti-hallucination"""
    is_safe: bool
    validation_mode: ValidationMode
    validation_result: ValidationResult
    confidence: float
    rejection_reason: str = None
    specific_information_detected: List[str] = None
    source_verification: Dict[str, bool] = None
    suggested_action: str = None

class AdaptiveHallucinationGuard:
    """
    🛡️ GARDE-FOU ANTI-HALLUCINATION ADAPTATIF
    
    Mode 1 : Conversations simples 💬
    - Questions sociales, générales
    - Vérification basique : pas d'informations spécifiques inappropriées
    
    Mode 2 : Informations factuelles 📊
    - Questions nécessitant des données d'entreprise
    - Validation en triangle : question + réponse + documents sources
    - Vérification stricte de la cohérence des informations
    """
    
    def __init__(self):
        # Patterns pour détecter les informations spécifiques
        self.specific_info_patterns = [
            # Chiffres et prix
            r'\d+[€$£¥]',                        # Prix : "10€", "25$"
            r'\d+[.,]\d+[€$£¥]',                # Prix décimaux : "10.50€"
            r'\d+\s*(euros?|dollars?|€)',       # Prix en mots : "10 euros"
            
            # Adresses et lieux
            r'\b\d+\s+[A-Za-z\s]+(rue|avenue|boulevard|street|avenue)\b',  # Adresses
            r'\b\d{5}\b',                       # Codes postaux
            r'\b[A-Za-z\s]+,\s*\d{5}\b',        # Ville + code postal
            
            # Téléphones
            r'\b\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}\b',  # Téléphones FR
            r'\b\+33[\s.-]?\d[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}\b',  # Téléphones internationaux
            
            # Emails
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Emails
            
            # Noms de produits spécifiques
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',   # Noms propres composés
            r'\b[A-Z]{2,}\b',                   # Acronymes
            
            # Dates spécifiques
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b',  # Dates
            r'\b(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4}\b',  # Mois + année
        ]
        
        # Patterns pour questions factuelles
        self.factual_question_patterns = [
            r'(?i)(où\s+êtes-vous|where\s+are\s+you)',
            r'(?i)(adresse|address)',
            r'(?i)(téléphone|phone)',
            r'(?i)(email|e-mail)',
            r'(?i)(prix|price|coût|cost)',
            r'(?i)(horaires|hours|ouverture)',
            r'(?i)(livraison|delivery)',
            r'(?i)(produits?|products?)',
            r'(?i)(services?|services?)',
            r'(?i)(qui\s+êtes-vous|who\s+are\s+you)',
            r'(?i)(que\s+vendez|what\s+do\s+you\s+sell)',
            r'(?i)(combien|how\s+much)',
        ]
        
        # Patterns pour conversations simples
        self.simple_conversation_patterns = [
            r'(?i)(bonjour|hello|salut|hi)',
            r'(?i)(comment\s+allez-vous|how\s+are\s+you)',
            r'(?i)(merci|thank\s+you|thanks)',
            r'(?i)(au\s+revoir|goodbye|bye)',
            r'(?i)(ça\s+va|are\s+you\s+ok)',
            r'(?i)(comment\s+tu\s+t\'appelles|what\s+is\s+your\s+name)',
            r'(?i)(qui\s+es-tu|who\s+are\s+you)',
        ]
    
    def detect_validation_mode(self, query: str, ai_response: str) -> Tuple[ValidationMode, float]:
        """
        Détermine le mode de validation approprié
        """
        query_lower = query.lower().strip()
        response_lower = ai_response.lower().strip()
        
        # 1. Vérifier si la réponse contient des informations spécifiques
        specific_info_count = 0
        for pattern in self.specific_info_patterns:
            matches = re.findall(pattern, ai_response)
            specific_info_count += len(matches)
        
        if specific_info_count > 0:
            return ValidationMode.FACTUAL_INFORMATION, 0.9
        
        # 2. Vérifier si c'est une question factuelle
        for pattern in self.factual_question_patterns:
            if re.search(pattern, query_lower):
                return ValidationMode.FACTUAL_INFORMATION, 0.8
        
        # 3. Vérifier si c'est une conversation simple
        for pattern in self.simple_conversation_patterns:
            if re.search(pattern, query_lower):
                return ValidationMode.SIMPLE_CONVERSATION, 0.8
        
        # 4. Par défaut : conversation simple
        return ValidationMode.SIMPLE_CONVERSATION, 0.6
    
    def validate_simple_conversation(self, query: str, ai_response: str) -> HallucinationCheck:
        """
        Mode 1 : Validation des conversations simples
        Vérifie qu'il n'y a pas d'informations spécifiques inappropriées
        """
        try:
            # Détecter les informations spécifiques dans la réponse
            specific_info = self._extract_specific_information(ai_response)
            
            if not specific_info:
                # Pas d'informations spécifiques : réponse simple et générale
                return HallucinationCheck(
                    is_safe=True,
                    validation_mode=ValidationMode.SIMPLE_CONVERSATION,
                    validation_result=ValidationResult.VALID,
                    confidence=0.9,
                    suggested_action="Réponse simple validée"
                )
            else:
                # Informations spécifiques détectées : rejeter
                return HallucinationCheck(
                    is_safe=False,
                    validation_mode=ValidationMode.SIMPLE_CONVERSATION,
                    validation_result=ValidationResult.INVALID,
                    confidence=0.2,
                    specific_information_detected=specific_info,
                    rejection_reason="Informations spécifiques inappropriées dans une conversation simple",
                    suggested_action="Reformuler sans informations spécifiques"
                )
        
        except Exception as e:
            logger.error(f"❌ Erreur validation conversation simple: {e}")
            return HallucinationCheck(
                is_safe=True,
                validation_mode=ValidationMode.SIMPLE_CONVERSATION,
                validation_result=ValidationResult.VALID,
                confidence=0.5,
                suggested_action="Validation par défaut"
            )
    
    def validate_factual_information(self, query: str, ai_response: str, source_documents: List[str] = None) -> HallucinationCheck:
        """
        Mode 2 : Validation des informations factuelles
        Validation en triangle : question + réponse + documents sources
        """
        try:
            # 1. Extraire les informations spécifiques de la réponse
            specific_info = self._extract_specific_information(ai_response)
            
            if not specific_info:
                # Pas d'informations spécifiques : validation basique
                return HallucinationCheck(
                    is_safe=True,
                    validation_mode=ValidationMode.FACTUAL_INFORMATION,
                    validation_result=ValidationResult.VALID,
                    confidence=0.7,
                    suggested_action="Réponse générale validée"
                )
            
            # 2. Vérifier la cohérence avec les documents sources
            if not source_documents:
                return HallucinationCheck(
                    is_safe=False,
                    validation_mode=ValidationMode.FACTUAL_INFORMATION,
                    validation_result=ValidationResult.INVALID,
                    confidence=0.1,
                    specific_information_detected=specific_info,
                    rejection_reason="Informations spécifiques sans documents sources",
                    suggested_action="Rechercher des documents sources ou reformuler"
                )
            
            # 3. Validation en triangle
            source_verification = {}
            all_verified = True
            
            for info in specific_info:
                is_verified = self._verify_information_in_sources(info, source_documents)
                source_verification[info] = is_verified
                if not is_verified:
                    all_verified = False
            
            if all_verified:
                return HallucinationCheck(
                    is_safe=True,
                    validation_mode=ValidationMode.FACTUAL_INFORMATION,
                    validation_result=ValidationResult.VALID,
                    confidence=0.9,
                    specific_information_detected=specific_info,
                    source_verification=source_verification,
                    suggested_action="Informations factuelles vérifiées"
                )
            else:
                unverified_info = [info for info, verified in source_verification.items() if not verified]
                return HallucinationCheck(
                    is_safe=False,
                    validation_mode=ValidationMode.FACTUAL_INFORMATION,
                    validation_result=ValidationResult.INVALID,
                    confidence=0.2,
                    specific_information_detected=specific_info,
                    source_verification=source_verification,
                    rejection_reason=f"Informations non vérifiées dans les sources: {', '.join(unverified_info)}",
                    suggested_action="Vérifier les sources ou reformuler la réponse"
                )
        
        except Exception as e:
            logger.error(f"❌ Erreur validation factuelle: {e}")
            return HallucinationCheck(
                is_safe=False,
                validation_mode=ValidationMode.FACTUAL_INFORMATION,
                validation_result=ValidationResult.INVALID,
                confidence=0.1,
                rejection_reason=f"Erreur de validation: {str(e)}",
                suggested_action="Vérification manuelle requise"
            )
    
    def _extract_specific_information(self, text: str) -> List[str]:
        """Extrait les informations spécifiques d'un texte"""
        specific_info = []
        
        for pattern in self.specific_info_patterns:
            matches = re.findall(pattern, text)
            specific_info.extend(matches)
        
        return list(set(specific_info))  # Supprimer les doublons
    
    def _verify_information_in_sources(self, information: str, sources: List[str]) -> bool:
        """Vérifie si une information est présente dans les sources"""
        if not sources:
            return False
        
        info_lower = information.lower()
        
        for source in sources:
            source_lower = source.lower()
            
            # Vérification exacte
            if info_lower in source_lower:
                return True
            
            # Vérification stricte pour les prix
            if re.search(r'\d+[€$£¥]', information):
                price_pattern = r'\d+[€$£¥]'
                response_price = re.search(price_pattern, information).group()
                source_prices = re.findall(price_pattern, source)
                
                # Vérification exacte des prix
                for price in source_prices:
                    if price.lower() == response_price.lower():
                        return True
                return False  # Prix non trouvé dans les sources
            
            # Vérification partielle pour les adresses
            if re.search(r'\d+\s+[A-Za-z\s]+(rue|avenue|boulevard)', information):
                address_pattern = r'\d+\s+[A-Za-z\s]+(rue|avenue|boulevard)'
                source_addresses = re.findall(address_pattern, source)
                if any(addr.lower() == info_lower for addr in source_addresses):
                    return True
        
        return False
    
    def check_hallucination(self, query: str, ai_response: str, source_documents: List[str] = None) -> HallucinationCheck:
        """
        Fonction principale de vérification anti-hallucination
        """
        try:
            # 1. Déterminer le mode de validation
            validation_mode, confidence = self.detect_validation_mode(query, ai_response)
            
            # 2. Appliquer la validation appropriée
            if validation_mode == ValidationMode.SIMPLE_CONVERSATION:
                return self.validate_simple_conversation(query, ai_response)
            else:
                return self.validate_factual_information(query, ai_response, source_documents)
        
        except Exception as e:
            logger.error(f"❌ Erreur vérification hallucination: {e}")
            return HallucinationCheck(
                is_safe=True,
                validation_mode=ValidationMode.SIMPLE_CONVERSATION,
                validation_result=ValidationResult.VALID,
                confidence=0.5,
                suggested_action="Validation par défaut"
            )

# Instance globale
adaptive_hallucination_guard = AdaptiveHallucinationGuard()

# Fonction d'interface
def check_hallucination_adaptive(query: str, ai_response: str, source_documents: List[str] = None) -> Dict[str, Any]:
    """
    🛡️ INTERFACE POUR VÉRIFICATION ANTI-HALLUCINATION ADAPTATIVE
    
    Usage:
    result = check_hallucination_adaptive("Bonjour", "Bonjour ! Comment puis-je vous aider ?")
    if result['is_safe']:
        print("Réponse sûre")
    else:
        print(f"Rejeté: {result['rejection_reason']}")
    """
    
    check = adaptive_hallucination_guard.check_hallucination(query, ai_response, source_documents)
    
    return {
        'is_safe': check.is_safe,
        'validation_mode': check.validation_mode.value,
        'validation_result': check.validation_result.value,
        'confidence': check.confidence,
        'rejection_reason': check.rejection_reason,
        'specific_information_detected': check.specific_information_detected,
        'source_verification': check.source_verification,
        'suggested_action': check.suggested_action
    }

if __name__ == "__main__":
    # Test du système
    test_cases = [
        # Mode 1 : Conversations simples
        ("Bonjour", "Bonjour ! Comment puis-je vous aider ?", None),
        ("Comment tu t'appelles ?", "Je m'appelle Gamma", None),
        
        # Mode 2 : Informations factuelles
        ("Où êtes-vous situé ?", "Nous sommes situés au 123 rue de la Paix, 75001 Paris", ["Adresse: 123 rue de la Paix, 75001 Paris"]),
        ("Quel est votre prix ?", "Le prix est de 25€", ["Prix: 25€"]),
        ("Quel est votre prix ?", "Le prix est de 50€", ["Prix: 25€"]),  # Incohérent
    ]
    
    for query, response, sources in test_cases:
        result = check_hallucination_adaptive(query, response, sources)
        print(f"Q: {query}")
        print(f"R: {response}")
        print(f"Mode: {result['validation_mode']}")
        print(f"Sûr: {result['is_safe']} (conf: {result['confidence']:.2f})")
        if result['specific_information_detected']:
            print(f"Infos détectées: {result['specific_information_detected']}")
        if not result['is_safe']:
            print(f"Raison: {result['rejection_reason']}")
        print("-" * 50)
