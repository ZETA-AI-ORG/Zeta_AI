"""
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
import os


logger = logging.getLogger(__name__)


# Credentials Supabase (même projet Lovable)
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ilbihprkxcgsigvueeme.supabase.co")
SUPABASE_KEY = (
    os.getenv("SUPABASE_KEY")
    or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")
    or ""
)


def _get_headers() -> Optional[Dict[str, str]]:
    if not SUPABASE_KEY:
        logger.error("[CONVERSATIONS] SUPABASE_KEY manquant (env SUPABASE_KEY / SUPABASE_SERVICE_ROLE_KEY)")
        return None

    return {
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
        headers = _get_headers()
        if not headers:
            return None
        params = {
            "company_id_text": f"eq.{company_id}",
            "select": "company_id_uuid",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, params=params, timeout=5.0)

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
        headers = _get_headers()
        if not headers:
            return None
        company_uuid = await _get_company_uuid(company_id)
        if not company_uuid:
            return None

        url = f"{SUPABASE_URL}/rest/v1/conversations"

        # 1) Chercher une conversation existante pour ce couple
        #    On utilise customer_name comme identifiant logique pour user_id
        params = {
            "company_id": f"eq.{company_uuid}",
            "customer_name": f"eq.{user_id}",
            "select": "id",
            "order": "created_at.desc",
            "limit": "1",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, params=params, timeout=5.0)

        if resp.status_code == 200:
            rows = resp.json() or []
            if rows:
                conv_id = rows[0].get("id")
                if conv_id:
                    return conv_id

        # 2) Aucune conversation → en créer une nouvelle
        payload: Dict[str, Any] = {
            "company_id": company_uuid,
            "customer_name": user_id,
            # champs status / priority ont généralement des valeurs par défaut côté DB
        }

        async with httpx.AsyncClient() as client:
            create_resp = await client.post(
                url,
                headers={**headers, "Prefer": "return=representation"},
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
        headers = _get_headers()
        if not headers:
            return False

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
                headers={**headers, "Prefer": "return=minimal"},
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

