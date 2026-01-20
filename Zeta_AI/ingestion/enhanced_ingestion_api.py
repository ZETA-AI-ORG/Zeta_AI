# MODIF CASCADE - suppression logique Meilisearch 2025-08-28
"""
Enhanced Ingestion API avec Mini-LLM Dispatcher intégré
Point d'entrée : Mini-LLM analyse et dispatche intelligemment vers PGVector + Meilisearch
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import logging
import os
from datetime import datetime

# Imports du projet - Structure existante respectée
from core.mini_llm_dispatcher import create_mini_llm_dispatcher, EnrichedChunk
from embedding_models import embed_text
from database.native_pgvector_client import native_client
from database.pgvector_client import upsert_company_chunks_by_chunk_id

logger = logging.getLogger(__name__)

# Router FastAPI
router = APIRouter(prefix="/enhanced-ingestion", tags=["enhanced-ingestion"])

class EnhancedIngestionRequest(BaseModel):
    company_id: str
    purge_before: Optional[bool] = False
    # Support pour les deux formats
    text_documents: Optional[List[Dict[str, Any]]] = None  # Nouveau format structuré
    
    class Config:
        extra = "allow"  # Permet d'accepter des champs supplémentaires (ancien format)

@router.post("/ingest-with-llm-dispatcher")
async def ingest_with_llm_dispatcher(request: EnhancedIngestionRequest):
    """
    Ingestion intelligente avec Mini-LLM Dispatcher
    
    Flow:
    1. Mini-LLM analyse et structure chaque document
    2. Génère expansion sémantique HYDE enrichie  
    3. Dispatche vers PGVector (tous) + Meilisearch (prioritaires)
    4. Logs détaillés de tout le processus
    """
    
    logger.info(f"[ENHANCED-INGEST] Début ingestion LLM pour company_id={request.company_id}")
    
    results = {
        "company_id": request.company_id,
        "processed_documents": 0,
        "total_chunks": 0,
        "pgvector_chunks": 0,
        "meilisearch_chunks": 0,
        "errors": []
    }
    
    try:
        # 1. Purge optionnelle
        if request.purge_before:
            await _purge_existing_data(request.company_id)
            logger.info(f"[ENHANCED-INGEST] Purge effectuée pour company_id={request.company_id}")
        
        # 2. Initialisation du Mini-LLM Dispatcher et MeiliHelper
        from database.meili_client import MeiliHelper
        helper = MeiliHelper()
        
        # Appliquer la configuration optimisée automatiquement
        helper.ensure_unified_index(request.company_id, apply_settings=True)
        logger.info(f"[ENHANCED-INGEST] Configuration Meilisearch optimisée appliquée pour company_id={request.company_id}")
        
        # 3. Initialisation du Mini-LLM Dispatcher
        # TODO: Intégrer votre client LLM (Groq, OpenAI, etc.)
        llm_client = await _get_llm_client()
        dispatcher = create_mini_llm_dispatcher(llm_client=llm_client)
        
        # 3. Traitement de chaque document via le dispatcher
        # 3. Traitement selon le format de données
        if request.text_documents:
            # Nouveau format structuré avec métadonnées
            documents_to_process = [(doc.get('file_name', f"doc_{i}"), doc.get('content', ''), doc.get('metadata', {})) 
                                  for i, doc in enumerate(request.text_documents) if doc.get('content')]
        else:
            # Ancien format clé-valeur direct
            documents = {k: v for k, v in request.dict().items() 
                        if k not in ['company_id', 'purge_before', 'text_documents'] and isinstance(v, str)}
            documents_to_process = [(doc_name, content, {}) for doc_name, content in documents.items()]
        
        all_enriched_chunks = []
        
        for doc_name, raw_content, metadata in documents_to_process:
            if not raw_content or not raw_content.strip():
                continue
                
            logger.info(f"[ENHANCED-INGEST] Traitement document '{doc_name}' ({len(raw_content)} chars)")
            
            try:
                # Le Mini-LLM fait tout le travail d'analyse et d'enrichissement
                enriched_chunks = await dispatcher.process_document(
                    raw_content=raw_content,
                    company_id=request.company_id,
                    document_type=doc_name
                )
                
                all_enriched_chunks.extend(enriched_chunks)
                results["processed_documents"] += 1
                
                logger.info(f"[ENHANCED-INGEST] Document '{doc_name}': {len(enriched_chunks)} chunks enrichis")
                
            except Exception as e:
                error_msg = f"Erreur traitement document '{doc_name}': {str(e)}"
                logger.error(f"[ENHANCED-INGEST] {error_msg}")
                results["errors"].append(error_msg)
        
        results["total_chunks"] = len(all_enriched_chunks)
        
        # 4. Dispatching vers les index selon les recommandations du Mini-LLM
        await _dispatch_to_indexes(all_enriched_chunks, request.company_id, results)
        
        logger.info(f"[ENHANCED-INGEST] Ingestion terminée: {results}")
        return results
        
    except Exception as e:
        error_msg = f"Erreur fatale ingestion: {str(e)}"
        logger.error(f"[ENHANCED-INGEST] {error_msg}")
        results["errors"].append(error_msg)
        return results

async def _get_llm_client():
    """
    Initialise le client LLM (Groq, OpenAI, etc.)
    TODO: Adapter selon votre configuration
    """
    try:
        # Utilise la configuration LLM existante de votre app.py
        from langchain_groq import ChatGroq
        
        # Utilise les mêmes variables d'environnement que votre système
        api_key = os.getenv("GROQ_API_KEY")  # Même nom que dans config.py
        if not api_key:
            logger.warning("[ENHANCED-INGEST] Pas de clé GROQ trouvée, mode fallback activé")
            return None
            
        # Utilise le même modèle que votre global_llm_hyde (plus rapide pour l'analyse)
        llm_client = ChatGroq(
            groq_api_key=api_key,
            model_name="llama-3.1-8b-instant",  # Même que votre global_llm_hyde
            temperature=0.1
        )
        
        return llm_client
        
    except Exception as e:
        logger.warning(f"[ENHANCED-INGEST] Impossible d'initialiser LLM: {e}, mode fallback")
        return None

async def _purge_existing_data(company_id: str):
    """Purge les données existantes pour cette entreprise"""
    try:
        # Purge PGVector - utilise votre native_client existant
        deleted_count = await native_client.purge_company_chunks(company_id)
        logger.info(f"[ENHANCED-INGEST] PGVector: {deleted_count} chunks supprimés")
        
                    
    except Exception as e:
        logger.error(f"[ENHANCED-INGEST] Erreur purge: {e}")


async def _dispatch_to_indexes(enriched_chunks: List[EnrichedChunk], company_id: str, results: Dict):
    """
    Dispatche les chunks enrichis vers les index selon les recommandations du Mini-LLM
    """
    
    # Séparer les chunks par destination
    pgvector_chunks = []
    
    for chunk in enriched_chunks:
        # Préparation pour PGVector
        if "pgvector" in chunk.target_indexes:
            pgvector_chunk = await _prepare_pgvector_chunk(chunk)
            pgvector_chunks.append(pgvector_chunk)

    
    # Insertion PGVector - utilise votre native_client directement
    if pgvector_chunks:
        try:
            logger.info(f"[ENHANCED-INGEST] Insertion {len(pgvector_chunks)} chunks dans PGVector")
            inserted_ids = await native_client.insert_company_chunks(company_id, pgvector_chunks, "document")
            results["pgvector_chunks"] = len(inserted_ids)
            logger.info(f"[ENHANCED-INGEST] PGVector: {len(inserted_ids)} chunks insérés")
        except Exception as e:
            error_msg = f"Erreur insertion PGVector: {str(e)}"
            logger.error(f"[ENHANCED-INGEST] {error_msg}")
            results["errors"].append(error_msg)
    
    
async def _prepare_pgvector_chunk(chunk: EnrichedChunk) -> Dict[str, Any]:
    """Prépare un chunk pour insertion dans PGVector selon votre structure existante"""
    
    # Contenu enrichi pour l'embedding
    enriched_content = chunk.content
    
    # Ajouter les expansions HYDE au contenu pour un embedding plus riche
    if chunk.hypothetical_queries:
        enriched_content += "\n\nQuestions fréquentes: " + " ".join(chunk.hypothetical_queries)
    
    if chunk.hypothetical_answers:
        enriched_content += "\n\nRéponses: " + " ".join(chunk.hypothetical_answers)
    
    # Génération de l'embedding avec votre fonction embed_text existante
    try:
        # Votre embed_text peut accepter string ou list, on utilise string
        embedding = embed_text(enriched_content)
        if hasattr(embedding, 'tolist'):
            embedding = embedding.tolist()
    except Exception as e:
        logger.error(f"[ENHANCED-INGEST] Erreur embedding: {e}")
        embedding = None
    
    # Structure compatible avec votre native_client
    return {
        "content": chunk.content,  # Contenu original pour l'affichage
        "embedding": embedding,   # Nom attendu par votre native_client
        "metadata": {
            **chunk.metadata,
            "chunk_id": chunk.chunk_id,
            "content_type": chunk.content_type.value,
            "priority": chunk.priority.value,
            "keywords": chunk.keywords,
            "synonyms": chunk.synonyms,
            "entities": chunk.entities,
            "hyde_queries": chunk.hypothetical_queries,
            "hyde_answers": chunk.hypothetical_answers,
            "data_type": "document",  # Requis par votre système
            "enriched_content": enriched_content  # Pour debug
        }
    }

# Endpoint de test pour vérifier le fonctionnement
@router.get("/test-dispatcher")
async def test_dispatcher():
    """Test rapide du Mini-LLM Dispatcher"""
    
    test_content = """
    === CASQUES MOTO ===
    
    Casque KING STAR (KS) - Noir
    Prix: 6500 FCFA
    Stock: 15 unités
    Tailles: M, L, XL
    
    Casque KING STAR (KS) - Rouge  
    Prix: 6500 FCFA
    Stock: 8 unités
    Tailles: M, L, XL
    """
    
    try:
        llm_client = await _get_llm_client()
        dispatcher = create_mini_llm_dispatcher(llm_client=llm_client)
        
        chunks = await dispatcher.process_document(
            raw_content=test_content,
            company_id="test_company",
            document_type="products_catalog"
        )
        
        return {
            "status": "success",
            "chunks_generated": len(chunks),
            "chunks_preview": [
                {
                    "content": chunk.content[:200] + "...",
                    "type": chunk.content_type.value,
                    "priority": chunk.priority.value,
                    "queries_count": len(chunk.hypothetical_queries),
                    "keywords_count": len(chunk.keywords),
                    "target_indexes": chunk.target_indexes
                }
                for chunk in chunks[:3]  # Premier 3 chunks seulement
            ]
        }
        
    except Exception as e:
        return {
            "status": "error", 
            "error": str(e)
        }
