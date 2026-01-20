"""
💰 CONFIGURATION DES COÛTS ET OPTIMISATIONS TOKEN
"""

# Objectifs de réduction par type de requête
CONTEXT_TARGETS = {
    "simple": 1500,      # Questions simples: -56% coûts
    "standard": 2500,    # Questions standard: -27% coûts  
    "complex": 3000,     # Questions complexes: -12% coûts
    "premium": 3500      # Questions premium: pas de limite
}

# Seuils pour déterminer le type de requête
REQUEST_COMPLEXITY = {
    "simple": {
        "keywords": ["prix", "tarif", "combien", "coût"],
        "max_words": 8,
        "max_intentions": 1
    },
    "standard": {
        "keywords": ["livraison", "produit", "commande"],
        "max_words": 15,
        "max_intentions": 2
    },
    "complex": {
        "max_words": 25,
        "max_intentions": 3
    }
}

def get_context_target(query: str, supabase_docs: int, meili_docs: int) -> int:
    """
    🎯 DÉTERMINE L'OBJECTIF DE CONTEXTE SELON LA COMPLEXITÉ
    """
    words = len(query.split())
    intentions = supabase_docs + meili_docs
    
    # Classification automatique
    if words <= 8 and intentions <= 1:
        return CONTEXT_TARGETS["simple"]
    elif words <= 15 and intentions <= 2:
        return CONTEXT_TARGETS["standard"]
    elif words <= 25 and intentions <= 3:
        return CONTEXT_TARGETS["complex"]
    else:
        return CONTEXT_TARGETS["premium"]

def estimate_cost_savings(original_chars: int, optimized_chars: int, model: str = "claude") -> dict:
    """
    💰 ESTIME LES ÉCONOMIES DE COÛTS
    """
    
    # Coûts par token (pour 1M tokens)
    MODEL_COSTS = {
        "claude": {"input": 3.00, "output": 15.00},
        "gpt4o": {"input": 5.00, "output": 15.00},
        "gemini": {"input": 0.50, "output": 1.50}
    }
    
    original_tokens = original_chars // 4
    optimized_tokens = optimized_chars // 4
    saved_tokens = original_tokens - optimized_tokens
    
    costs = MODEL_COSTS.get(model, MODEL_COSTS["claude"])
    
    # Calcul économies par requête
    cost_per_request_original = (original_tokens / 1_000_000) * costs["input"]
    cost_per_request_optimized = (optimized_tokens / 1_000_000) * costs["input"]
    savings_per_request = cost_per_request_original - cost_per_request_optimized
    
    # Calcul économies mensuelles (estimations)
    monthly_savings = {
        "1k_requests": savings_per_request * 1000,
        "10k_requests": savings_per_request * 10000,
        "100k_requests": savings_per_request * 100000
    }
    
    return {
        "tokens_saved": saved_tokens,
        "reduction_percent": (saved_tokens / original_tokens) * 100,
        "cost_per_request_saved": savings_per_request,
        "monthly_savings": monthly_savings
    }




