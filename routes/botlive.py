"""
🤖 BOTLIVE API - Routes pour intégration Frontend/N8N
Endpoints pour le système de commandes en direct
"""

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging
import time
import uuid
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/botlive", tags=["botlive"])

# ═══════════════════════════════════════════════════════════════════════════════
# 📋 MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class BotliveMessageRequest(BaseModel):
    """Requête pour envoyer un message au bot"""
    company_id: str = Field(..., description="ID de l'entreprise")
    user_id: str = Field(..., description="ID utilisateur (numéro WhatsApp/Messenger)")
    message: str = Field(default="", description="Message texte")
    images: List[str] = Field(default=[], description="URLs des images")
    conversation_history: str = Field(default="", description="Historique conversation")

class BotliveStatsRequest(BaseModel):
    """Requête pour les statistiques"""
    company_id: str
    time_range: str = Field(default="today", description="today, week, month")

class BotliveOrderStatusRequest(BaseModel):
    """Requête pour vérifier le statut d'une commande"""
    user_id: str
    company_id: str

class WebhookConfig(BaseModel):
    """Configuration webhook N8N"""
    webhook_url: str = Field(..., description="URL webhook N8N")
    events: List[str] = Field(default=["order_completed", "payment_validated", "intervention_required"])
    company_id: str

class DepositRequest(BaseModel):
    company_id: str = Field(..., description="ID de l'entreprise")
    amount_xof: int = Field(..., description="Montant de l'acompte en XOF")
    order_id: Optional[str] = None
    payment_method: Optional[str] = None
    validated_by: str = "ocr_easy"

# ═══════════════════════════════════════════════════════════════════════════════
# 🔥 ENDPOINTS PRINCIPAUX
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/message")
async def process_botlive_message(req: BotliveMessageRequest, background_tasks: BackgroundTasks):
    """
    🎯 ENDPOINT PRINCIPAL - Traite un message utilisateur (texte + images)
    
    Utilisé par:
    - Frontend (interface chat)
    - N8N (orchestration WhatsApp/Messenger)
    
    Returns:
        {
            "response": "Réponse du bot",
            "order_status": {...},
            "next_step": "produit|paiement|zone|numero|completed"
        }
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[BOTLIVE][{request_id}] Message reçu: user={req.user_id}, company={req.company_id}")
    
    try:
        # Traiter le message
        start_time = time.time()
        
        # Import lazy pour éviter circular import
        import app
        response = await app._botlive_handle(
            company_id=req.company_id,
            user_id=req.user_id,
            message=req.message,
            images=req.images,
            conversation_history=req.conversation_history
        )
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Récupérer l'état de la commande
        order_status = await get_order_state(req.user_id, req.company_id)
        
        # Déterminer la prochaine étape
        next_step = _determine_next_step(order_status)
        
        logger.info(f"[BOTLIVE][{request_id}] Réponse générée en {duration_ms}ms, next_step={next_step}")
        
        # Déclencher webhook si commande complétée
        if next_step == "completed":
            background_tasks.add_task(trigger_webhook, "order_completed", {
                "user_id": req.user_id,
                "company_id": req.company_id,
                "order_status": order_status
            })
        
        return JSONResponse(content={
            "success": True,
            "response": response,
            "order_status": order_status,
            "next_step": next_step,
            "duration_ms": duration_ms,
            "request_id": request_id
        })
        
    except Exception as e:
        logger.error(f"[BOTLIVE][{request_id}] Erreur: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur traitement message: {str(e)}")

@router.post("/message/stream")
async def process_botlive_message_stream(req: BotliveMessageRequest):
    """
    🌊 ENDPOINT STREAMING - Réponse en temps réel (SSE)
    
    Pour une meilleure UX avec affichage progressif de la réponse
    """
    request_id = str(uuid.uuid4())[:8]
    
    async def event_generator():
        try:
            # Import
            from app import _botlive_handle
            
            # Envoyer événement de démarrage
            yield f"data: {{'event': 'start', 'request_id': '{request_id}'}}\n\n"
            
            # Traiter le message
            response = await _botlive_handle(
                company_id=req.company_id,
                user_id=req.user_id,
                message=req.message,
                images=req.images,
                conversation_history=req.conversation_history
            )
            
            # Simuler streaming (découper la réponse)
            words = response.split()
            for i, word in enumerate(words):
                yield f"data: {{'event': 'token', 'content': '{word} '}}\n\n"
                await asyncio.sleep(0.05)  # 50ms entre chaque mot
            
            # État final
            order_status = await get_order_state(req.user_id, req.company_id)
            next_step = _determine_next_step(order_status)
            
            yield f"data: {{'event': 'done', 'order_status': {order_status}, 'next_step': '{next_step}'}}\n\n"
            
        except Exception as e:
            logger.error(f"[BOTLIVE][STREAM][{request_id}] Erreur: {e}")
            yield f"data: {{'event': 'error', 'message': '{str(e)}'}}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# ═══════════════════════════════════════════════════════════════════════════════
# 📊 ENDPOINTS STATISTIQUES & MONITORING
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/stats/{company_id}")
async def get_botlive_stats(company_id: str, time_range: str = "today"):
    """
    📊 Statistiques Mode LIVE
    
    Returns:
        {
            "ca_live_session": 1247.0,
            "ca_variation": "+23%",
            "commandes_total": 34,
            "commandes_variation": "+12",
            "clients_actifs": 156,
            "interventions_requises": 2,
            "activite_temps_reel": [...]
        }
    """
    try:
        # Utiliser le module de données réelles
        from core.botlive_dashboard_data import get_live_stats
        
        stats = await get_live_stats(company_id, time_range)
        
        return JSONResponse(content=stats)
        
    except Exception as e:
        logger.error(f"[BOTLIVE][STATS] Erreur: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur stats: {str(e)}")

@router.get("/orders/active/{company_id}")
async def get_active_orders_endpoint(company_id: str, limit: int = 50):
    """
    📦 Liste des commandes actives (en cours)
    
    Pour afficher dans le frontend les commandes en attente de validation
    """
    try:
        from core.botlive_dashboard_data import get_active_orders
        
        active_orders = await get_active_orders(company_id, limit)
        
        return JSONResponse(content={
            "success": True,
            "orders": active_orders,
            "total": len(active_orders)
        })
        
    except Exception as e:
        logger.error(f"[BOTLIVE][ACTIVE_ORDERS] Erreur: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/interventions/{company_id}")
async def get_interventions_required_endpoint(company_id: str):
    """
    ⚠️ Interventions requises (alertes)
    
    Retourne les commandes nécessitant une intervention manuelle
    """
    try:
        from core.botlive_dashboard_data import get_interventions_required
        
        interventions = await get_interventions_required(company_id)
        
        return JSONResponse(content={
            "success": True,
            "interventions": interventions,
            "count": len(interventions)
        })
        
    except Exception as e:
        logger.error(f"[BOTLIVE][INTERVENTIONS] Erreur: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/activity/{company_id}")
async def get_realtime_activity_endpoint(company_id: str, limit: int = 10):
    """
    ⚡ Activité en temps réel
    
    Returns:
        [
            {
                "type": "commande_enregistree",
                "client": "Sophie Laurent",
                "produit": "1x Produit A",
                "timestamp": "il y a 2 min"
            },
            ...
        ]
    """
    try:
        from core.botlive_dashboard_data import get_realtime_activity
        
        activities = await get_realtime_activity(company_id, limit)
        
        return JSONResponse(content={
            "success": True,
            "activities": activities
        })
        
    except Exception as e:
        logger.error(f"[BOTLIVE][ACTIVITY] Erreur: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/deposits")
async def create_deposit(req: DepositRequest):
    try:
        from core.botlive_dashboard_data import insert_deposit

        deposit = await insert_deposit(
            company_id=req.company_id,
            amount_xof=req.amount_xof,
            order_id=req.order_id,
            payment_method=req.payment_method,
            validated_by=req.validated_by,
        )

        return JSONResponse(content={
            "success": True,
            "deposit": deposit,
        })

    except Exception as e:
        logger.error(f"[BOTLIVE][DEPOSITS][CREATE] Erreur: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/deposits/{company_id}")
async def list_deposits(company_id: str, limit: int = 50):
    try:
        from core.botlive_dashboard_data import _fetch_deposits

        now = datetime.utcnow()
        start_date = now - timedelta(days=30)
        deposits = await _fetch_deposits(company_id, start_date, now)
        deposits_sorted = sorted(deposits, key=lambda d: d.get("validated_at", ""), reverse=True)

        return JSONResponse(content={
            "success": True,
            "deposits": deposits_sorted[:limit],
            "total": len(deposits_sorted),
        })

    except Exception as e:
        logger.error(f"[BOTLIVE][DEPOSITS][LIST] Erreur: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════════════════════════════════════════
# 🔗 ENDPOINTS WEBHOOKS N8N
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/webhook/register")
async def register_webhook(config: WebhookConfig):
    """
    📡 Enregistrer un webhook N8N
    
    Permet à N8N de s'abonner aux événements Botlive
    """
    try:
        # TODO: Stocker config webhook dans Supabase
        logger.info(f"[BOTLIVE][WEBHOOK] Enregistrement webhook: {config.webhook_url}")
        
        return JSONResponse(content={
            "success": True,
            "message": "Webhook enregistré",
            "config": config.dict()
        })
        
    except Exception as e:
        logger.error(f"[BOTLIVE][WEBHOOK] Erreur enregistrement: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhook/test")
async def test_webhook(webhook_url: str):
    """
    🧪 Tester un webhook
    
    Envoie un événement de test pour vérifier la connexion N8N
    """
    try:
        import httpx
        
        test_payload = {
            "event": "test",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "message": "Test webhook Botlive"
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=test_payload, timeout=5.0)
            
        return JSONResponse(content={
            "success": response.status_code == 200,
            "status_code": response.status_code,
            "response": response.text[:200]
        })
        
    except Exception as e:
        logger.error(f"[BOTLIVE][WEBHOOK][TEST] Erreur: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════════════════════════════════════════
# 🛠️ HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

async def get_order_state(user_id: str, company_id: str) -> Dict[str, Any]:
    """Récupère l'état actuel de la commande"""
    try:
        from core.order_state_tracker import order_tracker
        
        state = order_tracker.get_state(user_id)
        
        return {
            "produit": state.produit or "",
            "paiement": state.paiement or "",
            "zone": state.zone or "",
            "numero": state.numero or "",
            "completion_rate": state.get_completion_rate(),
            "is_complete": state.is_complete()
        }
    except Exception as e:
        logger.error(f"[BOTLIVE] Erreur get_order_state: {e}")
        return {
            "produit": "",
            "paiement": "",
            "zone": "",
            "numero": "",
            "completion_rate": 0,
            "is_complete": False
        }

def _determine_next_step(order_status: Dict[str, Any]) -> str:
    """Détermine la prochaine étape du workflow"""
    if order_status["is_complete"]:
        return "completed"
    elif not order_status["produit"]:
        return "produit"
    elif not order_status["paiement"]:
        return "paiement"
    elif not order_status["zone"]:
        return "zone"
    elif not order_status["numero"]:
        return "numero"
    else:
        return "completed"

async def trigger_webhook(event_type: str, data: Dict[str, Any]):
    """Déclenche un webhook N8N"""
    try:
        # TODO: Récupérer webhook URL depuis Supabase
        # TODO: Envoyer requête HTTP au webhook
        logger.info(f"[BOTLIVE][WEBHOOK] Événement: {event_type}, data: {data}")
        pass
    except Exception as e:
        logger.error(f"[BOTLIVE][WEBHOOK] Erreur trigger: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 ENDPOINTS ADMIN
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/admin/clear-state/{user_id}")
async def clear_user_state(user_id: str):
    """🗑️ Réinitialiser l'état d'une commande (admin)"""
    try:
        from core.order_state_tracker import order_tracker
        order_tracker.clear_state(user_id)
        
        return JSONResponse(content={
            "success": True,
            "message": f"État réinitialisé pour {user_id}"
        })
    except Exception as e:
        logger.error(f"[BOTLIVE][ADMIN] Erreur clear_state: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def botlive_health():
    """🏥 Health check du système Botlive"""
    try:
        from core.botlive_engine import get_botlive_engine
        
        # Vérifier que le moteur est initialisé
        engine = get_botlive_engine()
        
        return JSONResponse(content={
            "status": "healthy",
            "engine": "initialized",
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"[BOTLIVE][HEALTH] Erreur: {e}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            },
            status_code=503
        )
