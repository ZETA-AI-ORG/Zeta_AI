"""
Classificateur d'Intention Pré-RAG
Court-circuite HyDE pour les intentions qui ne nécessitent pas de recherche documentaire
"""

import re
from typing import Tuple, Optional
from enum import Enum

class IntentType(Enum):
    CONFIRMATION = "confirmation"  # "oui", "d'accord", "je confirme"
    META_CONVERSATION = "meta_conversation"  # "bonjour", "merci", "quel est ton nom"
    INFORMATION_SEARCH = "information_search"  # "prix des couches", "livraison"
    UNKNOWN = "unknown"

class IntentClassifier:
    def __init__(self):
        # Patterns de confirmation/transaction
        self.confirmation_patterns = [
            r'\b(oui|yes|ok|d\'accord|parfait|très bien|c\'est bon)\b',
            r'\b(je confirme|confirmé|confirmation)\b',
            r'\b(valider|validé|validation)\b',
            r'\b(accepter|accepté|j\'accepte)\b',
            r'\b(commander|commande|je commande)\b'
        ]
        
        # Patterns méta-conversation
        self.meta_patterns = [
            r'\b(bonjour|salut|bonsoir|hello|hi)\b',
            r'\b(merci|thank you|remercie)\b',
            r'\b(au revoir|bye|à bientôt)\b',
            r'\b(quel est ton nom|qui es-tu|comment tu t\'appelles)\b',
            r'\b(comment ça va|ça va)\b',
            r'\b(aide|help|assistance)\b'
        ]
        
        # Mots-clés de recherche d'information
        self.search_keywords = [
            'prix', 'coût', 'tarif', 'combien',
            'livraison', 'délai', 'transport',
            'produit', 'couche', 'taille',
            'stock', 'disponible', 'disponibilité',
            'paiement', 'mode de paiement',
            'adresse', 'zone', 'région',
            'horaire', 'ouvert', 'fermé',
            'retour', 'échange', 'garantie'
        ]

    def classify_intent(self, message: str, chat_history: str = "") -> Tuple[IntentType, float]:
        """
        Classifie l'intention du message utilisateur.
        
        Returns:
            Tuple[IntentType, float]: (type_intention, score_confiance)
        """
        message_lower = message.lower().strip()
        
        # 1. Vérifier les confirmations (priorité haute)
        confirmation_score = 0.0
        for pattern in self.confirmation_patterns:
            if re.search(pattern, message_lower):
                confirmation_score += 0.3
        
        # Bonus si le message est court et contient une confirmation
        if len(message.split()) <= 3 and confirmation_score > 0:
            confirmation_score += 0.4
            
        if confirmation_score >= 0.6:
            return IntentType.CONFIRMATION, min(confirmation_score, 1.0)
        
        # 2. Vérifier méta-conversation
        meta_score = 0.0
        for pattern in self.meta_patterns:
            if re.search(pattern, message_lower):
                meta_score += 0.4
        
        # Bonus pour messages courts de politesse
        if len(message.split()) <= 5 and meta_score > 0:
            meta_score += 0.3
            
        if meta_score >= 0.6:
            return IntentType.META_CONVERSATION, min(meta_score, 1.0)
        
        # 3. Vérifier recherche d'information
        search_score = 0.0
        for keyword in self.search_keywords:
            if keyword in message_lower:
                search_score += 0.2
        
        # Bonus pour questions explicites
        question_words = ['quel', 'quelle', 'combien', 'comment', 'où', 'quand', 'pourquoi']
        if any(word in message_lower for word in question_words):
            search_score += 0.3
            
        if search_score >= 0.4:
            return IntentType.INFORMATION_SEARCH, min(search_score, 1.0)
        
        # 4. Par défaut : recherche d'information (sécurité)
        return IntentType.INFORMATION_SEARCH, 0.3

    def should_bypass_rag(self, message: str, chat_history: str = "") -> Tuple[bool, str]:
        """
        Détermine si la pipeline RAG/HyDE doit être court-circuitée.
        
        Returns:
            Tuple[bool, str]: (bypass_rag, raison)
        """
        intent_type, confidence = self.classify_intent(message, chat_history)
        
        if intent_type == IntentType.CONFIRMATION and confidence >= 0.6:
            return True, f"Confirmation détectée (confiance: {confidence:.2f})"
        
        if intent_type == IntentType.META_CONVERSATION and confidence >= 0.6:
            return True, f"Méta-conversation détectée (confiance: {confidence:.2f})"
        
        return False, f"Recherche d'information requise (confiance: {confidence:.2f})"

# Instance globale
intent_classifier = IntentClassifier()

def integrate_intent_classification(message: str, chat_history: str = "") -> Tuple[bool, str, IntentType]:
    """
    Fonction d'intégration pour la pipeline RAG.
    
    Returns:
        Tuple[bool, str, IntentType]: (bypass_rag, raison, type_intention)
    """
    bypass, reason = intent_classifier.should_bypass_rag(message, chat_history)
    intent_type, _ = intent_classifier.classify_intent(message, chat_history)
    
    return bypass, reason, intent_type
