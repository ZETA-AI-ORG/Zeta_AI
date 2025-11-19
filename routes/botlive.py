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
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/botlive", tags=["botlive"])

DISABLE_VISION_MODELS = os.getenv("DISABLE_VISION_MODELS", "false").lower() == "true"

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

        # Construire automatiquement l'historique depuis Supabase (conversations + messages)
        conversation_history = await _build_conversation_history_from_messages(
            company_id=req.company_id,
            user_id=req.user_id,
        )

        # Import lazy pour éviter circular import
        import app
        response = await app._botlive_handle(
            company_id=req.company_id,
            user_id=req.user_id,
            message=req.message,
            images=req.images,
            conversation_history=conversation_history
        )
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Récupérer l'état de la commande
        order_status = await get_order_state(req.user_id, req.company_id)
        
        # Déterminer la prochaine étape
        next_step = _determine_next_step(order_status)

        conversation_id = None
        try:
            from core.conversations_manager import get_or_create_conversation, insert_message
            from core.activities_logger import log_new_conversation
            conversation_id = await get_or_create_conversation(req.company_id, req.user_id)
            if conversation_id:
                await insert_message(
                    conversation_id,
                    "user",
                    req.message or "",
                    {"source": "botlive", "channel": "messenger"}
                )
                if isinstance(response, str) and response:
                    await insert_message(
                        conversation_id,
                        "assistant",
                        response,
                        {"source": "botlive", "channel": "bot"}
                    )
                await log_new_conversation(req.company_id, req.user_id, conversation_id)
        except Exception as conv_err:
            logger.error(f"[BOTLIVE][{request_id}] Erreur logging conversation/messages: {conv_err}")

        if next_step == "completed" and conversation_id:
            try:
                from core.orders_manager import create_order
                from core.activities_logger import log_order_created
                from core.supabase_notepad import get_supabase_notepad

                produit = ""
                numero_client = req.user_id[-4:]
                if isinstance(order_status, dict):
                    produit = order_status.get("produit") or ""
                    numero_client = order_status.get("numero") or numero_client

                # Montant dynamique depuis le notepad Supabase (si disponible)
                total_amount = 2000.0
                try:
                    notepad_manager = get_supabase_notepad()
                    notepad = await notepad_manager.get_notepad(req.user_id, req.company_id)
                    paiement_info = notepad.get("paiement") or {}
                    montant_notepad = paiement_info.get("montant") or paiement_info.get("amount")
                    if montant_notepad:
                        total_amount = float(montant_notepad)
                except Exception as np_err:
                    logger.warning(f"[BOTLIVE][{request_id}] Impossible de lire montant notepad: {np_err}")

                items = [{"name": produit or "Commande Botlive", "quantity": 1, "price": total_amount}]
                order = await create_order(
                    company_id=req.company_id,
                    user_id=req.user_id,
                    customer_name=numero_client,
                    total_amount=total_amount,
                    items=items,
                    conversation_id=conversation_id
                )
                if order and isinstance(order, dict) and order.get("id"):
                    await log_order_created(req.company_id, numero_client, order["id"], total_amount)
            except Exception as order_err:
                logger.error(f"[BOTLIVE][{request_id}] Erreur création commande/activité: {order_err}")
        
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

@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str, limit: int = 50):
    try:
        import httpx
        from core.botlive_dashboard_data import SUPABASE_URL, SUPABASE_KEY

        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
        }
        url = f"{SUPABASE_URL}/rest/v1/messages"
        params = {
            "conversation_id": f"eq.{conversation_id}",
            "select": "*",
            "order": "created_at.asc",
            "limit": str(limit),
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers, params=params)

        if resp.status_code == 200:
            return JSONResponse(content={"success": True, "messages": resp.json()})

        logger.error(f"[BOTLIVE][MESSAGES] Erreur fetch messages: {resp.status_code} - {resp.text}")
        return JSONResponse(content={"success": False, "error": "Erreur récupération messages"}, status_code=500)

    except Exception as e:
        logger.error(f"[BOTLIVE][MESSAGES] Exception: {e}")
        raise HTTPException(status_code=500, detail="Erreur récupération messages")


@router.post("/interventions/{conversation_id}/take-over")
async def take_over_intervention(conversation_id: str):
    try:
        import httpx
        from core.botlive_dashboard_data import SUPABASE_URL, SUPABASE_KEY

        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
        }
        url = f"{SUPABASE_URL}/rest/v1/conversations"
        params = {"id": f"eq.{conversation_id}"}
        payload = {
            "priority": "high",
            "status": "in_progress",
            "updated_at": datetime.utcnow().isoformat(),
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.patch(url, headers=headers, params=params, json=payload)

        if resp.status_code in (200, 204):
            return JSONResponse(content={"success": True})

        logger.error(f"[BOTLIVE][INTERVENTIONS] Erreur take-over: {resp.status_code} - {resp.text}")
        return JSONResponse(content={"success": False, "error": "Erreur mise à jour intervention"}, status_code=500)

    except Exception as e:
        logger.error(f"[BOTLIVE][INTERVENTIONS] Exception take-over: {e}")
        raise HTTPException(status_code=500, detail="Erreur prise en charge intervention")


@router.post("/interventions/{conversation_id}/resolve")
async def resolve_intervention(conversation_id: str):
    try:
        import httpx
        from core.botlive_dashboard_data import SUPABASE_URL, SUPABASE_KEY

        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
        }
        url = f"{SUPABASE_URL}/rest/v1/conversations"
        params = {"id": f"eq.{conversation_id}"}
        payload = {
            "priority": "normal",
            "status": "resolved",
            "updated_at": datetime.utcnow().isoformat(),
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.patch(url, headers=headers, params=params, json=payload)

        if resp.status_code in (200, 204):
            return JSONResponse(content={"success": True})

        logger.error(f"[BOTLIVE][INTERVENTIONS] Erreur resolve: {resp.status_code} - {resp.text}")
        return JSONResponse(content={"success": False, "error": "Erreur résolution intervention"}, status_code=500)

    except Exception as e:
        logger.error(f"[BOTLIVE][INTERVENTIONS] Exception resolve: {e}")
        raise HTTPException(status_code=500, detail="Erreur résolution intervention")


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


async def _build_conversation_history_from_messages(company_id: str, user_id: str, max_messages: int = 20) -> str:
    """Reconstruit l'historique textuel depuis les tables conversations/messages.

    Format de sortie aligné avec les anciens tests Botlive:
        user: Bonjour, je veux commander
        IA: D'accord ! ...

    On récupère la conversation la plus récente pour (company_id_text, user_id)
    puis les messages associés, triés par created_at asc.
    """
    try:
        import httpx
        from core.botlive_dashboard_data import SUPABASE_URL, SUPABASE_KEY
        from core.conversations_manager import _get_company_uuid

        # Mapper company_id texte -> UUID si possible
        company_uuid = await _get_company_uuid(company_id)
        if not company_uuid:
            company_uuid = company_id

        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
        }

        # 1) Récupérer la conversation la plus récente pour ce couple
        conv_url = f"{SUPABASE_URL}/rest/v1/conversations"
        conv_params = [
            ("company_id", f"eq.{company_uuid}"),
            # Le schéma Lovable n'a pas de colonne user_id, on utilise customer_name
            ("customer_name", f"eq.{user_id}"),
            ("select", "id"),
            ("order", "created_at.desc"),
            ("limit", "1"),
        ]

        async with httpx.AsyncClient(timeout=10.0) as client:
            conv_resp = await client.get(conv_url, headers=headers, params=conv_params)

        if conv_resp.status_code != 200:
            logger.error(f"[BOTLIVE][HISTORY] Erreur fetch conversations: {conv_resp.status_code} - {conv_resp.text}")
            return ""

        conversations = conv_resp.json() or []
        if not conversations:
            return ""

        conversation_id = conversations[0].get("id")
        if not conversation_id:
            return ""

        # 2) Récupérer les messages de cette conversation
        msg_url = f"{SUPABASE_URL}/rest/v1/messages"
        msg_params = [
            ("conversation_id", f"eq.{conversation_id}"),
            ("select", "role,content,created_at"),
            ("order", "created_at.asc"),
            ("limit", str(max_messages)),
        ]

        async with httpx.AsyncClient(timeout=10.0) as client:
            msg_resp = await client.get(msg_url, headers=headers, params=msg_params)

        if msg_resp.status_code != 200:
            logger.error(f"[BOTLIVE][HISTORY] Erreur fetch messages: {msg_resp.status_code} - {msg_resp.text}")
            return ""

        messages = msg_resp.json() or []
        if not messages:
            return ""

        # 3) Construire l'historique textuel user:/IA:
        lines = []
        for m in messages:
            role = (m.get("role") or "").lower()
            content = m.get("content") or ""
            # Les tables Lovable stockent déjà content en texte
            prefix = "user:" if role == "user" else "IA:"
            lines.append(f"{prefix} {content}".strip())

        history = "\n".join(lines)
        logger.info(f"[BOTLIVE][HISTORY] Reconstruit {len(messages)} messages pour {user_id} ({len(history)} chars)")
        return history

    except Exception as e:
        logger.error(f"[BOTLIVE][HISTORY] Exception reconstruction historique: {e}")
        return ""

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
        if DISABLE_VISION_MODELS:
            return JSONResponse(content={
                "status": "healthy",
                "engine": "disabled",
                "timestamp": datetime.utcnow().isoformat()
            })

        from core.botlive_engine import get_botlive_engine

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
