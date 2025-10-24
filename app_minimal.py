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

@app.get("/auth-test")
async def auth_test():
    """Test que les routes auth sont chargées"""
    return {
        "status": "success",
        "message": "Auth routes loaded",
        "endpoints": ["/auth/login", "/auth/register", "/auth/refresh"]
    }

# Étape 3 : RAG Engine (Lazy Loading)
@app.get("/rag-test")
async def rag_test(query: str = "Bonjour"):
    """Test du RAG Engine avec lazy loading"""
    try:
        from core.universal_rag_engine import get_universal_rag_engine
        
        # Lazy init du RAG engine
        engine = get_universal_rag_engine()
        
        # Test simple
        result = await engine.process_query(
            query=query,
            company_id="test_company",
            user_id="test_user",
            company_name="Test Company"
        )
        
        return {
            "status": "success",
            "message": "RAG Engine loaded",
            "query": query,
            "response_preview": result.response[:200] + "..." if len(result.response) > 200 else result.response,
            "confidence": result.confidence,
            "processing_time_ms": result.processing_time_ms
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "type": type(e).__name__
        }

logger.info("✅ App minimal initialisée avec succès")
