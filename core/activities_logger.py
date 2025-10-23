"""
⚡ ACTIVITIES LOGGER - Logger événements dans table activities (Lovable)
Utilise la table activities (UUID) créée par Lovable
"""

import httpx
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Credentials Supabase
SUPABASE_URL = "https://ilbihprkxcgsigvueeme.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlsYmlocHJreGNnc2lndnVlZW1lIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTEzMTQwNCwiZXhwIjoyMDY0NzA3NDA0fQ.Zf0EJbmP5ePGBZL5cY1tFP9FDRvJXDZ3x98zUS993GA"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

async def get_company_uuid(company_id: str) -> Optional[str]:
    """Récupère l'UUID depuis company_mapping"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/company_mapping"
        params = {
            "company_id": f"eq.{company_id}",
            "select": "uuid"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=HEADERS, params=params, timeout=5.0)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return data[0]["uuid"]
        
        return None
        
    except Exception as e:
        logger.error(f"[ACTIVITIES] Erreur get_company_uuid: {e}")
        return None

async def log_activity(
    company_id: str,
    activity_type: str,
    title: str,
    description: str = "",
    status: str = "info",
    conversation_id: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> bool:
    """
    Logger une activité dans la table activities
    
    Args:
        company_id: ID entreprise (TEXT)
        activity_type: Type d'activité (ex: "commande_enregistree", "paiement_valide")
        title: Titre court
        description: Description détaillée
        status: "success", "warning", "info", "error"
        conversation_id: ID conversation (optionnel)
        metadata: Données additionnelles (optionnel)
    
    Returns:
        True si succès, False sinon
    """
    try:
        # Récupérer UUID
        company_uuid = await get_company_uuid(company_id)
        if not company_uuid:
            logger.warning(f"[ACTIVITIES] UUID introuvable pour company_id={company_id}")
            return False
        
        # Créer activité
        url = f"{SUPABASE_URL}/rest/v1/activities"
        payload = {
            "company_id": company_uuid,
            "conversation_id": conversation_id,
            "type": activity_type,
            "title": title,
            "description": description,
            "status": status,
            "metadata": metadata or {}
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={**HEADERS, "Prefer": "return=minimal"},
                json=payload,
                timeout=5.0
            )
            
            if response.status_code == 201:
                logger.info(f"[ACTIVITIES] ✅ Activité loggée: {activity_type} - {title}")
                return True
            else:
                logger.error(f"[ACTIVITIES] Erreur: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"[ACTIVITIES] Exception log_activity: {e}")
        return False

# ═══════════════════════════════════════════════════════════════════════════════
# 🎯 HELPERS SPÉCIFIQUES PAR TYPE D'ÉVÉNEMENT
# ═══════════════════════════════════════════════════════════════════════════════

async def log_order_created(company_id: str, customer_name: str, order_id: str, total_amount: float):
    """Logger création commande"""
    return await log_activity(
        company_id=company_id,
        activity_type="commande_enregistree",
        title=f"Commande de {customer_name}",
        description=f"Montant: {total_amount} FCFA",
        status="success",
        metadata={
            "order_id": order_id,
            "customer_name": customer_name,
            "total_amount": total_amount
        }
    )

async def log_payment_validated(company_id: str, user_id: str, amount: float, reference: str = ""):
    """Logger validation paiement"""
    return await log_activity(
        company_id=company_id,
        activity_type="paiement_valide",
        title=f"Paiement validé: {amount} FCFA",
        description=f"Référence: {reference}" if reference else "",
        status="success",
        metadata={
            "user_id": user_id,
            "amount": amount,
            "reference": reference
        }
    )

async def log_payment_issue(company_id: str, user_id: str, issue_type: str, message: str):
    """Logger problème paiement"""
    return await log_activity(
        company_id=company_id,
        activity_type="intervention",
        title=f"Intervention requise: {issue_type}",
        description=message,
        status="warning",
        metadata={
            "user_id": user_id,
            "issue_type": issue_type
        }
    )

async def log_new_conversation(company_id: str, user_id: str, conversation_id: str):
    """Logger nouvelle conversation"""
    return await log_activity(
        company_id=company_id,
        activity_type="nouvelle_requete_client",
        title="Nouvelle conversation",
        description=f"Client: {user_id[-4:]}",
        status="info",
        conversation_id=conversation_id,
        metadata={
            "user_id": user_id
        }
    )

async def log_session_started(company_id: str, mode: str, session_id: str):
    """Logger démarrage session"""
    return await log_activity(
        company_id=company_id,
        activity_type="session_started",
        title=f"Mode {mode.upper()} activé",
        description=f"Session ID: {session_id}",
        status="info",
        metadata={
            "mode": mode,
            "session_id": session_id
        }
    )

async def log_session_ended(company_id: str, mode: str, session_id: str, duration_minutes: int):
    """Logger fin session"""
    return await log_activity(
        company_id=company_id,
        activity_type="session_ended",
        title=f"Mode {mode.upper()} désactivé",
        description=f"Durée: {duration_minutes} minutes",
        status="info",
        metadata={
            "mode": mode,
            "session_id": session_id,
            "duration_minutes": duration_minutes
        }
    )

async def log_error(company_id: str, error_type: str, error_message: str, context: Dict = None):
    """Logger erreur système"""
    return await log_activity(
        company_id=company_id,
        activity_type="error",
        title=f"Erreur: {error_type}",
        description=error_message,
        status="error",
        metadata={
            "error_type": error_type,
            "context": context or {}
        }
    )
