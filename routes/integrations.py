from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging
import httpx

from database.supabase_client import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["integrations"])


class MessengerProfileRequest(BaseModel):
    company_id: str
    page_id: str
    sender_id: str


class MessengerProfileResponse(BaseModel):
    user_id: str
    user_display_name: str
    channel: str = "messenger"
    profile_pic: Optional[str] = None


class MessengerPageIntegrationRequest(BaseModel):
    """Représente l'intégration Messenger d'une page pour une entreprise.

    Ce modèle est volontairement minimal pour rester compatible avec le schéma actuel
    de la table `integrations` (company_id, provider, page_id, access_token).
    """

    company_id: str
    page_id: str
    access_token: str
    # Provider fixé à "messenger" mais laissé configurable pour évolutivité
    provider: str = "messenger"


async def _get_messenger_access_token(company_id: str, page_id: str) -> str:
    """Récupère le page_access_token Messenger depuis la table integrations.

    La table integrations a le schéma:
      - company_id (TEXT)
      - provider (TEXT)
      - page_id (TEXT)
      - access_token (TEXT)
    """

    url = f"{SUPABASE_URL}/rest/v1/integrations"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    params = {
        "company_id": f"eq.{company_id}",
        "provider": "eq.messenger",
        "page_id": f"eq.{page_id}",
        "select": "access_token",
        "limit": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers, params=params)

        if resp.status_code != 200:
            logger.error(
                "[INTEGRATIONS][MESSENGER] Erreur fetch token: %s - %s",
                resp.status_code,
                resp.text,
            )
            raise HTTPException(status_code=500, detail="Erreur récupération token Messenger")

        rows = resp.json() or []
        if not rows or not rows[0].get("access_token"):
            logger.warning(
                "[INTEGRATIONS][MESSENGER] Aucun access_token trouvé pour company_id=%s page_id=%s",
                company_id,
                page_id,
            )
            raise HTTPException(status_code=404, detail="Aucun token Messenger configuré pour cette entreprise")

        return rows[0]["access_token"]

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[INTEGRATIONS][MESSENGER] Exception get token: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne récupération token Messenger")


@router.post("/messenger/profile", response_model=MessengerProfileResponse)
async def get_messenger_profile(payload: MessengerProfileRequest) -> MessengerProfileResponse:
    """Retourne le profil Messenger (nom affiché) pour un sender_id donné.

    Utilise la table integrations pour récupérer le page_access_token correspondant
    à (company_id, page_id), puis appelle le Graph API:
      GET /v23.0/{sender_id}?fields=first_name,last_name,profile_pic
    """

    access_token = await _get_messenger_access_token(payload.company_id, payload.page_id)

    graph_url = f"https://graph.facebook.com/v23.0/{payload.sender_id}"
    params = {
        "fields": "first_name,last_name,profile_pic",
        "access_token": access_token,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(graph_url, params=params)

        if resp.status_code != 200:
            logger.error(
                "[INTEGRATIONS][MESSENGER] Erreur Graph API %s: %s",
                resp.status_code,
                resp.text,
            )
            raise HTTPException(status_code=502, detail="Erreur Graph API Messenger")

        data = resp.json() or {}
        first_name = data.get("first_name") or ""
        last_name = data.get("last_name") or ""
        display_name = (first_name + " " + last_name).strip() or payload.sender_id

        return MessengerProfileResponse(
            user_id=f"messenger_{payload.sender_id}",
            user_display_name=display_name,
            channel="messenger",
            profile_pic=data.get("profile_pic"),
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[INTEGRATIONS][MESSENGER] Exception Graph API: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne profil Messenger")


@router.post("/messenger/page")
async def upsert_messenger_page_integration(payload: MessengerPageIntegrationRequest):
    """Crée ou met à jour l'intégration Messenger d'une page pour une entreprise.

    Permet d'enregistrer dynamiquement, via API, le couple (company_id, provider, page_id)
    avec son `access_token` dans la table `integrations`, sans avoir à faire d'INSERT SQL
    manuel pour chaque nouveau client.

    Comportement attendu côté base de données :
      - Une contrainte unique (company_id, provider, page_id) assure qu'il n'y ait
        qu'une seule ligne par couple.
      - Prefer: resolution=merge-duplicates permet à PostgREST de faire un upsert.
    """

    url = f"{SUPABASE_URL}/rest/v1/integrations"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation",
    }

    body = {
        "company_id": payload.company_id,
        "provider": payload.provider,
        "page_id": payload.page_id,
        "access_token": payload.access_token,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, json=body)

        if resp.status_code not in (200, 201):
            logger.error(
                "[INTEGRATIONS][MESSENGER] Erreur upsert integration page: %s - %s",
                resp.status_code,
                resp.text,
            )
            raise HTTPException(status_code=500, detail="Erreur enregistrement intégration Messenger")

        data = resp.json() or {}
        # PostgREST peut renvoyer une liste ou un dict selon la configuration
        integration = data[0] if isinstance(data, list) and data else data

        return {"status": "ok", "integration": integration}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[INTEGRATIONS][MESSENGER] Exception upsert integration: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne enregistrement intégration Messenger")
