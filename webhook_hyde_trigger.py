#!/usr/bin/env python3
"""
🎯 WEBHOOK TRIGGER AUTOMATIQUE POUR ANALYSE HYDE
Endpoint pour déclencher automatiquement l'analyse HyDE après ingestion N8N
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import asyncio
import logging
from datetime import datetime
import os

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HydeTriggerRequest(BaseModel):
    company_id: str
    trigger_source: str = "n8n_webhook"
    force_reanalysis: bool = False

class HydeTriggerResponse(BaseModel):
    success: bool
    message: str
    company_id: str
    analysis_started: bool
    timestamp: str

async def trigger_hyde_analysis(company_id: str, force_reanalysis: bool = False):
    """
    Déclenche l'analyse HyDE en arrière-plan
    """
    try:
        logger.info(f"🔥 DÉCLENCHEMENT ANALYSE HYDE AUTOMATIQUE - Company: {company_id}")
        
        # Importer la classe d'ingestion
        from ingestion_complete import HydeIngestionProcessor
        
        # Créer le processeur
        processor = HydeIngestionProcessor(company_id=company_id)
        
        # Lancer l'analyse complète
        results = await processor.run_complete_analysis()
        
        if results:
            logger.info(f"✅ ANALYSE HYDE TERMINÉE - Company: {company_id}")
            return {
                "success": True,
                "documents_analyzed": len(results.get('documents', [])),
                "word_scores_generated": len(results.get('word_scores', {})),
                "cache_saved": bool(results.get('cache_file'))
            }
        else:
            logger.warning(f"⚠️ ANALYSE HYDE SANS RÉSULTATS - Company: {company_id}")
            return {"success": False, "reason": "no_results"}
            
    except Exception as e:
        logger.error(f"❌ ERREUR ANALYSE HYDE - Company: {company_id}, Error: {e}")
        return {"success": False, "error": str(e)}

# Créer l'application FastAPI pour le webhook
webhook_app = FastAPI(title="HyDE Auto-Trigger Webhook")

@webhook_app.post("/trigger_hyde_analysis", response_model=HydeTriggerResponse)
async def webhook_trigger_hyde(
    request: HydeTriggerRequest, 
    background_tasks: BackgroundTasks
):
    """
    Webhook pour déclencher automatiquement l'analyse HyDE
    Utilisé par N8N après ingestion de documents
    """
    try:
        logger.info(f"📥 WEBHOOK REÇU - Company: {request.company_id}, Source: {request.trigger_source}")
        
        # Valider company_id
        if not request.company_id or len(request.company_id) < 10:
            raise HTTPException(
                status_code=400, 
                detail="company_id invalide ou manquant"
            )
        
        # Lancer l'analyse en arrière-plan
        background_tasks.add_task(
            trigger_hyde_analysis, 
            request.company_id, 
            request.force_reanalysis
        )
        
        response = HydeTriggerResponse(
            success=True,
            message="Analyse HyDE déclenchée avec succès",
            company_id=request.company_id,
            analysis_started=True,
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"🚀 ANALYSE HYDE LANCÉE EN ARRIÈRE-PLAN - Company: {request.company_id}")
        return response
        
    except Exception as e:
        logger.error(f"❌ ERREUR WEBHOOK - Company: {request.company_id}, Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@webhook_app.get("/health")
async def health_check():
    """Health check pour vérifier que le webhook fonctionne"""
    return {
        "status": "healthy",
        "service": "hyde_auto_trigger",
        "timestamp": datetime.now().isoformat()
    }

@webhook_app.get("/status/{company_id}")
async def get_analysis_status(company_id: str):
    """
    Vérifier le statut de l'analyse HyDE pour une entreprise
    """
    try:
        # Vérifier si le cache HyDE existe
        cache_file = f"hyde_cache_{company_id}.json"
        cache_exists = os.path.exists(cache_file)
        
        if cache_exists:
            # Lire les métadonnées du cache
            import json
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                return {
                    "company_id": company_id,
                    "cache_exists": True,
                    "word_scores_count": len(cache_data.get('word_scores', {})),
                    "last_analysis": cache_data.get('timestamp', 'unknown'),
                    "documents_analyzed": len(cache_data.get('documents', []))
                }
            except Exception as e:
                return {
                    "company_id": company_id,
                    "cache_exists": True,
                    "error": f"Erreur lecture cache: {e}"
                }
        else:
            return {
                "company_id": company_id,
                "cache_exists": False,
                "message": "Aucune analyse HyDE trouvée"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    
    # Configuration du serveur webhook
    port = int(os.environ.get("HYDE_WEBHOOK_PORT", 8001))
    host = os.environ.get("HYDE_WEBHOOK_HOST", "0.0.0.0")
    
    logger.info(f"🚀 DÉMARRAGE WEBHOOK HYDE AUTO-TRIGGER")
    logger.info(f"📡 URL: http://{host}:{port}")
    logger.info(f"🎯 Endpoint: POST /trigger_hyde_analysis")
    
    uvicorn.run(
        webhook_app, 
        host=host, 
        port=port,
        log_level="info"
    )
