"""
Détecteur de changement de sujet (Context Switch)
Détecte quand l'utilisateur change de sujet pour réinitialiser le contexte dynamique
"""

import re
from typing import List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class TopicContext:
    """Représente le contexte d'un sujet de conversation"""
    main_topic: str
    keywords: List[str]
    confidence: float
    message_count: int = 1

class ContextSwitchDetector:
    def __init__(self):
        # Catégories de sujets principaux
        self.topic_patterns = {
            'produits_casques': re.compile(r'\b(casque|casques|moto|motard|protection|équipement)\b', re.I),
            'produits_couches': re.compile(r'\b(couche|couches|bébé|bébés|nourrisson|enfant|taille)\b', re.I),
            'prix_tarifs': re.compile(r'\b(prix|tarif|coût|combien|montant|frais|cher)\b', re.I),
            'livraison': re.compile(r'\b(livraison|délai|transport|expédition|réception)\b', re.I),
            'contact_info': re.compile(r'\b(contact|téléphone|email|adresse|horaire|whatsapp)\b', re.I),
            'commande_achat': re.compile(r'\b(commande|commander|acheter|achat|panier|paiement)\b', re.I),
            'stock_dispo': re.compile(r'\b(stock|disponible|disponibilité|rupture|réappro)\b', re.I),
            'retour_echange': re.compile(r'\b(retour|échange|garantie|remboursement|défaut)\b', re.I),
            'entreprise_info': re.compile(r'\b(entreprise|société|mission|qui|présentation)\b', re.I),
            'localisation': re.compile(r'\b(où|adresse|zone|quartier|région|ville|Abidjan|Cocody)\b', re.I)
        }
        
        # Mots de transition qui indiquent un changement de sujet
        self.transition_words = [
            'sinon', 'autrement', 'par contre', 'en fait', 'plutôt', 'finalement',
            'maintenant', 'aussi', 'également', 'autre chose', 'autre question',
            'passons à', 'parlons de', 'concernant', 'à propos de'
        ]
        
        # Historique du contexte (derniers sujets)
        self.topic_history: List[TopicContext] = []
        self.max_history = 3

    def extract_topic(self, message: str) -> Optional[TopicContext]:
        """Extrait le sujet principal d'un message"""
        message_lower = message.lower()
        topic_scores = {}
        
        # Calculer les scores pour chaque sujet
        for topic, pattern in self.topic_patterns.items():
            matches = pattern.findall(message)
            if matches:
                # Score basé sur le nombre de matches et leur pertinence
                score = len(matches) * 0.3
                
                # Bonus si le sujet est mentionné explicitement
                if any(word in message_lower for word in matches):
                    score += 0.4
                
                topic_scores[topic] = score
        
        if not topic_scores:
            return None
        
        # Prendre le sujet avec le meilleur score
        best_topic = max(topic_scores, key=topic_scores.get)
        confidence = min(topic_scores[best_topic], 1.0)
        
        # Extraire les mots-clés pertinents
        keywords = []
        pattern = self.topic_patterns[best_topic]
        keywords.extend(pattern.findall(message))
        
        return TopicContext(
            main_topic=best_topic,
            keywords=keywords,
            confidence=confidence
        )

    def detect_context_switch(self, message: str) -> Tuple[bool, str, Optional[str]]:
        """
        Détecte si il y a un changement de sujet
        
        Returns:
            Tuple[bool, str, Optional[str]]: (has_switched, reason, new_topic)
        """
        # Extraire le sujet actuel
        current_topic = self.extract_topic(message)
        
        if not current_topic:
            return False, "Aucun sujet spécifique détecté", None
        
        # Vérifier les mots de transition
        message_lower = message.lower()
        has_transition = any(word in message_lower for word in self.transition_words)
        
        # Si pas d'historique, c'est le premier sujet
        if not self.topic_history:
            self.topic_history.append(current_topic)
            return False, "Premier sujet de conversation", current_topic.main_topic
        
        # Comparer avec le dernier sujet
        last_topic = self.topic_history[-1]
        
        # Changement de sujet détecté si :
        # 1. Le sujet principal est différent ET
        # 2. Il y a des mots de transition OU la confiance est élevée
        if (current_topic.main_topic != last_topic.main_topic and 
            (has_transition or current_topic.confidence > 0.7)):
            
            # Ajouter le nouveau sujet à l'historique
            self.topic_history.append(current_topic)
            
            # Limiter l'historique
            if len(self.topic_history) > self.max_history:
                self.topic_history.pop(0)
            
            reason = f"Changement de '{last_topic.main_topic}' vers '{current_topic.main_topic}'"
            if has_transition:
                reason += " (mots de transition détectés)"
            
            return True, reason, current_topic.main_topic
        
        # Pas de changement, mais mettre à jour le compteur
        last_topic.message_count += 1
        return False, f"Continuation du sujet '{last_topic.main_topic}'", last_topic.main_topic

    def reset_context(self):
        """Remet à zéro l'historique des sujets"""
        self.topic_history.clear()

    def get_current_topic(self) -> Optional[str]:
        """Retourne le sujet actuel ou None"""
        if self.topic_history:
            return self.topic_history[-1].main_topic
        return None

    def get_topic_summary(self) -> str:
        """Retourne un résumé des sujets récents"""
        if not self.topic_history:
            return "Aucun sujet identifié"
        
        topics = [f"{t.main_topic} ({t.message_count} msg)" for t in self.topic_history[-2:]]
        return " → ".join(topics)

# Instance globale
context_switch_detector = ContextSwitchDetector()

def detect_topic_change(message: str) -> Tuple[bool, str, Optional[str]]:
    """
    Fonction d'intégration pour détecter les changements de sujet
    
    Returns:
        Tuple[bool, str, Optional[str]]: (has_switched, reason, new_topic)
    """
    return context_switch_detector.detect_context_switch(message)

def reset_topic_context():
    """Remet à zéro le contexte des sujets"""
    context_switch_detector.reset_context()

def get_current_topic() -> Optional[str]:
    """Retourne le sujet actuel de conversation"""
    return context_switch_detector.get_current_topic()
