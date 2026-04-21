"""
core/prompt_cache_listener.py
─────────────────────────────
Écoute le channel pg_notify 'prompt_cache_invalidate' envoyé par les triggers
Supabase sur :
    - company_rag_configs → payload {"table":"company_rag_configs","company_id":"..."}
    - subscriptions       → payload {"table":"subscriptions","company_id":"..."}
    - prompt_bots         → payload {"table":"prompt_bots","bot_type":"amanda|jessica"}

Quand une notification arrive, invalide TOUTES les couches de cache :
    1. SimplifiedPromptSystem (Redis zeta:prompt:{company_id} + in-memory)
    2. BotlivePromptsManager (_cache in-memory par company_id)
    3. prompt_bots_loader (Redis zeta:prompt_bots:{bot_type} + in-memory)

Usage (appelé au startup de FastAPI) :
    from core.prompt_cache_listener import start_prompt_cache_listener
    asyncio.create_task(start_prompt_cache_listener())

Environment :
    DATABASE_URL ou SUPABASE_DB_URL : chaîne de connexion Postgres (asyncpg)
"""

import asyncio
import json
import logging
import os

logger = logging.getLogger(__name__)

_CHANNEL = "prompt_cache_invalidate"


def _invalidate_all_layers(payload: dict) -> None:
    """Invalide toutes les couches cache selon le payload pg_notify.

    Payload attendu (flexibles, tous optionnels) :
        - company_id : str  → invalide SimplifiedPromptSystem + BotlivePromptsManager
        - bot_type   : str  → invalide prompt_bots_loader (amanda|jessica)
        - table      : str  → indicateur source (log only)
    """
    company_id = payload.get("company_id")
    bot_type = payload.get("bot_type")
    src_table = payload.get("table", "?")

    invalidated: list[str] = []

    # ── Layer 1 : SimplifiedPromptSystem (Redis prompt:{company_id}) ──
    if company_id:
        try:
            from core.simplified_prompt_system import get_simplified_prompt_system
            ps = get_simplified_prompt_system()
            ps.invalidate_cache(company_id=company_id)
            invalidated.append("simplified_prompt_system")
        except Exception as _e:
            logger.warning("[PROMPT_LISTENER] L1 SimplifiedPromptSystem KO: %s", _e)

    # ── Layer 2 : BotlivePromptsManager (cache in-memory par company_id) ──
    if company_id:
        try:
            from core.botlive_prompts_supabase import get_prompts_manager
            manager = get_prompts_manager()
            if manager:
                # clear_cache filtre sur startswith(company_id), on cible le company_id
                manager.clear_cache(company_id=company_id)
                # Sécurité : retirer aussi tout _cache_timestamps orphelin
                try:
                    for k in [k for k in list(manager._cache_timestamps.keys()) if str(k).startswith(company_id)]:
                        manager._cache_timestamps.pop(k, None)
                except Exception:
                    pass
                invalidated.append("botlive_prompts_manager")
        except Exception as _e:
            logger.warning("[PROMPT_LISTENER] L2 BotlivePromptsManager KO: %s", _e)

    # ── Layer 3 : prompt_bots_loader (templates Amanda/Jessica) ──
    if bot_type:
        try:
            from core.prompt_bots_loader import invalidate_cache as invalidate_bot_template
            invalidate_bot_template(bot_type)
            invalidated.append(f"prompt_bots_loader:{bot_type}")
        except Exception as _e:
            logger.warning("[PROMPT_LISTENER] L3 prompt_bots_loader KO: %s", _e)

    # ── GLOBAL : si aucun hint → vider tout (safety net) ──
    if not invalidated and not company_id and not bot_type:
        try:
            from core.simplified_prompt_system import get_simplified_prompt_system
            get_simplified_prompt_system().invalidate_cache(company_id=None)
            invalidated.append("simplified_prompt_system:GLOBAL")
        except Exception:
            pass

    logger.info(
        "[PROMPT_LISTENER] 🔔 pg_notify src=%s company=%s bot=%s → invalidé=%s",
        src_table, company_id or "∅", bot_type or "∅", invalidated or ["nothing"],
    )


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
                    data = json.loads(payload or "{}") if payload else {}
                    if not isinstance(data, dict):
                        data = {}
                    _invalidate_all_layers(data)
                except Exception as _e:
                    logger.error("[PROMPT_LISTENER] Erreur handle payload=%r: %s", payload, _e)

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
