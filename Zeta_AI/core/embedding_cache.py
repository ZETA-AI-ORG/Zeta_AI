"""
Cache intelligent pour les embeddings avec Redis et optimisations de performance
"""
import hashlib
import json
import numpy as np
from typing import Optional, List, Union
import redis
import os
from utils import log3

class EmbeddingCache:
    def __init__(self):
        self.redis_client = None
        self.cache_enabled = True
        self._init_redis()
    
    def _init_redis(self):
        """Initialise la connexion Redis avec fallback gracieux"""
        try:
            # Configuration Redis depuis l'environnement ou localhost par défaut
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            redis_db = int(os.getenv('REDIS_DB', 0))
            
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=False,  # Pour stocker les bytes numpy
                socket_timeout=2,
                socket_connect_timeout=2
            )
            
            # Test de connexion
            self.redis_client.ping()
            log3("[EMBEDDING_CACHE]", "✅ Redis connecté pour cache embeddings")
            
        except Exception as e:
            log3("[EMBEDDING_CACHE]", f"⚠️ Redis indisponible, cache désactivé: {e}")
            self.cache_enabled = False
            self.redis_client = None
    
    def _generate_cache_key(self, text: str, model_key: str) -> str:
        """Génère une clé de cache unique basée sur le texte et le modèle"""
        content = f"{model_key}:{text}"
        return f"emb:{hashlib.md5(content.encode()).hexdigest()}"
    
    def get_embedding(self, text: str, model_key: str) -> Optional[np.ndarray]:
        """Récupère un embedding depuis le cache"""
        if not self.cache_enabled or not self.redis_client:
            return None
        
        try:
            cache_key = self._generate_cache_key(text, model_key)
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                # Désérialisation numpy
                embedding = np.frombuffer(cached_data, dtype=np.float32)
                log3("[EMBEDDING_CACHE]", f"✅ Cache hit pour {model_key}")
                return embedding
                
        except Exception as e:
            log3("[EMBEDDING_CACHE]", f"❌ Erreur lecture cache: {e}")
        
        return None
    
    def store_embedding(self, text: str, model_key: str, embedding: np.ndarray, ttl: int = 3600):
        """Stocke un embedding dans le cache avec TTL"""
        if not self.cache_enabled or not self.redis_client:
            return
        
        try:
            cache_key = self._generate_cache_key(text, model_key)
            
            # Sérialisation numpy optimisée
            embedding_bytes = embedding.astype(np.float32).tobytes()
            
            # Stockage avec TTL (1h par défaut)
            self.redis_client.setex(cache_key, ttl, embedding_bytes)
            log3("[EMBEDDING_CACHE]", f"💾 Embedding mis en cache pour {model_key}")
            
        except Exception as e:
            log3("[EMBEDDING_CACHE]", f"❌ Erreur stockage cache: {e}")
    
    def get_batch_embeddings(self, texts: List[str], model_key: str) -> tuple[List[Optional[np.ndarray]], List[str]]:
        """
        Récupère des embeddings en batch depuis le cache
        
        Returns:
            tuple: (embeddings_cachés, textes_manquants)
        """
        if not self.cache_enabled or not self.redis_client:
            return [None] * len(texts), texts
        
        try:
            cache_keys = [self._generate_cache_key(text, model_key) for text in texts]
            cached_data = self.redis_client.mget(cache_keys)
            
            embeddings = []
            missing_texts = []
            
            for i, (text, data) in enumerate(zip(texts, cached_data)):
                if data:
                    embedding = np.frombuffer(data, dtype=np.float32)
                    embeddings.append(embedding)
                else:
                    embeddings.append(None)
                    missing_texts.append(text)
            
            hit_rate = (len(texts) - len(missing_texts)) / len(texts) * 100
            log3("[EMBEDDING_CACHE]", f"📊 Cache batch: {hit_rate:.1f}% hits ({len(texts)-len(missing_texts)}/{len(texts)})")
            
            return embeddings, missing_texts
            
        except Exception as e:
            log3("[EMBEDDING_CACHE]", f"❌ Erreur batch cache: {e}")
            return [None] * len(texts), texts
    
    def store_batch_embeddings(self, texts: List[str], model_key: str, embeddings: List[np.ndarray], ttl: int = 3600):
        """Stocke des embeddings en batch dans le cache"""
        if not self.cache_enabled or not self.redis_client or len(texts) != len(embeddings):
            return
        
        try:
            pipe = self.redis_client.pipeline()
            
            for text, embedding in zip(texts, embeddings):
                cache_key = self._generate_cache_key(text, model_key)
                embedding_bytes = embedding.astype(np.float32).tobytes()
                pipe.setex(cache_key, ttl, embedding_bytes)
            
            pipe.execute()
            log3("[EMBEDDING_CACHE]", f"💾 {len(embeddings)} embeddings mis en cache (batch)")
            
        except Exception as e:
            log3("[EMBEDDING_CACHE]", f"❌ Erreur batch stockage: {e}")

# Instance globale
embedding_cache = EmbeddingCache()
