#!/usr/bin/env python3
"""
🎯 INGESTION COMPLÈTE : LLM HYDE + SMART SPLITTER
Pipeline optimal pour données brutes vers documents parfaits

WORKFLOW:
1. Réception text_documents (structure par type, contenu brouillon)
2. LLM Hyde nettoie chaque document selon son type
3. Smart Splitter sépare les catalogues (1 prix = 1 doc)
4. Indexation MeiliSearch + Supabase

AVANTAGES:
- Corrige fautes automatiquement
- Normalise formats
- Sépare documents optimalement
- Données parfaites pour RAG
"""

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import logging
import uuid

router = APIRouter(prefix="/hyde-etl", tags=["llm-hyde-etl"])

class TextDocument(BaseModel):
    """Document texte avec métadonnées"""
    content: str
    file_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class HydeETLRequest(BaseModel):
    """Request pour ingestion complète"""
    company_id: str
    text_documents: List[Dict[str, Any]]
    purge_before: Optional[bool] = True

class HydeETLResponse(BaseModel):
    """Response avec stats détaillées"""
    success: bool
    company_id: str
    documents_input: int
    documents_cleaned: int
    documents_split: int
    documents_indexed: int
    processing_steps: List[str]
    message: str

@router.post("/ingest", response_model=HydeETLResponse)
async def hyde_etl_ingest(request: HydeETLRequest):
    """
    🎯 ENDPOINT PRINCIPAL - INGESTION COMPLÈTE
    
    Pipeline:
    1. LLM Hyde nettoie chaque document
    2. Smart Splitter sépare catalogues
    3. Indexation MeiliSearch
    """
    
    processing_steps = []
    
    try:
        print(f"\n🚀 HYDE ETL INGESTION - Company: {request.company_id}")
        print(f"📦 Documents input: {len(request.text_documents)}")
        print("="*80)
        
        # ÉTAPE 1: LLM HYDE - NETTOYAGE PAR TYPE
        print("\n1️⃣ LLM HYDE - NETTOYAGE ET STRUCTURATION")
        print("-"*80)
        
        from core.llm_client import get_groq_llm_client
        llm_client = get_groq_llm_client()
        
        cleaned_documents = []
        
        for doc in request.text_documents:
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            doc_type = metadata.get("type", "unknown")
            doc_id = metadata.get("document_id", metadata.get("id", "unknown"))
            
            print(f"\n   📄 Document: {doc_id} (type: {doc_type})")
            
            # Nettoyer selon le type
            cleaned_content = await clean_document_with_hyde(
                content=content,
                doc_type=doc_type,
                company_id=request.company_id,
                llm_client=llm_client
            )
            
            # Garder document nettoyé
            cleaned_documents.append({
                "id": doc_id,
                "content": cleaned_content,
                "metadata": {
                    **metadata,
                    "cleaned_by_hyde": True,
                    "original_length": len(content),
                    "cleaned_length": len(cleaned_content)
                }
            })
            
            print(f"      ✅ Nettoyé: {len(content)} → {len(cleaned_content)} chars")
        
        processing_steps.append(f"LLM Hyde: {len(cleaned_documents)} documents nettoyés")
        
        # ÉTAPE 2: SMART SPLITTER - SÉPARATION CATALOGUES
        print(f"\n2️⃣ SMART SPLITTER - SÉPARATION DOCUMENTS")
        print("-"*80)
        
        from core.smart_catalog_splitter import smart_split_document
        
        final_documents = []
        
        for doc in cleaned_documents:
            doc_type = doc.get("metadata", {}).get("type", "")
            
            # Si catalogue produits, on split
            if any(keyword in doc_type.lower() for keyword in ["product", "catalog", "catalogue", "faq"]):
                print(f"\n   🔪 Split: {doc['id']}")
                
                split_results = smart_split_document(doc, request.company_id)
                
                if len(split_results) > 1:
                    print(f"      ✅ {len(split_results)} documents créés")
                    final_documents.extend(split_results)
                else:
                    final_documents.append(doc)
            else:
                final_documents.append(doc)
        
        processing_steps.append(f"Smart Splitter: {len(final_documents)} documents finaux")
        
        # ÉTAPE 3: INDEXATION MEILISEARCH
        print(f"\n3️⃣ INDEXATION MEILISEARCH")
        print("-"*80)
        
        import meilisearch
        meili_client = meilisearch.Client(
            os.environ.get("MEILI_URL", "http://127.0.0.1:7700"),
            os.environ.get("MEILI_API_KEY", "")
        )
        
        index_name = f"company_docs_{request.company_id}"
        
        # Supprimer index si demandé
        if request.purge_before:
            try:
                meili_client.delete_index(index_name)
                print(f"   🗑️ Index {index_name} supprimé")
            except:
                pass
        
        # Créer index
        try:
            meili_client.create_index(index_name, {"primaryKey": "id"})
        except:
            pass
        
        # Préparer documents pour MeiliSearch
        meili_docs = []
        for doc in final_documents:
            meili_doc = {
                "id": doc.get("id", str(uuid.uuid4())),
                "company_id": request.company_id,
                "content": doc.get("content", ""),
                "type": doc.get("type", doc.get("metadata", {}).get("type", "unknown")),
                **doc.get("metadata", {})
            }
            meili_docs.append(meili_doc)
        
        # Indexer
        resp = meili_client.index(index_name).add_documents(meili_docs)
        print(f"   ✅ {len(meili_docs)} documents indexés")
        
        processing_steps.append(f"Indexation: {len(meili_docs)} documents dans MeiliSearch")
        
        # ÉTAPE 4: TODO - INDEXATION SUPABASE
        print(f"\n4️⃣ INDEXATION SUPABASE")
        print("-"*80)
        print(f"   ⏳ TODO: Génération embeddings + stockage Supabase")
        
        processing_steps.append("Supabase: TODO")
        
        print("\n" + "="*80)
        print("✅ PIPELINE COMPLET TERMINÉ")
        print("="*80)
        
        return HydeETLResponse(
            success=True,
            company_id=request.company_id,
            documents_input=len(request.text_documents),
            documents_cleaned=len(cleaned_documents),
            documents_split=len(final_documents),
            documents_indexed=len(meili_docs),
            processing_steps=processing_steps,
            message=f"✅ Pipeline complet: {len(request.text_documents)} → {len(meili_docs)} documents"
        )
        
    except Exception as e:
        logging.exception("[HYDE-ETL][ERROR]")
        raise HTTPException(status_code=500, detail=str(e))

async def clean_document_with_hyde(
    content: str,
    doc_type: str,
    company_id: str,
    llm_client
) -> str:
    """
    Nettoie un document avec LLM selon son type
    
    Args:
        content: Contenu brut (peut avoir fautes, formats incohérents)
        doc_type: Type de document (products_catalog, delivery, etc.)
        company_id: ID entreprise
        llm_client: Client LLM
        
    Returns:
        Contenu nettoyé et structuré
    """
    
    # Prompts spécialisés par type
    prompts_by_type = {
        "products_catalog": """Tu es un expert en nettoyage de catalogues produits.

TÂCHE: Nettoyer et structurer le catalogue ci-dessous.

CORRECTIONS À FAIRE:
1. Corriger fautes d'orthographe (ex: "paket" → "paquet")
2. Normaliser formats prix (ex: "5500f" → "5.500 F CFA")
3. Uniformiser structure
4. Garder TOUS les prix et variantes

FORMAT DE SORTIE:
=== CATALOGUES PRODUITS ===

PRODUITS : [Nom du produit]
VARIANTES ET PRIX :
[quantité] [unité] - [prix] F CFA | [prix unitaire] F/[unité]

IMPORTANT: Ne pas calculer, ne pas inventer, juste nettoyer et structurer.""",

        "delivery": """Tu es un expert en nettoyage d'informations de livraison.

TÂCHE: Nettoyer et structurer les infos de livraison.

CORRECTIONS:
1. Corriger fautes
2. Normaliser noms de zones
3. Formats prix uniformes
4. Délais clairs

FORMAT DE SORTIE:
=== LIVRAISON [ZONE] ===
Zones couvertes: [liste]
Tarif: [prix] FCFA
Délais: [info]""",

        "company_identity": """Tu es un expert en nettoyage d'informations entreprise.

TÂCHE: Nettoyer et structurer les infos de l'entreprise.

CORRECTIONS:
1. Corriger fautes
2. Rendre description claire
3. Formater proprement

FORMAT DE SORTIE:
=== ENTREPRISE [NOM] ===
Nom: [nom]
Assistant IA: [nom]
Secteur: [secteur]
Description: [description claire]""",

        "customer_support": """Tu es un expert en nettoyage d'infos de contact.

TÂCHE: Nettoyer et normaliser les contacts.

CORRECTIONS:
1. Formater numéros: +225XXXXXXXXXX
2. Corriger fautes
3. Horaires clairs

FORMAT DE SORTIE:
=== SUPPORT CLIENT ===
Téléphone: +225...
WhatsApp: +225...
Horaires: [horaires]"""
    }
    
    # Sélectionner prompt selon type
    system_prompt = prompts_by_type.get(
        doc_type.lower().replace("_", "").replace("-", ""),
        prompts_by_type["products_catalog"]  # Fallback
    )
    
    # Construire prompt complet
    full_prompt = f"""{system_prompt}

CONTENU À NETTOYER:
```
{content}
```

RÉPONDS UNIQUEMENT AVEC LE CONTENU NETTOYÉ, RIEN D'AUTRE."""
    
    try:
        # Appel LLM
        cleaned = await llm_client.complete(
            prompt=full_prompt,
            temperature=0.1,  # Basse température pour précision
            max_tokens=2000
        )
        
        return cleaned.strip()
        
    except Exception as e:
        print(f"      ⚠️ Erreur LLM: {e}, contenu original conservé")
        return content  # Fallback: garder original

@router.get("/stats/{company_id}")
async def get_hyde_etl_stats(company_id: str):
    """Stats MeiliSearch après ingestion"""
    
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

# Import manquant
from pydantic import Field
