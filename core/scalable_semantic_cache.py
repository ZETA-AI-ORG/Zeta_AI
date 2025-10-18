#!/usr/bin/env python3
"""
🎯 CACHE SÉMANTIQUE SCALABLE PAR COMPANY
Version améliorée avec isolation par company_id

ARCHITECTURE SCALABLE:
- Cache séparé par company_id
- Embeddings par company (évite pollution)
- Redis avec namespace par company
- Performance <100ms
"""

import asyncio
import hashlib
import json
import time
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from sentence_transformers import SentenceTransformer, util
import threading

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

@dataclass
class CacheEntry:
    """Entrée de cache simplifiée"""
    query: str
    response: str
    company_id: str
    query_embedding: List[float]
    timestamp: float
    hit_count: int
    ttl_seconds: int

class ScalableSemanticCache:
    """
    🎯 Cache Sémantique Scalable
    
    DIFFÉRENCES vs version précédente:
    - ✅ Isolation par company_id
    - ✅ Namespace Redis par company
    - ✅ Stats par company
    - ✅ Fonctionne pour ∞ entreprises
    """
    
    def __init__(self, 
                 similarity_threshold: float = 0.88,
                 max_cache_per_company: int = 500,  # ✅ Par company !
                 default_ttl: int = 1800):
        
        self.similarity_threshold = similarity_threshold
        self.max_cache_per_company = max_cache_per_company
        self.default_ttl = default_ttl
        
        # ✅ Cache par company_id (clé = company_id)
        self.memory_cache: Dict[str, Dict[str, CacheEntry]] = {}
        self.redis_client = None
        
        # Modèle d'embeddings léger
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        
        # ✅ Stats par company
        self.stats_by_company: Dict[str, Dict] = {}
        
        self.lock = threading.RLock()
        self._init_redis()
    
    def _init_redis(self):
        """Initialise Redis"""
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host='localhost',
                    port=6379,
                    db=5,  # DB 5 pour cache scalable
                    decode_responses=False
                )
                self.redis_client.ping()
                print("✅ ScalableSemanticCache: Redis DB 5 connecté")
            except:
                self.redis_client = None
                print("⚠️ ScalableSemanticCache: Redis non disponible")
    
    def _get_redis_key(self, company_id: str, cache_key: str) -> str:
        """Crée clé Redis avec namespace company"""
        return f"semantic_cache:v2:{company_id}:{cache_key}"
    
    def _create_embedding(self, text: str) -> List[float]:
        """Crée un embedding"""
        return self.model.encode(text, convert_to_tensor=False).tolist()
    
    def _compute_similarity(self, emb1: List[float], emb2: List[float]) -> float:
        """Calcule la similarité cosinus"""
        return util.cos_sim(emb1, emb2).item()
    
    def _init_company_cache(self, company_id: str):
        """Initialise cache et stats pour une company"""
        if company_id not in self.memory_cache:
            self.memory_cache[company_id] = {}
        
        if company_id not in self.stats_by_company:
            self.stats_by_company[company_id] = {
                "total_queries": 0,
                "cache_hits": 0,
                "cache_misses": 0,
                "avg_retrieve_time_ms": 0
            }
    
    async def get_cached_response(self, 
                                  query: str, 
                                  company_id: str) -> Optional[Tuple[str, float]]:
        """
        Récupère une réponse du cache (isolée par company)
        
        Args:
            query: Question de l'utilisateur
            company_id: ID de l'entreprise
            
        Returns:
            (response, confidence) si trouvé, None sinon
        """
        start_time = time.time()
        
        with self.lock:
            self._init_company_cache(company_id)
            
            stats = self.stats_by_company[company_id]
            stats["total_queries"] += 1
            
            # ✅ Cache SEULEMENT pour cette company
            company_cache = self.memory_cache[company_id]
            
            # Créer embedding query
            query_embedding = self._create_embedding(query)
            
            # Chercher dans le cache de CETTE company uniquement
            best_match = None
            best_similarity = 0.0
            
            for cache_key, entry in company_cache.items():
                # Vérifier TTL
                if time.time() - entry.timestamp > entry.ttl_seconds:
                    continue
                
                # Calculer similarité
                similarity = self._compute_similarity(query_embedding, entry.query_embedding)
                
                if similarity > best_similarity and similarity >= self.similarity_threshold:
                    best_similarity = similarity
                    best_match = entry
            
            # Stats
            retrieve_time_ms = (time.time() - start_time) * 1000
            stats["avg_retrieve_time_ms"] = (
                (stats["avg_retrieve_time_ms"] * (stats["total_queries"] - 1) + retrieve_time_ms)
                / stats["total_queries"]
            )
            
            if best_match:
                stats["cache_hits"] += 1
                best_match.hit_count += 1
                
                print(f"✅ Cache HIT [{company_id[:8]}] (sim: {best_similarity:.3f}, {retrieve_time_ms:.0f}ms)")
                return (best_match.response, best_similarity)
            else:
                stats["cache_misses"] += 1
                print(f"❌ Cache MISS [{company_id[:8]}] ({retrieve_time_ms:.0f}ms)")
                return None
    
    async def store_response(self, 
                            query: str,
                            response: str,
                            company_id: str,
                            ttl: Optional[int] = None):
        """
        Stocke une réponse dans le cache (isolée par company)
        
        Args:
            query: Question
            response: Réponse
            company_id: ID de l'entreprise
            ttl: Time-to-live optionnel
        """
        
        with self.lock:
            self._init_company_cache(company_id)
            
            # Créer embedding
            query_embedding = self._create_embedding(query)
            
            # Clé unique
            cache_key = hashlib.md5(f"{company_id}:{query}".encode()).hexdigest()
            
            # Créer entrée
            entry = CacheEntry(
                query=query,
                response=response,
                company_id=company_id,
                query_embedding=query_embedding,
                timestamp=time.time(),
                hit_count=0,
                ttl_seconds=ttl or self.default_ttl
            )
            
            # ✅ Stocker dans le cache de CETTE company
            self.memory_cache[company_id][cache_key] = entry
            
            # Nettoyer si trop d'entrées pour cette company
            if len(self.memory_cache[company_id]) > self.max_cache_per_company:
                self._cleanup_company_cache(company_id)
            
            total_entries = sum(len(cache) for cache in self.memory_cache.values())
            print(f"💾 Cache STORE [{company_id[:8]}] (company: {len(self.memory_cache[company_id])}, total: {total_entries})")
    
    def _cleanup_company_cache(self, company_id: str):
        """Nettoie les entrées obsolètes d'une company"""
        now = time.time()
        company_cache = self.memory_cache[company_id]
        
        # Supprimer entrées expirées
        expired_keys = [
            key for key, entry in company_cache.items()
            if now - entry.timestamp > entry.ttl_seconds
        ]
        
        for key in expired_keys:
            del company_cache[key]
        
        # Si encore trop, garder les plus utilisées
        if len(company_cache) > self.max_cache_per_company:
            sorted_entries = sorted(
                company_cache.items(),
                key=lambda x: x[1].hit_count
            )
            
            to_keep = dict(sorted_entries[-self.max_cache_per_company:])
            self.memory_cache[company_id] = to_keep
        
        print(f"🧹 Nettoyage [{company_id[:8]}]: {len(expired_keys)} expirées, {len(self.memory_cache[company_id])} conservées")
    
    def clear_company_cache(self, company_id: str):
        """Vide le cache d'une company spécifique"""
        with self.lock:
            if company_id in self.memory_cache:
                del self.memory_cache[company_id]
            if company_id in self.stats_by_company:
                del self.stats_by_company[company_id]
            print(f"🗑️ Cache vidé pour: {company_id}")
    
    def clear_all_caches(self):
        """Vide TOUS les caches"""
        with self.lock:
            self.memory_cache.clear()
            self.stats_by_company.clear()
            print("🗑️ Tous les caches vidés")
    
    def get_company_stats(self, company_id: str) -> Dict:
        """Stats pour une company spécifique"""
        with self.lock:
            if company_id not in self.stats_by_company:
                return {"error": "Company not found"}
            
            stats = self.stats_by_company[company_id].copy()
            
            hit_rate = (
                (stats["cache_hits"] / stats["total_queries"] * 100)
                if stats["total_queries"] > 0 else 0
            )
            
            cache_size = len(self.memory_cache.get(company_id, {}))
            
            return {
                **stats,
                "hit_rate_percent": hit_rate,
                "cache_size": cache_size,
                "company_id": company_id
            }
    
    def get_global_stats(self) -> Dict:
        """Stats globales toutes companies"""
        with self.lock:
            total_companies = len(self.memory_cache)
            total_entries = sum(len(cache) for cache in self.memory_cache.values())
            
            total_queries = sum(s["total_queries"] for s in self.stats_by_company.values())
            total_hits = sum(s["cache_hits"] for s in self.stats_by_company.values())
            
            global_hit_rate = (total_hits / total_queries * 100) if total_queries > 0 else 0
            
            return {
                "total_companies": total_companies,
                "total_entries": total_entries,
                "total_queries": total_queries,
                "total_hits": total_hits,
                "global_hit_rate_percent": global_hit_rate,
                "companies_list": list(self.memory_cache.keys())
            }

# Singleton global
_global_cache = None

def get_scalable_cache() -> ScalableSemanticCache:
    """Retourne l'instance globale du cache scalable"""
    global _global_cache
    if _global_cache is None:
        _global_cache = ScalableSemanticCache()
    return _global_cache


# API simplifiée pour intégration
async def get_cached_response_for_company(query: str, company_id: str) -> Optional[Tuple[str, float]]:
    """Récupère réponse du cache (API simple)"""
    cache = get_scalable_cache()
    return await cache.get_cached_response(query, company_id)

async def store_response_for_company(query: str, response: str, company_id: str):
    """Stocke réponse dans le cache (API simple)"""
    cache = get_scalable_cache()
    await cache.store_response(query, response, company_id)
