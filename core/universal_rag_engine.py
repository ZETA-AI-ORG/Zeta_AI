#!/usr/bin/env python3
"""
🌍 RAG ENGINE UNIVERSEL 2024 - ARCHITECTURE FRANCOPHONE AVANCÉE
Pipeline complet : NLP → Recherche Hybride → Fusion → Prompt Enrichi → Vérification QA
Optimisé pour la compréhension française et l'e-commerce
"""

import asyncio
import time
import logging
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# Imports Live Mode (réels)
from .live_mode_manager import LiveModeManager

# Imports des nouveaux modules
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
class UniversalRAGResult:
    """Résultat du RAG universel enrichi"""
    response: str
    confidence: float
    documents_found: bool
    processing_time_ms: float
    search_method: str
    context_used: str
    # Nouveaux champs pour l'architecture avancée
    nlp_analysis: Optional[Dict[str, Any]] = None
    fusion_metadata: Optional[Dict[str, Any]] = None
    verification_result: Optional[Dict[str, Any]] = None
    quality_score: Optional[float] = None
    # Champs pour debugging et validation
    thinking: str = ""
    validation: Optional[Dict[str, Any]] = None
    usage: Optional[Dict[str, Any]] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    model: str = ""

class UniversalRAGEngine:
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
        
        # Initialiser Supabase pour les prompts dynamiques
        try:
            from database.supabase_client import get_supabase_client
            self.supabase = get_supabase_client()
            logger.info("✅ Connexion Supabase initialisée (prompts dynamiques)")
        except Exception as e:
            logger.warning(f"⚠️ Supabase non disponible: {e}")
            self.supabase = None
        
        # Nouveaux composants avancés
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
            logger.warning("⚠️ Mode compatibilité - modules avancés désactivés")
        
    async def initialize(self):
        """Initialise les composants"""
        try:
            # Import dynamique pour éviter les erreurs
            import os
            from .llm_client import GroqLLMClient, OpenRouterLLMClient
            from embedding_models import get_embedding_model

            # ✅ RAG: prioriser OpenRouter (même logique que Botlive/Jessica)
            openrouter_key_present = bool((os.getenv("OPENROUTER_API_KEY") or "").strip())
            if openrouter_key_present:
                self.llm_client = OpenRouterLLMClient()
            else:
                self.llm_client = GroqLLMClient()
            self.embedding_model = get_embedding_model()
            
            # Initialisation des modules avancés
            if ADVANCED_MODULES_AVAILABLE:
                if self.semantic_engine:
                    self.semantic_engine.initialize()
                logger.info("✅ RAG Universel Francophone Avancé initialisé")
            else:
                logger.info("✅ RAG Universel (mode compatibilité) initialisé")
            
            return True
        except Exception as e:
            logger.error(f"❌ Erreur initialisation: {e}")
            return False
    
    async def advanced_search_pipeline(self, query: str, company_id: str, processed_query: Any = None) -> Dict[str, Any]:
        """
        🚀 PIPELINE DE RECHERCHE HYBRIDE AVANCÉ
        Combine MeiliSearch, recherche sémantique et fuzzy matching
        """
        if not ADVANCED_MODULES_AVAILABLE:
            return await self.search_sequential_sources(query, company_id)
        
        logger.info(f"🚀 [ADVANCED_SEARCH] Début pipeline hybride: '{query[:50]}...'")
        
        # Résultats consolidés
        all_results = {
            'meili_results': [],
            'semantic_results': [],
            'fuzzy_results': [],
            'fused_results': [],
            'final_context': '',
            'total_documents': 0,
            'search_methods_used': [],
            'search_method': 'hybrid_advanced'
        }
        
        # 1. Recherche MeiliSearch (existante)
        try:
            from database.vector_store_clean_v2 import search_all_indexes_parallel
            
            meili_raw = await search_all_indexes_parallel(
                query=query,
                company_id=company_id,
                max_results=10
            )
            
            # Conversion au format standard
            if meili_raw and isinstance(meili_raw, str):
                # Parser les résultats MeiliSearch
                meili_docs = []
                for i, doc_text in enumerate(meili_raw.split('\n\n')):
                    if doc_text.strip():
                        meili_docs.append({
                            'id': f'meili_{i}',
                            'content': doc_text.strip(),
                            'score': 0.8,  # Score par défaut
                            'metadata': {'source': 'meilisearch'}
                        })
                all_results['meili_results'] = meili_docs
                all_results['search_methods_used'].append('meilisearch')
                logger.info(f"🔍 [MEILI] {len(meili_docs)} documents trouvés")
            
        except Exception as e:
            logger.error(f"❌ [MEILI] Erreur: {e}")
        
        # 2. Recherche sémantique avancée
        if self.semantic_engine:
            try:
                config = SearchConfig(top_k=5, min_score=0.3, enable_reranking=True)
                semantic_results, _ = await self.semantic_engine.search(query, company_id, config)
                
                # Conversion au format standard
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
        
        # 3. Recherche fuzzy sur requêtes reformulées
        if processed_query.split_queries and len(processed_query.split_queries) > 1:
            try:
                fuzzy_docs = []
                for split_query in processed_query.split_queries[:3]:  # Max 3 sous-requêtes
                    # Recherche simple sur chaque sous-requête
                    sub_results = await self._fuzzy_search_fallback(split_query, company_id)
                    fuzzy_docs.extend(sub_results)
                
                all_results['fuzzy_results'] = fuzzy_docs
                if fuzzy_docs:
                    all_results['search_methods_used'].append('fuzzy_multi_intent')
                    logger.info(f"🔀 [FUZZY] {len(fuzzy_docs)} documents trouvés")
                
            except Exception as e:
                logger.error(f"❌ [FUZZY] Erreur: {e}")
        
        # 4. Fusion intelligente des résultats
        if self.fusion_engine and any([all_results['meili_results'], all_results['semantic_results'], all_results['fuzzy_results']]):
            try:
                fused_results, formatted_context = fuse_search_results(
                    all_results['meili_results'],
                    all_results['semantic_results'],
                    all_results['fuzzy_results'],
                    query
                )
                
                all_results['fused_results'] = [r.__dict__ for r in fused_results]  # Conversion dataclass
                all_results['final_context'] = formatted_context
                all_results['total_documents'] = len(fused_results)
                
                logger.info(f"🔀 [FUSION] {len(fused_results)} documents fusionnés")
                
            except Exception as e:
                logger.error(f"❌ [FUSION] Erreur: {e}")
                # Fallback : concaténation simple
                all_contexts = []
                for results in [all_results['meili_results'], all_results['semantic_results'], all_results['fuzzy_results']]:
                    for doc in results:
                        all_contexts.append(doc.get('content', ''))
                all_results['final_context'] = '\n\n'.join(all_contexts[:5])
                all_results['total_documents'] = len(all_contexts)
        
        return all_results
    
    async def _fuzzy_search_fallback(self, query: str, company_id: str) -> List[Dict[str, Any]]:
        """Recherche fuzzy simple en fallback"""
        try:
            # Utilisation de la recherche Supabase OPTIMISÉE
            from .supabase_optimized import search_documents
            
            supabase_results = await search_documents(
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

    # ═══════════════════════════════════════════════════════════════════════════════
    # 🚀 NOUVELLE ARCHITECTURE: RECHERCHE PARALLÈLE TRIPLE SOURCE
    # ═══════════════════════════════════════════════════════════════════════════════
    
    async def search_parallel_sources(
        self, 
        query: str, 
        company_id: str, 
        user_id: str = None,
        last_user_message: str = None
    ) -> Dict[str, Any]:
        """
        🚀 RECHERCHE PARALLÈLE TRIPLE SOURCE (Gemini Cache + Meili + Supabase)
        
        Architecture optimisée:
        1. Extraction regex INSTANTANÉE (zone/téléphone) - 0ms
        2. Détection keywords (remplace SetFit) - 0ms
        3. Triple recherche PARALLÈLE - max(40ms, 300ms, 2000ms)
        4. Fusion intelligente des résultats
        
        Returns:
            {
                'catalog_context': str,      # Produits (Gemini Cache)
                'delivery_context': str,     # Livraison (Regex + Meili)
                'payment_sav_context': str,  # Paiement/SAV (Meili)
                'company_context': str,      # Infos entreprise (Meili)
                'semantic_context': str,     # Fallback (Supabase)
                'meili_context': str,        # Compat avec ancien système
                'supabase_context': str,     # Compat avec ancien système
                'total_documents': int,
                'search_methods_used': list,
                'search_method': str,
                'regex_extracted': dict,     # Zone/téléphone extraits
                'keywords_detected': dict,   # Keywords détectés
                'has_instant_answer': bool   # True si regex suffit
            }
        """
        import time as time_module
        start_time = time_module.time()
        
        # ========== TRACKING ==========
        try:
            from core.rag_performance_tracker import get_tracker
            tracker = get_tracker(getattr(self, '_request_id', 'unknown'))
            tracker.start_step("search_parallel_sources", query_length=len(query))
        except:
            tracker = None
        
        # Résultat initial
        results = {
            'catalog_context': '',
            'delivery_context': '',
            'payment_sav_context': '',
            'company_context': '',
            'semantic_context': '',
            'meili_context': '',
            'supabase_context': '',
            'total_documents': 0,
            'search_methods_used': [],
            'search_method': 'parallel_triple',
            'regex_extracted': {},
            'keywords_detected': {},
            'has_instant_answer': False
        }
        
        # ═══════════════════════════════════════════════════════════════════════
        # ÉTAPE 0: IMPORT CATALOG CACHE MANAGER
        # ═══════════════════════════════════════════════════════════════════════
        try:
            from core.catalog_cache_manager import get_catalog_cache_manager
            cache_manager = get_catalog_cache_manager()
            print("✅ [PARALLEL] CatalogCacheManager chargé")
        except ImportError as e:
            print(f"⚠️ [PARALLEL] CatalogCacheManager non disponible: {e}")
            # Fallback vers recherche séquentielle
            return await self.search_sequential_sources(query, company_id, last_user_message, user_id)
        
        # ═══════════════════════════════════════════════════════════════════════
        # ÉTAPE 1: EXTRACTION REGEX INSTANTANÉE (0ms)
        # Zone de livraison + Numéro de téléphone
        # ═══════════════════════════════════════════════════════════════════════
        print(f"⚡ [ÉTAPE 1] Extraction regex instantanée...")
        regex_results = cache_manager.extract_regex_fast(query)
        results['regex_extracted'] = regex_results
        
        if regex_results.get('delivery_zone'):
            zone = regex_results['delivery_zone']
            print(f"   ✅ Zone extraite: {zone.get('name')} = {zone.get('cost')}F")
            results['delivery_context'] = regex_results.get('instant_context', '')
            results['has_instant_answer'] = regex_results.get('has_instant_answer', False)
            results['search_methods_used'].append('regex_zone')
        
        if regex_results.get('phone_number'):
            phone = regex_results['phone_number']
            print(f"   ✅ Téléphone extrait: {phone.get('normalized')} ({phone.get('operator')})")
            results['search_methods_used'].append('regex_phone')
        
        # ═══════════════════════════════════════════════════════════════════════
        # ÉTAPE 2: DÉTECTION KEYWORDS (0ms - remplace SetFit)
        # ═══════════════════════════════════════════════════════════════════════
        print(f"⚡ [ÉTAPE 2] Détection keywords (sans SetFit)...")
        keywords = cache_manager.detect_keywords(query)
        results['keywords_detected'] = keywords
        
        print(f"   → Product: {keywords['has_product']}, Delivery: {keywords['has_delivery']}")
        print(f"   → Payment: {keywords['has_payment']}, Contact: {keywords['has_contact']}")
        print(f"   → Priority source: {keywords['priority_source']}")

        # ═══════════════════════════════════════════════════════════════════════
        # ✅ EARLY-EXIT: NUMÉRO SEUL = 100% REGEX (AUCUN MEILI/SUPABASE)
        # Objectif: ultra-rapide pour extraction téléphone.
        # ═══════════════════════════════════════════════════════════════════════
        try:
            has_zone_regex = bool(regex_results.get('delivery_zone'))
            has_phone_regex = bool(regex_results.get('phone_number'))
            is_delivery_question = bool(keywords.get('has_delivery'))
            is_product_question = bool(keywords.get('has_product'))
            is_payment_question = bool(keywords.get('has_payment'))
            is_contact_question = bool(keywords.get('has_contact'))

            # Multi-intent: ne pas annuler les autres intentions.
            # On early-exit uniquement si l'intention est UNIQUE.
            intent_flags = [
                bool(is_product_question),
                bool(is_delivery_question),
                bool(is_payment_question),
                bool(is_contact_question),
            ]
            intent_count = sum(1 for f in intent_flags if f)

            # Téléphone: si numéro détecté par regex et pas d'autre intent.
            # Exemple: "Mon numéro c'est 070..." → pas de recherche.
            if has_phone_regex and is_contact_question and intent_count == 1:
                results['search_method'] = 'regex_only_phone'
                results['search_methods_used'] = list(dict.fromkeys(results['search_methods_used'] + ['regex_phone']))
                results['meili_context'] = ''
                results['supabase_context'] = ''
                results['total_documents'] = 1
                results['has_instant_answer'] = True

                total_time = (time_module.time() - start_time) * 1000
                print(f"⚡ [EARLY_EXIT] Téléphone via regex uniquement ({total_time:.0f}ms)")

                if tracker:
                    tracker.end_step(
                        documents_found=results['total_documents'],
                        search_method=results['search_method']
                    )
                return results
        except Exception:
            # Si un problème survient sur l'early-exit, on continue le pipeline normal.
            pass
        
        # ═══════════════════════════════════════════════════════════════════════
        # ÉTAPE 3: RECHERCHE PARALLÈLE TRIPLE SOURCE
        # ═══════════════════════════════════════════════════════════════════════
        print(f"🚀 [ÉTAPE 3] Lancement recherche parallèle triple...")
        
        search_results = await cache_manager.search_parallel(
            query=query,
            company_id=company_id,
            keywords=keywords,
            regex_results=regex_results
        )
        
        print(f"   ⏱️ Temps recherche parallèle: {search_results.get('total_time_ms', 0):.0f}ms")
        
        # ═══════════════════════════════════════════════════════════════════════
        # ÉTAPE 4: FUSION INTELLIGENTE DES RÉSULTATS
        # ═══════════════════════════════════════════════════════════════════════
        print(f"🔀 [ÉTAPE 4] Fusion des résultats...")
        
        fused = cache_manager.fuse_results(search_results, keywords)
        
        # Mettre à jour les résultats
        results['catalog_context'] = fused.get('catalog_context', '')
        results['payment_sav_context'] = fused.get('payment_sav_context', '')
        results['company_context'] = fused.get('company_context', '')
        results['semantic_context'] = fused.get('semantic_context', '')
        
        # Enrichir delivery_context si pas déjà rempli par regex
        if not results['delivery_context'] and fused.get('delivery_context'):
            results['delivery_context'] = fused['delivery_context']
        
        # Sources utilisées
        for src in fused.get('sources_used', []):
            if src not in results['search_methods_used']:
                results['search_methods_used'].append(src)
        
        # ═══════════════════════════════════════════════════════════════════════
        # ÉTAPE 5: ASSEMBLAGE CONTEXTE UNIFIÉ (compatibilité ancien système)
        # ═══════════════════════════════════════════════════════════════════════
        print(f"📦 [ÉTAPE 5] Assemblage contexte unifié...")
        
        # Construire meili_context pour compatibilité
        meili_parts = []
        if results['delivery_context']:
            meili_parts.append(f"🚚 LIVRAISON:\n{results['delivery_context']}")
        if results['payment_sav_context']:
            meili_parts.append(f"💳 PAIEMENT/SAV:\n{results['payment_sav_context']}")
        if results['company_context']:
            meili_parts.append(f"🏢 ENTREPRISE:\n{results['company_context']}")
        if results['catalog_context']:
            meili_parts.append(f"📦 CATALOGUE:\n{results['catalog_context']}")
        
        results['meili_context'] = "\n\n".join(meili_parts) if meili_parts else ''
        
        # Supabase context pour compatibilité
        results['supabase_context'] = results['semantic_context']
        
        # Compter documents
        meili_data = search_results.get('meilisearch', {})
        supa_data = search_results.get('supabase', {})
        results['total_documents'] = (
            len(meili_data.get('results', [])) + 
            len(supa_data.get('results', [])) +
            (1 if results['delivery_context'] else 0)  # Regex compte comme 1 doc
        )
        
        # ═══════════════════════════════════════════════════════════════════════
        # FIN: LOGGING ET TRACKING
        # ═══════════════════════════════════════════════════════════════════════
        total_time = (time_module.time() - start_time) * 1000
        
        print(f"✅ [PARALLEL] Recherche terminée en {total_time:.0f}ms")
        print(f"   → Documents: {results['total_documents']}")
        print(f"   → Sources: {results['search_methods_used']}")
        print(f"   → Instant answer: {results['has_instant_answer']}")
        
        if tracker:
            tracker.end_step(
                documents_found=results['total_documents'],
                search_method=results['search_method']
            )
        
        return results

    async def search_sequential_sources(self, query: str, company_id: str, last_user_message: str = None, user_id: str = None) -> Dict[str, Any]:
        """🎯 RECHERCHE SÉQUENTIELLE CLASSIQUE (Mode compatibilité)"""
        # ========== TRACKING ==========
        try:
            from core.rag_performance_tracker import get_tracker
            tracker = get_tracker(getattr(self, '_request_id', 'unknown'))
            tracker.start_step("search_sources", query_length=len(query))
        except:
            tracker = None
        
        results = {
            'supabase_context': '',
            'meili_context': '',
            'total_documents': 0,
            'search_methods_used': [],
            'search_method': 'sequential_classic'
        }
        
        # === APPEL HYDE POUR REFORMULATION DOCUMENTAIRE ===
        clarified_query = query
        try:
            from core.hyde_word_scorer import clarify_request_with_hyde
            if last_user_message:
                clarified = await clarify_request_with_hyde(query, last_user_message)
            else:
                clarified = await clarify_request_with_hyde(query, "")
            if clarified:
                print(f"[HYDE] Requête documentaire clarifiée : {clarified}")
                clarified_query = clarified
            else:
                print("[HYDE] Pas de clarification, on garde la requête d'origine.")
        except Exception as e:
            print(f"[HYDE] Erreur appel Hyde : {e}")
        
        # 🧹 ÉTAPE 0: PREPROCESSING AVANCÉ
        print(f"🧹 [ÉTAPE 0] Preprocessing: '{clarified_query[:30]}...'")
        # Initialisation par défaut
        filtered_query = clarified_query
        query_combinations = [[word] for word in clarified_query.split()]
        
        try:
            from .smart_stopwords import filter_query_for_meilisearch
            from .query_combinator import generate_query_combinations
            
            # Filtrage stop words
            filtered_query = filter_query_for_meilisearch(clarified_query)
            print(f"📝 Stop words supprimés: '{filtered_query}'")
            
            # Génération N-grammes
            query_combinations = generate_query_combinations(filtered_query)
            print(f"🔤 N-grammes: {len(query_combinations)} combinaisons")
            
        except Exception as e:
            print(f"❌ Erreur preprocessing: {str(e)[:50]}")
            # Les valeurs par défaut sont déjà définies
        
        # 🎯 ÉTAPE 1: RECHERCHE MEILISEARCH (PARALLÈLE GLOBALE - AUCUN EARLY EXIT)
        print(f"🔍 [ÉTAPE 1] MeiliSearch - Recherche parallèle globale...")
        meili_success = False
        try:
            # Import de la nouvelle fonction de recherche parallèle globale
            from database.vector_store_clean_v2 import search_all_indexes_parallel
            
            # Recherche EXHAUSTIVE dans TOUS les index en parallèle
            meili_results = await search_all_indexes_parallel(
                query=filtered_query,  # IMPORTANT: requête HYDE + stopwords filtrés → n-grams propres
                company_id=company_id,
                limit=10
            )
            
            if meili_results and len(meili_results.strip()) > 0:
                # Le contexte est déjà formaté par search_all_indexes_parallel
                results['meili_context'] = meili_results
                results['total_documents'] = meili_results.count('DOCUMENT #')
                results['search_methods_used'].append('meili_parallel_global')
                results['search_method'] = 'meilisearch_parallel_global'
                meili_success = True
                print(f"✅ [ÉTAPE 1] MeiliSearch Parallèle Globale OK: {results['total_documents']} docs")
            else:
                print(f"❌ [ÉTAPE 1] MeiliSearch: Aucun résultat → Fallback Supabase")
                
        except Exception as e:
            print(f"❌ MeiliSearch erreur: {str(e)[:50]} → Fallback")
        
        # 🔄 ÉTAPE FALLBACK INTELLIGENT: Supabase seulement si Meili insuffisant
        # Utilise SmartFallbackManager pour décider
        use_supabase_fallback = False
        fallback_reason = "meili_empty"
        
        if not meili_success:
            use_supabase_fallback = True
            fallback_reason = "meili_failed"
        else:
            # Meili a réussi, mais est-il suffisant?
            try:
                from core.context_optimizer import get_fallback_manager
                fallback_mgr = get_fallback_manager()
                use_supabase_fallback, fallback_reason = fallback_mgr.should_use_supabase_fallback(
                    meili_context=results['meili_context'],
                    query=query,
                    scored_docs=None
                )
                if use_supabase_fallback:
                    print(f"🔄 [SMART_FALLBACK] Meili insuffisant ({fallback_reason}) → Supabase complémentaire")
                else:
                    print(f"✅ [SMART_FALLBACK] Meili suffisant → Supabase skippé")
            except Exception as e:
                print(f"⚠️ [SMART_FALLBACK] Erreur évaluation: {e}")
                # En cas d'erreur, ne pas utiliser Supabase si Meili a réussi
                use_supabase_fallback = False
        
        if use_supabase_fallback:
            print(f"🔄 [ÉTAPE 2] Supabase fallback...")
            try:
                # ✅ PHASE 1: Utiliser singleton pré-chargé (pas nouvelle instance!)
                from .supabase_optimized_384 import get_supabase_optimized_384
                supabase = get_supabase_optimized_384(use_float16=True)
                
                # Recherche sémantique avec query originale
                supabase_docs = await supabase.search_documents(
                    query=query,
                    company_id=company_id,
                    limit=10  # Augmenté pour avoir plus de docs à rescorer
                )
                
                if supabase_docs:
                    # ✅ RESCORING + FILTRAGE + EXTRACTION PRÉCISE (PARALLÉLISÉ)
                    try:
                        import asyncio
                        from core.smart_metadata_extractor import rescore_documents, filter_by_dynamic_threshold, detect_query_intentions, get_company_boosters
                        from core.context_extractor import extract_relevant_context
                        from core.conversation_notepad import get_conversation_notepad
                        
                        # ═══════════════════════════════════════════════════════════
                        # PARALLÉLISATION: Notepad + Intentions + Boosters
                        # ═══════════════════════════════════════════════════════════
                        async def get_notepad_data():
                            if user_id:
                                notepad = get_conversation_notepad()
                                notepad_data = notepad.get_notepad(user_id, company_id)
                                return {
                                    "produit": notepad_data.get("product", {}).get("name", ""),
                                    "zone": notepad_data.get("delivery", {}).get("zone", "")
                                }
                            return {}
                        
                        async def get_intentions():
                            return detect_query_intentions(query)
                        
                        async def get_boosters():
                            return get_company_boosters(company_id) if company_id else None
                        
                        # Exécution parallèle
                        print("⚡ [PARALLEL] Lancement notepad + intentions + boosters...")
                        user_context, intentions, boosters = await asyncio.gather(
                            get_notepad_data(),
                            get_intentions(),
                            get_boosters()
                        )
                        print(f"⚡ [PARALLEL] Terminé - Intentions: {list(intentions.get('categories', []))}")
                        
                        # ═══════════════════════════════════════════════════════════
                        # ✅ AMÉLIORATION 4: PIPELINE OPTIMISÉ (Rescoring + Extraction parallèles)
                        # ═══════════════════════════════════════════════════════════
                        
                        async def rescore_and_filter():
                            """Rescoring + filtrage"""
                            docs = rescore_documents(supabase_docs, query, user_context, company_id)
                            return filter_by_dynamic_threshold(docs)
                        
                        async def extract_context():
                            """Extraction contexte (peut démarrer en parallèle)"""
                            # Attend rescoring terminé
                            filtered = await rescore_and_filter()
                            return extract_relevant_context(filtered, intentions, query, user_context)
                        
                        # Exécution optimisée
                        supabase_docs = await extract_context()
                        print(f"⚡ [OPTIMIZED] Rescoring + Filtrage + Extraction terminés")
                        print(f"🔍 [FILTRAGE] {len(supabase_docs)} docs retenus après pipeline optimisé")
                        
                    except Exception as e:
                        print(f"⚠️ [RESCORING] Erreur: {e} - Utilisation docs bruts")
                        import traceback
                        traceback.print_exc()
                    
                    # ✅ AMÉLIORATION 5: Détection ambiguïté
                    try:
                        from core.ambiguity_detector import detect_ambiguity, format_ambiguity_message
                        
                        is_ambiguous, ambiguity_type, options = detect_ambiguity(query, supabase_docs)
                        if is_ambiguous:
                            ambiguity_msg = format_ambiguity_message(ambiguity_type, options)
                            print(f"⚠️ [AMBIGUÏTÉ] Détectée: {ambiguity_type} - {len(options)} options")
                            # Injecter dans le contexte
                            results['ambiguity_detected'] = True
                            results['ambiguity_message'] = ambiguity_msg
                        else:
                            results['ambiguity_detected'] = False
                    except Exception as e:
                        print(f"⚠️ [AMBIGUÏTÉ] Erreur détection: {e}")
                        results['ambiguity_detected'] = False
                    
                    # Assemblage contexte Supabase avec titres fixes
                    supabase_context = self._format_supabase_context(supabase_docs)
                    
                    # Ajouter message ambiguïté si détecté
                    if results.get('ambiguity_detected'):
                        supabase_context = results['ambiguity_message'] + "\n\n" + supabase_context
                    
                    results['supabase_context'] = supabase_context
                    results['total_documents'] = len(supabase_docs)
                    results['search_methods_used'].append('supabase_semantic')
                    results['search_method'] = 'supabase_fallback'
                    print(f"✅ Supabase OK: {len(supabase_docs)} docs, {len(supabase_context)} chars")
                else:
                    # Même si 0 résultats, on marque que Supabase a été utilisé
                    results['search_method'] = 'supabase_fallback'
                    results['search_methods_used'].append('supabase_semantic')
                    print("❌ Supabase: 0 résultats")
                    
            except Exception as e:
                # Même en cas d'erreur, on marque la tentative Supabase
                results['search_method'] = 'supabase_fallback'
                results['search_methods_used'].append('supabase_error')
                print(f"❌ Supabase erreur: {str(e)[:50]}")
        
        # ========== FIN TRACKING SEARCH ==========
        if tracker:
            tracker.end_step(
                documents_found=results['total_documents'],
                search_method=results['search_method']
            )
        
        return results
    
    async def generate_response(self, query: str, search_results: Dict[str, Any], company_id: str, company_name: str = "notre entreprise", user_id: str = None, images=None) -> str:
        """🤖 Génère une réponse avec prompt dynamique Supabase et mémoire conversationnelle"""
        
        # ========== RÉCUPÉRATION PROMPT DYNAMIQUE (AVANT TRAITEMENT IMAGE) ==========
        try:
            dynamic_prompt = await self._get_dynamic_prompt(company_id, company_name)
            print("✅ Prompt dynamique récupéré")
            
            # Extraire configuration entreprise du prompt
            prompt_config = self._extract_config_from_prompt(dynamic_prompt)
            print(f"📋 [CONFIG EXTRAITE] Wave: {prompt_config['wave_phone']}, Acompte: {prompt_config['required_amount']} FCFA")
        except Exception as e:
            print(f"⚠️ Prompt par défaut: {str(e)[:30]}")
            dynamic_prompt = f"Tu es un assistant client professionnel pour {company_name}."
            prompt_config = {'wave_phone': None, 'required_amount': None}
        
        # ========== ANALYSE IMAGE SI PRÉSENTE ==========
        image_context = ""
        if images and len(images) > 0:
            print("📸 [IMAGE] Détectée, analyse via Botlive...")
            try:
                from core.image_analyzer import analyze_image_for_rag
                import requests
                import base64
                
                # Télécharger l'image depuis l'URL
                image_url = images[0]
                print(f"📥 [IMAGE] Téléchargement: {image_url[:80]}...")
                
                response = requests.get(image_url, timeout=15)
                response.raise_for_status()
                
                # Convertir en base64
                image_base64 = base64.b64encode(response.content).decode('utf-8')
                print(f"✅ [IMAGE] Téléchargée et convertie en base64 ({len(image_base64)} chars)")
                
                # Analyser l'image avec config entreprise
                image_analysis = await analyze_image_for_rag(
                    image_data=image_base64,
                    user_id=user_id or "unknown",
                    context=query,
                    company_phone=prompt_config.get('wave_phone'),
                    required_amount=prompt_config.get('required_amount')
                )
                
                print(f"✅ [IMAGE] Type: {image_analysis['type']}, Confiance: {image_analysis.get('confidence', 0):.2f}")
                
                # ========== FALLBACK AUTOMATIQUE VERS BOTLIVE POUR PAIEMENTS ==========
                if image_analysis["type"] == "payment":
                    print("💳 [FALLBACK] Image de paiement détectée → Redirection vers Botlive")
                    try:
                        from core.botlive_rag_hybrid import botlive_hybrid
                        
                        # Construire contexte pour Botlive
                        payment_data = image_analysis["data"]
                        
                        # Convertir amount en int (Botlive attend un int, pas une string)
                        amount = payment_data.get('amount', 0)
                        if isinstance(amount, str):
                            try:
                                amount = int(amount)
                            except (ValueError, TypeError):
                                amount = 0
                        
                        # Utiliser config extraite du prompt (avec fallback)
                        wave_phone = prompt_config.get('wave_phone') or '225 07 87 36 07 57'
                        required_amount = prompt_config.get('required_amount') or 2000
                        
                        context = {
                            'detected_objects': [],
                            'filtered_transactions': [{
                                'amount': amount,
                                'currency': 'FCFA',
                                'phone': payment_data.get('phone', ''),
                                'verified': payment_data.get('verified', False)
                            }],
                            'expected_deposit': required_amount,
                            'company_phone': wave_phone
                        }
                        
                        # Appeler Botlive
                        print(f"🔄 [FALLBACK] Appel Botlive avec context: {context}")
                        botlive_result = await botlive_hybrid.process_request(
                            user_id=user_id or "unknown",
                            message=query,
                            context=context,
                            conversation_history="",
                            company_id=company_id
                        )
                        
                        print(f"✅ [FALLBACK] Réponse Botlive reçue, retour au RAG")
                        return botlive_result.get('response', 'Erreur traitement paiement')
                        
                    except Exception as fallback_error:
                        print(f"❌ [FALLBACK] Erreur Botlive: {fallback_error}")
                        # Continuer avec RAG normal en cas d'erreur
                
                # Construire contexte selon type
                if image_analysis["type"] == "payment":
                    payment_data = image_analysis["data"]
                    image_context = f"""

📸 PREUVE PAIEMENT REÇUE:
- Montant: {payment_data.get('amount', 0)} FCFA
- Numéro: {payment_data.get('phone', 'Non détecté')}
- Transaction: {payment_data.get('transaction_id', 'Non détecté')}
- Statut: {'✅ VALIDÉ (≥2000 FCFA)' if payment_data.get('verified') else '❌ INSUFFISANT (<2000 FCFA)'}
- Vérifié le: {payment_data.get('verified_at', 'N/A')}

INSTRUCTION: Confirme ou refuse la commande selon le statut. Sois naturel et professionnel.
"""
                
                elif image_analysis["type"] == "product":
                    product_data = image_analysis["data"]
                    image_context = f"""

📸 IMAGE PRODUIT REÇUE:
- Produit: {product_data.get('product_name', 'Non identifié')}
- Type: {product_data.get('product_type', 'Non détecté')}
- Taille: {product_data.get('size', 'Non détectée')}
- Quantité visible: {product_data.get('quantity_visible', 'Non détectée')}
- Marque: {product_data.get('brand', 'Non détectée')}
- État: {product_data.get('condition', 'Non détecté')}

INSTRUCTION: Tu PEUX maintenant parler de ces détails précis sur le produit. 
Réponds naturellement à la question du client.
"""
                
                else:
                    image_context = f"""

📸 IMAGE REÇUE (type non identifié):
Analyse: {image_analysis.get('data', {}).get('raw_text', 'Aucune analyse disponible')}

INSTRUCTION: Demande poliment au client de préciser ce qu'il souhaite savoir sur cette image.
"""
                
                print(f"📝 [IMAGE_CONTEXT] Ajouté au prompt ({len(image_context)} chars)")
                
            except Exception as e:
                print(f"❌ [IMAGE_ERROR] Erreur analyse: {e}")
                image_context = "\n\n⚠️ Image reçue mais analyse échouée. Demande au client de la renvoyer."
        
        # ========== NOTEPAD CONVERSATIONNEL: EXTRACTION AUTOMATIQUE ==========
        try:
            from .conversation_notepad import (
                get_conversation_notepad,
                extract_product_info,
                extract_delivery_zone,
                extract_phone_number,
                extract_price_from_response
            )
            
            notepad = get_conversation_notepad()
            
            # Extraction automatique des infos de la requête utilisateur
            product_info = extract_product_info(query)
            if product_info:
                # Extraire le prix de la réponse LLM (on le fera après génération)
                logger.info(f"📝 Produit détecté: {product_info}")
            
            delivery_zone = extract_delivery_zone(query)
            if delivery_zone:
                logger.info(f"🚚 Zone détectée: {delivery_zone}")
            
            phone = extract_phone_number(query)
            if phone:
                notepad.update_phone(user_id, company_id, phone)
                logger.info(f"📞 Téléphone enregistré: {phone}")
            
        except Exception as e:
            logger.warning(f"⚠️ Erreur extraction notepad: {e}")
        
        # ========== EXTRACTION INTELLIGENTE ZONE LIVRAISON (REGEX + NORMALISATION) ==========
        delivery_context = ""
        delivery_zone_found = False  # ✅ Flag pour filtrage docs
        is_delivery_related_query = False
        try:
            q_lower = (query or "").lower()
            is_delivery_related_query = any(
                kw in q_lower
                for kw in [
                    "livraison",
                    "livrer",
                    "livrez",
                    "livre",
                    "frais",
                    "tarif",
                    "prix livraison",
                    "délai",
                    "delai",
                    "quartier",
                    "commune",
                    "zone",
                    "angre",
                    "rivier",
                    "cocody",
                    "yopougon",
                    "abobo",
                    "marcory",
                    "koumassi",
                    "plateau",
                    "treichville",
                    "adjame",
                    "adjamé",
                ]
            )
        except Exception:
            is_delivery_related_query = False
        
        try:
            from core.delivery_zone_extractor import (
                get_delivery_cost_smart,
                format_delivery_info
            )
            
            # Extraire zone de la requête avec normalisation
            delivery_info = get_delivery_cost_smart(query)
            
            if delivery_info.get("cost"):
                # Zone trouvée! Injecter dans notepad
                from core.conversation_notepad import get_conversation_notepad
                notepad = get_conversation_notepad()
                notepad.update_delivery(
                    user_id, 
                    company_id, 
                    delivery_info["name"], 
                    delivery_info["cost"]
                )
                logger.info(f"🚚 Zone extraite: {delivery_info['name']} = {delivery_info['cost']} FCFA (source: {delivery_info['source']})")
                
                # ✅ MARQUER ZONE TROUVÉE (pour filtrage docs MeiliSearch)
                delivery_zone_found = True
                
                # Formater pour injection dans prompt
                delivery_context = format_delivery_info(delivery_info)
                
        except Exception as e:
            logger.warning(f"⚠️ Extraction zone livraison échouée: {e}")
            delivery_context = ""
            delivery_zone_found = False
        
        # ✅ TOUJOURS AJOUTER L'HEURE CI (en début ou fin de delivery_context)
        try:
            from core.timezone_helper import get_delivery_context_with_time
            time_context = get_delivery_context_with_time()
            if time_context:
                # Si une zone est détectée, l'heure est déjà dans delivery_context via format_delivery_info()
                # Sinon, créer un delivery_context avec juste l'heure
                if not delivery_context and is_delivery_related_query:
                    delivery_context = time_context
                    logger.info(f"⏰ Heure CI injectée (aucune zone détectée)")
                else:
                    logger.info(f"⏰ Heure CI déjà incluse dans delivery_context (zone détectée)")
        except Exception as e:
            logger.warning(f"⚠️ Impossible d'injecter l'heure CI: {e}")
        
        # ========== MODE BOTLIVE: CONVERSATION GUIDÉE AVEC IMAGES ==========
        live_manager = LiveModeManager()
        if live_manager.get_status():
            print("🔴 [BOTLIVE] Mode Live actif - Traitement conversationnel guidé")
            
            # Import des modules Live
            from .live_conversation_state import get_live_conversation_state
            from .live_prompts import get_botlive_prompt, get_next_steps_instruction
            
            live_state = get_live_conversation_state()
            
            # Si des images sont fournies (depuis Messenger)
            if images and len(images) > 0:
                print(f"🔴 [BOTLIVE] {len(images)} image(s) reçue(s)")
                
                # Analyser chaque image avec YOLO/OCR
                for i, image_url in enumerate(images):
                    print(f"🔴 [BOTLIVE] Analyse image {i+1}: {image_url[:50]}...")
                    
                    try:
                        # Télécharger et analyser l'image
                        detection_result, detection_type = await self._analyze_live_image(image_url)
                        
                        # Fallback d'affectation si inconnu: assigner selon l'état manquant
                        if detection_type == "unknown":
                            missing_kind = live_state.get_missing(user_id)
                            if missing_kind in ("product", "payment"):
                                print(f"🔴 [BOTLIVE] Fallback assign => {missing_kind}")
                                detection_type = missing_kind
                        
                        # Stocker dans l'état conversationnel
                        status = live_state.add_detection(
                            user_id, company_id, image_url, detection_result, detection_type
                        )
                        
                        print(f"🔴 [BOTLIVE] Image analysée: type={detection_type}, status={status}")
                        
                        # Si commande complète
                        if status == "ready":
                            session = live_state.get_session(user_id)
                            final_message = await self._finalize_live_order(session)
                            live_state.clear(user_id)
                            return final_message
                        
                    except Exception as e:
                        print(f"🔴 [BOTLIVE] Erreur analyse image: {e}")
                        return "❌ Erreur lors de l'analyse de votre image. Veuillez réessayer."
            
            # Extraire zone livraison éventuelle depuis le message et mémoriser
            try:
                zone = self._extract_delivery_zone_from_text(query)
                if zone:
                    live_state.set_delivery_zone(user_id, zone)
            except Exception:
                pass

            # Générer contexte et prompt Botlive (avec frais livraison compacts)
            detection_context = live_state.get_context_for_llm(user_id)
            try:
                from .live_prompts import get_delivery_fees_compact
                detection_context = detection_context + get_delivery_fees_compact()
            except Exception:
                pass
            missing = live_state.get_missing(user_id)
            next_steps = get_next_steps_instruction(missing)
            
            botlive_prompt = get_botlive_prompt(company_name, detection_context, next_steps)
            
            print(f"🔴 [BOTLIVE] Contexte: {detection_context[:100]}...")
            print(f"🔴 [BOTLIVE] Étapes suivantes: {missing}")
            
            # Générer réponse avec prompt spécialisé Botlive
            try:
                response = await self.llm_client.complete(
                    prompt=f"{botlive_prompt}\n\nMessage utilisateur: {query}\n\nRéponse:",
                    temperature=0.3,  # Plus déterministe pour les commandes
                    max_tokens=512
                )
                
                print(f"🔴 [BOTLIVE] Réponse générée: {len(response)} chars")
                return response
                
            except Exception as e:
                print(f"🔴 [BOTLIVE] Erreur LLM: {e}")
                return "❌ Erreur technique. Veuillez réessayer."
        
        # --- Mode RAG Normal (existant) ---
        try:
            live_manager = LiveModeManager()
            if live_manager.get_status() and images and isinstance(images, (list, tuple)) and len(images) >= 2:
                # Import paresseux pour éviter l'import circulaire
                from .botlive_engine import BotliveEngine
                print("🔀 Redirection vers le moteur Botlive")
                botlive = BotliveEngine()
                return botlive.process_live_order(images[0], images[1])
        except Exception as e:
            print(f"[LIVE MODE] Erreur routage Botlive: {e}")

        # --- Patch robustesse LLM ---
        if self.llm_client is None:
            print("[LLM INIT] LLM client non initialisé, tentative de réinitialisation...")
            try:
                await self.initialize()
            except Exception as e:
                print(f"[LLM INIT][ERREUR] Impossible d'initialiser le LLM client: {e}")
                return "[ERREUR LLM] Impossible d'initialiser le modèle de langage."
        if self.llm_client is None:
            print("[LLM INIT][ERREUR] LLM client toujours None après initialisation.")
            return "[ERREUR LLM] LLM non disponible."

        print(f"🤖 [ÉTAPE 3] Génération LLM...")

        # --- Mémoire conversationnelle OPTIMISÉE ---
        try:
            from core.optimized_conversation_memory import get_optimized_conversation_context, add_user_conversation_message
        except ImportError:
            get_optimized_conversation_context = lambda *a, **kw: ""
            add_user_conversation_message = lambda *a, **kw: None
        
        conversation_context = ""
        if user_id:
            # D'abord récupérer le contexte existant
            conversation_context = get_optimized_conversation_context(user_id, company_id)
            print(f"🧠 Résumé mémoire conversationnelle OPTIMISÉE : {len(conversation_context)} caractères")
            
            # Puis ajouter le message utilisateur AVANT génération pour mise à jour du contexte
            try:
                await add_user_conversation_message(user_id, company_id, query, self.llm_client)
                # Récupérer le contexte mis à jour
                conversation_context = get_optimized_conversation_context(user_id, company_id)
                print(f"🧠 Contexte mis à jour après ajout message : {len(conversation_context)} caractères")
            except Exception as e:
                print(f"⚠️ Erreur mise à jour mémoire: {e}")
                # Continuer avec l'ancien contexte
        
        # ========== FILTRER DOCS LIVRAISON SI REGEX A TROUVÉ ==========
        # Si regex a trouvé la zone, supprimer les docs delivery de MeiliSearch (doublon)
        meili_context_filtered = search_results['meili_context']
        
        if delivery_zone_found:
            logger.info("✅ [DOCS] Zone trouvée par regex → Supprimer docs delivery de MeiliSearch (doublon)")
            
            # Filtrer les lignes contenant "LIVRAISON" ou "delivery_" dans l'index
            lines = meili_context_filtered.split('\n')
            filtered_lines = []
            skip_until_next_doc = False
            
            for line in lines:
                # Détecter début d'un document delivery
                if 'delivery_' in line or 'LIVRAISON -' in line:
                    skip_until_next_doc = True
                    continue
                
                # Détecter début d'un nouveau document (réinitialiser le skip)
                if line.startswith('DOCUMENT #'):
                    skip_until_next_doc = False
                
                # Garder la ligne si on ne skip pas
                if not skip_until_next_doc:
                    filtered_lines.append(line)
            
            meili_context_filtered = '\n'.join(filtered_lines)
            logger.info(f"📦 [DOCS] Docs delivery filtrés: {len(lines)} → {len(filtered_lines)} lignes")
        
        # ========== 🚀 OPTIMISATION CONTEXTE (Meili priority + Budget tokens) ==========
        try:
            from core.context_optimizer import optimize_rag_context, get_history_optimizer
            
            # Optimiser le contexte avec fallback intelligent + budgets
            optimization_result = optimize_rag_context(
                meili_context=meili_context_filtered,
                supabase_context=search_results.get('supabase_context', ''),
                query=query,
                scored_docs=None,  # Pas de docs scorés ici
                keywords=None
            )
            
            optimized_context = optimization_result['optimized_context']
            
            # Log des économies
            if optimization_result['total_chars_saved'] > 0:
                print(f"💰 [OPTIMIZE] Économie: {optimization_result['total_chars_saved']} chars")
                print(f"   → Supabase utilisé: {optimization_result['used_supabase']} ({optimization_result['fallback_reason']})")
            
            # Optimiser aussi l'historique de conversation
            if conversation_context:
                history_optimizer = get_history_optimizer()
                # Si conversation_context est déjà formaté, on le garde tel quel mais on le tronque si nécessaire
                if len(conversation_context) > 1200:
                    conversation_context = conversation_context[:1200] + "\n..."
                    print(f"🧠 [HISTORY] Tronqué à 1200 chars")
            
            # Construction du contexte structuré optimisé
            context_parts = []
            if conversation_context:
                context_parts.append(conversation_context)
            if optimized_context:
                context_parts.append(optimized_context)
            
            structured_context = "\n".join(context_parts) if context_parts else "Aucun document trouvé"
            
        except Exception as e:
            print(f"⚠️ [OPTIMIZE] Fallback assemblage classique: {e}")
            # Fallback: assemblage classique sans optimisation
            context_parts = []
            if conversation_context:
                context_parts.append(conversation_context)
            if meili_context_filtered:
                context_parts.append(meili_context_filtered)
            if search_results.get('supabase_context'):
                context_parts.append(search_results['supabase_context'])
            structured_context = "\n".join(context_parts) if context_parts else "Aucun document trouvé"
        
        print(f"📄 Contexte: {len(structured_context)} caractères")
        # Log contexte réduit
        context_preview = structured_context[:100] + ('...' if len(structured_context) > 100 else '')
        print(f"📄 [CONTEXTE] {context_preview}")
        
        # ========== AFFICHAGE VIOLET : CONTEXTE FINAL COMPLET ENVOYÉ AU LLM ==========
        if structured_context and structured_context != "Aucun document trouvé":
            print(f"\033[95m" + "="*80 + "\033[0m")
            print(f"\033[95m🟣 CONTEXTE FINAL COMPLET ENVOYÉ AU LLM\033[0m")
            print(f"\033[95m" + "="*80 + "\033[0m")
            print(f"\033[95m{structured_context}\033[0m")
            print(f"\033[95m" + "="*80 + "\033[0m")

        # --- ENRICHISSEMENT CONTEXTE PAR EXTRACTION REGEX --- DÉSACTIVÉ
        # ⚠️ SYSTÈME DÉSACTIVÉ : Le LLM avec <thinking> gère lui-même l'extraction
        # Ce système filtrait les documents et ne gardait que certaines infos
        # Désormais : Documents complets envoyés au LLM qui décide lui-même
        print("\n📄 [CONTEXTE] Envoi des documents COMPLETS au LLM (regex extraction désactivée)")
        
        # try:
        #     print("\n🔎 [REGEX] Début extraction regex sur les documents pertinents...")
        #     from core.rag_regex_extractor import extract_regex_entities_from_docs
        #     # Simulation : reconstituer la liste des docs pertinents (Meili ou Supabase)
        #     docs = []
        #     if hasattr(search_results, 'meili_docs') and search_results['meili_docs']:
        #         docs = search_results['meili_docs']
        #         print(f"[REGEX] {len(docs)} docs MeiliSearch à analyser")
        #     elif hasattr(search_results, 'supabase_docs') and search_results['supabase_docs']:
        #         docs = search_results['supabase_docs']
        #         print(f"[REGEX] {len(docs)} docs Supabase à analyser")
        #     # Sinon, fallback : tenter d'extraire les docs depuis le contexte brut
        #     if not docs and structured_context:
        #         docs = [{"content": structured_context}]
        #         print("[REGEX] Aucun doc structuré, fallback sur contexte brut")
        #     print("[REGEX] Chargement des patterns métier...")
        #     regex_entities = extract_regex_entities_from_docs(docs)
        #     print(f"[REGEX] Extraction terminée. Patterns trouvés : {sum(len(v) for v in regex_entities.values())}")
        #     regex_summary = []
        #     for label, values in regex_entities.items():
        #         if values:
        #             regex_summary.append(f"[REGEX {label}] " + ", ".join(set(values)))
        #             print(f"[REGEX] {label}: {values}")
        #     if regex_summary:
        #         structured_context += "\n\n" + "\n".join(regex_summary)
        #         print(f"[REGEX] Extraits ajoutés au contexte : {len(regex_summary)} patterns structurés")
        #         print(f"[REGEX] [DÉTAIL EXTRAITS] Entités ajoutées:\n" + "\n".join(regex_summary))
        #     else:
        #         print("[REGEX] Aucune entité extraite des documents")
        #     print("[REGEX] Auto-apprentissage : vérification de nouveaux patterns potentiels (voir logs de core/rag_regex_extractor.py)")
        #     print(f"[REGEX] [CONTEXTE FINAL] Taille après enrichissement: {len(structured_context)} caractères")
        # except Exception as e:
        #     print(f"[REGEX] Erreur enrichissement contexte : {e}")
        
        # 📋 PROMPT DÉJÀ RÉCUPÉRÉ AU DÉBUT (avant traitement image)
        print(f"📋 [DÉTAIL PROMPT] Contenu:\n{dynamic_prompt[:300]}{'...' if len(dynamic_prompt) > 300 else ''}")
        
        # Enrichissement intelligent du prompt avec détection de remises
        pricing_enhancement = self._detect_pricing_context(query, structured_context)
        
        # 🚀 CONSTRUCTION PROMPT CLASSIQUE (Enhanced désactivé)
        # Le système enhanced_prompt_engine générait des templates buggy
        # Désactivé pour utiliser directement le prompt simple
        print("✅ Utilisation du prompt classique (enhanced désactivé)")
        
        # Construction dynamique du prompt : remplacement des placeholders par les vraies valeurs
        conversation_history = search_results.get('conversation_history', '')
        system_prompt = dynamic_prompt
        system_prompt = system_prompt.replace("{context}", structured_context)
        system_prompt = system_prompt.replace("{history}", conversation_history)
        system_prompt = system_prompt.replace("{question}", query)
        if pricing_enhancement:
            system_prompt = system_prompt.replace("{pricing_enhancement}", pricing_enhancement)
        else:
            system_prompt = system_prompt.replace("{pricing_enhancement}", "")
        
        # ========== INJECTION CONTEXTE IMAGE ==========
        if image_context:
            system_prompt += image_context
            print("✅ [PROMPT] Contexte image injecté")
        
        # ========== INJECTION CONTEXTE LIVRAISON (REGEX EXTRACTION) ==========
        if delivery_context and (delivery_zone_found or is_delivery_related_query):
            # Injecter UNE SEULE FOIS avant <context> (remplacer seulement la 1ère occurrence)
            system_prompt = system_prompt.replace(
                "<context>",
                f"{delivery_context}\n\n<context>",
                1  # Remplacer UNIQUEMENT la 1ère occurrence
            )
            print("✅ [PROMPT] Contexte livraison injecté (frais exacts)")
        
        # ========== ENRICHISSEMENT CONTEXTE BOTLIVE (STATE + NOTEPAD) ==========
        try:
            from core.rag_tools_integration import enrich_prompt_with_context
            
            # Enrichir avec état commande et notepad si user_id disponible
            if user_id:
                system_prompt = enrich_prompt_with_context(
                    base_prompt=system_prompt,
                    user_id=user_id,
                    company_id=company_id,  # ✅ Passer company_id pour notepad
                    include_state=True,  # Inclure état commande
                    include_notepad=True  # Inclure notes utilisateur
                )
                print(f"🎨 Prompt enrichi avec contexte utilisateur (state + notepad)")
        except Exception as e:
            print(f"⚠️ Enrichissement contexte échoué: {e}")
        
        # ========== INJECTION ENHANCED MEMORY DANS PROMPT (PRIORITAIRE) ==========
        try:
            from .enhanced_memory import get_enhanced_memory
            
            if user_id:
                enhanced_memory = get_enhanced_memory()
                memory_context = enhanced_memory.get_context_for_llm(user_id, company_id)
                
                if memory_context:
                    system_prompt += f"\n\n{memory_context}"
                    print(f"🧠 [ENHANCED_MEMORY] Contexte injecté ({len(memory_context)} chars)")
        except Exception as e:
            print(f"⚠️ [ENHANCED_MEMORY] Injection échouée: {e}")
        
        # ========== INJECTION CONTEXTE NOTEPAD (SIMPLIFIÉ) ==========
        try:
            from .conversation_notepad import ConversationNotepad
            
            if user_id:
                notepad = ConversationNotepad.get_instance()
                notepad_data = notepad.get_all(user_id, company_id)
                
                if notepad_data:
                    # Construire contexte formaté
                    notepad_lines = ["\n📋 CONTEXTE COLLECTÉ (NE PAS REDEMANDER):"]
                    if notepad_data.get('produit'):
                        notepad_lines.append(f"   ✅ Produit: {notepad_data['produit']}")
                    if notepad_data.get('zone'):
                        notepad_lines.append(f"   ✅ Zone: {notepad_data['zone']}")
                    if notepad_data.get('telephone'):
                        notepad_lines.append(f"   ✅ Téléphone: {notepad_data['telephone']}")
                    if notepad_data.get('paiement'):
                        notepad_lines.append(f"   ✅ Paiement: {notepad_data['paiement']}")
                    
                    notepad_context = "\n".join(notepad_lines)
                    system_prompt += f"\n{notepad_context}\n"
                    logger.info(f"📋 Contexte notepad injecté: {len(notepad_context)} chars")
        except Exception as e:
            logger.warning(f"⚠️ Injection notepad échouée: {e}")
        
        # Ajout fallback si bloc question/contexte absent
        if "{question}" in system_prompt:
            system_prompt += f"\nQUESTION: {query}"
        if "{context}" in system_prompt:
            system_prompt += f"\nCONTEXTE DISPONIBLE:\n{structured_context}"
        system_prompt += "\n\nRÉPONSE:"
        
        # --- LOG ENRICHISSANT AVANT ENVOI LLM ---
        def highlight(val, color_code):
            return f"\033[{color_code}m{val}\033[0m"

        prompt_log = system_prompt
        injects = {
            company_name: '93',  # Jaune
            "Assistant": '92',   # Vert (ai_name)
            "commerce": '96',    # Cyan (secteur_activite)
            query: '91',          # Rouge (question)
        }
        for val, code in injects.items():
            if val and isinstance(val, str) and len(val) > 0:
                prompt_log = prompt_log.replace(val, highlight(val, code))
        # pricing_enhancement en magenta si présent
        if pricing_enhancement.strip():
            prompt_log = prompt_log.replace(pricing_enhancement.strip(), highlight(pricing_enhancement.strip(), '95'))
        # Context en bleu
        if structured_context.strip():
            prompt_log = prompt_log.replace(structured_context.strip(), highlight(structured_context.strip(), '94'))

        # Affichage COMPLET du prompt pour debug
        print(f"\n{'='*80}")
        print(f"🧠 PROMPT COMPLET ENVOYÉ AU LLM ({len(system_prompt)} chars)")
        print(f"{'='*80}")
        print(system_prompt)
        print(f"{'='*80}")
        
        try:
            # ========== TRACKING: APPEL LLM ==========
            try:
                from core.rag_performance_tracker import get_tracker
                tracker = get_tracker(getattr(self, '_request_id', 'unknown'))
                tracker.start_step("llm_generation", prompt_length=len(system_prompt))
            except:
                tracker = None
            
            llm_result = await self.llm_client.complete(
                prompt=system_prompt,
                temperature=0.7,
                max_tokens=1024  # Augmenté de 400 à 1024 pour réponses complètes
            )
            
            # Extraire réponse et usage
            token_usage = {}
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0
            total_cost = 0.0
            if isinstance(llm_result, dict):
                response = llm_result.get("response", llm_result)
                token_usage = llm_result.get("usage", {}) or {}
                model_used = llm_result.get("model", "unknown")

                try:
                    if isinstance(token_usage, dict):
                        prompt_tokens = int(token_usage.get("prompt_tokens") or 0)
                        completion_tokens = int(token_usage.get("completion_tokens") or 0)
                        total_tokens = int(token_usage.get("total_tokens") or (prompt_tokens + completion_tokens) or 0)
                        total_cost = float(
                            token_usage.get("total_cost")
                            if token_usage.get("total_cost") is not None
                            else (token_usage.get("cost") or 0.0)
                        )
                except Exception:
                    prompt_tokens = 0
                    completion_tokens = 0
                    total_tokens = 0
                    total_cost = 0.0
                
                # Enregistrer usage tokens
                if tracker and token_usage:
                    tracker.record_llm_usage(
                        model=model_used,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens
                    )
                    tracker.end_step(response_length=len(str(response)))
            else:
                response = llm_result
                if tracker:
                    tracker.end_step(response_length=len(str(response)))
            
            print(f"✅ LLM réponse: {len(str(response))} caractères")
            
            # ========== AFFICHAGE COLORÉ DE LA RÉPONSE LLM ==========
            print("\n\033[1m===== [RÉPONSE LLM COMPLÈTE] =====\033[0m")
            print(f"\033[93m{response}\033[0m")  # JAUNE pour la réponse complète
            print("\033[1m===== [FIN RÉPONSE LLM] =====\033[0m\n")
            
            # ========== SAUVEGARDE RÉPONSE COMPLÈTE (pour tests) ==========
            full_llm_response = response  # Sauvegarder AVANT extraction
            
            # ========== EXTRACTION BALISE <response> + OUTILS BOTLIVE ==========
            # Utiliser le système d'extraction avancé de Botlive
            thinking = ""  # Initialiser AVANT le try
            try:
                from core.rag_tools_integration import process_llm_response
                
                # Traitement complet avec outils
                processed = process_llm_response(
                    llm_output=response,
                    user_id=user_id,
                    enable_tools=True  # Activer calculator, notepad, state tracker
                )
                
                response = processed["response"]
                # ✅ CRITIQUE: Ne pas écraser thinking s'il est déjà rempli
                extracted_thinking = processed.get("thinking", "")
                if extracted_thinking:  # Seulement si non vide
                    thinking = extracted_thinking
                tools_executed = processed.get("tools_executed", 0)
                
                # Stocker pour accès externe (tests)
                self._last_full_response = full_llm_response
                self._last_thinking = thinking
                
                print(f"✅ Extraction <response>: {len(response)} chars")
                if thinking:
                    print(f"🧠 Thinking extrait: {len(thinking)} chars")
                if tools_executed > 0:
                    print(f"🔧 Outils exécutés: {tools_executed}")
                    
            except Exception as e:
                # Fallback: extraction simple
                print(f"⚠️ Fallback extraction simple: {e}")
                response_match = re.search(r'<response>(.*?)</response>', response, re.DOTALL | re.IGNORECASE)
                if response_match:
                    response = response_match.group(1).strip()
                else:
                    response = re.sub(r'<thinking>.*?</thinking>', '', response, flags=re.DOTALL | re.IGNORECASE).strip()
            
            # ========== POST-TRAITEMENT: ENHANCED MEMORY (PRIORITAIRE) ==========
            try:
                from .enhanced_memory import get_enhanced_memory
                
                if user_id:
                    enhanced_memory = get_enhanced_memory()
                    enhanced_memory.save_interaction(
                        user_id=user_id,
                        company_id=company_id,
                        user_message=query,
                        llm_response=response
                    )
                    logger.info(f"🧠 Enhanced memory mise à jour")
            except Exception as e:
                logger.warning(f"⚠️ Enhanced memory échoué: {e}")
            
            # ========== POST-TRAITEMENT: MISE À JOUR NOTEPAD AVEC RÉPONSE LLM ==========
            try:
                from .conversation_notepad import (
                    get_conversation_notepad,
                    extract_price_from_response
                )
                
                if user_id and product_info:
                    notepad = get_conversation_notepad()
                    
                    # Extraire le prix de la réponse LLM
                    price = extract_price_from_response(response)
                    
                    if price:
                        notepad.update_product(
                            user_id, company_id,
                            product_name=product_info['product_type'],
                            quantity=product_info['quantity'],
                            price=price,
                            variant=product_info.get('variant')
                        )
                        logger.info(f"💰 Prix extrait et enregistré: {price} FCFA")
                
                # Mise à jour zone de livraison si détectée
                if user_id and delivery_zone:
                    # Extraire le coût de livraison de la réponse
                    delivery_cost_match = re.search(
                        r'livraison[^0-9]*(\d+[\s\u202f]?\d{3})\s*(?:FCFA|F)',
                        response
                    )
                    if delivery_cost_match:
                        cost_str = delivery_cost_match.group(1).replace('\u202f', '').replace(' ', '')
                        delivery_cost = float(cost_str)
                        
                        notepad = get_conversation_notepad()
                        notepad.update_delivery(user_id, company_id, delivery_zone, delivery_cost)
                        logger.info(f"🚚 Livraison enregistrée: {delivery_zone} - {delivery_cost} FCFA")
                
            except Exception as e:
                logger.warning(f"⚠️ Post-traitement notepad échoué: {e}")
            
            # ========== CALCUL ET AFFICHAGE COLORÉ DES TOKENS ==========
            try:
                import tiktoken
                enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
                prompt_tokens = len(enc.encode(system_prompt))
                response_tokens = len(enc.encode(response))
            except Exception:
                # fallback simple : split sur les espaces
                prompt_tokens = len(system_prompt.split())
                response_tokens = len(response.split())
            
            total_tokens = prompt_tokens + response_tokens
            
            # ROUGE pour les infos de tokens
            print(f"\033[91m[LLM] Tokens totaux prompt+réponse : {total_tokens} {'(TROP ÉLEVÉ)' if total_tokens > 4000 else '(OK)'}\033[0m")
            print(f"\033[91m[LLM] Détail : prompt={prompt_tokens} | réponse={response_tokens} (estimation coût)\033[0m")
            # Mémoire déjà mise à jour AVANT génération - pas besoin de re-traitement
            
            # ========== RETOURNER RÉPONSE + MÉTRIQUES TOKENS ==========
            # Stocker les métriques pour utilisation dans process_query
            self._last_token_usage = token_usage
            self._last_prompt_tokens = prompt_tokens
            self._last_completion_tokens = completion_tokens
            self._last_total_tokens = total_tokens
            self._last_total_cost = total_cost
            self._last_model_used = model_used

            # --- RÉCAPITULATIF AUTOMATIQUE DÉSACTIVÉ (génère prix fantômes) ---
            # Cause: Template bugué avec "500 FCFA" inexistants
            # À réactiver après correction du template
            # from core.recap_template import generate_order_summary
            #
            # user_query_lower = query.lower()
            # add_recap = any(word in user_query_lower for word in ['récap', 'récapitulatif', 'résumé', 'confirmation', 'commande'])
            #
            # if generate_order_summary and add_recap:
            #     conversation_history = []
            #     if user_id:
            #         try:
            #             from core.conversation_memory import get_full_conversation_history
            #             conversation_history = get_full_conversation_history(user_id, company_id)
            #         except:
            #             conversation_history = [{"message": query, "user_id": user_id}]
            #     
            #     customer_info = self._extract_customer_from_context(conversation_history, user_id)
            #     products = self._extract_products_from_context(query, structured_context, conversation_history)
            #     delivery_info = self._extract_delivery_from_context(query, structured_context, customer_info)
            #     price_info = self._calculate_dynamic_pricing(products, delivery_info, structured_context)
            #     
            #     recap = generate_order_summary(customer_info, products, delivery_info, price_info, company_id)
            #     response += f"\n\n📋 RÉCAPITULATIF STRUCTURÉ :\n{recap}"

            # ========== EXÉCUTION DES ACTIONS LLM (BLOC-NOTE, CALCULATRICE) ==========
            try:
                from core.botlive_tools import execute_tools_in_response
                response = execute_tools_in_response(
                    response, 
                    user_id or "unknown", 
                    company_id
                )
                print("✅ [TOOLS] Actions LLM exécutées (bloc-note, calculatrice)")
            except Exception as e:
                print(f"⚠️ [TOOLS] Erreur exécution actions: {e}")

            return response
        except Exception as e:
            print(f"❌ LLM erreur: {str(e)[:50]}")
            return f"Je rencontre une difficulté technique. Pouvez-vous reformuler votre question ?"
    
    async def _analyze_live_image(self, image_url: str) -> tuple:
        """
        Analyse une image avec YOLO/OCR pour déterminer son type et contenu.
        
        Returns:
            tuple: (detection_result: dict, detection_type: str)
        """
        import tempfile
        import requests
        import os
        
        # Télécharger l'image
        try:
            r = requests.get(image_url, timeout=15)
            r.raise_for_status()
            
            # Créer fichier temporaire
            fd, temp_path = tempfile.mkstemp(suffix=".jpg")
            with os.fdopen(fd, "wb") as f:
                f.write(r.content)
            
            # Analyser avec BotliveEngine
            from .botlive_engine import BotliveEngine
            engine = BotliveEngine()
            
            # Tenter détection produit
            product_result = engine.detect_product(temp_path)
            
            # Tenter OCR paiement
            payment_result = engine.verify_payment(temp_path)
            
            # Déterminer le type d'image (heuristique renforcée)
            import re
            raw = (payment_result.get("raw_text", "") or "").lower()
            has_currency = bool(re.search(r"\b(fcfa|xof|cfa)\b", raw))
            has_amount = bool(re.search(r"\b\d{3,6}\b", raw))  # 3 à 6 chiffres consécutifs
            has_payment_kw = any(k in raw for k in ["wave", "orange", "mtn", "moov", "momo", "paiement", "recu", "reçu"]) 

            if payment_result.get("amount") or (has_currency and has_amount) or (has_payment_kw and has_amount):
                return payment_result, "payment"
            elif product_result.get("confidence", 0) >= 0.25:
                return product_result, "product"
            else:
                # Image non reconnue - demander à l'utilisateur
                return {
                    "name": "image_non_reconnue",
                    "confidence": 0.0,
                    "raw_text": payment_result.get("raw_text", "")
                }, "unknown"
        
        except Exception as e:
            print(f"[BOTLIVE] Erreur analyse image: {e}")
            return {"error": str(e)}, "error"
        
        finally:
            # Nettoyer le fichier temporaire
            try:
                if 'temp_path' in locals():
                    os.remove(temp_path)
            except Exception:
                pass
    
    async def _finalize_live_order(self, session: dict) -> str:
        """
        Finalise une commande Live avec les 2 images collectées.
        
        Args:
            session: Session contenant product_img, payment_img et détections
        
        Returns:
            Message de confirmation de commande
        """
        try:
            # Extraire les informations des détections
            product_detection = session.get("product_detection", {})
            payment_detection = session.get("payment_detection", {})
            
            # Construire le message de confirmation
            product_name = product_detection.get("name", "produit")
            product_confidence = product_detection.get("confidence", 0) * 100
            
            payment_amount = payment_detection.get("amount", "")
            payment_currency = payment_detection.get("currency", "FCFA")
            payment_ref = payment_detection.get("reference", "")
            
            # Message de base
            confirmation_parts = [
                "🎉 **COMMANDE VALIDÉE !**",
                "",
                f"📦 **Produit:** {product_name} (détection: {product_confidence:.1f}%)"
            ]
            
            # Informations de paiement
            if payment_amount:
                confirmation_parts.append(f"💳 **Paiement:** {payment_amount} {payment_currency}")
            else:
                confirmation_parts.append("💳 **Paiement:** Montant détecté mais non lisible")
            
            if payment_ref:
                confirmation_parts.append(f"📋 **Référence:** {payment_ref}")
            
            confirmation_parts.extend([
                "",
                "✅ Votre commande est en cours de traitement.",
                "📞 Nous vous contacterons pour la livraison.",
                "",
                "Merci de votre confiance ! 🙏"
            ])
            
            # TODO: Sauvegarder en base de données
            # await self._save_live_order_to_db(session)
            
            return "\n".join(confirmation_parts)
            
        except Exception as e:
            print(f"[BOTLIVE] Erreur finalisation: {e}")
            return "✅ Commande reçue ! Nous la traitons et vous recontactons rapidement."
    
    def _extract_config_from_prompt(self, prompt: str) -> dict:
        """Extrait WAVE_ENTREPRISE et ACOMPTE_REQUIS du prompt"""
        import re

        config = {
            'wave_phone': None,
            'required_amount': None
        }

        if not prompt:
            return config

        # Extraire WAVE_ENTREPRISE: +225 0787360757
        wave_match = re.search(r'WAVE_ENTREPRISE:\s*\+?([\d\s]+)', prompt)
        if wave_match:
            config['wave_phone'] = re.sub(r'\s+', '', wave_match.group(1))

        # Extraire ACOMPTE_REQUIS: 2000 FCFA
        acompte_match = re.search(r'ACOMPTE_REQUIS:\s*(\d+)\s*FCFA', prompt)
        if acompte_match:
            try:
                config['required_amount'] = int(acompte_match.group(1))
            except Exception:
                config['required_amount'] = None

        return config

    async def _get_dynamic_prompt(self, company_id: str, company_name: str) -> str:
        """📋 Récupère le prompt dynamique depuis Supabase (prompt_botlive_deepseek_v3)."""
        # Source de vérité: même champ que Botlive
        try:
            from core.botlive_prompts_supabase import BotlivePromptsManager

            manager = BotlivePromptsManager()
            prompt = manager.get_prompt(company_id=company_id, llm_choice="deepseek-v3")
            if prompt and len(prompt) > 50:
                return prompt
        except Exception as e:
            logger.warning(f"⚠️ Prompt prompt_botlive_deepseek_v3 indisponible ({company_id}): {e}")

        # Fallback final
        return f"Tu es un assistant client professionnel pour {company_name}."
    
    def _detect_pricing_context(self, query: str, context: str) -> str:
        """Détecte intelligemment les questions de prix et remises pour enrichir le prompt"""
        
        query_lower = query.lower()
        context_lower = context.lower()
        
        # Détection de questions sur les remises/quantités
        quantity_keywords = ["paquets", "quantité", "remise", "réduction", "prix", "tarif", "combien", "coûte"]
        pricing_keywords = ["fcfa", "prix", "tarif", "coût", "montant"]
        
        is_quantity_question = any(word in query_lower for word in quantity_keywords)
        has_pricing_context = any(word in context_lower for word in pricing_keywords)
        
        if is_quantity_question and has_pricing_context:
            # Extraction dynamique des tarifs dégressifs depuis le contexte
            
            # Patterns pour détecter les tarifs dégressifs
            degressive_patterns = [
                r"(\d+)\s*paquets?\s*[-–—]\s*([0-9,\.]+)\s*f?\s*cfa",
                r"(\d+)\s*[-–—]\s*([0-9,\.]+)\s*f?\s*cfa.*?([0-9,\.]+)\s*f/paquet",
                r"(\d+)\s*paquets?\s*\([^)]*\)\s*[-–—]\s*([0-9,\.]+)\s*f?\s*cfa"
            ]
            
            pricing_info = []
            for pattern in degressive_patterns:
                matches = re.findall(pattern, context_lower)
                for match in matches:
                    try:
                        quantity = int(match[0])
                        price = match[1].replace(",", "").replace(".", "")
                        if quantity > 1 and len(price) >= 3:  # Prix réaliste
                            pricing_info.append(f"{quantity} paquets = {match[1]} FCFA")
                    except:
                        continue
            
            if pricing_info:
                return f"""
INSTRUCTION SPÉCIALE TARIFICATION:
- Vérifiez TOUJOURS les tarifs dégressifs dans le contexte
- Tarifs détectés: {' | '.join(pricing_info[:5])}
- Si le client demande une quantité spécifique, cherchez le tarif exact dans le contexte
- Calculez les économies réalisées par rapport au prix unitaire
- Mentionnez explicitement les remises disponibles"""
        
        # Détection de questions sur l'acompte
        if any(word in query_lower for word in ["acompte", "payer", "total", "confirmer", "commande"]):
            # Recherche directe de l'acompte dans le contexte
            acompte_found = None
            acompte_patterns = [
                r"un acompte de (\d+) fcfa",
                r"acompte de (\d+) fcfa", 
                r"condition de commande.*?(\d+) fcfa",
                r"acompte.*?(\d+).*?fcfa"
            ]
            
            for pattern in acompte_patterns:
                match = re.search(pattern, context_lower)
                if match:
                    try:
                        amount = int(match.group(1))
                        if 500 <= amount <= 50000:
                            acompte_found = amount
                            break
                    except:
                        continue
            
            if acompte_found:
                return f"""
INSTRUCTION SPÉCIALE PAIEMENT:
- ACOMPTE DÉTECTÉ: {acompte_found} FCFA dans le contexte
- Mentionnez explicitement: "Un acompte de {acompte_found} FCFA est requis"
- Ne jamais indiquer 0 FCFA car l'acompte est de {acompte_found} FCFA
- Utilisez cette information pour tous les calculs de paiement"""
            else:
                return """
INSTRUCTION SPÉCIALE PAIEMENT:
- Recherchez dans le contexte les informations sur l'acompte requis
- Patterns à chercher: "acompte de X FCFA", "condition de commande", "avant que la commande"
- Extrayez le montant exact de l'acompte depuis le contexte
- Ne jamais indiquer 0 FCFA si un acompte est mentionné dans le contexte"""
        
        return ""
    
    def _extract_customer_from_context(self, conversation_history: List[Dict], user_id: str) -> Dict[str, Any]:
        """Extrait intelligemment les informations client depuis l'historique"""
        customer_info = {
            "name": user_id,
            "phone": "",
            "address": ""
        }
        
        for message in conversation_history:
            text = message.get("message", "").lower()
            
            # Extraction nom
            name_patterns = [
                r"mon nom (?:c'est|est) ([a-zA-ZÀ-ÿ\s]+)",
                r"je (?:m'appelle|suis) ([a-zA-ZÀ-ÿ\s]+)",
                r"nom[:\s]+([a-zA-ZÀ-ÿ\s]+)"
            ]
            
            for pattern in name_patterns:
                match = re.search(pattern, text)
                if match:
                    name = match.group(1).strip().title()
                    if len(name) > 2 and len(name) < 50:
                        customer_info["name"] = name
                        break
            
            # Extraction téléphone
            phone_patterns = [
                r"(\+225\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{2})",
                r"(0\d{2}\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{2})",
                r"(\d{10})"
            ]
            
            for pattern in phone_patterns:
                match = re.search(pattern, text)
                if match:
                    phone = re.sub(r'\s+', '', match.group(1))
                    if len(phone) >= 10:
                        customer_info["phone"] = phone
                        break
            
            # Extraction adresse/zone
            location_keywords = ["cocody", "yopougon", "plateau", "adjamé", "abobo", "marcory", "koumassi", "treichville"]
            for keyword in location_keywords:
                if keyword in text:
                    customer_info["address"] = keyword.title()
                    break
        
        return customer_info
    
    def _extract_products_from_context(self, query: str, context: str, conversation_history: List[Dict]) -> List[Dict[str, Any]]:
        """Extrait intelligemment les produits depuis le contexte et la conversation"""
        products = []
        
        # Analyser la conversation pour les produits mentionnés
        all_text = query + " " + " ".join([msg.get("message", "") for msg in conversation_history])
        text_lower = all_text.lower()
        
        # Extraction quantité
        quantity_patterns = [
            r"(\d+)\s*paquets?",
            r"quantité[:\s]*(\d+)",
            r"je (?:veux|souhaite|prends)\s*(\d+)"
        ]
        
        quantity = 1
        for pattern in quantity_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    quantity = int(match.group(1))
                    if 1 <= quantity <= 100:  # Validation réaliste
                        break
                except:
                    continue
        
        # Extraction type de produit
        product_type = "Non spécifié"
        if "culottes" in text_lower:
            product_type = "Couches culottes"
        elif "pression" in text_lower:
            product_type = "Couches à pression"
        elif "adultes" in text_lower:
            product_type = "Couches adultes"
        
        # Extraction taille (numérique ET alphabétique)
        size = "Non spécifiée"
        size_patterns = [
            # Tailles alphabétiques (XL, L, M, S, etc.)
            r"taille\s*(xl|xxl|l|m|s|xs)",
            r"size\s*(xl|xxl|l|m|s|xs)",
            r"\b(xl|xxl|l|m|s|xs)\b",
            # Tailles numériques (1, 2, 3, 4, etc.)
            r"taille\s*(\d+)",
            r"size\s*(\d+)",
            r"t(\d+)"
        ]
        
        for pattern in size_patterns:
            match = re.search(pattern, text_lower)
            if match:
                extracted_size = match.group(1).upper()
                # Formatage selon le type
                if extracted_size.isdigit():
                    size = f"Taille {extracted_size}"
                else:
                    size = f"Taille {extracted_size}"
                break
        
        # Extraction prix depuis le contexte (dynamique)
        unit_price = 0
        total_price = 0
        
        # Recherche prix dans le contexte pour la quantité exacte
        price_patterns = [
            rf"{quantity}\s*paquets?\s*[-–—]\s*([0-9,\.]+)\s*f?\s*cfa",
            r"(\d+)\s*paquets?\s*[-–—]\s*([0-9,\.]+)\s*f?\s*cfa"
        ]
        
        context_lower = context.lower()
        for pattern in price_patterns:
            matches = re.findall(pattern, context_lower)
            for match in matches:
                try:
                    if isinstance(match, tuple):
                        qty, price_str = match[0], match[1] if len(match) > 1 else match[0]
                        if int(qty) == quantity:
                            total_price = int(price_str.replace(",", "").replace(".", ""))
                            unit_price = total_price // quantity
                            break
                    else:
                        total_price = int(match.replace(",", "").replace(".", ""))
                        unit_price = total_price // quantity
                        break
                except:
                    continue
        
        # Si pas de prix exact trouvé, chercher prix unitaire
        if unit_price == 0:
            unit_patterns = [
                r"1\s*paquet\s*[-–—]\s*([0-9,\.]+)\s*f?\s*cfa",
                r"prix\s*unitaire[:\s]*([0-9,\.]+)"
            ]
            
            for pattern in unit_patterns:
                match = re.search(pattern, context_lower)
                if match:
                    try:
                        unit_price = int(match.group(1).replace(",", "").replace(".", ""))
                        total_price = unit_price * quantity
                        break
                    except:
                        continue
        
        products.append({
            "description": f"{product_type} {size}",
            "type": product_type.split()[-1].lower() if product_type != "Non spécifié" else "produit",
            "size": size,
            "quantity": quantity,
            "unit_price": unit_price,
            "total_price": total_price
        })
        
        return products
    
    def _extract_delivery_from_context(self, query: str, context: str, customer_info: Dict) -> Dict[str, Any]:
        """Extrait intelligemment les informations de livraison"""
        delivery_info = {
            "zone": customer_info.get("address", "Non spécifiée"),
            "delivery_cost": 0,
            "delivery_time": "À confirmer",
            "address": customer_info.get("address", "Non fournie")
        }
        
        # Extraction coût de livraison depuis le contexte
        zone_lower = delivery_info["zone"].lower()
        context_lower = context.lower()
        
        # Patterns pour détecter les coûts de livraison par zone
        delivery_patterns = [
            rf"{zone_lower}[^0-9]*(\d+)\s*fcfa",
            r"zones?\s*centrales?[^0-9]*(\d+)\s*fcfa",
            r"abidjan[^0-9]*(\d+)\s*fcfa",
            r"tarif[:\s]*(\d+)\s*fcfa"
        ]
        
        for pattern in delivery_patterns:
            match = re.search(pattern, context_lower)
            if match:
                try:
                    cost = int(match.group(1))
                    if 500 <= cost <= 10000:  # Validation réaliste
                        delivery_info["delivery_cost"] = cost
                        break
                except:
                    continue
        
        # Extraction délai de livraison
        if "jour même" in context_lower or "avant 11h" in context_lower:
            delivery_info["delivery_time"] = "Jour même"
        elif "lendemain" in context_lower:
            delivery_info["delivery_time"] = "Lendemain"
        elif "24h" in context_lower:
            delivery_info["delivery_time"] = "24h"
        elif "48h" in context_lower or "2 jours" in context_lower:
            delivery_info["delivery_time"] = "48h"
        
        return delivery_info
    
    def _calculate_dynamic_pricing(self, products: List[Dict], delivery_info: Dict, context: str) -> Dict[str, Any]:
        """Calcule dynamiquement les prix totaux"""
        subtotal = sum(product.get("total_price", 0) for product in products)
        delivery_cost = delivery_info.get("delivery_cost", 0)
        total = subtotal + delivery_cost
        
        return {
            "subtotal": subtotal,
            "delivery_cost": delivery_cost,
            "total": total,
            "products": products
        }
    
    async def process_query(self, query: str, company_id: str, user_id: str, company_name: str = None, skip_faq_cache: bool = False, request_id: str = None, images: List[str] = None) -> UniversalRAGResult:
        """
        🌍 TRAITEMENT UNIVERSEL AVANCÉ D'UNE REQUÊTE
        
        Pipeline complet :
        1. 🇫🇷 Analyse NLP française (intentions, entités, normalisation)
        2. 🔍 Recherche hybride intelligente
        3. 🔀 Fusion multi-sources
        4. 🎯 Prompt enrichi
        5. 🤖 Génération LLM
        6. ✅ Vérification QA
        """
        # Stocker request_id pour le tracker
        self._request_id = request_id or 'unknown'
        # --- FAQ CACHE (avant tout traitement lourd) ---
        # ✅ FAQ CACHE RÉACTIVÉ POUR OPTIMISATION PERFORMANCE
        if not skip_faq_cache:
            try:
                from core.faq_answer_cache import faq_answer_cache
                cache_key_context = company_id  # Pour éviter collisions multi-entreprise
                cached = faq_answer_cache.get(query, cache_key_context)
                if cached:
                    print("⚡ [FAQ CACHE] Réponse instantanée (cache hit)")
                    return UniversalRAGResult(
                        response=cached,
                        confidence=1.0,
                        documents_found=True,
                        processing_time_ms=1,
                        search_method="faq_cache",
                        context_used="FAQ_CACHE"
                    )
            except Exception as e:
                print(f"[FAQ CACHE] Erreur cache: {e}")

        """
        🌍 TRAITEMENT UNIVERSEL D'UNE REQUÊTE
        
        Principe : Simple, robuste, adaptatif
        """
        start_time = time.time()
        
        print(f"\n🌍 [DÉBUT] RAG Universel: '{query[:40]}...'")
        print(f"🏢 Company: {company_id[:12]}... | User: {user_id[:12]}...")
        
        try:
            # 1. Initialisation si nécessaire
            if not self.llm_client:
                print("🔧 Initialisation LLM client...")
                await self.initialize()
            
            # 2. 🚀 RECHERCHE PARALLÈLE TRIPLE SOURCE (Gemini Cache + Meili + Supabase)
            # Utilise CatalogCacheManager avec extraction regex instantanée
            search_results = await self.search_parallel_sources(query, company_id, user_id=user_id)
            
            # 3. Génération de réponse avec prompt dynamique
            company_display_name = company_name or f"l'entreprise {company_id[:8]}"
            response = await self.generate_response(query, search_results, company_id, company_display_name, user_id, images=images)

            # 4. Traitement des outils dans la réponse LLM
            # 🧠 SMART CONTEXT MANAGER - Passer company_id et documents sources
            try:
                from core.rag_tools_integration import process_llm_response
                processed_result = process_llm_response(response, user_id, company_id, enable_tools=True)

                response = processed_result['response']
                thinking = processed_result['thinking']

                print(f"🔧 [TOOLS] {processed_result['tools_executed']} outils exécutés")
                if processed_result['state_updated']:
                    print(f"💾 [TOOLS] État mis à jour")

            except Exception as e:
                print(f"⚠️ [TOOLS] Erreur exécution outils: {e}")
                # Continuer avec la réponse originale

            # --- Stockage dans le cache FAQ (après génération) ---
            # ✅ FAQ CACHE RÉACTIVÉ POUR OPTIMISATION PERFORMANCE
            if not skip_faq_cache:
                try:
                    from core.faq_answer_cache import faq_answer_cache
                    cache_key_context = company_id
                    response_str = str(response or "")
                    is_error_response = (
                        "[Erreur LLM]" in response_str
                        or "401 Unauthorized" in response_str
                        or "403 Forbidden" in response_str
                        or response_str.strip().startswith("[Erreur")
                    )
                    if not is_error_response:
                        faq_answer_cache.set(query, cache_key_context, response)
                        print("[FAQ CACHE] Réponse stockée dans le cache FAQ")
                    else:
                        print("[FAQ CACHE] Skip cache (réponse d'erreur)")
                except Exception as e:
                    print(f"[FAQ CACHE] Erreur stockage: {e}")
            # 4. Calcul de la confiance
            confidence = self.calculate_confidence(search_results, response)
            print(f"📊 Confiance calculée: {confidence:.2f}")
            
            # 5. Construction du résultat
            processing_time = (time.time() - start_time) * 1000
            
            # ✅ CRITIQUE: Utiliser self._last_thinking qui est sauvegardé ligne 1118
            # La variable locale 'thinking' peut être écrasée par des appels ultérieurs
            thinking_text = getattr(self, '_last_thinking', thinking)
            print(f"🔍 [THINKING_FINAL] Thinking à retourner: {len(thinking_text)} chars")
            print(f"🔍 [THINKING_FINAL] Contenu: {thinking_text[:200] if thinking_text else 'VIDE'}")
            print(f"🔍 [THINKING_FINAL] Source: {'self._last_thinking' if hasattr(self, '_last_thinking') else 'variable locale'}")
            
            # Récupérer les métriques de tokens depuis generate_response
            token_usage = getattr(self, '_last_token_usage', {})
            prompt_tokens = getattr(self, '_last_prompt_tokens', 0)
            completion_tokens = getattr(self, '_last_completion_tokens', 0)
            total_tokens = getattr(self, '_last_total_tokens', 0)
            total_cost = getattr(self, '_last_total_cost', 0.0)
            model_used = getattr(self, '_last_model_used', 'unknown')
            
            result = UniversalRAGResult(
                response=response,
                confidence=confidence,
                documents_found=search_results['total_documents'] > 0,
                processing_time_ms=processing_time,
                search_method=search_results['search_method'],
                context_used=search_results['supabase_context'] or search_results['meili_context'] or "Aucun",
                thinking=thinking_text,
                validation=None,  # Sera ajouté par botlive si nécessaire
                usage=token_usage if isinstance(token_usage, dict) else None,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=total_cost,
                model=str(model_used or ""),
            )
            print(f"✅ [FIN] RAG terminé: {processing_time:.0f}ms | Méthode: {search_results['search_method']}")
            
            # 🧠 AUTO-LEARNING: Track exécution en background
            try:
                from core.auto_learning_wrapper import track_rag_execution
                
                # Extraire thinking_data depuis réponse
                thinking_data = {}
                try:
                    thinking_src = thinking_text or ""
                    if thinking_src:
                        intent_m = re.search(r"<intent>(.*?)</intent>", thinking_src, re.DOTALL | re.IGNORECASE)
                        checklist_m = re.search(r"<checklist>(.*?)</checklist>", thinking_src, re.DOTALL | re.IGNORECASE)
                        next_m = re.search(r"<next>(.*?)</next>", thinking_src, re.DOTALL | re.IGNORECASE)
                        action_m = re.search(r"<action>(.*?)</action>", thinking_src, re.DOTALL | re.IGNORECASE)
                        thinking_data = {
                            "intent": (intent_m.group(1).strip() if intent_m else ""),
                            "checklist": (checklist_m.group(1).strip() if checklist_m else ""),
                            "next": (next_m.group(1).strip() if next_m else ""),
                            "action": (action_m.group(1).strip() if action_m else ""),
                        }
                except Exception:
                    thinking_data = {}
                
                # Préparer documents utilisés
                documents_used = []
                if search_results.get('meili_context'):
                    # Extraire documents depuis contexte MeiliSearch
                    for doc in search_results.get('meili_results', []):
                        documents_used.append({
                            'id': doc.get('id', 'unknown'),
                            'content': doc.get('content', ''),
                            'source': 'meilisearch'
                        })
                if search_results.get('supabase_results'):
                    # Documents Supabase
                    for doc in search_results.get('supabase_results', []):
                        documents_used.append({
                            'id': doc.get('id', 'unknown'),
                            'content': doc.get('content', ''),
                            'source': 'supabase'
                        })
                
                # Track en background (non-bloquant)
                asyncio.create_task(track_rag_execution(
                    company_id=company_id,
                    user_id=user_id,
                    query=query,
                    thinking_data=thinking_data,
                    documents_used=documents_used,
                    response_time_ms=int(processing_time),
                    llm_model=getattr(self, "llm_model", "unknown"),
                    conversation_id=getattr(self, "_request_id", None)
                ))
                
            except Exception as learning_error:
                # Silent fail - ne pas bloquer RAG
                print(f"⚠️ [AUTO-LEARNING] Erreur tracking: {learning_error}")
            
            return result
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            print(f"❌ [ERREUR] RAG échec: {str(e)[:50]} | {processing_time:.0f}ms")
            
            # Fallback d'urgence
            return UniversalRAGResult(
                response="Je rencontre une difficulté technique. Pouvez-vous réessayer ?",
                confidence=0.1,
                documents_found=False,
                processing_time_ms=processing_time,
                search_method="fallback",
                context_used="Aucun"
            )
    
    def calculate_confidence(self, search_results: Dict[str, Any], response: str) -> float:
        """Calcule la confiance de manière simple"""
        base_confidence = 0.5
        
        # Bonus si documents trouvés
        if search_results['total_documents'] > 0:
            base_confidence += 0.3
        
        # Bonus si plusieurs sources
        if len(search_results['search_methods_used']) > 1:
            base_confidence += 0.1
        
        # Bonus si réponse substantielle
        if len(response) > 100:
            base_confidence += 0.1
        
        return min(base_confidence, 1.0)
    
    def _format_meili_context(self, meili_results: str, query_combinations: List[List[str]]) -> str:
        """Formate le contexte MeiliSearch avec titres fixes par index"""
        if not meili_results:
            return ""
        
        print("🎨 [ASSEMBLAGE] Formatage contexte MeiliSearch...")
        
        # Simulation du formatage par index (à adapter selon la vraie structure)
        formatted_context = "╔═══════════════════════════════════════════════════════════════════════╗\n"
        formatted_context += "║  📦 INFORMATIONS TROUVÉES DANS MEILISEARCH                           ║\n"
        formatted_context += "║  Recherche par mots-clés optimisée                                   ║\n"
        formatted_context += "╚═══════════════════════════════════════════════════════════════════════╝\n\n"
        
        # 🔥 ÉTAPE 1: Calculer les scores pour TOUS les documents
        documents = meili_results.split('\n\n')
        doc_scores = []
        
        for doc in documents:
            if doc.strip():
                score = self._calculate_keyword_score(doc, query_combinations)
                keywords = self._extract_found_keywords(doc, query_combinations)
                doc_scores.append({
                    'content': doc,
                    'score': score,
                    'keywords': keywords
                })
        
        # 🔥 ÉTAPE 2: TRIER par score DÉCROISSANT (meilleurs d'abord)
        doc_scores.sort(key=lambda x: x['score'], reverse=True)
        
        # 🔥 ÉTAPE 3: FILTRER - Garder seulement les documents avec score >= 4/10
        filtered_docs = [d for d in doc_scores if d['score'] >= 4]
        
        # Si pas assez de docs avec score élevé, prendre au moins les 3 meilleurs
        if len(filtered_docs) < 3:
            filtered_docs = doc_scores[:3]
        
        # Limiter à 5 docs maximum
        filtered_docs = filtered_docs[:5]
        
        print(f"📊 [FILTRAGE] {len(documents)} docs → {len(filtered_docs)} retenus (score >= 4/10)")
        
        # 🔥 ÉTAPE 4: Afficher dans l'ordre de pertinence
        docs_processed = 0
        for i, doc_info in enumerate(filtered_docs, 1):
            score = doc_info['score']
            stars = self._get_star_rating(score)
            keywords = doc_info['keywords']
            content = doc_info['content']
            
            formatted_context += f"{stars} INFORMATION MEILISEARCH #{i} (Score: {score}/10)\n"
            formatted_context += f"📊 Mots-clés trouvés: {keywords}\n"
            formatted_context += f"📝 Contenu: {content[:200]}...\n\n"
            docs_processed += 1
        
        print(f"✅ Assemblage MeiliSearch: {docs_processed} docs formatés (triés par pertinence)")
        return formatted_context
    
    def _format_supabase_context(self, supabase_docs: List[Dict]) -> str:
        """Formate le contexte Supabase avec titres fixes"""
        if not supabase_docs:
            return ""
        
        print("🎨 [ASSEMBLAGE] Formatage contexte Supabase...")
        
        formatted_context = "╔═══════════════════════════════════════════════════════════════════════╗\n"
        formatted_context += "║  📊 INFORMATIONS TROUVÉES DANS SUPABASE (SÉMANTIQUE)                ║\n"
        formatted_context += "║  Recherche par similarité vectorielle                               ║\n"
        formatted_context += "╚═══════════════════════════════════════════════════════════════════════╝\n\n"
        
        for i, doc in enumerate(supabase_docs, 1):
            content = doc.get('content', '')  # Document COMPLET sans troncature
            score = doc.get('similarity_score', 0)
            stars = self._get_star_rating(int(score * 10))
            
            formatted_context += f"{stars} DOCUMENT SÉMANTIQUE #{i} (Score: {score:.3f})\n"
            formatted_context += f"📊 Similarité cosinus: {score*100:.1f}%\n"
            formatted_context += f"📝 Contenu: {content}\n\n"
        
        print(f"✅ Assemblage Supabase: {len(supabase_docs)} docs formatés")
        return formatted_context
    
    def _calculate_keyword_score(self, document: str, query_combinations: List[List[str]]) -> int:
        """
        Calcule le score de pertinence basé sur les mots-clés trouvés ET la puissance des n-grams
        
        Logique de scoring améliorée :
        - N-gram de 3 mots trouvé : +5 points (très pertinent)
        - N-gram de 2 mots trouvé : +3 points (pertinent)
        - Mot seul trouvé : +1 point (peu pertinent)
        
        Maximum : 10 points
        """
        doc_lower = document.lower()
        score = 0
        max_score = 10
        
        # Détecter les n-grams dans l'ordre décroissant (plus long = plus pertinent)
        for combo in query_combinations:
            combo_text = " ".join(combo).lower()
            
            # N-gram de 3+ mots (très pertinent)
            if len(combo) >= 3 and combo_text in doc_lower:
                score += 5
                continue  # Ne pas compter les mots individuels
            
            # N-gram de 2 mots (pertinent)
            if len(combo) == 2 and combo_text in doc_lower:
                score += 3
                continue
            
            # Mots individuels (peu pertinent mais utile)
            if len(combo) == 1:
                for word in combo:
                    if word.lower() in doc_lower:
                        score += 1
        
        # Normaliser le score sur 10
        return max(1, min(max_score, score))
    
    def _extract_found_keywords(self, document: str, query_combinations: List[List[str]]) -> str:
        """
        Extrait les mots-clés trouvés dans le document
        Priorise l'affichage des n-grams trouvés (plus pertinent)
        """
        doc_lower = document.lower()
        found_ngrams = []
        found_words = []
        
        # D'abord chercher les n-grams (plus pertinents)
        for combo in query_combinations:
            combo_text = " ".join(combo)
            
            # N-gram de 2+ mots
            if len(combo) >= 2 and combo_text.lower() in doc_lower:
                found_ngrams.append(f'"{combo_text}"')  # Guillemets pour indiquer un n-gram
            # Mots individuels
            elif len(combo) == 1:
                for word in combo:
                    if word.lower() in doc_lower and word not in found_words:
                        found_words.append(word)
        
        # Afficher d'abord les n-grams, puis les mots seuls
        all_found = found_ngrams + found_words
        
        if all_found:
            result = ", ".join(all_found[:6])
            if found_ngrams:
                result += f" (n-gram: {len(found_ngrams)})"
            return result
        
        return "aucun spécifique"
    
    def _get_star_rating(self, score: int) -> str:
        """Convertit un score en notation étoiles"""
        if score >= 8:
            return "🌟🌟🌟🌟🌟"
        elif score >= 6:
            return "🌟🌟🌟🌟⭐"
        elif score >= 4:
            return "🌟🌟🌟⭐⭐"
        elif score >= 2:
            return "🌟🌟⭐⭐⭐"
        else:
            return "🌟⭐⭐⭐⭐"

# Instance globale (lazy init)
universal_rag = None

def get_universal_rag_engine():
    """Lazy initialization of the global RAG engine"""
    global universal_rag
    if universal_rag is None:
        universal_rag = UniversalRAGEngine()
    return universal_rag

# Fonction d'interface simple
async def get_universal_rag_response(
    message: str, 
    company_id: str, 
    user_id: str, 
    images: List[str] = None,
    conversation_history: str = "",
    skip_faq_cache: bool = False,
    request_id: str = None,
    company_name: str = None
) -> Dict[str, Any]:
    """
    🌍 INTERFACE SIMPLE POUR RAG UNIVERSEL
    
    Usage:
    result = await get_universal_rag_response("Que vendez-vous?", "company123", "user456", [], "USER: Bonjour...")
    print(result['response'])
    """
    
    # 🔍 LOGS MÉMOIRE CONVERSATIONNELLE - POINT D'ENTRÉE RAG
    print(f"🔍 [RAG_ENTRY] RÉCEPTION REQUÊTE:")
    print(f"🔍 [RAG_ENTRY] Message: '{message}'")
    print(f"🔍 [RAG_ENTRY] Company: {company_id}")
    print(f"🔍 [RAG_ENTRY] User: {user_id}")
    print(f"🔍 [RAG_ENTRY] Images: {len(images) if images else 0}")
    print(f"🔍 [RAG_ENTRY] conversation_history: '{conversation_history}'")
    print(f"🔍 [RAG_ENTRY] Taille historique: {len(conversation_history)} chars")
    print(f"🔍 [RAG_ENTRY] Contient Cocody: {'Cocody' in conversation_history}")
    print()
    
    engine = get_universal_rag_engine()
    result = await engine.process_query(message, company_id, user_id, company_name, skip_faq_cache, request_id, images=images)
    
    return {
        'response': result.response,
        'confidence': result.confidence,
        'documents_found': result.documents_found,
        'processing_time_ms': result.processing_time_ms,
        'search_method': result.search_method,
        'context_used': result.context_used,
        'thinking': getattr(result, 'thinking', ''),  # ← AJOUT thinking
        'validation': getattr(result, 'validation', None),  # ← AJOUT validation
        'usage': getattr(result, 'usage', None),
        'prompt_tokens': int(getattr(result, 'prompt_tokens', 0) or 0),
        'completion_tokens': int(getattr(result, 'completion_tokens', 0) or 0),
        'total_tokens': int(getattr(result, 'total_tokens', 0) or 0),
        'cost': float(getattr(result, 'cost', 0.0) or 0.0),
        'model': getattr(result, 'model', ''),
        'success': True
    }

if __name__ == "__main__":
    import sys
    
    # Test dynamique avec paramètres de ligne de commande
    async def test():
        # Paramètres dynamiques
        company_id = sys.argv[1] if len(sys.argv) > 1 else "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
        user_id = sys.argv[2] if len(sys.argv) > 2 else "testuser129"
        company_name = sys.argv[3] if len(sys.argv) > 3 else "Rue du Gros"
        message = sys.argv[4] if len(sys.argv) > 4 else "Que vendez-vous?"
        
        print(f"🧪 Test RAG Engine avec:")
        print(f"🏢 Company: {company_id}")
        print(f"👤 User: {user_id}")
        print(f"🏪 Name: {company_name}")
        print(f"💬 Message: {message}")
        print("-" * 50)
        
        if system_prompt:
            result = await run_llm_with_tools(message, company_id, user_id, system_prompt, conversation_history)
        else:
            result = await universal_rag.process_query(message, company_id, user_id, company_name)
        
        print(f"🤖 Réponse: {result['response']}")
        print(f"📊 Confiance: {result['confidence']:.2f}")
        print(f"🔍 Méthode: {result['search_method']}")
    
    asyncio.run(test())
    
    def _generate_progression_directive(self, notepad_context: str, user_id: str, company_id: str) -> str:
        """
        Génère une directive dynamique de progression basée sur l'état actuel
        
        Args:
            notepad_context: Contexte du notepad
            user_id: ID utilisateur
            company_id: ID entreprise
        
        Returns:
            str: Directive formatée pour le LLM
        """
        try:
            # Analyser le contexte notepad pour déterminer ce qui est collecté
            has_product = False
            has_delivery = False
            has_phone = False
            has_payment = False
            
            if notepad_context:
                has_product = "Produits commandés:" in notepad_context or "produit" in notepad_context.lower()
                has_delivery = "Zone de livraison:" in notepad_context or "livraison" in notepad_context.lower()
                has_phone = "Téléphone:" in notepad_context or "téléphone" in notepad_context.lower()
                has_payment = "Méthode de paiement:" in notepad_context or "paiement" in notepad_context.lower()
            
            # Calculer le taux de complétion
            collected_count = sum([has_product, has_delivery, has_phone, has_payment])
            total_required = 4
            completion_rate = (collected_count / total_required) * 100
            
            # Construire la directive
            directive = "🎯 DIRECTIVE PROGRESSION COMMANDE (RECALCULÉE EN TEMPS RÉEL):\n"
            directive += f"📊 Taux de complétion: {completion_rate:.0f}% ({collected_count}/{total_required} infos collectées)\n\n"
            
            # Statut de chaque champ
            if has_product:
                directive += "✅ PRODUIT collecté\n"
            else:
                directive += "❌ PRODUIT manquant → PRIORITÉ ABSOLUE: Identifier le produit (lot 150 ou 300)\n"
            
            if has_delivery:
                directive += "✅ LIVRAISON collectée\n"
            else:
                directive += "❌ LIVRAISON manquante → PROCHAINE ÉTAPE: Demander la zone/commune\n"
            
            if has_phone:
                directive += "✅ TÉLÉPHONE collecté\n"
            else:
                directive += "❌ TÉLÉPHONE manquant → PROCHAINE ÉTAPE: Demander le numéro de contact\n"
            
            if has_payment:
                directive += "✅ PAIEMENT collecté\n"
            else:
                directive += "❌ PAIEMENT manquant → PROCHAINE ÉTAPE: Proposer Wave + acompte 2000 FCFA\n"
            
            # Directive finale selon l'état
            directive += "\n"
            if collected_count == 0:
                directive += "🎯 ACTION IMMÉDIATE: Commencer par identifier le PRODUIT souhaité\n"
            elif collected_count < total_required:
                # Identifier la prochaine info manquante prioritaire
                if not has_product:
                    next_step = "PRODUIT"
                elif not has_delivery:
                    next_step = "ZONE DE LIVRAISON"
                elif not has_phone:
                    next_step = "TÉLÉPHONE"
                else:
                    next_step = "PAIEMENT"
                
                directive += f"🎯 PROCHAINE INFO À COLLECTER: {next_step}\n"
                directive += "⚠️ IMPORTANT: Adapter la question selon le contexte de l'échange actuel\n"
            else:
                directive += "🎉 TOUTES LES INFOS COLLECTÉES!\n"
                directive += "🎯 ACTION FINALE: Fournir un RÉCAPITULATIF complet et demander CONFIRMATION\n"
            
            return directive
            
        except Exception as e:
            logger.error(f"❌ Erreur génération directive: {e}")
            return ""
