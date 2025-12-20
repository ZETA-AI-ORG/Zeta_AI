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
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Logger minimal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

# FastAPI app
app = FastAPI(title="ZETA AI Backend - Minimal")

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
# try:
#     from routes.botlive import router as botlive_router
#     app.include_router(botlive_router, tags=["Botlive"])  # Pas de prefix, déjà dans le router
#     logger.info("✅ Routes Botlive chargées")
# except Exception as e:
#     logger.warning(f"⚠️ Erreur chargement Botlive routes: {e}")
logger.info("⚠️ Routes Botlive désactivées temporairement pour Render")

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
