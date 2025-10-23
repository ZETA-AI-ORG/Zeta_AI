#!/usr/bin/env python3
"""
🔧 PROCESSEUR NLP SIMPLIFIÉ
Normalisation basique, détection intentions, NER
Système francophonie SUPPRIMÉ - Version allégée
"""

import re
import logging
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from unidecode import unidecode
from rapidfuzz import fuzz
# Système francophonie SUPPRIMÉ

logger = logging.getLogger(__name__)

@dataclass
class ProcessedQuery:
    """Résultat du traitement NLP"""
    original: str
    normalized: str
    lemmatized_words: List[str]
    corrected: str
    intentions: List[Dict[str, Any]]
    entities: List[Dict[str, Any]]
    split_queries: List[str]
    confidence: float

@dataclass
class IntentResult:
    """Résultat de détection d'intention"""
    intent: str
    confidence: float
    keywords: List[str]
    context: str

@dataclass
class EntityResult:
    """Résultat d'extraction d'entité"""
    entity: str
    type: str
    confidence: float
    position: Tuple[int, int]

class FrenchNLPProcessor:
    """
    🇫🇷 Processeur NLP français complet
    
    Fonctionnalités :
    - Normalisation (accents, casse, ponctuation)
    - Lemmatisation (singulier/pluriel, conjugaisons)
    - Correction orthographique légère
    - Détection d'intentions (e-commerce)
    - Extraction d'entités nommées
    - Split multi-intentions
    """
    
    def __init__(self):
        self.lemmatizer = None
        self._init_lemmatizer()
        
        # Intentions e-commerce françaises
        self.intent_patterns = {
            'product_inquiry': {
                'keywords': ['produit', 'article', 'vendre', 'vendez', 'disponible', 'stock', 'catalogue', 'gamme', 'référence'],
                'patterns': [
                    r'(?:que|quoi|qu\'est-ce que)\s+(?:vous\s+)?(?:vendez|proposez|avez)',
                    r'(?:quels?\s+)?(?:produits?|articles?)\s+(?:vous\s+)?(?:avez|vendez|proposez)',
                    r'(?:avez-vous|vous avez)\s+(?:des?\s+)?(?:produits?|articles?)',
                    r'(?:je\s+)?(?:cherche|recherche|veux|souhaite)\s+(?:un|une|des?)',
                    r'(?:disponible|en stock|dispo)'
                ]
            },
            'price_inquiry': {
                'keywords': ['prix', 'coût', 'coute', 'tarif', 'montant', 'fcfa', 'combien', 'cher'],
                'patterns': [
                    r'(?:quel\s+(?:est\s+le\s+)?)?prix',
                    r'(?:combien\s+)?(?:ça\s+)?(?:coûte|coute)',
                    r'(?:c\'est\s+)?combien',
                    r'tarifs?',
                    r'\d+\s*fcfa'
                ]
            },
            'order_intent': {
                'keywords': ['commander', 'commande', 'acheter', 'prendre', 'veux', 'souhaite', 'réserver'],
                'patterns': [
                    r'(?:je\s+)?(?:veux|souhaite|voudrai)\s+(?:commander|acheter|prendre)',
                    r'(?:passer\s+)?(?:une\s+)?commande',
                    r'(?:je\s+)?(?:commande|achète|prends)',
                    r'(?:réserver|réservation)'
                ]
            },
            'delivery_inquiry': {
                'keywords': ['livraison', 'livrer', 'livrez', 'transport', 'expédition', 'délai', 'quand'],
                'patterns': [
                    r'livraisons?',
                    r'(?:vous\s+)?livrez',
                    r'(?:délai|temps)\s+(?:de\s+)?livraison',
                    r'(?:quand|combien de temps)\s+.*(?:livr|reçoi)',
                    r'(?:frais\s+(?:de\s+)?)?(?:port|livraison|transport)'
                ]
            },
            'payment_inquiry': {
                'keywords': ['paiement', 'payer', 'payez', 'règlement', 'acompte', 'wave', 'mobile money'],
                'patterns': [
                    r'(?:comment\s+)?(?:payer|régler)',
                    r'(?:mode|moyen)\s+(?:de\s+)?paiement',
                    r'acomptes?',
                    r'wave|mobile\s+money',
                    r'(?:acceptez|prenez)\s+.*(?:wave|mobile|carte)'
                ]
            },
            'size_inquiry': {
                'keywords': ['taille', 'tailles', 'pointure', 'dimension', 'grandeur', 'format'],
                'patterns': [
                    r'(?:quelles?\s+)?tailles?',
                    r'(?:quelle\s+)?pointure',
                    r'(?:en\s+)?taille\s+\d+',
                    r'dimensions?',
                    r'(?:petit|moyen|grand|xl|xxl)'
                ]
            },
            'availability_inquiry': {
                'keywords': ['disponible', 'dispo', 'stock', 'rupture', 'épuisé', 'reste'],
                'patterns': [
                    r'(?:c\'est\s+)?disponibles?',
                    r'(?:en\s+)?stocks?',
                    r'(?:il\s+(?:vous\s+)?)?reste',
                    r'(?:rupture|épuisé)',
                    r'(?:avez-vous|vous avez)\s+(?:encore|toujours)'
                ]
            }
        }
        
        # Entités e-commerce françaises
        self.entity_patterns = {
            'PRODUCT_TYPE': {
                'patterns': [
                    r'couches?\s+(?:culottes?|à\s+pression|adultes?)',
                    r'(?:culottes?|pression)',
                    r'pampers?|huggies',
                    r'lingettes?',
                    r'produits?\s+bébé'
                ]
            },
            'QUANTITY': {
                'patterns': [
                    r'(\d+)\s*(?:paquets?|lots?|pièces?|unités?)',
                    r'(?:un|une|deux|trois|quatre|cinq|six|sept|huit|neuf|dix)\s+(?:paquet|lot)',
                    r'quantité\s*:\s*(\d+)'
                ]
            },
            'SIZE': {
                'patterns': [
                    r'taille\s*(\d+)',
                    r't(\d+)',
                    r'size\s*(\d+)',
                    r'(\d+)(?:kg|g)\s*(?:à|-)?\s*(\d+)(?:kg|g)'
                ]
            },
            'LOCATION': {
                'patterns': [
                    r'(?:à|vers|sur|dans)\s+(cocody|yopougon|plateau|adjamé|abobo|marcory|koumassi|treichville)',
                    r'(?:abidjan|bouaké|yamoussoukro|daloa|korhogo|san-pedro)',
                    r'côte\s+d\'ivoire|ci|225'
                ]
            },
            'PHONE': {
                'patterns': [
                    r'(\+?225\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{2})',
                    r'(0\d{2}\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{2})',
                    r'(\d{10})'
                ]
            },
            'PRICE': {
                'patterns': [
                    r'(\d+(?:[,\.]\d+)?)\s*(?:fcfa|f\s*cfa|francs?)',
                    r'(\d+)\s*(?:mille|k)\s*(?:fcfa|f)'
                ]
            }
        }
        
        # Mots de liaison pour split multi-intent
        self.intent_separators = [
            r'\s+et\s+(?:aussi\s+)?',
            r'\s+ainsi\s+que\s+',
            r'\s+également\s+',
            r'\s+de\s+plus\s+',
            r'\s+aussi\s+',
            r'\s*[,;]\s*(?:et\s+)?(?:aussi\s+)?',
            r'\s+ou\s+(?:bien\s+)?'
        ]
    
    def _init_lemmatizer(self):
        """Initialise le lemmatiseur français"""
        # Lemmatiseur désactivé (package non installé)
        self.lemmatizer = None
        logger.info("ℹ️ Lemmatiseur désactivé (non requis)")
    
    def normalize_text(self, text: str) -> str:
        """Normalise le texte (accents, casse, ponctuation)"""
        if not text:
            return ""
        
        # Supprimer accents
        normalized = unidecode(text.lower().strip())
        
        # Nettoyer ponctuation excessive
        normalized = re.sub(r'[^\w\s\-\']', ' ', normalized)
        
        # Normaliser espaces
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def lemmatize_words(self, text: str) -> List[str]:
        """Lemmatise tous les mots du texte"""
        if not self.lemmatizer or not text:
            return text.split()
        
        words = re.findall(r'\w+', text.lower())
        lemmatized = []
        
        for word in words:
            try:
                lemma = self.lemmatizer.lemmatize(word)
                lemmatized.append(lemma if lemma else word)
            except Exception:
                lemmatized.append(word)
        
        return lemmatized
    
    def correct_spelling(self, text: str) -> str:
        """Correction orthographique légère (patterns courants)"""
        corrections = {
            r'\bcombieng?\b': 'combien',
            r'\blivreison\b': 'livraison',
            r'\bcomande\b': 'commande',
            r'\bproduis\b': 'produits',
            r'\bprix\s+c\'est\b': 'prix',
            r'\bc\'est\s+quoi\s+le\s+prix\b': 'quel est le prix',
            r'\bje\s+veu\b': 'je veux',
            r'\bvous\s+avé\b': 'vous avez'
        }
        
        corrected = text
        for pattern, replacement in corrections.items():
            corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
        
        return corrected
    
    def detect_intentions(self, text: str) -> List[IntentResult]:
        """Détecte les intentions dans le texte"""
        text_lower = text.lower()
        detected_intents = []
        
        for intent_name, intent_data in self.intent_patterns.items():
            confidence = 0
            found_keywords = []
            
            # Score basé sur les mots-clés
            for keyword in intent_data['keywords']:
                if keyword in text_lower:
                    confidence += 0.1
                    found_keywords.append(keyword)
            
            # Score basé sur les patterns regex
            for pattern in intent_data['patterns']:
                if re.search(pattern, text_lower):
                    confidence += 0.3
                    break
            
            # Bonus si plusieurs mots-clés
            if len(found_keywords) > 1:
                confidence += 0.2
            
            if confidence > 0.2:  # Seuil minimal
                detected_intents.append(IntentResult(
                    intent=intent_name,
                    confidence=min(confidence, 1.0),
                    keywords=found_keywords,
                    context=text[:100]
                ))
        
        # Trier par confiance décroissante
        detected_intents.sort(key=lambda x: x.confidence, reverse=True)
        return detected_intents
    
    def extract_entities(self, text: str) -> List[EntityResult]:
        """Extrait les entités nommées du texte"""
        entities = []
        
        for entity_type, entity_data in self.entity_patterns.items():
            for pattern in entity_data['patterns']:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    entity_text = match.group(0)
                    start, end = match.span()
                    
                    # Calculer confiance basée sur la longueur et contexte
                    confidence = 0.7
                    if len(entity_text) > 5:
                        confidence += 0.2
                    if entity_type in ['PHONE', 'PRICE', 'QUANTITY']:
                        confidence += 0.1
                    
                    entities.append(EntityResult(
                        entity=entity_text,
                        type=entity_type,
                        confidence=min(confidence, 1.0),
                        position=(start, end)
                    ))
        
        # Déduplication par position
        unique_entities = []
        used_positions = set()
        
        for entity in sorted(entities, key=lambda x: x.confidence, reverse=True):
            if entity.position not in used_positions:
                unique_entities.append(entity)
                used_positions.add(entity.position)
        
        return unique_entities
    
    def split_multi_intent(self, text: str, intentions: List[IntentResult]) -> List[str]:
        """Split une requête multi-intentions en requêtes distinctes"""
        if len(intentions) <= 1:
            return [text]
        
        # Chercher les séparateurs
        split_queries = [text]
        
        for separator_pattern in self.intent_separators:
            new_splits = []
            for query in split_queries:
                parts = re.split(separator_pattern, query)
                if len(parts) > 1:
                    # Nettoyer et filtrer les parties vides
                    clean_parts = [part.strip() for part in parts if part.strip() and len(part.strip()) > 5]
                    new_splits.extend(clean_parts)
                else:
                    new_splits.append(query)
            split_queries = new_splits
        
        # Déduplication et validation
        final_queries = []
        for query in split_queries:
            query = query.strip()
            if query and len(query) > 5 and query not in final_queries:
                final_queries.append(query)
        
        return final_queries if len(final_queries) > 1 else [text]
    
    def process_query(self, query: str) -> ProcessedQuery:
        """Traitement complet d'une requête"""
        logger.info(f"🇫🇷 [NLP] Traitement: '{query[:50]}...'")
        
        # Étapes de traitement
        corrected = self.correct_spelling(query)
        normalized = self.normalize_text(corrected)
        lemmatized_words = self.lemmatize_words(normalized)
        intentions = self.detect_intentions(query)
        entities = self.extract_entities(query)
        split_queries = self.split_multi_intent(query, intentions)
        
        # Calcul confiance globale
        confidence = 0.5
        if intentions:
            confidence += 0.2 * min(len(intentions), 2)
        if entities:
            confidence += 0.1 * min(len(entities), 3)
        if len(split_queries) > 1:
            confidence += 0.1
        
        confidence = min(confidence, 1.0)
        
        # Logs détaillés
        logger.info(f"🇫🇷 [NLP] Normalisé: '{normalized}'")
        logger.info(f"🇫🇷 [NLP] Lemmatisé: {lemmatized_words[:10]}...")
        logger.info(f"🇫🇷 [NLP] Intentions: {[i.intent for i in intentions]}")
        logger.info(f"🇫🇷 [NLP] Entités: {[(e.entity, e.type) for e in entities]}")
        logger.info(f"🇫🇷 [NLP] Split: {len(split_queries)} requêtes")
        logger.info(f"🇫🇷 [NLP] Confiance: {confidence:.2f}")
        
        return ProcessedQuery(
            original=query,
            normalized=normalized,
            lemmatized_words=lemmatized_words,
            corrected=corrected,
            intentions=[{
                'intent': i.intent,
                'confidence': i.confidence,
                'keywords': i.keywords,
                'context': i.context
            } for i in intentions],
            entities=[{
                'entity': e.entity,
                'type': e.type,
                'confidence': e.confidence,
                'position': e.position
            } for e in entities],
            split_queries=split_queries,
            confidence=confidence
        )

# Instance globale
french_nlp = FrenchNLPProcessor()

# Interface simple
def process_french_query(query: str) -> ProcessedQuery:
    """Interface simple pour traitement NLP français"""
    return french_nlp.process_query(query)

if __name__ == "__main__":
    # Tests
    test_queries = [
        "QUELS SONT LES TAILLES DISPONIBLES EN PRESSION ET AUSSI EN CULOTTES?",
        "je veux commander 3 paquets de couches taille 2 et combien pour livraison à Cocody",
        "c'est combien le prix des culottes et vous livrez quand?",
        "avez-vous des produits en stock? je cherche des couches pour bébé"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"QUERY: {query}")
        print('='*60)
        
        result = process_french_query(query)
        print(f"Normalisé: {result.normalized}")
        print(f"Intentions: {[i['intent'] for i in result.intentions]}")
        print(f"Entités: {[(e['entity'], e['type']) for e in result.entities]}")
        print(f"Split: {result.split_queries}")
        print(f"Confiance: {result.confidence:.2f}")
