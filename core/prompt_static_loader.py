"""
🧱 MURAILLE DE CHINE - Loader read-only du prompt CORE immuable.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OBJECTIF
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Charger `prompts/prompt_core_immutable.md` UNE SEULE FOIS et en garder un cache
mémoire process-wide. Le texte retourné est strictement byte-identique au
contenu du fichier : Python ne l'expose à AUCUNE méthode de transformation
(pas de `.format()`, `.replace()`, `format_map()`).

Conséquence : ce bloc de ~5500 tokens reste byte-identique entre TOUTES les
boutiques → cache implicit Gemini partagé inter-boutiques (Niveau 1 de la
hiérarchie de cache : universel).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ARCHITECTURE DE CACHE MULTI-NIVEAUX (Gemini prefix caching)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Zone 1 : CORE immuable     ← ce module (cache universel ~5500 tok)
    Zone 2 : SHOP config       ← prompt_shop_dynamic.md (cache par boutique)
    Zone 3 : CATALOGUE         ← idem (cache par boutique, tri append-only)
    Zone 4 : HISTORIQUE        ← conversation_history (volatile)
    Zone 5 : SESSION payload   ← cart, price, errors (ultra volatile)

Ordre d'envoi à l'API : Z1 + Z2 + Z3 + Z4 + Z5 (stable → volatile).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Chemins par défaut (racine projet / prompts/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_CORE_PATH = _PROJECT_ROOT / "prompts" / "prompt_core_immutable.md"
_DEFAULT_SHOP_PATH = _PROJECT_ROOT / "prompts" / "prompt_shop_dynamic.md"

# Caches mémoire (process-wide, thread-safe pour lecture seule)
_CORE_CACHE: Optional[str] = None
_SHOP_CACHE: Optional[str] = None


def get_immutable_core(path: Optional[str] = None) -> str:
    """Retourne le contenu du CORE immuable, sans jamais le modifier.

    - Lecture unique (1er appel), cache mémoire process-wide.
    - Aucune transformation (.format / .replace / format_map) n'est appliquée.
    - Le chemin peut être surchargé via ENV `PROMPT_CORE_IMMUTABLE_PATH`.

    🔒 Invariant : la valeur retournée est byte-identique entre tous les
    appels et toutes les boutiques. Casser cet invariant = détruire le cache
    universel Gemini.
    """
    global _CORE_CACHE
    if _CORE_CACHE is not None:
        return _CORE_CACHE

    resolved_path = path or os.getenv("PROMPT_CORE_IMMUTABLE_PATH") or str(_DEFAULT_CORE_PATH)
    try:
        with open(resolved_path, "r", encoding="utf-8") as fp:
            _CORE_CACHE = fp.read()
        logger.info(
            "🧱 [MURAILLE] CORE immuable chargé depuis %s (%d chars, ~%d tokens estimés)",
            resolved_path,
            len(_CORE_CACHE),
            len(_CORE_CACHE) // 3.24 if _CORE_CACHE else 0,
        )
    except FileNotFoundError:
        logger.error("❌ [MURAILLE] Fichier CORE introuvable : %s", resolved_path)
        _CORE_CACHE = ""
    except Exception as e:
        logger.error("❌ [MURAILLE] Erreur lecture CORE (%s) : %s", resolved_path, e)
        _CORE_CACHE = ""

    return _CORE_CACHE


def get_shop_dynamic_template(path: Optional[str] = None) -> str:
    """Retourne le template SHOP dynamique (Z2+Z3+Z4+Z5).

    Contrairement au CORE immuable, ce template CONTIENT des placeholders
    `{xxx}` qui seront résolus par `_safe_format()` au moment de la requête.
    Lecture en cache mémoire (le template texte ne change pas entre requêtes ;
    seules les VALEURS injectées changent).

    Le chemin peut être surchargé via ENV `PROMPT_SHOP_DYNAMIC_PATH`.
    """
    global _SHOP_CACHE
    if _SHOP_CACHE is not None:
        return _SHOP_CACHE

    resolved_path = path or os.getenv("PROMPT_SHOP_DYNAMIC_PATH") or str(_DEFAULT_SHOP_PATH)
    try:
        with open(resolved_path, "r", encoding="utf-8") as fp:
            _SHOP_CACHE = fp.read()
        logger.info(
            "🏬 [MURAILLE] SHOP template chargé depuis %s (%d chars)",
            resolved_path,
            len(_SHOP_CACHE),
        )
    except FileNotFoundError:
        logger.error("❌ [MURAILLE] Fichier SHOP introuvable : %s", resolved_path)
        _SHOP_CACHE = ""
    except Exception as e:
        logger.error("❌ [MURAILLE] Erreur lecture SHOP (%s) : %s", resolved_path, e)
        _SHOP_CACHE = ""

    return _SHOP_CACHE


def reset_caches() -> None:
    """Force le rechargement des 2 templates au prochain appel.

    Utile pour les tests et pour recharger après modification des fichiers
    .md en développement. Ne jamais appeler en production sous charge.
    """
    global _CORE_CACHE, _SHOP_CACHE
    _CORE_CACHE = None
    _SHOP_CACHE = None
    logger.info("🔄 [MURAILLE] Caches CORE + SHOP réinitialisés")


def is_muraille_enabled() -> bool:
    """Helper : lit la variable d'environnement PROMPT_MURAILLE_ENABLED.

    Retourne True si activé (valeurs acceptées : "1", "true", "yes", "y", "on"),
    False sinon (défaut).
    """
    raw = os.getenv("PROMPT_MURAILLE_ENABLED")
    if raw is None:
        return False
    return str(raw).strip().lower() in {"1", "true", "yes", "y", "on"}
