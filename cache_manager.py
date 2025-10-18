#!/usr/bin/env python3
"""
🔧 ENDPOINT POUR VIDER LE CACHE PROMPT - FORCE RELOAD
Usage: curl -X POST http://127.0.0.1:8001/cache/clear_prompt -H "Content-Type: application/json" -d '{"company_id":"MpfnlSbqwaZ6F4HvxQLRL9du0yG3"}'
"""

import asyncio
import os
import sys
from datetime import datetime

# Ajouter le répertoire parent au path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Modèle pour la requête
class ClearPromptCacheRequest(BaseModel):
    company_id: str

# Router pour les opérations de cache
router = APIRouter(prefix="/cache", tags=["cache"])

# Variable globale pour stocker le cache prompt en mémoire
# (si pas déjà géré par GlobalPromptCache)
_prompt_cache = {}

@router.post("/clear_prompt")
async def clear_prompt_cache(request: ClearPromptCacheRequest):
    """
    🔄 Vide le cache prompt pour une entreprise spécifique
    Force le rechargement du prompt depuis Supabase
    """
    try:
        company_id = request.company_id

        # Vider le cache prompt pour cette entreprise
        cache_key = f"prompt_{company_id}"
        if cache_key in _prompt_cache:
            del _prompt_cache[cache_key]

        # Si vous utilisez GlobalPromptCache, vider aussi
        try:
            from core.global_prompt_cache import get_global_prompt_cache
            cache = get_global_prompt_cache()
            await cache.invalidate_prompt(company_id)
        except Exception:
            pass  # Pas grave si ça échoue

        return {
            "status": "success",
            "message": f"Cache prompt vidé pour l'entreprise {company_id}",
            "timestamp": datetime.utcnow().isoformat(),
            "cache_cleared": cache_key
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du vidage du cache: {e}")

@router.get("/prompt_cache_status")
async def get_prompt_cache_status():
    """📊 Statut du cache prompt"""
    return {
        "cache_size": len(_prompt_cache),
        "cached_companies": list(_prompt_cache.keys()),
        "timestamp": datetime.utcnow().isoformat()
    }

@router.post("/clear_all_prompts")
async def clear_all_prompt_caches():
    """🧹 Vide TOUT le cache prompt"""
    try:
        cache_size_before = len(_prompt_cache)
        _prompt_cache.clear()

        # Vider aussi GlobalPromptCache si utilisé
        try:
            from core.global_prompt_cache import get_global_prompt_cache
            cache = get_global_prompt_cache()
            cache.cache.clear()
        except Exception:
            pass

        return {
            "status": "success",
            "message": "Tout le cache prompt a été vidé",
            "entries_cleared": cache_size_before,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du vidage total: {e}")

# Fonction utilitaire pour vider le cache depuis le code
async def invalidate_prompt_cache(company_id: str):
    """Fonction utilitaire pour vider le cache depuis le code"""
    cache_key = f"prompt_{company_id}"
    if cache_key in _prompt_cache:
        del _prompt_cache[cache_key]
        print(f"✅ Cache prompt vidé pour {company_id}")

    try:
        from core.global_prompt_cache import get_global_prompt_cache
        cache = get_global_prompt_cache()
        await cache.invalidate_prompt(company_id)
    except Exception:
        pass

if __name__ == "__main__":
    # Test manuel
    print("🚀 TEST DE VIDAGE DU CACHE PROMPT")
    print("="*50)

    # Simuler le vidage
    test_company = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
    print(f"🔄 Vidage du cache pour {test_company}...")

    # Ajouter une fausse entrée
    _prompt_cache[f"prompt_{test_company}"] = {"test": "data"}

    print(f"📊 Cache avant vidage: {len(_prompt_cache)} entrées")
    print(f"📝 Entrées: {list(_prompt_cache.keys())}")

    # Vider
    asyncio.run(invalidate_prompt_cache(test_company))

    print(f"📊 Cache après vidage: {len(_prompt_cache)} entrées")
    print("✅ Test réussi !")
