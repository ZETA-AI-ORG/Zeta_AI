#!/usr/bin/env python3
"""
🎯 SYSTÈME DE COMBINAISONS PROGRESSIVES POUR MEILISEARCH
Après filtrage, teste toutes les combinaisons possibles pour maximiser les résultats
"""

import os
import requests
from itertools import combinations
from typing import List, Optional, Dict, Any
from utils import log3

# Imports pour les fonctions d'images (compatibilité)
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False


def search_meili_keywords(query: str, company_id: str, target_indexes: list = None, limit: int = 10) -> str:
    """
    🎯 SYSTÈME DE COMBINAISONS PROGRESSIVES MEILISEARCH
    Après filtrage, créer toutes les combinaisons possibles pour maximiser les résultats
    """
    log3("[MEILISEARCH] Requête", query)
    log3("[MEILISEARCH] Query originale", f"{query}, Company ID: {company_id}")
    
    # FILTRAGE MINIMAL: Retirer UNIQUEMENT les mots vides
    log3("[FILTRAGE_MINIMAL]", "🔧 FILTRAGE MINIMAL ACTIVÉ")
    log3("[FILTRAGE_MINIMAL]", f"📝 Query originale: '{query}'")
    log3("[FILTRAGE_MINIMAL]", f"📊 Longueur: {len(query)} caractères")
    
    # Appliquer le filtrage minimal (mots vides uniquement)
    from core.smart_stopwords import filter_query_for_meilisearch
    processed_keywords = filter_query_for_meilisearch(query)
    
    log3("[FILTRAGE_MINIMAL]", f"📝 Query filtrée: '{processed_keywords}'")
    log3("[FILTRAGE_MINIMAL]", f"📊 Longueur filtrée: {len(processed_keywords)} caractères")

    # 🎯 SYSTÈME DE COMBINAISONS PROGRESSIVES
    # Après filtrage, créer toutes les combinaisons possibles pour maximiser les résultats
    words = processed_keywords.split() if processed_keywords else []
    
    if not words:
        log3("[MEILI][GUARD] Aucun mot après filtrage", {
            "query_initiale": query,
            "processed_keywords": processed_keywords,
            "company_id": company_id
        })
        return ""
    
    # Générer toutes les combinaisons possibles
    search_queries = []
    
    # 1. Mots individuels (priorité faible)
    for word in words:
        if len(word) > 2:  # Éviter les mots trop courts
            search_queries.append((word, 1))
    
    # 2. Combinaisons de 2 mots (priorité moyenne)
    for combo in combinations(words, 2):
        search_queries.append((" ".join(combo), 2))
    
    # 3. Combinaisons de 3 mots (priorité haute)
    if len(words) >= 3:
        for combo in combinations(words, 3):
            search_queries.append((" ".join(combo), 3))
    
    # 4. Tous les mots ensemble (priorité maximale)
    if len(words) > 1:
        search_queries.append((" ".join(words), len(words)))
    
    # Trier par priorité (plus de mots = priorité plus haute)
    search_queries.sort(key=lambda x: x[1], reverse=True)
    
    log3("[MEILI][COMBINAISONS]", {
        "mots_filtres": words,
        "nb_combinaisons": len(search_queries),
        "combinaisons": [q[0] for q in search_queries[:5]]  # Top 5
    })
    
    # 🎯 RECHERCHE AVEC COMBINAISONS PROGRESSIVES
    all_results = []
    max_results_found = 0
    best_query = ""
    
    try:
        # Utiliser les index ciblés par le routeur d'intentions ou fallback
        if target_indexes and len(target_indexes) > 0:
            tenant_indexes = target_indexes
            log3("[MEILI][ROUTAGE_INTELLIGENT]", {
                "indexes_cibles": target_indexes,
                "nb_combinaisons": len(search_queries),
                "mode": "intention_routing_avec_combinaisons"
            })
        else:
            # Fallback sur tous les index si pas d'intentions détectées
            tenant_indexes = [
                f"products_{company_id}",
                f"delivery_{company_id}",
                f"support_paiement_{company_id}",
                f"company_docs_{company_id}",
                f"localisation_{company_id}",
                # Support des index en MAJUSCULES aussi
                f"PRODUCTS_{company_id}",
                f"DELIVERY_{company_id}",
                f"SUPPORT_PAIEMENT_{company_id}",
                f"COMPANY_DOCS_{company_id}",
                f"LOCALISATION_{company_id}"
            ]
        
        # 🎯 RECHERCHE EXHAUSTIVE: Tester TOUTES les combinaisons sans exception
        all_combo_results = {}  # Stocker les résultats de chaque combinaison
        
        for query_combo, priority in search_queries:
            log3("[MEILI][TEST_COMBO]", {
                "query": query_combo,
                "priorite": priority,
                "tentative": f"{search_queries.index((query_combo, priority)) + 1}/{len(search_queries)}"
            })
            
            combo_results = []
            for index_uid in tenant_indexes:
                try:
                    result = search_single_index_meilisearch(index_uid, query_combo, company_id, limit=5)
                    if result and len(result.strip()) > 0:
                        combo_results.append(result)
                except Exception as e:
                    continue
            
            # Stocker TOUS les résultats de cette combinaison
            if combo_results:
                results_count = sum(len(r.split('\n')) for r in combo_results if r)
                all_combo_results[query_combo] = {
                    "results": combo_results,
                    "count": results_count,
                    "priority": priority
                }
                
                log3("[MEILI][COMBO_SUCCESS]", {
                    "query": query_combo,
                    "priorite": priority,
                    "resultats": results_count,
                    "indexes_avec_resultats": len(combo_results)
                })
                
                # Garder trace de la meilleure combinaison
                if results_count > max_results_found:
                    max_results_found = results_count
                    best_query = query_combo
                    all_results = combo_results
            else:
                log3("[MEILI][COMBO_NO_RESULTS]", {
                    "query": query_combo,
                    "priorite": priority
                })
        
        # 📊 FUSION INTELLIGENTE DE TOUS LES RÉSULTATS
        if all_combo_results:
            # Fusionner tous les résultats uniques de toutes les combinaisons
            unique_results = set()
            unique_documents = set()  # Pour compter les documents distincts
            fusion_stats = {}
            
            for combo_query, combo_data in all_combo_results.items():
                for result in combo_data["results"]:
                    # Ajouter chaque résultat unique (lignes)
                    result_lines = result.strip().split('\n')
                    for line in result_lines:
                        if line.strip() and len(line.strip()) > 10:  # Éviter les lignes vides/courtes
                            unique_results.add(line.strip())
                    
                    # Compter les documents distincts (résultats complets)
                    if result.strip() and len(result.strip()) > 50:  # Document complet
                        unique_documents.add(result.strip())
                
                fusion_stats[combo_query] = {
                    "resultats": combo_data["count"],
                    "priorite": combo_data["priority"]
                }
            
            # Convertir en liste et fusionner
            final_unique_results = list(unique_results)
            final_result = "\n".join(final_unique_results)
            
            log3("[MEILI][FUSION_EXHAUSTIVE]", {
                "combinaisons_avec_resultats": len(all_combo_results),
                "documents_distincts": len(unique_documents),  # VRAI NOMBRE DE DOCUMENTS
                "lignes_uniques_totales": len(final_unique_results),  # LIGNES DE TEXTE
                "meilleure_combinaison": best_query,
                "stats_par_combo": fusion_stats,
                "longueur_finale": len(final_result)
            })
            
            return final_result
        
        if all_results:
            final_result = "\n".join(all_results)
            log3("[MEILI][FINAL_SUCCESS]", {
                "meilleure_query": best_query,
                "total_resultats": max_results_found,
                "longueur_finale": len(final_result)
            })
            return final_result
        else:
            log3("[MEILI][NO_RESULTS_ALL_COMBOS]", {
                "query_originale": query,
                "mots_filtres": words,
                "combinaisons_testees": len(search_queries),
                "indexes_testes": tenant_indexes
            })
            return ""
    
    except Exception as e:
        log3("[MEILI][ERROR_COMBINAISONS]", {
            "error": str(e),
            "query_originale": query,
            "company_id": company_id
        })
        return ""


def search_single_index_meilisearch(index_uid: str, query: str, company_id: str, limit: int = 10) -> str:
    """
    Recherche dans un seul index Meilisearch avec requêtes HTTP directes
    """
    try:
        meili_url = os.environ.get("MEILI_URL", "http://127.0.0.1:7700")
        meili_key = os.environ.get("MEILI_API_KEY") or os.environ.get("MEILI_MASTER_KEY", "")
        
        headers = {
            "Authorization": f"Bearer {meili_key}",
            "Content-Type": "application/json"
        }
        
        search_data = {
            "q": query,
            "limit": limit
        }
        
        response = requests.post(
            f"{meili_url}/indexes/{index_uid}/search",
            headers=headers,
            json=search_data,
            timeout=30
        )
        
        if response.status_code == 200:
            results = response.json()
            hits = results.get("hits", [])
            
            # Log pour debugging
            log3("[MEILI][SEARCH]", {
                "index": index_uid,
                "q": query,
                "hits": len(hits),
                "time_ms": results.get("processingTimeMs", 0),
                "sample": hits[0].get("content", "")[:50] if hits else ""
            })
            
            if hits:
                # Formater les résultats
                formatted_results = []
                for hit in hits:
                    content = hit.get("content", "")
                    if content and len(content.strip()) > 0:
                        formatted_results.append(content.strip())
                
                return "\n".join(formatted_results)
        else:
            log3("[MEILI][SEARCH]", {
                "index": index_uid,
                "q": query,
                "hits": 0,
                "time_ms": 0,
                "sample": ""
            })
        
        return ""
        
    except Exception as e:
        log3("[MEILI][SEARCH]", {
            "index": index_uid,
            "q": query,
            "hits": 0,
            "time_ms": 0,
            "sample": "",
            "error": str(e)
        })
        return ""


# ============================================================================
# FONCTIONS D'IMAGES (COMPATIBILITÉ AVEC L'ANCIEN SYSTÈME)
# ============================================================================

def get_qdrant_client():
    """Retourne le client Qdrant configuré"""
    if not QDRANT_AVAILABLE:
        raise ImportError("Qdrant client not available")
    
    return QdrantClient(
        host=os.environ.get("QDRANT_HOST", "localhost"),
        port=int(os.environ.get("QDRANT_PORT", 6333))
    )


def images_collection(company_id: str) -> str:
    """Nom de la collection d'images pour une entreprise"""
    return f"images_{company_id}"


def _ensure_collection(collection_name: str, vector_size: int = 512):
    """S'assure que la collection existe"""
    if not QDRANT_AVAILABLE:
        return
    
    try:
        qc = get_qdrant_client()
        qc.get_collection(collection_name)
    except Exception:
        # Collection n'existe pas, la créer
        from qdrant_client.models import VectorParams, Distance
        qc.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
        )


def _ensure_company_id_index(collection_name: str):
    """S'assure que l'index company_id existe"""
    if not QDRANT_AVAILABLE:
        return
    
    try:
        qc = get_qdrant_client()
        qc.create_payload_index(
            collection_name=collection_name,
            field_name="company_id",
            field_schema="keyword"
        )
    except Exception:
        pass  # Index existe déjà


def _company_filter(company_id: str):
    """Filtre par company_id"""
    if not QDRANT_AVAILABLE:
        return None
    
    return Filter(
        must=[
            FieldCondition(
                key="company_id",
                match=MatchValue(value=company_id)
            )
        ]
    )


def search_images(company_id: str, query_vector: list, limit: int = 10, *, min_score: Optional[float] = None, offset: int = 0):
    """Recherche de similarité d'images dans la collection du tenant."""
    if not QDRANT_AVAILABLE:
        return []
    
    qc = get_qdrant_client()
    collection = images_collection(company_id)
    _ensure_collection(collection, vector_size=len(query_vector))
    _ensure_company_id_index(collection)
    flt = _company_filter(company_id)
    
    try:
        hits = qc.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=limit,
            offset=offset or None,
            score_threshold=min_score,
            query_filter=flt,
        )
        # Normaliser la sortie: liste de dicts {id, score, payload}
        return [
            {
                "id": h.id,
                "score": getattr(h, "score", None),
                "payload": getattr(h, "payload", None),
            }
            for h in hits
        ]
    except Exception as e:
        log3("[QDRANT][ERROR]", f"Erreur recherche images: {e}")
        return []


def find_near_duplicates(company_id: str, query_vector: list, *, min_score: float = 0.995, limit: int = 20) -> List[dict]:
    """Détecte des quasi-doublons visuels en cherchant avec un score élevé."""
    return search_images(company_id=company_id, query_vector=query_vector, limit=limit, min_score=min_score)


def recommend_images_by_id(company_id: str, seed_id: str, limit: int = 10, *, min_score: Optional[float] = None, offset: int = 0):
    """Recommande des images similaires à partir d'un ID de référence."""
    if not QDRANT_AVAILABLE:
        return []
    
    qc = get_qdrant_client()
    collection = images_collection(company_id)
    
    try:
        # Récupérer le vecteur de l'image de référence
        seed_point = qc.retrieve(
            collection_name=collection,
            ids=[seed_id],
            with_vectors=True
        )
        
        if not seed_point or not seed_point[0].vector:
            return []
        
        # Utiliser ce vecteur pour la recherche
        return search_images(
            company_id=company_id,
            query_vector=seed_point[0].vector,
            limit=limit + 1,  # +1 car on va exclure l'image de référence
            min_score=min_score,
            offset=offset
        )[1:]  # Exclure le premier résultat (l'image elle-même)
        
    except Exception as e:
        log3("[QDRANT][ERROR]", f"Erreur recommandation images: {e}")
        return []


# ============================================================================
# FONCTIONS DE LIVRAISON (COMPATIBILITÉ)
# ============================================================================

def search_delivery(company_id: str, zone_query: str, limit: int = 5) -> List[dict]:
    """Recherche des frais/délais de livraison pour une zone donnée."""
    try:
        result = search_single_index_meilisearch(
            f"delivery_{company_id}", 
            zone_query, 
            company_id, 
            limit=limit
        )
        
        # Parser les résultats pour extraire zone, price, delay
        if not result:
            return []
        
        # Retourner un format simple pour compatibilité
        return [{"zone": zone_query, "price": "N/A", "delay": "N/A"}]
        
    except Exception as e:
        log3("[MEILI][delivery]", f"Erreur recherche livraison: {e}")
        return []
