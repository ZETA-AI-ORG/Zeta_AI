# -*- coding: utf-8 -*-
import warnings
warnings.filterwarnings("ignore")
from dotenv import load_dotenv
load_dotenv()

import logging
import os
import time
import uuid
from fastapi import FastAPI, HTTPException, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from prometheus_fastapi_instrumentator import Instrumentator
from metrics import setup_metrics
from fastapi.middleware.cors import CORSMiddleware
import requests
import tempfile
import re
from core.order_state_tracker import order_tracker

# ========== OPTIMISATION PERFORMANCE ==========
from config_performance import (
    configure_performance_logs,
    ENVIRONMENT,
    HYDE_SKIP_SIMPLE_QUERIES,
    MAX_HISTORY_MESSAGES,
    MAX_HISTORY_CHARS
)

# Feature flag pour la couche HYDE v18 parallèle (mode expérimental)
BOTLIVE_V18_ENABLED = os.getenv("BOTLIVE_V18_ENABLED", "false").lower() == "true"
# Nouveau feature flag: router embeddings Botlive (prioritaire sur HYDE quand activé)
BOTLIVE_ROUTER_EMBEDDINGS_ENABLED = os.getenv("BOTLIVE_ROUTER_EMBEDDINGS_ENABLED", "false").lower() == "true"

# Logger
# Configuration globale du logging (horodatage, niveau, message)
# ✅ OPTIMISATION: Niveau INFO par défaut (pas DEBUG) pour gain performance
LOG_LEVEL_STR = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_STR, logging.INFO)
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("app")
logger.setLevel(LOG_LEVEL)

# Configurer les logs selon l'environnement
configure_performance_logs()

# ========== ACTIVATION LOGGER JSON SERVEUR ==========
# Capture TOUS les logs (print, logger, erreurs) dans un fichier JSON
try:
    from core.server_logger import setup_server_logging
    setup_server_logging()
    print("✅ [SERVER_LOGGER] Logs serveur activés → logs/server/")
except Exception as e:
    print(f"⚠️ [SERVER_LOGGER] Erreur activation: {e}")

# Créer un gestionnaire de console
console_handler = logging.StreamHandler()
console_handler.setLevel(LOG_LEVEL)

# Créer un formateur
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Ajouter le gestionnaire au logger
logger.addHandler(console_handler)
logger.info("Logger configuré avec succès")

# Réduire la verbosité des bibliothèques bruyantes (HTTP/2, clients HTTP)
for noisy_logger in [
    "httpcore",
    "httpx",
    "hpack",
    "h2",
    "urllib3",
    "urllib3.connectionpool",
]:
    try:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
    except Exception:
        pass

app = FastAPI()

# Événements de cycle de vie pour le cache global
# SUPPRIMÉ - Remplacé par startup enhanced ci-dessous

@app.on_event("shutdown")
async def shutdown_event():
    """Nettoyage global des caches à l'arrêt de l'application"""
    try:
        from core.unified_cache_system import get_unified_cache_system
        cache_system = get_unified_cache_system()
        results = await cache_system.cleanup_all_caches()
        logger.info(f"🧹 Caches nettoyés: {results}")
    except Exception as e:
        logger.warning(f"⚠️ Échec nettoyage caches à l'arrêt: {e}")
    
    # ========== FLUSH LOGS SERVEUR ==========
    try:
        from core.server_logger import flush_server_logs
        flush_server_logs()
        logger.info("📝 Logs serveur sauvegardés")
    except Exception as e:
        logger.warning(f"⚠️ Erreur flush logs: {e}")

# --- SÉCURITÉ MINIMALE: CORS & API KEY ---
# Configuration CORS OPTIMISÉE
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    max_age=3600,
)

# Check API key presence at startup (Meilisearch & Supabase)
import config
if not config.MEILI_API_KEY or not config.SUPABASE_KEY:
    import warnings
    warnings.warn("[SECURITY] Clé API Meilisearch ou Supabase manquante! Vérifiez vos variables d'environnement.")

print("🔍 [DEBUG] Importing core.models...")
from core.models import ChatRequest
print("🔍 [DEBUG] Importing FIX_CONTEXT_LOSS_COMPLETE...")
try:
    from FIX_CONTEXT_LOSS_COMPLETE import build_smart_context_summary, extract_from_last_exchanges
    print("✅ [DEBUG] FIX_CONTEXT_LOSS_COMPLETE imported")
except Exception as e:
    logger.warning(f"⚠️ FIX_CONTEXT_LOSS_COMPLETE import failed: {e}")
    # Fallback functions
    def build_smart_context_summary(*args, **kwargs):
        return ""
    def extract_from_last_exchanges(*args, **kwargs):
        return []
print("🔍 [DEBUG] Importing pydantic...")
from pydantic import BaseModel

ZETA_BOTLIVE_ONLY = os.getenv("ZETA_BOTLIVE_ONLY", "false").lower() == "true"

if not ZETA_BOTLIVE_ONLY:
    print("🔍 [DEBUG] Importing universal_rag_engine...")
    from core.universal_rag_engine import get_universal_rag_response
    print("🔍 [DEBUG] Importing prompt_manager...")
    from core.prompt_manager import PromptManager
    print("🔍 [DEBUG] Importing supabase_client...")
    from database.supabase_client import get_company_system_prompt, search_supabase_semantic, get_supabase_client
    print("🔍 [DEBUG] Importing ingestion_api...")
    from ingestion.ingestion_api import router as ingestion_router
    print("🔍 [DEBUG] Importing global_embedding_cache...")
    from core.global_embedding_cache import initialize_global_cache, cleanup_global_cache
else:
    print(" [DEBUG] ZETA_BOTLIVE_ONLY=true: RAG engine & ingestion routes disabled on import")
    from database.supabase_client import get_company_system_prompt, get_supabase_client
    # PromptManager reste utile même en mode Botlive-only (gestion des versions de prompt)
    from core.prompt_manager import PromptManager
print(" [DEBUG] Importing auth router...")
from routes.auth import router as auth_router
print(" [DEBUG] Importing routes...")
from routes import auth, messenger
print(" [DEBUG] Importing meili_ingest_api...")
from meili_ingest_api import router as meili_router
# from routes.rag import router as rag_router  # SUPPRIMÉ - fichier obsolète
print(" [DEBUG] Importing meili router...")
from routes.meili import router as meili_explorer_router
app.include_router(meili_explorer_router, prefix="/meili")
print(" [DEBUG] Importing utils...")
from utils import log3, groq_resilience
print(" [DEBUG] Importing security_validator...")
from core.security_validator import validate_user_prompt
print(" [DEBUG] Importing hallucination_guard...")
from core.hallucination_guard import check_ai_response
print(" [DEBUG] Importing error_handler...")
from core.error_handler import safe_api_call, global_error_handler
print(" [DEBUG] Importing circuit_breaker...")
from core.circuit_breaker import groq_circuit_breaker, supabase_circuit_breaker, meilisearch_circuit_breaker
print(" [DEBUG] Importing integrations router...")
from routes.integrations import router as integrations_router
import traceback

# --- Image search API ---
print(" [DEBUG] Importing image_search...")
# TEMPORAIREMENT DÉSACTIVÉ - Bloque le démarrage
# from api.image_search import router as image_search_router
print(" [DEBUG] Image search router SKIPPED (debugging)")

# --- Botlive API Routes ---
print(" [DEBUG] Importing botlive router...")
from routes.botlive import router as botlive_router
app.include_router(botlive_router)
print(" [DEBUG] Botlive router ACTIVATED")
print(" [DEBUG] Importing WhatsApp router...")
try:
    from routes.whatsapp import router as whatsapp_router
    app.include_router(whatsapp_router)
    print(" [DEBUG] WhatsApp router ACTIVATED")
except Exception as _wa_e:
    print(f" [DEBUG] WhatsApp router not loaded: {_wa_e}")
print(" [DEBUG] All imports completed!")

# --- Models for prompt admin ---
class PromptUpdateRequest(BaseModel):
    prompt_template: str
    created_by: str

class PromptRollbackRequest(BaseModel):
    target_version: int
    created_by: str

# NOTE: Duplicate FastAPI() instantiation removed to keep a single app instance

# --- Monitoring Prometheus ---
setup_metrics(app)

# --- Rate Limiting (slowapi) ---
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- Événement de démarrage pour pré-charger les modèles ---
from embedding_models import get_embedding_model

@app.on_event("startup")
async def startup_event():
    """
    🚀 STARTUP ENHANCED - ÉLIMINATION LATENCE 3.6s
    - Pré-charge TOUS les modèles d'embedding
    - Initialise les caches avec warm-up
    - Génère embeddings de test pour optimisation
    - Monitoring performance temps réel
    - Active logging serveur JSON complet
    """
    import time
    startup_start = time.time()
    
    # ========== ACTIVER LOGGING SERVEUR JSON ==========
    try:
        from core.server_logger import setup_server_logging
        setup_server_logging()
        print("[STARTUP] 📝 Logging serveur JSON activé")
    except Exception as e:
        print(f"[STARTUP] ⚠️ Erreur logging serveur: {e}")
    
    print("[STARTUP] 🚀 ENHANCED - Élimination latence 3.6s en cours...")
    
    try:
        # Mode léger pour environnements contraints (ex: Render Free 512Mo)
        if ZETA_BOTLIVE_ONLY or os.getenv("ZETA_LIGHT_STARTUP", "false").lower() == "true":
            print("[STARTUP] ⚠️ Light/Botlive-only startup actif: pré-chargement des modèles désactivé")
            return

        # 1. Initialiser le système de cache unifié
        from core.unified_cache_system import get_unified_cache_system
        cache_system = get_unified_cache_system()
        print("[STARTUP] ✅ Cache unifié initialisé")
        
        # 2. Pré-charger uniquement les modèles 768D (standardisation perf/mémoire)
        from embedding_models import EMBEDDING_MODELS
        models_loaded = 0
        # Filtrer aux modèles 768D (ex: all-mpnet-base-v2, intfloat/e5-base-v2)
        filtered_models = {k: v for k, v in EMBEDDING_MODELS.items() if v.get("dim") == 768}
        filtered_models_count = len(filtered_models)
        
        print(f"[STARTUP] 🧠 Pré-chargement des {filtered_models_count} modèles 768D...")
        for model_key, model_info in filtered_models.items():
            try:
                model_start = time.time()
                model = cache_system.get_cached_model(model_info["name"])
                model_time = time.time() - model_start
                
                if model:
                    models_loaded += 1
                    print(f"[STARTUP] ✅ {model_key}: {model_time:.2f}s")
                else:
                    print(f"[STARTUP] ⚠️ {model_key}: Fallback nécessaire")
            except Exception as e:
                print(f"[STARTUP] ❌ {model_key}: {str(e)[:50]}")
        
        # 3. WARM-UP avec embeddings de test
        print("[STARTUP] 🔥 WARM-UP - Génération embeddings de test...")
        test_queries = [
            "Bonjour, combien coûte un paquet de couches?",
            "Livraison à Yopougon possible?",
            "Quels sont vos prix?"
        ]
        
        warmup_start = time.time()
        for i, test_query in enumerate(test_queries):
            try:
                from embedding_models import embed_text
                embedding = await embed_text(test_query, use_cache=True)
                print(f"[STARTUP] 🔥 Test {i+1}/3: {len(embedding)} dims")
            except Exception as e:
                print(f"[STARTUP] ⚠️ Test {i+1} échoué: {str(e)[:30]}")
        
        warmup_time = time.time() - warmup_start
        print(f"[STARTUP] ✅ WARM-UP terminé en {warmup_time:.2f}s")
        
        # 3.5. Initialiser Auto-Learning System
        try:
            from core.auto_learning_wrapper import init_auto_learning
            init_auto_learning()
        except Exception as e:
            print(f"[STARTUP] ⚠️ Auto-learning: {e}")
        
        # 4. Précharger les modèles populaires (sécurité)
        preload_count = cache_system.model_cache.preload_popular_models()
        print(f"[STARTUP] 📈 {preload_count} modèles populaires confirmés")
        
        # ✅ PHASE 1: PRÉ-CHARGEMENT MODÈLE 384 POUR FALLBACK RAPIDE
        try:
            from core.supabase_optimized_384 import get_supabase_optimized_384
            print("[STARTUP] 🔥 Pré-chargement modèle 384 dim (fallback Supabase)...")
            supabase_384 = get_supabase_optimized_384(use_float16=True)
            supabase_384.preload_model()
            print("[STARTUP] ✅ Modèle 384 pré-chargé - Fallback instantané activé!")
        except Exception as e:
            print(f"[STARTUP] ⚠️ Erreur pré-chargement 384: {e}")
        
        # 5. Statistiques finales détaillées
        stats = cache_system.get_global_stats()
        total_startup_time = time.time() - startup_start
        
        print("\n" + "="*60)
        print("🎆 STARTUP ENHANCED TERMINÉ AVEC SUCCÈS!")
        print("="*60)
        print(f"🚀 Temps total: {total_startup_time:.2f}s")
        print(f"🧠 Modèles chargés: {models_loaded}/{len(filtered_models)}")
        print(f"💾 Modèles en cache: {stats['model_cache']['models_cached']}")
        print(f"📈 Mémoire système: {stats['model_cache']['system_memory_usage']}")
        print(f"⚡ Embeddings en cache: {stats['embedding_cache']['cache_size']}")
        print(f"🎯 Hit rate: {stats['embedding_cache']['hit_rate_percent']}")
        print("\n📊 PERFORMANCE ATTENDUE:")
        print("  - Première requête: ~0.5s (modèles préchargés)")
        print("  - Requêtes suivantes: ~0.01s (cache hits)")
        print("  - Latence éliminée: 3.6s → 0.01s (❌ 99.7%)")
        print("="*60)
        
    except Exception as e:
        print(f"[STARTUP] ❌ ERREUR CRITIQUE: {e}")
        print("[STARTUP] 🔄 Tentative de fallback...")
        
        # Fallback robuste
        try:
            get_embedding_model()
            print("[STARTUP] ✅ Fallback réussi - modèle de base chargé")
        except Exception as fallback_error:
            print(f"[STARTUP] ❌ FALLBACK ÉCHOUÉ: {fallback_error}")
            print("[STARTUP] ⚠️ Application démarrée SANS pré-chargement")

# Configurer et exposer les métriques Prometheus
Instrumentator().instrument(app).expose(app)

app.include_router(auth.router)
app.include_router(messenger.router)
app.include_router(meili_router)
# Intégrations externes (Messenger multi-tenant, etc.)
app.include_router(integrations_router)
# NOTE: Removed duplicate include of meili_explorer_router; it is already mounted at prefix /meili above

if not ZETA_BOTLIVE_ONLY:
    app.include_router(ingestion_router)
else:
    logger.info("ZETA_BOTLIVE_ONLY=true: ingestion_router not mounted")

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
# app.include_router(image_search_router)  # DÉSACTIVÉ - Bloque le démarrage

# 🚀 NOUVEAU: Monitoring des caches optimisés
try:
    from routes.cache_monitoring import router as cache_monitoring_router
    app.include_router(cache_monitoring_router, prefix="/api", tags=["Cache Monitoring"])
    logger.info("🚀 Monitoring des caches intégré avec succès")
except Exception as e:
    logger.warning(f"⚠️ Erreur intégration monitoring caches: {e}")

# NOUVEAU: Intégration du Mini-LLM Dispatcher
if not ZETA_BOTLIVE_ONLY:
    try:
        from ingestion.enhanced_ingestion_api import router as enhanced_ingestion_router
        app.include_router(enhanced_ingestion_router, tags=["Enhanced-Ingestion"])
        logger.info("Router Enhanced Ingestion avec Mini-LLM Dispatcher monté avec succès")
    except Exception as e:
        logger.warning(f"Impossible de monter le router Enhanced Ingestion: {e}")
else:
    logger.info("ZETA_BOTLIVE_ONLY=true: Enhanced Ingestion router not mounted")

from redis_cache import RedisCache
redis_cache = RedisCache()
from fastapi import APIRouter

admin_router = APIRouter()

@admin_router.post("/admin/cache/flush")
def flush_cache():
    redis_cache.flush_all()
    return {"success": True, "message": "Cache Redis vidé."}

app.include_router(admin_router)

from datetime import datetime
from core.global_prompt_cache import get_global_prompt_cache

@app.post("/admin/cache/prompt/clear")
async def clear_prompt_cache_endpoint(request: dict):
    """
    🔄 Vide le cache prompt pour une entreprise spécifique
    Body: {"company_id": "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"}
    """
    try:
        company_id = request.get("company_id")
        if not company_id:
            raise HTTPException(status_code=400, detail="company_id requis")

        cache = get_global_prompt_cache()
        cleared = await cache.invalidate_prompt(company_id)

        return {
            "status": "success",
            "message": f"Cache prompt vidé pour {company_id}",
            "cache_cleared": cleared,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")

@app.post("/admin/cache/prompt/clear_all")
async def clear_all_prompt_cache_endpoint():
    """🧹 Vide tout le cache prompt"""
    try:
        cache = get_global_prompt_cache()
        cleared_count = await cache.clear_all_prompts()

        return {
            "status": "success",
            "message": "Tout le cache prompt vidé",
            "entries_cleared": cleared_count,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")

@app.get("/admin/cache/prompt/stats")
async def get_prompt_cache_stats_endpoint():
    """📊 Statistiques du cache prompt"""
    try:
        cache = get_global_prompt_cache()
        stats = cache.get_stats()

        return {
            "status": "success",
            "stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")

def deduplicate_conversation_history(history: str) -> str:
    """
    Optimise l'historique conversationnel:
    1. 🎯 OPTIMISÉ: Limite aux 3 derniers échanges (6 messages max) au lieu de 5
    2. Remplace 'assistant:' par 'IA:'
    3. Supprime les doublons consécutifs
    4. 📊 Raccourcit les URLs longues (-98% tokens)
    """
    if not history:
        return ""
    
    # 📊 OPTIMISATION TOKENS: Raccourcir URLs longues
    # Avant: https://scontent-atl3-3.xx.fbcdn.net/v/t1.15752-9/553786504_1339650347521010_7584722332323008254_n.jpg?_nc_cat=108&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=wI6F404RotMQ7kNvwEnhydb&_nc_oc=AdmqrPkDq5bTSUqR3fv3g0PrvQbXW9_9Frci7xyQgQ0werBvu95Sz_8rw99dCA-tpPzw_VcH2vgb6kW0y9q-RJI2&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent-atl3-3.xx&oh=03_Q7cD3wFOCg_nyFNqiAFZ2JtXL-o6TYQJotUYQ0L6mr8mM1BA7g&oe=6938095A
    # Après: [IMAGE]
    # Gain: ~400 chars → ~7 chars = -98% (-170 tokens par URL)
    import re
    # Pattern URLs images (Facebook, autres CDN)
    url_pattern = r'https?://[^\s]{50,}'
    history = re.sub(url_pattern, '[IMAGE]', history)
    
    # Normaliser les formats (ASSISTANT → IA, USER → user)
    history = history.replace('ASSISTANT:', 'IA:')
    history = history.replace('assistant:', 'IA:')
    history = history.replace('USER:', 'user:')
    
    lines = [line.strip() for line in history.split('\n') if line.strip()]
    
    # Filtrer uniquement les messages user/IA (case-insensitive)
    messages = []
    for line in lines:
        line_lower = line.lower()
        if line_lower.startswith('user:') or line_lower.startswith('ia:') or line_lower.startswith('assistant:'):
            messages.append(line)
    
    # 🎯 OPTIMISÉ: Limiter aux 6 derniers messages (3 échanges user/IA) au lieu de 10
    if len(messages) > 6:
        messages = messages[-6:]
        print(f"[HISTORIQUE] ✂️ Tronqué: {len(lines)} → 6 messages (3 échanges)")
    
    # Supprimer doublons consécutifs
    deduplicated = []
    previous_line = None
    
    for line in messages:
        # Éviter doublons consécutifs identiques
        if line != previous_line:
            deduplicated.append(line)
            previous_line = line
    
    result = '\n'.join(deduplicated)
    print(f"[HISTORIQUE] ✅ Optimisé: {len(messages)} → {len(deduplicated)} messages uniques")
    return result


def _sync_order_state_from_notepad(user_id: str, notepad: dict) -> None:
    """Synchronise order_state_tracker avec les données persistées du notepad.

    Utilise uniquement les champs disponibles dans le notepad pour mettre à jour
    l'état de commande (produit, paiement, zone, numéro). Si un champ est absent,
    il n'est pas modifié dans le tracker.
    """

    try:
        # Récupérer les valeurs depuis le notepad Supabase
        produit = notepad.get("last_product_mentioned")

        # ⚠️ PAIEMENT: ne synchroniser que si le paiement est VALIDÉ par OCR
        paiement_info = notepad.get("paiement") or {}
        paiement_value = None
        if paiement_info:
            is_validated = bool(
                paiement_info.get("valid") is True
                or paiement_info.get("validé") is True
                or paiement_info.get("validated") is True
            )
            if is_validated:
                paiement_montant = paiement_info.get("montant") or paiement_info.get("amount")
                if paiement_montant is not None:
                    paiement_value = str(paiement_montant)
                else:
                    # Paiement validé mais montant absent → marquer comme validé générique
                    paiement_value = "paiement_valide"
            else:
                # Paiement présent dans le notepad mais NON validé OCR → ignorer côté tracker
                logger.info(f"[ORDER_STATE_SYNC] Paiement ignoré (non validé OCR) pour {user_id}: {paiement_info}")

        zone = notepad.get("delivery_zone")
        numero = notepad.get("phone_number")

        # Si rien n'est présent, ne rien faire
        if not any([produit, paiement_value, zone, numero]):
            return

        # Comparer avec l'état actuel pour éviter des writes inutiles
        state = order_tracker.get_state(user_id)

        if produit and produit != state.produit:
            order_tracker.update_produit(user_id, str(produit))

        if paiement_value and paiement_value != state.paiement:
            order_tracker.update_paiement(user_id, paiement_value)

        if zone and zone != state.zone:
            order_tracker.update_zone(user_id, str(zone))

        if numero and numero != state.numero:
            order_tracker.update_numero(user_id, str(numero))

    except Exception as e:
        # Ne jamais casser le flux Botlive à cause du tracker, log uniquement
        logger.warning(f"[ORDER_STATE_SYNC] Échec synchronisation order_state_tracker pour {user_id}: {e}")

def _print_hybrid_summary(question: str, thinking: str, response: str, llm_used: str, 
                         prompt_tokens: int, completion_tokens: int, total_cost: float,
                         processing_time: float = 0.0, timings: dict = None, router_metrics: dict = None):
    """
    Affiche un résumé formaté et coloré de la réponse LLM avec temps détaillés incluant routeur HYDE
    """
    # Codes couleur ANSI
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    print("\n" + "="*80)
    print(f"{BOLD}🔵 QUESTION CLIENT:{RESET}")
    print(f"{BLUE}{question}{RESET}")
    print()
    
    if thinking and thinking.strip():
        print(f"{BOLD}🟡 RAISONNEMENT LLM:{RESET}")
        # Formater le thinking sur plusieurs lignes si long
        thinking_lines = thinking.strip().split('\n')
        for line in thinking_lines:
            if line.strip():
                print(f"{YELLOW}{line.strip()}{RESET}")
        print()
    
    print(f"{BOLD}🟢 RÉPONSE AU CLIENT:{RESET}")
    print(f"{GREEN}{response}{RESET}")
    print()
    
    print(f"{BOLD}🔴 TOKENS RÉELS & COÛTS:{RESET}")
    total_tokens = prompt_tokens + completion_tokens
    
    # Calculer les coûts selon le modèle
    if "deepseek" in llm_used.lower():
        # Tarifs DeepSeek V3 (simulés, à ajuster selon tarifs réels)
        input_cost = (prompt_tokens / 1_000_000) * 0.08  # Estimation
        output_cost = (completion_tokens / 1_000_000) * 0.12  # Estimation
        cost_detail = f"${input_cost:.6f} input + ${output_cost:.6f} output"
    else:
        # Tarifs Groq 70B
        input_cost = (prompt_tokens / 1_000_000) * 0.59
        output_cost = (completion_tokens / 1_000_000) * 0.79
        cost_detail = f"${input_cost:.6f} input + ${output_cost:.6f} output"
    
    print(f"{RED}Prompt: {prompt_tokens} | Completion: {completion_tokens} | TOTAL: {total_tokens}{RESET}")
    print(f"{RED}💰 COÛT LLM: ${total_cost:.6f} ({cost_detail}){RESET}")
    
    # Afficher métriques routeur HYDE si présentes
    if router_metrics and router_metrics.get('tokens', 0) > 0:
        router_tokens = router_metrics.get('tokens', 0)
        router_cost = router_metrics.get('cost', 0.0)
        print(f"{RED}💰 COÛT ROUTEUR HYDE (8B): ${router_cost:.6f} ({router_tokens} tokens){RESET}")
        total_with_router = total_cost + router_cost
        print(f"{RED}💰 COÛT TOTAL: ${total_with_router:.6f}{RESET}")
    else:
        print(f"{RED}💰 COÛT TOTAL: ${total_cost:.6f}{RESET}")
    
    print(f"{RED}🤖 MODÈLE: {llm_used}{RESET}")
    print()
    
    # ⏱️ AFFICHAGE TEMPS DÉTAILLÉS
    print(f"{BOLD}⏱️  TEMPS D'EXÉCUTION:{RESET}")
    if timings:
        # Timings détaillés par étape
        print(f"{CYAN}┌─ Étapes détaillées:{RESET}")
        
        # Routage (avec détails HYDE si disponibles)
        if 'routing' in timings:
            routing_time = timings['routing']*1000
            if router_metrics and router_metrics.get('tokens', 0) > 0:
                router_tokens = router_metrics.get('tokens', 0)
                router_cost_fcfa = router_metrics.get('cost', 0) * 600
                print(f"{CYAN}├── 1. Routage HYDE (8B): {routing_time:.2f}ms | {router_tokens} tokens | {router_cost_fcfa:.4f} FCFA{RESET}")
            else:
                print(f"{CYAN}├── 1. Routage intelligent: {routing_time:.2f}ms{RESET}")
        
        # Génération prompt
        if 'prompt_generation' in timings:
            print(f"{CYAN}├── 2. Génération prompt: {timings['prompt_generation']*1000:.2f}ms{RESET}")
        
        # Appel LLM (le plus long généralement)
        if 'llm_call' in timings:
            print(f"{CYAN}├── 3. Appel LLM ({llm_used}): {timings['llm_call']*1000:.2f}ms{RESET}")
        
        # Exécution outils
        if 'tools_execution' in timings:
            tools_time = timings['tools_execution']*1000
            if tools_time > 0.1:
                print(f"{CYAN}├── 4. Exécution outils: {tools_time:.2f}ms{RESET}")
            else:
                print(f"{CYAN}├── 4. Exécution outils: <0.1ms (aucun outil){RESET}")
        
        print(f"{CYAN}└── {RESET}")
    
    # Temps total
    print(f"{MAGENTA}{BOLD}⏱️  TEMPS TOTAL REQUÊTE: {processing_time*1000:.2f}ms ({processing_time:.3f}s){RESET}")
    print("="*80 + "\n")

async def _process_botlive_vision(image_url: str, company_phone: str = None) -> dict:
    """
    Traite une image pour le système hybride Botlive
    Retourne le contexte vision formaté
    
    Args:
        image_url: URL de l'image
        company_phone: Numéro de téléphone de l'entreprise pour filtrage transactions
    """
    import requests
    import tempfile
    import os

    # Mode ultra-light: désactiver complètement la vision si demandé (ex: Render Free 512Mo)
    if os.getenv("DISABLE_VISION_MODELS", "false").lower() == "true":
        print("[VISION] ⚠️ Vision désactivée (DISABLE_VISION_MODELS=true) → aucun modèle BLIP/EasyOCR chargé")
        return {
            'detected_objects': [],
            'filtered_transactions': []
        }
    
    detected_objects = []
    filtered_transactions = []
    is_product_image = False  # Initialiser pour éviter UnboundLocalError
    
    try:
        # Télécharger l'image (timeout réduit 30s → 10s)
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        
        # Créer fichier temporaire
        file_ext = ".jpg"
        if "." in image_url.split("?")[0]:
            file_ext = os.path.splitext(image_url.split("?")[0])[1] or ".jpg"
        
        fd, temp_file_path = tempfile.mkstemp(suffix=file_ext, prefix="hybrid_vision_")
        with os.fdopen(fd, 'wb') as tmp_file:
            tmp_file.write(response.content)
        
        # Traitement vision avec BotliveEngine (SINGLETON)
        from core.botlive_engine import get_botlive_engine
        engine = get_botlive_engine()
        
        # ═══════════════════════════════════════════════════════════════
        # ÉTAPE 1 : BLIP-2 (Détection PRODUIT)
        # ═══════════════════════════════════════════════════════════════
        product_result = engine.detect_product(temp_file_path)
        print(f"[VISION] 🎨 Résultat BLIP-2: {product_result}")
        
        is_product_image = False
        product_name = product_result.get('name', '').lower()
        confidence = product_result.get('confidence', 0)
        
        # Mots-clés indiquant un PAIEMENT (pas un produit)
        payment_keywords = ['text', 'message', 'screenshot', 'phone', 'screen', 'capture', 'payment', 'transaction']
        is_payment_screenshot = any(keyword in product_name for keyword in payment_keywords)
        
        if product_result.get('name') and confidence > 0.5 and not is_payment_screenshot:
            detected_objects.append({
                'label': product_result['name'],
                'confidence': confidence
            })
            is_product_image = True
            print(f"[VISION] ✅ Produit détecté: '{product_result['name']}' (conf: {confidence:.2f})")
            print(f"[VISION] 📦 Type image: PRODUIT")
            print(f"[VISION] ⚡ OPTIMISATION: OCR ignoré (image produit confirmée)")
        else:
            if is_payment_screenshot:
                print(f"[VISION] 💸 BLIP-2 détecte screenshot/texte: '{product_name}'")
                print(f"[VISION] ⚠️ Mots-clés paiement trouvés → REJET comme produit")
            else:
                print(f"[VISION] ⚠️ BLIP-2: Aucun produit détecté (conf: {confidence:.2f})")
            print(f"[VISION] 💰 Type image: PAIEMENT probable → Lancement OCR")
        
        # ═══════════════════════════════════════════════════════════════
        # ÉTAPE 2 : OCR (UNIQUEMENT si pas de produit détecté)
        # ═══════════════════════════════════════════════════════════════
        payment_result = {"amount": "", "currency": "", "reference": "", "raw_text": "", "all_transactions": []}
        
        if not is_product_image:
            # Image PAIEMENT : OCR avec validation stricte obligatoire
            print(f"[VISION] 💰 Lancement OCR avec validation stricte numéro {company_phone}")
            payment_result = engine.verify_payment(temp_file_path, company_phone=company_phone)
            print(f"[VISION] 💰 Résultat OCR: {payment_result}")
        else:
            print(f"[VISION] ⏭️  OCR skippé (produit détecté par BLIP-2)")
        
        # Gérer les erreurs de validation stricte
        if payment_result.get('error'):
            error_code = payment_result['error']
            
            if error_code == "NUMERO_ABSENT":
                error_msg = f"❌ CAPTURE INVALIDE\n\nLe numéro de l'entreprise ({company_phone}) n'apparaît pas dans la capture.\n\n📸 Merci d'envoyer une capture CLAIRE montrant :\n✅ Le montant envoyé\n✅ Le numéro destinataire ({company_phone})\n✅ La date de la transaction"
                filtered_transactions.append({
                    'amount': 0,
                    'currency': 'FCFA',
                    'error_message': error_msg
                })
                print(f"[VISION] 🚫 REJET: {error_code}")
                
            elif error_code == "TRANSACTION_ABSENTE":
                error_msg = f"❌ PAIEMENT NON DÉTECTÉ\n\nLe numéro {company_phone} est visible mais aucune transaction vers ce numéro n'a été trouvée.\n\n📸 Merci d'envoyer la capture du PAIEMENT (pas le solde) montrant le transfert vers {company_phone}"
                filtered_transactions.append({
                    'amount': 0,
                    'currency': 'FCFA',
                    'error_message': error_msg
                })
                print(f"[VISION] 🚫 REJET: {error_code}")
                
            elif error_code == "CAPTURE_INVALIDE":
                error_msg = f"❌ CAPTURE ILLISIBLE\n\nLa capture est floue ou incomplète. Impossible de détecter les informations de paiement.\n\n📸 Merci d'envoyer une NOUVELLE capture NETTE montrant :\n✅ Le montant\n✅ Le numéro {company_phone}\n✅ La confirmation de transfert"
                filtered_transactions.append({
                    'amount': 0,
                    'currency': 'FCFA',
                    'error_message': error_msg
                })
                print(f"[VISION] 🚫 REJET: {error_code}")
            
        elif payment_result.get('amount'):
            try:
                amount_str = payment_result['amount'].replace(',', '.').replace(' ', '')
                amount_float = float(amount_str)
                filtered_transactions.append({
                    'amount': int(amount_float),
                    'currency': payment_result.get('currency', 'FCFA'),
                    'reference': payment_result.get('reference', '')
                })
                print(f"[VISION] ✅ Transaction ajoutée: {int(amount_float)} FCFA")
            except (ValueError, AttributeError) as e:
                print(f"[VISION] ❌ Erreur conversion montant: {e}")
        else:
            print(f"[VISION] ⚠️ Aucun montant détecté dans l'image")
            if payment_result.get('raw_text'):
                print(f"[VISION] Texte brut OCR: {payment_result['raw_text'][:200]}")
        
        # Nettoyage
        try:
            os.unlink(temp_file_path)
        except:
            pass
            
    except Exception as e:
        print(f"❌ [VISION] Erreur traitement image: {e}")
    
    return {
        'detected_objects': detected_objects,
        'filtered_transactions': filtered_transactions
    }

async def _botlive_handle(company_id: str, user_id: str, message: str, images: list, conversation_history: str = "") -> str:
    """
    RAG Botlive conversationnel pour commandes rapides.
    
    Rôle: Assistant qui collecte progressivement (produit, paiement, livraison) via conversation naturelle.
    Outils: YOLO (vision produit), OCR (lecture paiement), historique conversation.
    
    Flux: Toujours conversationnel, que ce soit texte ou image.
    """
    import re  # Import nécessaire pour filtrage transactions

    # ═══════════════════════════════════════════════════════════════
    # PRÉ-TRAITEMENT: DÉTECTER LES URLS D'IMAGES DANS LE TEXTE
    # ═══════════════════════════════════════════════════════════════
    # Cas typique: "voici mon paiement : https://...jpg" sans champ images séparé
    if (not images) and message:
        try:
            url_pattern = r"(https?://\S+)"
            urls = re.findall(url_pattern, message)
            image_urls = []
            for url in urls:
                base = url.split("?")[0].lower()
                if any(base.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]):
                    image_urls.append(url)
            if image_urls:
                print(f"[BOTLIVE][URL] URLs d'image détectées dans message: {len(image_urls)}")
                images.extend(image_urls)
                # Nettoyer le texte pour le LLM (on retire les URLs brutes)
                for u in image_urls:
                    message = message.replace(u, "").strip()
        except Exception as e:
            print(f"[BOTLIVE][URL] Erreur détection URLs image: {e}")

    # ═══════════════════════════════════════════════════════════════
    # DÉDUPLICATION HISTORIQUE (évite pollution tokens)
    # ═══════════════════════════════════════════════════════════════
    conversation_history = deduplicate_conversation_history(conversation_history)
    
    # ═══════════════════════════════════════════════════════════════
    # SYSTÈMES DE CONTEXTE (Notepad Supabase + Extraction + Checkpoint)
    # ═══════════════════════════════════════════════════════════════
    from core.supabase_notepad import get_supabase_notepad
    from FIX_CONTEXT_LOSS_COMPLETE import extract_from_last_exchanges, build_smart_context_summary
    from core.conversation_checkpoint import ConversationCheckpoint
    
    # 1. Récupérer le notepad depuis Supabase (auto-expiration 7 jours)
    notepad_manager = get_supabase_notepad()
    notepad_data = await notepad_manager.get_notepad(user_id, company_id)
    
    print(f"📋 [NOTEPAD SUPABASE] Données chargées: {list(notepad_data.keys())}")
    
    # 🔄 DÉTECTION NOUVELLE CONVERSATION : Reset notepad si "bonjour" + historique court
    first_message_keywords = ['bonjour', 'salut', 'hello', 'bonsoir', 'hey', 'coucou', 'hi']
    is_greeting = any(kw in message.lower() for kw in first_message_keywords)
    # Compter le nombre de messages (lignes commençant par "user:" ou "IA:")
    message_count = conversation_history.count('user:') + conversation_history.count('IA:')
    is_short_history = message_count <= 2
    
    print(f"🔍 [RESET CHECK] Greeting={is_greeting}, Messages={message_count}, Short={is_short_history}")
    
    # NOTE: Le système hybride sera appelé APRÈS l'analyse BLIP-2/OCR
    
    if is_greeting and is_short_history:
        # Vérifier si notepad contient des données (pas vide)
        has_old_data = any(notepad_data.get(key) for key in ['photo_produit', 'delivery_zone', 'phone_number', 'paiement'])
        
        if has_old_data:
            print(f"🔄 [NOTEPAD] Nouvelle conversation détectée ('{message[:30]}...') - Reset notepad")  # ← Utiliser 'message'
            await notepad_manager.clear_notepad(user_id, company_id)
            notepad_data = {}  # Vider pour cette requête
            print(f"✅ [NOTEPAD] Notepad réinitialisé pour nouvelle commande")
            try:
                # Réinitialiser également l'état de commande local
                order_tracker.clear_state(user_id)
            except Exception as e:
                logger.warning(f"[ORDER_STATE_SYNC] Échec clear_state pour {user_id}: {e}")
    
    # 2. Extraire infos depuis l'historique
    print(f"\n{'='*80}")
    print(f"🔍 [CONTEXT DEBUG] EXTRACTION DEPUIS HISTORIQUE")
    print(f"{'='*80}")
    print(f"📝 Historique reçu: {len(conversation_history)} chars")
    print(f"📝 Contenu historique:\n{conversation_history}")
    print(f"{'='*80}\n")
    
    extracted_info = extract_from_last_exchanges(conversation_history)
    if extracted_info:
        print(f"✅ [EXTRACT] Infos extraites: {extracted_info}")
        
        # 🔧 PRÉSERVER DONNÉES BLIP-2 AVANT MERGE
        blip2_data = {
            "blip2_photo_verdict": notepad_data.get("blip2_photo_verdict"),
            "blip2_photo_data": notepad_data.get("blip2_photo_data"),
            "blip2_photo_date": notepad_data.get("blip2_photo_date")
        }
        
        # Mettre à jour le notepad avec les infos extraites
        if extracted_info.get('produit'):
            notepad_data['last_product_mentioned'] = extracted_info['produit']
            print(f"📦 [NOTEPAD] Produit sauvegardé: {extracted_info['produit']}")
        if extracted_info.get('zone'):
            notepad_data['delivery_zone'] = extracted_info['zone']
            notepad_data['delivery_cost'] = extracted_info.get('frais_livraison')
            print(f"🚚 [NOTEPAD] Zone sauvegardée: {extracted_info['zone']} ({extracted_info.get('frais_livraison')} FCFA)")
        if extracted_info.get('telephone'):
            notepad_data['phone_number'] = extracted_info['telephone']
            print(f"📞 [NOTEPAD] Téléphone sauvegardé: {extracted_info['telephone']}")
        
        # 🔧 RESTAURER DONNÉES BLIP-2 APRÈS MERGE
        for key, value in blip2_data.items():
            if value is not None:
                notepad_data[key] = value
                print(f"🤖 [NOTEPAD] BLIP-2 préservé: {key} = {value}")
        
        # 💾 Sauvegarder dans Supabase
        await notepad_manager.update_notepad(user_id, company_id, notepad_data)
        # Synchroniser l'état de commande local avec les nouvelles données du notepad
        _sync_order_state_from_notepad(user_id, notepad_data)
    else:
        print(f"⚠️ [EXTRACT] Aucune info extraite de l'historique")
        # Même si aucune nouvelle info n'est extraite, s'assurer que le tracker
        # reflète bien le notepad actuel (cas récap 4/4, confirmation, etc.)
        _sync_order_state_from_notepad(user_id, notepad_data)
    
    # 3. Construire résumé contexte intelligent
    print(f"\n🧠 [CONTEXT] Construction résumé intelligent...")
    try:
        context_summary = build_smart_context_summary(
            conversation_history=conversation_history,
            user_id=user_id,
            company_id=company_id,
            notepad_data=notepad_data
        )
        print(f"🧠 [CONTEXT] Résumé généré ({len(context_summary)} chars):\n{context_summary}")
    except Exception as ctx_error:
        print(f"⚠️ [CONTEXT] Erreur construction résumé: {ctx_error}")
        context_summary = ""
    print(f"{'='*80}\n")
    
    try:
        # ═══════════════════════════════════════════════════════════════
        # ÉTAPE 0: UTILISER LES PROMPTS HARDCODÉS (PRIORITÉ)
        # ═══════════════════════════════════════════════════════════════
        print(f"[BOTLIVE][PROMPT] 🔧 UTILISATION PROMPTS HARDCODÉS (MODE TEST)")
        
        # Charger dynamiquement le prompt Supabase
        from database.supabase_client import get_botlive_prompt
        botlive_prompt_template = await get_botlive_prompt(company_id)
        print(f"[BOTLIVE][PROMPT] ✅ Prompt Supabase chargé ({len(botlive_prompt_template)} chars)")
        
        # ═══════════════════════════════════════════════════════════════
        # INITIALISATION DES VARIABLES (portée globale fonction)
        # ═══════════════════════════════════════════════════════════════
        detected_objects = []
        detected_type = "unknown"
        confidence = 0.0
        raw_text = ""
        filtered_transactions = []
        image_status_for_llm = ""  # Statut compact pour injection LLM
        image_analysis_type = None  # PRODUIT/PAIEMENT/INVALIDE/None
        
        # ═══════════════════════════════════════════════════════════════
        # TRACKING DEMANDES IGNORÉES (Optimisé - Économie tokens)
        # ═══════════════════════════════════════════════════════════════
        tracking = {'produit_demandes': 0, 'paiement_demandes': 0, 'suggest_alternative': False}
        try:
            lines = conversation_history.split('\n')
            prod_ignored, pay_ignored = 0, 0
            last_prod_req, last_pay_req = False, False
            
            for line in lines:
                ll = line.lower()
                if line.startswith('IA:') or line.startswith('assistant:'):
                    last_prod_req = ('photo' in ll and 'produit' in ll) or 'image du produit' in ll
                    last_pay_req = 'capture' in ll or 'screenshot' in ll or 'preuve de paiement' in ll
                elif line.startswith('user:') or line.startswith('User:'):
                    if last_prod_req and '[image]' not in ll:
                        prod_ignored += 1
                        last_prod_req = False
                    if last_pay_req and '[image]' not in ll:
                        pay_ignored += 1
                        last_pay_req = False
            
            tracking = {
                'produit_demandes': min(prod_ignored, 3),
                'paiement_demandes': min(pay_ignored, 3),
                'suggest_alternative': prod_ignored >= 2
            }
            print(f"[TRACKING] Demandes ignorées: Produit={tracking['produit_demandes']}, Paiement={tracking['paiement_demandes']}")
        except Exception as e:
            print(f"[TRACKING] Erreur: {e}")
        
        # ═══════════════════════════════════════════════════════════════
        # INJECTION ALERTE ÉTAPE IGNORÉE (5 lignes - Solution optimale)
        # ═══════════════════════════════════════════════════════════════
        etape_alert = ""
        for etape, count in tracking.items():
            if count >= 2 and etape.endswith('_demandes'):
                etape_name = etape.replace('_demandes', '').upper()
                etape_alert += f"⚠️ ALERTE: {etape_name} demandé {count}x, ignoré → PASSER À AUTRE ÉTAPE\n"
        
        # ═══════════════════════════════════════════════════════════════
        # ÉTAPE 1: ANALYSE VISION (si image présente)
        # ═══════════════════════════════════════════════════════════════
        if images and len(images) > 0:
            image_url = images[0]
            temp_file_path = None
            
            try:
                # 1. Télécharger l'image URL → fichier temporaire
                import requests
                import tempfile
                import os
                
                print(f"[BOTLIVE] Téléchargement image: {image_url[:100]}...")
                response = requests.get(image_url, timeout=30)
                response.raise_for_status()
                try:
                    final_url = getattr(response, "url", image_url)
                    ctype = response.headers.get("Content-Type", "?")
                    clen = response.headers.get("Content-Length", "?")
                    print(f"[BOTLIVE][FETCH] URL finale: {final_url}")
                    print(f"[BOTLIVE][FETCH] Content-Type: {ctype} | Content-Length: {clen}")
                except Exception as meta_e:
                    print(f"[BOTLIVE][FETCH][META ERROR] {type(meta_e).__name__}: {meta_e}")
                
                # Créer fichier temporaire avec extension appropriée
                file_ext = ".jpg"  # Par défaut
                if "." in image_url.split("?")[0]:  # Avant les paramètres URL
                    file_ext = os.path.splitext(image_url.split("?")[0])[1] or ".jpg"
                
                fd, temp_file_path = tempfile.mkstemp(suffix=file_ext, prefix="botlive_")
                with os.fdopen(fd, 'wb') as tmp_file:
                    tmp_file.write(response.content)
                
                print(f"[BOTLIVE] Image téléchargée: {temp_file_path}")
                # Sauvegarde debug automatique (rotation <= 50 fichiers)
                try:
                    import shutil, glob, time
                    debug_dir = "/tmp/botlive_debug"
                    os.makedirs(debug_dir, exist_ok=True)
                    ts = int(time.time())
                    base = os.path.basename(temp_file_path)
                    debug_copy = os.path.join(debug_dir, f"{ts}_{base}")
                    shutil.copyfile(temp_file_path, debug_copy)
                    print(f"[BOTLIVE][DEBUG] Copie image sauvegardée: {debug_copy}")
                    files = sorted(glob.glob(os.path.join(debug_dir, "*")), key=os.path.getmtime)
                    excess = max(0, len(files) - 50)
                    for i in range(excess):
                        try:
                            os.remove(files[i])
                        except Exception:
                            pass
                except Exception as dbg_e:
                    print(f"[BOTLIVE][DEBUG][SAVE ERROR] {type(dbg_e).__name__}: {dbg_e}")
                
                # Upload automatique sur Supabase Storage pour URL stable
                public_url = None
                try:
                    from database.supabase_client import upload_image_to_supabase
                    # Lire le binaire depuis le temp file
                    with open(temp_file_path, 'rb') as fbin:
                        file_bytes = fbin.read()
                    # Construire un chemin logique botlive/company/date
                    ymd = time.strftime('%Y/%m/%d')
                    base = os.path.basename(temp_file_path)
                    storage_path = f"botlive/{company_id}/{ymd}/{base}"
                    public_url = upload_image_to_supabase(storage_path, file_bytes)
                    print(f"[BOTLIVE][SUPABASE] Image stockée: {public_url}")
                except Exception as up_e:
                    print(f"[BOTLIVE][SUPABASE][UPLOAD ERROR] {type(up_e).__name__}: {up_e}")
                
                # 2. Analyser avec BotliveEngine - PARALLÈLE (Gain 50% temps)
                try:
                    import asyncio
                    from core.botlive_engine import BotliveEngine
                    botlive_engine = BotliveEngine.get_instance()
                    print(f"[BOTLIVE] ✅ Singleton récupéré (pas de rechargement modèles)")
                    
                    # Extraire le numéro entreprise du prompt AVANT l'OCR
                    company_phone_for_ocr = None
                    expected_deposit_int = 2000  # Valeur par défaut
                    
                    if botlive_prompt_template:
                        wave_pattern = r'wave:\s*["\']?([+\d\s\-\.]+)["\']?'
                        phone_match = re.search(wave_pattern, botlive_prompt_template, re.IGNORECASE)
                        if phone_match:
                            raw_phone = phone_match.group(1).strip()
                            company_phone_for_ocr = botlive_engine._normalize_phone(raw_phone)
                            if len(company_phone_for_ocr) == 10:
                                print(f"[PARALLEL] ✅ Numéro WAVE: {company_phone_for_ocr}")
                        
                        if not company_phone_for_ocr:
                            company_phone_for_ocr = "0787360757"
                            print(f"[PARALLEL] ⚠️ Fallback numéro: {company_phone_for_ocr}")
                        
                        # Extraire acompte
                        try:
                            pattern = r"acompte[:\s]+(\d{1,6})"
                            m = re.search(pattern, botlive_prompt_template, re.IGNORECASE)
                            if m:
                                expected_deposit_int = int(m.group(1))
                        except Exception:
                            pass
                    
                    # 🔥 APPELER LES FONCTIONS D'ANALYSE (AVANT de les utiliser)
                    print(f"[BOTLIVE] 🔍 Analyse image avec BLIP-2 pour détection type...")
                    
                    # ÉTAPE 1: Détecter type image avec BLIP-2 D'ABORD
                    product = botlive_engine.detect_product(temp_file_path)
                    product_name = product.get('name', '').lower()
                    print(f"[BOTLIVE] BLIP-2 terminé: {product.get('name', 'N/A')}")
                    
                    # ÉTAPE 2: Déterminer si c'est un PAIEMENT ou un PRODUIT
                    is_payment_image = any(keyword in product_name for keyword in [
                        'wave', 'paiement', 'payment', 'transaction', 'transfert', 
                        'screenshot', 'capture', 'mobile money', 'solde', 'balance'
                    ])
                    
                    # ÉTAPE 3: Analyser selon le type
                    if is_payment_image:
                        print(f"[BOTLIVE] 💳 Image détectée: PAIEMENT → Analyse OCR...")
                        payment = botlive_engine.verify_payment(
                            image_path=temp_file_path,
                            company_phone=company_phone_for_ocr,
                            required_amount=expected_deposit_int
                        )
                        print(f"[BOTLIVE] OCR terminé: {payment.get('amount', 'N/A')} FCFA")
                    else:
                        print(f"[BOTLIVE] 📦 Image détectée: PRODUIT → Pas d'OCR paiement")
                        # 🔥 NOUVEAU: Sauvegarder photo produit dans le Notepad
                        try:
                            from datetime import datetime
                            notepad = await notepad_manager.get_notepad(user_id, company_id)
                            notepad['photo_produit'] = 'reçue'
                            notepad['photo_produit_description'] = product_name

                            # URL d'image produit VALIDÉE par BLIP
                            image_url_for_notepad = public_url or image_url
                            if image_url_for_notepad:
                                notepad['photo_produit_url'] = image_url_for_notepad

                            notepad['last_updated'] = datetime.now().isoformat()
                            
                            # Sauvegarder dans Supabase
                            await notepad_manager.update_notepad(user_id, company_id, notepad)
                            print(f"💾 [NOTEPAD] Photo produit sauvegardée: {product_name} | URL={notepad.get('photo_produit_url')}")
                            
                            # 🔥 RECONSTRUIRE LE CONTEXTE après sauvegarde
                            context_summary = build_smart_context_summary(
                                conversation_history=conversation_history,
                                user_id=user_id,
                                company_id=company_id,
                                notepad_data=notepad
                            )
                            print(f"🔄 [CONTEXT] Contexte mis à jour après photo produit ({len(context_summary)} chars)")
                        except Exception as notepad_err:
                            print(f"⚠️ [NOTEPAD] Erreur sauvegarde photo: {notepad_err}")
                        
                        payment = {
                            'valid': False,
                            'amount': 0,
                            'all_transactions': [],
                            'message': 'Image produit (pas de paiement détecté)'
                        }
                    
                    # Préparer les transactions pour validation cumulative
                    all_transactions_ocr = payment.get('all_transactions', [])
                    
                    # Convertir format OCR vers format attendu par validate_payment_cumulative
                    current_transactions = []
                    if all_transactions_ocr:
                        for tx in all_transactions_ocr:
                            # Convertir amount en int (peut être string depuis OCR)
                            amount_raw = tx.get('amount', 0)
                            try:
                                amount_int = int(amount_raw) if amount_raw else 0
                            except (ValueError, TypeError):
                                print(f"[BOTLIVE][PAYMENT_VALIDATOR] ⚠️ Montant invalide ignoré: {amount_raw}")
                                continue
                            
                            current_transactions.append({
                                'amount': amount_int,
                                'currency': 'FCFA',
                                'phone': tx.get('phone', ''),
                                'date': tx.get('date', '')
                            })
                    
                    # Appeler le validateur cumulatif
                    from core.payment_validator import validate_payment_cumulative, format_payment_for_prompt
                    
                    payment_validation_result = validate_payment_cumulative(
                        current_transactions=current_transactions,
                        conversation_history=conversation_history,
                        required_amount=expected_deposit_int
                    )
                    
                    print(f"[BOTLIVE][PAYMENT_VALIDATOR] Résultat validation:")
                    print(f"   Valid: {payment_validation_result['valid']}")
                    print(f"   Total reçu: {payment_validation_result['total_received']} FCFA")
                    print(f"   Paiements: {payment_validation_result['payments_history']}")
                    print(f"   Message: {payment_validation_result['message']}")
                    
                    # 🔥 NOUVEAU: Sauvegarder paiement validé dans le Notepad
                    if payment_validation_result['valid']:
                        try:
                            from datetime import datetime
                            notepad = await notepad_manager.get_notepad(user_id, company_id)
                            # ✅ FORMAT UNIFIÉ : Objet avec montant + statut
                            notepad['paiement'] = {
                                'montant': payment_validation_result['total_received'],
                                'validé': True,
                                'date': datetime.now().isoformat()
                            }
                            notepad['last_updated'] = datetime.now().isoformat()
                            
                            # Sauvegarder dans Supabase
                            await notepad_manager.update_notepad(user_id, company_id, notepad)
                            print(f"💾 [NOTEPAD] Paiement sauvegardé: {payment_validation_result['total_received']} FCFA")
                            print(f"🔍 [DEBUG] Notepad après sauvegarde paiement: {notepad.get('paiement')}")
                            
                            # 🔥 RECONSTRUIRE LE CONTEXTE après sauvegarde
                            context_summary = build_smart_context_summary(
                                conversation_history=conversation_history,
                                user_id=user_id,
                                company_id=company_id,
                                notepad_data=notepad
                            )
                            print(f"🔄 [CONTEXT] Contexte mis à jour après paiement ({len(context_summary)} chars)")
                            print(f"📄 [CONTEXT] Contenu:\n{context_summary}")
                        except Exception as notepad_err:
                            print(f"⚠️ [NOTEPAD] Erreur sauvegarde paiement: {notepad_err}")
                    
                    # Formater pour injection dans le prompt
                    if payment_validation_result['valid']:
                        payment_validation_text = f"\n💳 VALIDATION PAIEMENT:\n✅ VALIDÉ: {payment_validation_result['message']}\n"
                    else:
                        payment_validation_text = f"\n💳 VALIDATION PAIEMENT:\n❌ INSUFFISANT: {payment_validation_result['message']}\n"
                    
                    # Ajouter les transactions filtrées (pour compatibilité)
                    if current_transactions:
                        filtered_transactions.extend(current_transactions)

                    # "Yeux" uniquement: collecter ce que voient YOLO/EasyOCR, laisser l'LLM décider
                    import re
                    prod_label = (product.get("name") or "").strip()
                    prod_conf = float(product.get("confidence") or 0.0)
                    raw_text = (payment.get("raw_text") or "").strip()

                    # Extraire des montants candidats (ex: 5 000, 5000, 5.000, 5,000 avec devise optionnelle)
                    # FILTRAGE: Ignorer montants < 1000 FCFA (bruit OCR sur emballages)
                    amt_pattern = r"(\d{1,3}(?:[\s.,]\d{3})*(?:[\s.,]\d{2})?)\s*(fcfa|xof|cfa|€|eur|$|usd)?"
                    candidate_amounts = []
                    if raw_text:
                        for m in re.finditer(amt_pattern, raw_text, flags=re.IGNORECASE):
                            val = (m.group(1) or "").strip()
                            cur = (m.group(2) or "").upper().replace('XOF','FCFA').replace('EUR','€').replace('USD','$')
                            # Convertir en nombre pour filtrage
                            try:
                                amount_num = int(val.replace(" ", "").replace(",", "").replace(".", ""))
                                if amount_num >= 1000:  # Minimum 1000 FCFA
                                    candidate_amounts.append((val, cur))
                            except:
                                pass  # Ignorer les montants invalides

                    # Construire une liste d'objets détectés lisibles pour le prompt
                    detected_objects = []
                    if prod_label and prod_label.lower() != "inconnu" and prod_conf > 0:
                        detected_objects.append(f"objet:{prod_label}~{prod_conf:.2f}")
                    if candidate_amounts:
                        # Limiter pour éviter prompts trop longs
                        for val, cur in candidate_amounts[:5]:
                            detected_objects.append(f"montant:{val} {cur}".strip())
                    # OCR brut supprimé (bruit inutile pour le LLM, seuls les montants filtrés comptent)

                    # Ne pas forcer un type ici: laisser l'LLM décider
                    detected_type = "unknown"
                    confidence = 0.0

                    analysis_result = {
                        "type": detected_type,
                        "confidence": confidence,
                        "objects": detected_objects,
                        "raw_text": raw_text,
                        "candidate_amounts": candidate_amounts,
                        "product": {"label": prod_label, "confidence": prod_conf},
                    }
                    print(f"[BOTLIVE] Analyse (brute): type={detected_type}, prod={prod_label}:{prod_conf:.2f}, ocr_len={len(raw_text)} amts={len(candidate_amounts)}")
                    try:
                        print("[BOTLIVE][VISION RAW] raw_text=\n" + (raw_text or ""))
                        print(f"[BOTLIVE][VISION RAW] candidate_amounts={candidate_amounts}")
                        print(f"[BOTLIVE][VISION RAW] detected_objects={detected_objects}")
                    except Exception as log_e:
                        print(f"[BOTLIVE][VISION RAW][LOG ERROR] {type(log_e).__name__}: {log_e}")

                    detected_type = analysis_result.get("type", "unknown")
                    confidence = float(analysis_result.get("confidence", 0) or 0)
                    detected_objects = analysis_result.get("objects", []) or []
                    # Heuristique qualité image: si aucun objet ni texte OCR détecté
                    # on considère la photo comme inexploitable et on guide l'utilisateur
                    if (not detected_objects) and (not raw_text):
                        return """<response>
❌ Photo non exploitable. Merci de :
1. 📸 Recadrer le produit / le reçu de paiement
2. 💡 Améliorer la luminosité / éviter les reflets
3. 🔄 Envoyer une nouvelle photo
</response>"""
                    
                    # GÉNÉRATION STATUT COMPACT POUR LLM (Économie 60% tokens)
                    try:
                        # Déterminer le type d'analyse
                        if prod_label and prod_label.lower() != "inconnu" and prod_conf > 0.5:
                            image_analysis_type = 'PRODUIT'
                            image_status_for_llm = f"📦IMG:OK[{prod_label}|{prod_conf*100:.0f}%] 💳PAY:ATTENTE"
                            print(f"[STATUS] Type: PRODUIT | Statut: {image_status_for_llm}")
                        
                        elif filtered_transactions and len(filtered_transactions) > 0:
                            image_analysis_type = 'PAIEMENT'
                            tx_count = len(filtered_transactions)
                            # Déterminer statut paiement
                            if any(tx.get('error_message') for tx in filtered_transactions):
                                status = 'INVALIDE'
                            elif any(tx.get('amount', 0) >= 2000 for tx in filtered_transactions):
                                status = 'VALIDÉ'
                            else:
                                status = 'INSUFFISANT'
                            image_status_for_llm = f"📦IMG:ATTENTE 💳PAY:{status}[{tx_count}tx]"
                            print(f"[STATUS] Type: PAIEMENT | Statut: {image_status_for_llm}")
                        
                        elif (not detected_objects) and (not raw_text):
                            image_analysis_type = 'INVALIDE'
                            image_status_for_llm = "⚠️IMG:ILLISIBLE→redemander_image_nette"
                            print(f"[STATUS] Type: INVALIDE | Statut: {image_status_for_llm}")
                        
                        else:
                            # Aucune image ou analyse non concluante
                            image_analysis_type = None
                            image_status_for_llm = ""
                            print(f"[STATUS] Type: NONE | Pas de statut généré")
                        
                    except Exception as status_error:
                        print(f"[STATUS] Erreur génération statut: {status_error}")
                        image_status_for_llm = ""
                    
                    # Analyse vision terminée - le traitement LLM se fait à la fin de la fonction
                    
                except ImportError:
                    print("[BOTLIVE] BotliveEngine non disponible, fallback vers UniversalRAGEngine")
                    # Fallback vers UniversalRAGEngine._analyze_live_image
                    from core.universal_rag_engine import UniversalRAGEngine
                    engine = UniversalRAGEngine()
                    analysis = engine._analyze_live_image(temp_file_path)
                    
                    if isinstance(analysis, dict):
                        detected_type = analysis.get("type") or analysis.get("detected_type") or "unknown"
                        detected_objects = analysis.get("objects") or []
                        confidence = float(analysis.get("confidence", 0) or 0)

                        try:
                            from database.supabase_client import get_botlive_prompt
                            botlive_prompt_template = await get_botlive_prompt(company_id)
                        except Exception:
                            botlive_prompt_template = (
                                "Vous êtes un assistant de vente en direct. Analysez les images et guidez les clients à travers les étapes de commande. "
                                "Soyez concis et professionnel. Objets détectés: {detected_objects}. Type: {detected_type}. Confiance: {confidence}."
                            )

                        try:
                            from core.enhanced_prompt_engine import EnhancedPromptEngine
                            prompt_engine = EnhancedPromptEngine()
                            formatted_prompt = prompt_engine.format_prompt(
                                template=botlive_prompt_template,
                                variables={
                                    "detected_objects": ", ".join(detected_objects) if detected_objects else "aucun",
                                    "detected_type": detected_type,
                                    "confidence": f"{confidence*100:.1f}%",
                                    "company_id": company_id,
                                    "user_id": user_id,
                                }
                            )
                        except Exception:
                            formatted_prompt = botlive_prompt_template.format(
                                detected_objects=", ".join(detected_objects) if detected_objects else "aucun",
                                detected_type=detected_type,
                                confidence=f"{confidence*100:.1f}%",
                                company_id=company_id,
                                user_id=user_id,
                            )

                        try:
                            from core.llm_client import complete as generate_response
                            return await generate_response(
                                formatted_prompt,
                                model_name="llama-3.3-70b-versatile",
                                max_tokens=180
                            )
                        except Exception:
                            if detected_type == "product":
                                return "Produit détecté. Envoyez maintenant la preuve de paiement."
                            if detected_type == "payment":
                                return "Preuve de paiement détectée. Envoyez maintenant la photo du produit."
                            return "Image analysée. Envoyez une photo claire du produit ou de la preuve de paiement."
                
            except requests.RequestException as e:
                print(f"[BOTLIVE] Erreur téléchargement: {e}")
                return "Impossible de télécharger l'image. Réessayez avec une autre image."
            except Exception as e:
                print(f"[BOTLIVE] Erreur analyse: {e}")
                return "Erreur lors de l'analyse de l'image. Envoyez une photo claire du produit ou de la preuve de paiement."
            finally:
                # Nettoyer ou conserver le fichier temporaire selon variable d'env
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        keep = os.getenv("BOTLIVE_KEEP_TEMP", "0") == "1"
                        if keep:
                            print(f"[BOTLIVE] Temp conservé (BOTLIVE_KEEP_TEMP=1): {temp_file_path}")
                        else:
                            os.remove(temp_file_path)
                            print(f"[BOTLIVE] Fichier temporaire supprimé: {temp_file_path}")
                    except Exception as rm_e:
                        print(f"[BOTLIVE][TEMP][CLEAN ERROR] {type(rm_e).__name__}: {rm_e}")
        
        # ═══════════════════════════════════════════════════════════════
        # ÉTAPE 2: VALIDATION PAIEMENT (transactions déjà filtrées par OCR)
        # ═══════════════════════════════════════════════════════════════
        # Les transactions sont déjà dans filtered_transactions (issues du moteur OCR)
        print(f"[BOTLIVE][FILTER] Transactions déjà filtrées par OCR: {len(filtered_transactions)}")
        
        # Vérifier si payment_validation_text existe (créé lors de l'analyse image)
        if 'payment_validation_text' not in locals():
            payment_validation_text = ""
        
        # ═══════════════════════════════════════════════════════════════
        # ÉTAPE 3: APPEL LLM CONVERSATIONNEL (toujours, avec ou sans image)
        # ═══════════════════════════════════════════════════════════════
        # Extraction acompte depuis le prompt
        expected_deposit = 2000  # ← INT pour comparaisons
        expected_deposit_str = "2000 FCFA"  # ← STRING pour affichage
        try:
            pattern = r"acompte\s+(\d{1,5})\s*(fcfa|f\s*cfa|xof|cfa)\s*minimum"
            m = re.search(pattern, botlive_prompt_template, re.IGNORECASE)
            if m:
                expected_deposit = int(m.group(1))  # ← Convertir en INT
                expected_deposit_str = f"{m.group(1)} {m.group(2).upper()}"
        except:
            pass
        
        # Préparer les variables pour le prompt
        question_text = message or ""
        history_text = conversation_history
        context_text = ""
        
        # ═══════════════════════════════════════════════════════════════
        # SYSTÈME DELIVERY: Détection automatique + injection contexte
        # ═══════════════════════════════════════════════════════════════
        delivery_context = ""
        try:
            from core.delivery_zone_extractor import extract_delivery_zone_and_cost, format_delivery_info
            
            # Détecter si la question concerne la livraison
            zone_info = extract_delivery_zone_and_cost(question_text)
            
            if zone_info:
                # ✅ PATCH #1 : Vérifier si expédition (ville hors Abidjan)
                if zone_info.get('category') == 'expedition' and zone_info.get('error'):
                    # Expédition → Utiliser le message complet
                    delivery_context = f"🚚 EXPÉDITION HORS ABIDJAN:\n{zone_info['error']}"
                    print(f"🚚 [DELIVERY] Expédition détectée: {zone_info['name']} (à partir de {zone_info['cost']} FCFA)")
                else:
                    # Livraison Abidjan → Format normal
                    delivery_context = format_delivery_info(zone_info)
                    print(f"🚚 [DELIVERY] Zone détectée: {zone_info['name']} = {zone_info['cost']} FCFA")
                
                print(f"📋 [DELIVERY] Contexte injecté dans le prompt ({len(delivery_context)} chars)")
        except Exception as e:
            print(f"⚠️ [DELIVERY] Erreur extraction: {e}")
        
        # ═══════════════════════════════════════════════════════════════
        # LOGS DEBUG : Ce qui sera envoyé au LLM
        # ═══════════════════════════════════════════════════════════════
        print("\n" + "="*80)
        print("🔍 [BOTLIVE][AVANT LLM] DONNÉES VISION DISPONIBLES:")
        print(f"   detected_objects = {detected_objects}")
        print(f"   detected_type = {detected_type}")
        print(f"   confidence = {confidence}")
        print(f"   raw_text = {raw_text[:100] if raw_text else '[vide]'}...")
        print(f"   filtered_transactions = {filtered_transactions}")
        print(f"   expected_deposit = {expected_deposit} ({expected_deposit_str})")
        print("="*80 + "\n")
        
        # ═══════════════════════════════════════════════════════════════
        # SYSTÈME: UTILISER UNIQUEMENT LE PROMPT SUPABASE
        # ═══════════════════════════════════════════════════════════════
        try:
            # NE PLUS UTILISER update_botlive_prompt.get_prompt() - UTILISER SUPABASE UNIQUEMENT
            print(f"🔧 [PROMPT MODE] SUPABASE DIRECT")
            
            # Préparer les variables pour formatage
            # NE PLUS INJECTER DE DONNÉES VISION POUR LA VALIDATION PAIEMENT
            detected_objects_str = ""  # Vision ignorée pour paiement
            
            # INJECTER UNIQUEMENT LE VERDICT OCR
            if payment_validation_text:
                filtered_transactions_str = payment_validation_text
            else:
                filtered_transactions_str = "[AUCUNE TRANSACTION VALIDE]"
            
            # DEBUG: Vérifier les transactions avant formatage
            print(f"🔍 [DEBUG] filtered_transactions = {filtered_transactions}")
            print(f"🔍 [DEBUG] filtered_transactions_str = {filtered_transactions_str}")
            
            # Formater le prompt Supabase directement avec gestion d'erreur
            try:
                # ═══════════════════════════════════════════════════════════════
                # 🎯 OPTIMISATION TOKENS : Construction contexte UNIQUE
                # ═══════════════════════════════════════════════════════════════
                question_with_context = question_text or ""
                
                # Ajouter statut images compact (économie tokens)
                if image_status_for_llm:
                    question_with_context = f"📸 {image_status_for_llm}\n\n{question_with_context}"
                
                # ✅ PATCH #3: VALIDATION STRICTE COMMANDE (BLIP-2 + OCR)
                # ═══════════════════════════════════════════════════════════════
                validation_warnings = []
                
                # 1. Vérifier photo produit (BLIP-2 obligatoire)
                photo_produit_valide = False
                if notepad_data.get("photo_produit"):
                    # Photo déjà validée par BLIP-2
                    photo_produit_valide = True
                elif detected_objects and len(detected_objects) > 0:
                    # Extraire la vraie confiance de detected_objects
                    real_confidence = 0.0
                    for obj in detected_objects:
                        if isinstance(obj, str) and '~' in obj:
                            # Format: "objet:description~0.90"
                            try:
                                real_confidence = float(obj.split('~')[-1])
                                break
                            except:
                                pass
                        elif isinstance(obj, dict) and 'confidence' in obj:
                            real_confidence = obj['confidence']
                            break
                    
                    if real_confidence > 0.5:
                        # Image actuelle détectée par BLIP-2 avec confiance > 50%
                        photo_produit_valide = True
                        notepad_data["photo_produit"] = f"Détecté: {', '.join(detected_objects)} (conf: {real_confidence:.2f})"
                        print(f"✅ [VALIDATION] Photo produit validée avec confiance {real_confidence:.2f}")
                    else:
                        validation_warnings.append(f"📸 Photo produit confiance trop faible ({real_confidence:.2f} < 0.5)")
                else:
                    validation_warnings.append("📸 Photo produit manquante ou floue (BLIP-2 non validé)")
                
                # 2. Vérifier paiement (OCR obligatoire)
                paiement_valide = False
                if notepad_data.get("paiement") and notepad_data["paiement"].get("montant"):
                    # Paiement déjà validé
                    paiement_valide = True
                elif filtered_transactions and len(filtered_transactions) > 0:
                    # Transaction OCR détectée
                    montant = filtered_transactions[0].get("amount", 0)
                    if montant >= expected_deposit:  # ← Comparaison INT vs INT
                        paiement_valide = True
                        notepad_data["paiement"] = {"montant": montant, "validé": True}
                    else:
                        validation_warnings.append(f"💳 Acompte insuffisant: {montant} FCFA < {expected_deposit_str} (OCR détecté)")
                else:
                    validation_warnings.append(f"💳 Preuve paiement manquante (OCR non validé, acompte min: {expected_deposit_str})")
                
                # 3. Vérifier zone livraison
                if not notepad_data.get("delivery_zone"):
                    validation_warnings.append("📍 Zone livraison manquante")
                
                # 4. Vérifier téléphone (avec validation stricte)
                phone_valide = False
                if notepad_data.get("phone_number"):
                    from FIX_CONTEXT_LOSS_COMPLETE import validate_phone_ci
                    phone_validation = validate_phone_ci(notepad_data["phone_number"])
                    if phone_validation["valid"]:
                        phone_valide = True
                        # Normaliser le téléphone
                        notepad_data["phone_number"] = phone_validation["normalized"]
                    else:
                        validation_warnings.append(f"📞 Téléphone invalide: {phone_validation['error']}")
                else:
                    validation_warnings.append("📞 Numéro téléphone manquant")
                
                # ═══════════════════════════════════════════════════════════════
                # 🎯 OPTIMISATION : Construire contexte COMPACT (validation déjà dans context_summary)
                # ═══════════════════════════════════════════════════════════════
                
                # Logs validation (pour debug uniquement)
                if validation_warnings:
                    print(f"\n🚨 [VALIDATION] Éléments manquants détectés:")
                    for w in validation_warnings:
                        print(f"   ❌ {w}")
                else:
                    print(f"\n✅ [VALIDATION] Commande complète et validée !")
                
                # Construire contexte UNIQUE (sans duplication)
                final_context_parts = []
                
                # 1. Contexte livraison (si expédition)
                if delivery_context:
                    final_context_parts.append(delivery_context)
                
                # 2. Contexte mémoire (contient déjà les erreurs de validation)
                if context_summary:
                    final_context_parts.append(context_summary)
                
                # 3. Assembler contexte final
                if final_context_parts:
                    question_with_context = "\n\n".join(final_context_parts) + "\n\n" + question_with_context
                
                # Suggestions canoniques basées embeddings (mode écoute → canoniques/paires)
                try:
                    from core.canonical_retriever import get_canonical_suggestions, format_suggestions_for_prompt
                    canonical_suggestions = await get_canonical_suggestions(
                        question_text or "",
                        company_id=company_id,
                        top_k=2,
                    )
                    suggestions_block = format_suggestions_for_prompt(canonical_suggestions)
                    if suggestions_block:
                        question_with_context = question_with_context + "\n\n" + suggestions_block
                except Exception as e:
                    print(f"[BOTLIVE][SUGGESTIONS] Erreur suggestions canoniques: {e}")
                
                # IMPORTANT: Checklist sera injectée APRÈS le système hybride
                # Pour l'instant, on met un placeholder
                format_vars = {
                    "question": question_with_context,
                    "conversation_history": history_text or "",
                    "detected_objects": detected_objects_str,
                    "filtered_transactions": filtered_transactions_str,
                    "expected_deposit": expected_deposit_str,  # ← Utiliser la version STRING
                    "checklist": "[CHECKLIST SERA INJECTÉE PAR SYSTÈME HYBRIDE]"  # Placeholder
                }
                if "{context_text}" in botlive_prompt_template:
                    format_vars["context_text"] = ""
                formatted_prompt = botlive_prompt_template.format(**format_vars)
            except KeyError as ke:
                print(f"⚠️ [PROMPT] Variable manquante dans template: {ke}")
                # Fallback: remplacer manuellement
                formatted_prompt = botlive_prompt_template
                formatted_prompt = formatted_prompt.replace("{question}", question_text or "")
                formatted_prompt = formatted_prompt.replace("{conversation_history}", history_text or "")
                formatted_prompt = formatted_prompt.replace("{detected_objects}", detected_objects_str)
                formatted_prompt = formatted_prompt.replace("{filtered_transactions}", filtered_transactions_str)
                formatted_prompt = formatted_prompt.replace("{expected_deposit}", expected_deposit_str)  # ← Utiliser STRING
                formatted_prompt = formatted_prompt.replace("{checklist}", "[CHECKLIST SERA INJECTÉE PAR SYSTÈME HYBRIDE]")
            
            print(f"📊 [SUPABASE PROMPT] Formaté: {len(formatted_prompt)} chars")
            
        except ImportError as e:
            # Fallback si get_prompt() pas disponible
            print(f"⚠️ [PROMPT] Fallback mode statique (import error: {e})")
            safe_vars = {
                "detected_objects": ", ".join(detected_objects) if detected_objects else "[AUCUN OBJET DÉTECTÉ]",
                "detected_type": detected_type or "unknown",
                "confidence": f"{(confidence or 0)*100:.1f}%",
                "company_id": company_id,
                "user_id": user_id,
                "raw_text": raw_text or "[TEXTE NON EXTRAIT]",
                "filtered_transactions": filtered_transactions_str or "[AUCUNE TRANSACTION VALIDE]",
                "context": context_text or "",
                "history": history_text or "",
                "question": question_text or "",
                "conversation_history": history_text or "",
            }
            formatted_prompt = botlive_prompt_template.format(**safe_vars)
        except Exception as e:
            # Autre erreur - Fallback avec remplacement manuel
            print(f"[BOTLIVE][ERROR] Formatage prompt failed: {e}")
            formatted_prompt = botlive_prompt_template
            # Remplacer manuellement toutes les variables
            formatted_prompt = formatted_prompt.replace("{question}", question_text or "")
            formatted_prompt = formatted_prompt.replace("{conversation_history}", history_text or "")
            formatted_prompt = formatted_prompt.replace("{detected_objects}", detected_objects_str or "")
            formatted_prompt = formatted_prompt.replace("{filtered_transactions}", filtered_transactions_str or "[AUCUNE TRANSACTION VALIDE]")
            formatted_prompt = formatted_prompt.replace("{expected_deposit}", expected_deposit_str or "2000 FCFA")
        
        # ═══════════════════════════════════════════════════════════════
        # LOG : Vérifier que les variables sont bien dans le prompt
        # ═══════════════════════════════════════════════════════════════
        print("\n🔍 [BOTLIVE][PROMPT FORMATÉ] Vérification injection variables:")
        if "{detected_objects}" in formatted_prompt:
            print("   ❌ ERREUR: {detected_objects} NON REMPLACÉ dans le prompt !")
        else:
            print("   ✅ {detected_objects} remplacé")
        
        if "{filtered_transactions}" in formatted_prompt:
            print("   ❌ ERREUR: {filtered_transactions} NON REMPLACÉ dans le prompt !")
        else:
            print("   ✅ {filtered_transactions} remplacé")
        
        # Afficher un extrait du prompt formaté
        print(f"\n📄 [PROMPT EXTRAIT] (500 premiers chars):\n{formatted_prompt[:500]}...\n")
        
        # 🔍 AFFICHER LE PROMPT COMPLET POUR DEBUG
        print(f"\n{'='*80}")
        print(f"🔍 [DEBUG] PROMPT COMPLET ENVOYÉ AU LLM")
        print(f"{'='*80}")
        print(f"Longueur totale: {len(formatted_prompt)} chars")
        print(f"\n--- DÉBUT PROMPT ---\n")
        print(formatted_prompt)
        print(f"\n--- FIN PROMPT ---\n")
        print(f"{'='*80}\n")
        
        # ═══════════════════════════════════════════════════════════════
        # FORCER LE FORMAT DE RÉPONSE
        # ═══════════════════════════════════════════════════════════════
        formatted_prompt += """

⚠️⚠️⚠️ FORMAT DE RÉPONSE OBLIGATOIRE - NE PAS IGNORER ⚠️⚠️⚠️

Tu DOIS ABSOLUMENT répondre en utilisant EXACTEMENT ce format:

<thinking>
[Ton raisonnement détaillé ici]
</thinking>

<response>
[Ta réponse au client ici - 2-3 lignes max]
</response>

IMPORTANT: Si tu ne respectes pas ce format, ta réponse sera rejetée !
Commence MAINTENANT par <thinking> puis <response>.
"""
        
        # ═══════════════════════════════════════════════════════════════
        # SYSTÈME HYBRIDE PYTHON ↔ LLM (APRÈS ANALYSE VISION)
        # ═══════════════════════════════════════════════════════════════
        from core.loop_botlive_engine import get_loop_engine
        from core.persistent_collector import get_collector
        
        # Vérifier si système hybride activé
        loop_engine = get_loop_engine()
        import os as _os
        print(f"[HYBRID][DEBUG] USE_HYBRID_BOTLIVE={_os.getenv('USE_HYBRID_BOTLIVE')!r} | loop_enabled={loop_engine.is_enabled()}")
        if loop_engine.is_enabled():
            print(f"🔄 [HYBRID] Système hybride ACTIVÉ - Traitement avec vision...")
            
            try:
                # Préparer résultats vision pour le système hybride
                vision_result = None
                if detected_objects:
                    # ✅ EXTRAIRE LA VRAIE CONFIANCE DE detected_objects
                    real_confidence = 0.0
                    clean_descriptions = []
                    
                    for obj in detected_objects:
                        if isinstance(obj, str) and '~' in obj:
                            # Format: "objet:description~0.90"
                            try:
                                parts = obj.split('~')
                                real_confidence = float(parts[-1])
                                clean_descriptions.append(parts[0].replace('objet:', ''))
                            except:
                                clean_descriptions.append(obj)
                        elif isinstance(obj, dict):
                            if 'confidence' in obj:
                                real_confidence = obj['confidence']
                            clean_descriptions.append(obj.get('label', str(obj)))
                        else:
                            clean_descriptions.append(str(obj))
                    
                    vision_result = {
                        "description": ", ".join(clean_descriptions),
                        "confidence": real_confidence,  # ✅ VRAIE CONFIANCE
                        "type": detected_type,
                        "error": None
                    }
                    print(f"✅ [HYBRID] Vision result avec vraie confiance: {real_confidence:.2f}")
                
                ocr_result = None
                if filtered_transactions:
                    # IMPORTANT: Prendre la PREMIÈRE transaction (la plus récente)
                    # Ne PAS faire la somme car OCR retourne déjà les transactions triées
                    first_transaction = filtered_transactions[0]
                    ocr_result = {
                        "valid": True,
                        "amount": first_transaction.get('amount', 0),
                        "transactions": filtered_transactions
                    }
                
                # Collecter et persister les données
                collector = get_collector()
                collection_result = collector.collect_and_persist(
                    notepad=notepad_data,
                    vision_result=vision_result,
                    ocr_result=ocr_result,
                    message=message
                )
                
                # Si données mises à jour, sauvegarder
                if collection_result["updated"]:
                    await notepad_manager.update_notepad(user_id, company_id, collection_result["notepad"])
                    notepad_data = collection_result["notepad"]
                    print(f"💾 [HYBRID] Données persistées: {collection_result['updated']}")
                
                # Générer checklist enrichie AVANT d'appeler loop_engine
                # (pour l'injecter dans le prompt LLM principal)
                enriched_checklist = collection_result.get("checklist", "❌ Checklist non disponible")
                
                # Traiter avec le moteur en boucle
                def llm_fallback(prompt):
                    """LLM fallback - sera appelé si nécessaire"""
                    # On continuera avec le LLM normal plus bas
                    return "Continuez avec LLM normal"
                
                hybrid_result = loop_engine.process_message(
                    message=message,
                    notepad=collection_result["notepad"],
                    vision_result=vision_result,
                    ocr_result=ocr_result,
                    llm_function=llm_fallback
                )
                
                # 🔧 VÉRIFIER SI RÉCONCILIATEUR A MODIFIÉ NOTEPAD
                if hasattr(loop_engine, 'notepad_updated_by_reconciler') and loop_engine.notepad_updated_by_reconciler:
                    print(f"💾 [HYBRID] Réconciliateur a modifié notepad → Sauvegarde forcée")
                    await notepad_manager.update_notepad(user_id, company_id, collection_result["notepad"])
                    loop_engine.notepad_updated_by_reconciler = False  # Reset flag
                
                print(f"✅ [HYBRID] Réponse générée: {hybrid_result['response'][:100]}...")
                print(f"📊 [HYBRID] Source: {hybrid_result['source']}")
                print(f"📋 [HYBRID] Checklist: {hybrid_result['checklist']}")
                
                # Si Python a répondu automatiquement, retourner directement
                if hybrid_result["source"] in ["python_auto", "python_final_recap"]:
                    print(f"🎯 [HYBRID] Python automatique - Réponse directe")
                    return hybrid_result["response"]
                
                # Sinon, continuer avec LLM (fallback)
                print(f"🤖 [HYBRID] LLM guide - Continuer traitement normal")
                
                # INJECTER CHECKLIST ENRICHIE dans le prompt
                enriched_checklist = hybrid_result.get('checklist', enriched_checklist)
                formatted_prompt = formatted_prompt.replace(
                    "[CHECKLIST SERA INJECTÉE PAR SYSTÈME HYBRIDE]",
                    enriched_checklist
                )
                print(f"✅ [HYBRID] Checklist enrichie injectée dans prompt LLM")
                
            except Exception as hybrid_error:
                print(f"❌ [HYBRID] Erreur système hybride: {hybrid_error}")
                print(f"🔄 [HYBRID] Fallback vers système classique")
                # En cas d'erreur, utiliser checklist de base
                enriched_checklist = "❌ Erreur génération checklist"
                formatted_prompt = formatted_prompt.replace(
                    "[CHECKLIST SERA INJECTÉE PAR SYSTÈME HYBRIDE]",
                    enriched_checklist
                )
        else:
            print(f"⚠️ [HYBRID] Système hybride DÉSACTIVÉ - Mode classique")
            # Mode classique : checklist basique
            enriched_checklist = "❌ Système hybride désactivé"
            formatted_prompt = formatted_prompt.replace(
                "[CHECKLIST SERA INJECTÉE PAR SYSTÈME HYBRIDE]",
                enriched_checklist
            )

        # Appel LLM (fallback ou système classique)
        llm_text = None
        token_usage = {}
        client_response = None

        try:
            import re  # Import nécessaire pour l'extraction
            import os  # Import nécessaire pour getenv
            from core.llm_health_check import complete as generate_response
            # Utiliser le modèle Groq défini dans l'env, sinon défaut 70B versatile
            groq_model = "llama-3.3-70b-versatile"  # Forcé, plus jamais d'auto ou 8B

            # Par défaut: utiliser le prompt complet historique
            prompt_to_use = formatted_prompt

            # Indique si un router avancé a déjà construit un prompt spécifique
            routing_used = False
        except Exception as llm_prep_error:
            # Fermer proprement le bloc try de préparation LLM
            logger.error("[LLM_SETUP] Erreur préparation prompt: %s", llm_prep_error)
            # Valeurs par défaut si la préparation échoue
            prompt_to_use = formatted_prompt
            routing_used = False

        # ═══════════════════════════════════════════════════════════════
        # NOUVEAU LAYER: ROUTER EMBEDDINGS BOTLIVE (prioritaire)
        # ═══════════════════════════════════════════════════════════════
        if BOTLIVE_ROUTER_EMBEDDINGS_ENABLED:
            try:
                from core.botlive_intent_router import route_botlive_intent
                from core.jessica_prompt_segmenter import build_jessica_prompt_segment

                logger.info(
                    "[BOTLIVE_ROUTER] stage=INTENT status=START company_id=%s user_id=%s",
                    company_id,
                    user_id,
                )

                # Reconstruire un état compact similaire à celui de HYDE v18
                start_state = order_tracker.get_state(user_id)
                digits = "".join(
                    ch for ch in (start_state.numero or "") if ch.isdigit()
                ) if getattr(start_state, "numero", None) else ""
                tel_valide = len(digits) == 10

                state_compact = {
                    "photo_collected": bool(getattr(start_state, "produit", None)),
                    "paiement_collected": bool(getattr(start_state, "paiement", None)),
                    "zone_collected": bool(getattr(start_state, "zone", None)),
                    "tel_collected": bool(getattr(start_state, "numero", None)),
                    "tel_valide": tel_valide,
                }
                collected_count = (
                    int(state_compact["photo_collected"]) +
                    int(state_compact["paiement_collected"]) +
                    int(state_compact["zone_collected"]) +
                    int(state_compact["tel_collected"] and state_compact["tel_valide"])
                )
                state_compact["collected_count"] = collected_count
                state_compact["is_complete"] = bool(
                    getattr(start_state, "is_complete", lambda: False)()
                ) if hasattr(start_state, "is_complete") else False

                routing = await route_botlive_intent(
                    company_id=company_id,
                    user_id=user_id,
                    message=question_text or "",
                    conversation_history=history_text or "",
                    state_compact=state_compact,
                )

                hyde_like_result = {
                    "success": True,
                    "intent": routing.intent,
                    "confidence": routing.confidence,
                    "mode": routing.mode,
                    "missing_fields": routing.missing_fields,
                    "state": routing.state,
                    "raw": routing.debug.get("raw_message", ""),
                    "token_info": {
                        "source": "router_embeddings",
                        "intent_score": routing.debug.get("intent_score"),
                    },
                }

                logger.info(
                    "[BOTLIVE_ROUTER] stage=INTENT status=OK intent=%s mode=%s missing=%s score=%.2f",
                    routing.intent,
                    routing.mode,
                    routing.missing_fields,
                    routing.confidence,
                )

                segment = build_jessica_prompt_segment(
                    base_prompt_template=botlive_prompt_template,
                    hyde_result=hyde_like_result,
                    question_with_context=question_with_context,
                    conversation_history=history_text or "",
                    detected_objects_str=detected_objects_str,
                    filtered_transactions_str=filtered_transactions_str,
                    expected_deposit_str=expected_deposit_str,
                    enriched_checklist=enriched_checklist,
                )

                format_block = """

FORMAT DE RÉPONSE OBLIGATOIRE - NE PAS IGNORER

Tu DOIS ABSOLUMENT répondre en utilisant EXACTEMENT ce format:

<thinking>
[Ton raisonnement détaillé ici]
</thinking>

<response>
[Ta réponse au client ici - 2-3 lignes max]
</response>
"""

                prompt_to_use = segment["prompt"] + format_block
                routing_used = True

                logger.info(
                    "[BOTLIVE_ROUTER] stage=JESSICA_PROMPT status=OK mode=%s len=%s",
                    segment.get("mode"),
                    len(prompt_to_use),
                )

                # APPEL LLM AVEC FAILSAFE (PROMPT BASE + SEGMENT ADAPTATIF)
                try:
                    from core.botlive_failsafe import safe_llm_call_with_failsafe

                    routing_result = {
                        "mode": routing.mode,
                        "confidence": routing.confidence,
                        "intent": routing.intent,
                        "missing_fields": routing.missing_fields,
                        "state": routing.state,
                    }

                    company_config = {
                        "support_number": "+225 0787360757",
                        "product_type": "couches bébé",
                        "company_name": "Rue du Grossiste",
                    }

                    checklist_str = enriched_checklist or "[CHECKLIST NON DISPONIBLE]"

                    failsafe_result = await safe_llm_call_with_failsafe(
                        routing_result=routing_result,
                        company_config=company_config,
                        checklist=checklist_str,
                        user_message=question_with_context,
                    )

                    llm_text = failsafe_result.get("response")
                    token_usage = failsafe_result.get("tokens") or {}

                except Exception as failsafe_err:
                    logger.error("[BOTLIVE_FAILSAFE] Erreur appel LLM failsafe: %s", failsafe_err, exc_info=True)

            except Exception as router_err:
                logger.error(
                    "[BOTLIVE_ROUTER] stage=LAYER status=ERROR fallback=GLOBAL_OR_HYDE error=%s",
                    router_err,
                    exc_info=True,
                )

    # ... (rest of the code remains the same)
    # LAYER HYDE v18 DÉSACTIVÉ (commenté)
    # Ancien bloc optionnel, maintenant neutralisé pour éviter les erreurs
    # de structure try/except et se concentrer sur le router embeddings.
    #
    # if not routing_used and BOTLIVE_V18_ENABLED:
    #     try:
    #         from core.hyde_v18_layer import run_hyde_v18
    #         from core.jessica_prompt_segmenter import build_jessica_prompt_segment
    #
    #         logger.info(
    #             "[BOTLIVE_V18] stage=HYDE_INTENT status=START company_id=%s user_id=%s",
    #             company_id,
    #             user_id,
    #         )
    #
    #         hyde_result = await run_hyde_v18(
    #             company_id=company_id,
    #             user_id=user_id,
    #             message=question_text or "",
    #             conversation_history=history_text or "",
    #         )
    #
    #         if hyde_result.get("success"):
    #             ...
    #         else:
    #             ...
    #
    #     except Exception as hyde_v18_err:
    #         logger.error("[BOTLIVE_V18] Erreur layer HYDE: %s", hyde_v18_err, exc_info=True)


            # ═══════════════════════════════════════════════════════════════
            # LOGS COLORÉS POUR SUIVI
            # ═══════════════════════════════════════════════════════════════

            if llm_text is not None:

                # Extraire thinking et response
                thinking_match = re.search(r'<thinking>(.*?)</thinking>', llm_text, re.DOTALL)
                response_match = re.search(r'<response>(.*?)</response>', llm_text, re.DOTALL)
                
                # 🔵 QUESTION CLIENT (BLEU)
                print("\n" + "="*80)
                print(f"\033[94m🔵 QUESTION CLIENT:\033[0m")
                # Afficher le texte réel ou [IMAGE] si image sans texte
                if question_text:
                    display_question = question_text
                elif images:
                    display_question = "[IMAGE]"
                else:
                    display_question = "[Message vide]"
                print(f"\033[94m{display_question}\033[0m")
                
                # THINKING LLM (JAUNE)
                try:
                    if thinking_match:
                        thinking_content = thinking_match.group(1).strip()
                        from FIX_CONTEXT_LOSS_COMPLETE import extract_from_thinking_simple
                        thinking_data = extract_from_thinking_simple(llm_text)

                        if thinking_data:
                            print(f"\n [THINKING] Données extraites: {thinking_data}")

                            # Mettre à jour le notepad avec les données du thinking
                            notepad = await notepad_manager.get_notepad(user_id, company_id)
                            updated = False

                            # Mapper les champs (ignorer les métadonnées avec _)
                            if 'photo_produit' in thinking_data:
                                notepad['photo_produit'] = thinking_data['photo_produit']
                                updated = True
                            if 'photo_produit_description' in thinking_data:
                                notepad['photo_produit_description'] = thinking_data['photo_produit_description']
                                updated = True
                            if 'paiement' in thinking_data:
                                notepad['paiement'] = thinking_data['paiement']
                                updated = True
                            if 'acompte' in thinking_data:
                                notepad['acompte'] = thinking_data['acompte']
                                updated = True
                            if 'zone' in thinking_data:
                                notepad['delivery_zone'] = thinking_data['zone']
                                updated = True
                            if 'frais_livraison' in thinking_data:
                                notepad['delivery_cost'] = thinking_data['frais_livraison']
                                updated = True
                            if 'telephone' in thinking_data:
                                notepad['phone_number'] = thinking_data['telephone']
                                updated = True
                            if 'produit' in thinking_data:
                                notepad['last_product_mentioned'] = thinking_data['produit']
                                updated = True

                            # Sauvegarder si des changements
                            if updated:
                                await notepad_manager.update_notepad(user_id, company_id, notepad)
                                print(f" [THINKING] Notepad mis à jour depuis thinking")
                            else:
                                print(f" [THINKING] Aucune donnée à sauvegarder")
                        else:
                            print(f" [THINKING] Aucune donnée extraite du thinking")
                except Exception as thinking_err:
                    print(f" [THINKING] Erreur extraction: {thinking_err}")
            provider = token_usage.get("provider", "groq")
            fallback_used = token_usage.get("fallback_used", False)
            health_check = token_usage.get("health_check", False)
            model_used = token_usage.get("model", groq_model)

            # Sécuriser la récupération des compteurs de tokens
            prompt_tokens = token_usage.get("prompt_tokens")
            completion_tokens = token_usage.get("completion_tokens")
            total_tokens = token_usage.get("total_tokens")

            if (
                isinstance(prompt_tokens, (int, float)) and
                isinstance(completion_tokens, (int, float)) and
                isinstance(total_tokens, (int, float))
            ):
                if provider == "groq":
                    # Calcul coût Groq llama-3.3-70b-versatile (tarifs officiels)
                    input_cost = prompt_tokens * 0.00000059  # $0.59/1M tokens
                    output_cost = completion_tokens * 0.00000079  # $0.79/1M tokens
                    total_cost = input_cost + output_cost

                    health_status = " Health Check OK" if health_check else " Direct"
                    print(f"\n\033[91m TOKENS RÉELS GROQ ({health_status}):\033[0m")
                    print(f"\033[91mPrompt: {prompt_tokens} | Completion: {completion_tokens} | TOTAL: {total_tokens}\033[0m")
                    print(f"\033[91m COÛT: ${total_cost:.6f} (${input_cost:.6f} input + ${output_cost:.6f} output)\033[0m")
                    print(f"\033[91m MODÈLE: {model_used}\033[0m")

                elif provider == "deepseek":
                    estimated = " (estimé)" if token_usage.get('estimated') else ""
                    health_reason = " Groq Unhealthy" if health_check else " Fallback"
                    print(f"\n\033[93m TOKENS DEEPSEEK ({health_reason}):\033[0m")
                    print(f"\033[93mPrompt: {prompt_tokens} | Completion: {completion_tokens} | TOTAL: {total_tokens}{estimated}\033[0m")
                    print(f"\033[93m COÛT: ~$0.000001 (DeepSeek gratuit)\033[0m")
                    print(f"\033[93m MODÈLE: {model_used}\033[0m")

                elif provider == "emergency":
                    print(f"\n\033[95m RÉPONSE D'URGENCE:\033[0m")
                    print(f"\033[95mErreur: {token_usage.get('error', 'Unknown')}\033[0m")
                    print(f"\033[95m COÛT: $0.000000\033[0m")
                    print(f"\033[95m MODÈLE: emergency\033[0m")

            print("="*80 + "\n")

            return client_response

    except Exception as e:
        print(f"[BOTLIVE] Erreur générale: {e}")
        return "Mode Live indisponible temporairement. Réessayez ou envoyez votre question en texte."


@app.post("/chat")
@limiter.limit("300/minute")  # Augmenté pour tests de charge
async def chat_endpoint(req: ChatRequest, request: Request):
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    
    # ========== INITIALISER TRACKER PERFORMANCE ==========
    from core.rag_performance_tracker import get_tracker, cleanup_tracker
    tracker = get_tracker(request_id)
    tracker.start_step("endpoint_init")
    
    print("==== REQUÊTE CHAT REÇUE ====")
    logger.debug("=== NOUVELLE REQUÊTE CHAT ===")
    logger.info(f"[CHAT] ➡️ Reçu | request_id={request_id} company_id={req.company_id} user_id={req.user_id} question='{req.message[:80]}'")
    
    # 🔍 LOGS MÉMOIRE CONVERSATIONNELLE - ENDPOINT CHAT
    print(f"🔍 [CHAT_ENDPOINT] RÉCEPTION REQUÊTE:")
    print(f"🔍 [CHAT_ENDPOINT] Message: '{req.message}'")
    print(f"🔍 [CHAT_ENDPOINT] Company: {req.company_id}")
    print(f"🔍 [CHAT_ENDPOINT] User: {req.user_id}")
    print()
    
    # ═════════════════════════════════════════════════════════════
    # NORMALISATION MESSAGE : Si image présente, forcer message générique
    # (Impossible d'envoyer image + texte simultanément donc pas de conflit)
    # ═══════════════════════════════════════════════════════════════
    if req.images and len(req.images) > 0 and (not req.message or req.message.strip() == ""):
        req.message = "Voici la capture"
        print(f"📸 [CHAT_ENDPOINT] Image détectée sans texte → Message forcé: 'Voici la capture'")

    # === OPTIMISATION: PARALLÉLISER HYDE + CACHE + PROMPT ===
    # Gain attendu: 6.7s → 3.5s (-47%)
    import asyncio
    
    def _truncate_log(msg, size=100):
        msg = str(msg)
        return msg if len(msg) <= size else msg[:size] + '... (truncated)'
    
    # Utilisation de la troncature pour les logs peu essentiels
    logger.debug(f"Headers: {_truncate_log(dict(request.headers))}")
    logger.debug(f"Body: {_truncate_log(req)}")
    
    # Déterminer si HYDE nécessaire (skip pour requêtes courtes OU simples)
    word_count = len(req.message.split()) if req.message else 0
    
    # ⚡ OPTIMISATION: Skip HYDE pour questions simples (gain ~2s sur 60% requêtes)
    if HYDE_SKIP_SIMPLE_QUERIES:
        from core.hyde_optimizer import should_skip_hyde
        skip_hyde_simple = should_skip_hyde(req.message or "")
    else:
        skip_hyde_simple = False
    
    skip_hyde = req.botlive_enabled or word_count < 10 or not req.message or skip_hyde_simple
    
    if skip_hyde:
        reason = "botlive" if req.botlive_enabled else "court" if word_count < 10 else "simple" if skip_hyde_simple else "vide"
        print(f"⚡ [HYDE] Skippé ({reason}, mots={word_count})")
    
    # Créer tâches parallèles
    async def get_prompt_version():
        try:
            # ⚡ OPTIMISATION: Utiliser cache local pour prompts (gain ~3s)
            from core.prompt_local_cache import get_prompt_cache
            prompt_cache = get_prompt_cache()
            
            # Essayer cache d'abord
            cached_version = prompt_cache.get(f"{req.company_id}_version")
            if cached_version:
                return int(cached_version)
            
            # Sinon fetch Supabase
            supabase_client = get_supabase_client()
            prompt_manager = PromptManager(supabase_client)
            active_prompt = await prompt_manager.get_active_prompt(req.company_id)
            version = active_prompt['version']
            
            # Sauvegarder en cache
            prompt_cache.set(f"{req.company_id}_version", str(version))
            
            return version
        except Exception as e:
            log3("[PROMPT_ERROR]", f"Erreur récupération prompt: {e}")
            return 1
    
    async def run_hyde():
        if skip_hyde:
            return None
        try:
            from core.hyde_word_scorer import clarify_request_with_hyde
            clarified = await clarify_request_with_hyde(req.message)
            if clarified:
                print(f"[HYDE] Requête nettoyée : {clarified}")
                return clarified
            else:
                print("[HYDE] Aucun nettoyage nécessaire")
                return None
        except Exception as e:
            print(f"[HYDE] Erreur: {e}")
            return None
    
    # Exécuter en parallèle
    print("⚡ [PARALLEL] Lancement HYDE + Prompt version...")
    hyde_result, prompt_version = await asyncio.gather(
        run_hyde(),
        get_prompt_version()
    )
    
    # Appliquer résultat HYDE
    if hyde_result:
        req.message = hyde_result
    
    # === CACHE MULTI-NIVEAUX: EXACT + SÉMANTIQUE ===
    # ✅ CACHE RÉACTIVÉ POUR OPTIMISATION PERFORMANCE
    if not req.botlive_enabled:
        # NIVEAU 1: Cache exact (Redis classique)
        try:
            cache_key = redis_cache.make_key(req.message, req.company_id, prompt_version)
            cached_response = redis_cache.get(req.message, req.company_id, prompt_version)
            
            if cached_response:
                log3("[CACHE EXACT HIT]", f"Réponse trouvée en cache exact: {req.message[:50]}...")
                log3("[CACHE HIT]", f"Temps économisé: ~3-5 secondes de traitement RAG")
                
                # Enrichir la réponse avec les informations de cache
                if isinstance(cached_response, dict):
                    cached_response["cached"] = True
                    cached_response["cache_type"] = "exact"
                    cached_response["cache_hit_time"] = "~50ms"
                else:
                    cached_response = {
                        "response": cached_response,
                        "cached": True,
                        "cache_type": "exact",
                        "cache_hit_time": "~50ms"
                    }
                
                return cached_response
            
            log3("[CACHE EXACT MISS]", "Pas de match exact")
            
        except Exception as cache_error:
            log3("[CACHE ERROR]", f"Erreur cache exact: {cache_error}")
        
        # NIVEAU 2: Cache sémantique (similarité) - DÉSACTIVÉ POUR TESTS
        try:
            if False:  # Désactivé temporairement
                from core.semantic_cache import check_semantic_cache
                
                semantic_result = check_semantic_cache(req.message, req.company_id)
                
                if semantic_result:
                    similarity = semantic_result.get("similarity", 0)
                    # Convertir numpy types en Python natifs
                    similarity = float(similarity) if hasattr(similarity, 'item') else float(similarity)
                    
                    log3("[CACHE SEMANTIC HIT]", f"Réponse similaire trouvée (similarité: {similarity:.3f})")
                    log3("[CACHE SEMANTIC]", f"Question originale: {semantic_result.get('original_query', '')[:50]}...")
                    log3("[CACHE HIT]", f"Temps économisé: ~3-5 secondes de traitement RAG")
                    
                    response_data = semantic_result.get("response")
                    if isinstance(response_data, dict):
                        response_data["cached"] = True
                        response_data["cache_type"] = "semantic"
                        response_data["similarity"] = similarity
                        response_data["cache_hit_time"] = "~100ms"
                    else:
                        response_data = {
                            "response": response_data,
                            "cached": True,
                            "cache_type": "semantic",
                            "similarity": similarity,
                            "cache_hit_time": "~100ms"
                        }
                    
                    return response_data
                
                log3("[CACHE SEMANTIC MISS]", "Aucune réponse similaire, traitement RAG complet")
        except Exception as semantic_error:
            log3("[CACHE SEMANTIC ERROR]", f"Erreur cache sémantique: {semantic_error}")
        # Continuer sans cache en cas d'erreur

    """
    Endpoint principal du chatbot RAG multi-entreprise.
    """
    print(f"[API] Requête: {req.company_id[:8]}... | {req.user_id}")
    
    # Fin tracking endpoint_init
    tracker.end_step()
    
    # Validation de sécurité RENFORCÉE avec gestion d'erreur
    try:
        # Appel direct sans safe_api_call pour éviter les problèmes de coroutine
        security_check = validate_user_prompt(req.message)
        
        if not security_check.is_safe:
            logger.warning(f"[SECURITY] Requête bloquée pour {req.user_id}: {security_check.risk_level}")
            return {
                "response": "🛡️ Demande refusée pour des raisons de sécurité. Veuillez reformuler votre question de manière appropriée.",
                "security_blocked": True,
                "security_score": security_check.risk_level,
                "threats_detected": getattr(security_check, 'threats_detected', [])
            }
    except Exception as e:
        logger.error(f"[SECURITY] Erreur critique validation: {str(e)}")
        # Fallback: continuer avec validation basique
        security_check = type('SecurityCheck', (), {'is_safe': True, 'risk_level': 0})()
    
    # 🔍 RÉCUPÉRATION AUTOMATIQUE DE L'HISTORIQUE
    print(f"🔍 [CHAT_ENDPOINT] RÉCUPÉRATION HISTORIQUE AUTOMATIQUE:")
    try:
        conversation_history = await get_history(req.company_id, req.user_id)
        print(f"🔍 [CHAT_ENDPOINT] Historique récupéré: {len(conversation_history)} chars")
        print(f"🔍 [CHAT_ENDPOINT] Contient Cocody: {'Cocody' in conversation_history}")
    except Exception as e:
        print(f"🔍 [CHAT_ENDPOINT] Erreur récupération historique: {e}")
        conversation_history = ""
    
    # 🔍 SAUVEGARDE MESSAGE UTILISATEUR (incluant images)
    print(f"🔍 [CHAT_ENDPOINT] SAUVEGARDE MESSAGE UTILISATEUR:")
    try:
        user_content = {"text": req.message or "", "images": req.images or []}
        await save_message_supabase(req.company_id, req.user_id, "user", user_content)
        print(f"🔍 [CHAT_ENDPOINT] Message utilisateur sauvegardé")
    except Exception as e:
        print(f"🔍 [CHAT_ENDPOINT] Erreur sauvegarde message: {e}")
    
    # 🔍 LOGS MÉMOIRE - TRANSMISSION AU RAG
    print(f"🔍 [CHAT_ENDPOINT] TRANSMISSION AU RAG:")
    print(f"🔍 [CHAT_ENDPOINT] conversation_history transmis: '{conversation_history[:100]}...'")
    print()
    
    # ROUTAGE INTELLIGENT: Botlive vs RAG
    # ⚠️ CORRECTION CRITIQUE: Si botlive_enabled=True, TOUJOURS utiliser Botlive
    # (même sans images, pour maintenir le contexte conversationnel)
    has_images = req.images and len(req.images) > 0
    has_message = req.message and req.message.strip()
    
    # ✅ LOGIQUE CORRIGÉE: Botlive si mode activé (peu importe images/message)
    use_botlive = req.botlive_enabled or ZETA_BOTLIVE_ONLY
    
    if use_botlive:
        # 🚀 NOUVEAU SYSTÈME HYBRIDE DEEPSEEK V3 + GROQ 70B
        print(f"\n{'='*80}")
        print(f"🚀 [BOTLIVE] ENTRÉE SYSTÈME HYBRIDE")
        print(f"{'='*80}")
        print(f"Company ID: {req.company_id}")
        print(f"User ID: {req.user_id}")
        print(f"Message: {req.message}")
        print(f"Images: {len(req.images) if req.images else 0}")
        print(f"{'='*80}\n")
        
        try:
            print(f"[BOTLIVE] 📦 Import botlive_hybrid...")
            from core.botlive_rag_hybrid import botlive_hybrid
            print(f"[BOTLIVE] ✅ botlive_hybrid importé")
            
            print(f"[BOTLIVE] 📦 Import get_botlive_prompt...")
            from database.supabase_client import get_botlive_prompt
            print(f"[BOTLIVE] ✅ get_botlive_prompt importé")
            
            # Utiliser les prompts hardcodés pour extraction du numéro
            from core.botlive_prompts_hardcoded import DEEPSEEK_V3_PROMPT
            botlive_prompt_template = DEEPSEEK_V3_PROMPT
            print(f"[BOTLIVE] 🔧 Utilisation prompt hardcodé pour extraction numéro")
            
            # Extraire le numéro de téléphone de l'entreprise du prompt
            # Gère TOUS les formats: "📞 +225 07 87 36 07 57 ☎️", "WhatsApp: 0787360757", etc.
            company_phone = None
            if botlive_prompt_template:
                import re
                
                # Patterns multiples pour trouver le numéro (après mot-clé ou seul)
                phone_patterns = [
                    # Après mot-clé (WhatsApp, Tel, Contact, etc.)
                    r'(?:whatsapp|tel|téléphone|telephone|contact|appel|numéro|numero)[\s:]*[^\d]*((?:\+?225\s*)?\d{2}[\s\-]*\d{2}[\s\-]*\d{2}[\s\-]*\d{2}[\s\-]*\d{2})',
                    # N'importe où avec code pays
                    r'\+225[\s\-]*\d{2}[\s\-]*\d{2}[\s\-]*\d{2}[\s\-]*\d{2}[\s\-]*\d{2}',
                    # 10 chiffres quelque part
                    r'0\d{9}',
                ]
                
                for pattern in phone_patterns:
                    phone_match = re.search(pattern, botlive_prompt_template, re.IGNORECASE)
                    if phone_match:
                        if len(phone_match.groups()) > 0:
                            company_phone = phone_match.group(1)
                        else:
                            company_phone = phone_match.group(0)
                        
                        # Nettoyer (garder uniquement chiffres, espaces, +, -)
                        company_phone = company_phone.strip()
                        print(f"[BOTLIVE] 📱 Numéro entreprise extrait: {company_phone}")
                        break
                
                if not company_phone:
                    print(f"[BOTLIVE] ⚠️ Aucun numéro de téléphone trouvé dans le prompt")
            
            # Préparer le contexte pour le système hybride
            context = {
                'detected_objects': [],
                'filtered_transactions': [],
                'expected_deposit': '2000 FCFA',
                'company_phone': company_phone
            }
            
            # Si images présentes, les traiter d'abord
            if req.images and len(req.images) > 0:
                # Traitement vision (réutiliser la logique existante)
                vision_result = await _process_botlive_vision(req.images[0], company_phone=company_phone)
                context.update(vision_result)
                
                # Note: req.message est déjà normalisé en "Voici la capture" au début du endpoint
            
            # ✅ OPTIMISER L'HISTORIQUE AVANT DE L'ENVOYER AU SYSTÈME HYBRIDE
            conversation_history = deduplicate_conversation_history(conversation_history)
            
            # Appel du système hybride
            print(f"[BOTLIVE] 🚀 Appel botlive_hybrid.process_request()...")
            print(f"[BOTLIVE]    - user_id: {req.user_id}")
            print(f"[BOTLIVE]    - company_id: {req.company_id}")
            print(f"[BOTLIVE]    - message: {req.message}")
            print(f"[BOTLIVE]    - context keys: {list(context.keys())}")
            
            hybrid_result = await botlive_hybrid.process_request(
                user_id=req.user_id,
                message=req.message or "",
                context=context,
                conversation_history=conversation_history,
                company_id=req.company_id  # ← AJOUT: Passer company_id
            )
            
            print(f"[BOTLIVE] ✅ Réponse reçue du système hybride")
            
            response = {
                "response": hybrid_result['response'],
                "llm_used": hybrid_result['llm_used'],
                "routing_reason": hybrid_result['routing_reason'],
                "processing_time": hybrid_result['processing_time'],
                "tools_executed": hybrid_result['tools_executed'],
                "hybrid_system": True
            }
            
            # 🎨 AFFICHAGE FORMATÉ FINAL
            _print_hybrid_summary(
                question=req.message or "",
                thinking=hybrid_result.get('thinking', ''),
                response=hybrid_result['response'],
                llm_used=hybrid_result['llm_used'],
                prompt_tokens=hybrid_result.get('prompt_tokens', 0),
                completion_tokens=hybrid_result.get('completion_tokens', 0),
                total_cost=hybrid_result.get('total_cost', 0),
                processing_time=hybrid_result.get('processing_time', 0.0),
                timings=hybrid_result.get('timings', {}),
                router_metrics=hybrid_result.get('router_metrics', {})
            )
            
            # 📊 SAUVEGARDE JSON AUTOMATIQUE
            try:
                from core.json_logger import log_request_metrics
                
                router_metrics = hybrid_result.get('router_metrics', {})
                timings_raw = hybrid_result.get('timings', {})
                
                # Convertir tous les timings de secondes en millisecondes
                timings = {
                    'routing': timings_raw.get('routing', 0.0) * 1000,
                    'prompt_generation': timings_raw.get('prompt_generation', 0.0) * 1000,
                    'llm_call': timings_raw.get('llm_call', 0.0) * 1000,
                    'tools_execution': timings_raw.get('tools_execution', 0.0) * 1000,
                    'total': hybrid_result.get('processing_time', 0.0) * 1000
                }
                
                log_request_metrics(
                    question=req.message or "",
                    thinking=hybrid_result.get('thinking', ''),
                    response=hybrid_result['response'],
                    model=hybrid_result['llm_used'],
                    prompt_tokens=hybrid_result.get('prompt_tokens', 0),
                    completion_tokens=hybrid_result.get('completion_tokens', 0),
                    llm_cost=hybrid_result.get('total_cost', 0.0),
                    router_cost=router_metrics.get('cost', 0.0),
                    router_tokens=router_metrics.get('tokens', 0),
                    routing_reason=hybrid_result.get('routing_reason', ''),
                    timings=timings,
                    company_id=req.company_id,
                    user_id=req.user_id
                )
            except Exception as json_log_error:
                logger.error(f"❌ Erreur sauvegarde JSON: {json_log_error}")
            
        except Exception as hybrid_error:
            import traceback
            print(f"\n{'='*80}")
            print(f"❌ [HYBRID] ERREUR SYSTÈME HYBRIDE:")
            print(f"{'='*80}")
            print(f"Message: {hybrid_error}")
            print(f"Type: {type(hybrid_error).__name__}")
            print(f"\nTraceback complet:")
            traceback.print_exc()
            print(f"{'='*80}\n")
            logger.error(f"❌ [HYBRID] Erreur: {hybrid_error}", exc_info=True)
            
            # Fallback vers ancien système
            botlive_text = await _botlive_handle(req.company_id, req.user_id, req.message or "", req.images or [], conversation_history)
            response = {"response": botlive_text, "fallback_used": True}
    else:
        # RAG normal. Si image seule, créer un fallback minimal
        msg_for_rag = req.message or ("[Image reçue]" if (req.images and len(req.images) > 0) else "")

        # ========== CONSTRUCTION CONTEXTE INTELLIGENT ==========
        print(" [CONTEXT] Construction contexte intelligent...")
        context_summary = ""
        try:
            context_summary = build_smart_context_summary(
                conversation_history=conversation_history,
                user_id=req.user_id,
                company_id=req.company_id
            )
            print(f" [CONTEXT] Résumé généré:\n{context_summary}")
        except Exception as ctx_error:
            print(f" [CONTEXT] Erreur construction contexte: {ctx_error}")
            context_summary = ""

        response = await safe_api_call(
            lambda: get_universal_rag_response(msg_for_rag, req.company_id, req.user_id, req.images, conversation_history, False, request_id),
            context="rag_response",
            fallback_func=lambda: "Je rencontre des difficultés techniques. Pouvez-vous reformuler votre question ?",
            max_retries=3
        )

    # Si erreur dans RAG, utiliser la réponse fallback
    if hasattr(response, 'success') and not response.success:
        response = response.fallback_response or "Service temporairement indisponible."
    
    # ANCIEN SYSTÈME DÉSACTIVÉ - NOUVEAU SYSTÈME HYBRIDE DANS RAG ENGINE
    # Vérification hallucination avec gestion d'erreur
    try:
        # hallucination_check = await safe_api_call(
        #     lambda: check_ai_response(req.message, response, req.company_id),
        #     context="hallucination_check",
        #     max_retries=2
        # )
        # DÉSACTIVÉ - Le nouveau système hybride est intégré dans le RAG Engine
        # Créer un objet factice pour éviter les erreurs
        hallucination_check = type('HallucinationCheck', (), {
            'is_safe': True, 
            'confidence_score': 1.0,
            'suggested_response': None
        })()
        
        # ANCIEN SYSTÈME COMPLÈTEMENT DÉSACTIVÉ
        # Le nouveau système hybride gère tout dans le RAG Engine
        if False:  # Désactivé
            logger.warning(f"[HALLUCINATION] Réponse corrigée pour {req.user_id}: score={hallucination_check.confidence_score}")
            response = hallucination_check.suggested_response or response
        
        # 🔍 SAUVEGARDE RÉPONSE ASSISTANT
        print(f"🔍 [CHAT_ENDPOINT] SAUVEGARDE RÉPONSE ASSISTANT:")
        try:
            # Extraire la réponse selon le format
            response_text = response.get("response", str(response)) if isinstance(response, dict) else str(response)
            
            # Si Botlive : extraire SEULEMENT <response> (pas le <thinking>)
            if getattr(req, "botlive_enabled", False):
                import re
                response_match = re.search(r'<response>(.*?)</response>', response_text, re.DOTALL)
                if response_match:
                    response_text = response_match.group(1).strip()
                    print(f"🔍 [CHAT_ENDPOINT] Extraction <response> pour historique: {response_text[:100]}...")
                else:
                    print(f"⚠️ [CHAT_ENDPOINT] Pas de balise <response>, sauvegarde texte brut")
            
            await save_message_supabase(req.company_id, req.user_id, "assistant", {"text": response_text})
            print(f"🔍 [CHAT_ENDPOINT] Réponse assistant sauvegardée")
            
            # ========== EXTRACTION ET SAUVEGARDE CONTEXTE ==========
            print("🧠 [CONTEXT] Extraction contexte depuis historique...")
            try:
                # Construire historique complet avec nouveau message
                full_history = conversation_history + f"\nClient: {req.message}\nVous: {response_text}"
                
                # Extraire infos
                extracted = extract_from_last_exchanges(full_history)
                
                if extracted:
                    print(f"✅ [CONTEXT] Infos extraites: {extracted}")
                    
                    # Sauvegarder dans notepad
                    try:
                        from core.conversation_notepad import ConversationNotepad
                        notepad = ConversationNotepad()
                        
                        # Sauvegarder les données extraites
                        if extracted.get('produit'):
                            # Extraire prix si disponible
                            prix = float(extracted.get('prix_produit', 0)) if extracted.get('prix_produit') else 0.0
                            notepad.update_product(req.user_id, req.company_id, extracted['produit'], 300, prix)
                        
                        if extracted.get('zone') and extracted.get('frais_livraison'):
                            notepad.update_delivery(req.user_id, req.company_id, extracted['zone'], float(extracted['frais_livraison']))
                        
                        if extracted.get('telephone'):
                            notepad_data = notepad.get_notepad(req.user_id, req.company_id)
                            notepad_data['phone_number'] = extracted['telephone']
                        
                        if extracted.get('paiement'):
                            notepad.update_payment(req.user_id, req.company_id, extracted['paiement'])
                        
                        print(f"✅ [CONTEXT] Contexte sauvegardé dans notepad")
                    except Exception as notepad_error:
                        print(f"⚠️ [CONTEXT] Erreur sauvegarde notepad: {notepad_error}")
                else:
                    print("⚠️ [CONTEXT] Aucune info extraite")
            
            except Exception as extract_error:
                print(f"⚠️ [CONTEXT] Erreur extraction: {extract_error}")
            
        except Exception as e:
            print(f"🔍 [CHAT_ENDPOINT] Erreur sauvegarde réponse: {e}")
        
        # === SAUVEGARDE EN CACHE REDIS ===
        # Extraire thinking et validation depuis response (dict ou string)
        try:
            print(f"🔍 [DEBUG] Type de response: {type(response)}")
            print(f"🔍 [DEBUG] Contenu response: {str(response)[:200]}")
            
            thinking_data = ""
            validation_data = None
            if isinstance(response, dict):
                thinking_data = response.get('thinking', '')
                validation_data = response.get('validation', None)
                response_text = response.get('response', str(response))
                print(f"🔍 [DEBUG] Thinking extrait: {len(thinking_data)} chars")
                print(f"🔍 [DEBUG] Validation: {validation_data is not None}")
            else:
                response_text = str(response) if response else "Erreur: réponse vide"
                print(f"🔍 [DEBUG] Response est une string, pas de thinking")
        except Exception as debug_error:
            print(f"❌ [DEBUG] Erreur extraction thinking: {debug_error}")
            thinking_data = ""
            validation_data = None
            response_text = str(response) if response else "Erreur"
        
        # ═══════════════════════════════════════════════════════════════
        # 📊 ENRICHISSEMENT CONTEXTE COMPLET POUR DEBUGGING
        # ═══════════════════════════════════════════════════════════════
        
        # Récupérer TOUS les contextes système
        debug_contexts = {}
        
        try:
            # 1. STATE TRACKER (complétude commande)
            from core.order_state_tracker import order_tracker
            state = order_tracker.get_state(req.user_id)
            debug_contexts["state_tracker"] = {
                "completion_rate": state.get_completion_rate(),
                "missing_fields": state.get_missing_fields(),
                "collected_data": state.to_dict()
            }
        except Exception as e:
            debug_contexts["state_tracker"] = {"error": str(e)}
        
        try:
            # 2. NOTEPAD (mémoire conversationnelle)
            from core.conversation_notepad import ConversationNotepad
            notepad = ConversationNotepad()
            notepad_content = notepad.get_content(req.user_id, req.company_id)
            debug_contexts["notepad"] = {
                "content": notepad_content,
                "length": len(notepad_content)
            }
        except Exception as e:
            debug_contexts["notepad"] = {"error": str(e)}
        
        try:
            # 3. ENHANCED MEMORY (buffer conversationnel)
            from core.enhanced_memory import get_enhanced_memory
            enhanced_mem = get_enhanced_memory()
            recent_interactions = enhanced_mem.get_recent_interactions(req.user_id, limit=3)
            debug_contexts["enhanced_memory"] = {
                "recent_count": len(recent_interactions),
                "buffer_size": enhanced_mem.buffer_size
            }
        except Exception as e:
            debug_contexts["enhanced_memory"] = {"error": str(e)}
        
        try:
            # 4. THINKING PARSER (données structurées)
            if thinking_data:
                from core.thinking_parser import get_thinking_parser
                parser = get_thinking_parser()
                thinking_parsed = parser.parse_full_thinking(thinking_data)
                debug_contexts["thinking_parsed"] = {
                    "phase2_collected": thinking_parsed.get("phase2_collecte", {}),
                    "phase5_decision": thinking_parsed.get("phase5_decision", {}),
                    "completeness": thinking_parsed.get("completeness", "unknown")
                }
        except Exception as e:
            debug_contexts["thinking_parsed"] = {"error": str(e)}
        
        try:
            # 5. ANTI-HALLUCINATION (validation sources)
            debug_contexts["anti_hallucination"] = {
                "confidence_score": hallucination_check.confidence_score,
                "is_grounded": hallucination_check.is_grounded,
                "sources_used": getattr(hallucination_check, 'sources_count', 0)
            }
        except Exception as e:
            debug_contexts["anti_hallucination"] = {"error": str(e)}
        
        try:
            # 6. SECURITY CHECK
            debug_contexts["security"] = {
                "risk_level": security_check.risk_level,
                "is_safe": security_check.is_safe,
                "threats_detected": getattr(security_check, 'threats', [])
            }
        except Exception as e:
            debug_contexts["security"] = {"error": str(e)}
        
        try:
            # 7. CONVERSATION HISTORY (historique complet)
            from core.conversation_manager import get_conversation_manager
            conv_manager = get_conversation_manager()
            history = conv_manager.get_history(req.user_id, req.company_id, limit=5)
            debug_contexts["conversation_history"] = {
                "message_count": len(history),
                "last_messages": [{
                    "role": msg.get("role", "unknown"),
                    "content_preview": msg.get("content", "")[:100]
                } for msg in history[-3:]]
            }
        except Exception as e:
            debug_contexts["conversation_history"] = {"error": str(e)}
        
        try:
            # 8. CHECKPOINT (sauvegarde état)
            import os
            checkpoint_dir = "data/checkpoints"
            if os.path.exists(checkpoint_dir):
                checkpoints = [f for f in os.listdir(checkpoint_dir) if req.user_id in f]
                debug_contexts["checkpoints"] = {
                    "count": len(checkpoints),
                    "last_checkpoint": checkpoints[-1] if checkpoints else None
                }
        except Exception as e:
            debug_contexts["checkpoints"] = {"error": str(e)}
        
        final_response = {
            "response": response_text, 
            "cached": False,
            "security_score": security_check.risk_level,
            "hallucination_score": hallucination_check.confidence_score,
            "thinking": thinking_data,
            "validation": validation_data,
            "debug_contexts": debug_contexts  # ✅ TOUS LES CONTEXTES SYSTÈME
        }
        
        # Sauvegarder la réponse en cache pour les requêtes futures identiques
        # ✅ CACHE RÉACTIVÉ POUR OPTIMISATION PERFORMANCE
        if not getattr(req, "botlive_enabled", False):
            # Sauvegarder dans cache exact (Redis)
            try:
                redis_cache.set(req.message, req.company_id, prompt_version, final_response, ttl=1800)  # 30 minutes
                log3("[CACHE EXACT SAVE]", f"Réponse sauvegardée en cache exact: {req.message[:50]}...")
            except Exception as cache_save_error:
                log3("[CACHE SAVE ERROR]", f"Erreur sauvegarde cache exact: {cache_save_error}")
            
            # Sauvegarder dans cache sémantique
            try:
                from core.semantic_cache import save_to_semantic_cache
                save_to_semantic_cache(req.message, req.company_id, final_response, ttl=3600)  # 1h
                log3("[CACHE SEMANTIC SAVE]", f"Réponse sauvegardée en cache sémantique")
            except Exception as semantic_save_error:
                log3("[CACHE SEMANTIC SAVE ERROR]", f"Erreur sauvegarde cache sémantique: {semantic_save_error}")
        else:
            log3("[CACHE BYPASS]", "Écriture cache ignorée (mode Botlive)")
        
        # ========== FINALISER TRACKER & AFFICHER RÉSUMÉ ROUGE ==========
        try:
            from core.rag_performance_tracker import get_tracker, cleanup_tracker
            tracker = get_tracker(request_id)
            tracker.finish()
            
            # Afficher résumé en ROUGE
            tracker.print_summary_red()
            
            # Récupérer summary pour logs JSON
            performance_summary = tracker.get_summary()
            
            # Nettoyer le tracker
            cleanup_tracker(request_id)
        except Exception as tracker_error:
            logger.warning(f"⚠️ Erreur tracker: {tracker_error}")
            performance_summary = None
        
        # ========== SAUVEGARDE LOG JSON ==========
        try:
            from core.json_request_logger import get_json_request_logger
            
            processing_time_ms = (time.time() - start_time) * 1000
            # Utiliser response_text déjà extrait plus haut
            log_response_text = response_text if 'response_text' in locals() else (response.get("response", str(response)) if isinstance(response, dict) else str(response))
            
            # Préparer metadata avec performance
            metadata = {
                "processing_time_ms": round(processing_time_ms, 2),
                "cached": final_response.get("cached", False),
                "security_score": security_check.risk_level,
                "hallucination_score": hallucination_check.confidence_score,
                "botlive_enabled": getattr(req, "botlive_enabled", False),
                "has_images": bool(req.images),
                "prompt_version": prompt_version
            }
            
            # Ajouter performance tracking si disponible
            if performance_summary:
                metadata["performance"] = performance_summary
            
            json_logger = get_json_request_logger()
            json_logger.log_request(
                request_id=request_id,
                user_id=req.user_id,
                company_id=req.company_id,
                message=req.message,
                response=log_response_text,
                metadata=metadata
            )
            logger.debug(f"📝 Log JSON sauvegardé: {request_id}")
        except Exception as log_error:
            logger.warning(f"⚠️ Erreur sauvegarde log JSON: {log_error}")
        
        return final_response
    except Exception as e:
        print(f"[API] Erreur: {type(e).__name__}")
        logger.exception(f"[CHAT] ❌ Exception: {type(e).__name__}")
        
        # ========== SAUVEGARDE ERREUR JSON ==========
        try:
            from core.json_request_logger import get_json_request_logger
            
            processing_time_ms = (time.time() - start_time) * 1000
            
            json_logger = get_json_request_logger()
            json_logger.log_error(
                request_id=request_id,
                user_id=req.user_id,
                company_id=req.company_id,
                message=req.message,
                error=e,
                metadata={
                    "processing_time_ms": round(processing_time_ms, 2),
                    "error_location": "chat_endpoint"
                }
            )
            logger.debug(f"📝 Erreur JSON sauvegardée: {request_id}")
        except Exception as log_error:
            logger.warning(f"⚠️ Erreur sauvegarde erreur JSON: {log_error}")
        
        raise

# --- Ajout pour sauvegarde conversation (quick replies, etc.) ---
from typing import List, Optional
from pydantic import BaseModel
from core.conversation import save_message as save_message_supabase, get_history

class Message(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None

class ConversationPayload(BaseModel):
    company_id: str
    user_id: str
    messages: List[Message]

# --- Modèle pour l'onboarding d'entreprise ---
from pydantic import BaseModel
from typing import Optional

class OnboardCompanyRequest(BaseModel):
    company_id: Optional[str] = None
    company_name: str
    ai_name: str
    secteur_activite: str
    mission_principale: str
    objectif_final: str
    rag_enabled: bool = True
    fallback_to_human_message: str = "J'ai du mal à vous suivre. Pouvez-vous reformuler ou préférez-vous que je vous redirige vers un conseiller ?"
    ai_objective: Optional[str] = None
    # Nouveaux prompts Botlive (version 2.0)
    prompt_botlive_groq_70b: Optional[str] = None
    prompt_botlive_deepseek_v3: Optional[str] = None

class UpdateSystemPromptRequest(BaseModel):
    company_id: str
    system_prompt_template: str
    rag_enabled: bool = True

@app.post("/save_message")
async def save_message(payload: ConversationPayload):
    results = []
    for msg in payload.messages:
        try:
            await save_message_supabase(
                payload.company_id,
                payload.user_id,
                msg.role,
                msg.content
            )
            results.append({"role": msg.role, "status": "saved"})
        except Exception as e:
            results.append({"role": msg.role, "status": f"error: {str(e)}"})
    return {"status": "ok", "messages_saved": len([r for r in results if r['status']== 'saved']), "details": results}

@app.get("/health/groq")
async def groq_health():
    return groq_resilience.get_health_status()

# --- Endpoint Auto-Learning Insights ---
@app.get("/auto-learning/insights/{company_id}")
async def get_auto_learning_insights(company_id: str, days: int = 7):
    """Recupere les insights d'auto-learning pour une company."""

    try:
        from core.auto_learning_wrapper import get_company_insights
        insights = await get_company_insights(company_id, days)
        return insights
    except Exception as e:
        logger.error(f" Erreur récupération insights: {e}")
        logger.error(f" Erreur récupération insights: {e}")
        return {
            "enabled": False,
            "error": str(e),
            "company_id": company_id
        }

@app.get("/auto-learning/faq-suggestions/{company_id}")
async def get_faq_suggestions(company_id: str, min_occurrences: int = 5):
    """Genere des suggestions de FAQ a partir des questions frequentes."""

    try:
        from core.supabase_learning_engine import get_learning_engine
        engine = get_learning_engine()
        
        if not engine.supabase:
            return {"enabled": False, "error": "Supabase non disponible"}
        
        faqs = await engine.generate_faq_suggestions(company_id, min_occurrences)
        
        return {
            "enabled": True,
            "company_id": company_id,
            "total_suggestions": len(faqs),
            "faqs": faqs
        }
    except Exception as e:
        logger.error(f"❌ Erreur génération FAQ: {e}")
        return {
            "enabled": False,
            "error": str(e),
            "company_id": company_id
        }

# --- Endpoint d'onboarding d'entreprise ---
from database.supabase_client import onboard_company_to_supabase

@app.post("/onboard_company")
async def onboard_company_endpoint(req: OnboardCompanyRequest):
    """
    Endpoint pour l'onboarding d'une nouvelle entreprise.
    Gère l'insertion ou la mise à jour dans la table company_rag_configs de Supabase.
    """
    try:
        log3("[ONBOARD]", f"🚀 Début onboarding pour company_id: {req.company_id}")
        
        # Vérification des variables d'environnement
        from config import SUPABASE_URL, SUPABASE_KEY
        if not SUPABASE_URL or not SUPABASE_KEY:
            error_msg = "Configuration Supabase manquante. Vérifiez les variables d'environnement."
            log3("[ONBOARD]", f"❌ {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
            
        log3("[ONBOARD]", f"🔗 Supabase: {SUPABASE_URL}")
        log3("[ONBOARD]", f"🔑 Clé API: {'*' * 8}{SUPABASE_KEY[-4:] if SUPABASE_KEY else 'NONE'}")
        log3("[ONBOARD]", f"📋 Données reçues: {req.dict()}")
        
        try:
            # Générer un company_id s'il est manquant ou vide
            from uuid import uuid4
            effective_company_id = (req.company_id or "").strip() or uuid4().hex
            log3("[ONBOARD]", f"company_id effectif: {effective_company_id}")
            # Appel de la fonction d'insertion/mise à jour Supabase
            result = await onboard_company_to_supabase(
                company_id=effective_company_id,
                company_name=req.company_name,
                ai_name=req.ai_name,
                secteur_activite=req.secteur_activite,
                mission_principale=req.mission_principale,
                objectif_final=req.objectif_final,
                system_prompt_template=None,  # Sera géré par /update_system_prompt
                rag_enabled=req.rag_enabled,
                fallback_to_human_message=req.fallback_to_human_message,
                ai_objective=req.ai_objective,
                prompt_botlive_groq_70b=req.prompt_botlive_groq_70b,
                prompt_botlive_deepseek_v3=req.prompt_botlive_deepseek_v3
            )
            
            # Si Supabase ne renvoie rien (RLS SELECT bloqué), renvoyer un fallback non-null
            if not result:
                from datetime import datetime
                now = datetime.utcnow().isoformat()
                result = {
                    "company_id": effective_company_id,
                    "company_name": req.company_name,
                    "ai_name": req.ai_name,
                    "secteur_activite": req.secteur_activite,
                    "mission_principale": req.mission_principale,
                    "objectif_final": req.objectif_final,
                    "system_prompt_template": None,
                    "rag_enabled": req.rag_enabled,
                    "fallback_to_human_message": req.fallback_to_human_message,
                    "created_at": now,
                    "updated_at": now,
                }
                log3("[ONBOARD]", "ℹ️ Fallback data renvoyée (RLS SELECT probable)")

            log3("[ONBOARD]", f"✅ Succès - Données: {result}")
            return {
                "success": True,
                "message": f"Entreprise {req.company_name} configurée avec succès",
                "company_id": effective_company_id,
                "data": result
            }
            
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            log3("[ONBOARD]", f"❌ Erreur Supabase: {error_type} - {error_msg}")
            
            # Détails supplémentaires pour le débogage
            import traceback
            tb = traceback.format_exc()
            log3("[ONBOARD]", f"Stack trace: {tb}")
            
            # Vérifier les erreurs courantes de Supabase
            if "permission denied" in str(e).lower():
                detail = "Erreur de permission - Vérifiez les politiques RLS sur Supabase"
            elif "connection" in str(e).lower():
                detail = "Erreur de connexion à Supabase - Vérifiez l'URL et la clé API"
            else:
                detail = f"Erreur lors de la mise à jour de la base de données: {error_msg}"
        
            # Nettoyer les caractères Unicode problématiques
            clean_detail = detail.encode('ascii', 'ignore').decode('ascii')
            clean_error_msg = error_msg.encode('ascii', 'ignore').decode('ascii')
            
            raise HTTPException(
                status_code=500,
                detail=clean_detail,
                headers={
                    "X-Error-Type": error_type,
                    "X-Error-Details": clean_error_msg
                }
            )
            
    except HTTPException as http_exc:
        # On laisse passer les HTTPException telles qu'elles
        log3("[ONBOARD]", f"HTTPException: {http_exc.detail}")
        raise http_exc
        
    except Exception as e:
        # Gestion des erreurs inattendues
        error_type = type(e).__name__
        error_msg = str(e)
        log3("[ONBOARD]", f"❌ Erreur inattendue: {error_type} - {error_msg}")
        
        import traceback
        log3("[ONBOARD]", f"Stack trace: {traceback.format_exc()}")

# --- Endpoint de mise à jour du system_prompt_template ---
@app.post("/update_system_prompt")
async def update_system_prompt_endpoint(req: UpdateSystemPromptRequest):
    """
    Endpoint pour mettre à jour uniquement le system_prompt_template d'une entreprise.
    Utilisé par le workflow N8N pour injecter le prompt RAG généré.
    """
    try:
        log3("[UPDATE_PROMPT]", f"🚀 Mise à jour system_prompt pour company_id: {req.company_id}")
        
        # Vérification des variables d'environnement
        from config import SUPABASE_URL, SUPABASE_KEY
        if not SUPABASE_URL or not SUPABASE_KEY:
            error_msg = "Configuration Supabase manquante. Vérifiez les variables d'environnement."
            log3("[UPDATE_PROMPT]", f"❌ {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
        
        log3("[UPDATE_PROMPT]", f"📋 Longueur du prompt: {len(req.system_prompt_template)} caractères")
        
        try:
            # Importer la fonction Supabase
            from database.supabase_client import supabase
            
            # Mise à jour dans Supabase
            response = supabase.table("company_rag_configs").update({
                "system_prompt_template": req.system_prompt_template,
                "rag_enabled": req.rag_enabled,
                "updated_at": "now()"
            }).eq("company_id", req.company_id).execute()
            
            if not response.data:
                log3("[UPDATE_PROMPT]", f"⚠️ Aucune ligne mise à jour pour company_id: {req.company_id}")
                raise HTTPException(
                    status_code=404,
                    detail=f"Entreprise {req.company_id} non trouvée. Assurez-vous que /onboard_company a été appelé en premier."
                )
            
            log3("[UPDATE_PROMPT]", f"✅ Succès - system_prompt_template mis à jour")
            return {
                "success": True,
                "message": f"System prompt mis à jour pour {req.company_id}",
                "company_id": req.company_id,
                "prompt_length": len(req.system_prompt_template)
            }
            
        except HTTPException:
            raise
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            log3("[UPDATE_PROMPT]", f"❌ Erreur Supabase: {error_type} - {error_msg}")
            
            import traceback
            tb = traceback.format_exc()
            log3("[UPDATE_PROMPT]", f"Stack trace: {tb}")
            
            raise HTTPException(
                status_code=500,
                detail=f"Erreur lors de la mise à jour du prompt: {error_msg}"
            )
            
    except HTTPException as http_exc:
        log3("[UPDATE_PROMPT]", f"HTTPException: {http_exc.detail}")
        raise http_exc
        
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        log3("[UPDATE_PROMPT]", f"❌ Erreur inattendue: {error_type} - {error_msg}")
        
        import traceback
        log3("[UPDATE_PROMPT]", f"Stack trace: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Erreur inattendue: {error_msg}"
        )

# =====================
# Botlive: Live Mode API
# =====================

from pydantic import BaseModel

class ToggleLiveRequest(BaseModel):
    enable: bool

class ProcessOrderRequest(BaseModel):
    product_url: str
    payment_url: str
    company_id: str
    user_id: str

@app.post("/toggle-live-mode")
async def toggle_live_mode(req: ToggleLiveRequest):
    """Active/désactive le mode Live + logger dans bot_sessions."""
    try:
        from core.live_mode_manager import LiveModeManager
        from core.sessions_manager import start_session, end_session, get_active_session
        
        manager = LiveModeManager()
        
        if req.enable:
            # Activer mode LIVE
            manager.enable_live_mode()
            
            # Créer session dans bot_sessions
            session_id = await start_session(req.company_id, "live")
            
            return {
                "status": "enabled",
                "session_id": session_id
            }
        else:
            # Désactiver mode LIVE
            manager.disable_live_mode()
            
            # Terminer session active
            active_session = await get_active_session(req.company_id)
            if active_session:
                await end_session(active_session["id"], req.company_id)
            
            return {
                "status": "disabled"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"toggle-live-mode error: {e}")

@app.post("/live/process-order")
async def live_process_order(req: ProcessOrderRequest):
    """Télécharge 2 images depuis des URLs et déclenche BotliveEngine.process_live_order."""
    tmp_paths = []
    try:
        def _download(url: str) -> str:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            import os
            ext = os.path.splitext(url.split('?')[0])[1]
            if not ext or len(ext) > 5:
                ext = ".jpg"
            fd, path = tempfile.mkstemp(prefix="blv_", suffix=ext)
            with os.fdopen(fd, "wb") as f:
                f.write(r.content)
            tmp_paths.append(path)
            return path

        product_path = _download(req.product_url)
        payment_path = _download(req.payment_url)

        # Import paresseux (SINGLETON)
        from core.botlive_engine import BotliveEngine
        engine = BotliveEngine.get_instance()
        message = engine.process_live_order(product_path, payment_path)

        from uuid import uuid4
        order_id = uuid4().hex
        return {"message": message, "order_id": order_id}
    except requests.HTTPError as http_err:
        raise HTTPException(status_code=400, detail=f"Téléchargement image HTTP: {http_err}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"process-order error: {e}")
    finally:
        import os
        for p in tmp_paths:
            try:
                if p and os.path.isfile(p):
                    os.remove(p)
            except Exception:
                pass