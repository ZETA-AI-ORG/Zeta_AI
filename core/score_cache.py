"""
⚡ SCORE CACHE - Pré-calcul des scores fréquents
Cache les combinaisons query + doc fréquentes pour éviter recalculs
"""

import hashlib
import json
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Cache en mémoire (simple dict)
_SCORE_CACHE = {}
_CACHE_MAX_SIZE = 1000  # Limiter taille mémoire


def get_score_cache_key(query: str, doc_id: str, company_id: str) -> str:
    """Génère clé de cache unique"""
    combined = f"{company_id}:{query.lower()}:{doc_id}"
    return hashlib.md5(combined.encode()).hexdigest()[:16]


def get_cached_score(query: str, doc_id: str, company_id: str) -> Optional[float]:
    """
    Récupère score depuis cache
    
    Returns:
        Score si trouvé, None sinon
    """
    cache_key = get_score_cache_key(query, doc_id, company_id)
    
    if cache_key in _SCORE_CACHE:
        logger.debug(f"⚡ [SCORE CACHE] Hit pour {cache_key}")
        return _SCORE_CACHE[cache_key]
    
    return None


def set_cached_score(query: str, doc_id: str, company_id: str, score: float):
    """
    Sauvegarde score dans cache
    """
    global _SCORE_CACHE
    
    # Limiter taille cache (FIFO simple)
    if len(_SCORE_CACHE) >= _CACHE_MAX_SIZE:
        # Supprimer 10% des entrées les plus anciennes
        keys_to_remove = list(_SCORE_CACHE.keys())[:int(_CACHE_MAX_SIZE * 0.1)]
        for key in keys_to_remove:
            del _SCORE_CACHE[key]
    
    cache_key = get_score_cache_key(query, doc_id, company_id)
    _SCORE_CACHE[cache_key] = score
    logger.debug(f"💾 [SCORE CACHE] Sauvegardé {cache_key} = {score:.3f}")


def clear_score_cache():
    """Vide le cache"""
    global _SCORE_CACHE
    _SCORE_CACHE = {}
    logger.info("🧹 [SCORE CACHE] Cache vidé")


def get_cache_stats() -> Dict:
    """Statistiques du cache"""
    return {
        "size": len(_SCORE_CACHE),
        "max_size": _CACHE_MAX_SIZE,
        "usage_percent": (len(_SCORE_CACHE) / _CACHE_MAX_SIZE) * 100
    }


# ═══════════════════════════════════════════════════════════
# INTÉGRATION REDIS (optionnel, plus performant)
# ═══════════════════════════════════════════════════════════

def get_cached_score_redis(query: str, doc_id: str, company_id: str) -> Optional[float]:
    """Version Redis du cache (plus scalable)"""
    try:
        import redis
        redis_client = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
        
        cache_key = f"score:{get_score_cache_key(query, doc_id, company_id)}"
        cached = redis_client.get(cache_key)
        
        if cached:
            logger.debug(f"⚡ [SCORE CACHE REDIS] Hit")
            return float(cached)
    except Exception as e:
        logger.debug(f"⚠️ [SCORE CACHE REDIS] Erreur: {e}")
    
    return None


def set_cached_score_redis(query: str, doc_id: str, company_id: str, score: float, ttl: int = 3600):
    """Sauvegarde dans Redis avec TTL"""
    try:
        import redis
        redis_client = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
        
        cache_key = f"score:{get_score_cache_key(query, doc_id, company_id)}"
        redis_client.setex(cache_key, ttl, str(score))
        logger.debug(f"💾 [SCORE CACHE REDIS] Sauvegardé (TTL {ttl}s)")
    except Exception as e:
        logger.debug(f"⚠️ [SCORE CACHE REDIS] Erreur: {e}")


# ═══════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Test cache mémoire
    company_id = "test123"
    query = "Prix couches taille 3"
    doc_id = "doc_456"
    
    # Set
    set_cached_score(query, doc_id, company_id, 0.85)
    
    # Get
    score = get_cached_score(query, doc_id, company_id)
    print(f"Score récupéré: {score}")
    
    # Stats
    stats = get_cache_stats()
    print(f"Stats: {stats}")
    
    # Clear
    clear_score_cache()
    print("Cache vidé")
