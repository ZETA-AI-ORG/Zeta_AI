#!/usr/bin/env python3
"""
🚀 CACHE EMBEDDING OPTIMISÉ SCALABLE
Objectif: Réduire le temps de génération embeddings de 1.9s à 0.01s
Architecture: Cache intelligent avec similarité et TTL adaptatif
"""

import hashlib
import time
import numpy as np
from typing import Dict, Optional, Any, List, Tuple
from datetime import datetime, timedelta
import threading
from utils import log3

class GlobalEmbeddingCache:
    """
    🚀 Cache intelligent des embeddings avec détection de similarité
    - Cache basé sur hash de la query
    - Détection de similarité pour réutilisation
    - TTL adaptatif selon fréquence d'usage
    - Compression des embeddings pour économiser la mémoire
    """
    
    def __init__(self, max_cache_size: int = 10000, similarity_threshold: float = 0.95):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_cache_size = max_cache_size
        self.similarity_threshold = similarity_threshold
        self.lock = threading.RLock()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "similarity_hits": 0,
            "evictions": 0,
            "compressions": 0
        }
        
        log3("[EMBEDDING_CACHE]", "🚀 Cache embedding optimisé initialisé")
    
    def _create_query_hash(self, query: str, model_name: str = "all-mpnet-base-v2") -> str:
        """Crée un hash unique pour une query + modèle"""
        combined = f"{model_name}:{query.lower().strip()}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]
    
    def _calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calcule la similarité cosinus entre deux embeddings"""
        try:
            # Normaliser les vecteurs
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            # Similarité cosinus
            similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
            return float(similarity)
        except Exception:
            return 0.0
    
    def _find_similar_embedding(self, query: str, target_embedding: Optional[np.ndarray] = None) -> Optional[Tuple[str, np.ndarray]]:
        """
        🔍 Trouve un embedding similaire dans le cache
        Retourne (cache_key, embedding) si trouvé
        """
        if len(self.cache) == 0:
            return None
        
        query_words = set(query.lower().split())
        best_similarity = 0.0
        best_match = None
        
        with self.lock:
            for cache_key, cache_entry in self.cache.items():
                if self._is_expired(cache_entry):
                    continue
                
                cached_query = cache_entry["original_query"]
                cached_words = set(cached_query.lower().split())
                
                # Similarité textuelle rapide
                word_overlap = len(query_words.intersection(cached_words))
                word_union = len(query_words.union(cached_words))
                text_similarity = word_overlap / word_union if word_union > 0 else 0.0
                
                # Si similarité textuelle suffisante, vérifier embedding
                if text_similarity > 0.7 and target_embedding is not None:
                    cached_embedding = cache_entry["embedding"]
                    embedding_similarity = self._calculate_similarity(target_embedding, cached_embedding)
                    
                    if embedding_similarity > best_similarity and embedding_similarity >= self.similarity_threshold:
                        best_similarity = embedding_similarity
                        best_match = (cache_key, cached_embedding)
        
        if best_match:
            log3("[EMBEDDING_CACHE]", {
                "action": "similarity_match",
                "query": query[:50],
                "similarity_score": f"{best_similarity:.3f}",
                "threshold": self.similarity_threshold
            })
        
        return best_match
    
    def _is_expired(self, cache_entry: Dict[str, Any]) -> bool:
        """Vérifie si une entrée est expirée avec TTL adaptatif"""
        return datetime.now() > cache_entry["expires_at"]
    
    def _calculate_adaptive_ttl(self, access_count: int) -> timedelta:
        """TTL adaptatif basé sur la fréquence d'usage"""
        if access_count >= 10:
            return timedelta(hours=24)  # Très utilisé
        elif access_count >= 5:
            return timedelta(hours=6)   # Moyennement utilisé
        else:
            return timedelta(hours=1)   # Peu utilisé
    
    def _evict_oldest(self) -> None:
        """Supprime les entrées les plus anciennes si cache plein"""
        if len(self.cache) < self.max_cache_size:
            return
        
        with self.lock:
            # Trier par date d'accès (plus ancien en premier)
            sorted_entries = sorted(
                self.cache.items(),
                key=lambda x: x[1]["last_accessed"]
            )
            
            # Supprimer 20% des entrées les plus anciennes
            to_remove = int(len(sorted_entries) * 0.2)
            for i in range(to_remove):
                cache_key = sorted_entries[i][0]
                del self.cache[cache_key]
                self.stats["evictions"] += 1
        
        log3("[EMBEDDING_CACHE]", {"action": "eviction", "removed_count": to_remove})
    
    async def get_embedding(self, query: str, model_name: str = "all-mpnet-base-v2") -> Optional[np.ndarray]:
        """
        🎯 Récupère un embedding depuis le cache
        Utilise la similarité pour réutiliser des embeddings proches
        """
        query_hash = self._create_query_hash(query, model_name)
        
        with self.lock:
            # Cache hit exact
            if query_hash in self.cache:
                cache_entry = self.cache[query_hash]
                
                if not self._is_expired(cache_entry):
                    # Mettre à jour les stats d'accès
                    cache_entry["access_count"] += 1
                    cache_entry["last_accessed"] = datetime.now()
                    
                    # Recalculer TTL adaptatif
                    new_ttl = self._calculate_adaptive_ttl(cache_entry["access_count"])
                    cache_entry["expires_at"] = datetime.now() + new_ttl
                    
                    self.stats["hits"] += 1
                    log3("[EMBEDDING_CACHE]", {
                        "action": "cache_hit",
                        "query": query[:50],
                        "access_count": cache_entry["access_count"],
                        "new_ttl_hours": new_ttl.total_seconds() / 3600
                    })
                    
                    return cache_entry["embedding"]
                else:
                    # Entrée expirée
                    del self.cache[query_hash]
        
        # Recherche par similarité
        similar_match = self._find_similar_embedding(query)
        if similar_match:
            cache_key, embedding = similar_match
            self.stats["similarity_hits"] += 1
            
            # Mettre en cache avec la nouvelle query
            await self.set_embedding(query, embedding, model_name)
            return embedding
        
        # Cache miss complet
        self.stats["misses"] += 1
        log3("[EMBEDDING_CACHE]", {"action": "cache_miss", "query": query[:50]})
        return None
    
    async def set_embedding(self, query: str, embedding: np.ndarray, model_name: str = "all-mpnet-base-v2") -> None:
        """💾 Met en cache un embedding avec compression optionnelle"""
        if embedding is None or len(embedding) == 0:
            return
        
        # Éviction si nécessaire
        self._evict_oldest()
        
        query_hash = self._create_query_hash(query, model_name)
        now = datetime.now()
        
        # Compression pour économiser la mémoire (float32 au lieu de float64)
        compressed_embedding = embedding.astype(np.float32)
        
        with self.lock:
            self.cache[query_hash] = {
                "embedding": compressed_embedding,
                "original_query": query,
                "model_name": model_name,
                "cached_at": now,
                "last_accessed": now,
                "expires_at": now + timedelta(hours=1),  # TTL initial
                "access_count": 0,
                "embedding_size": compressed_embedding.nbytes
            }
        
        self.stats["compressions"] += 1
        log3("[EMBEDDING_CACHE]", {
            "action": "cache_set",
            "query": query[:50],
            "embedding_dims": len(compressed_embedding),
            "size_bytes": compressed_embedding.nbytes
        })
    
    def get_stats(self) -> Dict[str, Any]:
        """📊 Statistiques détaillées du cache"""
        with self.lock:
            total_requests = self.stats["hits"] + self.stats["misses"] + self.stats["similarity_hits"]
            hit_rate = ((self.stats["hits"] + self.stats["similarity_hits"]) / total_requests * 100) if total_requests > 0 else 0
            
            total_memory = sum(entry["embedding_size"] for entry in self.cache.values())
            
            return {
                "cache_size": len(self.cache),
                "max_cache_size": self.max_cache_size,
                "memory_usage_mb": total_memory / (1024 * 1024),
                "total_requests": total_requests,
                "exact_hits": self.stats["hits"],
                "similarity_hits": self.stats["similarity_hits"],
                "misses": self.stats["misses"],
                "hit_rate_percent": f"{hit_rate:.1f}%",
                "evictions": self.stats["evictions"],
                "compressions": self.stats["compressions"]
            }
    
    def clear_expired(self) -> int:
        """🧹 Nettoie les entrées expirées"""
        expired_keys = []
        
        with self.lock:
            for key, entry in self.cache.items():
                if self._is_expired(entry):
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache[key]
        
        if expired_keys:
            log3("[EMBEDDING_CACHE]", {"action": "cleanup_expired", "expired_count": len(expired_keys)})
        
        return len(expired_keys)

# Instance globale
_global_embedding_cache = None

def get_global_embedding_cache() -> GlobalEmbeddingCache:
    """🚀 Singleton pour le cache embedding optimisé"""
    global _global_embedding_cache
    if _global_embedding_cache is None:
        _global_embedding_cache = GlobalEmbeddingCache()
    return _global_embedding_cache
