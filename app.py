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

# ========== OPTIMISATION PERFORMANCE ==========
from config_performance import (
    configure_performance_logs,
    ENVIRONMENT,
    HYDE_SKIP_SIMPLE_QUERIES,
    MAX_HISTORY_MESSAGES,
    MAX_HISTORY_CHARS
)

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

from core.models import ChatRequest
from FIX_CONTEXT_LOSS_COMPLETE import build_smart_context_summary, extract_from_last_exchanges
from pydantic import BaseModel
from core.universal_rag_engine import get_universal_rag_response
from core.prompt_manager import PromptManager
from database.supabase_client import get_company_system_prompt, search_supabase_semantic, get_supabase_client
from ingestion.ingestion_api import router as ingestion_router
from core.global_embedding_cache import initialize_global_cache, cleanup_global_cache
from routes.auth import router as auth_router
from routes import auth, messenger
from meili_ingest_api import router as meili_router
# from routes.rag import router as rag_router  # SUPPRIMÉ - fichier obsolète
from routes.meili import router as meili_explorer_router
app.include_router(meili_explorer_router, prefix="/meili")
from utils import log3, groq_resilience
from core.security_validator import validate_user_prompt
from core.hallucination_guard import check_ai_response
from core.error_handler import safe_api_call, global_error_handler
from core.circuit_breaker import groq_circuit_breaker, supabase_circuit_breaker, meilisearch_circuit_breaker
import traceback

# --- Image search API ---
from api.image_search import router as image_search_router


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
# NOTE: Removed duplicate include of meili_explorer_router; it is already mounted at prefix /meili above
app.include_router(ingestion_router)
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(image_search_router)

# 🚀 NOUVEAU: Monitoring des caches optimisés
try:
    from routes.cache_monitoring import router as cache_monitoring_router
    app.include_router(cache_monitoring_router, prefix="/api", tags=["Cache Monitoring"])
    logger.info("🚀 Monitoring des caches intégré avec succès")
except Exception as e:
    logger.warning(f"⚠️ Erreur intégration monitoring caches: {e}")

# NOUVEAU: Intégration du Mini-LLM Dispatcher
try:
    from ingestion.enhanced_ingestion_api import router as enhanced_ingestion_router
    app.include_router(enhanced_ingestion_router, tags=["Enhanced-Ingestion"])
    logger.info("Router Enhanced Ingestion avec Mini-LLM Dispatcher monté avec succès")
except Exception as e:
    logger.warning(f"Impossible de monter le router Enhanced Ingestion: {e}")

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
    1. Limite aux 5 derniers échanges (10 messages max)
    2. Remplace 'assistant:' par 'IA:'
    3. Supprime les doublons consécutifs
    """
    if not history:
        return ""
    
    # Remplacer "assistant:" par "IA:"
    history = history.replace('assistant:', 'IA:')
    
    lines = [line.strip() for line in history.split('\n') if line.strip()]
    
    # Filtrer uniquement les messages user/IA
    messages = [line for line in lines if line.startswith('user:') or line.startswith('IA:')]
    
    # Limiter aux 10 derniers messages (5 échanges user/IA)
    if len(messages) > 10:
        messages = messages[-10:]
        print(f"[HISTORIQUE] ✂️ Tronqué: {len(lines)} → 10 messages (5 échanges)")
    
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
    # DÉDUPLICATION HISTORIQUE (évite pollution tokens)
    # ═══════════════════════════════════════════════════════════════
    conversation_history = deduplicate_conversation_history(conversation_history)
    try:
        # ═══════════════════════════════════════════════════════════════
        # ÉTAPE 0: UTILISER LES PROMPTS HARDCODÉS (PRIORITÉ)
        # ═══════════════════════════════════════════════════════════════
        print(f"[BOTLIVE][PROMPT] 🔧 UTILISATION PROMPTS HARDCODÉS (MODE TEST)")
        
        # Utiliser les prompts hardcodés au lieu de Supabase
        from core.botlive_prompts_hardcoded import GROQ_70B_PROMPT, DEEPSEEK_V3_PROMPT
        botlive_prompt_template = DEEPSEEK_V3_PROMPT  # Par défaut DeepSeek V3
        print(f"[BOTLIVE][PROMPT] ✅ Prompt hardcodé chargé ({len(botlive_prompt_template)} chars)")
        
        # ═══════════════════════════════════════════════════════════════
        # INITIALISATION DES VARIABLES (portée globale fonction)
        # ═══════════════════════════════════════════════════════════════
        detected_objects = []
        detected_type = "unknown"
        confidence = 0.0
        raw_text = ""
        
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
                
                # 2. Analyser avec BotliveEngine (YOLOv9 + EasyOCR)
                try:
                    from core.botlive_engine import BotliveEngine
                    botlive_engine = BotliveEngine()
                    # Utiliser les méthodes disponibles: detect_product et verify_payment sur la même image
                    product = botlive_engine.detect_product(temp_file_path) or {}
                    payment = botlive_engine.verify_payment(temp_file_path) or {}

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
        # ÉTAPE 2: FILTRAGE DES TRANSACTIONS (si OCR disponible)
        # ═══════════════════════════════════════════════════════════════
        filtered_transactions = []
        company_phone = ""
        
        # Numéro Wave entreprise (hardcodé car prompt ne le contient plus)
        company_phone = "0787360757"  # Rue du Grossiste
        print(f"[BOTLIVE][FILTER] Numéro entreprise: {company_phone}")
        
        try:
                
                # Parser l'OCR pour trouver les transactions
                if raw_text:
                    lines = raw_text.split('\n')
                    for i, line in enumerate(lines):
                        if company_phone in line.replace(" ", ""):
                            transaction_context = []
                            if i > 0:
                                transaction_context.append(lines[i-1].strip())
                            transaction_context.append(line.strip())
                            if i < len(lines) - 1:
                                transaction_context.append(lines[i+1].strip())
                            if i < len(lines) - 2:
                                transaction_context.append(lines[i+2].strip())
                            
                            transaction_text = " ".join(transaction_context)
                            amount_pattern = r"(\d{1,6}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*F"
                            amount_match = re.search(amount_pattern, transaction_text)
                            if amount_match:
                                raw_amount = amount_match.group(1)
                                # Normalisation: décimales vs milliers
                                if re.match(r"^\d+[.,]\d{2}$", raw_amount):
                                    amount = raw_amount.split('.')[0].split(',')[0]
                                elif re.match(r"^\d+[.,]\d{3}", raw_amount):
                                    amount = raw_amount.replace(",", "").replace(".", "")
                                else:
                                    amount = raw_amount
                                filtered_transactions.append({
                                    "amount": amount,
                                    "context": " | ".join(transaction_context),
                                    "phone": company_phone
                                })
                                print(f"[BOTLIVE][FILTER] Transaction: {amount}F vers {company_phone}")
        except Exception as filter_e:
            print(f"[BOTLIVE][FILTER][ERROR] {filter_e}")
        
        # ═══════════════════════════════════════════════════════════════
        # ÉTAPE 3: APPEL LLM CONVERSATIONNEL (toujours, avec ou sans image)
        # ═══════════════════════════════════════════════════════════════
        # Extraction acompte depuis le prompt
        expected_deposit = "2000 FCFA"
        try:
            pattern = r"acompte\s+(\d{1,5})\s*(fcfa|f\s*cfa|xof|cfa)\s*minimum"
            m = re.search(pattern, botlive_prompt_template, re.IGNORECASE)
            if m:
                expected_deposit = f"{m.group(1)} {m.group(2).upper()}"
        except:
            pass
        
        # Préparer les variables pour le prompt
        question_text = message or ""
        history_text = conversation_history
        context_text = ""
        
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
        print(f"   expected_deposit = {expected_deposit}")
        print("="*80 + "\n")
        
        # ═══════════════════════════════════════════════════════════════
        # SYSTÈME: UTILISER UNIQUEMENT LE PROMPT SUPABASE
        # ═══════════════════════════════════════════════════════════════
        try:
            # NE PLUS UTILISER update_botlive_prompt.get_prompt() - UTILISER SUPABASE UNIQUEMENT
            print(f"🔧 [PROMPT MODE] SUPABASE DIRECT")
            
            # Préparer les variables pour formatage
            detected_objects_str = ", ".join(detected_objects) if detected_objects else "[AUCUN OBJET DÉTECTÉ]"
            filtered_transactions_str = ", ".join([
                f"{t.get('amount','?')}F -> +225{t.get('phone','????')}" for t in (filtered_transactions or [])
            ]) or "[AUCUNE TRANSACTION VALIDE]"
            
            # DEBUG: Vérifier les transactions avant formatage
            print(f"🔍 [DEBUG] filtered_transactions = {filtered_transactions}")
            print(f"🔍 [DEBUG] filtered_transactions_str = {filtered_transactions_str}")
            
            # Formater le prompt Supabase directement avec gestion d'erreur
            try:
                formatted_prompt = botlive_prompt_template.format(
                    question=question_text or "",
                    conversation_history=history_text or "",
                    detected_objects=detected_objects_str,
                    filtered_transactions=filtered_transactions_str,
                    expected_deposit=str(expected_deposit or "2000 FCFA")
                )
            except KeyError as ke:
                print(f"⚠️ [PROMPT] Variable manquante dans template: {ke}")
                # Fallback: remplacer manuellement
                formatted_prompt = botlive_prompt_template
                formatted_prompt = formatted_prompt.replace("{question}", question_text or "")
                formatted_prompt = formatted_prompt.replace("{conversation_history}", history_text or "")
                formatted_prompt = formatted_prompt.replace("{detected_objects}", detected_objects_str)
                formatted_prompt = formatted_prompt.replace("{filtered_transactions}", filtered_transactions_str)
                formatted_prompt = formatted_prompt.replace("{expected_deposit}", str(expected_deposit or "2000 FCFA"))
            
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
                "filtered_transactions": "; ".join([
                    f"{t.get('amount','?')}F -> +225{t.get('phone','????')}" for t in (filtered_transactions or [])
                ]) or "[AUCUNE TRANSACTION VALIDE]",
                "expected_deposit": str(expected_deposit or "2000 FCFA"),
                "context": context_text or "",
                "history": history_text or "",
                "question": question_text or "",
                "conversation_history": history_text or "",
            }
            formatted_prompt = botlive_prompt_template.format(**safe_vars)
        except Exception as e:
            # Autre erreur
            print(f"[BOTLIVE][ERROR] Formatage prompt failed: {e}")
            formatted_prompt = f"{botlive_prompt_template}\n\nClient: {question_text}\nHistorique: {history_text[:500]}"
        
        # ═══════════════════════════════════════════════════════════════
        # LOG : Vérifier que les variables sont bien dans le prompt
        # ═══════════════════════════════════════════════════════════════
        print("\n🔍 [BOTLIVE][PROMPT FORMATÉ] Vérification injection variables:")
        if "{detected_objects}" in formatted_prompt:
            print("   ❌ ERREUR: {detected_objects} NON REMPLACÉ dans le prompt !")
        else:
            print("   ✅ {detected_objects} remplacé")
        
        if "{expected_deposit}" in formatted_prompt:
            print("   ❌ ERREUR: {expected_deposit} NON REMPLACÉ dans le prompt !")
        else:
            print("   ✅ {expected_deposit} remplacé")
        
        # Afficher un extrait du prompt formaté
        print(f"\n📄 [PROMPT EXTRAIT] (500 premiers chars):\n{formatted_prompt[:500]}...\n")
        
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
        
        # Appel LLM
        try:
            import re  # Import nécessaire pour l'extraction
            import os  # Import nécessaire pour getenv
            from core.llm_health_check import complete as generate_response
            # Utiliser le modèle Groq défini dans l'env, sinon défaut 70B versatile
            groq_model = os.getenv("DEFAULT_LLM_MODEL", "llama-3.3-70b-versatile")
            llm_text, token_usage = await generate_response(
                formatted_prompt,
                model_name=groq_model,
                max_tokens=1000,  # ✅ Augmenté pour permettre thinking + response
                temperature=0.7
            )
            
            # ═══════════════════════════════════════════════════════════════
            # LOGS COLORÉS POUR SUIVI
            # ═══════════════════════════════════════════════════════════════
            
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
            
            # 🟡 THINKING LLM (JAUNE)
            if thinking_match:
                thinking_content = thinking_match.group(1).strip()
                print(f"\n\033[93m🟡 RAISONNEMENT LLM:\033[0m")
                print(f"\033[93m{thinking_content}\033[0m")
            else:
                print(f"\n\033[93m🟡 RAISONNEMENT LLM: [Pas de balise <thinking>]\033[0m")
            
            # 🟢 RÉPONSE CLIENT (VERT)
            if response_match:
                client_response = response_match.group(1).strip()
                print(f"\n\033[92m🟢 RÉPONSE AU CLIENT:\033[0m")
                print(f"\033[92m{client_response}\033[0m")
            else:
                # Pas de balises → retourner texte brut
                client_response = llm_text.strip()
                print(f"\n\033[92m🟢 RÉPONSE AU CLIENT (sans balise):\033[0m")
                print(f"\033[92m{client_response}\033[0m")
            
            # 🔴 TOKENS + PROVIDER UTILISÉ
            prompt_tokens = token_usage.get("prompt_tokens", 0)
            completion_tokens = token_usage.get("completion_tokens", 0)
            total_tokens = token_usage.get("total_tokens", 0)
            provider = token_usage.get("provider", "groq")
            fallback_used = token_usage.get("fallback_used", False)
            health_check = token_usage.get("health_check", False)
            model_used = token_usage.get("model", groq_model)
            
            if provider == "groq":
                # Calcul coût Groq llama-3.3-70b-versatile (tarifs officiels)
                input_cost = prompt_tokens * 0.00000059  # $0.59/1M tokens
                output_cost = completion_tokens * 0.00000079  # $0.79/1M tokens
                total_cost = input_cost + output_cost
                
                health_status = "✅ Health Check OK" if health_check else "⚠️ Direct"
                print(f"\n\033[91m🔴 TOKENS RÉELS GROQ ({health_status}):\033[0m")
                print(f"\033[91mPrompt: {prompt_tokens} | Completion: {completion_tokens} | TOTAL: {total_tokens}\033[0m")
                print(f"\033[91m💰 COÛT: ${total_cost:.6f} (${input_cost:.6f} input + ${output_cost:.6f} output)\033[0m")
                print(f"\033[91m🤖 MODÈLE: {model_used}\033[0m")
            
            elif provider == "deepseek":
                estimated = " (estimé)" if token_usage.get('estimated') else ""
                health_reason = "🚫 Groq Unhealthy" if health_check else "🔄 Fallback"
                print(f"\n\033[93m🟡 TOKENS DEEPSEEK ({health_reason}):\033[0m")
                print(f"\033[93mPrompt: {prompt_tokens} | Completion: {completion_tokens} | TOTAL: {total_tokens}{estimated}\033[0m")
                print(f"\033[93m💰 COÛT: ~$0.000001 (DeepSeek gratuit)\033[0m")
                print(f"\033[93m🤖 MODÈLE: {model_used}\033[0m")
            
            elif provider == "emergency":
                print(f"\n\033[95m🆘 RÉPONSE D'URGENCE:\033[0m")
                print(f"\033[95mErreur: {token_usage.get('error', 'Unknown')}\033[0m")
                print(f"\033[95m💰 COÛT: $0.000000\033[0m")
                print(f"\033[95m🤖 MODÈLE: emergency\033[0m")
            
            print("="*80 + "\n")
            
            return client_response
        except Exception as e:
            print(f"[BOTLIVE][LLM] Erreur: {e}")
            import traceback
            traceback.print_exc()
            return "Bonjour ! 👋 Envoyez-moi la photo du produit que vous voulez commander."
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
    # ═════════════════════════════════════════════════════════════
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
    use_botlive = req.botlive_enabled
    
    if use_botlive:
        # 🚀 NOUVEAU SYSTÈME HYBRIDE DEEPSEEK V3 + GROQ 70B
        try:
            from core.botlive_rag_hybrid import botlive_hybrid
            from database.supabase_client import get_botlive_prompt
            
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
            hybrid_result = await botlive_hybrid.process_request(
                user_id=req.user_id,
                message=req.message or "",
                context=context,
                conversation_history=conversation_history
            )
            
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
            print(f"❌ [HYBRID] Erreur système hybride: {hybrid_error}")
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
                        from core.conversation_notepad import get_conversation_notepad
                        notepad = get_conversation_notepad()
                        
                        for key, value in extracted.items():
                            if key == 'produit':
                                notepad.add_product(value, req.user_id, req.company_id)
                            elif key in ['zone', 'frais_livraison', 'telephone', 'paiement', 'acompte', 'prix_produit', 'total']:
                                notepad.add_info(key, value, req.user_id, req.company_id)
                        
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
        final_response = {
            "response": response, 
            "cached": False,
            "security_score": security_check.risk_level,
            "hallucination_score": hallucination_check.confidence_score
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
            response_text = response.get("response", str(response)) if isinstance(response, dict) else str(response)
            
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
                response=response_text,
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
            clean_detail = detail.replace("'", "'").replace(""", '"').replace(""", '"')
            clean_error_msg = error_msg.replace("'", "'").replace(""", '"').replace(""", '"')
            
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
def toggle_live_mode(req: ToggleLiveRequest):
    """Active/désactive le mode Live via LiveModeManager."""
    try:
        from core.live_mode_manager import LiveModeManager
        manager = LiveModeManager()
        if req.enable:
            manager.enable_live_mode()
            status = "enabled"
        else:
            manager.disable_live_mode()
            status = "disabled"
        return {"status": status}
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

        # Import paresseux
        from core.botlive_engine import BotliveEngine
        engine = BotliveEngine()
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