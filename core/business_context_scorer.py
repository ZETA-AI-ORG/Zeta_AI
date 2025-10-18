import json
import re
from typing import Dict, List, Any, Set
from dataclasses import dataclass
from enum import Enum

class ContextType(Enum):
    CORE_BUSINESS = "core_business"
    PRODUCT = "product"
    SERVICE = "service"
    GEOGRAPHIC = "geographic"
    OPERATIONAL = "operational"
    SUPPORT = "support"
    GENERIC = "generic"

@dataclass
class ScoringWeights:
    """Poids pour différents types de contexte"""
    core_business: float = 10.0    # Mission, secteur d'activité
    product_direct: float = 9.0    # Noms de produits, catégories principales
    product_attributes: float = 7.0  # Couleurs, spécifications
    service_direct: float = 8.0    # Livraison, paiement
    geographic: float = 6.0        # Zones, villes
    operational: float = 5.0       # Stock, prix
    support: float = 4.0          # Contact, assistance
    generic: float = 1.0          # Mots communs

class BusinessContextScorer:
    """Système de scoring contextuel pour entreprises"""
    
    def __init__(self):
        self.weights = ScoringWeights()
        self.stop_words = {
            'le', 'la', 'les', 'de', 'du', 'des', 'et', 'ou', 'à', 'au', 'aux',
            'un', 'une', 'ce', 'cette', 'est', 'sont', 'pour', 'avec', 'sur',
            'dans', 'par', 'plus', 'moins', 'très', 'tout', 'tous', 'toute'
        }
        
    def extract_business_context(self, company_data: Dict) -> Dict[str, Set[str]]:
        """Extrait le contexte métier de l'entreprise"""
        context = {
            'core_business': set(),
            'product_categories': set(),
            'product_names': set(),
            'product_attributes': set(),
            'service_types': set(),
            'geographic_zones': set(),
            'operational_terms': set(),
            'support_channels': set()
        }
        
        for doc in company_data.get('text_documents', []):
            metadata = doc.get('metadata', {})
            doc_type = metadata.get('type', '')
            
            if doc_type == 'company':
                # Contexte métier principal
                context['core_business'].update(self._extract_terms(metadata.get('sector', '')))
                context['core_business'].update(self._extract_terms(metadata.get('mission', '')))
                context['geographic_zones'].update(metadata.get('zones', []))
                
            elif doc_type == 'product':
                # Produits et leurs attributs
                context['product_categories'].update(self._extract_terms(metadata.get('category', '')))
                context['product_categories'].update(self._extract_terms(metadata.get('subcategory', '')))
                context['product_names'].update(self._extract_terms(metadata.get('product_name', '')))
                
                # Attributs produits
                attributes = metadata.get('attributes', {})
                for key, value in attributes.items():
                    context['product_attributes'].update(self._extract_terms(str(value)))
                
                # Termes opérationnels
                if metadata.get('price'):
                    context['operational_terms'].add('prix')
                if metadata.get('stock'):
                    context['operational_terms'].add('stock')
                    
            elif doc_type == 'delivery':
                # Services de livraison
                context['service_types'].add('livraison')
                context['geographic_zones'].update([metadata.get('city', '')])
                if 'zone' in metadata:
                    context['geographic_zones'].add(metadata['zone'])
                if 'zone_group' in metadata:
                    context['geographic_zones'].update(metadata['zone_group'])
                    
            elif doc_type == 'payment':
                # Méthodes de paiement
                context['service_types'].add('paiement')
                context['service_types'].update(self._extract_terms(metadata.get('method', '')))
                
            elif doc_type == 'support':
                # Support client
                context['support_channels'].update(metadata.get('channels', []))
                context['support_channels'].add('support')
                
        return context
    
    def _extract_terms(self, text: str) -> Set[str]:
        """Extrait les termes significatifs d'un texte"""
        if not text:
            return set()
            
        # Nettoyage et normalisation
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        terms = text.split()
        
        # Filtrage des mots vides
        return {term for term in terms if term not in self.stop_words and len(term) > 2}
    
    def calculate_word_score(self, word: str, business_context: Dict[str, Set[str]]) -> float:
        """Calcule le score d'un mot selon le contexte métier"""
        word_lower = word.lower()
        
        # Score maximal : contexte métier principal
        if word_lower in business_context['core_business']:
            return self.weights.core_business
            
        # Score élevé : noms de produits et catégories principales
        if word_lower in business_context['product_names']:
            return self.weights.product_direct
        if word_lower in business_context['product_categories']:
            return self.weights.product_direct
            
        # Score moyen-élevé : services directs
        if word_lower in business_context['service_types']:
            return self.weights.service_direct
            
        # Score moyen : attributs produits
        if word_lower in business_context['product_attributes']:
            return self.weights.product_attributes
            
        # Score moyen-bas : zones géographiques
        if word_lower in business_context['geographic_zones']:
            return self.weights.geographic
            
        # Score bas : termes opérationnels
        if word_lower in business_context['operational_terms']:
            return self.weights.operational
            
        # Score minimal : support
        if word_lower in business_context['support_channels']:
            return self.weights.support
            
        # Scoring par similarité partielle
        partial_score = self._calculate_partial_match_score(word_lower, business_context)
        if partial_score > 0:
            return partial_score
            
        # Score par défaut pour mots génériques
        return self.weights.generic
    
    def _calculate_partial_match_score(self, word: str, context: Dict[str, Set[str]]) -> float:
        """Calcule un score basé sur la similarité partielle"""
        max_score = 0.0
        
        # Vérification de correspondances partielles
        for category, terms in context.items():
            for term in terms:
                if len(word) >= 4 and len(term) >= 4:
                    # Correspondance par inclusion
                    if word in term or term in word:
                        if category == 'core_business':
                            max_score = max(max_score, self.weights.core_business * 0.7)
                        elif category in ['product_names', 'product_categories']:
                            max_score = max(max_score, self.weights.product_direct * 0.6)
                        elif category == 'service_types':
                            max_score = max(max_score, self.weights.service_direct * 0.5)
                        elif category == 'product_attributes':
                            max_score = max(max_score, self.weights.product_attributes * 0.5)
        
        return max_score
    
    def score_document_terms(self, company_data: Dict, text: str) -> Dict[str, float]:
        """Score tous les termes d'un document"""
        business_context = self.extract_business_context(company_data)
        terms = self._extract_terms(text)
        
        scores = {}
        for term in terms:
            scores[term] = self.calculate_word_score(term, business_context)
            
        return scores
    
    def get_context_summary(self, company_data: Dict) -> Dict[str, Any]:
        """Résumé du contexte métier extrait"""
        context = self.extract_business_context(company_data)
        
        return {
            'core_business_terms': list(context['core_business']),
            'product_categories': list(context['product_categories']),
            'product_names': list(context['product_names']),
            'top_attributes': list(context['product_attributes']),
            'services': list(context['service_types']),
            'geographic_coverage': list(context['geographic_zones']),
            'total_unique_terms': sum(len(terms) for terms in context.values())
        }

    def filter_query_words(self, query: str, business_context: Dict[str, Set[str]], threshold: float = 4.0) -> List[tuple]:
        """Filtre les mots d'une requête selon leur pertinence"""
        terms = self._extract_terms(query)
        word_scores = []
        
        for term in terms:
            score = self.calculate_word_score(term, business_context)
            if score >= threshold:
                word_scores.append((term, score))
        
        # Tri par score décroissant
        return sorted(word_scores, key=lambda x: x[1], reverse=True)
    
    def get_filtered_search_terms(self, query: str, company_data: Dict, threshold: float = 4.0) -> str:
        """Retourne une requête filtrée avec seulement les mots pertinents"""
        business_context = self.extract_business_context(company_data)
        filtered_words = self.filter_query_words(query, business_context, threshold)
        
        # Reconstruction de la requête avec mots pertinents
        return " ".join([word for word, score in filtered_words])

# Exemple d'utilisation pour le filtrage de requêtes
if __name__ == "__main__":
    # Données de votre entreprise "rue du grossiste"
    company_data = {
        "text_documents": [
            {
                "metadata": {
                    "type": "company",
                    "sector": "Auto & Moto",
                    "mission": "proposer les meilleurs produits aux meilleurs prix",
                    "zones": ["Cote d'ivoire"]
                }
            },
            {
                "metadata": {
                    "type": "product",
                    "product_name": "CASQUES MOTO",
                    "category": "Auto & Moto",
                    "subcategory": "Casques & Équipement Moto",
                    "attributes": {"Couleur": "BLEU"},
                    "color": "BLEU"
                }
            }
        ]
    }
    
    scorer = BusinessContextScorer()
    
    # Test avec différentes requêtes utilisateur
    test_queries = [
        "je veux un casque moto bleu",
        "avez vous des produits pour moto ?",
        "casque rouge disponible ?",
        "prix livraison abidjan",
        "comment puis-je vous contacter ?"
    ]
    
    print("=== FILTRAGE DE REQUÊTES ===")
    for query in test_queries:
        print(f"\nRequête: '{query}'")
        
        # Filtrage avec seuil 4.0
        filtered = scorer.get_filtered_search_terms(query, company_data, threshold=4.0)
        print(f"Mots conservés (seuil 4.0): '{filtered}'")
        
        # Détail des scores
        business_context = scorer.extract_business_context(company_data)
        word_scores = scorer.filter_query_words(query, business_context, threshold=0.0)
        print("Scores détaillés:", [(w, round(s, 1)) for w, s in word_scores])
    
    print("\n=== RECOMMANDATIONS SEUILS ===")
    print("Seuil 6.0+ : Mots très pertinents (produits, secteur)")
    print("Seuil 4.0+ : Mots pertinents (incluant services, zones)")
    print("Seuil 2.0+ : Mots moyennement pertinents")
    print("Seuil <2.0 : Mots génériques (à filtrer)")
