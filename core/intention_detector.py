#!/usr/bin/env python3
"""
🧠 DÉTECTEUR D'INTENTION INTELLIGENT RÉVOLUTIONNAIRE
====================================================
NOUVELLE VISION:
- Index avec ≥1 doc = Intention existe (binaire)
- Stop words significatifs = Intentions d'action
- Reformulation suggestionnelle intelligente pour le LLM
- Focus sur la pertinence RAG
"""

from typing import Dict, List, Tuple, Set, Any
import re

class IntentionDetector:
    """
    Détecteur d'intention révolutionnaire basé sur:
    1. Documents prédominants par index (≥1 doc = intention existe)
    2. Stop words significatifs (intentions d'action)
    3. Suggestions contextuelles intelligentes pour le LLM
    """
    
    def __init__(self):
        # MOTS STOP WORDS SIGNIFICATIFS (révèlent des intentions d'action)
        self.action_keywords = {
            'PRIX': {
                'combien', 'prix', 'coût', 'coute', 'tarif', 'fcfa', 'fera', 
                'montant', 'total', 'cher', 'gratuit', 'payant'
            },
            'COMMANDE': {
                'commander', 'acheter', 'veux', 'voudrais', 'prendre',
                'réserver', 'valider', 'confirmer', 'commande', 'aimerais', 'souhaite'
            },
            'SUPPORT': {
                'aide', 'problème', 'question', 'comment', 'pourquoi',
                'contact', 'téléphone', 'whatsapp', 'support', 'help'
            },
            'INFORMATION': {
                'info', 'information', 'savoir', 'connaître', 'détail',
                'expliquer', 'dire', 'quoi', 'quel', 'quelle'
            }
        }
        
        # PATTERNS EXHAUSTIFS PAR TYPE D'INDEX (détection d'intention renforcée)
        self.index_keywords = {
            'PRODUIT': {
                'produit', 'article', 'item', 'stock', 'disponible', 'modèle', 
                'variante', 'catalogue', 'gamme', 'référence', 'format', 'taille',
                'couleur', 'marque', 'qualité', 'type', 'catégorie', 'collection'
            },
            'LIVRAISON': {
                'livraison', 'livrer', 'envoyer', 'expédier', 'transport', 'délai',
                'réception', 'acheminement', 'distribution', 'coursier', 'express',
                'rapide', 'standard', 'urgent', 'domicile', 'bureau'
            },
            'PAIEMENT': {
                'payer', 'paiement', 'facture', 'prix', 'coût', 'tarif', 'wave',
                'mobile', 'money', 'règlement', 'carte', 'espèces', 'virement',
                'crédit', 'débit', 'transaction', 'espèce', 'avance', 'acompte',
                'versement', 'solde', 'reste'
            },
            'LOCALISATION': {
                'zone', 'adresse', 'lieu', 'quartier', 'ville', 'région', 'secteur',
                'périmètre', 'géographique', 'territoire', 'commune', 'arrondissement',
                'boulevard', 'avenue', 'rue', 'situé', 'situe', 'locaux', 'emplacement',
                'géographique', 'position', 'coordonnées', 'localisation'
            }
        }
        
        # MAPPING INDEX → INTENTION (logique binaire)
        self.index_to_intention = {
            'products': 'PRODUIT',
            'delivery': 'LIVRAISON', 
            'support_paiement': 'PAIEMENT',
            'localisation': 'LOCALISATION',
            'company_docs': 'GENERAL'
        }
        
        # PATTERNS DE SUGGESTIONS CONTEXTUELLES
        self.suggestion_patterns = {
            # Combinaisons fréquentes
            ('PRIX', 'LIVRAISON'): "🎯 Le client veut connaître le coût de la livraison",
            ('PRIX', 'PRODUIT'): "🎯 Le client recherche des informations tarifaires sur un produit spécifique",
            ('PRIX', 'LIVRAISON', 'PRODUIT'): "🎯 Le client veut connaître le coût total (produit + livraison) pour finaliser un achat",
            ('LIVRAISON', 'LOCALISATION'): "🎯 Le client veut savoir si la livraison est possible dans sa zone",
            ('PRODUIT', 'COMMANDE'): "🎯 Le client souhaite acheter un produit spécifique",
            ('PAIEMENT', 'COMMANDE'): "🎯 Le client veut finaliser une commande et connaître les modalités de paiement",
            ('COMMANDE', 'PRIX', 'PRODUIT'): "🎯 Le client veut acheter un produit et connaître le prix",
            ('LIVRAISON', 'PRIX', 'PRODUIT'): "🎯 Le client veut connaître le coût total avec livraison",
            
            # Intentions simples
            ('PRIX',): "💰 Le client demande des informations tarifaires",
            ('LIVRAISON',): "🚚 Le client s'intéresse aux modalités de livraison",
            ('PRODUIT',): "📦 Le client recherche des informations produit",
            ('PAIEMENT',): "💳 Le client a des questions sur le paiement",
            ('SUPPORT',): "🆘 Le client a besoin d'aide ou de support",
            ('LOCALISATION',): "📍 Le client s'intéresse aux zones de service",
            ('COMMANDE',): "🛒 Le client souhaite passer commande",
            ('GENERAL',): "📄 Le client pose une question générale sur l'entreprise"
        }
    
    def detect_intentions(self, 
                         query: str, 
                         results_by_index: Dict[str, List]) -> Dict[str, Any]:
        """
        🎯 NOUVELLE LOGIQUE DE DÉTECTION D'INTENTION:
        1. Index avec ≥1 doc = Intention existe (binaire)
        2. Stop words significatifs = Intentions d'action
        3. Génération de suggestion contextuelle intelligente
        """
        
        # 1. DÉTECTER LES INTENTIONS PAR INDEX (logique binaire)
        index_intentions = self._detect_index_intentions(results_by_index)
        
        # 2. DÉTECTER LES INTENTIONS D'ACTION (stop words significatifs)
        action_intentions = self._detect_action_intentions(query)
        
        # 3. COMBINER TOUTES LES INTENTIONS
        all_intentions = list(set(index_intentions + action_intentions))
        
        # 4. GÉNÉRER LA SUGGESTION CONTEXTUELLE INTELLIGENTE
        llm_guidance = self._generate_contextual_suggestion(all_intentions, query)
        
        # 5. STRUCTURER LES DONNÉES POUR LE RAG
        structured_data = self._structure_intention_data(all_intentions)
        
        return {
            'detected_intentions': all_intentions,
            'llm_guidance': llm_guidance,
            'structured_data': structured_data,
            'confidence_score': 1.0 if all_intentions else 0.0,  # Binaire
            'evidence': {
                'index_intentions': index_intentions,
                'action_intentions': action_intentions,
                'total_indexes_with_docs': len([idx for idx, docs in results_by_index.items() if len(docs) >= 1])
            }
        }
    
    def _detect_index_intentions(self, results_by_index: Dict[str, List]) -> List[str]:
        """
        🎯 NOUVELLE LOGIQUE: Index avec ≥1 doc = Intention existe (binaire)
        Plus de calcul de poids, juste existence ou non
        """
        intentions = []
        
        for index_name, docs in results_by_index.items():
            if len(docs) >= 1:  # Seuil binaire: ≥1 doc = intention existe
                # Extraire le type d'index du nom complet
                for index_type, intention in self.index_to_intention.items():
                    if index_type in index_name:
                        intentions.append(intention)
                        break
        
        return intentions
    
    def _detect_action_intentions(self, query: str) -> List[str]:
        """
        🎯 NOUVELLE LOGIQUE: Détection binaire des intentions d'action via stop words significatifs
        """
        intentions = []
        query_lower = query.lower()
        
        # Détection via mots-clés d'action
        for intention, keywords in self.action_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                intentions.append(intention)
        
        # Détection renforcée via patterns exhaustifs d'index
        for intention, keywords in self.index_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                if intention not in intentions:
                    intentions.append(intention)
        
        return intentions
    
    def _generate_contextual_suggestion(self, intentions: List[str], query: str) -> str:
        """
        🎯 GÉNÈRE UNE SUGGESTION CONTEXTUELLE INTELLIGENTE POUR LE LLM
        Basée sur les patterns de combinaisons d'intentions
        """
        if not intentions:
            return "📄 Question générale sans intention spécifique détectée"
        
        # Trier les intentions pour créer une clé de pattern cohérente
        intentions_sorted = tuple(sorted(intentions))
        
        # Chercher un pattern exact
        if intentions_sorted in self.suggestion_patterns:
            return self.suggestion_patterns[intentions_sorted]
        
        # Chercher des patterns partiels (sous-ensembles)
        for pattern, suggestion in self.suggestion_patterns.items():
            if set(pattern).issubset(set(intentions)):
                return suggestion
        
        # Fallback: génération dynamique
        return self._generate_dynamic_suggestion(intentions, query)
    
    def _generate_dynamic_suggestion(self, intentions: List[str], query: str) -> str:
        """Génère une suggestion dynamique pour les combinaisons non prévues"""
        if len(intentions) == 1:
            intent = intentions[0]
            return f"🎯 Le client s'intéresse à : {intent}"
        
        elif len(intentions) == 2:
            return f"🎯 Le client s'intéresse à {intentions[0]} et {intentions[1]}"
        
        else:
            primary = intentions[0]
            others = ', '.join(intentions[1:])
            return f"🎯 Le client s'intéresse principalement à {primary}, avec des questions sur {others}"
    
    def _structure_intention_data(self, intentions: List[str]) -> Dict[str, Any]:
        """Structure les données d'intention pour le RAG"""
        return {
            'all_intentions': intentions,
            'primary_focus': intentions[0] if intentions else None,
            'secondary_aspects': intentions[1:] if len(intentions) > 1 else [],
            'intention_count': len(intentions),
            'has_multiple_intentions': len(intentions) > 1,
            'intention_signature': "|".join(sorted(intentions))  # Pour le cache sémantique
        }

# Instance globale
intention_detector = IntentionDetector()

def detect_user_intention(query: str, 
                         results_by_index: Dict[str, List]) -> Dict[str, Any]:
    """
    🎯 INTERFACE RÉVOLUTIONNAIRE POUR DÉTECTER L'INTENTION
    
    Args:
        query: Requête utilisateur
        results_by_index: Résultats par index après reranking
    
    Returns:
        Dict avec intentions détectées et suggestion LLM
    """
    return intention_detector.detect_intentions(query, results_by_index)

def format_intention_for_llm(intention_result: Dict[str, Any]) -> str:
    """
    📋 FORMATE LE RÉSULTAT D'INTENTION POUR LE LLM
    
    Génère un contexte enrichi avec la suggestion intelligente
    """
    if not intention_result['detected_intentions']:
        return "📄 Aucune intention spécifique détectée - Question générale"
    
    intentions = intention_result['detected_intentions']
    guidance = intention_result['llm_guidance']
    
    context_parts = [
        "🧠 ANALYSE D'INTENTION INTELLIGENTE:",
        guidance,
        f"📊 Intentions détectées: {', '.join(intentions)}",
    ]
    
    structured = intention_result['structured_data']
    if structured['has_multiple_intentions']:
        context_parts.append(f"💡 Focus principal: {structured['primary_focus']} | Aspects secondaires: {', '.join(structured['secondary_aspects'])}")
    
    return "\n".join(context_parts)
