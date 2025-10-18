#!/usr/bin/env python3
"""
🚀 API MULTI-INDEX RAG
Architecture RAG multi-index avec recherche hybride optimisée
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import asyncio
import time
import logging
from utils import log3

# Import des composants RAG
from core.universal_rag_engine import get_universal_rag_response

router = APIRouter(prefix="/multi-index", tags=["Multi-Index RAG"])

class MultiIndexQuery(BaseModel):
    """Modèle de requête multi-index"""
    query: str
    company_id: str
    user_id: str
    company_name: Optional[str] = None
    target_indexes: Optional[List[str]] = None
    search_method: Optional[str] = "hybrid"  # hybrid, meili_only, supabase_only

class MultiIndexResponse(BaseModel):
    """Réponse multi-index"""
    response: str
    confidence: float
    documents_found: bool
    processing_time_ms: float
    search_method: str
    context_used: str
    success: bool

class IndexSearchRequest(BaseModel):
    """Requête de recherche sur un index spécifique"""
    query: str
    limit: Optional[int] = 10

@router.post("/search", response_model=MultiIndexResponse)
async def multi_index_search(query: MultiIndexQuery):
    """
    🔍 Recherche RAG multi-index optimisée
    
    Utilise l'architecture séquentielle :
    1. MeiliSearch prioritaire (mots-clés)
    2. Supabase fallback (sémantique)
    3. Mémoire conversationnelle
    4. Cache intelligent
    """
    try:
        start_time = time.time()
        
        log3("[MULTI_INDEX_API]", {
            "action": "search_start",
            "query_preview": query.query[:50],
            "company_id": query.company_id[:12],
            "user_id": query.user_id[:12],
            "search_method": query.search_method
        })
        
        # Appel du RAG engine universel
        result = await get_universal_rag_response(
            message=query.query,
            company_id=query.company_id,
            user_id=query.user_id,
            company_name=query.company_name
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        log3("[MULTI_INDEX_API]", {
            "action": "search_complete",
            "success": result.get("success", True),
            "processing_time_ms": processing_time,
            "response_length": len(result.get("response", "")),
            "documents_found": result.get("documents_found", False)
        })
        
        return MultiIndexResponse(
            response=result.get("response", ""),
            confidence=result.get("confidence", 0.0),
            documents_found=result.get("documents_found", False),
            processing_time_ms=processing_time,
            search_method=result.get("search_method", "unknown"),
            context_used=result.get("context_used", ""),
            success=result.get("success", True)
        )
        
    except Exception as e:
        log3("[MULTI_INDEX_API]", {
            "action": "search_error",
            "error": str(e),
            "query_preview": query.query[:50]
        })
        
        raise HTTPException(
            status_code=500,
            detail=f"Erreur recherche multi-index: {str(e)}"
        )

@router.post("/search/index/{index_name}/{company_id}")
async def search_specific_index(
    index_name: str,
    company_id: str,
    request: IndexSearchRequest
):
    """
    🎯 Recherche sur un index spécifique
    """
    try:
        from core.multi_index_search_engine import MultiIndexSearchEngine
        
        search_engine = MultiIndexSearchEngine()
        results = await search_engine.search_single_index(
            index_name=index_name,
            company_id=company_id,
            query=request.query,
            limit=request.limit
        )
        
        # Formatage des résultats
        formatted_results = []
        for result in results.get("hits", []):
            formatted_results.append({
                "content": result.get("searchable_text", ""),
                "score": result.get("_score", 0),
                "metadata": {
                    k: v for k, v in result.items() 
                    if k not in ["searchable_text", "_score"]
                }
            })
        
        return {
            "results": formatted_results,
            "total_hits": len(formatted_results),
            "index": index_name,
            "processing_time": results.get("processing_time", 0),
            "query": request.query
        }
        
    except Exception as e:
        logging.exception(f"[INDEX_SEARCH][ERREUR] {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur recherche index {index_name}: {str(e)}"
        )

@router.get("/indexes/status/{company_id}")
async def get_indexes_status(company_id: str):
    """
    📊 Vérifier le statut des index MeiliSearch pour une entreprise
    """
    try:
        import os
        import meilisearch
        
        meili_client = meilisearch.Client(
            os.environ.get("MEILI_URL", "http://127.0.0.1:7700"), 
            os.environ.get("MEILI_API_KEY") or os.environ.get("MEILI_MASTER_KEY", "")
        )
        
        indexes_status = {}
        index_names = ["products", "delivery", "support_paiement", "localisation", "company_docs"]
        
        for index_name in index_names:
            index_uid = f"{index_name}_{company_id}"
            try:
                index = meili_client.index(index_uid)
                stats = index.get_stats()
                
                indexes_status[index_name] = {
                    "exists": True,
                    "documents_count": stats.get("numberOfDocuments", 0),
                    "is_indexing": stats.get("isIndexing", False),
                    "field_distribution": stats.get("fieldDistribution", {})
                }
            except Exception as e:
                indexes_status[index_name] = {
                    "exists": False,
                    "error": str(e)
                }
        
        return {
            "company_id": company_id,
            "indexes": indexes_status,
            "total_documents": sum(
                idx.get("documents_count", 0) 
                for idx in indexes_status.values() 
                if idx.get("exists", False)
            )
        }
        
    except Exception as e:
        logging.exception(f"[INDEX_STATUS][ERREUR] {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur vérification index: {str(e)}"
        )

@router.get("/health")
async def health_check():
    """🏥 Vérification santé API multi-index"""
    try:
        # Test rapide du système
        test_result = await get_universal_rag_response(
            message="test",
            company_id="health_check",
            user_id="health_check",
            company_name="Test"
        )
        
        return {
            "status": "healthy",
            "message": "API multi-index opérationnelle",
            "test_success": test_result.get("success", False),
            "features": [
                "multi_index_search",
                "searchable_text_priority", 
                "hyde_scoring",
                "smart_routing",
                "index_specific_search",
                "conversational_memory",
                "intelligent_caching"
            ],
            "timestamp": time.time()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Erreur: {str(e)}",
            "timestamp": time.time()
        }

@router.get("/stats")
async def get_stats():
    """📊 Statistiques de l'API multi-index"""
    try:
        # Récupérer les stats des caches
        from core.unified_cache_system import get_unified_cache_system
        cache_system = get_unified_cache_system()
        cache_stats = cache_system.get_global_stats()
        
        return {
            "status": "success",
            "cache_stats": cache_stats,
            "api_info": {
                "name": "Multi-Index RAG API",
                "version": "1.0.0",
                "architecture": "Sequential (MeiliSearch → Supabase)",
                "features": [
                    "Mémoire conversationnelle optimisée",
                    "Cache multi-niveaux",
                    "Recherche hybride",
                    "Fallback intelligent",
                    "Index spécialisés",
                    "Routing intelligent"
                ]
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur récupération stats: {str(e)}"
        )
