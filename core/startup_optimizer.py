#!/usr/bin/env python3
"""
🚀 STARTUP OPTIMIZER - ÉLIMINATION LATENCE 3.6s
===============================================

Optimisations avancées pour le démarrage :
1. Pré-chargement parallèle des modèles
2. Warm-up intelligent des caches
3. Monitoring performance temps réel
4. Fallback robuste en cas d'erreur

Objectif : Réduire latence première requête de 3.6s → 0.01s
"""

import asyncio
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional
from utils import log3

class StartupOptimizer:
    """
    🚀 Optimiseur de démarrage pour élimination latence
    
    Fonctionnalités :
    - Pré-chargement parallèle des modèles
    - Warm-up intelligent des embeddings
    - Monitoring performance en temps réel
    - Fallback automatique en cas d'erreur
    """
    
    def __init__(self):
        self.startup_stats = {
            "start_time": None,
            "models_loaded": 0,
            "embeddings_warmed": 0,
            "total_time": 0,
            "errors": []
        }
        self.warm_up_queries = [
            "Bonjour, combien coûte un paquet de couches?",
            "Livraison à Yopougon possible?", 
            "Quels sont vos prix?",
            "Zone de livraison Cocody",
            "Acompte Wave paiement",
            "Taille couches adultes",
            "Délai livraison Abidjan",
            "Prix paquet 30 couches"
        ]
    
    async def optimize_startup(self) -> Dict[str, Any]:
        """
        🎯 Lance l'optimisation complète du démarrage
        
        Returns:
            Dict avec statistiques de performance
        """
        self.startup_stats["start_time"] = time.time()
        log3("[STARTUP_OPT]", "🚀 Démarrage optimisation startup...")
        
        try:
            # 1. Initialiser le système de cache
            cache_system = await self._initialize_cache_system()
            
            # 2. Pré-charger les modèles en parallèle
            models_stats = await self._preload_models_parallel(cache_system)
            
            # 3. Warm-up des embeddings en parallèle
            warmup_stats = await self._warmup_embeddings_parallel()
            
            # 4. Validation finale du système
            validation_stats = await self._validate_system_ready(cache_system)
            
            # 5. Compilation des statistiques finales
            final_stats = self._compile_final_stats(
                cache_system, models_stats, warmup_stats, validation_stats
            )
            
            log3("[STARTUP_OPT]", "✅ Optimisation startup terminée avec succès")
            return final_stats
            
        except Exception as e:
            error_msg = f"Erreur critique startup: {str(e)}"
            self.startup_stats["errors"].append(error_msg)
            log3("[STARTUP_OPT]", f"❌ {error_msg}")
            
            # Fallback d'urgence
            return await self._emergency_fallback()
    
    async def _initialize_cache_system(self):
        """🏗️ Initialise le système de cache unifié"""
        try:
            from core.unified_cache_system import get_unified_cache_system
            cache_system = get_unified_cache_system()
            log3("[STARTUP_OPT]", "✅ Système de cache unifié initialisé")
            return cache_system
        except Exception as e:
            raise Exception(f"Échec initialisation cache: {e}")
    
    async def _preload_models_parallel(self, cache_system) -> Dict[str, Any]:
        """🧠 Pré-charge tous les modèles en parallèle"""
        try:
            from embedding_models import EMBEDDING_MODELS
            
            models_stats = {
                "total_models": len(EMBEDDING_MODELS),
                "loaded_successfully": 0,
                "load_times": {},
                "errors": []
            }
            
            log3("[STARTUP_OPT]", f"🧠 Pré-chargement de {len(EMBEDDING_MODELS)} modèles...")
            
            # Fonction de chargement pour un modèle
            def load_single_model(model_key: str, model_info: Dict) -> Dict:
                try:
                    start_time = time.time()
                    model = cache_system.get_cached_model(model_info["name"])
                    load_time = time.time() - start_time
                    
                    return {
                        "key": model_key,
                        "success": model is not None,
                        "load_time": load_time,
                        "error": None
                    }
                except Exception as e:
                    return {
                        "key": model_key,
                        "success": False,
                        "load_time": 0,
                        "error": str(e)
                    }
            
            # Exécution parallèle
            with ThreadPoolExecutor(max_workers=3) as executor:
                future_to_model = {
                    executor.submit(load_single_model, key, info): key 
                    for key, info in EMBEDDING_MODELS.items()
                }
                
                for future in as_completed(future_to_model):
                    result = future.result()
                    
                    if result["success"]:
                        models_stats["loaded_successfully"] += 1
                        models_stats["load_times"][result["key"]] = result["load_time"]
                        log3("[STARTUP_OPT]", f"✅ {result['key']}: {result['load_time']:.2f}s")
                    else:
                        models_stats["errors"].append(f"{result['key']}: {result['error']}")
                        log3("[STARTUP_OPT]", f"❌ {result['key']}: {result['error'][:50]}")
            
            self.startup_stats["models_loaded"] = models_stats["loaded_successfully"]
            log3("[STARTUP_OPT]", f"📊 Modèles chargés: {models_stats['loaded_successfully']}/{models_stats['total_models']}")
            
            return models_stats
            
        except Exception as e:
            raise Exception(f"Échec pré-chargement modèles: {e}")
    
    async def _warmup_embeddings_parallel(self) -> Dict[str, Any]:
        """🔥 Warm-up des embeddings en parallèle"""
        try:
            warmup_stats = {
                "total_queries": len(self.warm_up_queries),
                "successful_embeddings": 0,
                "embedding_times": [],
                "errors": []
            }
            
            log3("[STARTUP_OPT]", f"🔥 Warm-up de {len(self.warm_up_queries)} embeddings...")
            
            # Fonction de génération d'embedding
            async def generate_single_embedding(query: str) -> Dict:
                try:
                    start_time = time.time()
                    from embedding_models import embed_text
                    embedding = await embed_text(query, use_cache=True)
                    embed_time = time.time() - start_time
                    
                    return {
                        "query": query[:30],
                        "success": embedding is not None,
                        "embed_time": embed_time,
                        "dimensions": len(embedding) if embedding is not None else 0,
                        "error": None
                    }
                except Exception as e:
                    return {
                        "query": query[:30],
                        "success": False,
                        "embed_time": 0,
                        "dimensions": 0,
                        "error": str(e)
                    }
            
            # Exécution parallèle des embeddings
            tasks = [generate_single_embedding(query) for query in self.warm_up_queries]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, dict) and result["success"]:
                    warmup_stats["successful_embeddings"] += 1
                    warmup_stats["embedding_times"].append(result["embed_time"])
                    log3("[STARTUP_OPT]", f"🔥 {result['query']}: {result['embed_time']:.3f}s ({result['dimensions']} dims)")
                elif isinstance(result, dict):
                    warmup_stats["errors"].append(f"{result['query']}: {result['error']}")
                    log3("[STARTUP_OPT]", f"❌ {result['query']}: {result['error'][:30]}")
            
            self.startup_stats["embeddings_warmed"] = warmup_stats["successful_embeddings"]
            
            # Calcul statistiques de performance
            if warmup_stats["embedding_times"]:
                avg_time = sum(warmup_stats["embedding_times"]) / len(warmup_stats["embedding_times"])
                max_time = max(warmup_stats["embedding_times"])
                min_time = min(warmup_stats["embedding_times"])
                
                log3("[STARTUP_OPT]", f"📊 Warm-up stats: avg={avg_time:.3f}s, max={max_time:.3f}s, min={min_time:.3f}s")
                
                warmup_stats.update({
                    "avg_embedding_time": avg_time,
                    "max_embedding_time": max_time,
                    "min_embedding_time": min_time
                })
            
            return warmup_stats
            
        except Exception as e:
            raise Exception(f"Échec warm-up embeddings: {e}")
    
    async def _validate_system_ready(self, cache_system) -> Dict[str, Any]:
        """✅ Valide que le système est prêt pour production"""
        try:
            validation_stats = {
                "cache_system_ready": False,
                "models_accessible": False,
                "embeddings_functional": False,
                "performance_acceptable": False
            }
            
            log3("[STARTUP_OPT]", "🔍 Validation finale du système...")
            
            # 1. Vérifier cache system
            try:
                stats = cache_system.get_global_stats()
                validation_stats["cache_system_ready"] = stats["model_cache"]["models_cached"] > 0
            except:
                pass
            
            # 2. Vérifier accès aux modèles
            try:
                model = cache_system.get_cached_model("sentence-transformers/all-mpnet-base-v2")
                validation_stats["models_accessible"] = model is not None
            except:
                pass
            
            # 3. Test embedding rapide
            try:
                from embedding_models import embed_text
                test_start = time.time()
                embedding = await embed_text("test rapide", use_cache=True)
                test_time = time.time() - test_start
                
                validation_stats["embeddings_functional"] = embedding is not None
                validation_stats["performance_acceptable"] = test_time < 0.1  # < 100ms
                validation_stats["test_embedding_time"] = test_time
                
            except:
                pass
            
            # Résultat global
            all_checks = [
                validation_stats["cache_system_ready"],
                validation_stats["models_accessible"], 
                validation_stats["embeddings_functional"],
                validation_stats["performance_acceptable"]
            ]
            
            validation_stats["system_ready"] = all(all_checks)
            
            if validation_stats["system_ready"]:
                log3("[STARTUP_OPT]", "✅ Système validé - Prêt pour production")
            else:
                log3("[STARTUP_OPT]", "⚠️ Validation partielle - Vérifier les logs")
            
            return validation_stats
            
        except Exception as e:
            raise Exception(f"Échec validation système: {e}")
    
    def _compile_final_stats(
        self, 
        cache_system, 
        models_stats: Dict, 
        warmup_stats: Dict, 
        validation_stats: Dict
    ) -> Dict[str, Any]:
        """📊 Compile les statistiques finales"""
        
        total_time = time.time() - self.startup_stats["start_time"]
        self.startup_stats["total_time"] = total_time
        
        # Récupérer stats du cache
        try:
            cache_stats = cache_system.get_global_stats()
        except:
            cache_stats = {"error": "Stats indisponibles"}
        
        # Calcul de l'amélioration de performance
        baseline_latency = 3.6  # Latence de référence
        if warmup_stats.get("avg_embedding_time"):
            current_latency = warmup_stats["avg_embedding_time"]
            improvement_percent = ((baseline_latency - current_latency) / baseline_latency) * 100
        else:
            improvement_percent = 0
        
        final_stats = {
            "startup_summary": {
                "total_startup_time": total_time,
                "models_loaded": self.startup_stats["models_loaded"],
                "embeddings_warmed": self.startup_stats["embeddings_warmed"],
                "system_ready": validation_stats.get("system_ready", False),
                "errors_count": len(self.startup_stats["errors"])
            },
            "performance_metrics": {
                "baseline_latency_s": baseline_latency,
                "current_avg_latency_s": warmup_stats.get("avg_embedding_time", "N/A"),
                "improvement_percent": f"{improvement_percent:.1f}%",
                "target_achieved": improvement_percent > 95
            },
            "models_stats": models_stats,
            "warmup_stats": warmup_stats,
            "validation_stats": validation_stats,
            "cache_stats": cache_stats,
            "errors": self.startup_stats["errors"]
        }
        
        return final_stats
    
    async def _emergency_fallback(self) -> Dict[str, Any]:
        """🆘 Fallback d'urgence en cas d'échec critique"""
        try:
            log3("[STARTUP_OPT]", "🆘 Activation fallback d'urgence...")
            
            # Tentative de chargement minimal
            from embedding_models import get_embedding_model
            model = get_embedding_model()
            
            fallback_stats = {
                "startup_summary": {
                    "total_startup_time": time.time() - self.startup_stats["start_time"],
                    "models_loaded": 1 if model else 0,
                    "embeddings_warmed": 0,
                    "system_ready": model is not None,
                    "errors_count": len(self.startup_stats["errors"])
                },
                "fallback_mode": True,
                "errors": self.startup_stats["errors"]
            }
            
            if model:
                log3("[STARTUP_OPT]", "✅ Fallback réussi - Modèle de base chargé")
            else:
                log3("[STARTUP_OPT]", "❌ Fallback échoué - Démarrage dégradé")
            
            return fallback_stats
            
        except Exception as e:
            log3("[STARTUP_OPT]", f"❌ Fallback critique échoué: {e}")
            return {
                "startup_summary": {
                    "total_startup_time": time.time() - self.startup_stats["start_time"],
                    "models_loaded": 0,
                    "embeddings_warmed": 0,
                    "system_ready": False,
                    "errors_count": len(self.startup_stats["errors"]) + 1
                },
                "critical_failure": True,
                "errors": self.startup_stats["errors"] + [str(e)]
            }

# Instance globale
startup_optimizer = StartupOptimizer()

async def optimize_application_startup() -> Dict[str, Any]:
    """
    🚀 Point d'entrée principal pour l'optimisation startup
    
    Usage dans app.py:
    ```python
    @app.on_event("startup")
    async def startup_event():
        from core.startup_optimizer import optimize_application_startup
        stats = await optimize_application_startup()
        print(f"Startup terminé: {stats['startup_summary']}")
    ```
    """
    return await startup_optimizer.optimize_startup()
