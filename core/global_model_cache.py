#!/usr/bin/env python3
"""
🚀 CACHE MODÈLE GLOBAL PERSISTANT
Objectif: Éliminer le rechargement du modèle (8.3s → 0s)
Architecture: Singleton persistant avec gestion mémoire intelligente
"""

import time
import threading
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import gc
import psutil
import os
from utils import log3

class GlobalModelCache:
    """
    🚀 Cache persistant des modèles d'embedding
    - Singleton global pour éviter les rechargements
    - Gestion intelligente de la mémoire
    - Monitoring des ressources système
    - Préchargement automatique des modèles populaires
    """
    
    def __init__(self, memory_threshold_percent: float = 85.0):
        self.models: Dict[str, Any] = {}
        self.model_stats: Dict[str, Dict[str, Any]] = {}
        self.memory_threshold = memory_threshold_percent
        self.lock = threading.RLock()
        self.last_cleanup = datetime.now()
        self.cleanup_interval = timedelta(minutes=30)
        
        log3("[MODEL_CACHE]", "🚀 Cache modèle global initialisé")
    
    def _get_memory_usage(self) -> float:
        """Retourne l'usage mémoire actuel en pourcentage"""
        try:
            return psutil.virtual_memory().percent
        except Exception:
            return 0.0
    
    def _should_cleanup(self) -> bool:
        """Détermine si un nettoyage mémoire est nécessaire"""
        memory_usage = self._get_memory_usage()
        time_for_cleanup = datetime.now() - self.last_cleanup > self.cleanup_interval
        
        return memory_usage > self.memory_threshold or time_for_cleanup
    
    def _cleanup_unused_models(self) -> int:
        """
        🧹 Nettoie les modèles peu utilisés pour libérer la mémoire
        Garde les modèles les plus utilisés récemment
        """
        if len(self.models) <= 1:
            return 0  # Garder au moins un modèle
        
        removed_count = 0
        current_time = datetime.now()
        
        with self.lock:
            # Trier par dernière utilisation
            sorted_models = sorted(
                self.model_stats.items(),
                key=lambda x: x[1]["last_used"]
            )
            
            # Supprimer les modèles les moins utilisés (garder les 2 plus récents)
            models_to_remove = sorted_models[:-2] if len(sorted_models) > 2 else []
            
            for model_name, stats in models_to_remove:
                if model_name in self.models:
                    # Vérifier si pas utilisé récemment (> 1 heure)
                    time_since_use = current_time - stats["last_used"]
                    if time_since_use > timedelta(hours=1):
                        del self.models[model_name]
                        del self.model_stats[model_name]
                        removed_count += 1
                        
                        log3("[MODEL_CACHE]", {
                            "action": "model_removed",
                            "model_name": model_name,
                            "unused_hours": time_since_use.total_seconds() / 3600
                        })
        
        if removed_count > 0:
            # Forcer le garbage collection
            gc.collect()
            
            log3("[MODEL_CACHE]", {
                "action": "cleanup_complete",
                "removed_count": removed_count,
                "memory_after": f"{self._get_memory_usage():.1f}%"
            })
        
        self.last_cleanup = current_time
        return removed_count
    
    def get_model(self, model_name: str = "sentence-transformers/all-mpnet-base-v2"):
        """
        🎯 Récupère un modèle depuis le cache ou le charge
        Retourne le modèle prêt à utiliser
        """
        # Nettoyage préventif si nécessaire
        if self._should_cleanup():
            self._cleanup_unused_models()
        
        with self.lock:
            # Cache hit - modèle déjà en mémoire
            if model_name in self.models:
                # Mettre à jour les statistiques
                self.model_stats[model_name]["access_count"] += 1
                self.model_stats[model_name]["last_used"] = datetime.now()
                
                log3("[MODEL_CACHE]", {
                    "action": "model_cache_hit",
                    "model_name": model_name,
                    "access_count": self.model_stats[model_name]["access_count"],
                    "memory_usage": f"{self._get_memory_usage():.1f}%"
                })
                
                return self.models[model_name]
        
        # Cache miss - charger le modèle
        log3("[MODEL_CACHE]", {
            "action": "model_cache_miss",
            "model_name": model_name,
            "loading_start": True
        })
        
        model = self._load_model(model_name)
        
        if model is not None:
            with self.lock:
                self.models[model_name] = model
                self.model_stats[model_name] = {
                    "loaded_at": datetime.now(),
                    "last_used": datetime.now(),
                    "access_count": 1,
                    "model_size_mb": self._estimate_model_size(model)
                }
            
            log3("[MODEL_CACHE]", {
                "action": "model_loaded",
                "model_name": model_name,
                "estimated_size_mb": self.model_stats[model_name]["model_size_mb"],
                "total_models_cached": len(self.models),
                "memory_usage": f"{self._get_memory_usage():.1f}%"
            })
        
        return model
    
    def _load_model(self, model_name: str):
        """Charge un modèle depuis HuggingFace"""
        try:
            start_time = time.time()
            
            # Import dynamique pour éviter les dépendances circulaires
            from sentence_transformers import SentenceTransformer
            
            log3("[MODEL_CACHE]", {
                "action": "loading_from_huggingface",
                "model_name": model_name
            })
            
            model = SentenceTransformer(model_name)
            
            load_time = time.time() - start_time
            log3("[MODEL_CACHE]", {
                "action": "model_load_complete",
                "model_name": model_name,
                "load_time_seconds": f"{load_time:.2f}"
            })
            
            return model
            
        except Exception as e:
            log3("[MODEL_CACHE]", {
                "action": "model_load_error",
                "model_name": model_name,
                "error": str(e)
            })
            return None
    
    def _estimate_model_size(self, model) -> float:
        """Estime la taille du modèle en MB"""
        try:
            # Estimation basée sur les paramètres du modèle
            total_params = sum(p.numel() for p in model.parameters())
            # Approximation: 4 bytes par paramètre (float32)
            size_mb = (total_params * 4) / (1024 * 1024)
            return round(size_mb, 1)
        except Exception:
            return 0.0
    
    def preload_popular_models(self) -> int:
        """
        🚀 Précharge les modèles populaires en arrière-plan
        Utile au démarrage de l'application
        """
        popular_models = [
            "sentence-transformers/all-mpnet-base-v2",
            "sentence-transformers/all-MiniLM-L6-v2"
        ]
        
        loaded_count = 0
        for model_name in popular_models:
            if model_name not in self.models:
                model = self.get_model(model_name)
                if model is not None:
                    loaded_count += 1
        
        log3("[MODEL_CACHE]", {
            "action": "preload_complete",
            "loaded_count": loaded_count,
            "total_cached": len(self.models)
        })
        
        return loaded_count
    
    def get_stats(self) -> Dict[str, Any]:
        """📊 Statistiques détaillées du cache"""
        with self.lock:
            total_access = sum(stats["access_count"] for stats in self.model_stats.values())
            total_size_mb = sum(stats["model_size_mb"] for stats in self.model_stats.values())
            
            model_details = []
            for model_name, stats in self.model_stats.items():
                model_details.append({
                    "name": model_name,
                    "access_count": stats["access_count"],
                    "size_mb": stats["model_size_mb"],
                    "loaded_since_hours": (datetime.now() - stats["loaded_at"]).total_seconds() / 3600
                })
            
            return {
                "models_cached": len(self.models),
                "total_access_count": total_access,
                "total_size_mb": total_size_mb,
                "system_memory_usage": f"{self._get_memory_usage():.1f}%",
                "memory_threshold": f"{self.memory_threshold}%",
                "last_cleanup_minutes_ago": (datetime.now() - self.last_cleanup).total_seconds() / 60,
                "model_details": model_details
            }
    
    def force_cleanup(self) -> Dict[str, int]:
        """🗑️ Force un nettoyage complet du cache"""
        with self.lock:
            initial_count = len(self.models)
            removed_count = self._cleanup_unused_models()
            
            return {
                "initial_models": initial_count,
                "removed_models": removed_count,
                "remaining_models": len(self.models)
            }

# Instance globale singleton
_global_model_cache = None

def get_global_model_cache() -> GlobalModelCache:
    """🚀 Singleton pour le cache modèle global"""
    global _global_model_cache
    if _global_model_cache is None:
        _global_model_cache = GlobalModelCache()
    return _global_model_cache
