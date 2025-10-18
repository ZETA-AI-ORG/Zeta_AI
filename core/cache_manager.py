import redis
import os
import hashlib
from dotenv import load_dotenv
from utils import log3

load_dotenv()

class CacheManager:
    def delete_pattern(self, pattern):
        # Suppression de toutes les clés correspondant au motif (pattern) dans Redis
        if hasattr(self, 'client') and self.client:
            keys = self.client.keys(pattern)
            if keys:
                self.client.delete(*keys)

    """Gestionnaire de cache Redis avec expiration (TTL) par défaut."""
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(CacheManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'client'):
            try:
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
                self.client = redis.from_url(redis_url, decode_responses=True)
                self.client.ping()
                log3("[CACHE]", "Connexion à Redis établie avec succès.")
            except Exception as e:
                log3("[CACHE ERROR]", f"Impossible de se connecter à Redis: {e}")
                self.client = None

    def set(self, key: str, value: str, ttl_seconds: int = 86400):
        """Stocke une valeur dans le cache avec un TTL (par défaut 24h)."""
        if self.client:
            # Sécurité : refuser None ou valeur vide (str, dict, list)
            is_empty = False
            if value is None:
                is_empty = True
            elif isinstance(value, str) and (not value.strip()):
                is_empty = True
            elif isinstance(value, (dict, list)) and not value:
                is_empty = True
            if is_empty:
                log3("[CACHE WARNING]", f"Tentative d'écriture d'une valeur vide/None pour la clé '{key}'. Opération ignorée.")
                return
            try:
                self.client.set(key, value, ex=ttl_seconds)
            except Exception as e:
                log3("[CACHE ERROR]", f"Échec de l'écriture pour la clé '{key}': {e}")

    def get(self, key: str):
        """Récupère une valeur depuis le cache."""
        if self.client:
            try:
                return self.client.get(key)
            except Exception as e:
                log3("[CACHE ERROR]", f"Échec de la lecture pour la clé '{key}': {e}")
        return None

    def delete(self, key: str):
        """Supprime une clé spécifique du cache."""
        if self.client:
            try:
                self.client.delete(key)
            except Exception as e:
                log3("[CACHE ERROR]", f"Échec de la suppression pour la clé '{key}': {e}")

    def generic_get(self, key: str):
        """Alias pour get() - utilisé par les agents pour compatibilité."""
        return self.get(key)
    
    def generic_set(self, key: str, value, ttl: int = 86400):
        """Alias pour set() avec support JSON - utilisé par les agents."""
        import json
        is_empty = False
        if value is None:
            is_empty = True
        elif isinstance(value, str) and (not value.strip()):
            is_empty = True
        elif isinstance(value, (dict, list)) and not value:
            is_empty = True
        if is_empty:
            log3("[CACHE WARNING]", f"Tentative d'écriture d'une valeur vide/None pour la clé '{key}'. Opération ignorée.")
            return
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        self.set(key, str(value), ttl)
    
    def make_key(self, prefix: str, content: str, company_id: str) -> str:
        """Crée une clé de cache déterministe avec un hash du contenu."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        return f"cache:{prefix}:{company_id}:{content_hash}"

    def flush_all(self):
        """Vide l'intégralité du cache Redis."""
        if self.client:
            try:
                self.client.flushdb()
                log3("[CACHE]", "Cache Redis entièrement vidé.")
                return True
            except Exception as e:
                log3("[CACHE ERROR]", f"Échec du vidage du cache: {e}")
        return False

# Instance globale pour un accès facile dans toute l'application
cache_manager = CacheManager()
