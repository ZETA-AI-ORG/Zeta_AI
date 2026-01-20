"""
🚀 CACHE GLOBAL PERSISTANT POUR MODÈLES D'EMBEDDING
Solution innovante pour éviter les rechargements de modèles entre modules
Architecture singleton thread-safe avec cache disque optionnel
"""
import os
import pickle
import asyncio
import threading
from typing import Optional, Dict, List
from pathlib import Path
import tempfile
import hashlib

from sentence_transformers import SentenceTransformer
from utils import log3, timing_metric


class GlobalEmbeddingCache:
    """
    🎯 CACHE GLOBAL PERSISTANT POUR MODÈLES D'EMBEDDING
    
    Fonctionnalités :
    - Singleton thread-safe pour éviter les rechargements
    - Cache disque optionnel pour persistance entre redémarrages
    - Cache mémoire pour les embeddings calculés
    - Métriques de performance détaillées
    - Support multi-modèles
    """
    
    _instance: Optional['GlobalEmbeddingCache'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        self.models: Dict[str, SentenceTransformer] = {}
        self.embedding_cache: Dict[str, List[float]] = {}
        self.cache_stats = {
            'model_loads': 0,
            'model_reuses': 0,
            'embedding_hits': 0,
            'embedding_misses': 0
        }
        
        # Configuration du cache disque - DÉSACTIVÉ pour performance
        self.cache_dir = Path(tempfile.gettempdir()) / "chatbot_embedding_cache"
        self.cache_dir.mkdir(exist_ok=True)
        self.disk_cache_enabled = os.getenv("EMBEDDING_DISK_CACHE", "false").lower() == "true"
        
        log3("[GLOBAL_EMBEDDING_CACHE]", "✅ Cache global initialisé")
    
    def _get_model_cache_path(self, model_name: str) -> Path:
        """Génère le chemin de cache disque pour un modèle"""
        model_hash = hashlib.md5(model_name.encode()).hexdigest()[:8]
        return self.cache_dir / f"model_{model_hash}.pkl"
    
    def _get_embedding_cache_path(self) -> Path:
        """Génère le chemin de cache disque pour les embeddings"""
        return self.cache_dir / "embeddings_cache.pkl"
    
    async def _load_model_from_disk(self, model_name: str) -> Optional[SentenceTransformer]:
        """Charge un modèle depuis le cache disque"""
        if not self.disk_cache_enabled:
            return None
            
        cache_path = self._get_model_cache_path(model_name)
        if not cache_path.exists():
            return None
        
        try:
            log3("[GLOBAL_EMBEDDING_CACHE]", f"🔄 Chargement modèle depuis cache disque: {model_name}")
            loop = asyncio.get_event_loop()
            
            def load_from_pickle():
                with open(cache_path, 'rb') as f:
                    return pickle.load(f)
            
            model = await loop.run_in_executor(None, load_from_pickle)
            log3("[GLOBAL_EMBEDDING_CACHE]", f"✅ Modèle chargé depuis cache disque: {model_name}")
            return model
            
        except Exception as e:
            log3("[GLOBAL_EMBEDDING_CACHE]", f"⚠️ Erreur chargement cache disque {model_name}: {e}")
            # Supprimer le cache corrompu
            try:
                cache_path.unlink()
            except:
                pass
            return None
    
    async def _save_model_to_disk(self, model_name: str, model: SentenceTransformer):
        """Sauvegarde un modèle vers le cache disque"""
        if not self.disk_cache_enabled:
            return
            
        cache_path = self._get_model_cache_path(model_name)
        
        try:
            log3("[GLOBAL_EMBEDDING_CACHE]", f"💾 Sauvegarde modèle vers cache disque: {model_name}")
            loop = asyncio.get_event_loop()
            
            def save_to_pickle():
                with open(cache_path, 'wb') as f:
                    pickle.dump(model, f)
            
            await loop.run_in_executor(None, save_to_pickle)
            log3("[GLOBAL_EMBEDDING_CACHE]", f"✅ Modèle sauvegardé vers cache disque: {model_name}")
            
        except Exception as e:
            log3("[GLOBAL_EMBEDDING_CACHE]", f"⚠️ Erreur sauvegarde cache disque {model_name}: {e}")
    
    async def load_embeddings_from_disk(self):
        """Charge les embeddings depuis le cache disque"""
        if not self.disk_cache_enabled:
            return
            
        cache_path = self._get_embedding_cache_path()
        if not cache_path.exists():
            return
        
        try:
            log3("[GLOBAL_EMBEDDING_CACHE]", "🔄 Chargement embeddings depuis cache disque")
            loop = asyncio.get_event_loop()
            
            def load_embeddings():
                with open(cache_path, 'rb') as f:
                    return pickle.load(f)
            
            cached_embeddings = await loop.run_in_executor(None, load_embeddings)
            self.embedding_cache.update(cached_embeddings)
            log3("[GLOBAL_EMBEDDING_CACHE]", f"✅ {len(cached_embeddings)} embeddings chargés depuis cache disque")
            
        except Exception as e:
            log3("[GLOBAL_EMBEDDING_CACHE]", f"⚠️ Erreur chargement embeddings cache disque: {e}")
    
    async def save_embeddings_to_disk(self):
        """Sauvegarde les embeddings vers le cache disque"""
        if not self.disk_cache_enabled or not self.embedding_cache:
            return
            
        cache_path = self._get_embedding_cache_path()
        
        try:
            log3("[GLOBAL_EMBEDDING_CACHE]", f"💾 Sauvegarde {len(self.embedding_cache)} embeddings vers cache disque")
            loop = asyncio.get_event_loop()
            
            def save_embeddings():
                with open(cache_path, 'wb') as f:
                    pickle.dump(self.embedding_cache, f)
            
            await loop.run_in_executor(None, save_embeddings)
            log3("[GLOBAL_EMBEDDING_CACHE]", "✅ Embeddings sauvegardés vers cache disque")
            
        except Exception as e:
            log3("[GLOBAL_EMBEDDING_CACHE]", f"⚠️ Erreur sauvegarde embeddings cache disque: {e}")
    
    def get_model(self, model_name: str = "sentence-transformers/all-mpnet-base-v2") -> SentenceTransformer:
        """
        Obtient un modèle d'embedding avec cache global persistant
        
        Args:
            model_name: Nom du modèle SentenceTransformer
            
        Returns:
            Instance du modèle SentenceTransformer
        """
        # Vérification cache mémoire
        if model_name in self.models:
            self.cache_stats['model_reuses'] += 1
            log3("[GLOBAL_EMBEDDING_CACHE]", f"✅ Modèle réutilisé depuis cache mémoire: {model_name}")
            return self.models[model_name]
        
        # Chargement direct depuis HuggingFace (optimisé)
        log3("[GLOBAL_EMBEDDING_CACHE]", f"🔄 Chargement modèle depuis HuggingFace: {model_name}")
        model = SentenceTransformer(model_name)
        
        # Mise en cache mémoire
        self.models[model_name] = model
        self.cache_stats['model_loads'] += 1
        
        log3("[GLOBAL_EMBEDDING_CACHE]", f"✅ Modèle chargé et mis en cache: {model_name}")
        return model
    
    @timing_metric("global_embedding_generation")
    async def get_embedding(self, text: str, model_name: str = "sentence-transformers/all-mpnet-base-v2") -> List[float]:
        """
        Génère un embedding avec cache global
        
        Args:
            text: Texte à encoder
            model_name: Nom du modèle à utiliser
            
        Returns:
            Vecteur d'embedding normalisé
        """
        # Clé de cache unique
        cache_key = f"{model_name}:{hashlib.md5(text.encode()).hexdigest()}"
        
        # Vérification cache embeddings
        if cache_key in self.embedding_cache:
            self.cache_stats['embedding_hits'] += 1
            log3("[GLOBAL_EMBEDDING_CACHE]", f"✅ Embedding cache hit: {text[:50]}...")
            return self.embedding_cache[cache_key]
        
        # Génération embedding
        self.cache_stats['embedding_misses'] += 1
        model = self.get_model(model_name)
        
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None,
            lambda: model.encode(text, normalize_embeddings=True).tolist()
        )
        
        # Mise en cache avec limite de mémoire (max 50000 embeddings pour performance)
        if len(self.embedding_cache) >= 50000:
            # Suppression du plus ancien (FIFO simple)
            oldest_key = next(iter(self.embedding_cache))
            del self.embedding_cache[oldest_key]
        
        self.embedding_cache[cache_key] = embedding
        
        log3("[GLOBAL_EMBEDDING_CACHE]", f"✅ Embedding généré et mis en cache: {text[:50]}...")
        return embedding
    
    def get_stats(self) -> Dict:
        """Retourne les statistiques du cache"""
        total_model_requests = self.cache_stats['model_loads'] + self.cache_stats['model_reuses']
        total_embedding_requests = self.cache_stats['embedding_hits'] + self.cache_stats['embedding_misses']
        
        return {
            'models_loaded': len(self.models),
            'embeddings_cached': len(self.embedding_cache),
            'model_hit_rate': (self.cache_stats['model_reuses'] / max(total_model_requests, 1)) * 100,
            'embedding_hit_rate': (self.cache_stats['embedding_hits'] / max(total_embedding_requests, 1)) * 100,
            'cache_stats': self.cache_stats.copy(),
            'disk_cache_enabled': self.disk_cache_enabled,
            'cache_dir': str(self.cache_dir)
        }
    
    async def cleanup(self):
        """Nettoyage et sauvegarde finale"""
        log3("[GLOBAL_EMBEDDING_CACHE]", "🧹 Nettoyage du cache global...")
        await self.save_embeddings_to_disk()
        
        stats = self.get_stats()
        log3("[GLOBAL_EMBEDDING_CACHE]", f"📊 Statistiques finales: {stats}")


# Instance globale singleton
_global_cache: Optional[GlobalEmbeddingCache] = None

def get_global_embedding_cache() -> GlobalEmbeddingCache:
    """Factory pour obtenir l'instance globale du cache"""
    global _global_cache
    if _global_cache is None:
        _global_cache = GlobalEmbeddingCache()
    return _global_cache


# API simplifiée pour compatibilité
def get_cached_model(model_name: str = "sentence-transformers/all-mpnet-base-v2") -> SentenceTransformer:
    """API simplifiée pour obtenir un modèle mis en cache"""
    cache = get_global_embedding_cache()
    return cache.get_model(model_name)


async def get_cached_embedding(text: str, model_name: str = "sentence-transformers/all-mpnet-base-v2") -> List[float]:
    """API simplifiée pour obtenir un embedding mis en cache"""
    cache = get_global_embedding_cache()
    return await cache.get_embedding(text, model_name)


async def initialize_global_cache():
    """Initialise le cache global au démarrage de l'application"""
    cache = get_global_embedding_cache()
    await cache.load_embeddings_from_disk()
    log3("[GLOBAL_EMBEDDING_CACHE]", "🚀 Cache global initialisé et prêt")


async def cleanup_global_cache():
    """Nettoie le cache global à l'arrêt de l'application"""
    cache = get_global_embedding_cache()
    await cache.cleanup()
