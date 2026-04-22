"""
🔍 ZETA AI — STRUCTURED LOGGING (zlog)
Référence : zeta_ai_debug_log.md

Format : JSON structuré one-line pour parsing facile (grep, jq, docker logs).
Logger : "zeta" (séparé de "app" pour coexistence avec log3).
Niveaux : DEBUG, INFO, WARNING, ERROR — configurable via ZETA_LOG_LEVEL.
"""

import logging
import json
import os
import time
import sys

# ─── Configuration logger "zeta" ──────────────────────────────────────────────
_log_level_str = os.getenv("ZETA_LOG_LEVEL", "DEBUG").upper()
_log_level = getattr(logging, _log_level_str, logging.DEBUG)

logger = logging.getLogger("zeta")
logger.setLevel(_log_level)

# Éviter les doublons si le module est importé plusieurs fois
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setLevel(_log_level)
    # Format minimaliste : le contenu JSON est auto-suffisant
    _formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    _handler.setFormatter(_formatter)
    logger.addHandler(_handler)
    # Empêcher la propagation vers le root logger (évite les doublons uvicorn)
    logger.propagate = False


def zlog(level: str, phase: str, event: str, **kwargs):
    """
    Log structuré JSON pour observabilité temps réel.

    Args:
        level:  "debug" | "info" | "warning" | "error"
        phase:  Phase pipeline (ex: "AMANDA_IN", "GUARDIAN", "LLM_CALL", "COST")
        event:  Description courte de l'événement
        **kwargs: Données structurées (company_id, model, elapsed_ms, etc.)

    Usage:
        zlog("info", "AMANDA_IN", "requête reçue",
             request_id="f969034", company_id="W27Pw...", message_len=42)

    Sortie (stdout):
        2026-04-22 12:00:00 [INFO] [AMANDA_IN] requête reçue | {"phase":"AMANDA_IN","event":"requête reçue","request_id":"f969034",...}
    """
    payload = {
        "phase": phase,
        "event": event,
        **kwargs
    }

    # Sérialisation JSON sûre (datetime, Decimal, etc. → str)
    try:
        json_str = json.dumps(payload, ensure_ascii=False, default=str)
    except Exception:
        json_str = str(payload)

    log_line = f"[{phase}] {event} | {json_str}"

    log_fn = getattr(logger, level.lower(), logger.info)
    log_fn(log_line)


def zlog_error(phase: str, event: str, error: Exception, **kwargs):
    """
    Raccourci pour logguer une erreur avec traceback partiel.
    Respecte RÈGLE 1 : jamais silencieux sur erreur.
    """
    import traceback
    tb = traceback.format_exc()
    zlog("error", phase, event,
         error=str(error)[:300],
         error_type=type(error).__name__,
         traceback=tb[-500:] if tb and "NoneType" not in tb else "",
         **kwargs)
