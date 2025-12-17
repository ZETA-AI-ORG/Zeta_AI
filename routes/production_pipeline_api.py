from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Dict, Any
from core.production_pipeline import ProductionPipeline

router = APIRouter(prefix="/pipeline", tags=["production_pipeline"])
pipeline = ProductionPipeline()

class RouteMessageRequest(BaseModel):
    company_id: str
    user_id: str
    message: str
    conversation_history: str = ""
    state_compact: Dict[str, Any] = {}
    hyde_pre_enabled: bool | None = None

@router.post("/route_message")
async def route_message(req: RouteMessageRequest):
    result = await pipeline.route_message(
        req.company_id,
        req.user_id,
        req.message,
        req.conversation_history,
        req.state_compact,
        req.hyde_pre_enabled,
    )
    return result

@router.get("/stats")
def get_stats():
    return pipeline.get_stats()
