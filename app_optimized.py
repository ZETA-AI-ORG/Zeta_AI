"""
🚀 APPLICATION PRINCIPALE OPTIMISÉE
Intègre la nouvelle architecture de recherche sémantique
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Import de la nouvelle architecture
from core.optimized_rag_engine import get_rag_response
from utils import log3
from core.global_embedding_cache import initialize_global_cache, cleanup_global_cache

app = FastAPI(title="Chatbot RAG Optimisé", version="2.0")

# Événements de cycle de vie pour le cache global
@app.on_event("startup")
async def startup_event():
    """Initialisation du cache global au démarrage"""
    await initialize_global_cache()
    log3("[APP_OPTIMIZED]", "🚀 Cache global d'embeddings initialisé")

@app.on_event("shutdown")
async def shutdown_event():
    """Nettoyage du cache global à l'arrêt"""
    await cleanup_global_cache()
    log3("[APP_OPTIMIZED]", "🧹 Cache global d'embeddings nettoyé")

class ChatRequest(BaseModel):
    company_id: str
    user_id: str
    message: str

class ChatResponse(BaseModel):
    response: str
    status: str = "success"

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    🎯 ENDPOINT CHAT OPTIMISÉ
    Utilise la nouvelle architecture RAG
    """
    try:
        log3("[API]", f"📨 Nouvelle requête: {request.company_id}/{request.user_id}")
        
        # Validation
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Message vide")
        
        # Traitement avec le nouveau moteur RAG
        response = await get_rag_response(
            company_id=request.company_id,
            user_id=request.user_id,
            message=request.message
        )
        
        log3("[API]", f"✅ Réponse générée: {len(response)} caractères")
        
        return ChatResponse(response=response)
        
    except Exception as e:
        log3("[API]", f"💥 Erreur: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur interne")

@app.get("/health")
async def health_check():
    """Vérification de santé"""
    return {"status": "healthy", "version": "2.0"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
