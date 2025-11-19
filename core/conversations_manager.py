"""\n📞 CONVERSATIONS MANAGER - Gestion des conversations et messages via tables Lovable\nUtilise les tables conversations et messages (UUID) créées par Lovable\n"""\n\nimport httpx\nimport logging\nfrom typing import Dict, Any, Optional\n\nlogger = logging.getLogger(__name__)\n\n# Credentials Supabase (même projet Lovable)\nSUPABASE_URL = "https://ilbihprkxcgsigvueeme.supabase.co"\nSUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlsYmlocHJreGNnc2lndnVlZW1lIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTEzMTQwNCwiZXhwIjoyMDY0NzA3NDA0fQ.Zf0EJbmP5ePGBZL5cY1tFP9FDRvJXDZ3x98zUS993GA"\n\nHEADERS = {\n    "apikey": SUPABASE_KEY,\n    "Authorization": f"Bearer {SUPABASE_KEY}",\n    "Content-Type": "application/json",\n}\n\nasync def _get_company_uuid(company_id: str) -> Optional[str]:\n    """Récupère l'UUID depuis company_mapping à partir du company_id texte"""\n    try:\n        url = f"{SUPABASE_URL}/rest/v1/company_mapping"\n        params = {\n            "company_id_text": f"eq.{company_id}",\n            "select": "company_id_uuid",\n        }\n\n        async with httpx.AsyncClient() as client:\n            response = await client.get(url, headers=HEADERS, params=params, timeout=5.0)\n\n        if response.status_code == 200:\n            data = response.json()\n            if data and len(data) > 0:\n                return data[0]["company_id_uuid"]\n\n        logger.warning(f"[CONVERSATIONS] Mapping introuvable pour company_id_text={company_id}")\n        return None\n\n    except Exception as e:\n        logger.error(f"[CONVERSATIONS] Erreur _get_company_uuid: {e}")\n        return None\n\nasync def get_or_create_conversation(company_id: str, user_id: str) -> Optional[str]:\n    """Récupère ou crée une conversation pour (company_id, user_id).\n\n    Args:\n        company_id: ID entreprise (TEXT, côté backend)\n        user_id: ID utilisateur (Messenger / WhatsApp)\n\n    Returns:\n        conversation_id (UUID) ou None en cas d'erreur\n    """\n    try:\n        company_uuid = await _get_company_uuid(company_id)\n        if not company_uuid:\n            return None\n\n        # 1) Essayer de trouver une conversation existante active pour ce client\n        url = f"{SUPABASE_URL}/rest/v1/conversations"\n        params = {\n            "company_id": f"eq.{company_uuid}",\n            "customer_phone": f"eq.{user_id}",\n            "select": "id,status",\n            "order": "created_at.desc",\n            "limit": 1,\n        }\n\n        async with httpx.AsyncClient() as client:\n            resp = await client.get(url, headers=HEADERS, params=params, timeout=5.0)\n\n        if resp.status_code == 200:\n            data = resp.json() or []\n            if data:\n                return data[0]["id"]\n\n        # 2) Sinon, créer une nouvelle conversation\n        payload = {\n            "company_id": company_uuid,\n            "customer_phone": user_id,\n            "status": "active",\n            "priority": "normal",\n        }\n\n        async with httpx.AsyncClient() as client:\n            create_resp = await client.post(\n                url,\n                headers={**HEADERS, "Prefer": "return=representation"},\n                json=payload,\n                timeout=5.0,\n            )\n\n        if create_resp.status_code in (200, 201):\n            conv = create_resp.json()\n            if isinstance(conv, list) and conv:\n                conv = conv[0]\n            return conv.get("id")\n\n        logger.error(\n            f"[CONVERSATIONS] Erreur création: {create_resp.status_code} - {create_resp.text}"\n        )\n        return None\n\n    except Exception as e:\n        logger.error(f"[CONVERSATIONS] Exception get_or_create_conversation: {e}")\n        return None\n\nasync def insert_message(conversation_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> bool:\n    """Insère un message lié à une conversation."""\n    try:\n        url = f"{SUPABASE_URL}/rest/v1/messages"\n        payload = {\n            "conversation_id": conversation_id,\n            "role": role,\n            "content": content,\n            "metadata": metadata or {},\n        }\n\n        async with httpx.AsyncClient() as client:\n            resp = await client.post(\n                url,\n                headers={**HEADERS, "Prefer": "return=minimal"},\n                json=payload,\n                timeout=5.0,\n            )\n\n        if resp.status_code in (200, 201, 204):\n            return True\n\n        logger.error(f"[MESSAGES] Erreur insertion: {resp.status_code} - {resp.text}")\n        return False\n\n    except Exception as e:\n        logger.error(f"[MESSAGES] Exception insert_message: {e}")\n        return False\n\n"""
📞 CONVERSATIONS MANAGER
Gestion des conversations et messages via les tables Lovable

Tables utilisées (projet Supabase ilbihprkxcgsigvueeme) :
- company_mapping (company_id_text ↔ company_id_uuid)
- conversations (UUID)
- messages (UUID)
"""

from typing import Dict, Any, Optional

import httpx
import logging


logger = logging.getLogger(__name__)


# Credentials Supabase (même projet Lovable)
SUPABASE_URL = "https://ilbihprkxcgsigvueeme.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlsYmlocHJreGNnc2lndnVlZW1lIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTEzMTQwNCwiZXhwIjoyMDY0NzA3NDA0fQ."
    "Zf0EJbmP5ePGBZL5cY1tFP9FDRvJXDZ3x98zUS993GA"
)

HEADERS: Dict[str, str] = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}


async def _get_company_uuid(company_id: str) -> Optional[str]:
    """Retourne l'UUID de company à partir du company_id texte.

    Lit dans la table company_mapping (champ company_id_text).
    """

    try:
        url = f"{SUPABASE_URL}/rest/v1/company_mapping"
        params = {
            "company_id_text": f"eq.{company_id}",
            "select": "company_id_uuid",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=HEADERS, params=params, timeout=5.0)

        if resp.status_code != 200:
            logger.error(
                "[CONVERSATIONS] Erreur company_mapping: %s - %s",
                resp.status_code,
                resp.text,
            )
            return None

        data = resp.json() or []
        if data:
            uuid = data[0].get("company_id_uuid")
            if uuid:
                return uuid

        logger.warning(
            "[CONVERSATIONS] Mapping introuvable pour company_id_text=%s",
            company_id,
        )
        return None

    except Exception as exc:  # pragma: no cover - log uniquement
        logger.error("[CONVERSATIONS] Exception _get_company_uuid: %s", exc)
        return None


async def get_or_create_conversation(company_id: str, user_id: str) -> Optional[str]:
    """Récupère ou crée une conversation pour (company_id, user_id).

    - company_id : identifiant texte (côté backend / Botlive)
    - user_id    : identifiant utilisateur (Messenger / WhatsApp)
    """

    try:
        company_uuid = await _get_company_uuid(company_id)
        if not company_uuid:
            return None

        url = f"{SUPABASE_URL}/rest/v1/conversations"

        # 1) Chercher une conversation existante pour ce couple
        params = {
            "company_id": f"eq.{company_uuid}",
            "user_id": f"eq.{user_id}",
            "select": "id",
            "order": "created_at.desc",
            "limit": "1",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=HEADERS, params=params, timeout=5.0)

        if resp.status_code == 200:
            rows = resp.json() or []
            if rows:
                conv_id = rows[0].get("id")
                if conv_id:
                    return conv_id

        # 2) Aucune conversation → en créer une nouvelle
        payload: Dict[str, Any] = {
            "company_id": company_uuid,
            "user_id": user_id,
        }

        async with httpx.AsyncClient() as client:
            create_resp = await client.post(
                url,
                headers={**HEADERS, "Prefer": "return=representation"},
                json=payload,
                timeout=5.0,
            )

        if create_resp.status_code in (200, 201):
            body = create_resp.json()
            # Supabase peut renvoyer soit une liste, soit un objet unique
            if isinstance(body, list) and body:
                return body[0].get("id")
            if isinstance(body, dict):
                return body.get("id")

        logger.error(
            "[CONVERSATIONS] Erreur création conversation: %s - %s",
            create_resp.status_code,
            create_resp.text,
        )
        return None

    except Exception as exc:  # pragma: no cover - log uniquement
        logger.error("[CONVERSATIONS] Exception get_or_create_conversation: %s", exc)
        return None


async def insert_message(
    conversation_id: str,
    role: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """Insère un message dans la table messages.

    - conversation_id : UUID de la conversation
    - role            : "user" ou "assistant"
    - content         : texte du message
    - metadata        : jsonb optionnel (source, channel, etc.)
    """

    try:
        url = f"{SUPABASE_URL}/rest/v1/messages"

        payload: Dict[str, Any] = {
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
        }
        if metadata is not None:
            payload["metadata"] = metadata

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                headers={**HEADERS, "Prefer": "return=minimal"},
                json=payload,
                timeout=5.0,
            )

        if resp.status_code in (200, 201, 204):
            logger.info(
                "[CONVERSATIONS] Message inséré (conv=%s, role=%s, len=%s)",
                conversation_id,
                role,
                len(content or ""),
            )
            return True

        logger.error(
            "[CONVERSATIONS] Erreur insert_message: %s - %s",
            resp.status_code,
            resp.text,
        )
        return False

    except Exception as exc:  # pragma: no cover - log uniquement
        logger.error("[CONVERSATIONS] Exception insert_message: %s", exc)
        return False

