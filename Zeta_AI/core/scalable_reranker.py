"""
🎯 SCALABLE RERANKER - CROSS-ENCODER MULTI-TENANT
Reranking intelligent avec cross-encoder pour précision maximale
"""
import asyncio
import hashlib
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass

from utils import log3
from .tenant_config_manager import get_tenant_config, SearchConfig
from .scalable_meilisearch_engine import MeiliSearchResult
from .scalable_supabase_engine import SemanticResult


@dataclass
class RerankResult:
    """Résultat après reranking"""
    id: str
    content: str
    original_score: float
    rerank_score: float
    final_score: float
    source: str  # "meilisearch" ou "supabase"
    metadata: Dict[str, Any]


class ScalableReranker:
    """
    🎯 RERANKER SCALABLE MULTI-TENANT
    
    Fonctionnalités:
    - Cross-encoder pour précision maximale
    - Configuration par tenant
    - Cache des scores de reranking
    - Fallback intelligent si modèle indisponible
    - Fusion des sources (MeiliSearch + Supabase)
    """
    
    def __init__(self):
        self.cross_encoder = None
        self.model_loaded = False
        
        # Cache des scores de reranking
        self._cache: Dict[str, float] = {}
        self._stats = {
            'total_rerank_calls': 0,
            'cache_hits': 0,
            'total_rerank_time_ms': 0,
            'model_load_time_ms': 0
        }
        
        log3("[RERANKER]", "✅ Reranker scalable initialisé")
    
    def _load_cross_encoder(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """Charge le modèle cross-encoder (lazy loading)"""
        if self.model_loaded:
            return
        
        start_time = time.time()
        
        try:
            from sentence_transformers import CrossEncoder
            self.cross_encoder = CrossEncoder(model_name)
            self.model_loaded = True
            
            load_time = (time.time() - start_time) * 1000
            self._stats['model_load_time_ms'] = load_time
            
            log3("[RERANKER]", f"✅ Cross-encoder chargé en {load_time:.1f}ms")
            
        except Exception as e:
            log3("[RERANKER]", f"⚠️ Erreur chargement cross-encoder: {e}")
            self.cross_encoder = None
            self.model_loaded = False
    
    def _compute_cache_key(self, query: str, content: str) -> str:
        """Calcule la clé de cache pour une paire query-document"""
        combined = f"{query[:100]}|{content[:200]}"  # Limiter pour éviter clés trop longues
        return hashlib.md5(combined.encode()).hexdigest()
    
    def _rerank_with_cross_encoder(self, query: str, documents: List[str]) -> List[float]:
        """Reranking avec cross-encoder"""
        if not self.model_loaded or self.cross_encoder is None:
            # Fallback: retourner scores uniformes
            return [0.5] * len(documents)
        
        try:
            # Préparer les paires (query, document)
            pairs = [(query, doc) for doc in documents]
            
            # Prédiction des scores
            scores = self.cross_encoder.predict(pairs)
            
            # Convertir en liste si numpy array
            if hasattr(scores, 'tolist'):
                scores = scores.tolist()
            
            return scores
            
        except Exception as e:
            log3("[RERANKER]", f"⚠️ Erreur cross-encoder: {e}")
            # Fallback: scores basés sur la longueur du contenu
            return [min(0.8, len(doc.split()) / 100) for doc in documents]
    
    def _combine_scores(
        self,
        original_score: float,
        rerank_score: float,
        combination_method: str = "weighted"
    ) -> float:
        """
        Combine les scores originaux et de reranking
        
        Methods:
        - weighted: 70% rerank + 30% original
        - multiplicative: original * rerank
        - additive: original + rerank
        """
        if combination_method == "weighted":
            return 0.7 * rerank_score + 0.3 * original_score
        elif combination_method == "multiplicative":
            return original_score * rerank_score
        elif combination_method == "additive":
            return original_score + rerank_score
        else:
            return rerank_score  # Par défaut, utiliser seulement le rerank
    
    async def rerank_results(
        self,
        query: str,
        meilisearch_results: List[MeiliSearchResult],
        supabase_results: List[SemanticResult],
        company_id: str,
        top_k: int = 10
    ) -> List[RerankResult]:
        """
        Reranking principal des résultats combinés
        
        Args:
            query: Requête originale
            meilisearch_results: Résultats MeiliSearch
            supabase_results: Résultats Supabase sémantiques
            company_id: ID de l'entreprise
            top_k: Nombre de résultats finaux
            
        Returns:
            Liste des résultats rerankés et triés
        """
        start_time = time.time()
        
        # 1. Récupérer la configuration du tenant
        config = get_tenant_config(company_id).search
        
        if not config.rerank_enabled:
            # Reranking désactivé, retourner fusion simple
            return self._simple_fusion(query, meilisearch_results, supabase_results, top_k)
        
        # 2. Charger le modèle si nécessaire
        self._load_cross_encoder(config.rerank_model)
        
        # 3. Préparer tous les documents pour reranking
        all_documents = []
        document_metadata = []
        
        # Ajouter résultats MeiliSearch
        for result in meilisearch_results:
            all_documents.append(result.content)
            document_metadata.append({
                'id': result.id,
                'original_score': result.score,
                'source': 'meilisearch',
                'metadata': result.metadata
            })
        
        # Ajouter résultats Supabase
        for result in supabase_results:
            all_documents.append(result.content)
            document_metadata.append({
                'id': result.id,
                'original_score': result.similarity_score,
                'source': 'supabase',
                'metadata': result.metadata
            })
        
        if not all_documents:
            return []
        
        # 4. Vérifier le cache pour éviter recalculs
        cached_scores = []
        documents_to_rerank = []
        cache_indices = []
        
        for i, doc in enumerate(all_documents):
            cache_key = self._compute_cache_key(query, doc)
            if cache_key in self._cache:
                cached_scores.append((i, self._cache[cache_key]))
                self._stats['cache_hits'] += 1
            else:
                documents_to_rerank.append(doc)
                cache_indices.append((i, cache_key))
        
        # 5. Reranking des documents non cachés
        if documents_to_rerank:
            new_scores = self._rerank_with_cross_encoder(query, documents_to_rerank)
            
            # Mettre en cache les nouveaux scores
            for (orig_idx, cache_key), score in zip(cache_indices, new_scores):
                self._cache[cache_key] = score
        else:
            new_scores = []
        
        # 6. Reconstituer tous les scores
        all_rerank_scores = [0.0] * len(all_documents)
        
        # Scores cachés
        for idx, score in cached_scores:
            all_rerank_scores[idx] = score
        
        # Nouveaux scores
        new_score_idx = 0
        for orig_idx, _ in cache_indices:
            all_rerank_scores[orig_idx] = new_scores[new_score_idx]
            new_score_idx += 1
        
        # 7. Créer les résultats finaux
        rerank_results = []
        for i, (doc, metadata) in enumerate(zip(all_documents, document_metadata)):
            original_score = metadata['original_score']
            rerank_score = all_rerank_scores[i]
            final_score = self._combine_scores(original_score, rerank_score)
            
            result = RerankResult(
                id=metadata['id'],
                content=doc,
                original_score=original_score,
                rerank_score=rerank_score,
                final_score=final_score,
                source=metadata['source'],
                metadata=metadata['metadata']
            )
            rerank_results.append(result)
        
        # 8. Tri par score final décroissant
        rerank_results.sort(key=lambda x: x.final_score, reverse=True)
        
        # 9. Limitation au top-K
        rerank_results = rerank_results[:top_k]
        
        # 10. Métriques
        total_time = (time.time() - start_time) * 1000
        self._stats['total_rerank_calls'] += 1
        self._stats['total_rerank_time_ms'] += total_time
        
        log3("[RERANKER]", f"✅ {len(rerank_results)} docs rerankés en {total_time:.1f}ms")
        
        return rerank_results
    
    def _simple_fusion(
        self,
        query: str,
        meilisearch_results: List[MeiliSearchResult],
        supabase_results: List[SemanticResult],
        top_k: int
    ) -> List[RerankResult]:
        """Fusion simple sans reranking (fallback)"""
        all_results = []
        
        # Convertir MeiliSearch results
        for result in meilisearch_results:
            rerank_result = RerankResult(
                id=result.id,
                content=result.content,
                original_score=result.score,
                rerank_score=result.score,  # Pas de reranking
                final_score=result.score,
                source='meilisearch',
                metadata=result.metadata
            )
            all_results.append(rerank_result)
        
        # Convertir Supabase results
        for result in supabase_results:
            rerank_result = RerankResult(
                id=result.id,
                content=result.content,
                original_score=result.similarity_score,
                rerank_score=result.similarity_score,  # Pas de reranking
                final_score=result.similarity_score,
                source='supabase',
                metadata=result.metadata
            )
            all_results.append(rerank_result)
        
        # Déduplication par ID
        seen_ids = set()
        unique_results = []
        for result in all_results:
            if result.id not in seen_ids:
                seen_ids.add(result.id)
                unique_results.append(result)
        
        # Tri et limitation
        unique_results.sort(key=lambda x: x.final_score, reverse=True)
        return unique_results[:top_k]
    
    async def rerank_single_source(
        self,
        query: str,
        results: Union[List[MeiliSearchResult], List[SemanticResult]],
        company_id: str,
        top_k: int = 10
    ) -> List[RerankResult]:
        """Reranking d'une seule source (MeiliSearch OU Supabase)"""
        if isinstance(results[0], MeiliSearchResult):
            return await self.rerank_results(query, results, [], company_id, top_k)
        else:
            return await self.rerank_results(query, [], results, company_id, top_k)
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du reranker"""
        stats = dict(self._stats)
        
        if stats.get('total_rerank_calls', 0) > 0:
            stats['avg_rerank_time_ms'] = stats['total_rerank_time_ms'] / stats['total_rerank_calls']
        
        stats['cache_hit_rate'] = stats.get('cache_hits', 0) / max(stats.get('total_rerank_calls', 1), 1)
        stats['cache_size'] = len(self._cache)
        stats['model_loaded'] = self.model_loaded
        
        return stats
    
    def clear_cache(self):
        """Vide le cache de reranking"""
        self._cache.clear()
        log3("[RERANKER]", "✅ Cache de reranking vidé")


# Instance globale
_reranker: Optional[ScalableReranker] = None

def get_reranker() -> ScalableReranker:
    """Récupère l'instance globale du reranker"""
    global _reranker
    if _reranker is None:
        _reranker = ScalableReranker()
    return _reranker
