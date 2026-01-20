"""
🚀 SCALABLE RAG ENGINE - MOTEUR UNIFIÉ MULTI-TENANT
Pipeline complet: MeiliSearch + Supabase + Reranking + Cache + Monitoring
Architecture production-ready pour 1 à 1000 entreprises
"""
import asyncio
import time
import uuid
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass

from utils import log3
from .tenant_config_manager import get_tenant_config
from .scalable_meilisearch_engine import get_meilisearch_engine, MeiliSearchResult
from .scalable_supabase_engine import get_supabase_engine, SemanticResult
from .scalable_reranker import get_reranker, RerankResult
from .intelligent_cache_system_v2 import get_intelligent_cache
from .production_monitoring import record_query_metrics


@dataclass
class RAGResponse:
    """Réponse complète du système RAG"""
    query_id: str
    company_id: str
    query: str
    documents: List[RerankResult]
    response_text: str
    confidence_score: float
    
    # Métriques de performance
    total_time_ms: float
    search_time_ms: float
    rerank_time_ms: float
    llm_time_ms: float
    
    # Métadonnées
    sources_used: List[str]  # ["meilisearch", "supabase"]
    cache_hit: bool
    cache_level: Optional[str]
    
    # Coûts
    llm_tokens_input: int = 0
    llm_tokens_output: int = 0
    llm_cost_usd: float = 0.0


class ScalableRAGEngine:
    """
    🚀 MOTEUR RAG SCALABLE MULTI-TENANT
    
    Pipeline optimisé:
    1. 🔍 Recherche hybride (MeiliSearch + Supabase)
    2. 🎯 Reranking intelligent (cross-encoder)
    3. 🧠 Cache multi-niveau
    4. 🤖 Génération LLM optimisée
    5. 📊 Monitoring complet
    
    Scalabilité: 1 à 1000+ entreprises
    Performance: < 1s en moyenne, < 100ms avec cache
    """
    
    def __init__(self):
        # Composants du pipeline
        self.meilisearch = get_meilisearch_engine()
        self.supabase = get_supabase_engine()
        self.reranker = get_reranker()
        self.cache = get_intelligent_cache()
        
        # Client LLM (lazy loading)
        self.llm_client = None
        
        log3("[RAG_SCALABLE]", "✅ Moteur RAG scalable initialisé")
    
    def _get_llm_client(self):
        """Charge le client LLM (lazy loading)"""
        if self.llm_client is None:
            try:
                from .llm_client import GroqLLMClient
                self.llm_client = GroqLLMClient()
            except ImportError:
                log3("[RAG_SCALABLE]", "⚠️ Client LLM non disponible")
                self.llm_client = None
        return self.llm_client
    
    async def _search_phase(
        self,
        query: str,
        company_id: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> tuple[List[MeiliSearchResult], List[SemanticResult], float]:
        """
        Phase de recherche hybride parallèle
        
        Returns:
            (meilisearch_results, supabase_results, search_time_ms)
        """
        start_time = time.time()
        
        # Recherche parallèle MeiliSearch + Supabase
        tasks = []
        
        # MeiliSearch (full-text)
        tasks.append(self.meilisearch.search(query, company_id))
        
        # Supabase (sémantique) avec fallback
        tasks.append(self.supabase.search_with_fallback(query, company_id, filters))
        
        # Exécution parallèle
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Traitement des résultats
        meilisearch_results = results[0] if not isinstance(results[0], Exception) else []
        supabase_results = results[1] if not isinstance(results[1], Exception) else []
        
        search_time_ms = (time.time() - start_time) * 1000
        
        log3("[RAG_SCALABLE]", f"🔍 Recherche: {len(meilisearch_results)} MeiliSearch + {len(supabase_results)} Supabase en {search_time_ms:.1f}ms")
        
        return meilisearch_results, supabase_results, search_time_ms
    
    async def _rerank_phase(
        self,
        query: str,
        meilisearch_results: List[MeiliSearchResult],
        supabase_results: List[SemanticResult],
        company_id: str
    ) -> tuple[List[RerankResult], float]:
        """
        Phase de reranking avec cross-encoder
        
        Returns:
            (reranked_results, rerank_time_ms)
        """
        start_time = time.time()
        
        # Configuration du tenant
        config = get_tenant_config(company_id)
        top_k = config.search.rerank_top_k if config.search.rerank_enabled else 10
        
        # Reranking
        reranked_results = await self.reranker.rerank_results(
            query, meilisearch_results, supabase_results, company_id, top_k
        )
        
        rerank_time_ms = (time.time() - start_time) * 1000
        
        log3("[RAG_SCALABLE]", f"🎯 Reranking: {len(reranked_results)} docs en {rerank_time_ms:.1f}ms")
        
        return reranked_results, rerank_time_ms
    
    async def _llm_generation_phase(
        self,
        query: str,
        documents: List[RerankResult],
        company_id: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> tuple[str, float, int, int, float]:
        """
        Phase de génération LLM
        
        Returns:
            (response_text, llm_time_ms, tokens_input, tokens_output, cost_usd)
        """
        start_time = time.time()
        
        llm_client = self._get_llm_client()
        if not llm_client:
            return "Désolé, le service de génération n'est pas disponible.", 0, 0, 0, 0.0
        
        # Configuration du tenant
        config = get_tenant_config(company_id)
        
        # Construire le contexte
        context_parts = []
        for i, doc in enumerate(documents[:5], 1):  # Max 5 documents
            context_parts.append(f"[Source {i}] {doc.content[:500]}...")
        
        context = "\n\n".join(context_parts)
        
        # Historique de conversation
        history_str = ""
        if conversation_history:
            recent_history = conversation_history[-3:]  # 3 derniers échanges
            history_str = "\n".join([
                f"{'Client' if h.get('role') == 'user' else 'Assistant'}: {h.get('content', '')}"
                for h in recent_history
            ])
        
        # Prompt optimisé
        system_prompt = config.business.system_prompt_override or f"""Tu es un assistant clientèle expert pour {config.business.company_name}.
Tu réponds aux questions en te basant sur la base de connaissances fournie.
Tu es professionnel, courtois et précis. Si tu ne sais pas, tu le dis clairement."""
        
        user_prompt = f"""Contexte disponible:
{context}

{"Historique récent:" if history_str else ""}
{history_str}

Question du client: {query}

Instructions:
- Réponds en français de manière professionnelle
- Base-toi UNIQUEMENT sur le contexte fourni
- Cite tes sources [Source X] quand pertinent
- Si l'information n'est pas disponible, dis-le clairement
- Sois concis mais complet

Réponse:"""
        
        try:
            # Appel LLM avec configuration du tenant
            response = await llm_client.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=config.llm.temperature,
                max_tokens=config.llm.max_tokens
            )
            
            llm_time_ms = (time.time() - start_time) * 1000
            
            # Extraction des métriques (si disponibles)
            tokens_input = getattr(response, 'tokens_input', len(user_prompt.split()) * 1.3)
            tokens_output = getattr(response, 'tokens_output', len(response.split()) * 1.3)
            cost_usd = (tokens_input + tokens_output) * config.llm.cost_per_1k_tokens / 1000
            
            return response, llm_time_ms, int(tokens_input), int(tokens_output), cost_usd
            
        except Exception as e:
            log3("[RAG_SCALABLE]", f"⚠️ Erreur génération LLM: {e}")
            llm_time_ms = (time.time() - start_time) * 1000
            return f"Je rencontre des difficultés techniques. Pouvez-vous reformuler votre question ?", llm_time_ms, 0, 0, 0.0
    
    async def process_query(
        self,
        query: str,
        company_id: str,
        user_id: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None,
        filters: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> RAGResponse:
        """
        Point d'entrée principal du moteur RAG
        
        Args:
            query: Question de l'utilisateur
            company_id: ID de l'entreprise
            user_id: ID de l'utilisateur (optionnel)
            conversation_history: Historique de conversation
            filters: Filtres de recherche optionnels
            use_cache: Utiliser le cache ou non
            
        Returns:
            Réponse complète avec métriques
        """
        query_id = str(uuid.uuid4())
        start_time = time.time()
        
        log3("[RAG_SCALABLE]", f"🚀 Traitement requête {query_id[:8]} pour {company_id}")
        
        # Variables pour métriques
        cache_hit = False
        cache_level = None
        error_occurred = False
        error_message = None
        
        try:
            # 1. Vérifier le cache complet
            if use_cache:
                cached_response = await self.cache.get(
                    "rag_response", company_id, query,
                    user_id=user_id, filters=filters
                )
                
                if cached_response:
                    cache_hit = True
                    cache_level = "L1"  # Approximation
                    total_time_ms = (time.time() - start_time) * 1000
                    
                    log3("[RAG_SCALABLE]", f"✅ Cache hit complet en {total_time_ms:.1f}ms")
                    
                    # Enregistrer métriques
                    record_query_metrics(
                        query_id=query_id,
                        company_id=company_id,
                        query_text=query,
                        response_time_ms=total_time_ms,
                        cache_hit=True,
                        cache_level=cache_level,
                        final_results=len(cached_response.documents)
                    )
                    
                    return cached_response
            
            # 2. Phase de recherche
            meilisearch_results, supabase_results, search_time_ms = await self._search_phase(
                query, company_id, filters
            )
            
            # 3. Phase de reranking
            reranked_docs, rerank_time_ms = await self._rerank_phase(
                query, meilisearch_results, supabase_results, company_id
            )
            
            if not reranked_docs:
                # Aucun document trouvé
                response_text = "Je n'ai pas trouvé d'informations pertinentes pour répondre à votre question. Pouvez-vous la reformuler ou être plus spécifique ?"
                llm_time_ms = 0
                tokens_input = tokens_output = 0
                cost_usd = 0.0
            else:
                # 4. Phase de génération LLM
                response_text, llm_time_ms, tokens_input, tokens_output, cost_usd = await self._llm_generation_phase(
                    query, reranked_docs, company_id, conversation_history
                )
            
            # 5. Construire la réponse
            total_time_ms = (time.time() - start_time) * 1000
            
            sources_used = []
            if any(doc.source == "meilisearch" for doc in reranked_docs):
                sources_used.append("meilisearch")
            if any(doc.source == "supabase" for doc in reranked_docs):
                sources_used.append("supabase")
            
            # Calculer score de confiance
            confidence_score = 0.8 if reranked_docs else 0.3
            if reranked_docs:
                avg_score = sum(doc.final_score for doc in reranked_docs) / len(reranked_docs)
                confidence_score = min(0.95, avg_score / 10)  # Normaliser
            
            rag_response = RAGResponse(
                query_id=query_id,
                company_id=company_id,
                query=query,
                documents=reranked_docs,
                response_text=response_text,
                confidence_score=confidence_score,
                total_time_ms=total_time_ms,
                search_time_ms=search_time_ms,
                rerank_time_ms=rerank_time_ms,
                llm_time_ms=llm_time_ms,
                sources_used=sources_used,
                cache_hit=False,
                cache_level=None,
                llm_tokens_input=tokens_input,
                llm_tokens_output=tokens_output,
                llm_cost_usd=cost_usd
            )
            
            # 6. Mise en cache de la réponse complète
            if use_cache:
                await self.cache.set(
                    "rag_response", company_id, query, rag_response,
                    user_id=user_id, filters=filters
                )
            
            # 7. Enregistrer métriques
            record_query_metrics(
                query_id=query_id,
                company_id=company_id,
                query_text=query,
                response_time_ms=total_time_ms,
                meilisearch_time_ms=search_time_ms / 2,  # Approximation
                meilisearch_results=len(meilisearch_results),
                supabase_time_ms=search_time_ms / 2,  # Approximation
                supabase_results=len(supabase_results),
                rerank_time_ms=rerank_time_ms,
                final_results=len(reranked_docs),
                llm_time_ms=llm_time_ms,
                llm_tokens_input=tokens_input,
                llm_tokens_output=tokens_output,
                llm_cost_usd=cost_usd,
                cache_hit=False,
                error_occurred=False
            )
            
            log3("[RAG_SCALABLE]", f"✅ Requête {query_id[:8]} traitée en {total_time_ms:.1f}ms")
            
            return rag_response
            
        except Exception as e:
            error_occurred = True
            error_message = str(e)
            total_time_ms = (time.time() - start_time) * 1000
            
            log3("[RAG_SCALABLE]", f"❌ Erreur requête {query_id[:8]}: {e}")
            
            # Enregistrer métriques d'erreur
            record_query_metrics(
                query_id=query_id,
                company_id=company_id,
                query_text=query,
                response_time_ms=total_time_ms,
                error_occurred=True,
                error_message=error_message
            )
            
            # Réponse d'erreur
            return RAGResponse(
                query_id=query_id,
                company_id=company_id,
                query=query,
                documents=[],
                response_text="Je rencontre des difficultés techniques. Veuillez réessayer dans quelques instants.",
                confidence_score=0.0,
                total_time_ms=total_time_ms,
                search_time_ms=0,
                rerank_time_ms=0,
                llm_time_ms=0,
                sources_used=[],
                cache_hit=False,
                cache_level=None
            )
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques complètes du système"""
        return {
            'meilisearch': self.meilisearch.get_stats(),
            'supabase': self.supabase.get_stats(),
            'reranker': self.reranker.get_stats(),
            'cache': self.cache.get_stats()
        }
    
    def clear_caches(self, company_id: Optional[str] = None):
        """Vide tous les caches du système"""
        self.meilisearch.clear_cache(company_id)
        self.supabase.clear_cache(company_id)
        self.reranker.clear_cache()
        self.cache.clear_cache(company_id)
        
        log3("[RAG_SCALABLE]", f"✅ Caches vidés" + (f" pour {company_id}" if company_id else ""))


# Instance globale
_rag_engine: Optional[ScalableRAGEngine] = None

def get_scalable_rag_engine() -> ScalableRAGEngine:
    """Récupère l'instance globale du moteur RAG scalable"""
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = ScalableRAGEngine()
    return _rag_engine

async def process_rag_query(
    query: str,
    company_id: str,
    user_id: Optional[str] = None,
    conversation_history: Optional[List[Dict]] = None,
    filters: Optional[Dict[str, Any]] = None,
    use_cache: bool = True
) -> RAGResponse:
    """Fonction utilitaire pour traiter une requête RAG"""
    engine = get_scalable_rag_engine()
    return await engine.process_query(
        query, company_id, user_id, conversation_history, filters, use_cache
    )
