#!/usr/bin/env python3
"""
🚀 ENDPOINT DE MONITORING DES CACHES
Objectif: Surveiller les performances et statistiques de tous les caches
Architecture: API REST avec métriques détaillées et actions de maintenance
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional, List
import asyncio
from datetime import datetime
from utils import log3

# Import du système de cache unifié
from core.unified_cache_system import get_unified_cache_system

router = APIRouter(prefix="/cache", tags=["Cache Monitoring"])

@router.get("/stats", summary="📊 Statistiques globales des caches")
async def get_cache_stats():
    """
    🎯 Retourne les statistiques détaillées de tous les caches
    - Hit rates et performances
    - Utilisation mémoire
    - Temps de réponse moyens
    """
    try:
        cache_system = get_unified_cache_system()
        stats = cache_system.get_global_stats()
        
        # Ajouter des métriques système
        import psutil
        system_stats = {
            "system_memory_percent": psutil.virtual_memory().percent,
            "system_cpu_percent": psutil.cpu_percent(interval=1),
            "timestamp": datetime.now().isoformat()
        }
        
        return {
            "status": "success",
            "cache_stats": stats,
            "system_stats": system_stats,
            "performance_summary": _calculate_performance_summary(stats)
        }
        
    except Exception as e:
        log3("[CACHE_MONITORING]", {"action": "stats_error", "error": str(e)})
        raise HTTPException(status_code=500, detail=f"Erreur récupération stats: {e}")

@router.get("/performance", summary="⚡ Analyse de performance détaillée")
async def get_performance_analysis():
    """
    🚀 Analyse détaillée des gains de performance
    - Temps économisés par cache
    - Comparaison avec/sans cache
    - Recommandations d'optimisation
    """
    try:
        cache_system = get_unified_cache_system()
        stats = cache_system.get_global_stats()
        
        analysis = {
            "time_savings": {
                "total_seconds_saved": stats["unified_cache"]["total_time_saved_seconds"],
                "average_per_request": stats["unified_cache"]["average_time_saved_per_hit"],
                "estimated_daily_savings": _estimate_daily_savings(stats),
                "performance_improvement_percent": _calculate_improvement_percent(stats)
            },
            "cache_efficiency": {
                "overall_hit_rate": stats["unified_cache"]["hit_rate_percent"],
                "prompt_cache_efficiency": _analyze_cache_efficiency(stats["prompt_cache"]),
                "embedding_cache_efficiency": _analyze_cache_efficiency(stats["embedding_cache"]),
                "model_cache_efficiency": _analyze_cache_efficiency(stats["model_cache"])
            },
            "recommendations": _generate_recommendations(stats),
            "timestamp": datetime.now().isoformat()
        }
        
        return {
            "status": "success",
            "performance_analysis": analysis
        }
        
    except Exception as e:
        log3("[CACHE_MONITORING]", {"action": "performance_error", "error": str(e)})
        raise HTTPException(status_code=500, detail=f"Erreur analyse performance: {e}")

@router.post("/cleanup", summary="🧹 Nettoyage des caches")
async def cleanup_caches(
    force: bool = Query(False, description="Forcer le nettoyage même si pas nécessaire")
):
    """
    🗑️ Lance un nettoyage des caches expirés
    - Supprime les entrées expirées
    - Libère la mémoire
    - Optimise les performances
    """
    try:
        cache_system = get_unified_cache_system()
        
        cleanup_results = await cache_system.cleanup_all_caches()
        
        # Statistiques après nettoyage
        stats_after = cache_system.get_global_stats()
        
        return {
            "status": "success",
            "cleanup_results": cleanup_results,
            "stats_after_cleanup": {
                "prompt_cache_size": stats_after["prompt_cache"]["cache_size"],
                "embedding_cache_size": stats_after["embedding_cache"]["cache_size"],
                "model_cache_size": stats_after["model_cache"]["models_cached"],
                "memory_usage_mb": stats_after["embedding_cache"]["memory_usage_mb"]
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        log3("[CACHE_MONITORING]", {"action": "cleanup_error", "error": str(e)})
        raise HTTPException(status_code=500, detail=f"Erreur nettoyage: {e}")

@router.post("/preload/{company_id}", summary="🚀 Préchargement des ressources")
async def preload_company_resources(
    company_id: str,
    common_queries: Optional[List[str]] = Query(None, description="Queries communes à précacher")
):
    """
    ⚡ Précharge toutes les ressources pour une entreprise
    - Prompt de l'entreprise
    - Modèles d'embedding
    - Embeddings pour queries communes
    """
    try:
        cache_system = get_unified_cache_system()
        
        # Convertir les queries en liste si fourni
        queries_list = common_queries if common_queries else [
            "prix produit",
            "livraison délai",
            "contact support",
            "informations entreprise",
            "catalogue produits"
        ]
        
        preload_results = await cache_system.preload_company_resources(
            company_id, 
            queries_list
        )
        
        return {
            "status": "success",
            "company_id": company_id,
            "preload_results": preload_results,
            "queries_preloaded": len(queries_list),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        log3("[CACHE_MONITORING]", {"action": "preload_error", "company_id": company_id, "error": str(e)})
        raise HTTPException(status_code=500, detail=f"Erreur préchargement: {e}")

@router.get("/health", summary="🏥 Santé des caches")
async def cache_health_check():
    """
    ✅ Vérification de la santé des caches
    - Status de chaque cache
    - Détection de problèmes
    - Alertes de performance
    """
    try:
        cache_system = get_unified_cache_system()
        stats = cache_system.get_global_stats()
        
        health_status = {
            "overall_status": "healthy",
            "alerts": [],
            "cache_status": {
                "prompt_cache": _check_cache_health("prompt", stats["prompt_cache"]),
                "embedding_cache": _check_cache_health("embedding", stats["embedding_cache"]),
                "model_cache": _check_cache_health("model", stats["model_cache"])
            },
            "system_health": {
                "memory_usage_ok": psutil.virtual_memory().percent < 85,
                "cpu_usage_ok": psutil.cpu_percent(interval=1) < 80
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Déterminer le status global
        if any(not status["healthy"] for status in health_status["cache_status"].values()):
            health_status["overall_status"] = "warning"
        
        if not health_status["system_health"]["memory_usage_ok"]:
            health_status["overall_status"] = "critical"
            health_status["alerts"].append("Utilisation mémoire élevée")
        
        return {
            "status": "success",
            "health": health_status
        }
        
    except Exception as e:
        log3("[CACHE_MONITORING]", {"action": "health_error", "error": str(e)})
        raise HTTPException(status_code=500, detail=f"Erreur vérification santé: {e}")

@router.delete("/invalidate/{company_id}", summary="🗑️ Invalider cache entreprise")
async def invalidate_company_cache(company_id: str):
    """
    ❌ Invalide tous les caches pour une entreprise spécifique
    Utile quand les données de l'entreprise sont modifiées
    """
    try:
        cache_system = get_unified_cache_system()
        cache_system.invalidate_company_cache(company_id)
        
        return {
            "status": "success",
            "message": f"Cache invalidé pour l'entreprise {company_id}",
            "timestamp": time.time()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur invalidation cache: {str(e)}")

@router.post("/clear-prompt-cache", summary="🧹 Vider cache prompt global")
async def clear_prompt_cache():
    """
    🧹 Vide complètement le cache des prompts pour forcer le rechargement
    Utile après modification des prompts en base de données
    """
    try:
        cache_system = get_unified_cache_system()
        
        # Vider le cache prompt
        if hasattr(cache_system, 'prompt_cache'):
            cache_system.prompt_cache.clear()
            prompt_cleared = True
        else:
            prompt_cleared = False
        
        # Vider aussi Redis si disponible
        redis_cleared = 0
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            prompt_keys = r.keys("prompt_cache:*")
            if prompt_keys:
                r.delete(*prompt_keys)
                redis_cleared = len(prompt_keys)
        except:
            pass
        
        log3("[CACHE_MONITORING]", {
            "action": "clear_prompt_cache",
            "unified_cleared": prompt_cleared,
            "redis_keys_cleared": redis_cleared
        })
        
        return {
            "status": "success",
            "message": "Cache prompt vidé avec succès",
            "details": {
                "unified_cache_cleared": prompt_cleared,
                "redis_keys_cleared": redis_cleared,
                "next_call_will_reload": True
            },
            "timestamp": time.time()
        }
        
    except Exception as e:
        log3("[CACHE_MONITORING]", {"action": "clear_prompt_error", "error": str(e)})
        raise HTTPException(status_code=500, detail=f"Erreur nettoyage cache prompt: {str(e)}")

@router.post("/clear-prompt-cache/{company_id}", summary="🧹 Vider cache prompt entreprise")
async def clear_company_prompt_cache(company_id: str):
    """
    🧹 Vide le cache prompt pour une entreprise spécifique
    Utile après modification du prompt d'une entreprise
    """
    try:
        cache_system = get_unified_cache_system()
        
        # Vider le cache pour cette entreprise
        if hasattr(cache_system, 'invalidate_company_cache'):
            cache_system.invalidate_company_cache(company_id)
            company_cleared = True
        else:
            company_cleared = False
        
        # Vider Redis pour cette entreprise
        redis_cleared = 0
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            company_keys = r.keys(f"*{company_id}*")
            if company_keys:
                r.delete(*company_keys)
                redis_cleared = len(company_keys)
        except:
            pass
        
        log3("[CACHE_MONITORING]", {
            "action": "clear_company_prompt_cache",
            "company_id": company_id[:12],
            "company_cleared": company_cleared,
            "redis_keys_cleared": redis_cleared
        })
        
        return {
            "status": "success",
            "message": f"Cache prompt vidé pour l'entreprise {company_id}",
            "details": {
                "company_cache_cleared": company_cleared,
                "redis_keys_cleared": redis_cleared,
                "company_id": company_id
            },
            "timestamp": time.time()
        }
        
    except Exception as e:
        log3("[CACHE_MONITORING]", {"action": "clear_company_prompt_error", "error": str(e)})
        raise HTTPException(status_code=500, detail=f"Erreur nettoyage cache entreprise: {str(e)}")

# Fonctions utilitaires privées
def _calculate_performance_summary(stats: Dict[str, Any]) -> Dict[str, Any]:
    """Calcule un résumé des performances"""
    unified = stats["unified_cache"]
    
    return {
        "total_requests": unified["total_requests"],
        "cache_efficiency": unified["hit_rate_percent"],
        "time_saved_total": unified["total_time_saved_seconds"],
        "average_response_improvement": unified["average_time_saved_per_hit"],
        "estimated_cost_savings_daily": f"{float(unified['total_time_saved_seconds'].replace('s', '')) * 0.01:.2f}€"  # 1 centime par seconde économisée
    }

def _estimate_daily_savings(stats: Dict[str, Any]) -> str:
    """Estime les économies de temps quotidiennes"""
    try:
        total_saved = float(stats["unified_cache"]["total_time_saved_seconds"].replace('s', ''))
        requests = stats["unified_cache"]["total_requests"]
        
        if requests > 0:
            avg_per_request = total_saved / requests
            # Estimation: 1000 requêtes par jour
            daily_savings = avg_per_request * 1000
            return f"{daily_savings:.1f}s"
        
        return "0s"
    except:
        return "N/A"

def _calculate_improvement_percent(stats: Dict[str, Any]) -> str:
    """Calcule le pourcentage d'amélioration des performances"""
    try:
        hit_rate = float(stats["unified_cache"]["hit_rate_percent"].replace('%', ''))
        # Estimation: amélioration basée sur le hit rate
        # 90% hit rate = 90% d'amélioration sur les requêtes cachées
        improvement = hit_rate * 0.8  # Facteur de pondération
        return f"{improvement:.1f}%"
    except:
        return "N/A"

def _analyze_cache_efficiency(cache_stats: Dict[str, Any]) -> Dict[str, Any]:
    """Analyse l'efficacité d'un cache spécifique"""
    try:
        return {
            "hit_rate": cache_stats.get("hit_rate_percent", "N/A"),
            "size": cache_stats.get("cache_size", 0),
            "efficiency_rating": _rate_efficiency(cache_stats.get("hit_rate_percent", "0%"))
        }
    except:
        return {"hit_rate": "N/A", "size": 0, "efficiency_rating": "unknown"}

def _rate_efficiency(hit_rate_str: str) -> str:
    """Évalue l'efficacité basée sur le hit rate"""
    try:
        hit_rate = float(hit_rate_str.replace('%', ''))
        if hit_rate >= 80:
            return "excellent"
        elif hit_rate >= 60:
            return "good"
        elif hit_rate >= 40:
            return "average"
        else:
            return "poor"
    except:
        return "unknown"

def _generate_recommendations(stats: Dict[str, Any]) -> List[str]:
    """Génère des recommandations d'optimisation"""
    recommendations = []
    
    try:
        unified = stats["unified_cache"]
        hit_rate = float(unified["hit_rate_percent"].replace('%', ''))
        
        if hit_rate < 60:
            recommendations.append("Augmenter la durée de vie (TTL) des caches")
        
        if stats["embedding_cache"]["memory_usage_mb"] > 500:
            recommendations.append("Considérer un nettoyage plus fréquent du cache embeddings")
        
        if stats["model_cache"]["models_cached"] > 3:
            recommendations.append("Limiter le nombre de modèles en mémoire simultanément")
        
        if not recommendations:
            recommendations.append("Performance optimale - aucune action requise")
            
    except:
        recommendations.append("Impossible d'analyser - vérifier les logs")
    
    return recommendations

def _check_cache_health(cache_type: str, cache_stats: Dict[str, Any]) -> Dict[str, Any]:
    """Vérifie la santé d'un cache spécifique"""
    try:
        if cache_type == "embedding":
            memory_ok = cache_stats.get("memory_usage_mb", 0) < 1000  # Limite 1GB
            size_ok = cache_stats.get("cache_size", 0) < 50000  # Limite 50k entrées
        else:
            memory_ok = True
            size_ok = cache_stats.get("cache_size", 0) < 10000  # Limite générale
        
        hit_rate_str = cache_stats.get("hit_rate_percent", "0%")
        hit_rate = float(hit_rate_str.replace('%', ''))
        performance_ok = hit_rate > 30  # Minimum 30% hit rate
        
        return {
            "healthy": memory_ok and size_ok and performance_ok,
            "memory_ok": memory_ok,
            "size_ok": size_ok,
            "performance_ok": performance_ok,
            "hit_rate": hit_rate_str
        }
        
    except:
        return {
            "healthy": False,
            "memory_ok": False,
            "size_ok": False,
            "performance_ok": False,
            "hit_rate": "N/A"
        }
