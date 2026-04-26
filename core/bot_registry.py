"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎛️ BOT REGISTRY v2.0 — Configs LLM par bot + plan + boost
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Registry unifié des modèles LLM + hyperparamètres, avec résolution dynamique
par bot / plan d'abonnement / option boost.

Rôle LLM   : raisonnement + langage.
Rôle Python: calcul prix, orchestration, validation, swap catalogue.

Surcharge via env :
  AMANDA_MODEL, AMANDA_MODEL_FALLBACK
  JESSICA_MODEL_RANG_A, JESSICA_MODEL_RANG_S, JESSICA_MODEL_BOOST
  VISION_MODEL_OCR_PRODUIT, VISION_MODEL_OCR_PAIEMENT
  INSIGHT_MODEL

Utilisation:
    from core.bot_registry import get_amanda_config, get_jessica_config

    cfg = get_amanda_config(plan_name="pro", has_boost=True)
    # → {"model": "qwen/...", "fallback": "google/gemma-4-26b-...",
    #     "params": {"temperature": 0.72, "frequency_penalty": 0.45, ...}}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

try:
    from .zlog import zlog
except ImportError:
    from core.zlog import zlog


# ═══════════════════════════════════════════════════════════════════════════════
# 🎙️ AMANDA — Bot Live TikTok (Précommande VIP)
# Règle : IDENTIQUE pour tous les abonnements, BOOST IGNORÉ.
# ═══════════════════════════════════════════════════════════════════════════════

_AMANDA_MODEL = os.getenv("AMANDA_MODEL", "qwen/qwen3-235b-a22b-2507")
_AMANDA_FALLBACK = os.getenv("AMANDA_MODEL_FALLBACK", "google/gemma-4-26b-a4b-it")

AMANDA: Dict[str, Any] = {
    "decouverte": _AMANDA_MODEL,
    "starter":    _AMANDA_MODEL,
    "pro":        _AMANDA_MODEL,
    "elite":      _AMANDA_MODEL,
    "fallback":   _AMANDA_FALLBACK,
    "params": {
        "temperature":       0.72,
        "frequency_penalty": 0.45,
        "presence_penalty":  0.30,
        "max_tokens":        350,
        "top_p":             0.92,
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# 🛍️ JESSICA — Bot RAG Catalogue & Vente
# Règle : varie selon abonnement + option BOOST.
# ═══════════════════════════════════════════════════════════════════════════════

_JESSICA_RANG_A = os.getenv("JESSICA_MODEL_RANG_A", "google/gemma-4-26b-a4b-it")
_JESSICA_RANG_S = os.getenv("JESSICA_MODEL_RANG_S", "deepseek/deepseek-v4-flash")
_JESSICA_BOOST = os.getenv("JESSICA_MODEL_BOOST", "google/gemini-3.1-flash-lite-preview")
_JESSICA_FALLBACK = os.getenv("JESSICA_MODEL_FALLBACK", "google/gemma-4-26b-a4b-it")

JESSICA: Dict[str, Any] = {
    "decouverte": _JESSICA_RANG_A,   # RANG A
    "starter":    _JESSICA_RANG_A,   # RANG A
    "pro":        _JESSICA_RANG_S,   # RANG S
    "elite":      _JESSICA_RANG_S,   # RANG S
    "boost":      _JESSICA_BOOST,    # Override si boost activé (tout plan)
    "fallback":   _JESSICA_FALLBACK,

    "params_rang_a": {                      # Découverte / Starter
        "temperature":       0.45,
        "frequency_penalty": 0.20,
        "presence_penalty":  0.15,
        "max_tokens":        900,
        "top_p":             0.88,
    },
    "params_rang_s": {                      # Pro / Elite (sans boost)
        "temperature":       0.40,
        "frequency_penalty": 0.15,
        "presence_penalty":  0.10,
        "max_tokens":        900,
        "top_p":             0.85,
    },
    "params_boost": {                       # Boost activé (tout plan)
        "temperature":       0.38,
        "frequency_penalty": 0.15,
        "presence_penalty":  0.10,
        "max_tokens":        900,
        "top_p":             0.85,
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# 👁️ VISION — Traitement images (géré par Python, pas par plan)
# ═══════════════════════════════════════════════════════════════════════════════

VISION: Dict[str, Any] = {
    "ocr_produit":  os.getenv("VISION_MODEL_OCR_PRODUIT", "google/gemini-3.1-flash-lite-preview"),
    "ocr_paiement": os.getenv("VISION_MODEL_OCR_PAIEMENT", "google/gemini-3.1-pro-preview"),

    "params_ocr": {
        "temperature": 0.10,
        "max_tokens":  200,
    },
    "params_paiement": {
        "temperature": 0.05,
        "max_tokens":  300,
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# 📊 ZETA INSIGHT — Bilans analytiques
# ═══════════════════════════════════════════════════════════════════════════════

INSIGHT: Dict[str, Any] = {
    "model": os.getenv("INSIGHT_MODEL", "google/gemini-3.1-pro-preview"),
    "params": {
        "temperature": 0.60,
        "max_tokens":  4000,
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# 🛡️ GARDE-FOU — modèles autorisés
# ═══════════════════════════════════════════════════════════════════════════════

ALLOWED_MODELS = {
    "qwen/qwen3-235b-a22b-2507",
    "qwen/qwen3.5-flash-02-23",
    "google/gemma-4-26b-a4b-it",
    "google/gemma-4-31b-it",
    "deepseek/deepseek-v3.2",
    "deepseek/deepseek-v4-flash",
    "stepfun/step-3.5-flash",
    "google/gemini-3.1-flash-lite-preview",
    "google/gemini-3.1-pro-preview",
}


# ═══════════════════════════════════════════════════════════════════════════════
# 🧭 HELPERS — résolution bot → modèle + params
# ═══════════════════════════════════════════════════════════════════════════════

def _normalize_plan(plan_name: Optional[str]) -> str:
    p = (plan_name or "starter").strip().lower()
    if p in {"découverte", "decouverte"}:
        return "decouverte"
    if p in {"starter", "start"}:
        return "starter"
    if p in {"pro", "professional"}:
        return "pro"
    if p in {"elite", "enterprise"}:
        return "elite"
    return "starter"


def get_amanda_config(plan_name: Optional[str] = None, has_boost: bool = False) -> Dict[str, Any]:
    """Config LLM pour Amanda (Live TikTok).

    Règle : boost IGNORÉ, mêmes params pour tous les plans.
    """
    plan = _normalize_plan(plan_name)
    model = AMANDA.get(plan, AMANDA["starter"])
    zlog("info", "REGISTRY", "modèle résolu",
         bot_type="amanda", plan=plan, has_boost=False,
         model=model, boost_ignored=True)
    return {
        "bot": "amanda",
        "plan": plan,
        "has_boost": False,              # Amanda ignore le boost (règle métier)
        "model": model,
        "fallback": AMANDA["fallback"],
        "params": dict(AMANDA["params"]),
    }


def get_jessica_config(plan_name: Optional[str] = None, has_boost: bool = False) -> Dict[str, Any]:
    """Config LLM pour Jessica (RAG Catalogue).

    Règles :
    - decouverte/starter → RANG A (Gemma 26B)
    - pro/elite sans boost → RANG S (DeepSeek v3.2)
    - boost activé (tout plan) → BOOST (Gemini 3.1 flash-lite)
    """
    plan = _normalize_plan(plan_name)

    if has_boost:
        model = JESSICA["boost"]
        params = dict(JESSICA["params_boost"])
        rank = "BOOST"
    elif plan in {"pro", "elite"}:
        model = JESSICA["pro"] if plan == "pro" else JESSICA["elite"]
        params = dict(JESSICA["params_rang_s"])
        rank = "RANG_S"
    else:
        model = JESSICA.get(plan, JESSICA["starter"])
        params = dict(JESSICA["params_rang_a"])
        rank = "RANG_A"

    zlog("info", "REGISTRY", "modèle résolu",
         bot_type="jessica", plan=plan, has_boost=has_boost,
         model=model, rank=rank)

    return {
        "bot": "jessica",
        "plan": plan,
        "has_boost": bool(has_boost),
        "rank": rank,
        "model": model,
        "fallback": JESSICA["fallback"],
        "params": params,
    }


def get_vision_config(kind: str = "ocr_produit") -> Dict[str, Any]:
    """Config LLM pour la vision (OCR produit ou paiement)."""
    k = (kind or "ocr_produit").strip().lower()
    if k in {"paiement", "ocr_paiement"}:
        return {
            "bot": "vision_paiement",
            "model": VISION["ocr_paiement"],
            "params": dict(VISION["params_paiement"]),
        }
    return {
        "bot": "vision_produit",
        "model": VISION["ocr_produit"],
        "params": dict(VISION["params_ocr"]),
    }


def get_insight_config() -> Dict[str, Any]:
    """Config LLM pour Zeta Insight (bilans analytiques)."""
    return {
        "bot": "insight",
        "model": INSIGHT["model"],
        "params": dict(INSIGHT["params"]),
    }


def is_model_allowed(model_name: Optional[str]) -> bool:
    """True si le modèle appartient à la liste autorisée du registry v2.0."""
    if not model_name:
        return False
    allowed = str(model_name).strip() in ALLOWED_MODELS
    if not allowed:
        zlog("warning", "MODEL_GUARD", "modèle interdit remplacé",
             requested=model_name,
             fallback="will be resolved by caller",
             context="bot_registry")
    return allowed


def get_registry_snapshot() -> Dict[str, Any]:
    """État courant du registry (observabilité / dashboard admin)."""
    return {
        "amanda": {
            "model": _AMANDA_MODEL,
            "fallback": _AMANDA_FALLBACK,
            "params": AMANDA["params"],
        },
        "jessica": {
            "rang_a": _JESSICA_RANG_A,
            "rang_s": _JESSICA_RANG_S,
            "boost": _JESSICA_BOOST,
            "fallback": _JESSICA_FALLBACK,
        },
        "vision": {
            "ocr_produit": VISION["ocr_produit"],
            "ocr_paiement": VISION["ocr_paiement"],
        },
        "insight": {
            "model": INSIGHT["model"],
        },
        "allowed_models": sorted(ALLOWED_MODELS),
    }
