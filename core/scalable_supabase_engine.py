"""
🧠 SUPABASE SEMANTIC ENGINE SCALABLE - MULTI-TENANT OPTIMISÉ
Recherche sémantique pure avec pgvector, config-driven
"""
import asyncio
import hashlib
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import numpy as np

from utils import log3
from .tenant_config_manager import get_tenant_config, SearchConfig
from .global_embedding_cache import get_global_embedding_cache


@dataclass
class SemanticResult:
    """Résultat de recherche sémantique enrichi"""
    id: str
    content: str
    similarity_score: float
    metadata: Dict[str, Any]
    embedding_model: str
    chunk_index: int = 0


class ScalableSupabaseEngine:
    """
    🧠 MOTEUR SUPABASE SÉMANTIQUE SCALABLE MULTI-TENANT
    
    Fonctionnalités:
    - Recherche sémantique avec embeddings
    - Configuration par tenant
    - Cache des embeddings optimisé
    - Filtrage par métadonnées
    - Fallback intelligent
    """
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.embedding_cache = get_global_embedding_cache()
        
        # Cache des résultats sémantiques
        self._cache: Dict[str, Tuple[List[SemanticResult], float]] = {}
        self._stats = {
            'total_queries': 0,
            'cache_hits': 0,
            'embedding_cache_hits': 0,
            'total_query_time_ms': 0,
            'total_embedding_time_ms': 0
        }
        
        log3("[SUPABASE_SCALABLE]", "✅ Moteur Supabase sémantique scalable initialisé")
    
    async def _get_query_embedding(self, query: str, model_name: str = "all-MiniLM-L6-v2") -> np.ndarray:
        """Récupère l'embedding d'une requête (avec cache)"""
        start_time = time.time()
        
        # Vérifier le cache d'embeddings
        cache_key = f"{model_name}:{hashlib.md5(query.encode()).hexdigest()}"
        
        try:
            # Utiliser le cache global d'embeddings
            model = self.embedding_cache.get_model(model_name)
            embedding = model.encode(query, convert_to_numpy=True)
            
            embedding_time = (time.time() - start_time) * 1000
            self._stats['total_embedding_time_ms'] += embedding_time
            
            return embedding
            
        except Exception as e:
            log3("[SUPABASE_SCALABLE]", f"⚠️ Erreur embedding: {e}")
            # Fallback vers un modèle plus simple
            try:
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer('all-MiniLM-L6-v2')
                return model.encode(query, convert_to_numpy=True)
            except Exception as e2:
                log3("[SUPABASE_SCALABLE]", f"❌ Erreur embedding fallback: {e2}")
                raise e2
    
    def _build_metadata_filter(self, company_id: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Construit les filtres de métadonnées pour Supabase"""
        base_filter = {"company_id": {"eq": company_id}}
        
        if filters:
            for key, value in filters.items():
                if isinstance(value, dict):
                    # Filtres complexes (gte, lte, etc.)
                    base_filter[key] = value
                else:
                    # Filtres simples (égalité)
                    base_filter[key] = {"eq": value}
        
        return base_filter
    
    async def _search_semantic_supabase(
        self,
        embedding: np.ndarray,
        company_id: str,
        config: SearchConfig,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Recherche sémantique dans Supabase avec pgvector"""
        try:
            # Convertir embedding en liste pour Supabase
            embedding_list = embedding.tolist()
            
            # Construire la requête RPC
            rpc_params = {
                "query_embedding": embedding_list,
                "company_id": company_id,
                "similarity_threshold": config.supabase_similarity_threshold,
                "match_count": config.supabase_max_docs
            }
            
            # Ajouter filtres si nécessaire
            if filters:
                rpc_params["metadata_filter"] = filters
            
            # Exécuter la recherche
            result = self.supabase.rpc("match_documents_semantic", rpc_params).execute()
            
            if result.data:
                return result.data
            else:
                log3("[SUPABASE_SCALABLE]", f"Aucun résultat sémantique pour {company_id}")
                return []
                
        except Exception as e:
            log3("[SUPABASE_SCALABLE]", f"⚠️ Erreur recherche sémantique: {e}")
            return []
    
    def _convert_to_semantic_results(self, raw_results: List[Dict[str, Any]]) -> List[SemanticResult]:
        """Convertit les résultats bruts en SemanticResult"""
        results = []
        
        for doc in raw_results:
            result = SemanticResult(
                id=doc.get('id', ''),
                content=doc.get('content', ''),
                similarity_score=doc.get('similarity', 0.0),
                metadata=doc,
                embedding_model=doc.get('embedding_model', 'unknown'),
                chunk_index=doc.get('chunk_index', 0)
            )
            results.append(result)
        
        return results
    
    def _apply_semantic_boosting(self, results: List[SemanticResult], query: str) -> List[SemanticResult]:
        """Applique des boosts sémantiques spécifiques"""
        query_lower = query.lower()
        
        for result in results:
            content_lower = result.content.lower()
            
            # Boost si correspondance exacte trouvée
            if query_lower in content_lower:
                result.similarity_score *= 1.2
            
            # Boost si mots-clés importants
            important_keywords = ["prix", "livraison", "commande", "taille", "stock"]
            for keyword in important_keywords:
                if keyword in query_lower and keyword in content_lower:
                    result.similarity_score *= 1.1
        
        return results
    
    async def search_semantic(
        self,
        query: str,
        company_id: str,
        filters: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> List[SemanticResult]:
        """
        Recherche sémantique principale
        
        Args:
            query: Requête de recherche
            company_id: ID de l'entreprise
            filters: Filtres de métadonnées optionnels
            use_cache: Utiliser le cache ou non
            
        Returns:
            Liste des résultats sémantiques triés par similarité
        """
        start_time = time.time()
        
        # 1. Récupérer la configuration du tenant
        config = get_tenant_config(company_id).search
        
        if not config.supabase_enabled:
            log3("[SUPABASE_SCALABLE]", f"Supabase désactivé pour {company_id}")
            return []
        
        # 2. Vérifier le cache
        cache_key = f"{company_id}:{hashlib.md5((query + str(filters or {})).encode()).hexdigest()}"
        if use_cache and config.cache_enabled and cache_key in self._cache:
            cached_results, timestamp = self._cache[cache_key]
            if time.time() - timestamp < config.cache_ttl_seconds:
                log3("[SUPABASE_SCALABLE]", f"✅ Cache hit sémantique pour {company_id}")
                self._stats['cache_hits'] += 1
                return cached_results
        
        # 3. Générer l'embedding de la requête
        try:
            embedding = await self._get_query_embedding(query)
        except Exception as e:
            log3("[SUPABASE_SCALABLE]", f"❌ Impossible de générer embedding: {e}")
            return []
        
        # 4. Recherche sémantique
        raw_results = await self._search_semantic_supabase(
            embedding, company_id, config, filters
        )
        
        # 5. Conversion en SemanticResult
        results = self._convert_to_semantic_results(raw_results)
        
        # 6. Appliquer boosts sémantiques
        results = self._apply_semantic_boosting(results, query)
        
        # 7. Tri par similarité décroissante
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        
        # 8. Mise en cache
        if config.cache_enabled:
            self._cache[cache_key] = (results, time.time())
            # Nettoyage du cache si trop gros
            if len(self._cache) > config.cache_max_entries:
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]
        
        # 9. Métriques
        total_time = (time.time() - start_time) * 1000
        self._stats['total_queries'] += 1
        self._stats['total_query_time_ms'] += total_time
        
        log3("[SUPABASE_SCALABLE]", f"✅ {len(results)} docs sémantiques en {total_time:.1f}ms")
        
        return results
    
    async def search_with_fallback(
        self,
        query: str,
        company_id: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SemanticResult]:
        """
        Recherche sémantique avec fallback intelligent
        
        Si pas assez de résultats avec seuil élevé, 
        relance avec seuil plus bas
        """
        config = get_tenant_config(company_id).search
        
        # Première tentative avec seuil normal
        results = await self.search_semantic(query, company_id, filters)
        
        # Si pas assez de résultats, fallback avec seuil plus bas
        if len(results) < 3 and config.supabase_similarity_threshold > 0.5:
            log3("[SUPABASE_SCALABLE]", f"Fallback seuil bas pour {company_id}")
            
            # Temporairement baisser le seuil
            original_threshold = config.supabase_similarity_threshold
            config.supabase_similarity_threshold = 0.5
            
            try:
                fallback_results = await self.search_semantic(query, company_id, filters, use_cache=False)
                results.extend(fallback_results)
                
                # Déduplication
                seen_ids = set()
                unique_results = []
                for result in results:
                    if result.id not in seen_ids:
                        seen_ids.add(result.id)
                        unique_results.append(result)
                
                results = unique_results
                
            finally:
                # Restaurer le seuil original
                config.supabase_similarity_threshold = original_threshold
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du moteur sémantique"""
        stats = dict(self._stats)
        
        if stats.get('total_queries', 0) > 0:
            stats['avg_query_time_ms'] = stats['total_query_time_ms'] / stats['total_queries']
            stats['avg_embedding_time_ms'] = stats['total_embedding_time_ms'] / stats['total_queries']
        
        stats['cache_hit_rate'] = stats.get('cache_hits', 0) / max(stats.get('total_queries', 1), 1)
        stats['cache_size'] = len(self._cache)
        
        return stats
    
    def clear_cache(self, company_id: Optional[str] = None):
        """Vide le cache sémantique"""
        if company_id:
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{company_id}:")]
            for key in keys_to_remove:
                del self._cache[key]
            log3("[SUPABASE_SCALABLE]", f"✅ Cache sémantique vidé pour {company_id}")
        else:
            self._cache.clear()
            log3("[SUPABASE_SCALABLE]", "✅ Cache sémantique complet vidé")


# Instance globale
_supabase_engine: Optional[ScalableSupabaseEngine] = None

def get_supabase_engine() -> ScalableSupabaseEngine:
    """Récupère l'instance globale du moteur Supabase"""
    global _supabase_engine
    if _supabase_engine is None:
        from database.supabase_client import get_supabase_client
        supabase_client = get_supabase_client()
        _supabase_engine = ScalableSupabaseEngine(supabase_client)
    return _supabase_engine
