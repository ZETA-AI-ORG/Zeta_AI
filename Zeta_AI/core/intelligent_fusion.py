#!/usr/bin/env python3
"""
🔀 FUSION INTELLIGENTE MULTI-SOURCES
Combine et optimise les résultats de MeiliSearch, recherche sémantique, et fuzzy matching
"""

import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

class FusionStrategy(Enum):
    """Stratégies de fusion disponibles"""
    WEIGHTED_AVERAGE = "weighted_average"
    RANK_FUSION = "rank_fusion"
    SCORE_NORMALIZATION = "score_normalization"
    HYBRID_BOOST = "hybrid_boost"

@dataclass
class FusionConfig:
    """Configuration de fusion"""
    strategy: FusionStrategy = FusionStrategy.HYBRID_BOOST
    meili_weight: float = 0.4
    semantic_weight: float = 0.4
    fuzzy_weight: float = 0.2
    min_final_score: float = 0.3
    max_results: int = 10
    diversity_threshold: float = 0.8  # Seuil de similarité pour diversité
    boost_exact_matches: bool = True
    boost_multi_source: bool = True

@dataclass
class FusedResult:
    """Résultat fusionné avec métadonnées"""
    id: str
    content: str
    metadata: Dict[str, Any]
    final_score: float
    source_scores: Dict[str, float]  # Scores par source
    sources: List[str]  # Sources qui ont trouvé ce résultat
    fusion_metadata: Dict[str, Any]  # Métadonnées de fusion

class IntelligentFusionEngine:
    """
    🔀 MOTEUR DE FUSION INTELLIGENTE
    
    Fonctionnalités :
    - Fusion pondérée de multiples sources de recherche
    - Normalisation et calibration des scores
    - Déduplication intelligente avec diversité
    - Boost pour correspondances exactes et multi-sources
    - Métriques de qualité de fusion
    """
    
    def __init__(self, config: Optional[FusionConfig] = None):
        self.config = config or FusionConfig()
        
        # Patterns pour détection de correspondances exactes
        self.exact_match_patterns = [
            r'\b(?:taille|size)\s*(\d+)\b',
            r'\b(\d+)\s*(?:paquets?|lots?)\b',
            r'\b(?:culottes?|pression)\b',
            r'\b(?:livraison|delivery)\b',
            r'\b(?:prix|price|tarif)\b',
            r'\b(?:disponible|available|stock)\b'
        ]
    
    def normalize_scores(self, results: List[Dict[str, Any]], source: str) -> List[Dict[str, Any]]:
        """Normalise les scores d'une source spécifique"""
        if not results:
            return []
        
        # Extraction des scores
        scores = [r.get('score', 0) for r in results]
        if not scores:
            return results
        
        min_score = min(scores)
        max_score = max(scores)
        score_range = max_score - min_score
        
        # Normalisation min-max si range > 0
        normalized_results = []
        for result in results:
            original_score = result.get('score', 0)
            
            if score_range > 0:
                normalized_score = (original_score - min_score) / score_range
            else:
                normalized_score = 1.0 if original_score > 0 else 0.0
            
            # Ajustement par source
            if source == 'meilisearch':
                # MeiliSearch tend à avoir des scores plus élevés
                normalized_score *= 0.9
            elif source == 'semantic':
                # Recherche sémantique plus conservative
                normalized_score *= 1.1
            elif source == 'fuzzy':
                # Fuzzy matching peut être bruité
                normalized_score *= 0.8
            
            result_copy = result.copy()
            result_copy['normalized_score'] = normalized_score
            result_copy['original_score'] = original_score
            result_copy['source'] = source
            normalized_results.append(result_copy)
        
        logger.info(f"🔢 [NORMALIZE] {source}: {len(results)} résultats normalisés (range: {score_range:.3f})")
        return normalized_results
    
    def calculate_content_similarity(self, content1: str, content2: str) -> float:
        """Calcule la similarité entre deux contenus"""
        if not content1 or not content2:
            return 0.0
        
        # Utilisation de RapidFuzz pour la similarité
        similarity = fuzz.ratio(content1.lower(), content2.lower()) / 100.0
        return similarity
    
    def deduplicate_with_diversity(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Déduplication intelligente avec préservation de la diversité"""
        if not results:
            return []
        
        unique_results = []
        seen_contents = []
        
        # Trier par score décroissant
        sorted_results = sorted(results, key=lambda x: x.get('normalized_score', 0), reverse=True)
        
        for result in sorted_results:
            content = result.get('content', '')
            is_duplicate = False
            
            # Vérifier la similarité avec les contenus déjà vus
            for seen_content in seen_contents:
                similarity = self.calculate_content_similarity(content, seen_content)
                if similarity > self.config.diversity_threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_results.append(result)
                seen_contents.append(content)
        
        logger.info(f"🎯 [DEDUP] {len(results)} → {len(unique_results)} résultats après déduplication (seuil: {self.config.diversity_threshold})")
        return unique_results
    
    def detect_exact_matches(self, query: str, content: str) -> Dict[str, Any]:
        """Détecte les correspondances exactes dans le contenu"""
        import re
        
        exact_matches = []
        query_lower = query.lower()
        content_lower = content.lower()
        
        # Correspondance directe de mots-clés
        query_words = set(query_lower.split())
        content_words = set(content_lower.split())
        word_overlap = len(query_words.intersection(content_words))
        word_coverage = word_overlap / len(query_words) if query_words else 0
        
        # Correspondance de patterns spécifiques
        pattern_matches = 0
        for pattern in self.exact_match_patterns:
            if re.search(pattern, query_lower) and re.search(pattern, content_lower):
                pattern_matches += 1
        
        # Correspondance de phrases
        phrase_match = fuzz.partial_ratio(query_lower, content_lower) / 100.0
        
        return {
            'word_overlap': word_overlap,
            'word_coverage': word_coverage,
            'pattern_matches': pattern_matches,
            'phrase_match': phrase_match,
            'has_exact_match': word_coverage > 0.5 or pattern_matches > 0 or phrase_match > 0.8
        }
    
    def calculate_fusion_score(self, result: Dict[str, Any], query: str, source_weights: Dict[str, float]) -> float:
        """Calcule le score de fusion final"""
        base_score = result.get('normalized_score', 0)
        source = result.get('source', 'unknown')
        content = result.get('content', '')
        
        # Score pondéré par source
        source_weight = source_weights.get(source, 0.3)
        weighted_score = base_score * source_weight
        
        # Boost pour correspondances exactes
        if self.config.boost_exact_matches:
            exact_match_info = self.detect_exact_matches(query, content)
            if exact_match_info['has_exact_match']:
                exact_boost = 0.2 * (
                    exact_match_info['word_coverage'] * 0.4 +
                    min(exact_match_info['pattern_matches'] * 0.1, 0.3) +
                    exact_match_info['phrase_match'] * 0.3
                )
                weighted_score += exact_boost
        
        # Boost pour longueur de contenu appropriée
        content_length = len(content)
        if 50 <= content_length <= 500:  # Longueur optimale
            weighted_score += 0.05
        elif content_length > 500:  # Contenu très détaillé
            weighted_score += 0.1
        
        return min(weighted_score, 1.0)
    
    def fuse_results(
        self, 
        meili_results: List[Dict[str, Any]], 
        semantic_results: List[Dict[str, Any]], 
        fuzzy_results: List[Dict[str, Any]], 
        query: str
    ) -> List[FusedResult]:
        """
        🔀 FUSION PRINCIPALE DES RÉSULTATS
        
        Combine intelligemment les résultats de toutes les sources
        """
        logger.info(f"🔀 [FUSION] Début fusion: MeiliSearch={len(meili_results)}, Sémantique={len(semantic_results)}, Fuzzy={len(fuzzy_results)}")
        
        start_time = time.time()
        
        # 1. Normalisation des scores par source
        normalized_meili = self.normalize_scores(meili_results, 'meilisearch')
        normalized_semantic = self.normalize_scores(semantic_results, 'semantic')
        normalized_fuzzy = self.normalize_scores(fuzzy_results, 'fuzzy')
        
        # 2. Combinaison de tous les résultats
        all_results = normalized_meili + normalized_semantic + normalized_fuzzy
        
        # 3. Déduplication avec diversité
        unique_results = self.deduplicate_with_diversity(all_results)
        
        # 4. Calcul des scores de fusion
        source_weights = {
            'meilisearch': self.config.meili_weight,
            'semantic': self.config.semantic_weight,
            'fuzzy': self.config.fuzzy_weight
        }
        
        fused_results = []
        for result in unique_results:
            fusion_score = self.calculate_fusion_score(result, query, source_weights)
            
            # Filtrage par score minimum
            if fusion_score >= self.config.min_final_score:
                # Collecte des métadonnées de fusion
                exact_match_info = self.detect_exact_matches(query, result.get('content', ''))
                
                fused_result = FusedResult(
                    id=result.get('id', ''),
                    content=result.get('content', ''),
                    metadata=result.get('metadata', {}),
                    final_score=fusion_score,
                    source_scores={
                        result.get('source', 'unknown'): result.get('normalized_score', 0)
                    },
                    sources=[result.get('source', 'unknown')],
                    fusion_metadata={
                        'original_score': result.get('original_score', 0),
                        'normalized_score': result.get('normalized_score', 0),
                        'exact_match_info': exact_match_info,
                        'source_weight': source_weights.get(result.get('source', 'unknown'), 0.3)
                    }
                )
                fused_results.append(fused_result)
        
        # 5. Tri final par score de fusion
        fused_results.sort(key=lambda x: x.final_score, reverse=True)
        
        # 6. Limitation du nombre de résultats
        final_results = fused_results[:self.config.max_results]
        
        # Métriques de fusion
        fusion_time = time.time() - start_time
        logger.info(f"🔀 [FUSION] Terminé en {fusion_time*1000:.2f}ms: {len(all_results)} → {len(unique_results)} → {len(final_results)} résultats")
        
        # Logs détaillés des meilleurs résultats
        for i, result in enumerate(final_results[:3], 1):
            logger.info(f"🏆 [TOP{i}] Score: {result.final_score:.3f} | Source: {result.sources[0]} | Contenu: '{result.content[:50]}...'")
        
        return final_results
    
    def merge_multi_source_results(self, results: List[FusedResult]) -> List[FusedResult]:
        """Fusionne les résultats trouvés par plusieurs sources"""
        if not self.config.boost_multi_source:
            return results
        
        # Grouper par contenu similaire
        content_groups = {}
        for result in results:
            content_key = result.content[:100].lower().strip()  # Clé basée sur le début du contenu
            
            if content_key not in content_groups:
                content_groups[content_key] = []
            content_groups[content_key].append(result)
        
        # Fusionner les groupes multi-sources
        merged_results = []
        for content_key, group in content_groups.items():
            if len(group) == 1:
                # Résultat d'une seule source
                merged_results.append(group[0])
            else:
                # Résultat multi-sources - fusion
                best_result = max(group, key=lambda x: x.final_score)
                
                # Collecte des sources et scores
                all_sources = []
                all_source_scores = {}
                for r in group:
                    all_sources.extend(r.sources)
                    all_source_scores.update(r.source_scores)
                
                # Boost multi-source
                multi_source_boost = 0.15 * (len(set(all_sources)) - 1)
                boosted_score = min(best_result.final_score + multi_source_boost, 1.0)
                
                # Création du résultat fusionné
                merged_result = FusedResult(
                    id=best_result.id,
                    content=best_result.content,
                    metadata=best_result.metadata,
                    final_score=boosted_score,
                    source_scores=all_source_scores,
                    sources=list(set(all_sources)),
                    fusion_metadata={
                        **best_result.fusion_metadata,
                        'multi_source_boost': multi_source_boost,
                        'source_count': len(set(all_sources))
                    }
                )
                merged_results.append(merged_result)
        
        # Tri final
        merged_results.sort(key=lambda x: x.final_score, reverse=True)
        
        logger.info(f"🔗 [MULTI_SOURCE] {len(results)} → {len(merged_results)} après fusion multi-sources")
        return merged_results
    
    def format_fused_context(self, results: List[FusedResult], max_length: int = 4000) -> str:
        """Formate le contexte fusionné pour le LLM"""
        if not results:
            return ""
        
        context_parts = []
        current_length = 0
        
        for i, result in enumerate(results, 1):
            # En-tête avec métadonnées de fusion
            sources_str = " + ".join(result.sources)
            header = f"=== DOCUMENT FUSIONNÉ #{i} ===\n"
            header += f"Score final: {result.final_score:.3f} | Sources: {sources_str}\n"
            
            # Métadonnées si multi-source
            if len(result.sources) > 1:
                header += f"🔗 Multi-source (boost: +{result.fusion_metadata.get('multi_source_boost', 0):.2f})\n"
            
            # Correspondances exactes
            exact_info = result.fusion_metadata.get('exact_match_info', {})
            if exact_info.get('has_exact_match'):
                header += f"🎯 Correspondance exacte (couverture: {exact_info.get('word_coverage', 0):.1%})\n"
            
            header += f"Contenu:\n{result.content}\n\n"
            
            # Vérification de la longueur
            if current_length + len(header) > max_length:
                logger.info(f"📏 [CONTEXT] Limite atteinte ({max_length} chars) à {i-1} documents")
                break
            
            context_parts.append(header)
            current_length += len(header)
        
        formatted_context = "".join(context_parts)
        logger.info(f"📄 [CONTEXT] Contexte fusionné: {len(formatted_context)} chars, {len(context_parts)} documents")
        
        return formatted_context

# Instance globale
intelligent_fusion = IntelligentFusionEngine()

# Interface simple
def fuse_search_results(
    meili_results: List[Dict[str, Any]], 
    semantic_results: List[Dict[str, Any]], 
    fuzzy_results: List[Dict[str, Any]], 
    query: str,
    config: Optional[FusionConfig] = None
) -> Tuple[List[FusedResult], str]:
    """
    🔀 Interface simple pour fusion de résultats
    
    Returns:
        Tuple[List[FusedResult], str]: (résultats_fusionnés, contexte_formaté)
    """
    if config:
        fusion_engine = IntelligentFusionEngine(config)
    else:
        fusion_engine = intelligent_fusion
    
    # Fusion principale
    fused_results = fusion_engine.fuse_results(meili_results, semantic_results, fuzzy_results, query)
    
    # Fusion multi-sources
    final_results = fusion_engine.merge_multi_source_results(fused_results)
    
    # Formatage contexte
    formatted_context = fusion_engine.format_fused_context(final_results)
    
    return final_results, formatted_context

if __name__ == "__main__":
    # Tests de fusion
    test_meili = [
        {"id": "1", "content": "Couches culottes taille 3 disponibles en stock", "score": 0.8},
        {"id": "2", "content": "Livraison gratuite pour commandes > 50000 FCFA", "score": 0.6}
    ]
    
    test_semantic = [
        {"id": "1", "content": "Couches culottes taille 3 disponibles en stock", "score": 0.9},
        {"id": "3", "content": "Prix des couches: 15000 FCFA le paquet", "score": 0.7}
    ]
    
    test_fuzzy = [
        {"id": "4", "content": "Couches à pression taille 2 et 3", "score": 0.5}
    ]
    
    query = "couches taille 3 prix livraison"
    
    results, context = fuse_search_results(test_meili, test_semantic, test_fuzzy, query)
    
    print(f"\n{'='*60}")
    print(f"FUSION TEST: {query}")
    print('='*60)
    print(f"Résultats fusionnés: {len(results)}")
    for r in results:
        print(f"- Score: {r.final_score:.3f} | Sources: {r.sources} | Contenu: {r.content[:50]}...")
    print(f"\nContexte: {len(context)} chars")
