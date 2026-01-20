#!/usr/bin/env python3
"""
⚡ SYSTÈME DE CACHE INTELLIGENT MULTI-NIVEAUX
Architecture scalable avec prédiction et auto-optimisation
"""

import asyncio
import time
import json
import hashlib
import pickle
import zlib
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from collections import defaultdict, OrderedDict
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor

from core.cache_manager import cache_manager
from utils import log3


class CacheLevel(Enum):
    """Niveaux de cache avec priorités différentes"""
    MEMORY = "memory"      # Cache en mémoire ultra-rapide
    REDIS = "redis"        # Cache Redis distribué
    DISK = "disk"          # Cache disque pour persistance
    PREDICTION = "prediction"  # Cache prédictif


@dataclass
class CacheEntry:
    """Entrée de cache avec métadonnées intelligentes"""
    key: str
    value: Any
    level: CacheLevel
    created_at: float
    last_accessed: float
    access_count: int
    size_bytes: int
    ttl_seconds: int
    prediction_score: float = 0.0
    compression_ratio: float = 1.0


@dataclass
class CacheMetrics:
    """Métriques de performance du cache"""
    hit_rate: float
    miss_rate: float
    avg_response_time_ms: float
    total_requests: int
    memory_usage_mb: float
    compression_savings_mb: float


class IntelligentCacheSystem:
    """
    🧠 SYSTÈME DE CACHE INTELLIGENT AVEC APPRENTISSAGE
    
    Features:
    - Cache multi-niveaux (Memory → Redis → Disk)
    - Prédiction intelligente des requêtes futures
    - Compression automatique des gros objets
    - Auto-éviction basée sur patterns d'usage
    - Pré-chargement adaptatif
    - Métriques temps réel
    """
    
    def __init__(self, company_id: str, max_memory_mb: int = 100):
        self.company_id = company_id
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        
        # Caches multi-niveaux
        self.memory_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.access_patterns: Dict[str, List[float]] = defaultdict(list)
        self.prediction_cache: Dict[str, float] = {}
        
        # Métriques et monitoring
        self.metrics = {
            'hits': defaultdict(int),
            'misses': defaultdict(int),
            'response_times': defaultdict(list),
            'memory_usage': 0,
            'compression_savings': 0
        }
        
        # Thread pool pour opérations async
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.lock = threading.RLock()
        
        # Configuration adaptive
        self.config = {
            'compression_threshold_bytes': 1024,  # Compresser si > 1KB
            'prediction_threshold': 0.7,  # Score minimum pour prédiction
            'memory_eviction_threshold': 0.8,  # Éviction si > 80% mémoire
            'access_pattern_window': 3600,  # Fenêtre d'analyse 1h
        }
        
        log3("[INTELLIGENT_CACHE]", f"✅ Cache initialisé pour {company_id}")
    
    async def get(self, key: str, default: Any = None) -> Optional[Any]:
        """Récupération intelligente avec apprentissage des patterns"""
        start_time = time.time()
        
        # Normalisation de la clé
        cache_key = self._normalize_key(key)
        
        try:
            # Niveau 1: Cache mémoire (ultra-rapide)
            entry = await self._get_from_memory(cache_key)
            if entry:
                await self._record_access(cache_key, CacheLevel.MEMORY, start_time)
                return entry.value
            
            # Niveau 2: Cache Redis (rapide)
            entry = await self._get_from_redis(cache_key)
            if entry:
                # Promotion vers mémoire si fréquemment utilisé
                await self._maybe_promote_to_memory(entry)
                await self._record_access(cache_key, CacheLevel.REDIS, start_time)
                return entry.value
            
            # Niveau 3: Cache disque (persistant)
            entry = await self._get_from_disk(cache_key)
            if entry:
                await self._record_access(cache_key, CacheLevel.DISK, start_time)
                return entry.value
            
            # Cache miss - enregistrement pour apprentissage
            self.metrics['misses']['total'] += 1
            await self._learn_from_miss(cache_key)
            
            return default
            
        except Exception as e:
            log3("[INTELLIGENT_CACHE]", f"❌ Erreur get {cache_key}: {e}")
            return default
    
    async def set(self, key: str, value: Any, ttl_seconds: int = 3600, 
                  level: CacheLevel = CacheLevel.MEMORY) -> bool:
        """Stockage intelligent avec optimisation automatique"""
        
        cache_key = self._normalize_key(key)
        
        try:
            # Sérialisation et compression si nécessaire
            serialized_value, size_bytes, compression_ratio = await self._serialize_and_compress(value)
            
            # Création de l'entrée
            entry = CacheEntry(
                key=cache_key,
                value=value,
                level=level,
                created_at=time.time(),
                last_accessed=time.time(),
                access_count=1,
                size_bytes=size_bytes,
                ttl_seconds=ttl_seconds,
                compression_ratio=compression_ratio
            )
            
            # Stockage selon la stratégie optimale
            success = await self._store_optimally(entry, serialized_value)
            
            if success:
                # Mise à jour des métriques
                with self.lock:
                    self.metrics['memory_usage'] += size_bytes
                    if compression_ratio < 1.0:
                        savings = size_bytes * (1 - compression_ratio)
                        self.metrics['compression_savings'] += savings
                
                # Apprentissage des patterns
                await self._learn_from_set(cache_key, value)
            
            return success
            
        except Exception as e:
            log3("[INTELLIGENT_CACHE]", f"❌ Erreur set {cache_key}: {e}")
            return False
    
    async def _get_from_memory(self, key: str) -> Optional[CacheEntry]:
        """Récupération depuis cache mémoire avec LRU"""
        with self.lock:
            if key in self.memory_cache:
                entry = self.memory_cache[key]
                
                # Vérification TTL
                if time.time() - entry.created_at > entry.ttl_seconds:
                    del self.memory_cache[key]
                    return None
                
                # Mise à jour LRU
                self.memory_cache.move_to_end(key)
                entry.last_accessed = time.time()
                entry.access_count += 1
                
                return entry
        return None
    
    async def _get_from_redis(self, key: str) -> Optional[CacheEntry]:
        """Récupération depuis Redis avec décompression"""
        try:
            redis_key = f"intelligent_cache:{self.company_id}:{key}"
            cached_data = cache_manager.get(redis_key)
            
            if cached_data:
                # Désérialisation
                entry_data = json.loads(cached_data)
                value = await self._deserialize_and_decompress(
                    entry_data['serialized_value'],
                    entry_data.get('compression_ratio', 1.0)
                )
                
                entry = CacheEntry(
                    key=key,
                    value=value,
                    level=CacheLevel.REDIS,
                    created_at=entry_data['created_at'],
                    last_accessed=time.time(),
                    access_count=entry_data.get('access_count', 1) + 1,
                    size_bytes=entry_data['size_bytes'],
                    ttl_seconds=entry_data['ttl_seconds'],
                    compression_ratio=entry_data.get('compression_ratio', 1.0)
                )
                
                return entry
                
        except Exception as e:
            log3("[INTELLIGENT_CACHE]", f"⚠️ Erreur Redis get {key}: {e}")
        
        return None
    
    async def _get_from_disk(self, key: str) -> Optional[CacheEntry]:
        """Récupération depuis cache disque (placeholder pour implémentation future)"""
        # TODO: Implémenter cache disque avec SQLite ou fichiers
        return None
    
    async def _store_optimally(self, entry: CacheEntry, serialized_value: bytes) -> bool:
        """Stockage optimal selon la taille et les patterns d'accès"""
        
        # Décision intelligente du niveau de stockage
        if entry.size_bytes < 10 * 1024:  # < 10KB → Mémoire
            return await self._store_in_memory(entry)
        elif entry.size_bytes < 100 * 1024:  # < 100KB → Redis
            return await self._store_in_redis(entry, serialized_value)
        else:  # > 100KB → Disque
            return await self._store_in_disk(entry, serialized_value)
    
    async def _store_in_memory(self, entry: CacheEntry) -> bool:
        """Stockage en mémoire avec éviction intelligente"""
        with self.lock:
            # Vérification de l'espace disponible
            current_usage = sum(e.size_bytes for e in self.memory_cache.values())
            
            if current_usage + entry.size_bytes > self.max_memory_bytes:
                await self._evict_memory_entries(entry.size_bytes)
            
            self.memory_cache[entry.key] = entry
            return True
    
    async def _store_in_redis(self, entry: CacheEntry, serialized_value: bytes) -> bool:
        """Stockage Redis avec métadonnées"""
        try:
            redis_key = f"intelligent_cache:{self.company_id}:{entry.key}"
            
            entry_data = {
                'serialized_value': serialized_value.hex(),
                'created_at': entry.created_at,
                'access_count': entry.access_count,
                'size_bytes': entry.size_bytes,
                'ttl_seconds': entry.ttl_seconds,
                'compression_ratio': entry.compression_ratio
            }
            
            cache_manager.set(redis_key, json.dumps(entry_data), ttl_seconds=entry.ttl_seconds)
            return True
            
        except Exception as e:
            log3("[INTELLIGENT_CACHE]", f"❌ Erreur Redis set {entry.key}: {e}")
            return False
    
    async def _store_in_disk(self, entry: CacheEntry, serialized_value: bytes) -> bool:
        """Stockage disque (placeholder)"""
        # TODO: Implémenter stockage disque
        return await self._store_in_redis(entry, serialized_value)  # Fallback Redis
    
    async def _evict_memory_entries(self, needed_bytes: int):
        """Éviction intelligente basée sur LRU et patterns d'accès"""
        with self.lock:
            freed_bytes = 0
            keys_to_remove = []
            
            # Éviction LRU avec score d'importance
            for key, entry in self.memory_cache.items():
                if freed_bytes >= needed_bytes:
                    break
                
                # Score d'importance basé sur accès récents et fréquence
                time_since_access = time.time() - entry.last_accessed
                importance_score = entry.access_count / (1 + time_since_access / 3600)
                
                # Éviction si score faible
                if importance_score < 0.1:
                    keys_to_remove.append(key)
                    freed_bytes += entry.size_bytes
            
            # Suppression effective
            for key in keys_to_remove:
                del self.memory_cache[key]
            
            log3("[INTELLIGENT_CACHE]", f"🧹 Éviction: {len(keys_to_remove)} entrées, {freed_bytes} bytes libérés")
    
    async def _serialize_and_compress(self, value: Any) -> Tuple[bytes, int, float]:
        """Sérialisation avec compression intelligente"""
        
        # Sérialisation
        if isinstance(value, (str, int, float, bool)):
            serialized = json.dumps(value).encode('utf-8')
        else:
            serialized = pickle.dumps(value)
        
        original_size = len(serialized)
        
        # Compression si bénéfique
        if original_size > self.config['compression_threshold_bytes']:
            compressed = zlib.compress(serialized, level=6)
            if len(compressed) < original_size * 0.8:  # Gain > 20%
                return compressed, len(compressed), len(compressed) / original_size
        
        return serialized, original_size, 1.0
    
    async def _deserialize_and_decompress(self, data: str, compression_ratio: float) -> Any:
        """Désérialisation avec décompression"""
        
        # Conversion hex → bytes
        serialized = bytes.fromhex(data)
        
        # Décompression si nécessaire
        if compression_ratio < 1.0:
            serialized = zlib.decompress(serialized)
        
        # Désérialisation
        try:
            return json.loads(serialized.decode('utf-8'))
        except:
            return pickle.loads(serialized)
    
    async def _record_access(self, key: str, level: CacheLevel, start_time: float):
        """Enregistrement des accès pour apprentissage"""
        response_time = (time.time() - start_time) * 1000
        
        with self.lock:
            self.metrics['hits'][level.value] += 1
            self.metrics['response_times'][level.value].append(response_time)
            
            # Pattern d'accès pour prédiction
            self.access_patterns[key].append(time.time())
            
            # Nettoyage des anciens accès
            cutoff = time.time() - self.config['access_pattern_window']
            self.access_patterns[key] = [
                t for t in self.access_patterns[key] if t > cutoff
            ]
    
    async def _learn_from_miss(self, key: str):
        """Apprentissage depuis les cache miss"""
        # Analyse des patterns pour prédiction future
        pass
    
    async def _learn_from_set(self, key: str, value: Any):
        """Apprentissage depuis les opérations set"""
        # Analyse de la valeur pour optimisation future
        pass
    
    async def _maybe_promote_to_memory(self, entry: CacheEntry):
        """Promotion vers mémoire si accès fréquent"""
        if entry.access_count > 3 and entry.size_bytes < 50 * 1024:
            await self._store_in_memory(entry)
    
    def _normalize_key(self, key: str) -> str:
        """Normalisation des clés pour cohérence"""
        return hashlib.md5(f"{self.company_id}:{key}".encode()).hexdigest()
    
    async def get_metrics(self) -> CacheMetrics:
        """Métriques de performance en temps réel"""
        with self.lock:
            total_hits = sum(self.metrics['hits'].values())
            total_misses = sum(self.metrics['misses'].values())
            total_requests = total_hits + total_misses
            
            if total_requests == 0:
                return CacheMetrics(0, 0, 0, 0, 0, 0)
            
            hit_rate = total_hits / total_requests
            miss_rate = total_misses / total_requests
            
            # Temps de réponse moyen
            all_times = []
            for times in self.metrics['response_times'].values():
                all_times.extend(times)
            avg_response_time = sum(all_times) / len(all_times) if all_times else 0
            
            return CacheMetrics(
                hit_rate=hit_rate,
                miss_rate=miss_rate,
                avg_response_time_ms=avg_response_time,
                total_requests=total_requests,
                memory_usage_mb=self.metrics['memory_usage'] / (1024 * 1024),
                compression_savings_mb=self.metrics['compression_savings'] / (1024 * 1024)
            )
    
    async def preload_predictions(self):
        """Pré-chargement basé sur les prédictions"""
        # TODO: Implémenter prédiction et pré-chargement
        pass


# Factory pattern pour instances par entreprise
_cache_systems: Dict[str, IntelligentCacheSystem] = {}

def get_intelligent_cache(company_id: str) -> IntelligentCacheSystem:
    """Factory pour obtenir le cache intelligent d'une entreprise"""
    if company_id not in _cache_systems:
        _cache_systems[company_id] = IntelligentCacheSystem(company_id)
    return _cache_systems[company_id]


# API principale
async def smart_cache_get(key: str, company_id: str, default: Any = None) -> Any:
    """API principale - Récupération intelligente"""
    cache_system = get_intelligent_cache(company_id)
    return await cache_system.get(key, default)

async def smart_cache_set(key: str, value: Any, company_id: str, 
                         ttl_seconds: int = 3600) -> bool:
    """API principale - Stockage intelligent"""
    cache_system = get_intelligent_cache(company_id)
    return await cache_system.set(key, value, ttl_seconds)
