"""
🚀 ROUTES ENHANCED - NOUVEAUX ENDPOINTS
À ajouter dans app.py - endpoints parallèles
"""

# AJOUTER CES IMPORTS AU DÉBUT DE APP.PY (après les imports existants)
"""
# 🚀 IMPORTS ENHANCED - À ajouter dans app.py
from core.enhanced_rag_integration import enhanced_rag
from routes.streaming import router as streaming_router
from routes.dashboard import router as dashboard_router
from core.apm_monitoring import apm_monitor
from core.unified_cache_pro import unified_cache
from core.connection_manager_pro import connection_manager
"""

# AJOUTER CES ROUTES DANS APP.PY (après les routes existantes)
enhanced_routes_code = '''
# 🚀 ENHANCED ROUTES - NOUVEAUX ENDPOINTS PARALLÈLES

# Inclure les nouveaux routers
app.include_router(streaming_router, prefix="/api", tags=["streaming"])
app.include_router(dashboard_router, prefix="/api", tags=["dashboard"])

@app.post("/api/chat/enhanced")
@limiter.limit("30/minute")
async def chat_enhanced(request: Request, chat_request: ChatRequest):
    """
    🚀 ENDPOINT CHAT ENHANCED
    - Tous les systèmes d'optimisation activés
    - Cache intelligent
    - Monitoring APM
    - Optimisation tokens
    - Parallèle à l'endpoint existant
    """
    
    try:
        # Validation sécurité (même que l'original)
        validation_result = validate_user_prompt(chat_request.message)
        if validation_result['severity'] != 'LOW':
            logger.warning(f"[SECURITY_ENHANCED] Requête bloquée: {validation_result}")
            raise HTTPException(
                status_code=400,
                detail=f"🛡️ Demande non autorisée pour des raisons de sécurité: {validation_result['reason']}"
            )
        
        # Traitement enhanced
        response = await enhanced_rag.process_request_enhanced(
            message=chat_request.message,
            user_id=chat_request.user_id,
            company_id=chat_request.company_id,
            conversation_id=chat_request.conversation_id
        )
        
        return {
            "response": response['response'],
            "request_id": response['request_id'],
            "processing_time_ms": response['processing_time_ms'],
            "source": response['source'],
            "enhanced": True,
            "cached": response.get('cached', False),
            "quality_score": response.get('quality_score', 0),
            "token_optimization": response.get('token_optimization', {}),
            "timestamp": time.time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CHAT_ENHANCED] Erreur: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur enhanced: {str(e)}")

@app.get("/api/system/stats")
async def get_system_stats():
    """
    📊 STATISTIQUES SYSTÈME ENHANCED
    - Métriques APM
    - Stats cache
    - Performance connexions
    """
    
    try:
        # Récupérer toutes les stats
        apm_stats = apm_monitor.get_real_time_stats()
        cache_stats = unified_cache.get_stats()
        connection_stats = connection_manager.get_connection_stats()
        
        return {
            "apm": apm_stats,
            "cache": cache_stats,
            "connections": connection_stats,
            "timestamp": time.time(),
            "status": "healthy"
        }
        
    except Exception as e:
        logger.error(f"[SYSTEM_STATS] Erreur: {e}")
        return {
            "error": str(e),
            "timestamp": time.time(),
            "status": "error"
        }

@app.post("/api/cache/clear")
async def clear_cache(company_id: str = None):
    """
    🧹 NETTOYAGE CACHE
    - Vide le cache intelligent
    - Par entreprise ou global
    """
    
    try:
        if company_id:
            # TODO: Implémenter clear par company
            cleared_entries = await unified_cache.clear_expired()
        else:
            # Clear global
            cleared_entries = await unified_cache.clear_expired()
        
        return {
            "message": f"Cache nettoyé: {cleared_entries} entrées supprimées",
            "company_id": company_id,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"[CACHE_CLEAR] Erreur: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur nettoyage cache: {str(e)}")

@app.on_event("startup")
async def startup_enhanced():
    """
    🚀 STARTUP ENHANCED
    - Initialise tous les nouveaux systèmes
    - À ajouter après le startup existant
    """
    
    logger.info("🚀 Initialisation des systèmes enhanced...")
    
    try:
        # Initialiser le gestionnaire de connexions
        await connection_manager.initialize()
        logger.info("✅ Connection manager initialisé")
        
        # Le cache et l'APM se lancent automatiquement
        logger.info("✅ Tous les systèmes enhanced prêts")
        
    except Exception as e:
        logger.error(f"❌ Erreur startup enhanced: {e}")

@app.on_event("shutdown")
async def shutdown_enhanced():
    """
    🧹 SHUTDOWN ENHANCED
    - Nettoie tous les nouveaux systèmes
    - À ajouter après le shutdown existant
    """
    
    logger.info("🧹 Arrêt des systèmes enhanced...")
    
    try:
        # Arrêter le monitoring
        apm_monitor.stop_monitoring()
        
        # Fermer les connexions
        await connection_manager.cleanup()
        
        logger.info("✅ Systèmes enhanced arrêtés proprement")
        
    except Exception as e:
        logger.error(f"❌ Erreur shutdown enhanced: {e}")
'''

print("📋 CODE À AJOUTER DANS APP.PY:")
print("="*50)
print("\n1. IMPORTS À AJOUTER AU DÉBUT:")
print("-"*30)
print("""
# 🚀 IMPORTS ENHANCED
from core.enhanced_rag_integration import enhanced_rag
from routes.streaming import router as streaming_router
from routes.dashboard import router as dashboard_router
from core.apm_monitoring import apm_monitor
from core.unified_cache_pro import unified_cache
from core.connection_manager_pro import connection_manager
""")

print("\n2. ROUTES À AJOUTER APRÈS LES ROUTES EXISTANTES:")
print("-"*30)
print(enhanced_routes_code)

print("\n3. MODIFICATION DU STARTUP EXISTANT:")
print("-"*30)
print("""
# Dans la fonction startup_event() existante, ajouter:
try:
    await connection_manager.initialize()
    logger.info("✅ Systèmes enhanced initialisés")
except Exception as e:
    logger.error(f"❌ Erreur enhanced startup: {e}")
""")

print("\n4. MODIFICATION DU SHUTDOWN EXISTANT:")
print("-"*30)
print("""
# Dans la fonction shutdown_event() existante, ajouter:
try:
    apm_monitor.stop_monitoring()
    await connection_manager.cleanup()
    logger.info("✅ Systèmes enhanced arrêtés")
except Exception as e:
    logger.error(f"❌ Erreur enhanced shutdown: {e}")
""")

print("\n" + "="*50)
print("🎯 ENDPOINTS DISPONIBLES APRÈS INTÉGRATION:")
print("- POST /api/chat/enhanced - Chat avec optimisations")
print("- POST /api/chat/stream - Chat streaming temps réel")  
print("- GET /api/dashboard - Dashboard monitoring")
print("- GET /api/dashboard/api/metrics - API métriques")
print("- GET /api/system/stats - Statistiques système")
print("- POST /api/cache/clear - Nettoyage cache")
print("- GET /api/dashboard/health - Health check")
print("="*50)




