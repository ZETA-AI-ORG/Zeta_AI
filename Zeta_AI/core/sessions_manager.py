"""
🎮 SESSIONS MANAGER - Gestion sessions Mode LIVE/RAG
Utilise la table bot_sessions (UUID) créée par Lovable
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
    """Récupère l'UUID depuis company_mapping à partir du company_id texte"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/company_mapping"
        params = {
            # company_id ici est l'ID texte (company_id_text)
            "company_id_text": f"eq.{company_id}",
            "select": "company_id_uuid"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=HEADERS, params=params, timeout=5.0)

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return data[0]["company_id_uuid"]

        return None

    except Exception as e:
        logger.error(f"[SESSIONS] Erreur get_company_uuid: {e}")
        return None

async def start_session(company_id: str, mode: str) -> Optional[str]:
    """
    Démarre une nouvelle session
    
    Args:
        company_id: ID entreprise (TEXT)
        mode: "live" ou "rag"
    
    Returns:
        UUID de la session créée ou None si erreur
    """
    try:
        # Récupérer UUID
        company_uuid = await get_company_uuid(company_id)
        if not company_uuid:
            logger.error(f"[SESSIONS] UUID introuvable pour company_id={company_id}")
            return None
        
        # Créer session
        url = f"{SUPABASE_URL}/rest/v1/bot_sessions"
        payload = {
            "company_id": company_uuid,
            "mode": mode
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={**HEADERS, "Prefer": "return=representation"},
                json=payload,
                timeout=5.0
            )
            
            if response.status_code == 201:
                session = response.json()
                if isinstance(session, list) and len(session) > 0:
                    session = session[0]
                
                session_id = session.get("id")
                logger.info(f"[SESSIONS] ✅ Session démarrée: {session_id} (mode={mode})")
                
                # Logger activité
                try:
                    from core.activities_logger import log_session_started
                    await log_session_started(company_id, mode, session_id)
                except:
                    pass
                
                return session_id
            else:
                logger.error(f"[SESSIONS] Erreur création: {response.status_code}")
                return None
                
    except Exception as e:
        logger.error(f"[SESSIONS] Exception start_session: {e}")
        return None

async def end_session(session_id: str, company_id: str = None) -> bool:
    """
    Termine une session
    
    Args:
        session_id: UUID de la session
        company_id: ID entreprise (pour logging, optionnel)
    
    Returns:
        True si succès, False sinon
    """
    try:
        # Récupérer infos session avant de la terminer
        session_info = await get_session_by_id(session_id)
        
        # Terminer session
        url = f"{SUPABASE_URL}/rest/v1/bot_sessions"
        params = {
            "id": f"eq.{session_id}"
        }
        payload = {
            "ended_at": datetime.utcnow().isoformat()
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                url,
                headers=HEADERS,
                params=params,
                json=payload,
                timeout=5.0
            )
            
            if response.status_code == 204:
                logger.info(f"[SESSIONS] ✅ Session terminée: {session_id}")
                
                # Logger activité
                if company_id and session_info:
                    try:
                        from core.activities_logger import log_session_ended
                        started_at = datetime.fromisoformat(session_info["started_at"].replace("Z", "+00:00"))
                        duration_minutes = int((datetime.utcnow().replace(tzinfo=started_at.tzinfo) - started_at).total_seconds() / 60)
                        await log_session_ended(company_id, session_info["mode"], session_id, duration_minutes)
                    except:
                        pass
                
                return True
            else:
                logger.error(f"[SESSIONS] Erreur fin session: {response.status_code}")
                return False
                
    except Exception as e:
        logger.error(f"[SESSIONS] Exception end_session: {e}")
        return False

async def get_active_session(company_id: str) -> Optional[Dict[str, Any]]:
    """
    Récupère la session active d'une entreprise
    
    Args:
        company_id: ID entreprise (TEXT)
    
    Returns:
        Dict avec infos session ou None si aucune session active
    """
    try:
        # Récupérer UUID
        company_uuid = await get_company_uuid(company_id)
        if not company_uuid:
            return None
        
        # Récupérer session active (ended_at = NULL)
        url = f"{SUPABASE_URL}/rest/v1/bot_sessions"
        params = {
            "company_id": f"eq.{company_uuid}",
            "ended_at": "is.null",
            "select": "*",
            "order": "started_at.desc",
            "limit": "1"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=HEADERS, params=params, timeout=5.0)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return data[0]
        
        return None
        
    except Exception as e:
        logger.error(f"[SESSIONS] Exception get_active_session: {e}")
        return None

async def get_session_by_id(session_id: str) -> Optional[Dict[str, Any]]:
    """Récupère une session par son ID"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/bot_sessions"
        params = {
            "id": f"eq.{session_id}",
            "select": "*"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=HEADERS, params=params, timeout=5.0)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return data[0]
        
        return None
        
    except Exception as e:
        logger.error(f"[SESSIONS] Exception get_session_by_id: {e}")
        return None

async def is_live_mode_active(company_id: str) -> bool:
    """
    Vérifie si le mode LIVE est actif
    
    Args:
        company_id: ID entreprise (TEXT)
    
    Returns:
        True si mode LIVE actif, False sinon
    """
    try:
        session = await get_active_session(company_id)
        return session is not None and session.get("mode") == "live"
    except:
        return False
