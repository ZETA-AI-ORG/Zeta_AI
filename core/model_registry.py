"""
🏆 MODEL REGISTRY - ZETA AI V2.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Source unique de vérité pour les modèles LLM autorisés.

FAMILLE AUTORISÉE : Gemma (4-26B / 4-31B) + Gemini (3.1 Flash-Lite, 3.1 Pro).
INTERDIT : Groq/Llama, DeepSeek, Mistral, Qwen, Claude, GPT…

Matrice d'intelligence officielle (validée 19/04/2026) :
┌──────────┬────────────────────────────────────────┬───────────────────────────────┐
│ NIVEAU   │ MODÈLE OPENROUTER (SLUG)               │ CONTEXTE D'UTILISATION        │
├──────────┼────────────────────────────────────────┼───────────────────────────────┤
│ RANG A   │ google/gemma-4-26b-a4b-it              │ Découverte, Starter (Amanda)  │
│ RANG S   │ google/gemma-4-31b-it                  │ Pro/Elite défaut (Jessica)    │
│ RANG SS  │ google/gemini-3.1-flash-lite-preview   │ Option BOOST (Jessica Boost)  │
│ INSIGHT  │ google/gemini-3.1-pro-preview          │ Zeta Insight (bilans)         │
└──────────┴────────────────────────────────────────┴───────────────────────────────┘

Correspondance Bot → Plan → Modèle :
- Amanda          → Découverte / Starter           → RANG A   (gemma-4-26b-a4b-it)
- Jessica         → Pro / Elite (sans BOOST)       → RANG S   (gemma-4-31b-it)
- Jessica Boost   → Pro / Elite (avec BOOST)       → RANG SS  (gemini-3.1-flash-lite-preview)
- Zeta Insight    → Analytics / Bilans stratégiques→ INSIGHT  (gemini-3.1-pro-preview)

Surcharge possible via variables d'environnement :
  MODEL_RANG_A, MODEL_RANG_S, MODEL_RANG_SS, MODEL_INSIGHT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
from __future__ import annotations
import os
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# 🏆 MATRICE OFFICIELLE (surchargeable via env)
# ═══════════════════════════════════════════════════════════════════════════════

MODEL_RANG_A: str = os.getenv("MODEL_RANG_A", "google/gemma-4-26b-a4b-it")
MODEL_RANG_S: str = os.getenv("MODEL_RANG_S", "google/gemma-4-31b-it")
MODEL_RANG_SS: str = os.getenv("MODEL_RANG_SS", "google/gemini-3.1-flash-lite-preview")
MODEL_INSIGHT: str = os.getenv("MODEL_INSIGHT", "google/gemini-3.1-pro-preview")

# Modèle par défaut universel (Jessica / Pro-Elite = RANG S)
DEFAULT_MODEL: str = os.getenv("MODEL_DEFAULT", MODEL_RANG_S)


# ═══════════════════════════════════════════════════════════════════════════════
# 🛡️ GARDE-FOU (sécurité : refuse tout modèle hors famille autorisée)
# ═══════════════════════════════════════════════════════════════════════════════

# Préfixes autorisés (cohérence Gemma/Gemini uniquement)
_ALLOWED_PREFIXES = (
    "google/gemma",
    "google/gemini",
)

# Bannis explicitement (legacy Groq / DeepSeek / Mistral / Llama / Qwen / Claude / GPT)
_BANNED_PATTERNS = (
    "groq/", "deepseek", "mistral", "llama", "meta-llama",
    "qwen", "anthropic", "claude", "openai", "gpt-",
)


def is_model_allowed(model_name: Optional[str]) -> bool:
    """True si le modèle appartient à la famille Gemma/Gemini autorisée.
    
    Mode test: définir TEST_ALLOW_MODELS="model1,model2" pour autoriser temporairement
    des modèles spécifiques (ex: deepseek/deepseek-v3.2,qwen/qwen3-235b-a22b-2507).
    """
    if not model_name:
        return False
    m = str(model_name).strip().lower()
    
    # Mode test: allowlist explicite via env (ne pas utiliser en production)
    _test_allow = os.getenv("TEST_ALLOW_MODELS", "")
    if _test_allow:
        _allowed_test_models = [x.strip().lower() for x in _test_allow.split(",") if x.strip()]
        if any(m == allowed or model_name == allowed for allowed in _test_allow.split(",") if allowed.strip()):
            return True
    
    if any(bad in m for bad in _BANNED_PATTERNS):
        return False
    return any(m.startswith(p) for p in _ALLOWED_PREFIXES)


def enforce_allowed_model(model_name: Optional[str], *, context: str = "") -> str:
    """
    Garde-fou central : retourne le modèle demandé s'il est autorisé,
    sinon fallback sur DEFAULT_MODEL en loggant l'incident.
    
    Utilisation :
        model = enforce_allowed_model(requested_model, context="botlive_closing")
    """
    if is_model_allowed(model_name):
        return str(model_name)

    logger.warning(
        "🚫 [MODEL_GUARD] Modèle refusé '%s' (context=%s) → fallback '%s'",
        model_name, context or "unknown", DEFAULT_MODEL,
    )
    return DEFAULT_MODEL


# ═══════════════════════════════════════════════════════════════════════════════
# 🧭 RÉSOLUTION PAR PLAN + BOOST (spec commerciale 2026)
# ═══════════════════════════════════════════════════════════════════════════════

def resolve_model_for_plan(
    plan_name: Optional[str],
    *,
    has_boost: bool = False,
    is_closing: bool = False,
    is_pivot: bool = False,
) -> str:
    """
    Sélectionne le modèle LLM selon la grille commerciale 2026.

    Args:
        plan_name: "decouverte" | "starter" | "pro" | "elite" (insensible à la casse)
        has_boost: True si l'option BOOST est activée (Pro/Elite uniquement)
        is_closing: True si la commande est 100% complète (phase C)
        is_pivot: True si le client change de produit → remonter sur plus puissant

    Returns:
        str: ID OpenRouter (garanti famille Gemma/Gemini)
    """
    plan = (plan_name or "starter").strip().lower()

    # Cas pivot : toujours remonter sur le plus puissant disponible du plan
    if is_pivot:
        if plan in {"pro", "elite"} and has_boost:
            return MODEL_RANG_SS
        if plan in {"pro", "elite"}:
            return MODEL_RANG_S
        return MODEL_RANG_A  # Starter/Découverte

    # Cas closing : modèle économique (Rang A) pour toutes les strates
    if is_closing:
        return MODEL_RANG_A

    # Mode normal (négociation)
    if plan in {"decouverte", "découverte"}:
        return MODEL_RANG_A
    if plan == "starter":
        return MODEL_RANG_A
    if plan in {"pro", "elite"}:
        return MODEL_RANG_SS if has_boost else MODEL_RANG_S

    # Fallback sécurisé
    logger.info("[MODEL_REGISTRY] plan='%s' inconnu → RANG_A", plan)
    return MODEL_RANG_A


def get_registry_snapshot() -> Dict[str, str]:
    """Retourne l'état courant du registry (pour logs / debug / observabilité)."""
    return {
        "RANG_A": MODEL_RANG_A,
        "RANG_S": MODEL_RANG_S,
        "RANG_SS": MODEL_RANG_SS,
        "INSIGHT": MODEL_INSIGHT,
        "DEFAULT": DEFAULT_MODEL,
    }


if __name__ == "__main__":
    # Test rapide
    print("🏆 REGISTRY SNAPSHOT :", get_registry_snapshot())
    print("  decouverte          →", resolve_model_for_plan("decouverte"))
    print("  starter             →", resolve_model_for_plan("starter"))
    print("  pro (no boost)      →", resolve_model_for_plan("pro"))
    print("  pro (boost)         →", resolve_model_for_plan("pro", has_boost=True))
    print("  elite (closing)     →", resolve_model_for_plan("elite", is_closing=True))
    print("  elite (pivot)       →", resolve_model_for_plan("elite", is_pivot=True, has_boost=True))
    print("")
    print("🛡️ GARDE-FOU :")
    print("  gemma-3-27b-it      →", is_model_allowed("google/gemma-3-27b-it"))
    print("  llama-3.3-70b       →", is_model_allowed("meta-llama/llama-3.3-70b-instruct"))
    print("  deepseek-v3         →", is_model_allowed("deepseek/deepseek-v3"))
    print("  enforce(groq)       →", enforce_allowed_model("groq/llama-3.1-8b-instant", context="test"))
