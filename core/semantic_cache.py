#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧠 SEMANTIC CACHE - Cache intelligent basé sur similarité sémantique
Permet de réutiliser réponses pour questions similaires (pas identiques)
Gain attendu: Cache hit 5% → 40%
"""

import json
import numpy as np
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import hashlib


class SemanticCache:
    """
    Cache sémantique utilisant embeddings pour similarité
    """
    
    def __init__(self, similarity_threshold: float = 0.85, max_cache_size: int = 1000):
        """
        Args:
            similarity_threshold: Seuil de similarité (0-1) pour considérer match
            max_cache_size: Nombre max d'entrées en cache
        """
        self.similarity_threshold = similarity_threshold
        self.max_cache_size = max_cache_size
        
        # Cache en mémoire: {query_hash: {embedding, response, metadata}}
        self.cache: Dict[str, Dict[str, Any]] = {}
        
        # Index pour recherche rapide
        self.embeddings_matrix: Optional[np.ndarray] = None
        self.query_hashes: List[str] = []
        
        # Modèle embeddings (lazy loading)
        self.model = None
        self._init_model()
        
        # Redis pour persistance (optionnel)
        self.redis_client = None
        self._init_redis()
        
        print(f"✅ [SEMANTIC_CACHE] Initialisé (seuil={similarity_threshold}, max={max_cache_size})")
    
    def _init_model(self):
        """Initialise modèle embeddings (lazy loading)"""
        if self.model is not None:
            print("♻️  [SEMANTIC_CACHE] Modèle déjà chargé (réutilisation)")
            return
            
        try:
            from sentence_transformers import SentenceTransformer
            print("🔄 [SEMANTIC_CACHE] Chargement modèle embeddings...")
            
            # Modèle léger et rapide (90MB, ~50ms par embedding)
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            
            print("✅ [SEMANTIC_CACHE] Modèle chargé (all-MiniLM-L6-v2)")
        except ImportError:
            print("⚠️ [SEMANTIC_CACHE] sentence-transformers non installé")
            print("   Installation: pip install sentence-transformers")
            self.model = None
        except Exception as e:
            print(f"❌ [SEMANTIC_CACHE] Erreur chargement modèle: {e}")
            self.model = None
    
    def _init_redis(self):
        """Initialise connexion Redis avec connection pool"""
        try:
            import redis
            # ✅ OPTIMISATION: Connection pool pour réutiliser connexions
            redis_pool = redis.ConnectionPool(
                host='localhost',
                port=6379,
                db=1,  # DB différente du cache classique
                decode_responses=False,  # Pour stocker numpy arrays
                max_connections=10,  # Pool de 10 connexions
                socket_keepalive=True,
                socket_connect_timeout=2
            )
            self.redis_client = redis.Redis(connection_pool=redis_pool)
            self.redis_client.ping()
            print("✅ [SEMANTIC_CACHE] Redis connecté avec pool (persistance activée)")
        except Exception as e:
            print(f"⚠️ [SEMANTIC_CACHE] Redis non disponible: {e}")
            self.redis_client = None
    
    def _get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Génère embedding pour un texte"""
        if not self.model:
            return None
        
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            print(f"❌ [SEMANTIC_CACHE] Erreur embedding: {e}")
            return None
    
    def _cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Calcule similarité cosinus entre 2 embeddings"""
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _make_hash(self, query: str, company_id: str) -> str:
        """Génère hash unique pour query + company"""
        key = f"{company_id}:{query}"
        return hashlib.md5(key.encode()).hexdigest()[:16]
    
    def get(
        self,
        query: str,
        company_id: str,
        return_similarity: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Recherche réponse similaire dans le cache
        
        Args:
            query: Question utilisateur
            company_id: ID entreprise
            return_similarity: Retourner score similarité
        
        Returns:
            {
                "response": "...",
                "similarity": 0.92,  # Si return_similarity=True
                "cached_at": "2025-10-14T22:00:00",
                "original_query": "question originale"
            }
            ou None si pas de match
        """
        if not self.model:
            return None
        
        print(f"🔍 [SEMANTIC_CACHE] Recherche pour: '{query[:50]}...'")
        
        # Générer embedding de la requête
        query_embedding = self._get_embedding(query)
        if query_embedding is None:
            return None
        
        # Rechercher dans le cache
        best_match = None
        best_similarity = 0.0
        
        for query_hash, cached_data in self.cache.items():
            # Vérifier company_id
            if cached_data.get("company_id") != company_id:
                continue
            
            # Calculer similarité
            cached_embedding = cached_data.get("embedding")
            if cached_embedding is None:
                continue
            
            similarity = self._cosine_similarity(query_embedding, cached_embedding)
            
            # Garder meilleur match
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = cached_data
        
        # Vérifier seuil
        if best_similarity >= self.similarity_threshold:
            print(f"✅ [SEMANTIC_CACHE HIT] Similarité: {best_similarity:.3f}")
            print(f"   Original: '{best_match.get('original_query', '')[:50]}...'")
            
            result = {
                "response": best_match.get("response"),
                "cached_at": best_match.get("cached_at"),
                "original_query": best_match.get("original_query")
            }
            
            if return_similarity:
                result["similarity"] = best_similarity
            
            return result
        
        print(f"📭 [SEMANTIC_CACHE MISS] Meilleure similarité: {best_similarity:.3f} < {self.similarity_threshold}")
        return None
    
    def set(
        self,
        query: str,
        company_id: str,
        response: Any,
        ttl: int = 3600
    ):
        """
        Sauvegarde réponse dans le cache sémantique
        
        Args:
            query: Question utilisateur
            company_id: ID entreprise
            response: Réponse à cacher
            ttl: Durée de vie en secondes (défaut 1h)
        """
        if not self.model:
            return
        
        # Générer embedding
        query_embedding = self._get_embedding(query)
        if query_embedding is None:
            return
        
        # Créer hash
        query_hash = self._make_hash(query, company_id)
        
        # Préparer données
        cache_data = {
            "embedding": query_embedding,
            "response": response,
            "company_id": company_id,
            "original_query": query,
            "cached_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(seconds=ttl)).isoformat()
        }
        
        # Sauvegarder en mémoire
        self.cache[query_hash] = cache_data
        self.query_hashes.append(query_hash)
        
        # Nettoyer si trop d'entrées
        if len(self.cache) > self.max_cache_size:
            self._cleanup_old_entries()
        
        print(f"💾 [SEMANTIC_CACHE] Sauvegardé (TTL={ttl}s, total={len(self.cache)})")
        
        # Sauvegarder dans Redis (optionnel)
        if self.redis_client:
            try:
                redis_key = f"semantic_cache:{query_hash}"
                # Sérialiser (sans embedding pour économiser espace)
                redis_data = {
                    "response": response,
                    "company_id": company_id,
                    "original_query": query,
                    "cached_at": cache_data["cached_at"]
                }
                self.redis_client.setex(
                    redis_key,
                    ttl,
                    json.dumps(redis_data)
                )
            except Exception as e:
                print(f"⚠️ [SEMANTIC_CACHE] Erreur Redis: {e}")
    
    def _cleanup_old_entries(self):
        """Nettoie entrées expirées ou plus anciennes"""
        print("🧹 [SEMANTIC_CACHE] Nettoyage cache...")
        
        now = datetime.now()
        to_remove = []
        
        for query_hash, cached_data in self.cache.items():
            expires_at = datetime.fromisoformat(cached_data.get("expires_at", now.isoformat()))
            if expires_at < now:
                to_remove.append(query_hash)
        
        # Supprimer expirés
        for query_hash in to_remove:
            del self.cache[query_hash]
            if query_hash in self.query_hashes:
                self.query_hashes.remove(query_hash)
        
        # Si encore trop, supprimer plus anciens
        if len(self.cache) > self.max_cache_size:
            sorted_hashes = sorted(
                self.cache.items(),
                key=lambda x: x[1].get("cached_at", ""),
                reverse=False
            )
            
            to_remove_count = len(self.cache) - self.max_cache_size
            for query_hash, _ in sorted_hashes[:to_remove_count]:
                del self.cache[query_hash]
                if query_hash in self.query_hashes:
                    self.query_hashes.remove(query_hash)
        
        print(f"✅ [SEMANTIC_CACHE] Nettoyé ({len(to_remove)} supprimés, {len(self.cache)} restants)")
    
    def clear(self):
        """Vide complètement le cache"""
        self.cache.clear()
        self.query_hashes.clear()
        self.embeddings_matrix = None
        print("🗑️  [SEMANTIC_CACHE] Cache vidé")
    
    def stats(self) -> Dict[str, Any]:
        """Retourne statistiques du cache"""
        return {
            "total_entries": len(self.cache),
            "max_size": self.max_cache_size,
            "similarity_threshold": self.similarity_threshold,
            "model_loaded": self.model is not None,
            "redis_connected": self.redis_client is not None
        }


# ============================================================================
# SINGLETON
# ============================================================================

_semantic_cache: Optional[SemanticCache] = None


def get_semantic_cache(
    similarity_threshold: float = 0.85,
    max_cache_size: int = 1000
) -> SemanticCache:
    """Récupère instance singleton du cache sémantique"""
    global _semantic_cache
    if _semantic_cache is None:
        _semantic_cache = SemanticCache(
            similarity_threshold=similarity_threshold,
            max_cache_size=max_cache_size
        )
    return _semantic_cache


# ============================================================================
# FONCTION HELPER POUR APP.PY
# ============================================================================

def check_semantic_cache(
    query: str,
    company_id: str
) -> Optional[Dict[str, Any]]:
    """
    Vérifie cache sémantique (interface simple)
    
    Usage dans app.py:
        cached = check_semantic_cache(req.message, req.company_id)
        if cached:
            return cached["response"]
    """
    cache = get_semantic_cache()
    return cache.get(query, company_id, return_similarity=True)


def save_to_semantic_cache(
    query: str,
    company_id: str,
    response: Any,
    ttl: int = 3600
):
    """
    Sauvegarde dans cache sémantique (interface simple)
    
    Usage dans app.py:
        save_to_semantic_cache(req.message, req.company_id, response)
    """
    cache = get_semantic_cache()
    cache.set(query, company_id, response, ttl)
