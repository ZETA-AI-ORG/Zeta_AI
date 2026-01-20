#!/usr/bin/env python3
"""
🎯 OPTIMISEUR MEILISEARCH ADAPTATIF AVEC APPRENTISSAGE AUTOMATIQUE
Filtrage intelligent et auto-optimisation des requêtes basée sur les patterns
"""

import asyncio
import time
import json
import re
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
from enum import Enum
import numpy as np

from core.intelligent_cache_system import smart_cache_get, smart_cache_set
from core.business_config_manager import get_business_config
from utils import log3


class QueryComplexity(Enum):
    """Niveaux de complexité des requêtes"""
    SIMPLE = "simple"           # Mots-clés directs
    MODERATE = "moderate"       # Multi-mots avec contexte
    COMPLEX = "complex"         # Multi-intentions, verbeux
    EXTREME = "extreme"         # Syntaxe brisée, surcharge


@dataclass
class QueryPattern:
    """Pattern de requête avec métriques d'optimisation"""
    original_query: str
    optimized_query: str
    complexity: QueryComplexity
    success_rate: float
    avg_results: float
    avg_response_time_ms: float
    usage_count: int
    last_used: float
    optimization_rules: List[str]


@dataclass
class FilteringStrategy:
    """Stratégie de filtrage adaptative"""
    stop_words_removal: bool
    synonym_expansion: bool
    fuzzy_matching: bool
    phonetic_matching: bool
    semantic_clustering: bool
    context_boosting: bool
    weights: Dict[str, float]


class AdaptiveMeiliOptimizer:
    """
    🧠 OPTIMISEUR MEILISEARCH AVEC APPRENTISSAGE DYNAMIQUE
    
    Features:
    - Analyse automatique des patterns de requêtes
    - Optimisation adaptative basée sur les résultats
    - Filtrage intelligent multi-niveaux
    - Expansion de synonymes contextuelle
    - Auto-ajustement des poids de recherche
    - Métriques de performance en temps réel
    """
    
    def __init__(self, company_id: str):
        self.company_id = company_id
        self.query_patterns: Dict[str, QueryPattern] = {}
        self.filtering_strategies: Dict[QueryComplexity, FilteringStrategy] = {}
        self.performance_history = defaultdict(list)
        self.business_config = None
        
        # Mots vides contextuels (universels)
        self.dynamic_stop_words = {
            'base': {'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'et', 'ou', 'mais', 'donc'},
            'hesitation': {'euh', 'bon', 'alors', 'hmmm', 'enfin', 'voilà', 'quoi'},
            'politesse': {'bonjour', 'bonsoir', 'salut', 'merci', 'svp', 's\'il vous plaît'},
            'filler': {'je veux dire', 'en fait', 'c\'est-à-dire', 'par exemple'}
        }
        
        # Initialisation par défaut des synonymes et mots-clés
        self.contextual_synonyms = {}
        self.domain_keywords = {'produit', 'service', 'prix', 'qualité', 'livraison', 'support'}
        
        # Initialisation des stratégies par défaut
        self._initialize_filtering_strategies()
        
        # Initialisation asynchrone
        asyncio.create_task(self._initialize_async())
    
    async def _initialize_async(self):
        """Initialisation asynchrone avec gestion robuste des erreurs"""
        try:
            # Chargement de la configuration métier
            self.business_config = await get_business_config(self.company_id)
            
            if self.business_config and hasattr(self.business_config, 'keywords'):
                keywords = self.business_config.keywords
                # Gestion sécurisée des attributs keywords
                if hasattr(keywords, 'products'):
                    self.domain_keywords.update(keywords.products)
                elif isinstance(keywords, dict) and 'products' in keywords:
                    self.domain_keywords.update(keywords['products'])
                    
                if hasattr(keywords, 'services'):
                    self.domain_keywords.update(keywords.services)
                elif isinstance(keywords, dict) and 'services' in keywords:
                    self.domain_keywords.update(keywords['services'])
                    
                if hasattr(keywords, 'delivery'):
                    self.domain_keywords.update(keywords.delivery)
                elif isinstance(keywords, dict) and 'delivery' in keywords:
                    self.domain_keywords.update(keywords['delivery'])
            
            # Chargement des patterns appris
            await self._load_learned_patterns()
            
            # Log sectoriel avec fallback sécurisé
            sector_value = "unknown"
            if self.business_config and hasattr(self.business_config, 'sector'):
                if hasattr(self.business_config.sector, 'value'):
                    sector_value = self.business_config.sector.value
                else:
                    sector_value = str(self.business_config.sector)
            
            log3("[MEILI_OPTIMIZER]", {
                "company_id": self.company_id,
                "sector": sector_value,
                "synonyms_domains": len(self.contextual_synonyms),
                "initialization": "success"
            })
            
        except Exception as e:
            log3("[MEILI_OPTIMIZER]", f"❌ Erreur initialisation: {e}")
            # Fallback avec mots-clés génériques
            self.domain_keywords = {'produit', 'service', 'prix', 'qualité', 'livraison', 'support'}
    
    def _initialize_filtering_strategies(self):
        """Initialise les stratégies de filtrage par complexité"""
        
        self.filtering_strategies = {
            QueryComplexity.SIMPLE: FilteringStrategy(
                stop_words_removal=False,  # Garder tous les mots pour requêtes simples
                synonym_expansion=True,
                fuzzy_matching=False,
                phonetic_matching=False,
                semantic_clustering=False,
                context_boosting=True,
                weights={'exact_match': 2.0, 'partial_match': 1.0, 'fuzzy_match': 0.5}
            ),
            
            QueryComplexity.MODERATE: FilteringStrategy(
                stop_words_removal=True,
                synonym_expansion=True,
                fuzzy_matching=True,
                phonetic_matching=False,
                semantic_clustering=True,
                context_boosting=True,
                weights={'exact_match': 1.8, 'partial_match': 1.2, 'fuzzy_match': 0.8}
            ),
            
            QueryComplexity.COMPLEX: FilteringStrategy(
                stop_words_removal=True,
                synonym_expansion=True,
                fuzzy_matching=True,
                phonetic_matching=True,
                semantic_clustering=True,
                context_boosting=True,
                weights={'exact_match': 1.5, 'partial_match': 1.3, 'fuzzy_match': 1.0}
            ),
            
            QueryComplexity.EXTREME: FilteringStrategy(
                stop_words_removal=True,
                synonym_expansion=True,
                fuzzy_matching=True,
                phonetic_matching=True,
                semantic_clustering=True,
                context_boosting=False,  # Éviter le bruit
                weights={'exact_match': 1.2, 'partial_match': 1.1, 'fuzzy_match': 1.0}
            )
        }
    
    async def optimize_query(self, original_query: str, intention_context: Optional[Dict] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Optimisation intelligente d'une requête avec apprentissage
        """
        start_time = time.time()
        
        # Détection de la complexité
        complexity = self._analyze_query_complexity(original_query)
        
        # Cache check pour patterns connus
        cache_key = f"meili_optimization:{hash(original_query)}:{complexity.value}"
        cached_result = await smart_cache_get(cache_key, self.company_id)
        if cached_result:
            return cached_result['optimized_query'], cached_result['metadata']
        
        # Stratégie de filtrage adaptée
        strategy = self.filtering_strategies[complexity]
        
        # Pipeline d'optimisation
        optimized_query = original_query.lower().strip()
        optimization_steps = []
        
        # 1. Nettoyage des mots vides selon la complexité
        if strategy.stop_words_removal:
            optimized_query, removed_words = self._remove_dynamic_stop_words(optimized_query, complexity)
            if removed_words:
                optimization_steps.append(f"Suppression mots vides: {removed_words}")
        
        # 2. Normalisation et nettoyage
        optimized_query = self._normalize_query(optimized_query)
        optimization_steps.append("Normalisation syntaxique")
        
        # 3. Expansion de synonymes contextuelle
        if strategy.synonym_expansion and intention_context:
            optimized_query = self._expand_contextual_synonyms(optimized_query, intention_context)
            optimization_steps.append("Expansion synonymes contextuels")
        
        # 4. Clustering sémantique pour requêtes complexes
        if strategy.semantic_clustering and complexity in [QueryComplexity.COMPLEX, QueryComplexity.EXTREME]:
            optimized_query = self._apply_semantic_clustering(optimized_query)
            optimization_steps.append("Clustering sémantique")
        
        # 5. Boost contextuel selon l'intention
        boost_terms = []
        if strategy.context_boosting and intention_context:
            boost_terms = self._generate_context_boosts(intention_context)
        
        # Métadonnées d'optimisation
        metadata = {
            'original_query': original_query,
            'complexity': complexity.value,
            'optimization_steps': optimization_steps,
            'strategy_used': asdict(strategy),
            'boost_terms': boost_terms,
            'processing_time_ms': (time.time() - start_time) * 1000
        }
        
        # Apprentissage et cache
        await self._learn_from_optimization(original_query, optimized_query, complexity, metadata)
        await smart_cache_set(cache_key, {
            'optimized_query': optimized_query,
            'metadata': metadata
        }, self.company_id, ttl_seconds=3600)
        
        log3("[MEILI_OPTIMIZER]", {
            "original": original_query[:50],
            "optimized": optimized_query[:50],
            "complexity": complexity.value,
            "steps": len(optimization_steps),
            "processing_ms": round(metadata['processing_time_ms'], 2)
        })
        
        return optimized_query, metadata
    
    def _analyze_query_complexity(self, query: str) -> QueryComplexity:
        """Analyse automatique de la complexité d'une requête"""
        
        words = query.lower().split()
        word_count = len(words)
        
        # Indicateurs de complexité
        hesitation_words = sum(1 for word in words if word in self.dynamic_stop_words['hesitation'])
        punctuation_density = len(re.findall(r'[?!.;,]', query)) / max(1, len(query))
        repeated_words = len(words) - len(set(words))
        
        # Détection syntaxe brisée
        has_broken_syntax = bool(re.search(r'\b\w+\s*\?\s*\w+', query))
        
        # Détection verbosité excessive
        is_verbose = word_count > 30 and any(phrase in query.lower() for phrase in [
            'j\'aimerais savoir', 'je voudrais', 'est-ce que', 'ça dépend'
        ])
        
        # Détection multi-intentions
        intention_markers = ['mais aussi', 'et en plus', 'et combien', 'et qui']
        has_multi_intentions = any(marker in query.lower() for marker in intention_markers)
        
        # Classification
        if has_broken_syntax or word_count <= 5:
            return QueryComplexity.EXTREME
        elif is_verbose or hesitation_words > 2:
            return QueryComplexity.COMPLEX
        elif has_multi_intentions or word_count > 15:
            return QueryComplexity.MODERATE
        else:
            return QueryComplexity.SIMPLE
    
    def _remove_dynamic_stop_words(self, query: str, complexity: QueryComplexity) -> Tuple[str, List[str]]:
        """Suppression intelligente des mots vides selon le contexte"""
        
        words = query.split()
        removed_words = []
        
        # Sélection des catégories de mots vides selon la complexité
        categories_to_remove = ['base']
        
        if complexity in [QueryComplexity.COMPLEX, QueryComplexity.EXTREME]:
            categories_to_remove.extend(['hesitation', 'filler'])
        
        if complexity == QueryComplexity.EXTREME:
            categories_to_remove.append('politesse')
        
        # Suppression avec préservation du sens
        filtered_words = []
        for word in words:
            should_remove = False
            for category in categories_to_remove:
                if word in self.dynamic_stop_words[category]:
                    should_remove = True
                    removed_words.append(word)
                    break
            
            if not should_remove:
                filtered_words.append(word)
        
        # Garantir qu'il reste au moins 1 mot significatif
        if not filtered_words and words:
            filtered_words = [words[-1]]  # Garder le dernier mot
        
        return ' '.join(filtered_words), removed_words
    
    def _normalize_query(self, query: str) -> str:
        """Normalisation syntaxique avancée"""
        
        # Suppression des caractères répétés
        query = re.sub(r'(.)\1{2,}', r'\1', query)
        
        # Nettoyage de la ponctuation excessive
        query = re.sub(r'[?!]{2,}', '?', query)
        query = re.sub(r'\.{2,}', '.', query)
        
        # Suppression des espaces multiples
        query = re.sub(r'\s+', ' ', query)
        
        # Correction des apostrophes
        query = query.replace("'", "'")
        
        return query.strip()
    
    def _generate_contextual_synonyms(self) -> Dict[str, Dict[str, List[str]]]:
        """Génération des synonymes contextuels depuis la configuration métier"""
        
        if not self.business_config:
            return {}
        
        # Utilisation des synonymes de la configuration métier
        business_synonyms = self.business_config.synonyms
        
        # Organisation par intention (mapping générique)
        contextual_synonyms = {
            'product_catalog': business_synonyms,
            'delivery': business_synonyms,
            'payment': business_synonyms,
            'support': business_synonyms
        }
        
        return contextual_synonyms
    
    def _expand_contextual_synonyms(self, query: str, intention_context: Dict) -> str:
        """Expansion de synonymes basée sur le contexte d'intention"""
        
        primary_intention = intention_context.get('primary')
        if not primary_intention or not self.contextual_synonyms:
            return query
        
        # Sélection du domaine de synonymes
        domain_synonyms = self.contextual_synonyms.get(primary_intention, {})
        
        words = query.split()
        expanded_words = []
        
        for word in words:
            expanded_words.append(word)
            
            # Recherche de synonymes
            for base_word, synonyms in domain_synonyms.items():
                if word == base_word or word in synonyms:
                    # Ajout du terme de base si pas déjà présent
                    if base_word not in expanded_words:
                        expanded_words.append(base_word)
                    break
        
        return ' '.join(expanded_words)
    
    def _apply_semantic_clustering(self, query: str) -> str:
        """Clustering sémantique pour requêtes complexes basé sur la config métier"""
        
        if not self.business_config:
            return query
        
        words = query.split()
        keywords = self.business_config.keywords
        
        # Groupement par domaines sémantiques dynamiques
        clusters = {
            'product': [],
            'action': [],
            'location': [],
            'attribute': []
        }
        
        # Classification basée sur la configuration métier (accès sécurisé)
        for word in words:
            if hasattr(keywords, 'products') and word in keywords.products:
                clusters['product'].append(word)
            elif isinstance(keywords, dict) and word in keywords.get('products', []):
                clusters['product'].append(word)
            elif hasattr(keywords, 'actions') and word in keywords.actions:
                clusters['action'].append(word)
            elif isinstance(keywords, dict) and word in keywords.get('actions', []):
                clusters['action'].append(word)
            elif hasattr(keywords, 'locations') and word in keywords.locations:
                clusters['location'].append(word)
            elif isinstance(keywords, dict) and word in keywords.get('locations', []):
                clusters['location'].append(word)
            elif hasattr(keywords, 'attributes') and word in keywords.attributes:
                clusters['attribute'].append(word)
            elif isinstance(keywords, dict) and word in keywords.get('attributes', []):
                clusters['attribute'].append(word)
        
        # Reconstruction optimisée
        optimized_parts = []
        for cluster_type, cluster_words in clusters.items():
            if cluster_words:
                optimized_parts.extend(cluster_words)
        
        # Ajout des mots non classifiés
        unclustered = [w for w in words if not any(w in cluster for cluster in clusters.values())]
        optimized_parts.extend(unclustered)
        
        return ' '.join(optimized_parts) if optimized_parts else query
    
    def _generate_context_boosts(self, intention_context: Dict) -> List[str]:
        """Génération de termes de boost selon le contexte métier"""
        
        if not self.business_config:
            return []
        
        boosts = []
        primary_intention = intention_context.get('primary')
        keywords = self.business_config.keywords
        
        # Boost adaptatif selon l'intention et la configuration métier (accès sécurisé)
        if primary_intention == 'product_catalog':
            if hasattr(keywords, 'products'):
                boosts.extend(list(keywords.products)[:5])  # Top 5 produits
            elif isinstance(keywords, dict):
                boosts.extend(list(keywords.get('products', []))[:5])
            
            if hasattr(keywords, 'attributes'):
                boosts.extend(list(keywords.attributes)[:3])  # Top 3 attributs
            elif isinstance(keywords, dict):
                boosts.extend(list(keywords.get('attributes', []))[:3])
                
        elif primary_intention == 'delivery':
            if hasattr(keywords, 'services'):
                boosts.extend(list(keywords.services)[:3])
            elif isinstance(keywords, dict):
                boosts.extend(list(keywords.get('services', []))[:3])
            if hasattr(keywords, 'locations'):
                boosts.extend(list(keywords.locations)[:3])
            elif isinstance(keywords, dict):
                boosts.extend(list(keywords.get('locations', []))[:3])
                
        elif primary_intention == 'support':
            if hasattr(keywords, 'services'):
                boosts.extend(list(keywords.services)[:5])
            elif isinstance(keywords, dict):
                boosts.extend(list(keywords.get('services', []))[:5])
                
        elif primary_intention == 'payment':
            services = keywords.services if hasattr(keywords, 'services') else keywords.get('services', [])
            boosts.extend([kw for kw in services if 'paiement' in kw or 'pay' in kw])
        
        return boosts
    
    async def _learn_from_optimization(self, original: str, optimized: str, 
                                     complexity: QueryComplexity, metadata: Dict):
        """Apprentissage depuis les optimisations"""
        
        pattern_key = f"{complexity.value}:{hash(original)}"
        
        if pattern_key in self.query_patterns:
            pattern = self.query_patterns[pattern_key]
            pattern.usage_count += 1
            pattern.last_used = time.time()
        else:
            self.query_patterns[pattern_key] = QueryPattern(
                original_query=original,
                optimized_query=optimized,
                complexity=complexity,
                success_rate=1.0,  # Sera mis à jour avec les résultats
                avg_results=0.0,
                avg_response_time_ms=metadata['processing_time_ms'],
                usage_count=1,
                last_used=time.time(),
                optimization_rules=metadata['optimization_steps']
            )
    
    async def update_pattern_performance(self, original_query: str, 
                                       results_count: int, response_time_ms: float):
        """Mise à jour des performances d'un pattern"""
        
        complexity = self._analyze_query_complexity(original_query)
        pattern_key = f"{complexity.value}:{hash(original_query)}"
        
        if pattern_key in self.query_patterns:
            pattern = self.query_patterns[pattern_key]
            
            # Mise à jour des métriques (moyenne mobile)
            alpha = 0.1  # Facteur de lissage
            pattern.avg_results = (1 - alpha) * pattern.avg_results + alpha * results_count
            pattern.avg_response_time_ms = (1 - alpha) * pattern.avg_response_time_ms + alpha * response_time_ms
            
            # Calcul du taux de succès
            pattern.success_rate = min(1.0, pattern.avg_results / 5.0)  # 5 résultats = succès parfait
    
    async def get_optimization_metrics(self) -> Dict[str, Any]:
        """Métriques d'optimisation pour monitoring"""
        
        if not self.query_patterns:
            return {}
        
        patterns_by_complexity = defaultdict(list)
        for pattern in self.query_patterns.values():
            patterns_by_complexity[pattern.complexity.value].append(pattern)
        
        metrics = {}
        for complexity, patterns in patterns_by_complexity.items():
            if patterns:
                avg_success_rate = np.mean([p.success_rate for p in patterns])
                avg_results = np.mean([p.avg_results for p in patterns])
                avg_response_time = np.mean([p.avg_response_time_ms for p in patterns])
                
                metrics[complexity] = {
                    'pattern_count': len(patterns),
                    'avg_success_rate': round(avg_success_rate, 3),
                    'avg_results': round(avg_results, 2),
                    'avg_response_time_ms': round(avg_response_time, 2)
                }
        
        return metrics
    
    async def _load_learned_patterns(self):
        """Chargement des patterns appris depuis le cache"""
        
        try:
            cached_patterns = await smart_cache_get(f"meili_patterns:{self.company_id}", self.company_id)
            if cached_patterns:
                for pattern_data in cached_patterns:
                    pattern = QueryPattern(**pattern_data)
                    pattern_key = f"{pattern.complexity.value}:{hash(pattern.original_query)}"
                    self.query_patterns[pattern_key] = pattern
                
                log3("[MEILI_OPTIMIZER]", f"✅ {len(self.query_patterns)} patterns chargés")
        except Exception as e:
            log3("[MEILI_OPTIMIZER]", f"⚠️ Erreur chargement patterns: {e}")
    
    async def save_learned_patterns(self):
        """Sauvegarde des patterns appris"""
        
        try:
            patterns_data = [asdict(pattern) for pattern in self.query_patterns.values()]
            await smart_cache_set(
                f"meili_patterns:{self.company_id}",
                patterns_data,
                self.company_id,
                ttl_seconds=86400 * 7  # 7 jours
            )
            log3("[MEILI_OPTIMIZER]", "💾 Patterns sauvegardés")
        except Exception as e:
            log3("[MEILI_OPTIMIZER]", f"❌ Erreur sauvegarde: {e}")


# Factory pattern
_optimizers: Dict[str, AdaptiveMeiliOptimizer] = {}

def get_meili_optimizer(company_id: str) -> AdaptiveMeiliOptimizer:
    """Factory pour obtenir l'optimiseur MeiliSearch"""
    if company_id not in _optimizers:
        _optimizers[company_id] = AdaptiveMeiliOptimizer(company_id)
    return _optimizers[company_id]


# API principale
async def optimize_meili_query(query: str, company_id: str, 
                              intention_context: Optional[Dict] = None) -> Tuple[str, Dict]:
    """API principale - Optimisation intelligente des requêtes MeiliSearch"""
    optimizer = get_meili_optimizer(company_id)
    return await optimizer.optimize_query(query, intention_context)
