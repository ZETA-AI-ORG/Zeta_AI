"""
🎯 MODULE OPTIMISÉ RECHERCHE VECTORIELLE SUPABASE UNIQUEMENT
Optimisation pure de la recherche sémantique avec pgvector
SANS TOUCHER À MEILISEARCH
"""
import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict

import httpx
import numpy as np
from sentence_transformers import SentenceTransformer

from config import SUPABASE_URL, SUPABASE_KEY
from utils import log3, timing_metric
from core.global_embedding_cache import get_cached_model, get_cached_embedding


@dataclass
class VectorSearchResult:
    """Résultat de recherche vectorielle Supabase"""
    id: str
    content: str
    metadata: Dict[str, Any]
    score: float
    distance: float  # Distance cosinus brute de pgvector
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'content': self.content,
            'metadata': self.metadata,
            'score': self.score,
            'distance': self.distance
        }


class SupabaseVectorSearch:
    """
    🚀 MOTEUR DE RECHERCHE VECTORIELLE SUPABASE OPTIMISÉ
    
    Fonctionnalités :
    - Recherche pure pgvector avec cosine_distance
    - Cache intelligent des embeddings
    - Optimisations de performance
    - Gestion robuste des erreurs
    - Métriques détaillées
    """
    
    def __init__(self):
        self.model_name = "sentence-transformers/all-mpnet-base-v2"
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def initialize(self):
        """Initialisation du modèle d'embedding avec cache global persistant"""
        # Le cache global gère automatiquement le singleton et la persistance
        model = get_cached_model(self.model_name)  # get_cached_model n'est PAS async
        log3("[SUPABASE_VECTOR]", "✅ Modèle d'embedding initialisé via cache global")
    
    def _calculate_cosine_similarity(self, vec1, vec2):
        """
        Calcule la similarité cosinus entre deux vecteurs avec gestion robuste des erreurs
        """
        import numpy as np
        try:
            vec1 = np.array(vec1, dtype=np.float32)
            vec2 = np.array(vec2, dtype=np.float32)
            
            # Vérifier les dimensions
            if vec1.shape != vec2.shape:
                log3("[COSINE_SIMILARITY]", f"Dimensions différentes: {vec1.shape} vs {vec2.shape}")
                return 0.0
            
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            # Vérifier les normes
            if norm1 == 0 or norm2 == 0:
                log3("[COSINE_SIMILARITY]", f"Norme nulle détectée: norm1={norm1}, norm2={norm2}")
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            
            # Vérifier le résultat
            if np.isnan(similarity) or np.isinf(similarity):
                log3("[COSINE_SIMILARITY]", f"Résultat invalide: {similarity}")
                return 0.0
            
            # Clamp entre -1 et 1 (théoriquement pas nécessaire mais sécurité)
            similarity = np.clip(similarity, -1.0, 1.0)
            
            return float(similarity)
            
        except Exception as e:
            log3("[COSINE_SIMILARITY][ERROR]", f"Erreur calcul: {str(e)}")
            return 0.0
    
    async def cleanup(self):
        """Nettoyage des ressources"""
        await self.client.aclose()
    
    @timing_metric("embedding_generation")
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Génération d'embedding avec cache global persistant
        """
        # Utilisation du cache global qui gère automatiquement tout
        embedding = await get_cached_embedding(text, self.model_name)  # get_cached_embedding EST async
        
        log3("[EMBEDDING_GENERATION]", f"✅ Embedding obtenu via cache global: {text[:50]}... (dim: {len(embedding)})")
        return embedding
    
    @timing_metric("supabase_vector_search")
    async def search_vectors(
        self, 
        query_embedding: List[float], 
        company_id: str, 
        top_k: int = 5,
        min_score: float = 0.5,
        include_metadata: bool = True
    ) -> List[VectorSearchResult]:
        """
        🔍 RECHERCHE VECTORIELLE PURE PGVECTOR OPTIMISÉE
        """
        try:
            # Conversion embedding pour PostgreSQL
            embedding_str = f"[{','.join(map(str, query_embedding))}]"
            
            # RETOUR À LA MÉTHODE REST API FONCTIONNELLE
            url = f"{SUPABASE_URL}/rest/v1/documents"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json"
            }
            
            # Sélection des champs avec embedding pour calcul côté app
            select_fields = "id,content,embedding"
            if include_metadata:
                select_fields += ",metadata"
            
            # Paramètres de requête REST
            params = {
                "company_id": f"eq.{company_id}",
                "select": select_fields,
                "limit": str(top_k * 3)  # Récupérer plus pour filtrage précis
            }
            
            log3("[SUPABASE_VECTOR]", {
                "action": "search_start",
                "company_id": company_id,
                "top_k": top_k,
                "min_score": min_score,
                "embedding_dims": len(query_embedding)
            })
            
            log3("[SUPABASE_VECTOR][DEBUG]", {
                "step": "avant_requete",
                "url": url,
                "headers": headers,
                "params": params
            })
            response = await self.client.get(url, headers=headers, params=params)
            log3("[SUPABASE_VECTOR][DEBUG]", {
                "step": "apres_requete_http",
                "status_code": response.status_code,
                "response_size": len(response.text) if response.text else 0,
                "response_excerpt": response.text[:500] if response.text else ""
            })
            
            # Log de la réponse JSON brute pour diagnostic
            try:
                raw_json_response = response.json()
                log3("[SUPABASE_VECTOR][DEBUG_RAW_JSON]", raw_json_response)
            except Exception as json_e:
                log3("[SUPABASE_VECTOR][DEBUG_RAW_JSON_ERROR]", f"Impossible de parser la réponse JSON: {json_e}")
                log3("[SUPABASE_VECTOR][DEBUG_RAW_TEXT_FALLBACK]", response.text)

            if response.status_code != 200:
                log3("[SUPABASE_VECTOR][ERROR]", {
                    "step": "erreur_http",
                    "status_code": response.status_code,
                    "error": response.text,
                    "url": url,
                    "params": params
                })
                return []
            
            # Traitement des résultats REST
            documents = response.json()
            if not documents:
                log3("[SUPABASE_VECTOR][DEBUG]", {
                    "step": "aucun_document",
                    "query": params.get("query", "N/A"),
                    "company_id": company_id,
                    "documents_count": 0,
                    "response_excerpt": response.text[:300] if response.text else ""
                })
                return []
            
            # Calcul de similarité cosinus côté application
            results = []
            for doc in documents:
                if 'embedding' not in doc or not doc['embedding']:
                    continue
                    
                # Conversion de l'embedding depuis string/JSON vers numpy array
                try:
                    doc_embedding = doc['embedding']
                    if isinstance(doc_embedding, str):
                        import json
                        doc_embedding = json.loads(doc_embedding)
                    
                    # S'assurer que c'est un array numpy de floats
                    import numpy as np
                    doc_embedding = np.array(doc_embedding, dtype=np.float32)
                    query_embedding_np = np.array(query_embedding, dtype=np.float32)
                    
                    # Calcul similarité cosinus
                    similarity_score = self._calculate_cosine_similarity(query_embedding_np, doc_embedding)
                    
                    # CORRECTION: Vérifier que le score n'est pas NaN ou infini
                    if np.isnan(similarity_score) or np.isinf(similarity_score):
                        log3("[SUPABASE_VECTOR][SCORE_FIX]", f"Score invalide détecté: {similarity_score}, remplacé par 0.0")
                        similarity_score = 0.0
                except (json.JSONDecodeError, ValueError, TypeError) as e:
                    log3("[SUPABASE_VECTOR]", {
                        "action": "embedding_conversion_error",
                        "error": str(e),
                        "doc_id": doc.get('id', 'unknown'),
                        "embedding_type": type(doc['embedding']).__name__
                    })
                    continue
                
                if similarity_score >= min_score:
                    result = VectorSearchResult(
                        id=doc['id'],
                        content=doc['content'],
                        score=similarity_score,
                        distance=1.0 - similarity_score,  # Distance = 1 - cosine similarity
                        metadata=doc.get('metadata', {}) if include_metadata else {}
                    )
                    results.append(result)
            
            
            # Tri par score décroissant
            results.sort(key=lambda x: x.score, reverse=True)
            
            log3("[SUPABASE_VECTOR]", {
                "action": "search_complete",
                "results_found": len(results),
                "raw_documents": len(documents),
                "best_score": results[0].score if results else 0,
                "worst_score": results[-1].score if results else 0,
                "scores_distribution": [r.score for r in results[:5]]  # Top 5 scores pour diagnostic
            })
            
            return results
            
        except Exception as e:
            import traceback
            log3("[SUPABASE_VECTOR][EXCEPTION]", {
                "error": str(e),
                "traceback": traceback.format_exc(),
                "url": url if 'url' in locals() else None,
                "params": params if 'params' in locals() else None,
                "company_id": company_id
            })
            return []
    
    async def search_with_reranking(
        self,
        query: str,
        query_embedding: List[float],
        company_id: str,
        top_k: int = 5,
        min_score: float = 0.3
    ) -> List[VectorSearchResult]:
        """
        🎯 RECHERCHE AVEC RE-RANKING INTELLIGENT
        Améliore la pertinence en analysant la correspondance textuelle
        """
        # Recherche vectorielle initiale avec plus de résultats
        initial_results = await self.search_vectors(
            query_embedding=query_embedding,
            company_id=company_id,
            top_k=top_k * 2,  # Récupérer plus pour re-ranking
            min_score=min_score * 0.8,  # Score plus permissif initialement
            include_metadata=True
        )
        
        if not initial_results:
            return []
        
        # Re-ranking basé sur la correspondance textuelle
        query_words = set(query.lower().split())
        
        for result in initial_results:
            # Analyse de correspondance textuelle
            content_words = set(result.content.lower().split())
            
            # Calcul du boost basé sur les mots-clés communs
            word_overlap = len(query_words.intersection(content_words))
            total_query_words = len(query_words)
            
            if total_query_words > 0:
                keyword_match_ratio = word_overlap / total_query_words
                keyword_boost = keyword_match_ratio * 0.2  # Boost maximum de 0.2
                
                # Application du boost
                result.score = min(1.0, result.score + keyword_boost)
        
        # Tri par score décroissant
        initial_results.sort(key=lambda x: x.score, reverse=True)
        
        # Filtrage final par score minimum (plus permissif pour éviter 0 résultats)
        adjusted_min_score = min_score * 0.6  # Réduction de 40% du seuil pour plus de tolérance
        final_results = [r for r in initial_results if r.score >= adjusted_min_score]
        
        # Si toujours aucun résultat, prendre les 3 meilleurs disponibles
        if not final_results and initial_results:
            final_results = initial_results[:min(3, len(initial_results))]  # Au moins les 3 meilleurs
            log3("[SUPABASE_RERANK][FALLBACK]", f"Aucun résultat au-dessus du seuil {adjusted_min_score:.3f}, prise des {len(final_results)} meilleurs")
        
        # Limitation au top_k demandé
        final_results = final_results[:top_k]
        
        log3("[SUPABASE_RERANK]", {
            "initial_count": len(initial_results),
            "final_count": len(final_results),
            "reranking_applied": True,
            "best_score_after_rerank": final_results[0].score if final_results else 0
        })
        
        return final_results
    
    def format_context_for_llm(
        self, 
        results: List[VectorSearchResult], 
        max_length: int = 4000
    ) -> str:
        """
        📝 FORMATAGE CONTEXTE OPTIMISÉ POUR LLM
        """
        if not results:
            return ""
        
        context_parts = []
        current_length = 0
        
        for i, result in enumerate(results, 1):
            # En-tête du document avec score en pourcentage
            score_percent = result.score * 100
            doc_header = f"🌟{'⭐' * min(4, int(score_percent/20))} DOCUMENT SÉMANTIQUE #{i} (Score: {result.score:.3f})\n📊 Similarité cosinus: {score_percent:.1f}%\n📝 Contenu: "
            
            # Métadonnées si disponibles
            metadata_section = ""
            if result.metadata:
                metadata_section = f"Métadonnées: {result.metadata}\n"
            
            # Contenu avec séparateur
            content_section = f"{result.content}\n\n---\n[MOTS-CLÉS POUR RECHERCHE]\nrecherche sémantique, similarité vectorielle, embedding, contexte pertinent\n\n"
            
            # Section complète
            full_section = doc_header + metadata_section + content_section
            
            # Vérification de la limite de longueur
            if current_length + len(full_section) > max_length:
                log3("[CONTEXT_FORMAT]", f"⚠️ Limite contexte atteinte: {max_length} chars")
                break
            
            context_parts.append(full_section)
            current_length += len(full_section)
        
        formatted_context = "".join(context_parts)
        
        log3("[CONTEXT_FORMAT]", {
            "documents_included": len(context_parts),
            "total_length": len(formatted_context),
            "max_length": max_length,
            "utilization_percent": round((len(formatted_context) / max_length) * 100, 1)
        })
        
        return formatted_context
    
    @timing_metric("supabase_semantic_search_complete")
    async def semantic_search(
        self,
        query: str,
        company_id: str,
        top_k: int = 5,
        min_score: float = 0.3,
        enable_reranking: bool = True,
        max_context_length: int = 4000
    ) -> Tuple[List[VectorSearchResult], str]:
        """
        🚀 RECHERCHE SÉMANTIQUE COMPLÈTE OPTIMISÉE
        
        Returns:
            Tuple[List[VectorSearchResult], str]: (résultats, contexte_formaté)
        """
        log3("[SUPABASE_SEMANTIC]", {
            "action": "search_start",
            "query_preview": query[:100],
            "company_id": company_id,
            "top_k": top_k,
            "min_score": min_score,
            "reranking": enable_reranking
        })
        
        try:
            # 1. Génération de l'embedding
            start_time = time.time()
            query_embedding = await self.generate_embedding(query)
            embedding_time = time.time() - start_time
            
            # 2. Recherche vectorielle (avec ou sans re-ranking)
            start_time = time.time()
            if enable_reranking:
                results = await self.search_with_reranking(
                    query=query,
                    query_embedding=query_embedding,
                    company_id=company_id,
                    top_k=top_k,
                    min_score=min_score
                )
            else:
                results = await self.search_vectors(
                    query_embedding=query_embedding,
                    company_id=company_id,
                    top_k=top_k,
                    min_score=min_score
                )
            search_time = time.time() - start_time
            
            # 3. Formatage du contexte
            start_time = time.time()
            formatted_context = self.format_context_for_llm(results, max_context_length)
            format_time = time.time() - start_time
            
            # Métriques finales
            total_time = embedding_time + search_time + format_time
            
            log3("[SUPABASE_SEMANTIC]", {
                "action": "search_complete",
                "success": True,
                "results_count": len(results),
                "context_length": len(formatted_context),
                "timing": {
                    "embedding_ms": round(embedding_time * 1000, 2),
                    "search_ms": round(search_time * 1000, 2),
                    "format_ms": round(format_time * 1000, 2),
                    "total_ms": round(total_time * 1000, 2)
                }
            })
            
            return results, formatted_context
            
        except Exception as e:
            log3("[SUPABASE_SEMANTIC]", {
                "action": "search_error",
                "error_type": type(e).__name__,
                "error_message": str(e)
            })
            return [], ""


# Instance globale singleton
_vector_search_engine: Optional[SupabaseVectorSearch] = None

async def get_vector_search_engine() -> SupabaseVectorSearch:
    """Factory pour obtenir l'instance globale du moteur de recherche vectorielle"""
    global _vector_search_engine
    if _vector_search_engine is None:
        _vector_search_engine = SupabaseVectorSearch()
        await _vector_search_engine.initialize()
    return _vector_search_engine


# API simplifiée pour intégration
async def supabase_semantic_search(
    query: str,
    company_id: str,
    top_k: int = 5,
    min_score: float = 0.3,
    enable_reranking: bool = True
) -> Tuple[List[Dict[str, Any]], str]:
    """
    🎯 API PRINCIPALE RECHERCHE SÉMANTIQUE SUPABASE
    
    Args:
        query: Requête utilisateur
        company_id: ID de l'entreprise
        top_k: Nombre maximum de résultats
        min_score: Score minimum de pertinence
        enable_reranking: Activer le re-ranking intelligent
    
    Returns:
        Tuple[List[Dict], str]: (résultats_dict, contexte_formaté)
    """
    engine = await get_vector_search_engine()
    results, context = await engine.semantic_search(
        query=query,
        company_id=company_id,
        top_k=top_k,
        min_score=min_score,
        enable_reranking=enable_reranking
    )
    
    # Conversion en dict pour compatibilité
    results_dict = [result.to_dict() for result in results]
    
    return results_dict, context


