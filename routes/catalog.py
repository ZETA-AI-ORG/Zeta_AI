#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📦 CATALOG ROUTES - Gestion du cache catalogue Gemini
Endpoints pour invalidation, refresh et monitoring du cache

ENDPOINTS:
- POST /catalog/invalidate     → Invalide le cache (webhook frontend)
- POST /catalog/refresh        → Force le refresh du cache
- GET  /catalog/status         → Status du cache pour une entreprise
- POST /catalog/warmup         → Préchauffe le cache au démarrage
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
import time

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/catalog", tags=["Catalog Cache"])


# ═══════════════════════════════════════════════════════════════════════════════
# MODÈLES PYDANTIC
# ═══════════════════════════════════════════════════════════════════════════════

class CatalogInvalidateRequest(BaseModel):
    """Requête d'invalidation du cache catalogue"""
    company_id: str
    reason: Optional[str] = "manual"  # manual, product_update, price_change, stock_update


class CatalogRefreshRequest(BaseModel):
    """Requête de refresh forcé du cache"""
    company_id: str
    force: bool = False  # Force même si cache valide


class CatalogStatusResponse(BaseModel):
    """Réponse status du cache"""
    company_id: str
    cache_exists: bool
    cache_age_seconds: Optional[float] = None
    product_count: int = 0
    source: str = "none"
    last_invalidation: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/invalidate")
async def invalidate_catalog_cache(request: CatalogInvalidateRequest) -> Dict[str, Any]:
    """
    🗑️ INVALIDE LE CACHE CATALOGUE
    
    Appelé par le frontend quand:
    - Un produit est ajouté/modifié/supprimé
    - Les prix changent
    - Le stock est mis à jour
    
    Args:
        company_id: ID de l'entreprise
        reason: Raison de l'invalidation (pour logs)
        
    Returns:
        {"success": true, "message": "Cache invalidé"}
    """
    try:
        from core.catalog_cache_manager import get_catalog_cache_manager
        
        cache_manager = get_catalog_cache_manager()
        cache_manager.invalidate_cache(request.company_id)
        
        logger.info(f"🗑️ [CATALOG] Cache invalidé: {request.company_id} (raison: {request.reason})")
        
        return {
            "success": True,
            "message": f"Cache catalogue invalidé pour {request.company_id}",
            "reason": request.reason,
            "timestamp": time.time()
        }
        
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="CatalogCacheManager non disponible"
        )
    except Exception as e:
        logger.error(f"❌ [CATALOG] Erreur invalidation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur invalidation cache: {str(e)}"
        )


@router.post("/refresh")
async def refresh_catalog_cache(
    request: CatalogRefreshRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    🔄 FORCE LE REFRESH DU CACHE CATALOGUE
    
    Recharge le catalogue depuis Supabase et met à jour le cache Redis.
    Peut être appelé après une mise à jour massive du catalogue.
    
    Args:
        company_id: ID de l'entreprise
        force: Force le refresh même si cache valide
        
    Returns:
        {"success": true, "product_count": N}
    """
    try:
        from core.catalog_cache_manager import get_catalog_cache_manager
        
        cache_manager = get_catalog_cache_manager()
        
        # Invalider d'abord
        cache_manager.invalidate_cache(request.company_id)
        
        # Recharger en background
        async def reload_cache():
            try:
                cache_data = await cache_manager.get_catalog_cache(request.company_id)
                logger.info(f"✅ [CATALOG] Cache rechargé: {request.company_id} ({cache_data.get('product_count', 0)} produits)")
            except Exception as e:
                logger.error(f"❌ [CATALOG] Erreur reload: {e}")
        
        background_tasks.add_task(reload_cache)
        
        return {
            "success": True,
            "message": f"Refresh du cache lancé pour {request.company_id}",
            "force": request.force,
            "timestamp": time.time()
        }
        
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="CatalogCacheManager non disponible"
        )
    except Exception as e:
        logger.error(f"❌ [CATALOG] Erreur refresh: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur refresh cache: {str(e)}"
        )


@router.get("/status/{company_id}")
async def get_catalog_status(company_id: str) -> CatalogStatusResponse:
    """
    📊 STATUS DU CACHE CATALOGUE
    
    Retourne l'état actuel du cache pour une entreprise:
    - Existence du cache
    - Âge du cache
    - Nombre de produits
    - Source (redis/supabase/none)
    
    Args:
        company_id: ID de l'entreprise
        
    Returns:
        CatalogStatusResponse
    """
    try:
        from core.catalog_cache_manager import get_catalog_cache_manager
        
        cache_manager = get_catalog_cache_manager()
        cache_data = await cache_manager.get_catalog_cache(company_id)
        
        cache_age = None
        if cache_data.get('cached_at'):
            cache_age = time.time() - cache_data['cached_at']
        
        return CatalogStatusResponse(
            company_id=company_id,
            cache_exists=cache_data.get('source') != 'none',
            cache_age_seconds=cache_age,
            product_count=cache_data.get('product_count', 0),
            source=cache_data.get('source', 'none'),
            last_invalidation=None  # TODO: tracker les invalidations
        )
        
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="CatalogCacheManager non disponible"
        )
    except Exception as e:
        logger.error(f"❌ [CATALOG] Erreur status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur récupération status: {str(e)}"
        )


@router.post("/warmup")
async def warmup_catalog_cache(
    company_ids: list[str],
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    🔥 PRÉCHAUFFE LE CACHE AU DÉMARRAGE
    
    Charge les catalogues des entreprises actives en cache Redis
    pour éviter les cold starts.
    
    Args:
        company_ids: Liste des IDs d'entreprises à préchauffer
        
    Returns:
        {"success": true, "companies_queued": N}
    """
    try:
        from core.catalog_cache_manager import get_catalog_cache_manager
        
        cache_manager = get_catalog_cache_manager()
        
        async def warmup_company(cid: str):
            try:
                await cache_manager.get_catalog_cache(cid)
                logger.info(f"🔥 [WARMUP] Cache préchauffé: {cid}")
            except Exception as e:
                logger.warning(f"⚠️ [WARMUP] Erreur {cid}: {e}")
        
        # Lancer en background pour chaque entreprise
        for cid in company_ids:
            background_tasks.add_task(warmup_company, cid)
        
        return {
            "success": True,
            "message": f"Warmup lancé pour {len(company_ids)} entreprises",
            "companies_queued": len(company_ids),
            "timestamp": time.time()
        }
        
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="CatalogCacheManager non disponible"
        )
    except Exception as e:
        logger.error(f"❌ [CATALOG] Erreur warmup: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur warmup: {str(e)}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT DEBUG/TEST
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/test-extraction")
async def test_regex_extraction(message: str) -> Dict[str, Any]:
    """
    🧪 TEST D'EXTRACTION REGEX
    
    Teste l'extraction de zone de livraison et numéro de téléphone
    depuis un message utilisateur.
    
    Args:
        message: Message à analyser
        
    Returns:
        {
            "delivery_zone": {...} | null,
            "phone_number": {...} | null,
            "keywords": {...},
            "has_instant_answer": bool
        }
    """
    try:
        from core.catalog_cache_manager import get_catalog_cache_manager
        
        cache_manager = get_catalog_cache_manager()
        
        # Extraction regex
        regex_results = cache_manager.extract_regex_fast(message)
        
        # Détection keywords
        keywords = cache_manager.detect_keywords(message)
        
        return {
            "message": message,
            "delivery_zone": regex_results.get('delivery_zone'),
            "phone_number": regex_results.get('phone_number'),
            "instant_context": regex_results.get('instant_context'),
            "has_instant_answer": regex_results.get('has_instant_answer', False),
            "keywords": keywords
        }
        
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="CatalogCacheManager non disponible"
        )
    except Exception as e:
        logger.error(f"❌ [CATALOG] Erreur test: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur test extraction: {str(e)}"
        )
