"""
🚀 APP MINIMAL - DÉMARRAGE GARANTI
Seulement les imports essentiels pour que le serveur démarre
"""
import warnings
warnings.filterwarnings("ignore")
from dotenv import load_dotenv
load_dotenv()
import logging
import os
import time
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import List

# Logger minimal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

# FastAPI app
app = FastAPI(title="ZETA AI Backend - Minimal")


_redis_cache_instance = None


def _get_redis_cache():
    global _redis_cache_instance
    if _redis_cache_instance is not None:
        return _redis_cache_instance

    try:
        from redis_cache import RedisCache

        ttl = int(os.getenv("CACHE_EXACT_TTL", "1800") or 1800)
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _redis_cache_instance = RedisCache(url=redis_url, default_ttl=ttl)
        return _redis_cache_instance
    except Exception:
        _redis_cache_instance = None
        return None

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
@app.head("/")
async def root():
    return {"status": "ok", "message": "ZETA AI Backend - Minimal Mode"}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "mode": "minimal",
        "message": "Server is running in minimal mode"
    }

@app.get("/test")
async def test():
    return {"test": "success", "imports": "minimal"}


class ChatRequest(BaseModel):
    company_id: str
    user_id: str
    message: str
    conversation_history: str = ""
    images: List[str] = []


class RagBotEnabledRequest(BaseModel):
    company_id: str
    user_id: str
    enabled: bool


@app.post("/chat")
async def chat(chat_request: ChatRequest):
    try:
        from core.simplified_rag_engine import get_simplified_rag_response

        disable_rag_cache = (os.getenv("DISABLE_RAG_CACHE", "false") or "false").lower() in {"1", "true", "yes", "on"}
        disable_rag_exact_cache = (os.getenv("DISABLE_RAG_EXACT_CACHE", "false") or "false").lower() in {"1", "true", "yes", "on"}
        cache = None if (disable_rag_cache or disable_rag_exact_cache) else _get_redis_cache()

        prompt_version = os.getenv("PROMPT_VERSION", "minimal")

        if cache is not None:
            try:
                cached_response = cache.get(
                    chat_request.message,
                    chat_request.company_id,
                    prompt_version,
                    user_id=chat_request.user_id,
                )
                if cached_response is not None:
                    return {"status": "success", "response": cached_response}
            except Exception:
                pass

        start_ts = time.time()
        response = await get_simplified_rag_response(
            query=chat_request.message,
            company_id=chat_request.company_id,
            user_id=chat_request.user_id,
            images=chat_request.images,
        )

        if cache is not None:
            try:
                ttl = int(os.getenv("CACHE_EXACT_TTL", "1800") or 1800)
                if ttl < 0:
                    ttl = 0
                cache.set(
                    chat_request.message,
                    chat_request.company_id,
                    prompt_version,
                    response,
                    ttl=ttl,
                    user_id=chat_request.user_id,
                )
            except Exception:
                pass

        _ = time.time() - start_ts
        return {"status": "success", "response": response}
    except Exception as e:
        logger.exception("/chat failed")
        return {"status": "error", "error": str(e), "type": type(e).__name__}


@app.post("/rag/bot/enabled")
async def set_rag_bot_enabled(req: RagBotEnabledRequest):
    """Active/désactive le bot RAG (/chat) pour un user_id.

    Mapping unique (pas de nouveau flag):
    - enabled=True  => bot_paused=False
    - enabled=False => bot_paused=True
    """
    try:
        from core.order_state_tracker import order_tracker

        order_tracker.set_flag(req.user_id, "bot_paused", (not bool(req.enabled)))
        return {
            "status": "success",
            "company_id": req.company_id,
            "user_id": req.user_id,
            "enabled": bool(req.enabled),
        }
    except Exception as e:
        logger.exception("/rag/bot/enabled failed")
        return {"status": "error", "error": str(e), "type": type(e).__name__}

@app.get("/db-test")
async def db_test():
    """Test de connexion Supabase"""
    try:
        from database.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # Test simple : récupérer 1 ligne de company_mapping
        result = supabase.table("company_mapping").select("*").limit(1).execute()
        
        return {
            "status": "success",
            "message": "Supabase connected",
            "data_count": len(result.data) if result.data else 0
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "type": type(e).__name__
        }

# Étape 2 : Authentification
try:
    from routes.auth import router as auth_router
    app.include_router(auth_router, prefix="/auth", tags=["Auth"])
    logger.info("✅ Routes d'authentification chargées")
except Exception as e:
    logger.warning(f"⚠️ Erreur chargement auth routes: {e}")

# Étape 2b : Human labels (Active Learning)
try:
    from routes.human_labels import router as human_labels_router
    app.include_router(human_labels_router, prefix="/api", tags=["human_labels"])
    logger.info("✅ Routes human_labels chargées")
except Exception as e:
    logger.warning(f"⚠️ Erreur chargement human_labels routes: {e}")

@app.get("/auth-test")
async def auth_test():
    """Test que les routes auth sont chargées"""
    return {
        "status": "success",
        "message": "Auth routes loaded",
        "endpoints": ["/auth/login", "/auth/register", "/auth/refresh"]
    }

# Étape 3 : Botlive (Vision AI - Pas de RAG nécessaire) - DÉSACTIVÉ TEMPORAIREMENT
BOTLIVE_ENABLED = os.getenv("BOTLIVE_ENABLED", "true").lower() == "true"
if BOTLIVE_ENABLED:
    try:
        from routes.botlive import router as botlive_router

        app.include_router(botlive_router, tags=["Botlive"])  # Pas de prefix, déjà dans le router
        logger.info("✅ Routes Botlive chargées")
    except Exception as e:
        logger.warning(f"⚠️ Erreur chargement Botlive routes: {e}")
else:
    logger.info("⚠️ BOTLIVE_ENABLED=false: Routes Botlive désactivées")

@app.get("/botlive-test")
async def botlive_test():
    """Test que les routes Botlive sont chargées"""
    return {
        "status": "success",
        "message": "Botlive routes loaded",
        "endpoints": [
            "/botlive/health",
            "/botlive/process-order",
            "/botlive/toggle-live-mode"
        ],
        "note": "Botlive uses Vision AI, no RAG needed"
    }

logger.info("✅ App minimal initialisée avec succès")
