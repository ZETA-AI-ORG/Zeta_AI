import os
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from google.oauth2 import service_account
from google.auth.transport import requests as google_auth_requests
from config import GOOGLE_PROJECT_ID, GOOGLE_PRIVATE_KEY, GOOGLE_CLIENT_EMAIL, GOOGLE_CLIENT_ID

import logging
logger = logging.getLogger(__name__)

router = APIRouter()

class JWTRequest(BaseModel):
    scope: str  # Le scope Google JWT demandé

# Construction du dict Google Service Account info (adapté pour compatibilité)
GOOGLE_SERVICE_ACCOUNT_INFO = None
if all([GOOGLE_PROJECT_ID, GOOGLE_PRIVATE_KEY, GOOGLE_CLIENT_EMAIL, GOOGLE_CLIENT_ID]):
    GOOGLE_SERVICE_ACCOUNT_INFO = {
        "type": "service_account",
        "project_id": GOOGLE_PROJECT_ID,
        "private_key": GOOGLE_PRIVATE_KEY.replace('\\n', '\n'),
        "client_email": GOOGLE_CLIENT_EMAIL,
        "client_id": GOOGLE_CLIENT_ID,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{GOOGLE_CLIENT_EMAIL}"
    }
else:
    logger.warning("Variables d'environnement Google manquantes pour le Service Account. JWT Google désactivé.")

@router.post("/generate_jwt")
async def generate_google_jwt(request_body: JWTRequest):
    """
    Génère un JWT (Access Token) signé pour l'authentification Google OAuth2
    en utilisant le fichier JSON temporaire ou les variables d'environnement.
    """
    try:
        # Essayer d'abord avec le fichier JSON temporaire
        import os
        json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "service_account_temp.json")
        if os.path.exists(json_path):
            logger.info("Utilisation du fichier service_account_temp.json")
            credentials = service_account.Credentials.from_service_account_file(
                json_path,
                scopes=[request_body.scope]
            )
        elif GOOGLE_SERVICE_ACCOUNT_INFO:
            logger.info("Utilisation des variables d'environnement")
            credentials = service_account.Credentials.from_service_account_info(
                GOOGLE_SERVICE_ACCOUNT_INFO,
                scopes=[request_body.scope]
            )
        else:
            logger.error("Aucune configuration du compte de service Google trouvée.")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Configuration du compte de service Google manquante.")
        
        request = google_auth_requests.Request()
        credentials.refresh(request)
        jwt_token = credentials.token
        logger.info(f"JWT Google généré avec succès pour le scope: {request_body.scope[:50]}...")
        return JSONResponse(status_code=status.HTTP_200_OK, content={"jwt": jwt_token})
    except Exception as e:
        logger.error(f"Erreur lors de la génération du JWT Google: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erreur lors de la génération du JWT: {e}")
