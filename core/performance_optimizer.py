"""
🚀 PERFORMANCE OPTIMIZER - OPTIMISATIONS SANS TOUCHER AU FORMAT LLM
Optimise uniquement les performances du système existant
"""
import os
import asyncio
import functools
from typing import Optional, Dict, Any
import httpx
from pathlib import Path

from utils import log3


class PerformanceOptimizer:
    """
    🚀 OPTIMISEUR DE PERFORMANCE
    
    Optimisations appliquées:
    1. Cache embedding persistant forcé
    2. Connection pooling HTTP optimisé
    3. Initialisation lazy des composants
    4. Cache prompt en mémoire
    5. Réduction latence MeiliSearch
    """
    
    _instance: Optional['PerformanceOptimizer'] = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        
        # 1. CACHE EMBEDDING PERSISTANT FORCÉ
        os.environ["EMBEDDING_DISK_CACHE"] = "false"  # Désactiver disque (trop lent)
        
        # 2. CONNECTION POOLING OPTIMISÉ
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            limits=httpx.Limits(
                max_connections=200,  # Au lieu de 100
                max_keepalive_connections=50  # Au lieu de 20
            ),
            http2=True  # Activer HTTP/2 pour multiplexing
        )
        
        # 3. CACHE PROMPT EN MÉMOIRE
        self.prompt_cache: Dict[str, tuple[str, float]] = {}
        self.prompt_cache_ttl = 3600  # 1 heure
        
        # 4. CACHE MODÈLES EMBEDDING PRÉCHARGÉS
        self.preloaded_models = {}
        
        log3("[PERF_OPTIMIZER]", "✅ Optimiseur de performance initialisé")
    
    async def preload_embedding_models(self):
        """Précharge les modèles d'embedding au démarrage"""
        from core.global_embedding_cache import GlobalEmbeddingCache
        
        cache = GlobalEmbeddingCache()
        
        # Modèles à précharger
        models_to_load = [
            "sentence-transformers/all-MiniLM-L6-v2",
            "sentence-transformers/all-mpnet-base-v2"
        ]
        
        log3("[PERF_OPTIMIZER]", f"🔄 Préchargement {len(models_to_load)} modèles...")
        
        for model_name in models_to_load:
            try:
                model = cache.get_model(model_name)
                self.preloaded_models[model_name] = model
                log3("[PERF_OPTIMIZER]", f"✅ Modèle préchargé: {model_name}")
            except Exception as e:
                log3("[PERF_OPTIMIZER]", f"⚠️ Erreur préchargement {model_name}: {e}")
        
        log3("[PERF_OPTIMIZER]", f"✅ {len(self.preloaded_models)} modèles préchargés")
    
    def get_http_client(self) -> httpx.AsyncClient:
        """Retourne le client HTTP optimisé"""
        return self.http_client
    
    async def get_prompt_cached(self, company_id: str, fetch_func) -> str:
        """
        Récupère un prompt avec cache mémoire
        
        Args:
            company_id: ID de l'entreprise
            fetch_func: Fonction async pour récupérer le prompt depuis DB
            
        Returns:
            Prompt texte
        """
        import time
        
        # Vérifier cache mémoire
        if company_id in self.prompt_cache:
            prompt, timestamp = self.prompt_cache[company_id]
            if time.time() - timestamp < self.prompt_cache_ttl:
                log3("[PERF_OPTIMIZER]", f"✅ Prompt cache hit: {company_id}")
                return prompt
        
        # Fetch depuis DB
        log3("[PERF_OPTIMIZER]", f"🔄 Prompt cache miss: {company_id}")
        prompt = await fetch_func()
        
        # Mise en cache
        self.prompt_cache[company_id] = (prompt, time.time())
        
        # Limiter taille du cache (max 100 entreprises)
        if len(self.prompt_cache) > 100:
            oldest_key = min(self.prompt_cache.keys(), 
                           key=lambda k: self.prompt_cache[k][1])
            del self.prompt_cache[oldest_key]
        
        return prompt
    
    def optimize_meilisearch_query(self, ngrams: list, max_ngrams: int = 20) -> list:
        """
        Optimise les n-grams pour réduire le nombre de requêtes
        
        Args:
            ngrams: Liste complète des n-grams
            max_ngrams: Nombre maximum à garder
            
        Returns:
            Liste optimisée des n-grams
        """
        # Stratégie: garder les n-grams les plus longs et les plus pertinents
        
        # 1. Trier par longueur décroissante (tri-grams > bi-grams > uni-grams)
        sorted_ngrams = sorted(ngrams, key=lambda x: (-len(x.split()), x))
        
        # 2. Filtrer les n-grams redondants
        optimized = []
        seen_words = set()
        
        for ngram in sorted_ngrams:
            words = set(ngram.split())
            
            # Garder si apporte de nouveaux mots OU si c'est un tri-gram
            if len(ngram.split()) >= 3 or not words.issubset(seen_words):
                optimized.append(ngram)
                seen_words.update(words)
            
            if len(optimized) >= max_ngrams:
                break
        
        log3("[PERF_OPTIMIZER]", f"🔧 N-grams optimisés: {len(ngrams)} → {len(optimized)}")
        return optimized
    
    async def parallel_meilisearch_optimized(
        self,
        indexes: list,
        ngrams: list,
        search_func,
        max_concurrent: int = 50
    ) -> Dict[str, list]:
        """
        Recherche parallèle MeiliSearch optimisée
        
        Args:
            indexes: Liste des index à chercher
            ngrams: Liste des n-grams
            search_func: Fonction de recherche async
            max_concurrent: Nombre max de requêtes concurrentes
            
        Returns:
            Résultats par index
        """
        # Optimiser les n-grams
        optimized_ngrams = self.optimize_meilisearch_query(ngrams, max_ngrams=20)
        
        # Créer les tâches
        tasks = []
        for index in indexes:
            for ngram in optimized_ngrams:
                tasks.append((index, ngram, search_func(index, ngram)))
        
        log3("[PERF_OPTIMIZER]", f"🔍 Lancement {len(tasks)} recherches optimisées...")
        
        # Exécution par batch pour éviter surcharge
        results_by_index = {}
        
        for i in range(0, len(tasks), max_concurrent):
            batch = tasks[i:i+max_concurrent]
            batch_results = await asyncio.gather(
                *[task for _, _, task in batch],
                return_exceptions=True
            )
            
            # Regrouper résultats
            for j, (index, ngram, _) in enumerate(batch):
                if i+j < len(batch_results) and not isinstance(batch_results[j], Exception):
                    if index not in results_by_index:
                        results_by_index[index] = []
                    results_by_index[index].extend(batch_results[j])
        
        log3("[PERF_OPTIMIZER]", f"✅ Recherches terminées: {len(results_by_index)} index")
        return results_by_index
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques d'optimisation"""
        return {
            'preloaded_models': len(self.preloaded_models),
            'prompt_cache_size': len(self.prompt_cache),
            'http_connections': {
                'max': 200,
                'keepalive': 50,
                'http2_enabled': True
            }
        }
    
    async def cleanup(self):
        """Nettoyage des ressources"""
        await self.http_client.aclose()
        log3("[PERF_OPTIMIZER]", "✅ Ressources nettoyées")


# Instance globale
_optimizer: Optional[PerformanceOptimizer] = None

def get_performance_optimizer() -> PerformanceOptimizer:
    """Récupère l'instance globale de l'optimiseur"""
    global _optimizer
    if _optimizer is None:
        _optimizer = PerformanceOptimizer()
    return _optimizer


async def initialize_performance_optimizations():
    """Initialise toutes les optimisations au démarrage de l'app"""
    optimizer = get_performance_optimizer()
    
    log3("[PERF_OPTIMIZER]", "🚀 Initialisation optimisations...")
    
    # Précharger les modèles d'embedding
    await optimizer.preload_embedding_models()
    
    log3("[PERF_OPTIMIZER]", "✅ Optimisations initialisées")
    
    return optimizer
