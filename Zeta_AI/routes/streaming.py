"""
🚀 ROUTES STREAMING - ENDPOINT PARALLÈLE
Nouveau endpoint sans toucher à l'existant
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from core.streaming_engine import streaming_engine
from core.models import ChatRequest
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class StreamingChatRequest(BaseModel):
    """Modèle de requête pour streaming - identique à l'existant"""
    message: str
    user_id: str
    company_id: str
    conversation_id: str = None

@router.post("/chat/stream")
async def stream_chat(request: StreamingChatRequest):
    """
    🚀 ENDPOINT STREAMING PARALLÈLE
    - Même interface que /chat mais avec streaming
    - Compatible avec EventSource côté frontend
    - ZÉRO impact sur l'endpoint existant
    """
    
    try:
        # Validation identique à l'existant
        if not request.message or not request.message.strip():
            raise HTTPException(status_code=400, detail="Message requis")
        
        if not request.company_id:
            raise HTTPException(status_code=400, detail="Company ID requis")
        
        logger.info(f"[STREAMING] Nouvelle requête: {request.message[:50]}...")
        
        # Streaming de la réponse
        return StreamingResponse(
            streaming_engine.stream_search_progress(
                query=request.message,
                company_id=request.company_id
            ),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[STREAMING] Erreur: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@router.get("/chat/stream/test")
async def test_streaming():
    """Endpoint de test pour le streaming"""
    
    async def test_generator():
        import asyncio
        import json
        import time
        
        for i in range(10):
            yield f"data: {json.dumps({'type': 'test', 'count': i, 'timestamp': time.time()})}\n\n"
            await asyncio.sleep(0.5)
        
        yield f"data: {json.dumps({'type': 'complete', 'message': 'Test terminé'})}\n\n"
    
    return StreamingResponse(
        test_generator(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )




