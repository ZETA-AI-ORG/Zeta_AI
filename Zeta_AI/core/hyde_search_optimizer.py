#!/usr/bin/env python3
"""
🎯 OPTIMISEUR DE RECHERCHE BASÉ SUR LE SCORING HYDE
Exploite les scores de mots pour optimiser la recherche de documents
"""

import asyncio
import sys
import os
sys.path.append('.')
from typing import Dict, List, Optional, Tuple, Any
from core.hyde_word_scorer import HydeWordScorer
from core.metadata_extractor import MetadataExtractor
import json

class HydeSearchOptimizer:
    """
    Optimiseur de recherche utilisant les scores HyDE pour améliorer la pertinence
    """
    
    def __init__(self):
        self.hyde_scorer = HydeWordScorer()
        
    async def optimize_query(self, query: str, company_id: str, sector: str = None) -> Dict[str, Any]:
        """
        Optimise une requête en analysant les scores des mots
        
        Returns:
            Dict avec requête optimisée et métadonnées de boost
        """
        # 1. Scorer les mots de la requête
        word_scores = await self.hyde_scorer.score_query_words(query, sector)
        
        # 2. Analyser la distribution des scores
        analysis = self._analyze_word_scores(word_scores)
        
        # 3. Générer les boosts pour MeiliSearch
        search_boosts = self._generate_search_boosts(word_scores, analysis)
        
        # 4. Créer la requête optimisée
        optimized_query = self._build_optimized_query(query, word_scores, analysis)
        
        return {
            "original_query": query,
            "optimized_query": optimized_query,
            "word_scores": word_scores,
            "analysis": analysis,
            "search_boosts": search_boosts,
            "optimization_strategy": self._get_optimization_strategy(analysis)
        }
    
    def _analyze_word_scores(self, word_scores: Dict[str, int]) -> Dict[str, Any]:
        """Analyse la distribution des scores pour déterminer la stratégie"""
        if not word_scores:
            return {"type": "empty", "confidence": 0}
        
        scores = list(word_scores.values())
        critical_words = [w for w, s in word_scores.items() if s >= 10]
        high_words = [w for w, s in word_scores.items() if s >= 8]
        medium_words = [w for w, s in word_scores.items() if s >= 5]
        low_words = [w for w, s in word_scores.items() if s < 5]
        
        total_words = len(word_scores)
        avg_score = sum(scores) / len(scores) if scores else 0
        max_score = max(scores) if scores else 0
        
        # Déterminer le type de requête
        if len(critical_words) >= 2:
            query_type = "high_precision"
            confidence = 0.9
        elif len(high_words) >= 1:
            query_type = "balanced"
            confidence = 0.7
        elif len(medium_words) >= 1:
            query_type = "exploratory"
            confidence = 0.5
        else:
            query_type = "generic"
            confidence = 0.3
        
        return {
            "type": query_type,
            "confidence": confidence,
            "total_words": total_words,
            "avg_score": avg_score,
            "max_score": max_score,
            "critical_words": critical_words,
            "high_words": high_words,
            "medium_words": medium_words,
            "low_words": low_words,
            "score_distribution": {
                "10+": len(critical_words),
                "8-9": len([w for w, s in word_scores.items() if 8 <= s < 10]),
                "5-7": len([w for w, s in word_scores.items() if 5 <= s < 8]),
                "0-4": len(low_words)
            }
        }
    
    def _generate_search_boosts(self, word_scores: Dict[str, int], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Génère les boosts pour optimiser la recherche MeiliSearch"""
        
        # Boosts basés sur les scores de mots
        word_boosts = {}
        for word, score in word_scores.items():
            if score >= 10:
                word_boosts[word] = 10.0  # Boost maximum
            elif score >= 8:
                word_boosts[word] = 5.0   # Boost élevé
            elif score >= 5:
                word_boosts[word] = 2.0   # Boost modéré
            else:
                word_boosts[word] = 1.0   # Boost neutre
        
        # Stratégie de recherche adaptée
        if analysis["type"] == "high_precision":
            strategy = {
                "mode": "precise",
                "searchable_text_boost": 15,
                "content_boost": 8,
                "metadata_boost": 12,
                "typo_tolerance": False,
                "exact_match_priority": True
            }
        elif analysis["type"] == "balanced":
            strategy = {
                "mode": "balanced", 
                "searchable_text_boost": 10,
                "content_boost": 5,
                "metadata_boost": 8,
                "typo_tolerance": True,
                "exact_match_priority": False
            }
        else:
            strategy = {
                "mode": "broad",
                "searchable_text_boost": 8,
                "content_boost": 3,
                "metadata_boost": 5,
                "typo_tolerance": True,
                "exact_match_priority": False
            }
        
        return {
            "word_boosts": word_boosts,
            "strategy": strategy,
            "confidence_multiplier": analysis["confidence"]
        }
    
    def _build_optimized_query(self, original_query: str, word_scores: Dict[str, int], analysis: Dict[str, Any]) -> str:
        """Construit une requête optimisée avec boosts intégrés"""
        
        words = original_query.lower().split()
        optimized_parts = []
        
        for word in words:
            score = word_scores.get(word, 0)
            
            if score >= 10:
                # Mots critiques - boost maximum avec guillemets pour exactitude
                optimized_parts.append(f'"{word}"^10')
            elif score >= 8:
                # Mots très pertinents - boost élevé
                optimized_parts.append(f"{word}^5")
            elif score >= 5:
                # Mots pertinents - boost modéré
                optimized_parts.append(f"{word}^2")
            else:
                # Mots normaux - pas de boost
                optimized_parts.append(word)
        
        return " ".join(optimized_parts)
    
    def _get_optimization_strategy(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Détermine la stratégie d'optimisation recommandée"""
        
        strategy_map = {
            "high_precision": {
                "description": "Requête haute précision avec mots critiques",
                "recommended_actions": [
                    "Prioriser searchable_text avec boost 15x",
                    "Désactiver tolérance typos",
                    "Forcer correspondance exacte",
                    "Limiter à 5-10 résultats"
                ],
                "index_priority": ["products", "delivery", "support_paiement"]
            },
            "balanced": {
                "description": "Requête équilibrée avec bonne pertinence",
                "recommended_actions": [
                    "Boost modéré searchable_text 10x",
                    "Activer tolérance typos",
                    "Recherche dans tous les champs",
                    "Retourner 10-20 résultats"
                ],
                "index_priority": ["products", "delivery", "support_paiement", "company", "location"]
            },
            "exploratory": {
                "description": "Requête exploratoire large",
                "recommended_actions": [
                    "Recherche large tous index",
                    "Boost léger searchable_text 8x",
                    "Tolérance typos activée",
                    "Retourner 20+ résultats"
                ],
                "index_priority": ["products", "company", "delivery", "support_paiement", "location"]
            },
            "generic": {
                "description": "Requête générique - recherche large",
                "recommended_actions": [
                    "Recherche full-text standard",
                    "Pas de boost spécial",
                    "Maximum de résultats",
                    "Utiliser reranking"
                ],
                "index_priority": ["company", "products", "delivery", "support_paiement", "location"]
            }
        }
        
        return strategy_map.get(analysis["type"], strategy_map["generic"])

    async def get_index_routing_strategy(self, word_scores: Dict[str, int], analysis: Dict[str, Any]) -> List[str]:
        """
        Détermine quels index prioriser selon les mots de la requête
        """
        # Mots-clés par index
        index_keywords = {
            "products": ["produit", "prix", "stock", "couleur", "taille", "modèle", "marque", "casque", "moto", "riz", "huile", "bananes"],
            "delivery": ["livraison", "zone", "délai", "transport", "yopougon", "abidjan", "cocody"],
            "support_paiement": ["paiement", "support", "aide", "contact", "orange", "wave", "mobile"],
            "company": ["entreprise", "mission", "secteur", "bio", "saveurs", "afrique"],
            "location": ["adresse", "localisation", "boutique", "magasin"]
        }
        
        # Calculer les scores par index
        index_scores = {}
        for index_name, keywords in index_keywords.items():
            score = 0
            matches = 0
            for keyword in keywords:
                if keyword in word_scores:
                    score += word_scores[keyword]
                    matches += 1
            
            # Score moyen pondéré par le nombre de matches
            if matches > 0:
                index_scores[index_name] = (score / matches) * (1 + matches * 0.1)
            else:
                index_scores[index_name] = 0
        
        # Trier par score décroissant
        sorted_indexes = sorted(index_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Retourner les index avec score > 0, sinon tous
        relevant_indexes = [idx for idx, score in sorted_indexes if score > 0]
        
        return relevant_indexes if relevant_indexes else list(index_keywords.keys())


# Fonction utilitaire pour intégration facile
async def optimize_search_query(query: str, company_id: str, sector: str = None) -> Dict[str, Any]:
    """
    Fonction utilitaire pour optimiser une requête de recherche
    """
    optimizer = HydeSearchOptimizer()
    return await optimizer.optimize_query(query, company_id, sector)


# Test rapide
if __name__ == "__main__":
    async def test_optimization():
        optimizer = HydeSearchOptimizer()
        
        # Test avec requête agro-alimentaire
        result = await optimizer.optimize_query(
            "riz parfumé 5kg livraison abidjan prix", 
            "AGR123456789", 
            "agro-alimentaire"
        )
        
        print("🎯 OPTIMISATION DE REQUÊTE")
        print("=" * 50)
        print(f"Requête originale: {result['original_query']}")
        print(f"Requête optimisée: {result['optimized_query']}")
        print(f"Type d'analyse: {result['analysis']['type']}")
        print(f"Confiance: {result['analysis']['confidence']:.1%}")
        print(f"Stratégie: {result['optimization_strategy']['description']}")
        
        print("\n📊 DISTRIBUTION DES SCORES:")
        for score_range, count in result['analysis']['score_distribution'].items():
            print(f"  {score_range}: {count} mots")
        
        print("\n🚀 ACTIONS RECOMMANDÉES:")
        for action in result['optimization_strategy']['recommended_actions']:
            print(f"  • {action}")
    
    asyncio.run(test_optimization())
