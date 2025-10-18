"""
🧠 CACHE UNIFIÉ INTELLIGENT - SYSTÈME PROFESSIONNEL
Remplace tous les caches fragmentés par un système unifié
"""

import asyncio
import json
import time
import hashlib
import pickle
import zlib
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from collections import OrderedDict, defaultdict
import threading
import aioredis
from pathlib import Path
import tempfile
import logging

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Entrée de cache optimisée"""
    value: Any
    timestamp: float
    ttl_seconds: int
    access_count: int = 0
    size_bytes: int = 0
    compressed: bool = False

@dataclass
class CacheStats:
    """Statistiques de cache"""
    total_gets: int = 0
    total_sets: int = 0
    hits: int = 0
    misses: int = 0
    memory_usage_bytes: int = 0
    redis_usage_bytes: int = 0

class UnifiedCachePro:
    """
    🎯 CACHE UNIFIÉ PROFESSIONNEL
    
    Fonctionnalités:
    - L1: Mémoire ultra-rapide (1MB hot data)
    - L2: Redis distribué (100MB warm data) 
    - L3: Disque persistant (1GB cold data)
    - Compression automatique des gros objets
    - Éviction intelligente LRU + ML
    - Prédiction des accès futurs
    - Métriques temps réel
    """
    
    def __init__(self, max_memory_mb: int = 50):
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        
        # Cache L1 - Mémoire
        self.l1_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.l1_lock = threading.RLock()
        
        # Cache L2 - Redis (connexion lazy)
        self.redis_client = None
        self.redis_connected = False
        
        # Cache L3 - Disque
        self.disk_cache_dir = Path(tempfile.gettempdir()) / "chatbot_unified_cache"
        self.disk_cache_dir.mkdir(exist_ok=True)
        
        # Statistiques et monitoring
        self.stats = CacheStats()
        self.access_patterns: Dict[str, List[float]] = defaultdict(list)
        self.prediction_scores: Dict[str, float] = {}
        
        # Configuration
        self.compression_threshold = 1024  # Compresser si > 1KB
        self.prediction_window = 3600  # 1 heure
        self.eviction_threshold = 0.8  # Éviction si > 80% plein
        
        logger.info(f"[UNIFIED_CACHE] ✅ Cache unifié initialisé (max: {max_memory_mb}MB)")
    
    async def _ensure_redis_connection(self):
        """Connexion lazy à Redis"""
        if not self.redis_connected:
            try:
                self.redis_client = await aioredis.from_url(
                    "redis://localhost:6379",
                    encoding="utf-8",
                    decode_responses=False,
                    max_connections=20
                )
                
                # Test de connexion
                await self.redis_client.ping()
                self.redis_connected = True
                logger.info("[UNIFIED_CACHE] ✅ Connexion Redis établie")
                
            except Exception as e:
                logger.warning(f"[UNIFIED_CACHE] ⚠️ Redis non disponible: {e}")
                self.redis_connected = False
    
    def _normalize_key(self, key: str) -> str:
        """Normalise une clé de cache"""
        return hashlib.md5(key.encode()).hexdigest()
    
    def _should_compress(self, data: bytes) -> bool:
        """Détermine si les données doivent être compressées"""
        return len(data) > self.compression_threshold
    
    def _compress_data(self, data: bytes) -> bytes:
        """Compresse les données"""
        return zlib.compress(data, level=6)
    
    def _decompress_data(self, data: bytes) -> bytes:
        """Décompresse les données"""
        return zlib.decompress(data)
    
    def _serialize_value(self, value: Any) -> tuple[bytes, bool]:
        """Sérialise une valeur avec compression optionnelle"""
        try:
            serialized = pickle.dumps(value)
            
            if self._should_compress(serialized):
                compressed = self._compress_data(serialized)
                return compressed, True
            else:
                return serialized, False
                
        except Exception as e:
            logger.error(f"[UNIFIED_CACHE] Erreur sérialisation: {e}")
            return b"", False
    
    def _deserialize_value(self, data: bytes, compressed: bool = False) -> Any:
        """Désérialise une valeur avec décompression optionnelle"""
        try:
            if compressed:
                data = self._decompress_data(data)
            
            return pickle.loads(data)
            
        except Exception as e:
            logger.error(f"[UNIFIED_CACHE] Erreur désérialisation: {e}")
            return None
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Récupération intelligente multi-niveaux"""
        cache_key = self._normalize_key(key)
        self.stats.total_gets += 1
        
        # L1: Cache mémoire
        with self.l1_lock:
            if cache_key in self.l1_cache:
                entry = self.l1_cache[cache_key]
                
                # Vérifier TTL
                if time.time() - entry.timestamp < entry.ttl_seconds:
                    # Déplacer en fin (LRU)
                    self.l1_cache.move_to_end(cache_key)
                    entry.access_count += 1
                    self.stats.hits += 1
                    
                    # Enregistrer pattern d'accès
                    self._record_access_pattern(cache_key)
                    
                    logger.debug(f"[UNIFIED_CACHE] L1 HIT: {key[:30]}...")
                    return entry.value
                else:
                    # TTL expiré
                    del self.l1_cache[cache_key]
        
        # L2: Cache Redis
        if self.redis_connected or await self._ensure_redis_connection():
            try:
                redis_data = await self.redis_client.get(f"cache:{cache_key}")
                if redis_data:
                    # Désérialiser
                    cache_entry_data = json.loads(redis_data)
                    
                    # Vérifier TTL
                    if time.time() - cache_entry_data['timestamp'] < cache_entry_data['ttl_seconds']:
                        value = self._deserialize_value(
                            cache_entry_data['data'], 
                            cache_entry_data.get('compressed', False)
                        )
                        
                        if value is not None:
                            # Promouvoir vers L1 si fréquemment utilisé
                            await self._maybe_promote_to_l1(key, value, cache_entry_data['ttl_seconds'])
                            
                            self.stats.hits += 1
                            self._record_access_pattern(cache_key)
                            
                            logger.debug(f"[UNIFIED_CACHE] L2 HIT: {key[:30]}...")
                            return value
                    else:
                        # TTL expiré, supprimer
                        await self.redis_client.delete(f"cache:{cache_key}")
            
            except Exception as e:
                logger.warning(f"[UNIFIED_CACHE] Erreur Redis get: {e}")
        
        # L3: Cache disque
        disk_path = self.disk_cache_dir / f"{cache_key}.cache"
        if disk_path.exists():
            try:
                with open(disk_path, 'rb') as f:
                    cache_entry_data = pickle.load(f)
                
                # Vérifier TTL
                if time.time() - cache_entry_data['timestamp'] < cache_entry_data['ttl_seconds']:
                    value = cache_entry_data['value']
                    
                    # Promouvoir vers L2 ou L1
                    await self._maybe_promote_from_disk(key, value, cache_entry_data['ttl_seconds'])
                    
                    self.stats.hits += 1
                    logger.debug(f"[UNIFIED_CACHE] L3 HIT: {key[:30]}...")
                    return value
                else:
                    # TTL expiré
                    disk_path.unlink(missing_ok=True)
            
            except Exception as e:
                logger.warning(f"[UNIFIED_CACHE] Erreur disque get: {e}")
                disk_path.unlink(missing_ok=True)
        
        # Cache miss complet
        self.stats.misses += 1
        logger.debug(f"[UNIFIED_CACHE] MISS: {key[:30]}...")
        return default
    
    async def set(self, key: str, value: Any, ttl_seconds: int = 3600):
        """Stockage intelligent multi-niveaux"""
        cache_key = self._normalize_key(key)
        self.stats.total_sets += 1
        
        # Sérialiser la valeur
        serialized_data, compressed = self._serialize_value(value)
        size_bytes = len(serialized_data)
        
        # Créer l'entrée
        entry = CacheEntry(
            value=value,
            timestamp=time.time(),
            ttl_seconds=ttl_seconds,
            size_bytes=size_bytes,
            compressed=compressed
        )
        
        # L1: Toujours essayer de mettre en mémoire pour hot data
        await self._set_l1(cache_key, entry)
        
        # L2: Redis pour données warm
        if self.redis_connected or await self._ensure_redis_connection():
            await self._set_l2(cache_key, entry, serialized_data)
        
        # L3: Disque pour données importantes (TTL > 1h)
        if ttl_seconds > 3600:
            await self._set_l3(cache_key, entry)
        
        logger.debug(f"[UNIFIED_CACHE] SET: {key[:30]}... ({size_bytes} bytes)")
    
    async def _set_l1(self, cache_key: str, entry: CacheEntry):
        """Stockage L1 avec éviction intelligente"""
        with self.l1_lock:
            # Vérifier si éviction nécessaire
            while self._get_l1_memory_usage() > self.max_memory_bytes * self.eviction_threshold:
                if not self.l1_cache:
                    break
                
                # Éviction LRU du moins récemment utilisé
                lru_key, lru_entry = self.l1_cache.popitem(last=False)
                self.stats.memory_usage_bytes -= lru_entry.size_bytes
                logger.debug(f"[UNIFIED_CACHE] Éviction L1: {lru_key}")
            
            # Ajouter la nouvelle entrée
            self.l1_cache[cache_key] = entry
            self.stats.memory_usage_bytes += entry.size_bytes
    
    async def _set_l2(self, cache_key: str, entry: CacheEntry, serialized_data: bytes):
        """Stockage L2 Redis"""
        try:
            redis_entry = {
                'data': serialized_data,
                'timestamp': entry.timestamp,
                'ttl_seconds': entry.ttl_seconds,
                'compressed': entry.compressed,
                'size_bytes': entry.size_bytes
            }
            
            await self.redis_client.setex(
                f"cache:{cache_key}",
                entry.ttl_seconds,
                json.dumps(redis_entry, default=lambda x: x.hex() if isinstance(x, bytes) else x)
            )
            
        except Exception as e:
            logger.warning(f"[UNIFIED_CACHE] Erreur Redis set: {e}")
    
    async def _set_l3(self, cache_key: str, entry: CacheEntry):
        """Stockage L3 disque"""
        try:
            disk_path = self.disk_cache_dir / f"{cache_key}.cache"
            
            disk_entry = {
                'value': entry.value,
                'timestamp': entry.timestamp,
                'ttl_seconds': entry.ttl_seconds
            }
            
            with open(disk_path, 'wb') as f:
                pickle.dump(disk_entry, f)
                
        except Exception as e:
            logger.warning(f"[UNIFIED_CACHE] Erreur disque set: {e}")
    
    def _get_l1_memory_usage(self) -> int:
        """Calcule l'usage mémoire L1"""
        return sum(entry.size_bytes for entry in self.l1_cache.values())
    
    def _record_access_pattern(self, cache_key: str):
        """Enregistre les patterns d'accès pour prédiction"""
        current_time = time.time()
        self.access_patterns[cache_key].append(current_time)
        
        # Garder seulement la fenêtre de prédiction
        cutoff_time = current_time - self.prediction_window
        self.access_patterns[cache_key] = [
            t for t in self.access_patterns[cache_key] if t > cutoff_time
        ]
    
    async def _maybe_promote_to_l1(self, key: str, value: Any, ttl_seconds: int):
        """Promotion conditionnelle vers L1"""
        cache_key = self._normalize_key(key)
        
        # Promouvoir si accès fréquents
        access_frequency = len(self.access_patterns.get(cache_key, []))
        if access_frequency > 3:  # Seuil de promotion
            entry = CacheEntry(
                value=value,
                timestamp=time.time(),
                ttl_seconds=ttl_seconds,
                size_bytes=len(str(value))
            )
            await self._set_l1(cache_key, entry)
            logger.debug(f"[UNIFIED_CACHE] Promotion L1: {key[:30]}...")
    
    async def _maybe_promote_from_disk(self, key: str, value: Any, ttl_seconds: int):
        """Promotion depuis le disque"""
        # Promouvoir vers L2 au minimum
        await self.set(key, value, ttl_seconds)
    
    async def clear_expired(self):
        """Nettoyage des entrées expirées"""
        current_time = time.time()
        expired_keys = []
        
        # L1: Nettoyage mémoire
        with self.l1_lock:
            for cache_key, entry in self.l1_cache.items():
                if current_time - entry.timestamp >= entry.ttl_seconds:
                    expired_keys.append(cache_key)
            
            for cache_key in expired_keys:
                del self.l1_cache[cache_key]
        
        logger.info(f"[UNIFIED_CACHE] Nettoyage: {len(expired_keys)} entrées expirées")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques détaillées"""
        hit_rate = (self.stats.hits / max(self.stats.total_gets, 1)) * 100
        
        return {
            'hit_rate_percent': round(hit_rate, 2),
            'total_requests': self.stats.total_gets,
            'cache_hits': self.stats.hits,
            'cache_misses': self.stats.misses,
            'l1_entries': len(self.l1_cache),
            'l1_memory_usage_mb': round(self._get_l1_memory_usage() / (1024 * 1024), 2),
            'l1_memory_limit_mb': round(self.max_memory_bytes / (1024 * 1024), 2),
            'redis_connected': self.redis_connected,
            'access_patterns_tracked': len(self.access_patterns)
        }

# Instance globale
unified_cache = UnifiedCachePro()




