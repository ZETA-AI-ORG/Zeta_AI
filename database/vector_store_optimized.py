#!/usr/bin/env python3
"""
🚀 SYSTÈME DE COMBINAISONS OPTIMISÉ POUR PERFORMANCE
Objectif: < 10 secondes par requête
"""

import os
import requests
import asyncio
import aiohttp
from itertools import combinations
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils import log3

# Imports pour les fonctions d'images (compatibilité)
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False


async def search_meili_keywords_optimized(query: str, company_id: str, target_indexes: list = None, limit: int = 10) -> str:
    """
    🚀 VERSION OPTIMISÉE: Recherche parallèle avec limites intelligentes
    Objectif: < 5 secondes pour Meilisearch
    """
    import time
    start_time = time.time()
    
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

    # 🎯 SYSTÈME DE COMBINAISONS OPTIMISÉ
    words = processed_keywords.split() if processed_keywords else []
    
    if not words:
        log3("[MEILI][GUARD] Aucun mot après filtrage", {
            "query_initiale": query,
            "processed_keywords": processed_keywords,
            "company_id": company_id
        })
        return ""
    
    # 🚀 OPTIMISATION 1: LIMITER LES COMBINAISONS (MAX 15 au lieu de 42)
    search_queries = []
    
    # Priorité MAXIMALE: Tous les mots ensemble
    if len(words) > 1:
        search_queries.append((" ".join(words), len(words)))
    
    # Priorité HAUTE: Combinaisons de 3 mots (limitées à 10)
    if len(words) >= 3:
        combos_3 = list(combinations(words, 3))[:10]  # MAX 10
        for combo in combos_3:
            search_queries.append((" ".join(combo), 3))
    
    # Priorité MOYENNE: Combinaisons de 2 mots (limitées à 5)
    if len(words) >= 2:
        combos_2 = list(combinations(words, 2))[:5]  # MAX 5
        for combo in combos_2:
            search_queries.append((" ".join(combo), 2))
    
    # Trier par priorité (plus de mots = priorité plus haute)
    search_queries.sort(key=lambda x: x[1], reverse=True)
    
    # 🚀 OPTIMISATION 2: LIMITER À 15 COMBINAISONS MAX
    search_queries = search_queries[:15]
    
    log3("[MEILI][COMBINAISONS_OPTIMISEES]", {
        "mots_filtres": words,
        "nb_combinaisons": len(search_queries),
        "combinaisons": [q[0] for q in search_queries[:5]]  # Top 5
    })
    
    # 🚀 OPTIMISATION 3: INDEX INTELLIGENTS (5 au lieu de 10)
    if target_indexes and len(target_indexes) > 0:
        tenant_indexes = target_indexes[:5]  # Limiter à 5 index max
    else:
        # Prioriser les index minuscules (plus rapides)
        tenant_indexes = [
            f"products_{company_id}",
            f"delivery_{company_id}",
            f"support_paiement_{company_id}",
            f"company_docs_{company_id}",
            f"localisation_{company_id}"
        ]
    
    # 🚀 OPTIMISATION 4: RECHERCHE PARALLÈLE ASYNCHRONE
    all_combo_results = {}
    max_results_found = 0
    best_query = ""
    
    try:
        # Utiliser aiohttp pour les requêtes parallèles
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=5),  # Timeout global 5s
            connector=aiohttp.TCPConnector(limit=20)  # Max 20 connexions parallèles
        ) as session:
            
            # Créer toutes les tâches en parallèle
            tasks = []
            for query_combo, priority in search_queries:
                for index_uid in tenant_indexes:
                    task = search_single_index_async(session, index_uid, query_combo, company_id, limit=3)  # Limit réduit
                    tasks.append((task, query_combo, priority, index_uid))
            
            # 🚀 OPTIMISATION 5: EARLY STOPPING
            # Exécuter par batch et s'arrêter dès qu'on a assez de résultats
            batch_size = 10
            total_results = 0
            
            for i in range(0, len(tasks), batch_size):
                batch = tasks[i:i+batch_size]
                batch_results = await asyncio.gather(*[task[0] for task in batch], return_exceptions=True)
                
                for j, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        continue
                    
                    task_info = batch[j]
                    query_combo, priority, index_uid = task_info[1], task_info[2], task_info[3]
                    
                    if result and len(result.strip()) > 0:
                        if query_combo not in all_combo_results:
                            all_combo_results[query_combo] = {
                                "results": [],
                                "count": 0,
                                "priority": priority
                            }
                        
                        all_combo_results[query_combo]["results"].append(result)
                        all_combo_results[query_combo]["count"] += len(result.split('\n'))
                        total_results += 1
                
                # 🚀 EARLY STOPPING: Si on a assez de résultats, on s'arrête
                if total_results >= 20:  # Stop à 20 résultats
                    log3("[MEILI][EARLY_STOPPING]", {
                        "resultats_trouves": total_results,
                        "batch_traite": i // batch_size + 1,
                        "temps_ecoule": f"{time.time() - start_time:.2f}s"
                    })
                    break
        
        # 📊 FUSION INTELLIGENTE OPTIMISÉE
        if all_combo_results:
            unique_results = set()
            unique_documents = set()
            
            for combo_query, combo_data in all_combo_results.items():
                for result in combo_data["results"]:
                    result_lines = result.strip().split('\n')
                    for line in result_lines:
                        if line.strip() and len(line.strip()) > 10:
                            unique_results.add(line.strip())
                    
                    if result.strip() and len(result.strip()) > 50:
                        unique_documents.add(result.strip())
                
                if combo_data["count"] > max_results_found:
                    max_results_found = combo_data["count"]
                    best_query = combo_query
            
            final_unique_results = list(unique_results)
            final_result = "\n".join(final_unique_results)
            
            execution_time = time.time() - start_time
            
            log3("[MEILI][FUSION_OPTIMISEE]", {
                "combinaisons_avec_resultats": len(all_combo_results),
                "documents_distincts": len(unique_documents),
                "lignes_uniques_totales": len(final_unique_results),
                "meilleure_combinaison": best_query,
                "temps_execution": f"{execution_time:.2f}s",
                "objectif_atteint": execution_time < 5.0,
                "longueur_finale": len(final_result)
            })
            
            return final_result
        else:
            execution_time = time.time() - start_time
            log3("[MEILI][NO_RESULTS_OPTIMIZED]", {
                "query_originale": query,
                "mots_filtres": words,
                "combinaisons_testees": len(search_queries),
                "temps_execution": f"{execution_time:.2f}s"
            })
            return ""
    
    except Exception as e:
        execution_time = time.time() - start_time
        log3("[MEILI][ERROR_OPTIMIZED]", {
            "error": str(e),
            "query_originale": query,
            "temps_execution": f"{execution_time:.2f}s"
        })
        return ""


async def search_single_index_async(session: aiohttp.ClientSession, index_uid: str, query: str, company_id: str, limit: int = 3) -> str:
    """
    🚀 Recherche asynchrone dans un seul index (OPTIMISÉE)
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
            "limit": limit  # Réduit à 3 au lieu de 10
        }
        
        async with session.post(
            f"{meili_url}/indexes/{index_uid}/search",
            headers=headers,
            json=search_data,
            timeout=aiohttp.ClientTimeout(total=2)  # Timeout 2s par requête
        ) as response:
            
            if response.status == 200:
                results = await response.json()
                hits = results.get("hits", [])
                
                if hits:
                    # Formater les résultats (version allégée)
                    formatted_results = []
                    for hit in hits:
                        content = hit.get("content", "")
                        if content and len(content.strip()) > 0:
                            # Tronquer le contenu si trop long (optimisation)
                            if len(content) > 500:
                                content = content[:500] + "..."
                            formatted_results.append(content.strip())
                    
                    return "\n".join(formatted_results)
            
            return ""
            
    except Exception as e:
        return ""


# Fonction de fallback synchrone pour compatibilité
def search_meili_keywords(query: str, company_id: str, target_indexes: list = None, limit: int = 10) -> str:
    """
    🚀 Wrapper synchrone CORRIGÉ - évite les conflits asyncio
    """
    try:
        # Vérifier si on est déjà dans une boucle asyncio
        try:
            loop = asyncio.get_running_loop()
            # Si on est dans une boucle, utiliser la version synchrone directement
            log3("[MEILI][ASYNCIO_DETECTED]", "Boucle asyncio détectée, utilisation version synchrone")
            return search_meili_keywords_simple(query, company_id, target_indexes, limit)
        except RuntimeError:
            # Pas de boucle en cours, on peut créer une nouvelle boucle
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    search_meili_keywords_optimized(query, company_id, target_indexes, limit)
                )
                return result
            finally:
                loop.close()
                
    except Exception as e:
        log3("[MEILI][FALLBACK_ERROR]", {"error": str(e)})
        # Fallback vers la version synchrone simple
        return search_meili_keywords_simple(query, company_id, target_indexes, limit)


def search_meili_keywords_simple(query: str, company_id: str, target_indexes: list = None, limit: int = 10) -> str:
    """
    🚀 Version simple et rapide avec combinaisons (fallback synchrone)
    """
    import time
    start_time = time.time()
    
    log3("[MEILI][SIMPLE]", f"Recherche synchrone: {query}")
    
    from core.smart_stopwords import filter_query_for_meilisearch
    processed_keywords = filter_query_for_meilisearch(query)
    words = processed_keywords.split() if processed_keywords else []
    
    if not words:
        return ""
    
    # 🎯 COMBINAISONS SIMPLIFIÉES (max 10 au lieu de 42)
    search_queries = []
    
    # Priorité MAXIMALE: Tous les mots ensemble
    if len(words) > 1:
        search_queries.append((" ".join(words), len(words)))
    
    # Priorité HAUTE: Combinaisons de 2-3 mots (limitées à 5)
    if len(words) >= 2:
        from itertools import combinations
        # Combinaisons de 3 mots max 3
        if len(words) >= 3:
            combos_3 = list(combinations(words, 3))[:3]
            for combo in combos_3:
                search_queries.append((" ".join(combo), 3))
        
        # Combinaisons de 2 mots max 3
        combos_2 = list(combinations(words, 2))[:3]
        for combo in combos_2:
            search_queries.append((" ".join(combo), 2))
    
    # Mots individuels (max 3)
    for word in words[:3]:
        search_queries.append((word, 1))
    
    # Trier par priorité et limiter à 10
    search_queries.sort(key=lambda x: x[1], reverse=True)
    search_queries = search_queries[:10]
    
    # Index prioritaires (5 au lieu de 10)
    if target_indexes and len(target_indexes) > 0:
        tenant_indexes = target_indexes[:3]  # Limiter à 3 index
    else:
        tenant_indexes = [
            f"products_{company_id}",
            f"delivery_{company_id}",
            f"support_paiement_{company_id}"
        ]
    
    # 🚀 RECHERCHE SYNCHRONE AVEC COMBINAISONS
    all_results = set()
    results_found = 0
    
    for query_combo, priority in search_queries:
        for index_uid in tenant_indexes:
            try:
                result = search_single_index_meilisearch_simple(index_uid, query_combo, company_id, limit=3)
                if result and len(result.strip()) > 0:
                    # Ajouter les lignes uniques
                    result_lines = result.strip().split('\n')
                    for line in result_lines:
                        if line.strip() and len(line.strip()) > 10:
                            all_results.add(line.strip())
                    results_found += 1
                    
                    # Early stopping si on a assez de résultats
                    if results_found >= 5:
                        break
            except Exception as e:
                continue
        
        if results_found >= 5:
            break
    
    # Fusionner les résultats
    if all_results:
        final_result = "\n".join(list(all_results))
        execution_time = time.time() - start_time
        
        log3("[MEILI][SIMPLE_SUCCESS]", {
            "combinaisons_testees": len(search_queries),
            "resultats_uniques": len(all_results),
            "temps_execution": f"{execution_time:.2f}s",
            "longueur_finale": len(final_result)
        })
        
        return final_result
    else:
        execution_time = time.time() - start_time
        log3("[MEILI][SIMPLE_NO_RESULTS]", {
            "query_originale": query,
            "combinaisons_testees": len(search_queries),
            "temps_execution": f"{execution_time:.2f}s"
        })
        return ""


def search_single_index_meilisearch_simple(index_uid: str, query: str, company_id: str, limit: int = 5) -> str:
    """
    Version simple et rapide pour fallback
    """
    try:
        import requests
        
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
            timeout=3  # Timeout court
        )
        
        if response.status_code == 200:
            results = response.json()
            hits = results.get("hits", [])
            
            if hits:
                formatted_results = []
                for hit in hits:
                    content = hit.get("content", "")
                    if content and len(content.strip()) > 0:
                        formatted_results.append(content.strip())
                
                return "\n".join(formatted_results)
        
        return ""
        
    except Exception as e:
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
        result = search_single_index_meilisearch_simple(
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
