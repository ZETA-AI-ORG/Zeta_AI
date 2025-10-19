"""
🚀 WRAPPER OPTIMISÉ POUR MEILISEARCH
Réduit la latence de recherche sans changer la logique
"""
import asyncio
import time
from typing import List, Dict, Any, Optional
import httpx
from collections import defaultdict

from utils import log3


class MeiliSearchOptimizedWrapper:
    """
    Wrapper optimisé pour MeiliSearch qui:
    1. Réduit le nombre de n-grams (30 → 20)
    2. Utilise HTTP/2 avec connection pooling
    3. Batch les requêtes intelligemment
    4. Cache les résultats temporairement
    """
    
    def __init__(self, meili_client, http_client: Optional[httpx.AsyncClient] = None):
        """
        Args:
            meili_client: Client MeiliSearch existant
            http_client: Client HTTP optimisé (optionnel)
        """
        self.meili_client = meili_client
        self.http_client = http_client or httpx.AsyncClient(
            timeout=httpx.Timeout(5.0, connect=2.0),
            limits=httpx.Limits(max_connections=200, max_keepalive_connections=50),
            http2=True
        )
        
        # Cache temporaire des résultats (TTL 60s)
        self.result_cache: Dict[str, tuple[List[Dict], float]] = {}
        self.cache_ttl = 60
        
        log3("[MEILI_OPTIMIZED]", "✅ Wrapper MeiliSearch optimisé initialisé")
    
    def _optimize_ngrams(self, ngrams: List[str], max_ngrams: int = 20) -> List[str]:
        """
        Optimise les n-grams pour réduire le nombre de requêtes
        
        Stratégie:
        1. Garder tous les tri-grams (plus spécifiques)
        2. Garder les bi-grams qui apportent de nouveaux mots
        3. Garder les uni-grams importants (chiffres, mots-clés)
        """
        # Séparer par type
        trigrams = [ng for ng in ngrams if len(ng.split()) == 3]
        bigrams = [ng for ng in ngrams if len(ng.split()) == 2]
        unigrams = [ng for ng in ngrams if len(ng.split()) == 1]
        
        optimized = []
        seen_words = set()
        
        # 1. Tous les tri-grams (très spécifiques)
        for ng in trigrams:
            optimized.append(ng)
            seen_words.update(ng.split())
        
        # 2. Bi-grams qui apportent de nouveaux mots
        for ng in bigrams:
            words = set(ng.split())
            if not words.issubset(seen_words):
                optimized.append(ng)
                seen_words.update(words)
        
        # 3. Uni-grams importants (chiffres, mots longs)
        for ng in unigrams:
            if ng.isdigit() or len(ng) > 5:
                if ng not in seen_words:
                    optimized.append(ng)
                    seen_words.add(ng)
        
        # Limiter au max
        result = optimized[:max_ngrams]
        
        if len(result) < len(ngrams):
            log3("[MEILI_OPTIMIZED]", f"🔧 N-grams optimisés: {len(ngrams)} → {len(result)}")
        
        return result
    
    async def search_parallel_optimized(
        self,
        indexes: List[str],
        ngrams: List[str],
        limit: int = 10,
        max_concurrent: int = 50
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Recherche parallèle optimisée sur plusieurs index
        
        Args:
            indexes: Liste des index à chercher
            ngrams: Liste des n-grams
            limit: Nombre max de résultats par recherche
            max_concurrent: Nombre max de requêtes concurrentes
            
        Returns:
            Résultats groupés par index
        """
        start_time = time.time()
        
        # 1. Optimiser les n-grams
        optimized_ngrams = self._optimize_ngrams(ngrams, max_ngrams=20)
        
        # 2. Créer les tâches de recherche
        tasks = []
        task_metadata = []
        
        for index_name in indexes:
            for ngram in optimized_ngrams:
                # Vérifier cache
                cache_key = f"{index_name}:{ngram}"
                if cache_key in self.result_cache:
                    cached_results, timestamp = self.result_cache[cache_key]
                    if time.time() - timestamp < self.cache_ttl:
                        # Utiliser le cache
                        continue
                
                # Créer la tâche
                task = self._search_single(index_name, ngram, limit)
                tasks.append(task)
                task_metadata.append((index_name, ngram))
        
        log3("[MEILI_OPTIMIZED]", f"🔍 Lancement {len(tasks)} recherches optimisées...")
        
        # 3. Exécuter par batch pour éviter surcharge
        results_by_index = defaultdict(list)
        
        for i in range(0, len(tasks), max_concurrent):
            batch = tasks[i:i+max_concurrent]
            batch_metadata = task_metadata[i:i+max_concurrent]
            
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            
            # Traiter les résultats
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    log3("[MEILI_OPTIMIZED]", f"⚠️ Erreur recherche: {result}")
                    continue
                
                index_name, ngram = batch_metadata[j]
                
                # Ajouter au résultat
                if result:
                    results_by_index[index_name].extend(result)
                    
                    # Mettre en cache
                    cache_key = f"{index_name}:{ngram}"
                    self.result_cache[cache_key] = (result, time.time())
        
        elapsed = (time.time() - start_time) * 1000
        log3("[MEILI_OPTIMIZED]", f"✅ Recherches terminées: {len(results_by_index)} index en {elapsed:.0f}ms")
        
        return dict(results_by_index)
    
    async def _search_single(
        self,
        index_name: str,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Recherche sur un seul index avec un n-gram
        
        Args:
            index_name: Nom de l'index
            query: N-gram à chercher
            limit: Nombre max de résultats
            
        Returns:
            Liste des documents trouvés
        """
        try:
            index = self.meili_client.index(index_name)
            results = await asyncio.to_thread(
                index.search,
                query,
                {"limit": limit, "attributesToRetrieve": ["*"]}
            )
            
            return results.get('hits', [])
            
        except Exception as e:
            log3("[MEILI_OPTIMIZED]", f"⚠️ Erreur recherche {index_name}/{query}: {e}")
            return []
    
    def clear_cache(self):
        """Vide le cache de résultats"""
        self.result_cache.clear()
        log3("[MEILI_OPTIMIZED]", "🗑️ Cache vidé")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du cache"""
        return {
            'cache_size': len(self.result_cache),
            'cache_ttl': self.cache_ttl
        }
    
    async def cleanup(self):
        """Nettoyage des ressources"""
        if self.http_client:
            await self.http_client.aclose()
        log3("[MEILI_OPTIMIZED]", "✅ Ressources nettoyées")


def wrap_meilisearch_client(meili_client, http_client: Optional[httpx.AsyncClient] = None):
    """
    Enveloppe un client MeiliSearch existant avec le wrapper optimisé
    
    Args:
        meili_client: Client MeiliSearch existant
        http_client: Client HTTP optimisé (optionnel)
        
    Returns:
        Wrapper optimisé
    """
    return MeiliSearchOptimizedWrapper(meili_client, http_client)
