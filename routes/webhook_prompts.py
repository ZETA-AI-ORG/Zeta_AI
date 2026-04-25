import os
import logging
import json
from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from core.company_cache_manager import company_cache
from core.botlive_prompts_supabase import prompts_manager

router = APIRouter(prefix="/api/webhook", tags=["webhooks"])
logger = logging.getLogger(__name__)

ZETA_AUTH_SECRET = os.getenv("ZETA_AUTH_SECRET", "zeta_diagnostic_default_secret")

@router.post("/invalidate-company")
async def invalidate_company(request: Request):
    """
    Invalide le cache d'une entreprise spécifique (Profil + Prompt).
    """
    try:
        data = await request.json()
        company_id = data.get("company_id")
        if not company_id:
            return JSONResponse({"status": "error", "message": "Missing company_id"}, status_code=400)
        
        # 1. Invalider le profil (Redis DB 0)
        await company_cache.invalidate_cached_profile(company_id)
        
        # 2. Invalider le prompt
        prompts_manager.invalidate_cache(company_id)
        
        logger.info(f"🗑️ [WEBHOOK] Cache global invalidé pour {company_id}")
        return {"status": "ok", "message": f"Cache invalidated for {company_id}"}
    except Exception as e:
        logger.error(f"❌ [WEBHOOK] Erreur invalidation: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@router.post("/sync-companies")
async def sync_companies(request: Request):
    """
    Synchronise massivement toutes les entreprises actives de Supabase vers Redis.
    """
    auth = request.headers.get("X-ZETA-AUTH")
    if auth != ZETA_AUTH_SECRET:
        return JSONResponse({"status": "error", "message": "Unauthorized"}, status_code=401)
        
    try:
        result = await company_cache.sync_all_companies()
        return result
    except Exception as e:
        logger.error(f"❌ [WEBHOOK] Erreur sync globale: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
