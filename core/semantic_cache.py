#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧠 SEMANTIC CACHE - GPTCache (sqlite + faiss)
Permet de réutiliser réponses pour questions similaires (pas identiques)
"""

import os
from typing import Any, Callable, Optional

cache = None
_gptcache_ready = False
_gptcache_init_failed = False

import logging
logger = logging.getLogger(__name__)

CACHE_DIR = os.getenv("GPTCACHE_DIR", "cache/gptcache/")
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").strip().lower() in {"1", "true", "yes", "y", "on"}

EMBEDDING_MODEL = "sentence-transformers/paraphrase-MiniLM-L6-v2"


def is_cache_enabled() -> bool:
    return CACHE_ENABLED


def _init_gptcache():
    global cache
    global _gptcache_ready
    global _gptcache_init_failed

    if not is_cache_enabled():
        return None
    if _gptcache_ready:
        return cache
    if _gptcache_init_failed:
        return None
    try:
        from gptcache import cache as _cache
        from gptcache.manager import get_data_manager
        from gptcache.similarity_evaluation import SearchDistanceEvaluation
        from gptcache.processor.pre import get_prompt
        from sentence_transformers import SentenceTransformer

        cache = _cache

        cache_dir = os.path.normpath(CACHE_DIR)
        os.makedirs(cache_dir, exist_ok=True)
        sqlite_path = os.path.join(cache_dir, "gptcache.sqlite3")
        
        cache.init(
            data_manager=get_data_manager(
                data_path=sqlite_path,
            ),
            embedding_func=SentenceTransformer(EMBEDDING_MODEL).encode,
            similarity_evaluation=SearchDistanceEvaluation(),
            pre_embedding_func=get_prompt,
        )
        logger.info(f"[GPTCACHE] Initialisé (sqlite+faiss, dir={CACHE_DIR})")
    except Exception as e:
        _gptcache_init_failed = True
        logger.error(f"[GPTCACHE] Erreur init: {e}")
        return None
    _gptcache_ready = True
    return cache


def semantic_cache_decorator(func: Callable) -> Callable:
    if not is_cache_enabled():
        return func
    try:
        global cache
        if cache is None:
            _init_gptcache()
        if cache is None:
            return func
        try:
            from gptcache.adapter.api import cache_decorator as gptcache_decorator
        except Exception:
            try:
                from gptcache.adapter import cache_decorator as gptcache_decorator
            except Exception:
                return func
        return gptcache_decorator(cache_obj=cache)(func)
    except Exception as e:
        logger.error(f"[GPTCACHE] Erreur decorator: {e}")
        return func

# Initialisation à l'import si activé
gptcache_instance = _init_gptcache() if is_cache_enabled() else None
