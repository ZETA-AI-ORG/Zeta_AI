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

logger.info("✅ App minimal initialisée avec succès")
