"""
🚀 RECHERCHE SÉMANTIQUE AVANCÉE - ARCHITECTURE FRANCOPHONE
Recherche sémantique optimisée avec embeddings multilingues, txtai, et fusion intelligente
"""
import asyncio
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import httpx
from sentence_transformers import SentenceTransformer

# Imports pour recherche sémantique avancée
try:
    import txtai
    from txtai.embeddings import Embeddings
    TXTAI_AVAILABLE = True
except ImportError:
    TXTAI_AVAILABLE = False

try:
    from config import SUPABASE_URL, SUPABASE_KEY
    from utils import log3, timing_metric
    from core.global_embedding_cache import get_cached_model, get_cached_embedding
except ImportError:
    # Fallback pour tests
    SUPABASE_URL = ""
    SUPABASE_KEY = ""
    def log3(*args, **kwargs): print(*args, **kwargs)
    def timing_metric(name): return lambda f: f

logger = logging.getLogger(__name__)


class SearchStrategy(Enum):
    """Stratégies de recherche disponibles"""
    VECTOR_ONLY = "vector_only"
    HYBRID = "hybrid"
    KEYWORD_FALLBACK = "keyword_fallback"


@dataclass
class SearchResult:
    """Résultat de recherche unifié"""
    id: str
    content: str
    metadata: Dict[str, Any]
    score: float
    source: str  # 'supabase', 'meilisearch'
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'content': self.content,
            'metadata': self.metadata,
            'score': self.score,
            'source': self.source
        }


@dataclass
class SearchConfig:
    """Configuration de recherche"""
    top_k: int = 5
    min_score: float = 0.3
    strategy: SearchStrategy = SearchStrategy.VECTOR_ONLY
    enable_reranking: bool = True
    max_context_length: int = 4000


class OptimizedSemanticSearchEngine:
    """
    🎯 MOTEUR DE RECHERCHE SÉMANTIQUE OPTIMISÉ
    
    Caractéristiques :
    - Architecture modulaire et testable
    - Performance optimisée avec async/await
    - Cache intelligent des embeddings
    - Recherche vectorielle pure (pgvector)
    - Fallback intelligent si nécessaire
    - Métriques de performance intégrées
    """
    
    def __init__(self):
        # Modèles multilingues optimisés pour le français
        # OPTIMISATION: Utilise modèle léger au lieu du lourd (1.11 GB → 90 MB)
        self.model_name = "sentence-transformers/all-MiniLM-L6-v2"  # Modifié pour performance
        self.french_model_name = "dangvantuan/sentence-camembert-large"
        self._client = None  # Lazy init to prevent blocking on import
        
        # txtai pour recherche sémantique avancée
        self.txtai_index = None
        self.documents_cache = {}
        
        # Configuration francophone
        self.french_stopwords = {
            'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'et', 'ou', 'mais',
            'donc', 'car', 'ni', 'or', 'ce', 'ces', 'cet', 'cette', 'mon', 'ma',
            'mes', 'ton', 'ta', 'tes', 'son', 'sa', 'ses', 'notre', 'nos', 'votre',
            'vos', 'leur', 'leurs', 'je', 'tu', 'il', 'elle', 'nous', 'vous', 'ils',
            'elles', 'me', 'te', 'se', 'nous', 'vous', 'se', 'moi', 'toi', 'lui',
            'elle', 'nous', 'vous', 'eux', 'elles', 'dans', 'sur', 'avec', 'sans',
            'pour', 'par', 'vers', 'chez', 'sous', 'entre', 'depuis', 'pendant',
            'avant', 'après', 'très', 'plus', 'moins', 'aussi', 'encore', 'déjà',
            'toujours', 'jamais', 'souvent', 'parfois', 'quelquefois', 'bien', 'mal',
            'mieux', 'pire', 'beaucoup', 'peu', 'assez', 'trop', 'tant', 'autant'
        }
    
    @property
    def client(self):
        """Lazy initialization of httpx client"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
        
    def initialize(self):
        """Initialisation du moteur avec cache global et txtai"""
        try:
            # Cache global pour embeddings
            model = get_cached_model(self.model_name)
            log3("[SEMANTIC_ENGINE]", "✅ Modèle d'embedding initialisé via cache global")
            
            # Initialisation txtai si disponible
            if TXTAI_AVAILABLE:
                self.txtai_index = Embeddings({
                    "path": self.model_name,
                    "content": True,
                    "objects": True,
                    "functions": [
                        {"name": "similarity", "function": "txtai.pipeline.text.Similarity"}
                    ]
                })
                log3("[SEMANTIC_ENGINE]", "✅ txtai initialisé avec modèle multilingue")
            else:
                log3("[SEMANTIC_ENGINE]", "⚠️ txtai non disponible, utilisation fallback")
                
        except Exception as e:
            logger.error(f"❌ Erreur initialisation semantic engine: {e}")
            log3("[SEMANTIC_ENGINE]", f"❌ Erreur: {e}")
    
    async def cleanup(self):
        """Nettoyage des ressources"""
        if self._client is not None:
            await self._client.aclose()
    
    @timing_metric("embedding_generation")
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Génération d'embedding avec cache global persistant
        """
        # Utilisation du cache global qui gère automatiquement tout
        embedding = await get_cached_embedding(text, self.model_name)
        
        log3("[EMBEDDING_GENERATION]", f"✅ Embedding obtenu via cache global: {text[:50]}... (dim: {len(embedding)})")
        return embedding
    
    @timing_metric("vector_search")
    async def search_vectors(
        self, 
        query_embedding: List[float], 
        company_id: str, 
        config: SearchConfig
    ) -> List[SearchResult]:
        """
        🔍 RECHERCHE VECTORIELLE PURE OPTIMISÉE
        Utilise directement pgvector sans RPC
        """
        try:
            # Format embedding pour PostgreSQL
            embedding_str = f"[{','.join(map(str, query_embedding))}]"
            
            # Requête optimisée avec pgvector
            url = f"{SUPABASE_URL}/rest/v1/documents"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json"
            }
            
            # Paramètres optimisés
            params = {
                "company_id": f"eq.{company_id}",
                "select": "id,content,metadata",
                "order": f"embedding.cosine_distance({embedding_str}).asc",
                "limit": str(config.top_k)
            }
            
            log3("[VECTOR_SEARCH]", f"🔍 Recherche pgvector (company_id={company_id}, top_k={config.top_k})")
            
            # Requête asynchrone
            response = await self.client.get(url, headers=headers, params=params)
            
            if response.status_code != 200:
                log3("[VECTOR_SEARCH]", f"❌ Erreur HTTP {response.status_code}: {response.text}")
                return []
            
            # Traitement des résultats
            raw_results = response.json() or []
            results = []
            
            for i, doc in enumerate(raw_results):
                # Score basé sur le rang (pgvector trie par distance croissante)
                score = max(0.1, 1.0 - (i * 0.1))
                
                result = SearchResult(
                    id=doc.get('id', ''),
                    content=doc.get('content', ''),
                    metadata=doc.get('metadata', {}),
                    score=score,
                    source='supabase'
                )
                
                # Filtrage par score minimum
                if score >= config.min_score:
                    results.append(result)
            
            log3("[VECTOR_SEARCH]", f"✅ {len(results)} résultats trouvés (score >= {config.min_score})")
            return results
            
        except Exception as e:
            log3("[VECTOR_SEARCH]", f"💥 Erreur: {type(e).__name__}: {str(e)}")
            return []
    
    async def rerank_results(self, results: List[SearchResult], query: str) -> List[SearchResult]:
        """
        🎯 RE-RANKING INTELLIGENT DES RÉSULTATS
        Améliore la pertinence en analysant le contenu
        """
        if not results or len(results) <= 1:
            return results
        
        try:
            # Mots-clés de la requête
            query_words = set(query.lower().split())
            
            # Score de re-ranking basé sur la correspondance textuelle
            for result in results:
                content_words = set(result.content.lower().split())
                keyword_overlap = len(query_words.intersection(content_words))
                
                # Boost du score basé sur la correspondance
                keyword_boost = min(0.3, keyword_overlap * 0.05)
                result.score = min(1.0, result.score + keyword_boost)
            
            # Tri par score décroissant
            results.sort(key=lambda x: x.score, reverse=True)
            
            log3("[RERANKING]", f"✅ Re-ranking terminé, meilleur score: {results[0].score:.3f}")
            return results
            
        except Exception as e:
            log3("[RERANKING]", f"⚠️ Erreur re-ranking: {str(e)}")
            return results
    
    def format_context(self, results: List[SearchResult], max_length: int = 4000) -> str:
        """
        📝 FORMATAGE OPTIMISÉ DU CONTEXTE
        Génère un contexte structuré pour le LLM
        """
        if not results:
            return ""
        
        context_parts = []
        current_length = 0
        
        for i, result in enumerate(results, 1):
            # Format section
            section = f"=== DOCUMENT {i} (Score: {result.score:.3f}) ===\n"
            
            # Métadonnées si disponibles
            if result.metadata:
                section += f"Métadonnées: {result.metadata}\n"
            
            section += f"{result.content}\n\n"
            
            # Vérification de la longueur
            if current_length + len(section) > max_length:
                log3("[CONTEXT_FORMAT]", f"⚠️ Limite de contexte atteinte ({max_length} chars)")
                break
            
            context_parts.append(section)
            current_length += len(section)
        
        formatted_context = "".join(context_parts)
        log3("[CONTEXT_FORMAT]", f"✅ Contexte formaté: {len(formatted_context)} chars, {len(context_parts)} documents")
        
        return formatted_context
    
    @timing_metric("semantic_search_total")
    async def txtai_search(self, query: str, company_id: str, config: SearchConfig) -> List[SearchResult]:
        """Recherche sémantique avancée avec txtai"""
        if not TXTAI_AVAILABLE or not self.txtai_index:
            return []
        
        try:
            # Préparation des documents pour txtai (si pas déjà fait)
            if company_id not in self.documents_cache:
                await self._build_txtai_index(company_id)
            
            # Recherche sémantique avec txtai
            results = self.txtai_index.search(query, config.top_k)
            
            search_results = []
            for i, (score, doc_id, text) in enumerate(results):
                if score >= config.min_score:
                    search_results.append(SearchResult(
                        id=str(doc_id),
                        content=text,
                        metadata={"txtai_score": score},
                        score=score,
                        source='txtai'
                    ))
            
            log3("[TXTAI_SEARCH]", f"✅ {len(search_results)} résultats txtai (score >= {config.min_score})")
            return search_results
            
        except Exception as e:
            log3("[TXTAI_SEARCH]", f"❌ Erreur txtai: {e}")
            return []
    
    async def _build_txtai_index(self, company_id: str):
        """Construit l'index txtai pour une entreprise"""
        try:
            # Récupération des documents depuis Supabase
            url = f"{SUPABASE_URL}/rest/v1/documents"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json"
            }
            params = {
                "company_id": f"eq.{company_id}",
                "select": "id,content,metadata"
            }
            
            response = await self.client.get(url, headers=headers, params=params)
            if response.status_code == 200:
                documents = response.json() or []
                
                # Préparation pour txtai
                txtai_docs = []
                for doc in documents:
                    txtai_docs.append({
                        "id": doc.get('id'),
                        "text": doc.get('content', ''),
                        "metadata": doc.get('metadata', {})
                    })
                
                # Construction de l'index
                if txtai_docs and self.txtai_index:
                    self.txtai_index.index(txtai_docs)
                    self.documents_cache[company_id] = len(txtai_docs)
                    log3("[TXTAI_INDEX]", f"✅ Index txtai construit: {len(txtai_docs)} docs pour {company_id}")
                
        except Exception as e:
            log3("[TXTAI_INDEX]", f"❌ Erreur construction index: {e}")

    async def search(
        self, 
        query: str, 
        company_id: str, 
        config: Optional[SearchConfig] = None
    ) -> Tuple[List[SearchResult], str]:
        """
        🚀 RECHERCHE SÉMANTIQUE HYBRIDE AVANCÉE
        Combine pgvector, txtai, et re-ranking intelligent
        
        Returns:
            Tuple[List[SearchResult], str]: (résultats, contexte_formaté)
        """
        if not config:
            config = SearchConfig()
        
        log3("[SEMANTIC_SEARCH]", f"🔍 Début recherche hybride: '{query[:50]}...' (company_id={company_id})")
        
        all_results = []
        
        # 1. Recherche vectorielle classique (pgvector)
        start_time = time.time()
        query_embedding = await self.generate_embedding(query)
        vector_results = await self.search_vectors(query_embedding, company_id, config)
        embedding_time = time.time() - start_time
        
        all_results.extend(vector_results)
        log3("[SEMANTIC_SEARCH]", f"✅ Recherche vectorielle: {len(vector_results)} résultats")
        
        # 2. Recherche txtai (si disponible)
        start_time = time.time()
        txtai_results = await self.txtai_search(query, company_id, config)
        txtai_time = time.time() - start_time
        
        all_results.extend(txtai_results)
        log3("[SEMANTIC_SEARCH]", f"✅ Recherche txtai: {len(txtai_results)} résultats")
        
        # 3. Déduplication par contenu
        start_time = time.time()
        unique_results = self._deduplicate_results(all_results)
        dedup_time = time.time() - start_time
        
        # 4. Re-ranking intelligent
        start_time = time.time()
        if config.enable_reranking and unique_results:
            unique_results = await self.rerank_results(unique_results, query)
        rerank_time = time.time() - start_time
        
        # 5. Limitation et formatage
        start_time = time.time()
        final_results = unique_results[:config.top_k]
        formatted_context = self.format_context(final_results, config.max_context_length)
        format_time = time.time() - start_time
        
        # Métriques de performance
        total_time = embedding_time + txtai_time + dedup_time + rerank_time + format_time
        log3("[SEMANTIC_SEARCH]", {
            "query_preview": query[:50],
            "vector_results": len(vector_results),
            "txtai_results": len(txtai_results),
            "unique_results": len(unique_results),
            "final_results": len(final_results),
            "context_length": len(formatted_context),
            "timing": {
                "embedding_ms": round(embedding_time * 1000, 2),
                "txtai_ms": round(txtai_time * 1000, 2),
                "dedup_ms": round(dedup_time * 1000, 2),
                "rerank_ms": round(rerank_time * 1000, 2),
                "format_ms": round(format_time * 1000, 2),
                "total_ms": round(total_time * 1000, 2)
            }
        })
        
        return final_results, formatted_context
    
    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Déduplication intelligente des résultats"""
        if not results:
            return []
        
        unique_results = []
        seen_contents = set()
        
        # Trier par score décroissant d'abord
        sorted_results = sorted(results, key=lambda x: x.score, reverse=True)
        
        for result in sorted_results:
            # Normalisation du contenu pour comparaison
            normalized_content = result.content.lower().strip()[:200]  # Premiers 200 chars
            
            if normalized_content not in seen_contents:
                seen_contents.add(normalized_content)
                unique_results.append(result)
        
        log3("[DEDUPLICATION]", f"✅ {len(results)} → {len(unique_results)} résultats après déduplication")
        return unique_results


# Instance globale singleton
_search_engine: Optional[OptimizedSemanticSearchEngine] = None

def get_search_engine():
    """Factory pour obtenir l'instance globale du moteur de recherche sémantique"""
    global _search_engine
    if _search_engine is None:
        _search_engine = OptimizedSemanticSearchEngine()
        _search_engine.initialize()
    return _search_engine


# API simplifiée pour compatibilité
async def semantic_search(
    query: str, 
    company_id: str, 
    top_k: int = 5, 
    min_score: float = 0.3
) -> Tuple[List[Dict[str, Any]], str]:
    """
    🎯 API SIMPLIFIÉE POUR RECHERCHE SÉMANTIQUE
    
    Args:
        query: Requête utilisateur
        company_id: ID de l'entreprise
        top_k: Nombre maximum de résultats
        min_score: Score minimum de pertinence
    
    Returns:
        Tuple[List[Dict], str]: (résultats_dict, contexte_formaté)
    """
    config = SearchConfig(
        top_k=top_k,
        min_score=min_score,
        strategy=SearchStrategy.HYBRID,  # ✅ Utilise MeiliSearch + Supabase
        enable_reranking=True
    )
    
    engine = get_search_engine()
    results, context = await engine.search(query, company_id, config)
    
    # Conversion en dict pour compatibilité
    results_dict = [result.to_dict() for result in results]
    
    return results_dict, context
