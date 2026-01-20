#!/usr/bin/env python3
"""
🎯 CLASSIFICATEUR D'INTENTION AVANCÉ 2024
Système de classification d'intention de niveau enterprise basé sur les meilleures pratiques
"""

import re
import json
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class IntentType(Enum):
    """Types d'intention avec niveaux de priorité"""
    # Intentions sociales (pas besoin de documents)
    SOCIAL_GREETING = "social_greeting"
    POLITENESS = "politeness"
    GENERAL_CONVERSATION = "general_conversation"
    OFF_TOPIC = "off_topic"
    
    # Intentions métier (besoin de documents)
    PRODUCT_INQUIRY = "product_inquiry"
    PRICING_INFO = "pricing_info"
    DELIVERY_INFO = "delivery_info"
    SUPPORT_CONTACT = "support_contact"
    COMPANY_INFO = "company_info"
    ORDER_STATUS = "order_status"
    COMPLAINT = "complaint"
    
    # Intentions critiques (validation stricte)
    TECHNICAL_SPECS = "technical_specs"
    MEDICAL_ADVICE = "medical_advice"
    FINANCIAL_ADVICE = "financial_advice"

@dataclass
class IntentResult:
    """Résultat de classification d'intention"""
    primary_intent: IntentType
    confidence: float
    all_intents: Dict[IntentType, float]
    requires_documents: bool
    is_critical: bool
    fallback_required: bool
    context_hints: List[str]
    processing_time_ms: float

class AdvancedIntentClassifier:
    """
    🎯 CLASSIFICATEUR D'INTENTION ENTERPRISE 2024
    
    Fonctionnalités avancées :
    1. Classification multi-classe avec seuils de confiance
    2. Détection contextuelle intelligente
    3. Gestion des ambiguïtés
    4. Fallback automatique
    5. Apprentissage adaptatif
    """
    
    def __init__(self):
        self.start_time = datetime.now()
        
        # Seuils de confiance configurables
        self.confidence_thresholds = {
            'high': 0.8,      # Confiance élevée
            'medium': 0.6,    # Confiance moyenne
            'low': 0.4,       # Confiance faible
            'fallback': 0.3   # Seuil de fallback
        }
        
        # Patterns de classification avancés
        self.intent_patterns = self._build_intent_patterns()
        
        # Mots-clés contextuels
        self.context_keywords = self._build_context_keywords()
        
        # Cache des classifications
        self.classification_cache = {}
        self.cache_ttl = 3600  # 1 heure
        
        logger.info("[INTENT_CLASSIFIER] Système de classification avancé initialisé")
    
    def _build_intent_patterns(self) -> Dict[IntentType, List[Dict]]:
        """Construit les patterns de classification avancés"""
        return {
            # Intentions sociales
            IntentType.SOCIAL_GREETING: [
                {
                    'patterns': [
                        r'(?i)(bonjour|salut|hello|hi|hey)',
                        r'(?i)(comment\s+tu\s+t\'appelles|quel\s+est\s+ton\s+nom)',
                        r'(?i)(qui\s+es-tu|who\s+are\s+you)',
                        r'(?i)(comment\s+ça\s+va|how\s+are\s+you)',
                        r'(?i)(bienvenue|welcome)'
                    ],
                    'weight': 1.0,
                    'context_hints': ['greeting', 'introduction', 'social']
                }
            ],
            
            IntentType.POLITENESS: [
                {
                    'patterns': [
                        r'(?i)(merci|thank\s+you|thanks)',
                        r'(?i)(s\'il\s+vous\s+plaît|please)',
                        r'(?i)(excusez-moi|excuse\s+me)',
                        r'(?i)(pardon|sorry)',
                        r'(?i)(de\s+rien|you\'re\s+welcome)'
                    ],
                    'weight': 0.9,
                    'context_hints': ['politeness', 'courtesy']
                }
            ],
            
            IntentType.GENERAL_CONVERSATION: [
                {
                    'patterns': [
                        r'(?i)(comment\s+allez-vous|how\s+are\s+you)',
                        r'(?i)(ça\s+va|are\s+you\s+ok)',
                        r'(?i)(parlez-vous\s+français|do\s+you\s+speak)',
                        r'(?i)(quelle\s+heure\s+est-il|what\s+time)',
                        r'(?i)(il\s+fait\s+beau|nice\s+weather)'
                    ],
                    'weight': 0.8,
                    'context_hints': ['conversation', 'general']
                }
            ],
            
            # Intentions métier
            IntentType.PRODUCT_INQUIRY: [
                {
                    'patterns': [
                        r'(?i)(quels?\s+produits?|what\s+products?)',
                        r'(?i)(que\s+vendez|what\s+do\s+you\s+sell)',
                        r'(?i)(que\s+proposez|what\s+do\s+you\s+offer)',
                        r'(?i)(catalogue|catalog)',
                        r'(?i)(montrez-moi|show\s+me)',
                        r'(?i)(disponible|available)',
                        r'(?i)(stock|inventory)',
                        r'(?i)(gamme|range)',
                        r'(?i)(articles?|items?)',
                        r'(?i)(services?|services?)'
                    ],
                    'weight': 1.0,
                    'context_hints': ['product', 'catalog', 'inventory', 'sales']
                }
            ],
            
            IntentType.PRICING_INFO: [
                {
                    'patterns': [
                        r'(?i)(prix|price|coût|cost)',
                        r'(?i)(combien|how\s+much)',
                        r'(?i)(tarif|rate)',
                        r'(?i)(promotion|discount)',
                        r'(?i)(offre|offer)'
                    ],
                    'weight': 1.0,
                    'context_hints': ['pricing', 'cost', 'money']
                }
            ],
            
            IntentType.DELIVERY_INFO: [
                {
                    'patterns': [
                        r'(?i)(livraison|delivery)',
                        r'(?i)(expédition|shipping)',
                        r'(?i)(délai|delay|time)',
                        r'(?i)(zone|area)',
                        r'(?i)(frais\s+de\s+port|shipping\s+cost)'
                    ],
                    'weight': 1.0,
                    'context_hints': ['delivery', 'shipping', 'logistics']
                }
            ],
            
            IntentType.SUPPORT_CONTACT: [
                {
                    'patterns': [
                        r'(?i)(contact|support|aide|help)',
                        r'(?i)(service\s+client|customer\s+service)',
                        r'(?i)(téléphone|phone)',
                        r'(?i)(email|mail)',
                        r'(?i)(assistance|assistance)'
                    ],
                    'weight': 0.9,
                    'context_hints': ['support', 'contact', 'help']
                }
            ],
            
            IntentType.COMPANY_INFO: [
                {
                    'patterns': [
                        r'(?i)(qui\s+êtes-vous|who\s+are\s+you)',
                        r'(?i)(entreprise|company)',
                        r'(?i)(histoire|history)',
                        r'(?i)(mission|mission)',
                        r'(?i)(équipe|team)'
                    ],
                    'weight': 0.8,
                    'context_hints': ['company', 'about', 'information']
                }
            ],
            
            # Intentions critiques
            IntentType.TECHNICAL_SPECS: [
                {
                    'patterns': [
                        r'(?i)(spécifications|specifications)',
                        r'(?i)(technique|technical)',
                        r'(?i)(dimensions|size)',
                        r'(?i)(matériau|material)',
                        r'(?i)(certification|certification)'
                    ],
                    'weight': 1.0,
                    'context_hints': ['technical', 'specs', 'detailed']
                }
            ],
            
            IntentType.MEDICAL_ADVICE: [
                {
                    'patterns': [
                        r'(?i)(médical|medical)',
                        r'(?i)(santé|health)',
                        r'(?i)(docteur|doctor)',
                        r'(?i)(traitement|treatment)',
                        r'(?i)(médicament|medicine)'
                    ],
                    'weight': 1.0,
                    'context_hints': ['medical', 'health', 'critical']
                }
            ],
            
            IntentType.OFF_TOPIC: [
                {
                    'patterns': [
                        r'(?i)(politique|politics)',
                        r'(?i)(sport|sports)',
                        r'(?i)(météo|weather)',
                        r'(?i)(actualités|news)',
                        r'(?i)(divertissement|entertainment)'
                    ],
                    'weight': 0.7,
                    'context_hints': ['off-topic', 'unrelated']
                }
            ]
        }
    
    def _build_context_keywords(self) -> Dict[str, List[str]]:
        """Construit les mots-clés contextuels"""
        return {
            'urgent': ['urgent', 'rapide', 'immédiat', 'asap'],
            'question': ['?', 'comment', 'pourquoi', 'quand', 'où'],
            'negation': ['pas', 'non', 'ne', 'jamais', 'aucun'],
            'quantification': ['beaucoup', 'peu', 'tous', 'certains', 'plusieurs'],
            'temporal': ['maintenant', 'hier', 'demain', 'bientôt', 'toujours']
        }
    
    async def classify_intent(self, text: str, context: Dict[str, Any] = None) -> IntentResult:
        """
        🎯 CLASSIFICATION D'INTENTION AVANCÉE
        
        Args:
            text: Texte à classifier
            context: Contexte conversationnel
            
        Returns:
            IntentResult: Résultat de classification
        """
        start_time = datetime.now()
        
        # Normalisation du texte
        normalized_text = self._normalize_text(text)
        
        # Vérification du cache
        cache_key = f"{normalized_text}_{hash(str(context))}"
        if cache_key in self.classification_cache:
            cached_result = self.classification_cache[cache_key]
            if (datetime.now() - cached_result['timestamp']).seconds < self.cache_ttl:
                return cached_result['result']
        
        # Classification multi-classe
        intent_scores = await self._calculate_intent_scores(normalized_text, context)
        
        # Sélection de l'intention principale
        primary_intent, confidence = self._select_primary_intent(intent_scores)
        
        # Détermination des propriétés de l'intention
        requires_documents = self._requires_documents(primary_intent)
        is_critical = self._is_critical_intent(primary_intent)
        fallback_required = confidence < self.confidence_thresholds['fallback']
        
        # Extraction des indices contextuels
        context_hints = self._extract_context_hints(normalized_text, primary_intent)
        
        # Création du résultat
        result = IntentResult(
            primary_intent=primary_intent,
            confidence=confidence,
            all_intents=intent_scores,
            requires_documents=requires_documents,
            is_critical=is_critical,
            fallback_required=fallback_required,
            context_hints=context_hints,
            processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000
        )
        
        # Mise en cache
        self.classification_cache[cache_key] = {
            'result': result,
            'timestamp': datetime.now()
        }
        
        logger.info(f"[INTENT_CLASSIFIER] Classifié: '{text[:50]}...' → {primary_intent.value} (conf: {confidence:.2f})")
        
        return result
    
    def _normalize_text(self, text: str) -> str:
        """Normalise le texte pour la classification"""
        # Suppression des caractères spéciaux
        text = re.sub(r'[^\w\s\?\!\.]', ' ', text)
        
        # Normalisation des espaces
        text = re.sub(r'\s+', ' ', text)
        
        # Conversion en minuscules
        text = text.lower().strip()
        
        return text
    
    async def _calculate_intent_scores(self, text: str, context: Dict[str, Any] = None) -> Dict[IntentType, float]:
        """Calcule les scores pour chaque intention"""
        scores = {}
        
        for intent_type, patterns_list in self.intent_patterns.items():
            max_score = 0.0
            
            for pattern_group in patterns_list:
                pattern_score = 0.0
                matched_patterns = 0
                
                for pattern in pattern_group['patterns']:
                    if re.search(pattern, text):
                        pattern_score += 1.0
                        matched_patterns += 1
                
                if matched_patterns > 0:
                    # Score basé sur le nombre de patterns correspondants
                    pattern_score = (pattern_score / len(pattern_group['patterns'])) * pattern_group['weight']
                    
                    # Bonus pour les correspondances multiples
                    if matched_patterns > 1:
                        pattern_score *= 1.2
                    
                    max_score = max(max_score, pattern_score)
            
            # Ajustement basé sur le contexte
            if context:
                max_score = self._adjust_score_with_context(max_score, intent_type, context)
            
            scores[intent_type] = min(max_score, 1.0)
        
        return scores
    
    def _adjust_score_with_context(self, score: float, intent_type: IntentType, context: Dict[str, Any]) -> float:
        """Ajuste le score basé sur le contexte conversationnel"""
        # Bonus pour les intentions dans le contexte
        if 'previous_intents' in context:
            if intent_type in context['previous_intents']:
                score *= 1.1
        
        # Bonus pour les mots-clés contextuels
        if 'keywords' in context:
            for keyword in context['keywords']:
                if keyword in self.context_keywords.get('urgent', []):
                    score *= 1.05
        
        return score
    
    def _select_primary_intent(self, scores: Dict[IntentType, float]) -> Tuple[IntentType, float]:
        """Sélectionne l'intention principale basée sur les scores"""
        if not scores:
            return IntentType.GENERAL_CONVERSATION, 0.0
        
        # Tri par score décroissant
        sorted_intents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        primary_intent, confidence = sorted_intents[0]
        
        # Vérification des seuils de confiance
        if confidence < self.confidence_thresholds['low']:
            # Si confiance très faible, utiliser fallback
            return IntentType.GENERAL_CONVERSATION, confidence
        
        return primary_intent, confidence
    
    def _requires_documents(self, intent: IntentType) -> bool:
        """Détermine si une intention nécessite des documents"""
        document_required_intents = {
            IntentType.PRODUCT_INQUIRY,
            IntentType.PRICING_INFO,
            IntentType.DELIVERY_INFO,
            IntentType.SUPPORT_CONTACT,
            IntentType.COMPANY_INFO,
            IntentType.ORDER_STATUS,
            IntentType.COMPLAINT,
            IntentType.TECHNICAL_SPECS,
            IntentType.MEDICAL_ADVICE
        }
        
        return intent in document_required_intents
    
    def _is_critical_intent(self, intent: IntentType) -> bool:
        """Détermine si une intention est critique"""
        critical_intents = {
            IntentType.TECHNICAL_SPECS,
            IntentType.MEDICAL_ADVICE,
            IntentType.FINANCIAL_ADVICE,
            IntentType.COMPLAINT
        }
        
        return intent in critical_intents
    
    def _extract_context_hints(self, text: str, intent: IntentType) -> List[str]:
        """Extrait les indices contextuels du texte"""
        hints = []
        
        # Vérification des mots-clés contextuels
        for category, keywords in self.context_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    hints.append(category)
        
        # Ajout des indices spécifiques à l'intention
        if intent in self.intent_patterns:
            for pattern_group in self.intent_patterns[intent]:
                hints.extend(pattern_group.get('context_hints', []))
        
        return list(set(hints))  # Suppression des doublons
    
    def get_fallback_intent(self, text: str) -> IntentType:
        """Retourne l'intention de fallback appropriée"""
        # Si le texte contient des mots de politesse, utiliser POLITENESS
        if any(word in text.lower() for word in ['merci', 'please', 's\'il vous plaît']):
            return IntentType.POLITENESS
        
        # Si le texte contient des questions, utiliser GENERAL_CONVERSATION
        if '?' in text or any(word in text.lower() for word in ['comment', 'pourquoi', 'quand']):
            return IntentType.GENERAL_CONVERSATION
        
        # Sinon, utiliser SOCIAL_GREETING par défaut
        return IntentType.SOCIAL_GREETING
    
    def clear_cache(self):
        """Vide le cache de classification"""
        self.classification_cache.clear()
        logger.info("[INTENT_CLASSIFIER] Cache vidé")

# Instance globale
intent_classifier = AdvancedIntentClassifier()

# Fonction d'interface pour compatibilité
async def classify_intent_advanced(text: str, context: Dict[str, Any] = None) -> IntentResult:
    """Interface simplifiée pour la classification d'intention"""
    return await intent_classifier.classify_intent(text, context)

if __name__ == "__main__":
    # Test du classificateur
    async def test_classifier():
        test_cases = [
            "Comment tu t'appelles ?",
            "Quels sont vos produits ?",
            "Combien coûte la livraison ?",
            "Merci beaucoup",
            "Bonjour, comment allez-vous ?"
        ]
        
        for text in test_cases:
            result = await classify_intent_advanced(text)
            print(f"'{text}' → {result.primary_intent.value} (conf: {result.confidence:.2f})")
    
    asyncio.run(test_classifier())
