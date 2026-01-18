#!/usr/bin/env python3
"""
🚀 SYSTÈME DE CACHE UNIFIÉ SCALABLE
Objectif: Réduire le temps total de 19.6s à 7.3s
Architecture: Intégration de tous les caches avec monitoring unifié
"""

import asyncio
import time
from typing import Dict, Any, Optional
from datetime import datetime
import threading
from utils import log3

# Import des caches spécialisés
from core.global_prompt_cache import get_global_prompt_cache
from core.global_embedding_cache_optimized import get_global_embedding_cache
from core.global_model_cache import get_global_model_cache
from core.global_catalog_cache import get_global_catalog_cache

class UnifiedCacheSystem:
    """
    🚀 Système de cache unifié pour toutes les entreprises
    - Coordination entre tous les caches
    - Monitoring global des performances
    - Préchargement intelligent
    - Nettoyage automatique
    """
    
    def __init__(self):
        self.prompt_cache = get_global_prompt_cache()
        self.embedding_cache = get_global_embedding_cache()
        self.model_cache = get_global_model_cache()
        self.catalog_cache = get_global_catalog_cache()
        
        self.global_stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_time_saved_seconds": 0.0
        }
        
        self.lock = threading.RLock()
        log3("[UNIFIED_CACHE]", "🚀 Système de cache unifié initialisé")
    
    async def get_cached_prompt(self, company_id: str) -> Optional[str]:
        """
        🎯 Récupère un prompt avec cache optimisé
        Gain attendu: 2.1s → 0.01s
        """
        start_time = time.time()
        
        try:
            prompt = await self.prompt_cache.get_prompt(company_id)
            
            if prompt:
                time_saved = 2.1 - (time.time() - start_time)  # 2.1s = temps DB normal
                with self.lock:
                    self.global_stats["cache_hits"] += 1
                    self.global_stats["total_time_saved_seconds"] += time_saved
                
                # LOG SIMPLIFIÉ - Une seule ligne
                log3("[UNIFIED_CACHE]", f"✅ Prompt hit: {company_id[:8]}... | Saved: {time_saved:.3f}s")
            else:
                with self.lock:
                    self.global_stats["cache_misses"] += 1
            
            with self.lock:
                self.global_stats["total_requests"] += 1
            
            return prompt
            
        except Exception as e:
            log3("[UNIFIED_CACHE]", f"❌ Prompt error: {company_id[:8]}... | {str(e)}")
            return None
    
    async def get_cached_embedding(self, query: str, model_name: str = "sentence-transformers/all-mpnet-base-v2") -> Optional:
        """
        🎯 Récupère un embedding avec cache optimisé
        Gain attendu: 1.9s → 0.01s
        """
        start_time = time.time()
        
        try:
            embedding = await self.embedding_cache.get_embedding(query, model_name)
            
            if embedding is not None:
                time_saved = 1.9 - (time.time() - start_time)  # 1.9s = temps génération normal
                with self.lock:
                    self.global_stats["cache_hits"] += 1
                    self.global_stats["total_time_saved_seconds"] += time_saved
                
                log3("[UNIFIED_CACHE]", f"✅ Embedding hit: '{query[:30]}...' | Saved: {time_saved:.3f}s")
            else:
                with self.lock:
                    self.global_stats["cache_misses"] += 1
            
            with self.lock:
                self.global_stats["total_requests"] += 1
            
            return embedding
            
        except Exception as e:
            log3("[UNIFIED_CACHE]", f"❌ Embedding error: '{query[:30]}...' | {str(e)}")
            return None
    
    def get_cached_model(self, model_name: str = "sentence-transformers/all-mpnet-base-v2"):
        """
        🎯 Récupère un modèle avec cache persistant
        Gain attendu: 8.3s → 0s (après premier chargement)
        """
        start_time = time.time()
        
        try:
            model = self.model_cache.get_model(model_name)
            
            if model is not None:
                load_time = time.time() - start_time
                
                # Si chargement rapide = cache hit
                if load_time < 1.0:  # Moins d'1 seconde = cache hit
                    time_saved = 8.3 - load_time  # 8.3s = temps chargement normal
                    with self.lock:
                        self.global_stats["cache_hits"] += 1
                        self.global_stats["total_time_saved_seconds"] += time_saved
                    
                    log3("[UNIFIED_CACHE]", f"✅ Model hit: {model_name.split('/')[-1]} | Saved: {time_saved:.3f}s")
                else:
                    # Premier chargement
                    with self.lock:
                        self.global_stats["cache_misses"] += 1
                    
                    log3("[UNIFIED_CACHE]", f"🆕 Model loaded: {model_name.split('/')[-1]} | Time: {load_time:.3f}s")
            
            with self.lock:
                self.global_stats["total_requests"] += 1
            
            return model
            
        except Exception as e:
            log3("[UNIFIED_CACHE]", f"❌ Model error: {model_name.split('/')[-1]} | {str(e)}")
            return None
    
    async def preload_company_resources(self, company_id: str, common_queries: list = None) -> Dict[str, bool]:
        """
        🚀 Précharge toutes les ressources d'une entreprise
        Idéal pour les entreprises fréquemment utilisées
        """
        results = {
            "prompt_preloaded": False,
            "model_preloaded": False,
            "embeddings_preloaded": 0
        }
        
        try:
            # Précharger le prompt
            prompt = await self.prompt_cache.get_prompt(company_id)
            if prompt:
                results["prompt_preloaded"] = True
            
            # Précharger le modèle
            model = self.model_cache.get_model()
            if model:
                results["model_preloaded"] = True
            
            # Précharger des embeddings pour queries communes
            if common_queries and model:
                for query in common_queries[:5]:  # Limiter à 5 queries
                    try:
                        # Générer et cacher l'embedding
                        embedding = model.encode([query])
                        if len(embedding) > 0:
                            await self.embedding_cache.set_embedding(query, embedding[0])
                            results["embeddings_preloaded"] += 1
                    except Exception:
                        continue
            
            log3("[UNIFIED_CACHE]", {
                "action": "preload_complete",
                "company_id": company_id,
                "results": results
            })
            
        except Exception as e:
            log3("[UNIFIED_CACHE]", {
                "action": "preload_error",
                "company_id": company_id,
                "error": str(e)
            })
        
        return results
    
    def get_global_stats(self) -> Dict[str, Any]:
        """📊 Statistiques globales de tous les caches"""
        with self.lock:
            total_requests = self.global_stats["total_requests"]
            hit_rate = (self.global_stats["cache_hits"] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "unified_cache": {
                    "total_requests": total_requests,
                    "cache_hits": self.global_stats["cache_hits"],
                    "cache_misses": self.global_stats["cache_misses"],
                    "hit_rate_percent": f"{hit_rate:.1f}%",
                    "total_time_saved_seconds": f"{self.global_stats['total_time_saved_seconds']:.1f}s",
                    "average_time_saved_per_hit": f"{self.global_stats['total_time_saved_seconds'] / max(1, self.global_stats['cache_hits']):.3f}s"
                },
                "prompt_cache": self.prompt_cache.get_stats(),
                "embedding_cache": self.embedding_cache.get_stats(),
                "model_cache": self.model_cache.get_stats(),
                "catalog_cache": self.catalog_cache.get_stats(),
            }

    def invalidate_company_cache(self, company_id: str) -> Dict[str, Any]:
        """❌ Invalide tous les caches d'une entreprise (prompts + catalogue)."""
        results: Dict[str, Any] = {
            "company_id": company_id,
            "prompt_invalidated": False,
            "catalog_invalidated": False,
        }
        try:
            try:
                results["prompt_invalidated"] = bool(asyncio.run(self.prompt_cache.invalidate_prompt(company_id)))
            except RuntimeError:
                # Si déjà dans une boucle async, exécuter sans bloquer
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.prompt_cache.invalidate_prompt(company_id))
                    results["prompt_invalidated"] = True
                except Exception:
                    results["prompt_invalidated"] = False
            except Exception:
                results["prompt_invalidated"] = False

            try:
                try:
                    results["catalog_invalidated"] = bool(asyncio.run(self.catalog_cache.invalidate_catalog(company_id)))
                except RuntimeError:
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(self.catalog_cache.invalidate_catalog(company_id))
                        results["catalog_invalidated"] = True
                    except Exception:
                        results["catalog_invalidated"] = False
            except Exception:
                results["catalog_invalidated"] = False

            log3("[UNIFIED_CACHE]", {"action": "invalidate_company_cache", **results})
        except Exception:
            return results
        return results
    
    async def cleanup_all_caches(self) -> Dict[str, int]:
        """🧹 Nettoyage global de tous les caches"""
        results = {
            "prompt_expired": 0,
            "embedding_expired": 0,
            "model_cleanup": 0
        }
        
        try:
            # Nettoyer les caches expirés
            results["prompt_expired"] = self.prompt_cache.clear_expired()
            results["embedding_expired"] = self.embedding_cache.clear_expired()
            
            # Nettoyer les modèles peu utilisés
            model_cleanup = self.model_cache.force_cleanup()
            results["model_cleanup"] = model_cleanup.get("removed_models", 0)
            
            log3("[UNIFIED_CACHE]", {
                "action": "global_cleanup",
                "results": results
            })
            
        except Exception as e:
            log3("[UNIFIED_CACHE]", {
                "action": "cleanup_error",
                "error": str(e)
            })
        
        return results

# Instance globale singleton
_unified_cache_system = None

def get_unified_cache_system() -> UnifiedCacheSystem:
    """🚀 Singleton pour le système de cache unifié"""
    global _unified_cache_system
    if _unified_cache_system is None:
        _unified_cache_system = UnifiedCacheSystem()
    return _unified_cache_system

# Fonction de commodité pour l'intégration facile
async def get_optimized_resources(company_id: str, query: str, model_name: str = "sentence-transformers/all-mpnet-base-v2"):
    """
    🎯 Fonction tout-en-un pour récupérer toutes les ressources optimisées
    Retourne: (prompt, embedding, model)
    """
    cache_system = get_unified_cache_system()
    
    # Récupération en parallèle quand possible
    prompt_task = cache_system.get_cached_prompt(company_id)
    embedding_task = cache_system.get_cached_embedding(query, model_name)
    
    # Modèle en premier (synchrone)
    model = cache_system.get_cached_model(model_name)
    
    # Attendre les tâches async
    prompt, embedding = await asyncio.gather(prompt_task, embedding_task, return_exceptions=True)
    
    # Gérer les exceptions
    if isinstance(prompt, Exception):
        prompt = None
    if isinstance(embedding, Exception):
        embedding = None
    
    return prompt, embedding, model
