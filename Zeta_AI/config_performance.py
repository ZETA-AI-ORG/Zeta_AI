"""
⚡ CONFIGURATION PERFORMANCE - Optimisation < 6s
Gestion des logs et paramètres de performance
"""

import os
import logging

# ========== ENVIRONNEMENT ==========
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")  # production | development | test

# ========== LOGS CONFIGURATION ==========
def configure_performance_logs():
    """
    Configure les logs selon l'environnement
    Production: WARNING+ seulement (gain ~15s)
    Development: DEBUG (tous les logs)
    """
    if ENVIRONMENT == "production":
        # Désactiver logs verbeux en production
        logging.getLogger("database.vector_store_clean_v2").setLevel(logging.WARNING)
        logging.getLogger("core.context_extractor").setLevel(logging.WARNING)
        logging.getLogger("core.delivery_zone_extractor").setLevel(logging.WARNING)
        logging.getLogger("core.universal_rag_engine").setLevel(logging.WARNING)
        logging.getLogger("core.thinking_parser").setLevel(logging.WARNING)
        logging.getLogger("core.data_change_tracker").setLevel(logging.WARNING)
        logging.getLogger("core.conversation_checkpoint").setLevel(logging.WARNING)
        logging.getLogger("app").setLevel(logging.INFO)
        
        print("⚡ [PERFORMANCE] Logs optimisés pour production (WARNING+)")
    else:
        # Tous les logs en développement
        logging.basicConfig(level=logging.DEBUG)
        print("🔧 [DEV] Logs verbeux activés (DEBUG)")

# ========== CACHE CONFIGURATION ==========
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
CACHE_EXACT_TTL = int(os.getenv("CACHE_EXACT_TTL", "1800"))  # 30 minutes
CACHE_SEMANTIC_TTL = int(os.getenv("CACHE_SEMANTIC_TTL", "3600"))  # 1 heure
FAQ_CACHE_ENABLED = os.getenv("FAQ_CACHE_ENABLED", "true").lower() == "true"

# ========== PROMPT CACHE LOCAL ==========
PROMPT_LOCAL_CACHE_ENABLED = True
PROMPT_CACHE_TTL = 3600  # 1 heure

# ========== HYDE CONFIGURATION ==========
HYDE_ENABLED = os.getenv("HYDE_ENABLED", "true").lower() == "true"
HYDE_SKIP_SIMPLE_QUERIES = True  # Skip HYDE pour questions simples

# Patterns de questions simples (pas besoin de HYDE)
SIMPLE_QUERY_PATTERNS = [
    r'prix\s+\d+',
    r'combien\s+(coute|cout|coûte|coût)',
    r'livraison\s+\w+',
    r'contact|telephone|whatsapp|tel|phone',
    r'paiement|wave|orange\s+money',
    r'horaire|heure|ouvert',
    r'adresse|localisation|où'
]

# ========== CONVERSATION HISTORY ==========
MAX_HISTORY_MESSAGES = 5  # Limiter historique (gain ~1s)
MAX_HISTORY_CHARS = 500   # Tronquer si trop long

# ========== MEILISEARCH OPTIMIZATION ==========
MAX_NGRAMS = 30  # Limiter n-grams (gain ~1.5s)
MEILISEARCH_TIMEOUT = 3000  # 3 secondes max

# ========== ASYNC OPERATIONS ==========
ASYNC_CHECKPOINT = True  # Checkpoint en background
ASYNC_TRACKING = True    # Tracking en background
ASYNC_LOGS = True        # Logs JSON en background

# ========== PERFORMANCE TRACKING ==========
TRACK_PERFORMANCE = True
PERFORMANCE_LOG_PATH = "logs/performance"

# ========== GROQ LLM ==========
LLM_TIMEOUT = 10000  # 10 secondes max
LLM_STREAMING = False  # À implémenter

# ========== AUTO-LEARNING SYSTEM ==========
ENABLE_AUTO_LEARNING = os.getenv("ENABLE_AUTO_LEARNING", "false").lower() == "true"
AUTO_LEARNING_MIN_OCCURRENCES = 2  # Min occurrences pour créer pattern
AUTO_LEARNING_CONFIDENCE_THRESHOLD = 0.8  # Min confiance pour auto-apply

# Modules d'auto-learning activés
LEARNING_PATTERNS = True  # Apprendre patterns regex
LEARNING_THINKING = True  # Analytics thinking LLM
LEARNING_DOCUMENTS = True  # Intelligence documentaire
LEARNING_LLM_PERF = True  # Performance LLM tracking
LEARNING_AUTO_IMPROVEMENTS = False  # Auto-apply améliorations (prudence!)
LEARNING_FAQ_GENERATION = True  # Générer FAQ auto

print(f"⚡ [CONFIG] Environnement: {ENVIRONMENT}")
print(f"⚡ [CONFIG] Cache: {'✅ Activé' if CACHE_ENABLED else '❌ Désactivé'}")
print(f"⚡ [CONFIG] HYDE: {'✅ Activé' if HYDE_ENABLED else '❌ Désactivé'}")
print(f"⚡ [CONFIG] HYDE skip simple: {'✅ Oui' if HYDE_SKIP_SIMPLE_QUERIES else '❌ Non'}")
print(f"⚡ [CONFIG] Auto-Learning: {'✅ Activé' if ENABLE_AUTO_LEARNING else '❌ Désactivé'}")
