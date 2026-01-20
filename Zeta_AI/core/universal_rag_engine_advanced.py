#!/usr/bin/env python3
"""
🌍 RAG ENGINE UNIVERSEL FRANCOPHONE AVANCÉ 2024
Pipeline complet : NLP → Recherche Hybride → Fusion → Prompt Enrichi → Vérification QA
Architecture complètement intégrée pour la compréhension française et l'e-commerce
"""

import asyncio
import time
import logging
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# Imports des modules avancés
try:
    from .french_nlp_processor import FrenchNLPProcessor, ProcessedQuery
    from .semantic_search_engine import OptimizedSemanticSearchEngine, SearchConfig
    from .intelligent_fusion import IntelligentFusionEngine, FusionConfig, fuse_search_results
    from .prompt_enricher import PromptEnricher, enrich_llm_prompt
    from .response_verifier import ResponseVerifier, VerificationLevel, verify_llm_response
    ADVANCED_MODULES_AVAILABLE = True
except ImportError as e:
    logging.warning(f"⚠️ Modules avancés non disponibles: {e}")
    ADVANCED_MODULES_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class AdvancedRAGResult:
    """Résultat du RAG avancé avec métadonnées complètes"""
    response: str
    confidence: float
    documents_found: bool
    processing_time_ms: float
    search_method: str
    context_used: str
    # Métadonnées avancées
    nlp_analysis: Optional[Dict[str, Any]] = None
    fusion_metadata: Optional[Dict[str, Any]] = None
    verification_result: Optional[Dict[str, Any]] = None
    quality_score: Optional[float] = None
    pipeline_stages: Optional[List[str]] = None

class AdvancedUniversalRAGEngine:
    """
    🌍 RAG ENGINE UNIVERSEL FRANCOPHONE AVANCÉ
    
    Architecture complète :
    1. 🇫🇷 Prétraitement NLP français (normalisation, lemmatisation, intentions, entités)
    2. 🔍 Recherche hybride (MeiliSearch + Sémantique + Fuzzy)
    3. 🔀 Fusion intelligente multi-sources
    4. 🎯 Prompt enrichi avec intentions/entités
    5. 🤖 Génération LLM optimisée
    6. ✅ Vérification QA et factualité
    7. 📊 Métriques et auditabilité complètes
    """
    
    def __init__(self):
        self.llm_client = None
        self.embedding_model = None
        
        # Composants avancés
        if ADVANCED_MODULES_AVAILABLE:
            self.nlp_processor = FrenchNLPProcessor()
            self.semantic_engine = OptimizedSemanticSearchEngine()
            self.fusion_engine = IntelligentFusionEngine()
            self.prompt_enricher = PromptEnricher()
            self.response_verifier = ResponseVerifier()
            logger.info("✅ Architecture francophone avancée initialisée")
        else:
            self.nlp_processor = None
            self.semantic_engine = None
            self.fusion_engine = None
            self.prompt_enricher = None
            self.response_verifier = None
            logger.warning("⚠️ Mode dégradé - modules avancés non disponibles")
        
        # Configuration par défaut
        self.search_config = SearchConfig(
            top_k=8,
            min_score=0.3,
            enable_reranking=True,
            max_context_length=4000
        )
        
        self.fusion_config = FusionConfig(
            meili_weight=0.4,
            semantic_weight=0.4,
            fuzzy_weight=0.2,
            boost_exact_matches=True,
            boost_multi_source=True
        )
        
        self.verification_level = VerificationLevel.STANDARD
    
    async def initialize(self):
        """Initialise tous les composants"""
        try:
            # Import dynamique pour éviter les erreurs
            from .llm_client import GroqLLMClient
            from embedding_models import get_embedding_model
            
            self.llm_client = GroqLLMClient()
            self.embedding_model = get_embedding_model()
            
            # Initialisation des modules avancés
            if ADVANCED_MODULES_AVAILABLE:
                if self.semantic_engine:
                    self.semantic_engine.initialize()
                logger.info("✅ RAG Universel Francophone Avancé initialisé")
            else:
                logger.info("✅ RAG Universel (mode dégradé) initialisé")
            
            return True
        except Exception as e:
            logger.error(f"❌ Erreur initialisation: {e}")
            return False
    
    async def process_query_advanced(
        self, 
        query: str, 
        company_id: str, 
        user_id: str, 
        company_name: str = None
    ) -> AdvancedRAGResult:
        """
        🚀 TRAITEMENT AVANCÉ COMPLET D'UNE REQUÊTE
        
        Pipeline francophone intégral :
        1. 🇫🇷 Analyse NLP française complète
        2. 🔍 Recherche hybride multi-sources
        3. 🔀 Fusion intelligente des résultats
        4. 🎯 Enrichissement du prompt
        5. 🤖 Génération LLM optimisée
        6. ✅ Vérification QA et factualité
        """
        start_time = time.time()
        pipeline_stages = []
        
        logger.info(f"🚀 [ADVANCED_RAG] Début traitement: '{query[:50]}...'")
        logger.info(f"🏢 Company: {company_id[:12]}... | User: {user_id[:12]}...")
        
        # Variables de résultats
        nlp_analysis = None
        search_results = None
        fusion_metadata = None
        verification_result = None
        quality_score = None
        response = ""
        context_used = ""
        
        try:
            # Initialisation si nécessaire
            if not self.llm_client:
                await self.initialize()
            
            # ========== ÉTAPE 1 : ANALYSE NLP FRANÇAISE ==========
            pipeline_stages.append("nlp_analysis")
            processed_query = None
            
            if ADVANCED_MODULES_AVAILABLE and self.nlp_processor:
                try:
                    logger.info("🇫🇷 [ÉTAPE 1] Analyse NLP française...")
                    processed_query = self.nlp_processor.process_query(query)
                    
                    nlp_analysis = {
                        'original': processed_query.original,
                        'normalized': processed_query.normalized,
                        'lemmatized_words': processed_query.lemmatized_words,
                        'corrected': processed_query.corrected,
                        'intentions': processed_query.intentions,
                        'entities': processed_query.entities,
                        'split_queries': processed_query.split_queries,
                        'confidence': processed_query.confidence
                    }
                    
                    logger.info(f"✅ [NLP] Analyse terminée: {len(processed_query.intentions)} intentions, {len(processed_query.entities)} entités")
                    
                except Exception as e:
                    logger.error(f"❌ [NLP] Erreur: {e}")
                    processed_query = None
            
            # ========== ÉTAPE 2 : RECHERCHE HYBRIDE ==========
            pipeline_stages.append("hybrid_search")
            
            if ADVANCED_MODULES_AVAILABLE and processed_query:
                search_results = await self._advanced_search_pipeline(query, company_id, processed_query)
                
                fusion_metadata = {
                    'search_methods': search_results.get('search_methods_used', []),
                    'total_sources': len(search_results.get('search_methods_used', [])),
                    'documents_by_source': {
                        'meilisearch': len(search_results.get('meili_results', [])),
                        'semantic': len(search_results.get('semantic_results', [])),
                        'fuzzy': len(search_results.get('fuzzy_results', []))
                    },
                    'fusion_score': search_results.get('fusion_score', 0),
                    'total_documents': search_results.get('total_documents', 0)
                }
                
                context_used = search_results.get('final_context', '')
                
            else:
                # Fallback vers recherche classique
                search_results = await self._fallback_search(query, company_id)
                context_used = search_results.get('combined_context', '')
            
            # ========== ÉTAPE 3 : GÉNÉRATION AVEC PROMPT ENRICHI ==========
            pipeline_stages.append("enriched_generation")
            
            company_display_name = company_name or f"l'entreprise {company_id[:8]}"
            company_info = {
                'ai_name': 'Jessica',  # Par défaut
                'company_name': company_display_name,
                'business_sector': 'Commerce'
            }
            
            if ADVANCED_MODULES_AVAILABLE and self.prompt_enricher and processed_query:
                try:
                    logger.info("🎯 [ÉTAPE 3] Génération avec prompt enrichi...")
                    
                    # Enrichissement du prompt
                    enriched_prompt = self.prompt_enricher.enrich_prompt(
                        query, context_used, processed_query.intentions, processed_query.entities, company_info
                    )
                    
                    # Génération LLM avec prompt enrichi
                    response = await self._generate_llm_response(
                        enriched_prompt.system_prompt,
                        enriched_prompt.user_prompt
                    )
                    
                    logger.info(f"✅ [PROMPT] Template utilisé: {enriched_prompt.template_used}")
                    
                except Exception as e:
                    logger.error(f"❌ [PROMPT] Erreur enrichissement: {e}")
                    # Fallback vers génération classique
                    response = await self._generate_simple_response(query, context_used, company_info)
            else:
                # Génération classique
                response = await self._generate_simple_response(query, context_used, company_info)
            
            # ========== ÉTAPE 4 : VÉRIFICATION QA ==========
            pipeline_stages.append("qa_verification")
            
            if ADVANCED_MODULES_AVAILABLE and self.response_verifier and response:
                try:
                    logger.info("✅ [ÉTAPE 4] Vérification QA...")
                    
                    verification = self.response_verifier.verify_response(
                        response, context_used, query, 
                        processed_query.intentions if processed_query else [],
                        processed_query.entities if processed_query else []
                    )
                    
                    verification_result = {
                        'is_valid': verification.is_valid,
                        'quality_score': verification.quality_score,
                        'issues_count': len(verification.issues),
                        'issues_by_severity': {},
                        'corrected_available': verification.corrected_response is not None
                    }
                    
                    # Statistiques des issues
                    for issue in verification.issues:
                        severity = issue.severity
                        verification_result['issues_by_severity'][severity] = \
                            verification_result['issues_by_severity'].get(severity, 0) + 1
                    
                    quality_score = verification.quality_score
                    
                    # Utiliser la correction si disponible et nécessaire
                    if not verification.is_valid and verification.corrected_response:
                        response = verification.corrected_response
                        logger.info("🔧 [QA] Réponse corrigée automatiquement")
                    
                    logger.info(f"✅ [QA] Vérification terminée: score={quality_score:.2f}, valid={verification.is_valid}")
                    
                except Exception as e:
                    logger.error(f"❌ [QA] Erreur vérification: {e}")
            
            # ========== CALCUL FINAL ==========
            pipeline_stages.append("finalization")
            
            # Calcul de confiance globale
            confidence = self._calculate_global_confidence(
                nlp_analysis, fusion_metadata, quality_score, len(response)
            )
            
            # Méthode de recherche
            search_method = "advanced_hybrid" if ADVANCED_MODULES_AVAILABLE else "fallback_classic"
            if search_results:
                search_method = search_results.get('search_method', search_method)
            
            # Documents trouvés
            documents_found = bool(context_used and len(context_used.strip()) > 50)
            
            # Temps de traitement
            processing_time = (time.time() - start_time) * 1000
            
            logger.info(f"🎉 [ADVANCED_RAG] Terminé en {processing_time:.0f}ms | Confiance: {confidence:.2f}")
            
            return AdvancedRAGResult(
                response=response,
                confidence=confidence,
                documents_found=documents_found,
                processing_time_ms=processing_time,
                search_method=search_method,
                context_used=context_used,
                nlp_analysis=nlp_analysis,
                fusion_metadata=fusion_metadata,
                verification_result=verification_result,
                quality_score=quality_score,
                pipeline_stages=pipeline_stages
            )
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            logger.error(f"❌ [ADVANCED_RAG] Erreur critique: {str(e)[:100]} | {processing_time:.0f}ms")
            
            # Fallback d'urgence
            return AdvancedRAGResult(
                response="Je rencontre une difficulté technique. Pouvez-vous réessayer votre question ?",
                confidence=0.1,
                documents_found=False,
                processing_time_ms=processing_time,
                search_method="emergency_fallback",
                context_used="",
                pipeline_stages=pipeline_stages
            )
    
    async def _advanced_search_pipeline(self, query: str, company_id: str, processed_query: ProcessedQuery) -> Dict[str, Any]:
        """Pipeline de recherche hybride avancé"""
        logger.info("🔍 [SEARCH] Pipeline hybride avancé...")
        
        all_results = {
            'meili_results': [],
            'semantic_results': [],
            'fuzzy_results': [],
            'final_context': '',
            'total_documents': 0,
            'search_methods_used': [],
            'search_method': 'hybrid_advanced',
            'fusion_score': 0
        }
        
        # 1. Recherche MeiliSearch
        try:
            from database.vector_store_clean_v2 import search_all_indexes_parallel
            
            meili_raw = await search_all_indexes_parallel(
                query=query,
                company_id=company_id,
                limit=self.search_config.top_k
            )
            
            if meili_raw and isinstance(meili_raw, str):
                meili_docs = []
                for i, doc_text in enumerate(meili_raw.split('\n\n')):
                    if doc_text.strip():
                        meili_docs.append({
                            'id': f'meili_{i}',
                            'content': doc_text.strip(),
                            'score': 0.8,
                            'metadata': {'source': 'meilisearch'}
                        })
                
                all_results['meili_results'] = meili_docs
                all_results['search_methods_used'].append('meilisearch')
                logger.info(f"🔍 [MEILI] {len(meili_docs)} documents trouvés")
        
        except Exception as e:
            logger.error(f"❌ [MEILI] Erreur: {e}")
        
        # 2. Recherche sémantique
        if self.semantic_engine:
            try:
                semantic_results, _ = await self.semantic_engine.search(
                    query, company_id, self.search_config
                )
                
                semantic_docs = []
                for result in semantic_results:
                    semantic_docs.append({
                        'id': result.id,
                        'content': result.content,
                        'score': result.score,
                        'metadata': {**result.metadata, 'source': 'semantic'}
                    })
                
                all_results['semantic_results'] = semantic_docs
                all_results['search_methods_used'].append('semantic')
                logger.info(f"🧠 [SEMANTIC] {len(semantic_docs)} documents trouvés")
                
            except Exception as e:
                logger.error(f"❌ [SEMANTIC] Erreur: {e}")
        
        # 3. Recherche fuzzy multi-intent
        if processed_query.split_queries and len(processed_query.split_queries) > 1:
            try:
                fuzzy_docs = []
                for split_query in processed_query.split_queries[:3]:
                    sub_results = await self._fuzzy_search_fallback(split_query, company_id)
                    fuzzy_docs.extend(sub_results)
                
                all_results['fuzzy_results'] = fuzzy_docs
                if fuzzy_docs:
                    all_results['search_methods_used'].append('fuzzy_multi_intent')
                    logger.info(f"🔀 [FUZZY] {len(fuzzy_docs)} documents trouvés")
                
            except Exception as e:
                logger.error(f"❌ [FUZZY] Erreur: {e}")
        
        # 4. Fusion intelligente
        if self.fusion_engine and any([all_results['meili_results'], all_results['semantic_results'], all_results['fuzzy_results']]):
            try:
                fused_results, formatted_context = fuse_search_results(
                    all_results['meili_results'],
                    all_results['semantic_results'],
                    all_results['fuzzy_results'],
                    query,
                    self.fusion_config
                )
                
                all_results['final_context'] = formatted_context
                all_results['total_documents'] = len(fused_results)
                all_results['fusion_score'] = sum(r.final_score for r in fused_results) / len(fused_results) if fused_results else 0
                
                logger.info(f"🔀 [FUSION] {len(fused_results)} documents fusionnés (score moyen: {all_results['fusion_score']:.2f})")
                
            except Exception as e:
                logger.error(f"❌ [FUSION] Erreur: {e}")
                # Fallback simple
                all_contexts = []
                for results in [all_results['meili_results'], all_results['semantic_results'], all_results['fuzzy_results']]:
                    for doc in results[:3]:  # Max 3 par source
                        all_contexts.append(doc.get('content', ''))
                
                all_results['final_context'] = '\n\n'.join(all_contexts)
                all_results['total_documents'] = len(all_contexts)
        
        return all_results
    
    async def _fuzzy_search_fallback(self, query: str, company_id: str) -> List[Dict[str, Any]]:
        """Recherche fuzzy en fallback"""
        try:
            from .supabase_simple import SupabaseSimple
            
            supabase = SupabaseSimple()
            supabase_results = await supabase.search_documents(
                query=query,
                company_id=company_id,
                limit=3
            )
            
            fuzzy_docs = []
            for doc in supabase_results:
                fuzzy_docs.append({
                    'id': doc.get('id', ''),
                    'content': doc.get('content', ''),
                    'score': doc.get('similarity_score', 0.5),
                    'metadata': {**doc.get('metadata', {}), 'source': 'fuzzy_supabase'}
                })
            
            return fuzzy_docs
            
        except Exception as e:
            logger.error(f"❌ [FUZZY_FALLBACK] Erreur: {e}")
            return []
    
    async def _fallback_search(self, query: str, company_id: str) -> Dict[str, Any]:
        """Recherche de fallback classique"""
        try:
            # Import de la fonction de recherche existante
            from database.vector_store_clean_v2 import search_all_indexes_parallel
            
            meili_results = await search_all_indexes_parallel(
                query=query,
                company_id=company_id,
                limit=5
            )
            
            return {
                'combined_context': meili_results or '',
                'search_method': 'fallback_meilisearch',
                'total_documents': 1 if meili_results else 0
            }
            
        except Exception as e:
            logger.error(f"❌ [FALLBACK_SEARCH] Erreur: {e}")
            return {
                'combined_context': '',
                'search_method': 'fallback_failed',
                'total_documents': 0
            }
    
    async def _generate_llm_response(self, system_prompt: str, user_prompt: str) -> str:
        """Génération LLM avec prompts enrichis"""
        try:
            if not self.llm_client:
                await self.initialize()
            
            # Appel LLM avec prompts enrichis
            response = await self.llm_client.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            return response or "Je n'ai pas pu générer une réponse appropriée."
            
        except Exception as e:
            logger.error(f"❌ [LLM_ENRICHED] Erreur: {e}")
            return "Je rencontre une difficulté pour traiter votre demande."
    
    async def _generate_simple_response(self, query: str, context: str, company_info: Dict[str, Any]) -> str:
        """Génération LLM simple en fallback"""
        try:
            if not self.llm_client:
                await self.initialize()
            
            # Prompt simple
            system_prompt = f"""Tu es {company_info.get('ai_name', 'un assistant IA')} de {company_info.get('company_name', 'notre entreprise')}.
Réponds de manière professionnelle et utile en français."""
            
            user_prompt = f"""Question: {query}

Contexte disponible:
{context}

Réponds de manière précise et professionnelle."""
            
            response = await self.llm_client.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            return response or "Je n'ai pas pu traiter votre demande."
            
        except Exception as e:
            logger.error(f"❌ [LLM_SIMPLE] Erreur: {e}")
            return "Je rencontre une difficulté technique."
    
    def _calculate_global_confidence(
        self, 
        nlp_analysis: Optional[Dict], 
        fusion_metadata: Optional[Dict], 
        quality_score: Optional[float], 
        response_length: int
    ) -> float:
        """Calcule la confiance globale du pipeline"""
        confidence = 0.5  # Base
        
        # Bonus NLP
        if nlp_analysis:
            nlp_conf = nlp_analysis.get('confidence', 0)
            confidence += nlp_conf * 0.2
        
        # Bonus fusion
        if fusion_metadata:
            sources_count = fusion_metadata.get('total_sources', 0)
            if sources_count > 1:
                confidence += 0.15
            
            docs_count = fusion_metadata.get('total_documents', 0)
            if docs_count > 0:
                confidence += min(docs_count * 0.05, 0.2)
        
        # Bonus qualité
        if quality_score:
            confidence += quality_score * 0.3
        
        # Bonus longueur réponse
        if response_length > 100:
            confidence += 0.1
        
        return min(confidence, 1.0)

# Instance globale avancée
advanced_rag_engine = AdvancedUniversalRAGEngine()

# Interface simple pour compatibilité
async def get_advanced_rag_response(
    message: str, 
    company_id: str, 
    user_id: str, 
    company_name: str = None,
    conversation_history: str = ""
) -> Dict[str, Any]:
    """
    🚀 INTERFACE AVANCÉE POUR RAG FRANCOPHONE
    
    Utilise le pipeline complet avec toutes les optimisations
    """
    logger.info(f"🚀 [ADVANCED_ENTRY] Requête: '{message[:50]}...'")
    
    result = await advanced_rag_engine.process_query_advanced(
        message, company_id, user_id, company_name
    )
    
    return {
        'response': result.response,
        'confidence': result.confidence,
        'documents_found': result.documents_found,
        'processing_time_ms': result.processing_time_ms,
        'search_method': result.search_method,
        'context_used': result.context_used,
        'success': True,
        # Métadonnées avancées
        'nlp_analysis': result.nlp_analysis,
        'fusion_metadata': result.fusion_metadata,
        'verification_result': result.verification_result,
        'quality_score': result.quality_score,
        'pipeline_stages': result.pipeline_stages
    }

if __name__ == "__main__":
    import sys
    
    async def test_advanced():
        """Test du pipeline avancé"""
        company_id = sys.argv[1] if len(sys.argv) > 1 else "XkCn8fjNWEWwqiiKMgJX7OcQrUJ3"
        user_id = sys.argv[2] if len(sys.argv) > 2 else "testuser_advanced"
        company_name = sys.argv[3] if len(sys.argv) > 3 else "Rue du Gros"
        message = sys.argv[4] if len(sys.argv) > 4 else "Je veux 3 paquets de couches taille 2 et combien pour livraison à Cocody?"
        
        print(f"🧪 Test RAG Engine Avancé:")
        print(f"🏢 Company: {company_name}")
        print(f"👤 User: {user_id}")
        print(f"💬 Message: {message}")
        print("-" * 80)
        
        result = await get_advanced_rag_response(message, company_id, user_id, company_name)
        
        print(f"🤖 Réponse: {result['response']}")
        print(f"📊 Confiance: {result['confidence']:.2f}")
        print(f"🔍 Méthode: {result['search_method']}")
        print(f"⏱️ Temps: {result['processing_time_ms']:.0f}ms")
        
        if result.get('nlp_analysis'):
            nlp = result['nlp_analysis']
            print(f"🇫🇷 NLP: {len(nlp.get('intentions', []))} intentions, {len(nlp.get('entities', []))} entités")
        
        if result.get('quality_score'):
            print(f"✅ Qualité: {result['quality_score']:.2f}")
    
    asyncio.run(test_advanced())
