"""
Ingestion API - Version optimisée et complète
Point d'entrée principal pour l'ingestion de documents d'entreprise
Intégration MeiliSearch + Supabase avec routage intelligent
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import logging
import os
import asyncio
import uuid
import meilisearch
from datetime import datetime
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

# Configuration du logger
logger = logging.getLogger(__name__)

# Imports du projet
from embedding_models import embed_text
from database.supabase_client import delete_all_chunks_for_company, insert_text_chunk_in_supabase
from database.meili_client import MeiliHelper
from database.supabase_client import get_supabase_client

# Router FastAPI
router = APIRouter(prefix="/ingestion", tags=["ingestion"])

class IngestionRequest(BaseModel):
    company_id: str
    documents: List[Dict[str, Any]]


class BotlivePromptUpsertRequest(BaseModel):
    company_id: str
    prompt: str
    ai_name: Optional[str] = None
    company_name: Optional[str] = None

# Configuration optimisée et COMPLÈTE des settings MeiliSearch par index
# 🔥 AUTO-CONFIGURATION À L'INGESTION - Plus besoin de scripts externes
INDEX_SETTINGS = {
    "products": {
        "searchableAttributes": ["searchable_text", "content_fr", "product_name", "name", "description", "color", "category", "subcategory", "brand", "size", "tags", "slug"],
        "filterableAttributes": ["company_id", "type", "category", "subcategory", "color", "brand", "size", "price", "min_price", "max_price", "currency", "stock", "in_stock", "available", "tags", "is_active"],
        "sortableAttributes": ["price", "min_price", "max_price", "stock", "created_at", "updated_at", "popularity", "priority"],
        "rankingRules": ["words", "typo", "proximity", "attribute", "sort", "exactness"],
        "typoTolerance": {"enabled": True, "minWordSizeForTypos": {"oneTypo": 4, "twoTypos": 8}},
        "synonyms": {
            "couche": ["couches", "pampers", "huggies"],
            "culotte": ["culottes"],
            "bebe": ["bébé", "enfant", "nourrisson"],
            "moto": ["motorcycle", "motorbike", "scooter"],
            "casque": ["casques", "helmet", "helmets"],
            "noir": ["black", "noire"], "bleu": ["blue", "bleue"], "rouge": ["red"], 
            "blanc": ["white", "blanche"], "gris": ["gray", "grey", "grise"],
            "vert": ["green", "verte"], "jaune": ["yellow"], "rose": ["pink"]
        },
        "stopWords": ["le", "la", "les", "de", "du", "des", "un", "une", "et", "à", "au", "aux", "en", "pour", "sur", "par", "avec", "sans"],
        "faceting": {"maxValuesPerFacet": 200},
        "pagination": {"maxTotalHits": 2000}
    },
    "delivery": {
        "searchableAttributes": ["searchable_text", "content_fr", "zone", "zone_name", "zone_group", "city", "commune", "quartier", "details"],
        "filterableAttributes": ["company_id", "type", "zone", "zone_group", "city", "fee", "delivery_fee", "currency", "free_delivery", "express_available"],
        "sortableAttributes": ["fee", "delivery_fee", "priority"],
        "synonyms": {
            "cocody": ["cocody-angré", "cocody-danga", "cocody-riviera"],
            "yopougon": ["yop", "yopougon-niangon", "yopougon-selmer"],
            "abidjan": ["cocody", "yopougon", "plateau", "marcory", "treichville", "abobo", "adjamé"],
            "livraison": ["delivery", "shipping", "expedition"],
            "gratuit": ["free", "gratuite"],
            "express": ["rapide", "urgent"]
        },
        "stopWords": ["le", "la", "les", "de", "du", "des", "à", "au"],
        "faceting": {"maxValuesPerFacet": 200}
    },
    "support_paiement": {
        "searchableAttributes": ["searchable_text", "content_fr", "method", "payment_method", "contact_info", "details", "question", "answer"],
        "filterableAttributes": ["company_id", "type", "method", "payment_method", "payment_accepted", "acompte_required", "prepaid_only", "policy_kind"],
        "synonyms": {
            "wave": ["waveci", "orange money", "om"],
            "paiement": ["payment", "payement"],
            "acompte": ["accompte", "avance", "arrhes"]
        },
        "stopWords": ["le", "la", "les", "de", "du", "des"],
        "faceting": {"maxValuesPerFacet": 100}
    },
    "localisation": {
        "searchableAttributes": ["searchable_text", "content_fr", "zone_name", "address", "location", "location_name", "city", "quartier"],
        "filterableAttributes": ["company_id", "type", "zone", "city", "store_type", "location_type", "has_physical_store"],
        "synonyms": {
            "cocody": ["cocody-angré", "cocody-danga", "cocody-riviera"],
            "yopougon": ["yop", "yopougon-niangon"],
            "abidjan": ["cocody", "yopougon", "plateau", "marcory", "treichville"]
        }
    },
    "company_docs": {
        "searchableAttributes": ["searchable_text", "content_fr", "product_name", "color", "tags", "zone", "zone_group", "method", "details", "category", "subcategory", "name", "slug"],
        "filterableAttributes": ["company_id", "type", "doc_type", "category", "subcategory", "color", "price", "currency", "stock", "city", "zone", "zone_group", "method", "policy_kind", "tags", "section", "language"],
        "sortableAttributes": ["price", "stock", "updated_at"],
        "rankingRules": ["words", "typo", "proximity", "attribute", "sort", "exactness"],
        "synonyms": {
            "cocody": ["cocody-angré", "cocody-danga", "cocody-riviera"],
            "yopougon": ["yop", "yopougon-niangon", "yopougon-selmer"],
            "abidjan": ["cocody", "yopougon", "plateau", "marcory", "treichville", "abobo", "adjamé"],
            "couche": ["couches", "pampers", "huggies"],
            "culotte": ["culottes"],
            "bebe": ["bébé", "enfant", "nourrisson"],
            "noir": ["black", "noire"], "bleu": ["blue", "bleue"], "rouge": ["red"],
            "blanc": ["white", "blanche"], "gris": ["gray", "grey", "grise"],
            "wave": ["waveci", "orange money"],
            "livraison": ["delivery", "shipping"],
            "gratuit": ["free", "gratuite"]
        },
        "stopWords": ["le", "la", "les", "de", "du", "des", "un", "une", "et", "à", "au", "aux", "en", "pour", "sur", "par", "avec", "sans", "ce", "cette", "ces"],
        "typoTolerance": {"enabled": True, "minWordSizeForTypos": {"oneTypo": 4, "twoTypos": 8}},
        "faceting": {"maxValuesPerFacet": 200},
        "pagination": {"maxTotalHits": 2000}
    },
    "company": {
        "searchableAttributes": ["name", "ai_name", "sector", "mission", "objective", "description", "zone", "address"],
        "filterableAttributes": ["company_id", "sector", "zone", "city", "is_active"],
        "stopWords": ["le", "la", "les", "de", "du"]
    }
}

async def push_to_meili(company_id: str, documents: List[Dict[str, Any]]):
    """
    Fonction principale pour pousser les documents vers MeiliSearch avec découpage intelligent
    
    Args:
        company_id: ID de l'entreprise
        documents: Liste des documents à traiter
    
    Returns:
        Dict avec résumé de l'ingestion
    """
    try:
        logger.info(f"[INGESTION] === DÉBUT INGESTION ===")
        logger.info(f"[DEBUG] company_id reçu: {company_id} (type: {type(company_id)})")
        logger.info(f"[DEBUG] documents reçus: {type(documents)} (longueur: {len(documents) if documents else 'None'})")
        
        # PROTECTION TOTALE CONTRE LES VALEURS NONE
        if company_id is None:
            logger.error("[DEBUG] company_id est None")
            raise ValueError("company_id ne peut pas être None")
        
        logger.info(f"[DEBUG] Conversion company_id en string...")
        company_id = str(company_id)
        logger.info(f"[DEBUG] company_id après str(): '{company_id}'")
        
        logger.info(f"[DEBUG] Strip company_id...")
        company_id = company_id.strip()
        logger.info(f"[DEBUG] company_id après strip(): '{company_id}'")
        
        if not company_id:
            raise ValueError("company_id ne peut pas être vide après nettoyage")
        
        # Protection documents
        if documents is None:
            logger.info("[DEBUG] documents est None, initialisation liste vide")
            documents = []
        
        if not isinstance(documents, list):
            logger.error(f"[DEBUG] documents n'est pas une liste: {type(documents)}")
            raise ValueError("documents doit être une liste")
            
        logger.info(f"[DEBUG] Protection terminée, début traitement...")
        
    except Exception as e:
        logger.error(f"[DEBUG] ERREUR dans protection initiale: {e}")
        logger.error(f"[DEBUG] Type erreur: {type(e)}")
        import traceback
        logger.error(f"[DEBUG] Traceback: {traceback.format_exc()}")
        raise
    
    if not documents:
        logger.warning("[INGESTION] Aucun document fourni")
        return {"message": "Aucun document à traiter", "errors": []}
    
    try:
        import meilisearch
    except ImportError:
        logger.error("[INGESTION] Module meilisearch non disponible")
        return {"message": "Module meilisearch non disponible", "errors": ["meilisearch_unavailable"]}
    
    # Initialisation du client MeiliSearch
    client = meilisearch.Client(
        os.environ.get("MEILI_URL", "http://127.0.0.1:7700"), 
        os.environ.get("MEILI_API_KEY") or os.environ.get("MEILI_MASTER_KEY", "")
    )
    
    # Types d'index à gérer
    index_types = ["products", "delivery", "support_paiement", "localisation", "company_docs", "company"]
    
    logger.info(f"[INGESTION] Début ingestion pour company_id={company_id}")
    logger.info(f"[PURGE] === SUPPRESSION ET RECRÉATION DES INDEX DÉSACTIVÉE ===")
    logger.info(f"[PURGE] MeiliSearch désactivé sur cet endpoint")
    logger.info(f"[PURGE] Utiliser /ingestion/ingest-structured pour MeiliSearch")
    
    # ÉTAPE 1: Purge complète et recréation des index DÉSACTIVÉE
    
    # Fonction pour configurer automatiquement les settings d'un index
    def _ensure_index_settings(index_type: str):
        """Configure automatiquement les settings optimaux pour un index"""
        index_name = f"{index_type}_{company_id}"
        
        try:
            # Vérifier si l'index existe, sinon le créer
            try:
                client.get_index(index_name)
            except Exception:
                # Index n'existe pas, le créer
                logger.info(f"[CONFIG] Création index '{index_name}'")
                client.create_index(index_name, {"primaryKey": "id"})
                import time
                time.sleep(0.5)  # Attendre la création
            
            # Appliquer les settings optimaux si disponibles
            if index_type in INDEX_SETTINGS:
                settings = INDEX_SETTINGS[index_type]
                logger.info(f"[CONFIG] Application settings pour '{index_name}'")
                task = client.index(index_name).update_settings(settings)
                # Ne pas attendre la fin de la tâche (async)
                logger.info(f"[CONFIG] ✅ Settings appliqués (task_uid={task.task_uid})")
            else:
                logger.warning(f"[CONFIG] ⚠️  Pas de settings définis pour type '{index_type}'")
                
        except Exception as e:
            logger.error(f"[CONFIG] ❌ Erreur configuration '{index_name}': {e}")
    
    # Fonction interne pour l'upsert des documents
    def _upsert_documents(index_type: str, documents: List[Dict[str, Any]]):
        """Upsert des documents dans un index MeiliSearch"""
        if not documents:
            return
        
        index_name = f"{index_type}_{company_id}"
        try:
            # 🔧 CONFIGURATION AUTOMATIQUE DES SETTINGS
            _ensure_index_settings(index_type)
            
            # Attendre que l'index soit prêt
            import time
            time.sleep(1)
            
            # Enrichir les documents avec company_id et timestamp
            for doc in documents:
                doc["company_id"] = company_id
                if "created_at" not in doc:
                    doc["created_at"] = datetime.now().isoformat()
                # Générer un ID unique si manquant
                if "id" not in doc or not doc.get("id"):
                    doc["id"] = str(uuid.uuid4())
            
            # Indexation des documents
            task = client.index(index_name).add_documents(documents)
            client.wait_for_task(task.task_uid)
            logger.info(f"[INDEXATION] ✅ {len(documents)} documents indexés dans '{index_name}'")
            
        except Exception as e:
            logger.error(f"[INDEXATION] ❌ Erreur indexation '{index_name}': {e}")
    
    # ÉTAPE 2: Traitement et catégorisation des documents
    categorized_docs = {
        "products": [],
        "delivery": [],
        "support_paiement": [],
        "localisation": [],
        "company_docs": []
    }
    
    # ÉTAPE 3: Traitement intelligent des documents directement depuis le paramètre
    logger.info(f"[DÉCOUPAGE] === ANALYSE DU PAYLOAD ===")
    logger.info(f"[DÉCOUPAGE] Nombre de documents reçus: {len(documents)}")
    
    if documents:
        logger.info(f"[DÉCOUPAGE] === TRAITEMENT DE {len(documents)} DOCUMENTS ===")
        
        for i, doc in enumerate(documents, 1):
            try:
                logger.info(f"[DEBUG][DOC-{i}] Traitement document {i}")
                
                # Protection complète du document
                if doc is None:
                    logger.warning(f"[DÉCOUPAGE][DOC-{i}] Document None ignoré")
                    continue
                
                logger.info(f"[DEBUG][DOC-{i}] Type document: {type(doc)}")
                
                if not isinstance(doc, dict):
                    logger.warning(f"[DÉCOUPAGE][DOC-{i}] Document non-dict ignoré: {type(doc)}")
                    continue
                
                logger.info(f"[DEBUG][DOC-{i}] Clés document: {list(doc.keys())}")
                
                # Protection métadonnées
                metadata = doc.get("metadata")
                logger.info(f"[DEBUG][DOC-{i}] metadata brut: {metadata} (type: {type(metadata)})")
                
                if metadata is None:
                    metadata = {}
                elif not isinstance(metadata, dict):
                    metadata = {}
                
                logger.info(f"[DEBUG][DOC-{i}] metadata après protection: {metadata}")
                
                # Protection type
                doc_type_raw = metadata.get("type")
                logger.info(f"[DEBUG][DOC-{i}] doc_type_raw: {doc_type_raw} (type: {type(doc_type_raw)})")
                
                if doc_type_raw is None:
                    doc_type = ""
                else:
                    try:
                        doc_type = str(doc_type_raw).lower().strip()
                    except Exception as e:
                        logger.error(f"[DEBUG][DOC-{i}] Erreur conversion doc_type: {e}")
                        doc_type = ""
                
                logger.info(f"[DEBUG][DOC-{i}] doc_type final: '{doc_type}'")
                
                # Protection ID
                doc_id_raw = metadata.get('id') or metadata.get('document_id')
                logger.info(f"[DEBUG][DOC-{i}] doc_id_raw: {doc_id_raw} (type: {type(doc_id_raw)})")
                
                if doc_id_raw is None:
                    doc_id = f'doc_{company_id}_{i}'
                else:
                    try:
                        doc_id = str(doc_id_raw).strip()
                    except Exception as e:
                        logger.error(f"[DEBUG][DOC-{i}] Erreur conversion doc_id: {e}")
                        doc_id = f'doc_{company_id}_{i}'
                
                logger.info(f"[DEBUG][DOC-{i}] doc_id final: '{doc_id}'")
                
                # Protection contenu
                content_raw = doc.get("content")
                logger.info(f"[DEBUG][DOC-{i}] content_raw: {type(content_raw)} (longueur: {len(str(content_raw)) if content_raw else 'None'})")
                
                if content_raw is None:
                    content = ""
                else:
                    try:
                        content = str(content_raw).strip()
                    except Exception as e:
                        logger.error(f"[DEBUG][DOC-{i}] Erreur conversion content: {e}")
                        content = ""
                
                logger.info(f"[DEBUG][DOC-{i}] content final: longueur {len(content)}")
                
                if not content:
                    logger.warning(f"[DÉCOUPAGE][DOC-{i}] Contenu vide ignoré")
                    continue
                    
            except Exception as e:
                logger.error(f"[DEBUG][DOC-{i}] ERREUR traitement document: {e}")
                import traceback
                logger.error(f"[DEBUG][DOC-{i}] Traceback: {traceback.format_exc()}")
                continue
            
            logger.info(f"[DÉCOUPAGE][DOC-{i}] ==========================================")
            logger.info(f"[DÉCOUPAGE][DOC-{i}] ID: {doc_id}")
            logger.info(f"[DÉCOUPAGE][DOC-{i}] TYPE DÉTECTÉ: '{doc_type}'")
            logger.info(f"[DÉCOUPAGE][DOC-{i}] TAILLE: {len(content)} caractères")
            
            # DÉCOUPAGE INTELLIGENT UNIFIÉ POUR TOUS LES TYPES
            processed_chunks = _smart_document_chunking(content, metadata, doc_id, doc_type)
            
            logger.info(f"[DÉCOUPAGE][DOC-{i}] CHUNKS GÉNÉRÉS: {len(processed_chunks)}")
            
            # Distribuer les chunks dans les index appropriés
            for j, chunk in enumerate(processed_chunks, 1):
                chunk_type = chunk.get("type", doc_type)
                chunk_name = chunk.get("chunk_name", f"chunk_{j}")
                
                logger.info(f"[DÉCOUPAGE][DOC-{i}] - CHUNK {j}: {chunk_name} (type: {chunk_type})")
                
                # Routage par type vers les index spécialisés
                destination_indexes = _route_document_to_indexes(chunk, chunk_type)
                
                for dest_index in destination_indexes:
                    if dest_index in categorized_docs:
                        categorized_docs[dest_index].append(chunk.copy())
                        logger.info(f"[DÉCOUPAGE][DOC-{i}] - CHUNK {j} → INDEX '{dest_index}'")
            
            logger.info(f"[DÉCOUPAGE][DOC-{i}] ==========================================")
    
    # ÉTAPE 4: Indexation MeiliSearch DÉSACTIVÉE
    logger.info(f"[INDEXATION] === INDEXATION MEILISEARCH DÉSACTIVÉE ===")
    logger.info(f"[INDEXATION] Cet endpoint ne fait plus d'indexation MeiliSearch")
    logger.info(f"[INDEXATION] Utiliser /ingestion/ingest-structured pour MeiliSearch")
    logger.info(f"[INDEXATION] Seule l'ingestion Supabase est active")
    logger.info(f"[INDEXATION] ========================================")
    errors = []
    
    # ÉTAPE 5: Routage automatique vers Supabase
    try:
        logger.info(f"[SUPABASE_ROUTING] === ROUTAGE AUTOMATIQUE VERS SUPABASE ===")
        
        # ROUTER TOUS LES CHUNKS VERS SUPABASE (pas seulement company_docs)
        all_documents_for_supabase = []
        
        # Parcourir TOUS les index avec leurs documents
        for index_type, docs in categorized_docs.items():
            if docs:
                logger.info(f"[SUPABASE_ROUTING] Traitement de {len(docs)} documents depuis {index_type}")
                
                for doc in docs:
                    # Préparation du document pour Supabase avec embedding
                    supabase_doc = await _prepare_document_for_supabase(doc, company_id, index_type)
                    if supabase_doc:
                        all_documents_for_supabase.append(supabase_doc)
            else:
                logger.info(f"[SUPABASE_ROUTING] Aucun document dans {index_type}")
        
        if all_documents_for_supabase:
            logger.info(f"[SUPABASE_ROUTING] Documents à insérer: {len(all_documents_for_supabase)}")
            
            # Suppression des anciens documents de cette entreprise
            deleted_count = await delete_all_chunks_for_company(company_id)
            logger.info(f"[SUPABASE_ROUTING] Anciens documents supprimés: {deleted_count}")
            
            # Insertion par batch pour optimiser les performances
            batch_size = 50
            inserted_total = 0
            
            for i in range(0, len(all_documents_for_supabase), batch_size):
                batch = all_documents_for_supabase[i:i+batch_size]
                try:
                    inserted_batch = await insert_text_chunk_in_supabase(batch)
                    batch_count = len(inserted_batch) if inserted_batch else 0
                    inserted_total += batch_count
                    logger.info(f"[SUPABASE_ROUTING] Batch {i//batch_size + 1}: {batch_count} documents insérés")
                except Exception as batch_error:
                    logger.error(f"[SUPABASE_ROUTING] Erreur batch {i//batch_size + 1}: {batch_error}")
            
            logger.info(f"[SUPABASE_ROUTING] Total inséré: {inserted_total} documents")
            
            # ═══════════════════════════════════════════════════════════
            # EXTRACTION ET SAUVEGARDE BOOSTERS
            # ═══════════════════════════════════════════════════════════
            try:
                logger.info(f"[BOOSTERS] === EXTRACTION BOOSTERS ===")
                from core.company_boosters_extractor import extract_company_boosters
                from datetime import datetime
                
                # Extraire boosters depuis tous les documents
                boosters = extract_company_boosters({
                    "company_id": company_id,
                    "text_documents": documents
                })
                
                logger.info(f"[BOOSTERS] Keywords: {len(boosters.get('keywords', []))} détectés")
                logger.info(f"[BOOSTERS] Catégories: {list(boosters.get('categories', {}).keys())}")
                
                # Convertir sets en lists pour JSON
                boosters_json = {
                    "company_id": company_id,
                    "keywords": list(boosters.get("keywords", [])),
                    "categories": {
                        cat: {
                            "products": data.get("products", []),
                            "zones": data.get("zones", []),
                            "methods": data.get("methods", []),
                            "phones": data.get("phones", []),
                            "name": data.get("name", ""),
                            "sector": data.get("sector", ""),
                            "keywords": list(data.get("keywords", []))
                        }
                        for cat, data in boosters.get("categories", {}).items()
                    },
                    "filters": boosters.get("filters", {}),
                    "updated_at": datetime.now().isoformat()
                }
                
                # Sauvegarder dans Supabase
                from database.supabase_client import get_supabase_client
                supabase = get_supabase_client()
                
                # Upsert avec on_conflict pour gérer les duplicates
                result = supabase.table("company_boosters").upsert(
                    boosters_json,
                    on_conflict="company_id"
                ).execute()
                
                logger.info(f"[BOOSTERS] ✅ Boosters sauvegardés pour {company_id[:12]}...")
                
            except Exception as boosters_error:
                logger.error(f"[BOOSTERS] ❌ Erreur extraction boosters: {boosters_error}")
                import traceback
                traceback.print_exc()
            
        else:
            logger.info(f"[SUPABASE_ROUTING] Aucun document à router vers Supabase")
            
    except Exception as supabase_error:
        logger.error(f"[SUPABASE_ROUTING] Erreur générale: {supabase_error}")
        errors.append(f"supabase_error: {str(supabase_error)}")
    
    logger.info(f"[INGESTION] === INGESTION TERMINÉE AVEC SUCCÈS ===")
    return {
        "message": "Ingestion terminée avec succès", 
        "errors": errors,
        "company_id": company_id,
        "processed_documents": len(documents) if documents else 0,
        "indexes_updated": len([k for k, v in categorized_docs.items() if v])
    }


def _smart_document_chunking(content: str, metadata: Dict[str, Any], doc_id: str, doc_type: str) -> List[Dict[str, Any]]:
    """
    Découpage intelligent des documents selon leur type
    - Catalogues produits: 1 chunk par produit
    - Autres documents: 1 chunk complet
    """
    chunks = []
    
    # Protection totale des paramètres
    if content is None:
        content = ""
    else:
        content = str(content).strip()
    
    if not content:
        return chunks
    
    if metadata is None:
        metadata = {}
    elif not isinstance(metadata, dict):
        metadata = {}
    
    if doc_id is None:
        doc_id = "unknown_doc"
    else:
        doc_id = str(doc_id).strip()
    
    if doc_type is None:
        doc_type = ""
    else:
        doc_type = str(doc_type).strip()
    
    # DÉCOUPAGE SPÉCIAL POUR LES CATALOGUES PRODUITS
    if doc_type in ["products_catalog", "catalogue_produits"]:
        logger.info(f"[SMART_CHUNKING] Découpage catalogue produits détecté pour {doc_id}")
        
        import re
        
        # POINTS D'ANCRAGE UNIVERSELS SCALABLES - Compatible toute entreprise
        universal_product_patterns = [
            # Pattern principal: "PRODUITS :" suivi du nom
            r'PRODUITS\s*:\s*([^\n\r]+)',
            # Pattern alternatif: "PRODUIT :" (singulier)
            r'PRODUIT\s*:\s*([^\n\r]+)',
            # Pattern service: "SERVICE :" 
            r'SERVICE\s*:\s*([^\n\r]+)',
            # Pattern offre: "OFFRE :" 
            r'OFFRE\s*:\s*([^\n\r]+)',
            # Pattern article: "ARTICLE :" 
            r'ARTICLE\s*:\s*([^\n\r]+)',
            # Pattern item: "ITEM :" 
            r'ITEM\s*:\s*([^\n\r]+)'
        ]
        
        # SÉPARATEURS UNIVERSELS - Points d'ancrage fixes
        universal_separators = [
            r'---+',           # Tirets multiples
            r'===+',           # Égals multiples  
            r'\*\*\*+',        # Astérisques multiples
            r'___+',           # Underscores multiples
            r'#{3,}',          # Hash multiples
            r'[-=*_]{5,}',     # Mélange de séparateurs
            r'\n\s*\n\s*(?=PRODUITS?\s*:)',  # Double saut avant PRODUIT(S)
            r'\n\s*\n\s*(?=SERVICE\s*:)',    # Double saut avant SERVICE
            r'\n\s*\n\s*(?=OFFRE\s*:)',      # Double saut avant OFFRE
        ]
        
        # Construire le pattern de division universel
        separator_pattern = '|'.join([f'(?:{sep})' for sep in universal_separators])
        division_pattern = f'(?={"|".join([pat for pat in universal_product_patterns])})|{separator_pattern}'
        
        # Diviser le contenu par les points d'ancrage universels
        try:
            product_sections = re.split(division_pattern, content, flags=re.IGNORECASE | re.MULTILINE)
        except Exception as e:
            logger.error(f"[SMART_CHUNKING] Erreur regex split: {e}")
            # Fallback: diviser par --- seulement
            product_sections = content.split('---')
        
        logger.info(f"[SMART_CHUNKING] {len(product_sections)} sections détectées avec points d'ancrage universels")
        
        for i, section in enumerate(product_sections):
            try:
                # Protection section None
                if section is None:
                    logger.warning(f"[SMART_CHUNKING] Section {i+1} est None, ignorée")
                    continue
                
                # Conversion sécurisée en string
                try:
                    section = str(section).strip()
                except Exception as e:
                    logger.error(f"[SMART_CHUNKING] Erreur conversion section {i+1}: {e}")
                    continue
                
                # Ignorer les sections vides ou qui ne sont que des séparateurs
                if not section or re.match(r'^[-=*_#\s]+$', section):
                    continue
                
                # FILTRER LES CHUNKS DE TITRE/EN-TÊTE INUTILES
                section_lower = section.lower().strip()
                
                # Ignorer les titres génériques sans contenu détaillé
                if (len(section) < 100 and (
                    section_lower.startswith('=== catalogues produits ===') or
                    section_lower.startswith('catalogues produits') or
                    re.match(r'^produits?\s*:\s*[^\\n]*$', section_lower) or
                    section_lower in ['couches à pression ( pour enfant de 0 à 30 kg )', 
                                     'couches culottes ( pour enfant de 5 à 30 kg )',
                                     'couches culottes  ( pour enfant de 5 à 30 kg )',
                                     'couches adultes']
                )):
                    logger.info(f"[SMART_CHUNKING] Section {i+1} ignorée (titre/en-tête): {section[:50]}...")
                    continue
                
                logger.info(f"[SMART_CHUNKING] Traitement section {i+1}: {len(section)} caractères")
                
                # Détecter le nom du produit avec tous les patterns universels
                product_name = None
                for pattern in universal_product_patterns:
                    try:
                        match = re.search(pattern, section, re.IGNORECASE)
                        if match and match.group(1):
                            product_name = str(match.group(1)).strip()
                            break
                    except Exception as e:
                        logger.error(f"[SMART_CHUNKING] Erreur pattern {pattern}: {e}")
                        continue
                
                # Fallback si aucun pattern trouvé
                if not product_name:
                    try:
                        # Essayer de prendre la première ligne non-vide comme nom
                        first_lines = [line.strip() for line in section.split('\n')[:3] if line and line.strip()]
                        product_name = first_lines[0] if first_lines else f"Produit {i+1}"
                    except Exception as e:
                        logger.error(f"[SMART_CHUNKING] Erreur fallback nom: {e}")
                        product_name = f"Produit {i+1}"
                
                # Sécurité: s'assurer que product_name n'est jamais None
                if product_name is None:
                    product_name = f"Produit {i+1}"
                
                # Nettoyer le nom du produit avec protection None
                try:
                    product_name = re.sub(r'^[=\-*_#\s]+|[=\-*_#\s]+$', '', str(product_name)).strip()
                except (AttributeError, TypeError, Exception) as e:
                    logger.error(f"[SMART_CHUNKING] Erreur nettoyage nom: {e}")
                    product_name = f"Produit {i+1}"
                
                # Dernière sécurité: nom par défaut si vide après nettoyage
                if not product_name or product_name.isspace():
                    product_name = f"Produit {i+1}"
                    
            except Exception as e:
                logger.error(f"[SMART_CHUNKING] Erreur traitement section {i+1}: {e}")
                import traceback
                logger.error(f"[SMART_CHUNKING] Traceback: {traceback.format_exc()}")
                continue
            
            # Créer un chunk dédié pour ce produit avec ID scalable
            try:
                chunk = {
                    "id": f"{doc_id}_product_{i+1}",
                    "content": str(section).strip(),
                    "type": "product",
                    "chunk_category": "individual_product", 
                    "chunk_name": f"Produit: {product_name}",
                    "product_name": product_name,
                    "original_doc_id": doc_id,
                    "created_at": datetime.now().isoformat(),
                    "searchable_text": str(section).strip(),
                    "extraction_method": "universal_anchors"  # Traçabilité
                }
                
                # Ajouter les métadonnées du document original
                if metadata and isinstance(metadata, dict):
                    chunk.update(metadata)
                    chunk["type"] = "product"  # Forcer le type produit
                
                chunks.append(chunk)
                logger.info(f"[SMART_CHUNKING] Chunk produit universel créé: {product_name}")
                
            except Exception as e:
                logger.error(f"[SMART_CHUNKING] Erreur création chunk {i+1}: {e}")
                continue
    
    else:
        # CHUNK UNIQUE POUR LES AUTRES TYPES DE DOCUMENTS
        chunk = {
            "id": doc_id,
            "content": content.strip(),
            "type": doc_type,
            "chunk_category": "complete_document",
            "chunk_name": f"Document {doc_type}",
            "original_doc_id": doc_id,
            "created_at": datetime.now().isoformat(),
            "searchable_text": content.strip()
        }
        
        # Ajouter les métadonnées du document original
        if metadata:
            # Préserver custom_attributes avant update
            custom_attrs = metadata.get("custom_attributes")
            chunk.update(metadata)
            # Restaurer custom_attributes si présent
            if custom_attrs:
                chunk["custom_attributes"] = custom_attrs
        
        chunks.append(chunk)
    
    return chunks


def _route_document_to_indexes(chunk: Dict[str, Any], doc_type: str) -> List[str]:
    """
    Détermine vers quels index router un document selon son type
    """
    chunk_type = chunk.get("type", doc_type).lower()
    indexes = []
    
    # Routage spécialisé par type
    if chunk_type in ["company_identity", "company"]:
        indexes.append("company")
    elif chunk_type in ["products_catalog", "catalogue_produits", "product"]:
        indexes.append("products")
    elif chunk_type in ["delivery_abidjan_center", "delivery_abidjan_outskirts", "delivery_special_zones", "livraison"]:
        indexes.append("delivery")
    elif chunk_type in ["customer_support", "payment_process", "return_policy", "support", "paiement"]:
        indexes.append("support_paiement")
    elif chunk_type in ["location_info", "localisation"]:
        indexes.append("localisation")
    else:
        # Documents génériques vont dans company_docs
        indexes.append("company_docs")
    
    return indexes


async def _prepare_document_for_supabase(doc: Dict[str, Any], company_id: str, index_type: str) -> Optional[Dict[str, Any]]:
    """
    Prépare un document MeiliSearch pour insertion dans Supabase avec embedding
    GARANTIE: UN DOCUMENT = UN CHUNK - AUCUNE TRONCATURE NI DIVISION
    ✅ NOUVEAU: Extraction automatique des métadonnées intelligentes
    """
    try:
        # Contenu du document (PRÉSERVATION INTÉGRALE)
        content = doc.get("content", "")
        if not content or not content.strip():
            return None
        
        # Génération de l'embedding sur le contenu complet
        try:
            embedding = await embed_text(content)  # ⚠️ AWAIT ajouté !
            if hasattr(embedding, 'tolist'):
                embedding = embedding.tolist()
        except Exception as e:
            logger.error(f"[SUPABASE_ROUTING] Erreur embedding: {e}")
            return None
        
        # ✅ EXTRACTION AUTOMATIQUE DES MÉTADONNÉES INTELLIGENTES
        smart_metadata = {}
        try:
            from core.smart_metadata_extractor import auto_detect_metadata
            smart_metadata = auto_detect_metadata(content, company_id)
            logger.info(f"[SMART_METADATA] Métadonnées extraites: type={smart_metadata.get('doc_type')}, "
                       f"categories={len(smart_metadata.get('categories', []))}, "
                       f"attributes={len(smart_metadata.get('attributes', {}))}")
        except Exception as e:
            logger.warning(f"[SMART_METADATA] Erreur extraction métadonnées: {e}")
            # Continuer sans métadonnées intelligentes
        
        # Préparation du document pour Supabase
        supabase_doc = {
            "company_id": company_id,
            "content": content,  # CONTENU COMPLET SANS MODIFICATION
            "embedding": embedding,
            "metadata": {
                # Métadonnées originales
                "original_id": doc.get("id", ""),
                "type": doc.get("type", ""),
                "chunk_category": doc.get("chunk_category", ""),
                "chunk_name": doc.get("chunk_name", ""),
                "zone_name": doc.get("zone_name", ""),
                "original_doc_id": doc.get("original_doc_id", ""),
                "index_type": index_type,
                "ingestion_source": "meilisearch_routing",
                "created_at": doc.get("created_at", datetime.now().isoformat()),
                "content_length": len(content),
                "is_complete_document": True,  # Marque document complet
                
                # ✅ MÉTADONNÉES PRODUIT (product_name, custom_attributes, etc.)
                "product_name": doc.get("product_name", ""),
                "custom_attributes": doc.get("custom_attributes", {}),
                "category": doc.get("category", ""),
                "subcategory": doc.get("subcategory", ""),
                "price_min": doc.get("price_min", 0),
                "price_max": doc.get("price_max", 0),
                
                # ✅ MÉTADONNÉES INTELLIGENTES
                "smart_doc_type": smart_metadata.get("doc_type", ""),
                "smart_categories": smart_metadata.get("categories", []),
                "smart_subcategories": smart_metadata.get("subcategories", []),
                "smart_attributes": smart_metadata.get("attributes", {}),
            }
        }
        
        return supabase_doc
        
    except Exception as e:
        logger.error(f"[SUPABASE_ROUTING] Erreur préparation document: {e}")
        return None


@router.post("/push_to_meili")
async def push_to_meili_endpoint(request: IngestionRequest):
    """
    Endpoint principal pour l'ingestion de documents
    
    Accepte les formats :
    - Nouveau format structuré avec text_documents
    - Format legacy avec clés directes
    
    Retourne un résumé détaillé de l'ingestion
    """
    try:
        logger.info(f"[ENDPOINT] Requête d'ingestion reçue pour company_id={request.company_id}")
        result = await push_to_meili(request.company_id, request.documents)
        logger.info(f"[ENDPOINT] Ingestion terminée avec succès pour company_id={request.company_id}")
        return result
    except Exception as e:
        logger.error(f"[ENDPOINT] Erreur ingestion pour company_id={request.company_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur d'ingestion: {str(e)}")


@router.post("/upsert-botlive-prompt-deepseek")
async def upsert_botlive_prompt_deepseek(payload: BotlivePromptUpsertRequest):
    try:
        company_id = (payload.company_id or "").strip()
        prompt = payload.prompt or ""
        if not company_id:
            raise HTTPException(status_code=400, detail="company_id manquant")
        if not prompt or not str(prompt).strip():
            raise HTTPException(status_code=400, detail="prompt manquant")

        supabase = get_supabase_client()
        now_iso = datetime.now().isoformat()

        row: Dict[str, Any] = {
            "company_id": company_id,
            "prompt_botlive_deepseek_v3": str(prompt),
            "botlive_prompts_updated_at": now_iso,
        }
        if payload.ai_name is not None and str(payload.ai_name).strip():
            row["ai_name"] = str(payload.ai_name).strip()
        if payload.company_name is not None and str(payload.company_name).strip():
            row["company_name"] = str(payload.company_name).strip()

        result = supabase.table("company_rag_configs").upsert(
            row,
            on_conflict="company_id",
        ).execute()

        updated = 0
        try:
            updated = len(result.data) if result and getattr(result, "data", None) else 0
        except Exception:
            updated = 0

        logger.info(
            "[BOTLIVE_PROMPT][UPSERT] ✅ upsert deepseek prompt for company_id=%s | chars=%s | updated_rows=%s",
            company_id,
            len(str(prompt)),
            updated,
        )

        return {
            "status": "ok",
            "company_id": company_id,
            "updated_at": now_iso,
            "prompt_chars": len(str(prompt)),
            "updated_rows": updated,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[BOTLIVE_PROMPT][UPSERT] ❌")
        raise HTTPException(status_code=500, detail=str(e))


# === ENDPOINT DÉDIÉ MEILISEARCH ===
@router.post("/ingest-structured")
async def ingest_structured(payload: IngestionRequest):
    try:
        if not payload.company_id:
            raise HTTPException(status_code=400, detail="company_id manquant")
        
        company_id = payload.company_id
        documents = payload.documents or []
        
        if not documents:
            raise HTTPException(status_code=400, detail="Aucun document valide à indexer")
        
        logger.info(f"[MEILI_STRUCTURED] Début ingestion pour company_id={company_id}")
        
        # ✨ ÉTAPE 1: LLM HYDE - DÉSACTIVÉ (n8n génère déjà du texte parfait)
        logger.info(f"[HYDE] === ÉTAPE 1: SKIP NETTOYAGE LLM (n8n génère déjà du texte propre) ===")
        
        # Conserver les documents originaux (pas de nettoyage)
        cleaned_documents = documents
        
        # ✨ ÉTAPE 2: PARSE JSON PRODUITS (1 variante = 1 document)
        logger.info(f"[PRODUCT_SPLIT] === ÉTAPE 2: DÉCOUPAGE VARIANTES PRODUITS ===")
        
        processed_documents = []
        
        for doc in cleaned_documents:
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            doc_type = metadata.get("type", "")
            doc_id = metadata.get("document_id", "unknown")
            
            # Parser JSON pour produits uniquement
            if any(keyword in doc_type.lower() for keyword in ["product", "catalog", "catalogue"]):
                logger.info(f"[HYDE] Parse JSON catalogue: {doc_id}")
                
                try:
                    import json
                    import re
                    
                    # Extraire JSON du contenu (peut être dans ```json...```)
                    json_match = re.search(r'```json\s*(\[.*?\])\s*```', content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                    else:
                        # Chercher directement un array JSON
                        json_match = re.search(r'\[.*\]', content, re.DOTALL)
                        if json_match:
                            json_str = json_match.group(0)
                        else:
                            # Pas de JSON trouvé, garder tel quel
                            logger.warning(f"[HYDE] Pas de JSON trouvé, document conservé")
                            processed_documents.append(doc)
                            continue
                    
                    # Parser le JSON
                    items = json.loads(json_str)
                    
                    if isinstance(items, list) and len(items) > 0:
                        # Créer un document par item
                        for idx, item in enumerate(items, 1):
                            unique_id = f"{doc_id}_item_{idx}"  # ID UNIQUE
                            
                            # Content court pour LLM
                            item_content = f"{item.get('quantity', '')} {item.get('unit', '')} de {item.get('product', 'Produit')}: {item.get('price', 0):,} F CFA".replace(',', '.')
                            
                            # SUPER SEARCHABLE_TEXT enrichi pour recherche MeiliSearch
                            searchable_parts = [
                                item.get('product', ''),
                                item.get('variant', ''),
                                item.get('description', ''),
                                f"{item.get('quantity', '')} {item.get('unit', '')}",
                                f"{item.get('price', 0)} FCFA",
                                metadata.get('usage', ''),
                                metadata.get('notes', ''),
                                metadata.get('category', ''),
                                metadata.get('subcategory', ''),
                                metadata.get('product_name', '')
                            ]
                            searchable_text = " ".join([str(p) for p in searchable_parts if p]).strip()
                            
                            split_doc = {
                                "content": item_content,
                                "searchable_text": searchable_text,  # SUPER META pour recherche
                                "metadata": {
                                    **metadata,
                                    "type": "pricing",
                                    "document_id": unique_id,  # ID unique
                                    "id": unique_id,  # IMPORTANT: ID pour MeiliSearch
                                    "product": item.get("product", ""),
                                    "variant": item.get("variant", ""),
                                    "price": item.get("price", 0),
                                    "quantity": item.get("quantity", 0),
                                    "unit": item.get("unit", ""),
                                    "description": item.get("description", ""),
                                    "split_from": doc_id
                                }
                            }
                            
                            processed_documents.append(split_doc)
                        
                        logger.info(f"[HYDE] ✅ {len(items)} documents créés depuis JSON")
                    else:
                        logger.warning(f"[HYDE] JSON vide, document conservé")
                        processed_documents.append(doc)
                        
                except Exception as e:
                    logger.warning(f"[HYDE] Erreur parse JSON: {e}, document conservé")
                    processed_documents.append(doc)
            else:
                # Autres types: garder tel quel
                processed_documents.append(doc)
        
        # Remplacer documents par versions processées
        documents = processed_documents
        logger.info(f"[HYDE] === PIPELINE TERMINÉ: {len(documents)} documents finaux ===")
        # ✨ FIN NOUVEAU
        
        # Initialisation du client MeiliSearch
        client = meilisearch.Client(
            os.environ.get("MEILI_URL", "http://127.0.0.1:7700"), 
            os.environ.get("MEILI_API_KEY") or os.environ.get("MEILI_MASTER_KEY", "")
        )
        
        # Types d'index à gérer
        index_types = ["products", "delivery", "support_paiement", "localisation", "company_docs"]
        
        # PURGE BEFORE - Suppression directe des index
        if getattr(payload, 'purge_before', True):
            logger.info(f"[MEILI_PURGE] === SUPPRESSION DIRECTE DES INDEX ===")
            
            for index_type in index_types:
                index_name = f"{index_type}_{company_id}"
                try:
                    # Suppression directe
                    client.index(index_name).delete()
                    logger.info(f"[MEILI_PURGE] ✅ Index '{index_name}' supprimé")
                except Exception as e:
                    logger.info(f"[MEILI_PURGE] ℹ️ Index '{index_name}' n'existait pas: {e}")
        
        # Recréation des index avec settings optimisés
        logger.info(f"[MEILI_CREATE] === RECRÉATION DES INDEX ===")
        for index_type in index_types:
            index_name = f"{index_type}_{company_id}"
            try:
                # Recréation avec settings optimisés
                client.create_index(index_name, {"primaryKey": "id"})
                
                # Configuration COMPLÈTE des attributs de recherche et de filtrage
                index = client.index(index_name)
                
                # Attributs recherchables (ordre de priorité)
                index.update_searchable_attributes([
                    'searchable_text', 'content', 'product', 'variant', 'chunk_name', 'zone_name', 
                    'file_name', 'type', 'document_id', 'id_raw', 'id_slug'
                ])
                
                # Attributs filtrables
                index.update_filterable_attributes([
                    'type', 'chunk_category', 'company_id', 'document_id', 
                    'id', 'id_raw', 'id_slug', 'file_name', 'created_at',
                    # Produits
                    'product', 'variant', 'price', 'quantity', 'unit',
                    'category', 'subcategory', 'product_name',
                    # Livraison
                    'delivery_zone', 'zone_names',
                    # Support
                    'phone', 'payment_methods', 'acompte_required',
                    # Localisation
                    'location_type', 'has_physical_store', 'zone', 'country',
                    # Identité
                    'name', 'ai_name', 'sector'
                ])
                
                # Attributs triables
                index.update_sortable_attributes([
                    'company_id', 'created_at', 'type', 'document_id', 'file_name', 
                    'price', 'quantity'  # Tri produits
                ])
                
                # Attributs affichés dans les résultats (tous les champs)
                index.update_displayed_attributes(['*'])  # Afficher TOUS les attributs
                
                logger.info(f"[MEILI_CREATE] ✅ Index '{index_name}' recréé avec settings optimisés")
                
            except Exception as e:
                logger.error(f"[MEILI_CREATE] ❌ Erreur avec l'index '{index_name}': {e}")
                continue
        
        # Fonction interne pour l'upsert des documents
        def _upsert_documents_structured(index_type: str, documents: List[Dict[str, Any]]):
            """Upsert des documents dans un index MeiliSearch"""
            if not documents:
                return
            
            index_name = f"{index_type}_{company_id}"
            try:
                # Attendre que l'index soit prêt
                import time
                time.sleep(1)
                
                # Enrichir les documents avec company_id et timestamp
                for doc in documents:
                    doc["company_id"] = company_id
                    if "created_at" not in doc:
                        doc["created_at"] = datetime.now().isoformat()
                    # Générer un ID unique si manquant
                    if "id" not in doc or not doc.get("id"):
                        doc["id"] = str(uuid.uuid4())
                
                # Indexation
                index = client.index(index_name)
                task = index.add_documents(documents)
                
                logger.info(f"[MEILI_INDEXATION] ✅ {len(documents)} documents indexés dans '{index_name}'")
                
            except Exception as e:
                logger.error(f"[MEILI_INDEXATION] ❌ Erreur indexation '{index_name}': {e}")
        
        # Traitement et catégorisation des documents
        categorized_docs = {
            "products": [],
            "delivery": [],
            "support_paiement": [],
            "localisation": [],
            "company_docs": []
        }
        
        # Traitement des documents avec routage
        logger.info(f"[MEILI_ROUTING] === ROUTAGE DES DOCUMENTS ===")
        
        for i, doc in enumerate(documents, 1):
            try:
                if doc is None or not isinstance(doc, dict):
                    continue
                
                # Extraire les métadonnées
                metadata = doc.get("metadata", {})
                if not isinstance(metadata, dict):
                    metadata = {}
                
                # Créer le document normalisé avec TOUS les champs métadonnées
                normalized_doc = {
                    "id": metadata.get("id") or metadata.get("document_id") or str(uuid.uuid4()),
                    "company_id": company_id,
                    "content": doc.get("content", ""),
                    "searchable_text": doc.get("searchable_text", ""),  # SUPER META pour produits
                    "type": metadata.get("type", ""),
                    "file_name": doc.get("file_name", ""),
                    "created_at": datetime.now().isoformat()
                }
                
                # PRÉSERVER TOUTES les métadonnées importantes
                for key, value in metadata.items():
                    if key not in normalized_doc:
                        normalized_doc[key] = value
                
                doc_type = metadata.get("type", "").lower()
                
                # ROUTAGE VERS INDEX SPÉCIALISÉS + COMPANY_DOCS (plan de secours)
                
                # 1. DOCUMENTS PRODUITS (inclus "pricing" généré par le smart splitter)
                if "product" in doc_type or "catalogue" in doc_type or "pricing" in doc_type:
                    categorized_docs["products"].append(normalized_doc)
                    product_name = normalized_doc.get("product", "produit")
                    logger.info(f"[MEILI_ROUTING] Doc {i} → products ({product_name})")
                
                # 2. DOCUMENTS DE LIVRAISON
                elif "delivery" in doc_type or "livraison" in doc_type:
                    categorized_docs["delivery"].append(normalized_doc)
                    logger.info(f"[MEILI_ROUTING] Doc {i} → delivery (type: {doc_type})")
                
                # 3. DOCUMENTS SUPPORT & PAIEMENT
                elif "support" in doc_type or "payment" in doc_type or "paiement" in doc_type:
                    categorized_docs["support_paiement"].append(normalized_doc)
                    logger.info(f"[MEILI_ROUTING] Doc {i} → support_paiement (type: {doc_type})")
                
                # 4. DOCUMENTS DE LOCALISATION
                elif "location" in doc_type or "localisation" in doc_type:
                    categorized_docs["localisation"].append(normalized_doc)
                    logger.info(f"[MEILI_ROUTING] Doc {i} → localisation (type: {doc_type})")
                
                # TOUS LES DOCUMENTS vont TOUJOURS dans company_docs (index global de secours)
                company_doc = normalized_doc.copy()
                company_doc["id"] = f"global_{normalized_doc['id']}"
                categorized_docs["company_docs"].append(company_doc)
                logger.info(f"[MEILI_ROUTING] Doc {i} → company_docs (backup global: {doc_type})")
                
            except Exception as e:
                logger.error(f"[MEILI_ROUTING] Erreur traitement doc {i}: {e}")
                continue
        
        # Indexation dans les index spécialisés
        logger.info(f"[MEILI_INDEXATION] === INDEXATION DANS LES INDEX SPÉCIALISÉS ===")
        total_indexed = 0
        
        for index_type, docs in categorized_docs.items():
            if docs:
                logger.info(f"[MEILI_INDEXATION] Index '{index_type}': {len(docs)} documents")
                _upsert_documents_structured(index_type, docs)
                total_indexed += len(docs)
            else:
                logger.info(f"[MEILI_INDEXATION] Index '{index_type}': 0 documents")
        
        logger.info(f"[MEILI_STRUCTURED] === INGESTION TERMINÉE ===")
        logger.info(f"[MEILI_STRUCTURED] Total indexé: {total_indexed} documents")
        
        return {
            "company_id": company_id,
            "indexed": total_indexed,
            "indexes_created": len(index_types),
            "message": "Ingestion MeiliSearch terminée avec succès"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[INGEST][STRUCTURED] Erreur d'indexation")
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint de santé pour vérifier la disponibilité
@router.get("/health")
async def health_check():
    """Vérification de santé de l'API d'ingestion"""
    try:
        import meilisearch
        return {
            "status": "healthy",
            "meilisearch_available": True,
            "timestamp": datetime.now().isoformat()
        }
    except ImportError:
        return {
            "status": "degraded",
            "meilisearch_available": False,
            "timestamp": datetime.now().isoformat()
        }
