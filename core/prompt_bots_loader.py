"""
🧠 Prompt Bots Loader — Système C unifié (Amanda + Jessica)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Charge les templates de prompt depuis la table Supabase `prompt_bots`.
Cache Redis 1h + fallback in-memory + fallback fichier local (résilience).

Schéma table `prompt_bots` (Supabase) :
    - id            UUID PK
    - bot_type      VARCHAR(50) UNIQUE  (ex: "amanda", "jessica")
    - prompt_content TEXT               (template avec {variables})
    - version       VARCHAR(20)
    - is_active     BOOLEAN
    - updated_at    TIMESTAMPTZ
    - created_at    TIMESTAMPTZ

Flux :
    Supabase (source de vérité)
        ↓ fetch si cache expiré
    Redis zeta:prompt_bots:{bot_type} (TTL 1h)
        ↓ hit → retour direct
    In-memory (fallback Redis down)
        ↓ fallback ultime
    Fichier .md local (résilience totale)

Invalidation :
    - TTL 1h automatique
    - `invalidate_cache(bot_type)` manuel (appelé par endpoint admin après sync)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import os
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)

# ───────────────────────────────────────────────────────────────────────
# Configuration
# ───────────────────────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY", "")

_REDIS_KEY_PREFIX = "zeta:prompt_bots:"
_REDIS_TTL_SECONDS = 3600  # 1h (filet de sécurité même si trigger rate)

# Fallback fichiers locaux si Supabase + Redis + in-memory tous indisponibles
_BASE_DIR = Path(__file__).parent.parent
_LOCAL_FALLBACK_FILES: Dict[str, Path] = {
    "amanda": _BASE_DIR / "AMANDA PROMPT UNIVERSEL.md",
    "jessica": _BASE_DIR / "prompt_universel_v2.md",
}

# ───────────────────────────────────────────────────────────────────────
# Cache in-memory (fallback si Redis down)
# ───────────────────────────────────────────────────────────────────────
_memory_cache: Dict[str, str] = {}
_memory_cache_ts: Dict[str, float] = {}

# ───────────────────────────────────────────────────────────────────────
# Redis connection (lazy, singleton)
# ───────────────────────────────────────────────────────────────────────
_redis_client = None
_redis_initialized = False


def _get_redis():
    """Retourne le client Redis ou None si indisponible. Lazy init."""
    global _redis_client, _redis_initialized
    if _redis_initialized:
        return _redis_client
    _redis_initialized = True
    try:
        import redis as _redis_lib
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        client = _redis_lib.from_url(url, decode_responses=True, socket_connect_timeout=2)
        client.ping()
        _redis_client = client
        logger.info("✅ [PROMPT_BOTS] Redis connecté")
    except Exception as e:
        logger.warning(f"⚠️ [PROMPT_BOTS] Redis indisponible → fallback in-memory: {e}")
        _redis_client = None
    return _redis_client


def _redis_key(bot_type: str) -> str:
    return f"{_REDIS_KEY_PREFIX}{bot_type}"


# ───────────────────────────────────────────────────────────────────────
# Supabase fetch (source de vérité)
# ───────────────────────────────────────────────────────────────────────
def _fetch_from_supabase(bot_type: str) -> Optional[str]:
    """
    Lit le prompt actif depuis Supabase table `prompt_bots`.
    Retourne None en cas d'erreur ou si bot_type introuvable / inactif.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning("⚠️ [PROMPT_BOTS] Credentials Supabase manquants")
        return None

    url = f"{SUPABASE_URL}/rest/v1/prompt_bots"
    params = {
        "bot_type": f"eq.{bot_type}",
        "is_active": "eq.true",
        "select": "prompt_content,version,updated_at",
        "limit": "1",
    }
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    try:
        resp = httpx.get(url, params=params, headers=headers, timeout=5.0)
        if resp.status_code != 200:
            logger.error(
                f"❌ [PROMPT_BOTS] Supabase {resp.status_code} pour bot_type={bot_type}: "
                f"{resp.text[:200]}"
            )
            return None
        rows = resp.json() or []
        if not rows:
            logger.warning(f"⚠️ [PROMPT_BOTS] Aucun prompt actif pour bot_type={bot_type}")
            return None
        content = str(rows[0].get("prompt_content") or "").strip()
        version = rows[0].get("version", "?")
        if not content:
            logger.warning(f"⚠️ [PROMPT_BOTS] Prompt vide pour bot_type={bot_type}")
            return None
        logger.info(
            f"📥 [PROMPT_BOTS] Supabase FETCH bot_type={bot_type} "
            f"v={version} ({len(content)} chars)"
        )
        return content
    except Exception as e:
        logger.error(f"❌ [PROMPT_BOTS] Erreur fetch Supabase bot_type={bot_type}: {e}")
        return None


def _fetch_from_local_file(bot_type: str) -> Optional[str]:
    """Dernier recours : lit le fichier .md local (résilience totale)."""
    path = _LOCAL_FALLBACK_FILES.get(bot_type)
    if not path or not path.exists():
        return None
    try:
        content = path.read_text(encoding="utf-8").strip()
        logger.warning(
            f"🆘 [PROMPT_BOTS] Fallback FICHIER LOCAL pour bot_type={bot_type} "
            f"({path.name}, {len(content)} chars)"
        )
        return content
    except Exception as e:
        logger.error(f"❌ [PROMPT_BOTS] Erreur lecture fichier local {path}: {e}")
        return None


# ───────────────────────────────────────────────────────────────────────
# API publique
# ───────────────────────────────────────────────────────────────────────
def get_prompt_template(bot_type: str) -> str:
    """
    Retourne le template de prompt pour un bot donné.

    Ordre de résolution :
        1. Redis (TTL 1h)
        2. In-memory (fallback Redis down)
        3. Supabase (refresh + remplit caches)
        4. Fichier .md local (dernier recours)

    Args:
        bot_type: "amanda" ou "jessica"

    Returns:
        Template string avec placeholders `{var}`. "" si tout échoue.
    """
    bot_type = (bot_type or "").strip().lower()
    if not bot_type:
        return ""

    # 1) Redis
    redis_client = _get_redis()
    if redis_client is not None:
        try:
            val = redis_client.get(_redis_key(bot_type))
            if val:
                print(f"📦 [PROMPT_BOTS] Cache HIT (Redis) pour bot={bot_type}")
                return val
        except Exception as e:
            print(f"⚠️ [PROMPT_BOTS] Redis read error: {e}")

    # 2) In-memory (valide si < TTL)
    mem_val = _memory_cache.get(bot_type)
    mem_ts = _memory_cache_ts.get(bot_type, 0.0)
    if mem_val and (time.time() - mem_ts) < _REDIS_TTL_SECONDS:
        print(f"📦 [PROMPT_BOTS] Cache HIT (In-Memory) pour bot={bot_type}")
        # Re-hydrate Redis si possible
        if redis_client is not None:
            try:
                redis_client.setex(_redis_key(bot_type), _REDIS_TTL_SECONDS, mem_val)
            except Exception:
                pass
        return mem_val

    # 3) Supabase (source de vérité)
    content = _fetch_from_supabase(bot_type)

    # 4) Fallback fichier local
    if not content:
        content = _fetch_from_local_file(bot_type)

    if not content:
        print(f"❌ [PROMPT_BOTS] TOUS les fallbacks ont échoué pour bot_type={bot_type}")
        return ""

    # Remplir les caches
    _memory_cache[bot_type] = content
    _memory_cache_ts[bot_type] = time.time()
    if redis_client is not None:
        try:
            redis_client.setex(_redis_key(bot_type), _REDIS_TTL_SECONDS, content)
            logger.info(f"💾 [PROMPT_BOTS] Redis SET bot_type={bot_type} (TTL {_REDIS_TTL_SECONDS}s)")
        except Exception as e:
            logger.warning(f"⚠️ [PROMPT_BOTS] Redis write error: {e}")

    return content


def invalidate_cache(bot_type: str) -> bool:
    """
    Invalide le cache (Redis + in-memory) pour un bot_type.
    Appelé par l'endpoint admin après sync Supabase.

    Returns True si au moins un cache a été invalidé.
    """
    bot_type = (bot_type or "").strip().lower()
    if not bot_type:
        return False

    invalidated = False

    # In-memory
    if bot_type in _memory_cache:
        del _memory_cache[bot_type]
        _memory_cache_ts.pop(bot_type, None)
        invalidated = True

    # Redis
    redis_client = _get_redis()
    if redis_client is not None:
        try:
            deleted = redis_client.delete(_redis_key(bot_type))
            if deleted:
                invalidated = True
        except Exception as e:
            logger.warning(f"⚠️ [PROMPT_BOTS] Redis delete error: {e}")

    if invalidated:
        logger.info(f"🗑️ [PROMPT_BOTS] Cache invalidé pour bot_type={bot_type}")
    return invalidated


def upload_prompt_to_supabase(
    bot_type: str,
    prompt_content: str,
    version: str = "1.0",
    is_active: bool = True,
) -> bool:
    """
    UPSERT un template dans Supabase (utilisé par le script de sync initial
    ou l'endpoint admin pour pousser un nouveau prompt depuis un fichier).

    Args:
        bot_type: "amanda" ou "jessica"
        prompt_content: contenu du template
        version: version sémantique (ex: "1.0", "2.1")
        is_active: activer immédiatement ce prompt

    Returns True si succès.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("❌ [PROMPT_BOTS] Credentials Supabase manquants")
        return False

    if not prompt_content or not prompt_content.strip():
        logger.error(f"❌ [PROMPT_BOTS] Contenu vide pour {bot_type}, upload refusé")
        return False

    url = f"{SUPABASE_URL}/rest/v1/prompt_bots?on_conflict=bot_type"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        # UPSERT sur la contrainte UNIQUE bot_type
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    payload = {
        "bot_type": bot_type,
        "prompt_content": prompt_content,
        "version": version,
        "is_active": is_active,
    }
    try:
        resp = httpx.post(url, headers=headers, json=payload, timeout=10.0)
        if resp.status_code in (200, 201, 204):
            logger.info(
                f"✅ [PROMPT_BOTS] Upload OK bot_type={bot_type} v={version} "
                f"({len(prompt_content)} chars)"
            )
            # Invalider le cache pour forcer un refresh immédiat
            invalidate_cache(bot_type)
            return True
        else:
            logger.error(
                f"❌ [PROMPT_BOTS] Upload failed {resp.status_code}: {resp.text[:300]}"
            )
            return False
    except Exception as e:
        logger.error(f"❌ [PROMPT_BOTS] Exception upload bot_type={bot_type}: {e}")
        return False
