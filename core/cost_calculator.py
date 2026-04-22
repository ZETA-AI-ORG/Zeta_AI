"""
💰 ZETA AI — COST CALCULATOR (OpenRouter real pricing)
Référence : PIPELINE_COMPLETE.md §4

Calcul du coût réel par appel LLM en fonction :
- Du modèle utilisé (COST_TABLE)
- Des tokens prompt (billable = prompt - cached)
- Des tokens cached (cache_read rate réduit)
- Des tokens completion

RÈGLE : chaque calcul est loggué via zlog.
"""

from core.zlog import zlog

# ═══════════════════════════════════════════════════════════════════════════════
# TABLE DE COÛTS — TARIFS OPENROUTER RÉELS ($/1M tokens)
# Source : PIPELINE_COMPLETE.md §4 — VERSION GRAVÉE
# ═══════════════════════════════════════════════════════════════════════════════

COST_TABLE = {
    "qwen/qwen3-235b-a22b-2507":            {"input": 0.071, "output": 0.10},
    "google/gemma-4-26b-a4b-it":            {"input": 0.08,  "output": 0.35},
    "google/gemma-4-31b-it":                {"input": 0.13,  "output": 0.38},
    "deepseek/deepseek-v3.2":               {"input": 0.081, "output": 0.419},
    "google/gemini-3.1-flash-lite-preview": {"input": 0.10,  "output": 0.40},
    "google/gemini-3.1-pro-preview":        {"input": 0.50,  "output": 1.50},
}

# Cache read rates (providers OpenRouter)
# Tokens lus depuis le cache coûtent ~10% du prix input normal
CACHE_READ_TABLE = {
    "qwen/qwen3-235b-a22b-2507":            0.0071,  # 10% of input
    "google/gemma-4-26b-a4b-it":            0.01,    # DeepInfra
    "google/gemma-4-31b-it":                0.013,
    "deepseek/deepseek-v3.2":               0.0081,  # DeepSeek direct
    "google/gemini-3.1-flash-lite-preview": 0.025,
    "google/gemini-3.1-pro-preview":        0.125,
}

# Taux de conversion USD → FCFA
USD_TO_FCFA = 615


def compute_cost(model: str, prompt_tokens: int, completion_tokens: int,
                 cached_tokens: int = 0) -> float:
    """
    Calcule le coût réel d'un appel LLM.

    Args:
        model:             Identifiant modèle OpenRouter
        prompt_tokens:     Tokens prompt total (inclut cached)
        completion_tokens: Tokens de complétion
        cached_tokens:     Tokens lus depuis le cache (prompt_tokens_details.cached_tokens)

    Returns:
        Coût total en USD (float)

    Formule:
        cost = (billable_input * rate_input + cached * rate_cache + completion * rate_output) / 1_000_000
    """
    rates = COST_TABLE.get(model)
    if not rates:
        zlog("warning", "COST", "modèle absent de COST_TABLE — tarif par défaut",
             model=model)
        rates = {"input": 0.10, "output": 0.40}

    cache_read_rate = CACHE_READ_TABLE.get(model, rates["input"] * 0.1)

    billable_input = max(prompt_tokens - cached_tokens, 0)

    cost = (
        billable_input    * rates["input"]  +
        cached_tokens     * cache_read_rate +
        completion_tokens * rates["output"]
    ) / 1_000_000

    cache_hit_pct = round(cached_tokens / max(prompt_tokens, 1) * 100, 1)

    zlog("info", "COST", "coût calculé",
         model=model,
         prompt_tokens=prompt_tokens,
         cached_tokens=cached_tokens,
         billable_input=billable_input,
         completion_tokens=completion_tokens,
         cache_hit_rate_pct=cache_hit_pct,
         cost_usd=round(cost, 8),
         cost_fcfa=round(cost * USD_TO_FCFA, 4))

    return cost
