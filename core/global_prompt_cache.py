#!/usr/bin/env python3
"""
🚀 CACHE PROMPT GLOBAL SCALABLE
Objectif: Réduire le temps de récupération des prompts de 2.1s à 0.01s
Architecture: Cache en mémoire avec TTL et invalidation intelligente
"""

import asyncio
import time
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import threading
from utils import log3

class GlobalPromptCache:
    """
    🚀 Cache global des prompts d'entreprise avec gestion intelligente
    - Cache en mémoire avec TTL
    - Invalidation automatique
    - Thread-safe pour multi-entreprise
    - Préchargement intelligent
    """
    
    def __init__(self, default_ttl_minutes: int = 30):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = timedelta(minutes=default_ttl_minutes)
        self.lock = threading.RLock()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "invalidations": 0,
            "preloads": 0
        }
        
        log3("[PROMPT_CACHE]", "🚀 Cache prompt global initialisé")
    
    def _is_expired(self, cache_entry: Dict[str, Any]) -> bool:
        """Vérifie si une entrée de cache est expirée"""
        return datetime.now() > cache_entry["expires_at"]
    
    def clear_expired(self) -> int:
        """🧹 Supprime les entrées expirées et retourne le nombre nettoyé"""
        removed = 0
        now = datetime.now()
        with self.lock:
            # Créer une liste de clés pour éviter de modifier le dict durant l'itération
            for key in list(self.cache.keys()):
                try:
                    entry = self.cache.get(key)
                    if entry and now > entry.get("expires_at", now):
                        del self.cache[key]
                        removed += 1
                        self.stats["invalidations"] += 1
                except Exception:
                    # Tolérant aux erreurs pour ne pas interrompre le cycle de nettoyage
                    continue
        log3("[PROMPT_CACHE]", f"🧹 Expirés nettoyés: {removed}")
        return removed
    
    def _create_cache_key(self, company_id: str) -> str:
        """Crée une clé de cache standardisée"""
        return f"prompt_{company_id}"
    
    async def get_prompt(self, company_id: str) -> Optional[str]:
        """
        🎯 Récupère le prompt depuis le cache ou la base de données
        Retourne None si non trouvé
        """
        cache_key = self._create_cache_key(company_id)
        
        with self.lock:
            # Vérifier le cache
            if cache_key in self.cache:
                cache_entry = self.cache[cache_key]
                
                if not self._is_expired(cache_entry):
                    # Cache hit ! - LOG SIMPLIFIÉ
                    self.stats["hits"] += 1
                    cache_entry["access_count"] += 1
                    log3("[PROMPT_CACHE]", f"✅ Hit: {company_id[:8]}... | {len(cache_entry['prompt'])} chars")
                    return cache_entry["prompt"]
                else:
                    # Entrée expirée
                    del self.cache[cache_key]
                    self.stats["invalidations"] += 1
        
        # Cache miss - récupérer depuis la base
        self.stats["misses"] += 1
        log3("[PROMPT_CACHE]", f"❌ Miss: {company_id[:8]}...")
        
        # Récupérer depuis Supabase
        prompt = await self._fetch_from_database(company_id)
        
        if prompt:
            await self.set_prompt(company_id, prompt)
            return prompt
        
        return None
    
    async def _fetch_from_database(self, company_id: str) -> Optional[str]:
        """Récupère le prompt depuis la base de données"""
        try:
            # IMPORTANT: utiliser la fonction de fetch direct pour éviter la récursion
            # get_company_system_prompt() appelle déjà le cache unifié, ce qui créerait une boucle
            from database.supabase_client import _fetch_prompt_from_database as direct_fetch
            
            start_time = time.time()
            prompt = await direct_fetch(company_id)
            fetch_time = (time.time() - start_time) * 1000
            
            # LOG SIMPLIFIÉ - Une seule ligne
            log3("[PROMPT_CACHE]", f"📥 DB fetch: {company_id[:8]}... | {fetch_time:.0f}ms | {len(prompt) if prompt else 0} chars")
            
            return prompt if prompt and len(prompt.strip()) > 0 else None
            
        except Exception as e:
            log3("[PROMPT_CACHE]", f"❌ DB error: {company_id[:8]}... | {str(e)}")
            return None
    
    async def set_prompt(self, company_id: str, prompt: str, ttl_minutes: Optional[int] = None) -> None:
        """💾 Met en cache un prompt avec TTL personnalisé"""
        if not prompt or len(prompt.strip()) == 0:
            return
        
        cache_key = self._create_cache_key(company_id)
        ttl = timedelta(minutes=ttl_minutes) if ttl_minutes else self.default_ttl
        expires_at = datetime.now() + ttl
        
        with self.lock:
            self.cache[cache_key] = {
                "prompt": prompt,
                "cached_at": datetime.now(),
                "expires_at": expires_at,
                "company_id": company_id,
                "access_count": 0
            }
        
    async def invalidate_prompt(self, company_id: str) -> bool:
        """
        🗑️ Invalide le cache prompt pour une entreprise spécifique
        Force le rechargement depuis la base de données
        """
        cache_key = self._create_cache_key(company_id)

        with self.lock:
            if cache_key in self.cache:
                del self.cache[cache_key]
                self.stats["invalidations"] += 1
                log3("[PROMPT_CACHE]", f"🗑️ Cache invalidé pour {company_id}")
                return True
            else:
                log3("[PROMPT_CACHE]", f"⚠️ Aucun cache trouvé pour {company_id}")
                return False

    async def clear_all_prompts(self) -> int:
        """🧹 Vide tout le cache prompt"""
        with self.lock:
            cache_size = len(self.cache)
            self.cache.clear()
            self.stats["invalidations"] += cache_size
            log3("[PROMPT_CACHE]", f"🧹 Tout le cache vidé ({cache_size} entrées)")
            return cache_size
    
    def get_stats(self) -> Dict[str, Any]:
        """📊 Statistiques du cache"""
        with self.lock:
            total_requests = self.stats["hits"] + self.stats["misses"]
            hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "cache_size": len(self.cache),
                "total_requests": total_requests,
                "hits": self.stats["hits"],
                "misses": self.stats["misses"],
                "hit_rate_percent": f"{hit_rate:.1f}%",
                "invalidations": self.stats["invalidations"],
                "preloads": self.stats["preloads"]
            }

# Instance globale
_global_prompt_cache = None

def get_global_prompt_cache() -> GlobalPromptCache:
    """🚀 Singleton pour le cache prompt global"""
    global _global_prompt_cache
    if _global_prompt_cache is None:
        _global_prompt_cache = GlobalPromptCache()
    return _global_prompt_cache
