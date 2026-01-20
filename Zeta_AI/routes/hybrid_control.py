"""
🎯 API DE CONTRÔLE SYSTÈME HYBRIDE
Endpoints pour activer/désactiver/monitorer le système hybride
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import logging

from core.botlive_router import get_router
from core.hybrid_botlive_engine import get_hybrid_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/botlive/hybrid", tags=["Hybrid Control"])


class HybridStatusResponse(BaseModel):
    """Réponse statut système hybride"""
    enabled: bool
    message: str
    metrics: Dict[str, Any]


class MetricsResponse(BaseModel):
    """Réponse métriques"""
    hybrid_enabled: bool
    old_system: Dict[str, Any]
    hybrid_system: Dict[str, Any]
    comparison: Dict[str, Any]


@router.post("/enable", response_model=HybridStatusResponse)
async def enable_hybrid():
    """
    Active le système hybride
    
    **ATTENTION:** Cela bascule TOUTES les requêtes vers le nouveau système.
    Assurez-vous d'avoir testé en local avant.
    """
    try:
        router_instance = get_router()
        router_instance.enable_hybrid()
        
        engine = get_hybrid_engine()
        engine.enable()
        
        logger.info("🚀 [API] Système HYBRIDE activé via API")
        
        return HybridStatusResponse(
            enabled=True,
            message="Système hybride activé avec succès",
            metrics=router_instance.get_metrics()
        )
    
    except Exception as e:
        logger.error(f"❌ [API] Erreur activation hybride: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disable", response_model=HybridStatusResponse)
async def disable_hybrid():
    """
    Désactive le système hybride (ROLLBACK)
    
    Retour immédiat à l'ancien système.
    Utilisez ceci en cas de problème avec le système hybride.
    """
    try:
        router_instance = get_router()
        router_instance.disable_hybrid()
        
        engine = get_hybrid_engine()
        engine.disable()
        
        logger.warning("⚠️ [API] ROLLBACK vers ancien système via API")
        
        return HybridStatusResponse(
            enabled=False,
            message="Rollback effectué, ancien système actif",
            metrics=router_instance.get_metrics()
        )
    
    except Exception as e:
        logger.error(f"❌ [API] Erreur désactivation hybride: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/toggle", response_model=HybridStatusResponse)
async def toggle_hybrid():
    """
    Bascule entre les deux systèmes
    
    Si hybride actif → désactive
    Si hybride inactif → active
    """
    try:
        router_instance = get_router()
        router_instance.toggle()
        
        engine = get_hybrid_engine()
        if router_instance.is_hybrid_enabled():
            engine.enable()
        else:
            engine.disable()
        
        status = "activé" if router_instance.is_hybrid_enabled() else "désactivé"
        logger.info(f"🔄 [API] Système hybride {status} via toggle")
        
        return HybridStatusResponse(
            enabled=router_instance.is_hybrid_enabled(),
            message=f"Système hybride {status}",
            metrics=router_instance.get_metrics()
        )
    
    except Exception as e:
        logger.error(f"❌ [API] Erreur toggle hybride: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=HybridStatusResponse)
async def get_status():
    """
    Récupère le statut actuel du système hybride
    """
    try:
        router_instance = get_router()
        engine = get_hybrid_engine()
        
        return HybridStatusResponse(
            enabled=router_instance.is_hybrid_enabled(),
            message="Système hybride actif" if router_instance.is_hybrid_enabled() else "Ancien système actif",
            metrics=router_instance.get_metrics()
        )
    
    except Exception as e:
        logger.error(f"❌ [API] Erreur récupération statut: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """
    Récupère les métriques de comparaison entre les deux systèmes
    
    Utile pour décider quel système est le plus performant.
    """
    try:
        router_instance = get_router()
        metrics = router_instance.get_metrics()
        
        return MetricsResponse(**metrics)
    
    except Exception as e:
        logger.error(f"❌ [API] Erreur récupération métriques: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset-metrics")
async def reset_metrics():
    """
    Réinitialise les métriques
    
    Utile pour recommencer une phase de test A/B.
    """
    try:
        router_instance = get_router()
        router_instance.metrics = {
            "old_system": {"count": 0, "errors": 0, "avg_time": 0},
            "hybrid_system": {"count": 0, "errors": 0, "avg_time": 0}
        }
        
        logger.info("🔄 [API] Métriques réinitialisées")
        
        return {"message": "Métriques réinitialisées avec succès"}
    
    except Exception as e:
        logger.error(f"❌ [API] Erreur réinitialisation métriques: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Vérification santé du système hybride
    """
    try:
        router_instance = get_router()
        engine = get_hybrid_engine()
        
        return {
            "status": "healthy",
            "hybrid_enabled": router_instance.is_hybrid_enabled(),
            "engine_enabled": engine.is_enabled(),
            "metrics": router_instance.get_metrics()
        }
    
    except Exception as e:
        logger.error(f"❌ [API] Erreur health check: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
