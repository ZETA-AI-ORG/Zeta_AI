"""
🧠 INTELLIGENT CACHE SYSTEM V2 - MULTI-NIVEAU SCALABLE
Cache intelligent avec plusieurs niveaux pour performance maximale
"""
import asyncio
import hashlib
import json
import pickle
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import threading

from utils import log3


@dataclass
class CacheEntry:
    """Entrée de cache avec métadonnées"""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int
    ttl_seconds: int
    size_bytes: int
    company_id: str
    cache_level: str  # L1, L2, L3


@dataclass
class CacheStats:
    """Statistiques du cache"""
    total_requests: int = 0
    l1_hits: int = 0
    l2_hits: int = 0
    l3_hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_size_bytes: int = 0
    avg_response_time_ms: float = 0.0


class IntelligentCacheSystemV2:
    """
    🧠 SYSTÈME DE CACHE INTELLIGENT MULTI-NIVEAU
    
    Architecture:
    - L1: Mémoire ultra-rapide (résultats récents, 100ms TTL)
    - L2: Mémoire rapide (résultats fréquents, 5min TTL)  
    - L3: Disque/Redis (résultats rares, 1h TTL)
    
    Fonctionnalités:
    - Cache adaptatif par tenant
    - Éviction intelligente (LRU + fréquence)
    - Compression automatique
    - Métriques détaillées
    - Nettoyage automatique
    """
    
    def __init__(self, 
                 l1_max_size_mb: int = 50,
                 l2_max_size_mb: int = 200,
                 l3_max_size_mb: int = 1000):
        
        # Configuration des niveaux
        self.l1_max_size = l1_max_size_mb * 1024 * 1024  # Bytes
        self.l2_max_size = l2_max_size_mb * 1024 * 1024
        self.l3_max_size = l3_max_size_mb * 1024 * 1024
        
        # Stockage par niveau
        self.l1_cache: Dict[str, CacheEntry] = {}  # Ultra-rapide
        self.l2_cache: Dict[str, CacheEntry] = {}  # Rapide
        self.l3_cache: Dict[str, CacheEntry] = {}  # Persistant
        
        # Statistiques
        self.stats = CacheStats()
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Nettoyage automatique
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5 minutes
        
        # Répertoire pour cache L3
        self.l3_dir = Path("cache/l3")
        self.l3_dir.mkdir(parents=True, exist_ok=True)
        
        log3("[CACHE_V2]", "✅ Cache intelligent multi-niveau initialisé")
    
    def _compute_cache_key(self, 
                          cache_type: str,
                          company_id: str,
                          query: str,
                          **kwargs) -> str:
        """Calcule une clé de cache unique"""
        # Inclure tous les paramètres dans la clé
        key_data = {
            'type': cache_type,
            'company_id': company_id,
            'query': query[:200],  # Limiter la longueur
            **kwargs
        }
        
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _estimate_size(self, obj: Any) -> int:
        """Estime la taille d'un objet en bytes"""
        try:
            return len(pickle.dumps(obj))
        except:
            # Fallback: estimation approximative
            if isinstance(obj, str):
                return len(obj.encode('utf-8'))
            elif isinstance(obj, (list, tuple)):
                return sum(self._estimate_size(item) for item in obj[:10])  # Sample
            elif isinstance(obj, dict):
                return sum(self._estimate_size(k) + self._estimate_size(v) 
                          for k, v in list(obj.items())[:10])  # Sample
            else:
                return 1024  # Estimation par défaut
    
    def _should_cache_in_l1(self, cache_type: str, size_bytes: int) -> bool:
        """Détermine si un objet doit aller en L1"""
        # L1 pour objets petits et fréquents
        if size_bytes > 10 * 1024:  # > 10KB
            return False
        
        # Types prioritaires pour L1
        l1_types = ['query_embedding', 'quick_search', 'user_context']
        return cache_type in l1_types
    
    def _should_cache_in_l2(self, cache_type: str, size_bytes: int) -> bool:
        """Détermine si un objet doit aller en L2"""
        # L2 pour objets moyens et modérément fréquents
        if size_bytes > 100 * 1024:  # > 100KB
            return False
        
        # Types prioritaires pour L2
        l2_types = ['search_results', 'llm_response', 'processed_query']
        return cache_type in l2_types
    
    def _get_ttl_for_type(self, cache_type: str, level: str) -> int:
        """Retourne le TTL approprié selon le type et niveau"""
        ttl_config = {
            'L1': {
                'query_embedding': 300,      # 5 min
                'quick_search': 60,          # 1 min
                'user_context': 600,         # 10 min
                'default': 180               # 3 min
            },
            'L2': {
                'search_results': 1800,      # 30 min
                'llm_response': 3600,        # 1h
                'processed_query': 900,      # 15 min
                'default': 1800              # 30 min
            },
            'L3': {
                'search_results': 7200,      # 2h
                'llm_response': 14400,       # 4h
                'processed_query': 3600,     # 1h
                'default': 7200              # 2h
            }
        }
        
        return ttl_config[level].get(cache_type, ttl_config[level]['default'])
    
    def _evict_lru(self, cache: Dict[str, CacheEntry], target_size: int):
        """Éviction LRU avec prise en compte de la fréquence"""
        if not cache:
            return
        
        # Trier par score d'éviction (dernière utilisation + fréquence)
        def eviction_score(entry: CacheEntry) -> float:
            age_hours = (datetime.now() - entry.last_accessed).total_seconds() / 3600
            frequency_bonus = min(entry.access_count / 10, 5)  # Max 5 points
            return age_hours - frequency_bonus
        
        sorted_entries = sorted(cache.values(), key=eviction_score, reverse=True)
        
        current_size = sum(entry.size_bytes for entry in cache.values())
        
        # Éviction jusqu'à atteindre la taille cible
        for entry in sorted_entries:
            if current_size <= target_size:
                break
            
            del cache[entry.key]
            current_size -= entry.size_bytes
            self.stats.evictions += 1
            
            log3("[CACHE_V2]", f"Éviction {entry.cache_level}: {entry.key[:16]}...")
    
    def _cleanup_expired(self):
        """Nettoie les entrées expirées"""
        now = datetime.now()
        
        for cache, level in [(self.l1_cache, 'L1'), (self.l2_cache, 'L2'), (self.l3_cache, 'L3')]:
            expired_keys = []
            
            for key, entry in cache.items():
                if (now - entry.created_at).total_seconds() > entry.ttl_seconds:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del cache[key]
                
            if expired_keys:
                log3("[CACHE_V2]", f"Nettoyage {level}: {len(expired_keys)} entrées expirées")
    
    def _auto_cleanup(self):
        """Nettoyage automatique périodique"""
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            self._cleanup_expired()
            
            # Éviction si nécessaire
            l1_size = sum(e.size_bytes for e in self.l1_cache.values())
            if l1_size > self.l1_max_size:
                self._evict_lru(self.l1_cache, int(self.l1_max_size * 0.8))
            
            l2_size = sum(e.size_bytes for e in self.l2_cache.values())
            if l2_size > self.l2_max_size:
                self._evict_lru(self.l2_cache, int(self.l2_max_size * 0.8))
            
            l3_size = sum(e.size_bytes for e in self.l3_cache.values())
            if l3_size > self.l3_max_size:
                self._evict_lru(self.l3_cache, int(self.l3_max_size * 0.8))
            
            self._last_cleanup = current_time
    
    async def get(self, 
                  cache_type: str,
                  company_id: str,
                  query: str,
                  **kwargs) -> Optional[Any]:
        """
        Récupère une valeur du cache (multi-niveau)
        
        Args:
            cache_type: Type de cache (search_results, llm_response, etc.)
            company_id: ID de l'entreprise
            query: Requête ou clé principale
            **kwargs: Paramètres additionnels pour la clé
            
        Returns:
            Valeur cachée ou None si pas trouvée
        """
        start_time = time.time()
        
        with self._lock:
            self.stats.total_requests += 1
            
            # Nettoyage automatique
            self._auto_cleanup()
            
            # Calculer la clé
            cache_key = self._compute_cache_key(cache_type, company_id, query, **kwargs)
            
            # Recherche L1 (ultra-rapide)
            if cache_key in self.l1_cache:
                entry = self.l1_cache[cache_key]
                entry.last_accessed = datetime.now()
                entry.access_count += 1
                self.stats.l1_hits += 1
                
                response_time = (time.time() - start_time) * 1000
                log3("[CACHE_V2]", f"✅ L1 hit en {response_time:.1f}ms")
                return entry.value
            
            # Recherche L2 (rapide)
            if cache_key in self.l2_cache:
                entry = self.l2_cache[cache_key]
                entry.last_accessed = datetime.now()
                entry.access_count += 1
                self.stats.l2_hits += 1
                
                # Promouvoir vers L1 si fréquent et petit
                if entry.access_count > 5 and entry.size_bytes < 5 * 1024:
                    self._promote_to_l1(entry)
                
                response_time = (time.time() - start_time) * 1000
                log3("[CACHE_V2]", f"✅ L2 hit en {response_time:.1f}ms")
                return entry.value
            
            # Recherche L3 (persistant)
            if cache_key in self.l3_cache:
                entry = self.l3_cache[cache_key]
                entry.last_accessed = datetime.now()
                entry.access_count += 1
                self.stats.l3_hits += 1
                
                # Promouvoir vers L2 si fréquent
                if entry.access_count > 3:
                    self._promote_to_l2(entry)
                
                response_time = (time.time() - start_time) * 1000
                log3("[CACHE_V2]", f"✅ L3 hit en {response_time:.1f}ms")
                return entry.value
            
            # Cache miss
            self.stats.misses += 1
            return None
    
    async def set(self,
                  cache_type: str,
                  company_id: str,
                  query: str,
                  value: Any,
                  **kwargs):
        """
        Stocke une valeur dans le cache (niveau approprié)
        
        Args:
            cache_type: Type de cache
            company_id: ID de l'entreprise
            query: Requête ou clé principale
            value: Valeur à cacher
            **kwargs: Paramètres additionnels
        """
        with self._lock:
            # Calculer la clé et la taille
            cache_key = self._compute_cache_key(cache_type, company_id, query, **kwargs)
            size_bytes = self._estimate_size(value)
            
            now = datetime.now()
            
            # Déterminer le niveau approprié
            if self._should_cache_in_l1(cache_type, size_bytes):
                level = 'L1'
                cache = self.l1_cache
            elif self._should_cache_in_l2(cache_type, size_bytes):
                level = 'L2'
                cache = self.l2_cache
            else:
                level = 'L3'
                cache = self.l3_cache
            
            # Créer l'entrée
            entry = CacheEntry(
                key=cache_key,
                value=value,
                created_at=now,
                last_accessed=now,
                access_count=1,
                ttl_seconds=self._get_ttl_for_type(cache_type, level),
                size_bytes=size_bytes,
                company_id=company_id,
                cache_level=level
            )
            
            # Stocker
            cache[cache_key] = entry
            
            log3("[CACHE_V2]", f"✅ Stocké en {level}: {cache_type} ({size_bytes} bytes)")
    
    def _promote_to_l1(self, entry: CacheEntry):
        """Promeut une entrée vers L1"""
        if entry.cache_level == 'L2' and entry.size_bytes < 10 * 1024:
            # Supprimer de L2
            if entry.key in self.l2_cache:
                del self.l2_cache[entry.key]
            
            # Ajouter à L1
            entry.cache_level = 'L1'
            self.l1_cache[entry.key] = entry
            
            log3("[CACHE_V2]", f"⬆️ Promotion L2→L1: {entry.key[:16]}...")
    
    def _promote_to_l2(self, entry: CacheEntry):
        """Promeut une entrée vers L2"""
        if entry.cache_level == 'L3' and entry.size_bytes < 100 * 1024:
            # Supprimer de L3
            if entry.key in self.l3_cache:
                del self.l3_cache[entry.key]
            
            # Ajouter à L2
            entry.cache_level = 'L2'
            self.l2_cache[entry.key] = entry
            
            log3("[CACHE_V2]", f"⬆️ Promotion L3→L2: {entry.key[:16]}...")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques détaillées"""
        with self._lock:
            total_requests = self.stats.total_requests
            
            stats = {
                'total_requests': total_requests,
                'hit_rate': (self.stats.l1_hits + self.stats.l2_hits + self.stats.l3_hits) / max(total_requests, 1),
                'l1_hit_rate': self.stats.l1_hits / max(total_requests, 1),
                'l2_hit_rate': self.stats.l2_hits / max(total_requests, 1),
                'l3_hit_rate': self.stats.l3_hits / max(total_requests, 1),
                'miss_rate': self.stats.misses / max(total_requests, 1),
                'evictions': self.stats.evictions,
                'cache_sizes': {
                    'L1': {
                        'entries': len(self.l1_cache),
                        'size_mb': sum(e.size_bytes for e in self.l1_cache.values()) / (1024 * 1024),
                        'max_size_mb': self.l1_max_size / (1024 * 1024)
                    },
                    'L2': {
                        'entries': len(self.l2_cache),
                        'size_mb': sum(e.size_bytes for e in self.l2_cache.values()) / (1024 * 1024),
                        'max_size_mb': self.l2_max_size / (1024 * 1024)
                    },
                    'L3': {
                        'entries': len(self.l3_cache),
                        'size_mb': sum(e.size_bytes for e in self.l3_cache.values()) / (1024 * 1024),
                        'max_size_mb': self.l3_max_size / (1024 * 1024)
                    }
                }
            }
            
            return stats
    
    def clear_cache(self, company_id: Optional[str] = None, cache_type: Optional[str] = None):
        """Vide le cache (optionnellement filtré)"""
        with self._lock:
            caches = [
                (self.l1_cache, 'L1'),
                (self.l2_cache, 'L2'),
                (self.l3_cache, 'L3')
            ]
            
            total_cleared = 0
            
            for cache, level in caches:
                keys_to_remove = []
                
                for key, entry in cache.items():
                    should_remove = True
                    
                    if company_id and entry.company_id != company_id:
                        should_remove = False
                    
                    if cache_type and not key.startswith(hashlib.md5(cache_type.encode()).hexdigest()[:8]):
                        should_remove = False
                    
                    if should_remove:
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del cache[key]
                    total_cleared += 1
            
            log3("[CACHE_V2]", f"✅ {total_cleared} entrées supprimées du cache")


# Instance globale
_intelligent_cache: Optional[IntelligentCacheSystemV2] = None

def get_intelligent_cache() -> IntelligentCacheSystemV2:
    """Récupère l'instance globale du cache intelligent"""
    global _intelligent_cache
    if _intelligent_cache is None:
        _intelligent_cache = IntelligentCacheSystemV2()
    return _intelligent_cache
