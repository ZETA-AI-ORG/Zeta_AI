#!/usr/bin/env python3
"""
🎯 API D'INGESTION AVEC LLM HYDE
Endpoint ultra-simple pour l'utilisateur

WORKFLOW:
POST /hyde/ingest
{
  "company_id": "...",
  "raw_data": "Copier-coller n'importe quoi ici..."
}

→ LLM Hyde structure automatiquement
→ Indexation dans MeiliSearch + Supabase
→ Données parfaites ✅
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import logging

router = APIRouter(prefix="/hyde", tags=["llm-hyde-ingestion"])

class HydeIngestRequest(BaseModel):
    """Request ultra-simple pour l'utilisateur"""
    company_id: str
    raw_data: str
    purge_before: Optional[bool] = True  # Supprimer données existantes

class HydeIngestResponse(BaseModel):
    """Response avec stats"""
    success: bool
    documents_created: int
    documents_indexed: int
    structured_data: Optional[dict] = None
    message: str

@router.post("/ingest", response_model=HydeIngestResponse)
async def hyde_ingest(request: HydeIngestRequest):
    """
    🎯 ENDPOINT PRINCIPAL - INGESTION INTELLIGENTE
    
    L'utilisateur envoie données brutes, le système fait tout le reste.
    
    Exemples de données brutes acceptées:
    - Email copié-collé
    - Message WhatsApp
    - Document Word
    - Tableau Excel (texte)
    - N'importe quoi !
    """
    
    try:
        print(f"\n🚀 HYDE INGESTION - Company: {request.company_id}")
        print(f"📝 Données brutes: {len(request.raw_data)} caractères")
        
        # 1. Initialiser LLM client
        from core.llm_client import get_groq_llm_client
        llm_client = get_groq_llm_client()
        
        # 2. Initialiser LLM Hyde
        from core.llm_hyde_ingestion import get_llm_hyde_ingestion
        hyde = get_llm_hyde_ingestion(llm_client)
        
        # 3. Pipeline complet: raw → structured → documents
        documents = await hyde.process_raw_ingestion(request.raw_data, request.company_id)
        
        if not documents:
            return HydeIngestResponse(
                success=False,
                documents_created=0,
                documents_indexed=0,
                message="Aucun document créé. Vérifiez les données brutes."
            )
        
        # 4. Supprimer index existant si demandé
        if request.purge_before:
            try:
                import meilisearch
                meili_client = meilisearch.Client(
                    os.environ.get("MEILI_URL", "http://127.0.0.1:7700"),
                    os.environ.get("MEILI_API_KEY", "")
                )
                
                index_name = f"company_docs_{request.company_id}"
                meili_client.delete_index(index_name)
                print(f"🗑️ Index {index_name} supprimé")
            except Exception as e:
                print(f"⚠️ Erreur suppression index: {e}")
        
        # 5. Indexation MeiliSearch
        print(f"\n📤 Indexation dans MeiliSearch...")
        
        import meilisearch
        meili_client = meilisearch.Client(
            os.environ.get("MEILI_URL", "http://127.0.0.1:7700"),
            os.environ.get("MEILI_API_KEY", "")
        )
        
        index_name = f"company_docs_{request.company_id}"
        
        try:
            meili_client.create_index(index_name, {"primaryKey": "id"})
        except:
            pass  # Index existe déjà
        
        # Indexer
        resp = meili_client.index(index_name).add_documents(documents)
        print(f"✅ {len(documents)} documents indexés dans MeiliSearch")
        
        # 6. TODO: Indexation Supabase (avec embeddings)
        print(f"⏳ Indexation Supabase (TODO)")
        
        return HydeIngestResponse(
            success=True,
            documents_created=len(documents),
            documents_indexed=len(documents),
            message=f"✅ {len(documents)} documents créés et indexés avec succès"
        )
        
    except Exception as e:
        logging.exception("[HYDE][INGESTION][ERROR]")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test")
async def hyde_test(request: HydeIngestRequest):
    """
    🧪 ENDPOINT DE TEST
    
    Teste la structuration sans indexer.
    Retourne les données structurées pour inspection.
    """
    
    try:
        print(f"\n🧪 HYDE TEST - Company: {request.company_id}")
        
        # Initialiser
        from core.llm_client import get_groq_llm_client
        from core.llm_hyde_ingestion import get_llm_hyde_ingestion
        
        llm_client = get_groq_llm_client()
        hyde = get_llm_hyde_ingestion(llm_client)
        
        # Structure seulement
        structured_data = await hyde.structure_raw_data(request.raw_data, request.company_id)
        
        # Générer documents
        documents = hyde.structured_to_documents(structured_data, request.company_id)
        
        return {
            "success": True,
            "structured_data": structured_data,
            "documents_preview": documents[:5],  # Premiers 5
            "total_documents": len(documents),
            "message": "✅ Structuration réussie (pas d'indexation)"
        }
        
    except Exception as e:
        logging.exception("[HYDE][TEST][ERROR]")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/{company_id}")
async def hyde_stats(company_id: str):
    """
    📊 STATS DE L'INDEX
    
    Retourne stats MeiliSearch pour une company
    """
    
    try:
        import meilisearch
        meili_client = meilisearch.Client(
            os.environ.get("MEILI_URL", "http://127.0.0.1:7700"),
            os.environ.get("MEILI_API_KEY", "")
        )
        
        index_name = f"company_docs_{company_id}"
        stats = meili_client.index(index_name).get_stats()
        
        return {
            "success": True,
            "company_id": company_id,
            "index_name": index_name,
            "stats": stats
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
