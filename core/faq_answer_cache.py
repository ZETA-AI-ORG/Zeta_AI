#!/usr/bin/env python3
"""
🧠 CACHE RÉPONSES FAQ (Redis/mémoire, TTL intelligent)
====================================================
- Optimise le temps de réponse pour les questions fréquentes
- Utilise Redis si disponible, sinon fallback mémoire
- TTL adaptatif (par défaut 1h)
"""
import hashlib
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

class FaqAnswerCache:
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        if REDIS_AVAILABLE:
            self.redis = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        else:
            self.redis = None

    def _make_key(self, question: str, context: str = "") -> str:
        base = (question.strip().lower() + "|" + context.strip().lower())
        return hashlib.sha256(base.encode()).hexdigest()

    def get(self, question: str, context: str = "") -> Optional[str]:
        key = self._make_key(question, context)
        # Redis
        if self.redis:
            value = self.redis.get(key)
            if value:
                self.redis.expire(key, self.ttl_seconds)  # refresh TTL
                return value
        # Mémoire
        entry = self.memory_cache.get(key)
        if entry and entry["expires_at"] > time.time():
            return entry["answer"]
        if entry:
            del self.memory_cache[key]
        return None

    def set(self, question: str, context: str, answer: str, ttl: Optional[int] = None):
        key = self._make_key(question, context)
        ttl_to_use = ttl if ttl else self.ttl_seconds
        # Redis
        if self.redis:
            self.redis.setex(key, ttl_to_use, answer)
        # Mémoire
        self.memory_cache[key] = {
            "answer": answer,
            "expires_at": time.time() + ttl_to_use
        }

    def clear_expired(self):
        now = time.time()
        to_delete = [k for k, v in self.memory_cache.items() if v["expires_at"] < now]
        for k in to_delete:
            del self.memory_cache[k]
        return len(to_delete)

# Singleton global
faq_answer_cache = FaqAnswerCache()
