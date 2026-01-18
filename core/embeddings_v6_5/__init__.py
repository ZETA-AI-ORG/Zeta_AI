# -*- coding: utf-8 -*-
"""
EMBEDDINGS V6.5 - Layer 3 Sémantique (Filet de sécurité)

Architecture hybride :
- Layer 1 : V6 Prefilter (Paiement/Contact/SAV) → conf 0.93-0.98
- Layer 2 : V5 Keywords (Prix/Livraison/Achat) → conf 0.90-0.95
- Layer 3 : Embeddings V6.5 (Edge cases) → conf 0.75-0.88 ← CE MODULE
- Layer 4 : SetFit ML (Fallback) → conf variable

RÈGLES STRICTES :
- Seuil min : 0.75 (en dessous = ignore)
- Seuil suggestion : 0.82 (au-dessus = log pour review)
- Confiance max : 0.88 (ne jamais dépasser V6/V5)
- Max prototypes : 8 par intent
- Cache obligatoire (performance)
- Pas d'auto-learning (suggestions manuelles uniquement)
"""

from .semantic_filter import SemanticFilterV65
from .suggestion_logger import SuggestionLoggerV65
from .prototypes import INTENT_PROTOTYPES_V65, EMBEDDINGS_CONFIG_V65

__all__ = [
    "SemanticFilterV65",
    "SuggestionLoggerV65", 
    "INTENT_PROTOTYPES_V65",
    "EMBEDDINGS_CONFIG_V65",
]
