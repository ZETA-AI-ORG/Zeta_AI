"""
core/prompt_cache_listener.py
─────────────────────────────
Écoute le channel pg_notify 'prompt_cache_invalidate' envoyé
par le trigger Supabase sur company_rag_configs.

Quand un UPDATE arrive, invalide le cache Redis/in-memory du
SimplifiedPromptSystem singleton.

Usage (appelé au startup de FastAPI) :
    from core.prompt_cache_listener import start_prompt_cache_listener
    asyncio.create_task(start_prompt_cache_listener())
"""

import asyncio
import json
import logging
import os

logger = logging.getLogger(__name__)

_CHANNEL = "prompt_cache_invalidate"


async def start_prompt_cache_listener() -> None:
    """
    Boucle asyncpg qui écoute le channel pg_notify Supabase.
    Se reconnecte automatiquement si la connexion est perdue.
    """
    db_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not db_url:
        logger.warning(
            "[PROMPT_LISTENER] DATABASE_URL absent — listener pg_notify désactivé."
        )
        return

    while True:
        try:
            import asyncpg

            conn: asyncpg.Connection = await asyncpg.connect(db_url)
            logger.info("[PROMPT_LISTENER] 🟢 Connecté à Postgres — écoute '%s'", _CHANNEL)

            async def _handle(connection, pid, channel, payload):
                try:
                    data = json.loads(payload or "{}")
                    company_id = data.get("company_id")
                    from core.simplified_prompt_system import get_simplified_prompt_system

                    ps = get_simplified_prompt_system()
                    ps.invalidate_cache(company_id=company_id)
                    logger.info(
                        "[PROMPT_LISTENER] 🔔 Cache invalidé via pg_notify → company_id=%s",
                        company_id or "GLOBAL",
                    )
                except Exception as _e:
                    logger.error("[PROMPT_LISTENER] Erreur handle: %s", _e)

            await conn.add_listener(_CHANNEL, _handle)

            # Garder la boucle vivante
            while True:
                await asyncio.sleep(10)
                # Envoyer un keep-alive pour détecter les déconnexions
                try:
                    await conn.execute("SELECT 1")
                except Exception:
                    logger.warning("[PROMPT_LISTENER] Keep-alive échoué — reconnexion...")
                    break

        except ImportError:
            logger.warning("[PROMPT_LISTENER] asyncpg non installé — listener désactivé.")
            return
        except Exception as e:
            logger.error("[PROMPT_LISTENER] 🔴 Connexion perdue (%s) — retry dans 15s", e)
            await asyncio.sleep(15)
