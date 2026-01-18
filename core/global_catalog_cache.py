import os
import threading
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Dict, Optional


class GlobalCatalogCache:
    def __init__(self, default_ttl_minutes: int = 30):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = timedelta(minutes=default_ttl_minutes)
        self.lock = threading.RLock()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "invalidations": 0,
        }

    def _create_cache_key(self, company_id: str) -> str:
        return f"catalog_{company_id}"

    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        try:
            return datetime.now() > entry["expires_at"]
        except Exception:
            return True

    async def get_catalog(
        self,
        company_id: str,
        builder: Callable[[], Awaitable[Dict[str, Any]]],
        ttl_minutes: Optional[int] = None,
    ) -> Dict[str, Any]:
        cache_key = self._create_cache_key(company_id)

        with self.lock:
            entry = self.cache.get(cache_key)
            if entry and (not self._is_expired(entry)):
                self.stats["hits"] += 1
                entry["access_count"] = int(entry.get("access_count", 0)) + 1
                return entry.get("catalog") or {}

        self.stats["misses"] += 1
        catalog = await builder()
        if not isinstance(catalog, dict):
            return {}

        ttl_env = os.getenv("CATALOG_CACHE_TTL_MINUTES")
        ttl_final: Optional[int] = ttl_minutes
        if ttl_final is None and ttl_env is not None:
            try:
                ttl_final = int(str(ttl_env).strip())
            except Exception:
                ttl_final = None

        ttl = timedelta(minutes=ttl_final) if ttl_final else self.default_ttl
        expires_at = datetime.now() + ttl

        with self.lock:
            self.cache[cache_key] = {
                "catalog": catalog,
                "cached_at": datetime.now(),
                "expires_at": expires_at,
                "company_id": company_id,
                "access_count": 0,
            }

        return catalog

    async def invalidate_catalog(self, company_id: str) -> bool:
        cache_key = self._create_cache_key(company_id)
        with self.lock:
            if cache_key in self.cache:
                del self.cache[cache_key]
                self.stats["invalidations"] += 1
                return True
        return False

    def clear_expired(self) -> int:
        removed = 0
        now = datetime.now()
        with self.lock:
            for key in list(self.cache.keys()):
                entry = self.cache.get(key)
                if entry and now > entry.get("expires_at", now):
                    del self.cache[key]
                    removed += 1
                    self.stats["invalidations"] += 1
        return removed

    def get_stats(self) -> Dict[str, Any]:
        with self.lock:
            total_requests = int(self.stats.get("hits", 0)) + int(self.stats.get("misses", 0))
            hit_rate = (self.stats.get("hits", 0) / total_requests * 100) if total_requests > 0 else 0.0
            return {
                "cache_size": len(self.cache),
                "total_requests": total_requests,
                "hits": self.stats.get("hits", 0),
                "misses": self.stats.get("misses", 0),
                "hit_rate_percent": f"{hit_rate:.1f}%",
                "invalidations": self.stats.get("invalidations", 0),
            }


_global_catalog_cache: Optional[GlobalCatalogCache] = None


def get_global_catalog_cache() -> GlobalCatalogCache:
    global _global_catalog_cache
    if _global_catalog_cache is None:
        ttl_env = os.getenv("CATALOG_CACHE_DEFAULT_TTL_MINUTES")
        ttl_minutes = 30
        if ttl_env is not None:
            try:
                ttl_minutes = int(str(ttl_env).strip())
            except Exception:
                ttl_minutes = 30
        _global_catalog_cache = GlobalCatalogCache(default_ttl_minutes=ttl_minutes)
    return _global_catalog_cache
