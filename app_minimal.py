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
import asyncio
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import List

# Logger minimal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

# FastAPI app
app = FastAPI(title="ZETA AI Backend - Minimal")


@app.on_event("startup")
async def _startup_prompt_listener():
    """Lance le listener pg_notify pour invalider le cache prompt en temps réel."""
    try:
        from core.prompt_cache_listener import start_prompt_cache_listener
        asyncio.create_task(start_prompt_cache_listener())
        logger.info("✅ [STARTUP] Listener pg_notify 'prompt_cache_invalidate' lancé")
    except Exception as _e:
        logger.warning("⚠️ [STARTUP] Listener pg_notify non lancé: %s", _e)



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


async def _bg_intervention_check(
    company_id: str, user_id: str, user_message: str, bot_response: str,
) -> None:
    """Background task: check intervention after RAGBot response."""
    try:
        from routes.botlive import _compute_rule_based_intervention
        from core.intervention_logger import log_intervention_in_conversation_logs

        rule = _compute_rule_based_intervention(user_message)
        if not rule.get("requires_intervention"):
            return
        await log_intervention_in_conversation_logs(
            company_id_text=company_id,
            user_id=user_id,
            message=rule.get("reason") or user_message,
            metadata={
                "needs_intervention": True,
                "reason": rule.get("reason"),
                "priority": "critical" if rule.get("reason") == "explicit_handoff" else "high",
                "caps_ratio": rule.get("caps_ratio"),
                "source": "ragbot",
                "detected_by": "rule_based",
                "source_bot": "ragbot",
            },
            channel="whatsapp",
            direction="system",
            source="ragbot_bg_check",
        )
        logger.info(
            "[RAGBOT][INTERVENTION] Detected %s for user=%s company=%s",
            rule.get("reason"), user_id, company_id,
        )
    except Exception as exc:
        logger.warning("[RAGBOT][INTERVENTION] bg check failed: %s", exc)


@app.post("/chat")
async def chat(chat_request: ChatRequest, background_tasks: BackgroundTasks):
    """Endpoint principal pour le chat"""
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
                    logger.info(
                        "[RAG_EXACT_CACHE] HIT company_id=%s user_id=%s prompt_version=%s",
                        chat_request.company_id,
                        chat_request.user_id,
                        prompt_version,
                    )
                    return {"status": "success", "response": cached_response}
                logger.debug(
                    "[RAG_EXACT_CACHE] MISS company_id=%s user_id=%s prompt_version=%s",
                    chat_request.company_id,
                    chat_request.user_id,
                    prompt_version,
                )
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
                logger.info(
                    "[RAG_EXACT_CACHE] SET company_id=%s user_id=%s prompt_version=%s ttl=%s",
                    chat_request.company_id,
                    chat_request.user_id,
                    prompt_version,
                    ttl,
                )
            except Exception:
                pass

        _ = time.time() - start_ts
        background_tasks.add_task(
            _bg_intervention_check,
            company_id=chat_request.company_id,
            user_id=chat_request.user_id,
            user_message=chat_request.message,
            bot_response=response if isinstance(response, str) else str(response),
        )
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

@app.post("/api/cache/invalidate-prompt")
async def invalidate_prompt_cache(company_id: str = None):
    """
    🧹 INVALIDE LE CACHE DES PROMPTS
    Appelé par Supabase Trigger via HTTP POST.
    """
    try:
        from core.simplified_prompt_system import get_simplified_prompt_system
        prompt_system = get_simplified_prompt_system()
        prompt_system.invalidate_cache(company_id=company_id)
        
        return {
            "status": "success",
            "message": f"Cache prompt invalidé pour {'tous' if not company_id else company_id}",
            "company_id": company_id,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"[CACHE_INVALIDATE] Erreur: {e}")
        return {"status": "error", "message": str(e)}

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
        from routes.botlive import router as botlive_router, shared_router as botliveandrag_router

        app.include_router(botlive_router, tags=["Botlive"])  # Pas de prefix, déjà dans le router
        app.include_router(botliveandrag_router, tags=["BotliveAndRag"])  # Pas de prefix, déjà dans le router
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

# Étape 4 : Notifications + Push
try:
    from routes.notifications import router as notifications_router
    app.include_router(notifications_router, tags=["Notifications"])
    logger.info("✅ Routes Notifications + Push chargées")
except Exception as e:
    logger.warning(f"⚠️ Erreur chargement Notifications routes: {e}")

logger.info("✅ App minimal initialisée avec succès")
