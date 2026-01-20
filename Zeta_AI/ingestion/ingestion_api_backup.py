from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel, Field, Extra
from typing import Optional, Any, List, Dict, Set
import logging
import os
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from dotenv import load_dotenv

# Chargement des variables d'environnement depuis .env
load_dotenv()

# Configuration du logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.debug('DEBUG MODE ACTIVATED')

import unicodedata
import numpy as np
import uuid
try:
    from sklearn.feature_extraction.text import HashingVectorizer
    _SKLEARN_AVAILABLE = True
except Exception as _sk_ex:
    HashingVectorizer = None
    _SKLEARN_AVAILABLE = False
    logging.warning(f"[INGEST][SPARSE] scikit-learn non disponible: {_sk_ex}")

# Configuration Meilisearch
MEILI_EMBEDDER_NAME = os.getenv("MEILI_EMBEDDER_NAME", "huggingface-embedder")
MEILI_HUGGING_FACE_MODEL = os.getenv("MEILI_HUGGING_FACE_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# Imports internes projet
from embedding_models import embed_text
from database.pgvector_client import (
    upsert_company_chunks_by_chunk_id,
)
from database.native_pgvector_client import purge_company_chunks
from database.meili_client import MeiliHelper

# FastAPI router/app
router = APIRouter(prefix="/ingestion", tags=["ingestion"])

class IngestionRequest(BaseModel):
    company_id: str
    data: Dict[str, Any]

# Configuration des settings par index
INDEX_SETTINGS = {
    "products": {
        "searchableAttributes": ["title", "content", "searchable_text", "product_name", "category", "subcategory"],
        "filterableAttributes": ["company_id", "category", "subcategory", "price", "stock", "sku"],
        "sortableAttributes": ["price", "stock"],
    },
    "delivery": {
        "searchableAttributes": ["title", "content", "searchable_text", "zone_name"],
        "filterableAttributes": ["company_id", "zone_name", "type"],
    },
    "support_paiement": {
        "searchableAttributes": ["title", "content", "searchable_text", "category"],
        "filterableAttributes": ["company_id", "category", "type"],
    },
    "localisation": {
        "searchableAttributes": ["title", "content", "searchable_text", "zone_name"],
        "filterableAttributes": ["company_id", "zone_name", "type"],
    },
    "company_docs": {
        "searchableAttributes": ["title", "content", "searchable_text", "category"],
        "filterableAttributes": ["company_id", "category", "type"],
    },
    "company": {
        "searchableAttributes": ["name", "ai_name", "sector", "mission", "objective", "description", "zone"],
        "filterableAttributes": ["company_id", "sector", "zone"],
    },
}

async def push_to_meili(company_id: str, data: Dict[str, Any]):
    """
    Pousse les données vers MeiliSearch avec gestion des synonymes et stopwords
    Découpage intelligent selon le type de document avec préservation du searchable_text
    PURGE AUTOMATIQUE à chaque ingestion
    """
    if not data:
        return
    try:
        import meilisearch
    except Exception:
        print("[ERREUR] Module meilisearch non disponible")
        return {"message": "Module meilisearch non disponible", "errors": ["meilisearch_unavailable"]}
    
    client = meilisearch.Client(
        os.environ.get("MEILI_URL", "http://127.0.0.1:7700"), 
        os.environ.get("MEILI_API_KEY") or os.environ.get("MEILI_MASTER_KEY", "")
    )
    
    # Index types à créer
    index_types = ["products", "delivery", "support_paiement", "localisation", "company_docs", "company"]
    
    print(f"\n[PURGE] === SUPPRESSION COMPLÈTE DES INDEX ===")
    
    # Suppression radicale et recréation des index
    for index_type in index_types:
        index_name = f"{index_type}_{company_id}"
        try:
            client.get_index(index_name)
            # si existant, suppression complète
            delete_task = client.delete_index(index_name)
            client.wait_for_task(delete_task.task_uid)
            print(f"[PURGE] ✅ Index '{index_name}' supprimé")
        except Exception:
            print(f"[PURGE] ℹ️  Index '{index_name}' n'existait pas")
        
        # Recréation de l'index avec settings
        try:
            client.create_index(index_name, {"primaryKey": "id"})
            settings = INDEX_SETTINGS.get(index_type, {})
            if settings:
                client.index(index_name).update_settings(settings)
            print(f"[PURGE] ✅ Index '{index_name}' recréé avec settings")
        except Exception as e:
            print(f"[PURGE] ❌ Erreur création '{index_name}': {e}")
    
    def _upsert(index_type: str, documents: List[Dict[str, Any]]):
        if not documents:
            return
        
        index_name = f"{index_type}_{company_id}"
        try:
            # Attendre que l'index soit prêt
            import time
            time.sleep(2)
            
            # Ajouter company_id à tous les documents
            for doc in documents:
                doc["company_id"] = company_id
                if "created_at" not in doc:
                    doc["created_at"] = datetime.now().isoformat()
            
            # Upsert des documents
            task = client.index(index_name).add_documents(documents)
            client.wait_for_task(task.task_uid)
            print(f"[INDEXATION] ✅ {len(documents)} documents indexés dans '{index_name}'")
            
        except Exception as e:
            print(f"[INDEXATION] ❌ Erreur indexation '{index_name}': {e}")
    
    # Découpage intelligent des documents selon leur type
    categorized_docs = {
        "products": [],
        "delivery": [],
        "support_paiement": [],
        "localisation": [],
        "company_docs": []
    }
    
    # Traiter les documents prétraités de N8N
    documents_key = None
    documents_data = []
    
    if "text_documents" in data:
        documents_key = "text_documents"
        documents_data = data["text_documents"]
    elif "documents" in data:
        documents_key = "documents"
        documents_data = data["documents"]
    
    print(f"[DÉCOUPAGE] === DEBUG PAYLOAD REÇU ===")
    print(f"[DÉCOUPAGE] Clés disponibles: {list(data.keys())}")
    print(f"[DÉCOUPAGE] Clé documents détectée: {documents_key}")
    print(f"[DÉCOUPAGE] Nombre de documents: {len(documents_data) if documents_data else 0}")
    
    if documents_data:
        print(f"[DÉCOUPAGE] === TRAITEMENT DE {len(documents_data)} DOCUMENTS ===")
        
        for i, doc in enumerate(documents_data, 1):
            metadata = doc.get("metadata", {})
            doc_type = metadata.get("type", "").lower()
            doc_id = doc.get('id', f'doc_{i}')
            content = doc.get("content", "")
            
            print(f"\n[DÉCOUPAGE][DOC-{i}] ==========================================")
            print(f"[DÉCOUPAGE][DOC-{i}] ID: {doc_id}")
            print(f"[DÉCOUPAGE][DOC-{i}] TYPE DÉTECTÉ: '{doc_type}'")
            
            # DÉCOUPAGE INTELLIGENT UNIFIÉ POUR TOUS LES TYPES
            processed_chunks = _smart_document_chunking(content, metadata, doc_id, doc_type)
            
            print(f"[DÉCOUPAGE][DOC-{i}] CHUNKS GÉNÉRÉS: {len(processed_chunks)}")
            
            # Distribuer les chunks dans les index appropriés
            for j, chunk in enumerate(processed_chunks, 1):
                chunk_type = chunk.get("type", doc_type)
                chunk_name = chunk.get("chunk_name", f"chunk_{j}")
                
                print(f"[DÉCOUPAGE][DOC-{i}] - CHUNK {j}: {chunk_name} (type: {chunk_type})")
                
                # Routage par type vers les index spécialisés
                if chunk_type in ["product", "products_catalog"] or chunk.get("chunk_category") == "product":
                    categorized_docs["products"].append(chunk)
                    destination_index = "products"
                elif chunk_type.startswith("delivery") or chunk_type in ["delivery", "delivery_abidjan_center", "delivery_abidjan_outskirts", "delivery_special_zones"]:
                    categorized_docs["delivery"].append(chunk)
                    destination_index = "delivery"
                elif chunk_type in ["payment", "support", "customer_support", "payment_process"]:
                    categorized_docs["support_paiement"].append(chunk)
                    destination_index = "support_paiement"
                elif chunk_type in ["location", "location_info"]:
                    categorized_docs["localisation"].append(chunk)
                    destination_index = "localisation"
                elif chunk_type in ["company", "business_summary", "customer_faq", "return_policy", "company_identity"]:
                    destination_index = "company_docs (exclusif)"
                else:
                    destination_index = "company_docs (autres)"
                
                # ROUTAGE EXCLUSIF - Pas de duplication dans company_docs
                if destination_index == "company_docs (exclusif)":
                    categorized_docs["company_docs"].append(chunk)
                elif destination_index == "company_docs (autres)":
                    categorized_docs["company_docs"].append(chunk)
                
                # AJOUT SYSTÉMATIQUE À COMPANY_DOCS POUR INDEX GLOBAL
                if destination_index not in ["company_docs (exclusif)", "company_docs (autres)"]:
                    categorized_docs["company_docs"].append(chunk)
                
                print(f"[DÉCOUPAGE][DOC-{i}] - CHUNK {j} → INDEX '{destination_index}' + company_docs")
            
            print(f"[DÉCOUPAGE][DOC-{i}] =========================================\n")
    
    # Indexer chaque catégorie avec logs détaillés
    print(f"\n[INDEXATION] === RÉSUMÉ FINAL DU DÉCOUPAGE ===")
    errors = []
    for index_type, docs in categorized_docs.items():
        print(f"[INDEXATION] Index '{index_type}': {len(docs)} documents")
        if docs:
            for j, doc in enumerate(docs, 1):
                print(f"[INDEXATION] - Doc {j}: ID={doc.get('id', 'N/A')}, Type={doc.get('type', 'N/A')}")
            _upsert(index_type, docs)
        else:
            print(f"[INDEXATION] - AUCUN DOCUMENT pour l'index '{index_type}'")
    print(f"[INDEXATION] ========================================\n")
    
    # NOUVEAU: Routage automatique vers Supabase avec les mêmes documents MeiliSearch
    try:
        print(f"\n[SUPABASE_ROUTING] === ROUTAGE AUTOMATIQUE VERS SUPABASE ===")
        
        # SIMPLIFICATION: Prendre directement chaque document de company_docs
        # 3 produits MeiliSearch = 3 chunks Supabase dédiés
        all_documents_for_supabase = []
        
        # Utiliser directement l'index company_docs qui contient TOUS les documents
        company_docs = categorized_docs.get("company_docs", [])
        if company_docs:
            print(f"[SUPABASE_ROUTING] Traitement de {len(company_docs)} documents depuis company_docs")
            for doc in company_docs:
                # GARANTIE: 1 document MeiliSearch = 1 chunk Supabase dédié
                supabase_doc = await _prepare_document_for_supabase(doc, company_id, "company_docs")
                if supabase_doc:
                    all_documents_for_supabase.append(supabase_doc)
        else:
            print(f"[SUPABASE_ROUTING] Aucun document dans company_docs")
        
        if all_documents_for_supabase:
            print(f"[SUPABASE_ROUTING] Documents à insérer: {len(all_documents_for_supabase)}")
            
            # Supprimer les anciens documents de cette entreprise
            from database.supabase_client import delete_all_chunks_for_company, insert_text_chunk_in_supabase
            import asyncio
            
            deleted_count = await delete_all_chunks_for_company(company_id)
            print(f"[SUPABASE_ROUTING] Anciens documents supprimés: {deleted_count}")
            
            # Insérer les nouveaux documents par batch
            batch_size = 50
            inserted_total = 0
            for i in range(0, len(all_documents_for_supabase), batch_size):
                batch = all_documents_for_supabase[i:i+batch_size]
                inserted_batch = await insert_text_chunk_in_supabase(batch)
                inserted_total += len(inserted_batch) if inserted_batch else 0
                print(f"[SUPABASE_ROUTING] Batch {i//batch_size + 1}: {len(inserted_batch) if inserted_batch else 0} documents insérés")
            
            print(f"[SUPABASE_ROUTING] Total inséré: {inserted_total} documents")
        else:
            print(f"[SUPABASE_ROUTING] Aucun document à router vers Supabase")
            
    except Exception as supabase_error:
        print(f"[SUPABASE_ROUTING] Erreur: {supabase_error}")
    
    # Indexer aussi les données directes si présentes
    _upsert("products", data.get("products", []))
    _upsert("delivery", data.get("delivery", []))
    _upsert("support_paiement", data.get("support_paiement", []))
    _upsert("localisation", data.get("localisation", []))
    _upsert("company_docs", data.get("company_docs", []))
    
    return {"message": "Ingestion terminée avec succès", "errors": errors}


async def _prepare_document_for_supabase(doc: Dict[str, Any], company_id: str, index_type: str) -> Dict[str, Any]:
    """
    Prépare un document MeiliSearch pour insertion dans Supabase avec embedding
    GARANTIE: UN DOCUMENT = UN CHUNK - AUCUNE TRONCATURE NI DIVISION NI MODIFICATION
    """
    try:
        from embedding_models import embed_text
        import uuid
        
        # Contenu du document (PRESERVATION INTEGRALE - AUCUNE MODIFICATION)
        content = doc.get("content", "")
        if not content:
            return None
        
        # AUCUNE LIMITE DE TAILLE - CONSERVATION INTEGRALE DU CONTENU
        # Le document est préservé tel quel, peu importe sa longueur
        
        # Générer l'embedding sur le contenu complet
        try:
            embedding = embed_text(content)
            if hasattr(embedding, 'tolist'):
                embedding = embedding.tolist()
        except Exception as e:
            print(f"[SUPABASE_ROUTING] Erreur embedding: {e}")
            return None
        
        # Préparer le document pour Supabase (CONTENU INTEGRAL PRESERVE)
        supabase_doc = {
            "id": str(uuid.uuid4()),
            "company_id": company_id,
            "content": content,  # CONTENU COMPLET SANS TRONCATURE
            "embedding": embedding,
            "metadata": {
                "original_id": doc.get("id", ""),
                "type": doc.get("type", ""),
                "chunk_category": doc.get("chunk_category", ""),
                "chunk_name": doc.get("chunk_name", ""),
                "zone_name": doc.get("zone_name", ""),
                "original_doc_id": doc.get("original_doc_id", ""),
                "index_type": index_type,
                "ingestion_source": "meilisearch_routing",
                "created_at": doc.get("created_at", ""),
                "content_length": len(content),  # Pour traçabilité
                "is_complete_document": True  # Marque que c'est un document complet
            }
        }
        
        return supabase_doc
        
    except Exception as e:
        print(f"[SUPABASE_ROUTING] Erreur préparation document: {e}")
        return None


def _smart_document_chunking(content: str, metadata: Dict[str, Any], doc_id: str, doc_type: str) -> List[Dict[str, Any]]:
    """
    Découpage intelligent unifié pour tous les types de documents
    """
    chunks = []
    
    if not content or not content.strip():
        return chunks
    
    # Créer un chunk unique pour le document complet
    chunk = {
        "id": doc_id,
        "content": content.strip(),
        "type": doc_type,
        "chunk_category": "single",
        "chunk_name": f"Document {doc_type}",
        "original_doc_id": doc_id,
        "created_at": datetime.now().isoformat()
    }
    
    # Ajouter les métadonnées du document original
    if metadata:
        chunk.update(metadata)
    
    chunks.append(chunk)
    return chunks


@router.post("/push_to_meili")
async def push_to_meili_endpoint(request: IngestionRequest):
    """
    Endpoint pour pousser des données vers MeiliSearch
    """
    try:
        result = await push_to_meili(request.company_id, request.data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
