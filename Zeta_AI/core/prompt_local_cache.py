"""
⚡ PROMPT LOCAL CACHE - Cache en mémoire pour prompts
Évite les appels Supabase répétés (gain ~3s par requête)
"""

import time
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class PromptLocalCache:
    """
    Cache local en mémoire pour les prompts système
    Évite les fetch Supabase répétés
    """
    
    def __init__(self, ttl: int = 3600):
        """
        Args:
            ttl: Time-to-live en secondes (défaut: 1 heure)
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl
        logger.info(f"⚡ [PROMPT_CACHE] Initialisé (TTL: {ttl}s)")
    
    def get(self, company_id: str) -> Optional[str]:
        """
        Récupère un prompt depuis le cache
        
        Args:
            company_id: ID de l'entreprise
            
        Returns:
            Prompt si trouvé et valide, None sinon
        """
        cache_key = f"prompt_{company_id}"
        cached = self.cache.get(cache_key)
        
        if not cached:
            return None
        
        # Vérifier expiration
        age = time.time() - cached['timestamp']
        if age > self.ttl:
            logger.info(f"⚠️ [PROMPT_CACHE] Expiré pour {company_id} (age: {age:.1f}s)")
            del self.cache[cache_key]
            return None
        
        logger.info(f"⚡ [PROMPT_CACHE] HIT pour {company_id} (age: {age:.1f}s)")
        return cached['prompt']
    
    def set(self, company_id: str, prompt: str):
        """
        Sauvegarde un prompt dans le cache
        
        Args:
            company_id: ID de l'entreprise
            prompt: Contenu du prompt
        """
        cache_key = f"prompt_{company_id}"
        self.cache[cache_key] = {
            'prompt': prompt,
            'timestamp': time.time()
        }
        logger.info(f"💾 [PROMPT_CACHE] Sauvegardé pour {company_id} ({len(prompt)} chars)")
    
    def invalidate(self, company_id: str):
        """
        Invalide le cache pour une entreprise
        
        Args:
            company_id: ID de l'entreprise
        """
        cache_key = f"prompt_{company_id}"
        if cache_key in self.cache:
            del self.cache[cache_key]
            logger.info(f"🗑️ [PROMPT_CACHE] Invalidé pour {company_id}")
    
    def clear(self):
        """Vide tout le cache"""
        self.cache.clear()
        logger.info("🗑️ [PROMPT_CACHE] Cache vidé")
    
    def stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du cache"""
        total_entries = len(self.cache)
        total_size = sum(len(entry['prompt']) for entry in self.cache.values())
        
        return {
            'entries': total_entries,
            'total_size_chars': total_size,
            'ttl': self.ttl
        }


# Singleton global
_prompt_cache_instance: Optional[PromptLocalCache] = None

def get_prompt_cache() -> PromptLocalCache:
    """Retourne l'instance singleton du cache"""
    global _prompt_cache_instance
    if _prompt_cache_instance is None:
        _prompt_cache_instance = PromptLocalCache()
    return _prompt_cache_instance


# ========== FONCTION HELPER POUR INTÉGRATION ==========

async def get_prompt_with_cache(company_id: str, fetch_func) -> str:
    """
    Récupère un prompt avec cache local
    
    Args:
        company_id: ID de l'entreprise
        fetch_func: Fonction async pour fetch depuis Supabase
        
    Returns:
        Prompt (depuis cache ou Supabase)
    """
    cache = get_prompt_cache()
    
    # Essayer le cache d'abord
    cached_prompt = cache.get(company_id)
    if cached_prompt:
        return cached_prompt
    
    # Sinon, fetch depuis Supabase
    logger.info(f"📥 [PROMPT_CACHE] MISS pour {company_id}, fetch Supabase...")
    prompt = await fetch_func(company_id)
    
    # Sauvegarder dans le cache
    if prompt:
        cache.set(company_id, prompt)
    
    return prompt
