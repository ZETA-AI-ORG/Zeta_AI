"""
🚀 RAG ENGINE SIMPLIFIÉ - VERSION COMPLÈTEMENT FONCTIONNELLE
Architecture épurée, performante et maintenable SANS dépendances manquantes
"""
import asyncio
import logging
import traceback
from typing import Dict, List, Optional, Any
from core.preprocessing import post_hyde_filter
from core.smart_stopwords import filter_query_for_meilisearch
from core.cache_manager import cache_manager
from core.quick_context_lookup import QuickContextLookup
from core.context_sources import ContextSources
from core.dynamic_offtopic_detector import DynamicOffTopicDetector
from core.intelligent_hallucination_guard import IntelligentHallucinationGuard
from core.intention_router import intention_router
from core.llm_client import GroqLLMClient
from core.business_config_manager import BusinessConfigManager
from core.prompt_manager import PromptManager
from database.supabase_client import get_supabase_client
from database.vector_store import search_meili_keywords  # Utilise la version optimisée MeiliSearch
from core.price_calculator import calculate_order_price, extract_delivery_zone_from_conversation
from core.recap_template import generate_order_summary, extract_customer_info_from_conversation
from core.progressive_memory_system import process_conversation_message, get_memory_system
from utils import log3
from datetime import datetime
import os
import json
import uuid
import hashlib
import time
import logging
from core.query_combinator import generate_query_combinations
# from core.meilisearch_orchestrator import   # Désactivé, non critique pour la recherche principale
from core.dynamic_catalog_loader import _extract_delivery_cost, _extract_delivery_time, _extract_zones_from_text
from core.adaptive_meili_optimizer import get_meili_optimizer
from core.hyde_search_optimizer import HydeSearchOptimizer

logger = logging.getLogger(__name__)
# from .dual_search_engine import DualSearchEngine  # Module non utilisé
from .conversation_memory import conversation_memory, update_conversation_context
from .smart_context_fusion import fuse_all_contexts, enhance_context_with_suggestions
from .conversation import save_message, get_history
from .dynamic_offtopic_detector import analyze_offtopic_query
from core.supabase_vector_search import SupabaseVectorSearch
from database.vector_store import search_meili_keywords  # Utilise la version optimisée MeiliSearch
from core.adaptive_meili_optimizer import get_meili_optimizer
from core.hyde_search_optimizer import HydeSearchOptimizer

# 🚀 NOUVEAUX SYSTÈMES ANTI-HALLUCINATION 2024
from .advanced_intent_classifier import classify_intent_advanced, IntentType
from .context_aware_hallucination_guard import validate_response_contextual, ValidationLevel
from .intelligent_fallback_system import generate_intelligent_fallback, FallbackType
from .confidence_scoring_system import calculate_confidence_score, ConfidenceLevel

# 📊 SYSTÈME DE LOGGING DÉTAILLÉ
from .detailed_logging_system import (
    start_detailed_logging, log_intent_classification, log_document_search,
    log_llm_generation, log_validation, log_confidence_scoring, log_fallback,
    log_response_sent, log_error, get_structured_logs, save_logs_to_file
)

# === MODE DEBUG ANTI-HALLUCINATION ===
DEBUG_HALLUCINATION = True  # Activé par défaut pour traquer les hallucinations

def debug_log_hallucination(label: str, content: str, force_full: bool = True):
    """Log spécialisé pour traquer les hallucinations - affiche le contenu complet"""
    if DEBUG_HALLUCINATION:
        display_content = content
        print(f"\n🔍 [ANTI-HALLUCINATION DEBUG] {label}")
        print("=" * 80)
        print(display_content)
        print("=" * 80 + "\n")

class SimplifiedRAGEngine:
    """
    🎯 MOTEUR RAG SIMPLIFIÉ
    - Architecture claire et modulaire
    - Dual search: Supabase (sémantique) + Meilisearch (full-text)
    - Performance optimisée avec async parallèle
    - Logs structurés et debugging facile
    """

    def __init__(self):
        self.llm_client = GroqLLMClient()
        self.config_manager = BusinessConfigManager()
        self.supabase_client = get_supabase_client()
        self.prompt_manager = PromptManager(self.supabase_client)
        self.hallucination_guard = IntelligentHallucinationGuard()

    async def dual_search(self, query: str, company_id: str) -> tuple[List[Dict], str, str]:
        """
        🔍 RECHERCHE DUALE OPTIMISÉE AVEC ROUTAGE D'INTENTIONS
        Supabase sémantique + Meilisearch ciblé par intention + Détection hors-sujet
        """
        log3("[DUAL_SEARCH]", f"🚀 Début recherche: '{query}'")
        
        # 0. Détection hors-sujet avec fallback intelligent
        try:
            offtopic_analysis = await analyze_offtopic_query(query, company_id, context_available=False)
            # Gérer le cas où offtopic_analysis est un objet QueryAnalysis
            if hasattr(offtopic_analysis, 'is_offtopic'):
                is_offtopic = offtopic_analysis.is_offtopic
            elif isinstance(offtopic_analysis, dict):
                is_offtopic = offtopic_analysis.get("is_offtopic", False)
            else:
                is_offtopic = False
        except Exception as e:
            log3("[DUAL_SEARCH]", f"⚠️ Erreur détection hors-sujet: {e}")
            is_offtopic = False
        
        if is_offtopic:
            log3("[DUAL_SEARCH]", "🚫 Requête hors-sujet détectée")
            return [], "", ""
        
        # 1. Génération d'hypothèse HYDE avancée
        try:
            # Détection d'intention pour HYDE
            if any(word in query.lower() for word in ['vendez', 'produits', 'services', 'catalogue', 'offre']):
                intent_type = "product_inquiry"
            elif any(word in query.lower() for word in ['prix', 'coût', 'tarif', 'combien']):
                intent_type = "product_inquiry"
            elif any(word in query.lower() for word in ['livraison', 'délai', 'transport', 'expédition']):
                intent_type = "delivery_info"
            elif any(word in query.lower() for word in ['contact', 'téléphone', 'email', 'aide', 'support']):
                intent_type = "support_contact"
            elif any(word in query.lower() for word in ['entreprise', 'société', 'qui', 'à propos']):
                intent_type = "company_info"
            else:
                intent_type = "general"
            
            # Génération d'hypothèse selon l'intention
            if intent_type == "product_inquiry":
                optimized_query = f"""Voici un catalogue détaillé de nos produits et services :

PRODUITS PRINCIPAUX :
- Produit A : Description détaillée, caractéristiques, avantages
- Produit B : Spécifications techniques, cas d'usage  
- Produit C : Gamme complète, options personnalisées

SERVICES ASSOCIÉS :
- Service de conseil et d'accompagnement
- Support technique et maintenance
- Formation et documentation

NOTRE EXPERTISE :
- X années d'expérience dans le domaine
- Certifications et qualifications
- Références clients et témoignages

Pour plus d'informations sur nos produits, contactez-nous ou consultez notre catalogue détaillé."""
            elif intent_type == "pricing_info":
                optimized_query = f"""Voici nos tarifs et conditions commerciales :

TARIFS DE BASE :
- Produit A : Prix de base, options et variantes
- Produit B : Tarifs dégressifs selon quantité
- Service C : Forfaits et tarifs horaires

CONDITIONS SPÉCIALES :
- Remises pour commandes importantes
- Tarifs préférentiels pour partenaires
- Offres promotionnelles saisonnières

MODALITÉS DE PAIEMENT :
- Paiement comptant : Remise de X%
- Paiement différé : Conditions et délais
- Financement : Solutions de paiement échelonné

Pour un devis personnalisé, contactez notre service commercial."""
            elif intent_type == "delivery_info":
                optimized_query = f"""Nos options de livraison et délais :

LIVRAISON STANDARD :
- Délai : X jours ouvrés
- Zone de livraison : France métropolitaine
- Suivi de commande en temps réel

LIVRAISON EXPRESS :
- Délai : 24-48h
- Zones prioritaires
- Frais supplémentaires

LIVRAISON INTERNATIONALE :
- Délais selon destination
- Formalités douanières
- Assurance transport

INSTALLATION ET MISE EN SERVICE :
- Service d'installation professionnel
- Formation utilisateur
- Garantie et SAV

Consultez nos conditions générales pour plus de détails."""
            else:
                optimized_query = f"""Document hypothétique pour: {query}

Ce document contient des informations détaillées sur le sujet demandé, incluant :
- Contexte et explications
- Détails techniques et pratiques
- Exemples et cas d'usage
- Ressources et références

Pour toute question complémentaire, n'hésitez pas à nous contacter."""
            
            hyde_metadata = {
                "original_query": query,
                "hypothesis": optimized_query,
                "intent_type": intent_type,
                "confidence": 0.8,
                "generation_method": "advanced_template"
            }
            
            log3("[HYDE_ADVANCED]", {
                "original_query": query,
                "intent_type": intent_type,
                "hypothesis_length": len(optimized_query),
                "hypothesis_preview": optimized_query,
                "confidence": 0.8
            })
        except Exception as e:
            log3("[HYDE_ADVANCED]", f"⚠️ Erreur HYDE avancé: {e}")
            optimized_query = query
            hyde_metadata = {}
        
        # Utiliser la requête optimisée pour les deux recherches
        hyde_hypothesis = optimized_query
        
        # 2. Recherche Supabase avec HyDE spécialisé
        supabase_start = time.time()
        
        async def supabase_search_async():
            try:
                log3("[DEBUG_SUPABASE]", "🔍 Début supabase_search_async")
                # Utilisation de la méthode qui fonctionne (comme dans le test)
                supabase_engine = SupabaseVectorSearch()
                await supabase_engine.initialize()
                
                # Génération embedding avec la même méthode que le test
                embedding = await supabase_engine.generate_embedding(hyde_hypothesis)
                
                results = await supabase_engine.search_vectors(
                    query_embedding=embedding,
                    company_id=company_id,
                    top_k=5,
                    min_score=0.3
                )
                
                # Formatage des résultats pour compatibilité
                formatted_results = []
                context_parts = []
                
                for result in results:
                    formatted_results.append({
                        "content": result.content,
                        "score": result.score,
                        "title": result.metadata.get("title", "Document"),
                        "chunk_id": result.id,
                        "metadata": result.metadata
                    })
                    context_parts.append(result.content)
                
                context = "\n\n".join(context_parts)
                return formatted_results, context
            except Exception as e:
                log3("[SUPABASE_ERROR]", f"Erreur recherche Supabase: {e}")
                return [], ""
        
        supabase_task = asyncio.create_task(supabase_search_async())
        
        # 3. Optimisation MeiliSearch avec apprentissage adaptatif
        async def meili_search_async():
            try:
                # Utiliser la requête HyDE optimisée pour MeiliSearch aussi
                meili_query = hyde_hypothesis
                
                # Optimisation MeiliSearch adaptative
                try:
                    from core.adaptive_meili_optimizer import optimize_meili_query
                    optimized_meili_query, optimization_metadata = await optimize_meili_query(
                        meili_query, 
                        company_id, 
                        hyde_metadata
                    )
                    # Log supprimé pour clarifier diagnostic Supabase
                except Exception as e:
                    # Log supprimé pour clarifier diagnostic Supabase
                    optimized_meili_query = meili_query
                
                # FILTRAGE STOP WORDS: Appliquer le système de filtrage avant MeiliSearch
                filtered_query = filter_query_for_meilisearch(optimized_meili_query)
                logger.info(f"[STOP_WORDS_FILTER] 🔍 FILTRAGE STOP WORDS APPLIQUÉ (OPTIMIZER):")
                logger.info(f"[STOP_WORDS_FILTER] - Query originale: '{optimized_meili_query}'")
                logger.info(f"[STOP_WORDS_FILTER] - Query filtrée: '{filtered_query}'")
                logger.info(f"[STOP_WORDS_FILTER] - Réduction: {len(optimized_meili_query)} → {len(filtered_query)} caractères")
                
                # Recherche MeiliSearch
                return await search_meili_keywords(
                    query=filtered_query,  # Query filtrée avec stop words
                    company_id=company_id,
                    target_indexes=None
                )
            except Exception as e:
                # Log supprimé pour clarifier diagnostic Supabase
                return []
        
        meili_start = time.time()
        meili_task = asyncio.create_task(meili_search_async())
        
        # Attente des résultats en parallèle
        try:
            log3("[DEBUG_GATHER]", "🔍 AVANT asyncio.gather() - Tâches créées")
            (supabase_results, supabase_context), meili_results = await asyncio.gather(
                supabase_task,
                meili_task,
                return_exceptions=True
            )
            
            # Calcul des temps de performance
            supabase_time = (time.time() - supabase_start) * 1000
            meili_time = (time.time() - meili_start) * 1000
            
            log3("[PERFORMANCE_SEARCH]", {
                "supabase_time_ms": f"{supabase_time:.2f}",
                "meili_time_ms": f"{meili_time:.2f}",
                "total_search_time_ms": f"{max(supabase_time, meili_time):.2f}"
            })
            
            # Gestion des erreurs avec traceback détaillé
            if isinstance(supabase_results, Exception):
                log3("[ERROR_SUPABASE]", {
                    "error_type": type(supabase_results).__name__,
                    "error_message": str(supabase_results),
                    "traceback_preview": traceback.format_exc(),
                    "query_preview": optimized_query,
                    "company_id": company_id
                })
                supabase_results, supabase_context = [], ""
            
            if isinstance(meili_results, Exception):
                # Log supprimé pour clarifier diagnostic Supabase
                meili_results = []
            
            # Mise à jour des performances de l'optimiseur MeiliSearch
            if meili_results and not isinstance(meili_results, Exception):
                try:
                    optimizer = get_meili_optimizer(company_id)
                    await optimizer.update_pattern_performance(
                        query, 
                        len(meili_results), 
                        100  # Temps approximatif - sera amélioré avec monitoring
                    )
                except Exception as e:
                    # Log supprimé pour clarifier diagnostic Supabase
                    pass
        
            # LOGS DE TRANSFORMATION DE DONNÉES AVANT FUSION
            log3("[DATA_TRANSFORMATION]", {
                "supabase_raw_type": type(supabase_results).__name__,
                "supabase_raw_length": len(supabase_results) if hasattr(supabase_results, '__len__') else "N/A",
                "supabase_preview": str(supabase_results),
                "meili_raw_type": type(meili_results).__name__,
                "meili_raw_length": len(meili_results) if hasattr(meili_results, '__len__') else "N/A",
                "meili_preview": str(meili_results)
            })
            
            # LOGS DÉTAILLÉS COMPLETS - TOUS LES DOCUMENTS TROUVÉS
            # Sécurisation des types pour éviter 'str' object has no attribute 'get'
            transformation_start = time.time()
            
            safe_supabase_results = []
            if isinstance(supabase_results, list):
                for doc in supabase_results:
                    if isinstance(doc, dict):
                        safe_supabase_results.append(doc)
                    else:
                        safe_supabase_results.append({"content": str(doc), "score": "N/A", "title": "Raw Result"})
            
            safe_meili_results = []
            if not isinstance(meili_results, Exception) and meili_results:
                # CORRECTION: MeiliSearch retourne un dict avec 'results' key
                if isinstance(meili_results, dict) and 'results' in meili_results:
                    # Extraire les résultats du dict MeiliSearch
                    actual_results = meili_results['results']
                    # Log supprimé pour clarifier diagnostic Supabase
                    for doc in actual_results:
                        if isinstance(doc, dict):
                            safe_meili_results.append(doc)
                        else:
                            safe_meili_results.append({"content": str(doc), "score": "N/A", "title": "Raw Result"})
                elif isinstance(meili_results, list):
                    for doc in meili_results:
                        if isinstance(doc, dict):
                            safe_meili_results.append(doc)
                        else:
                            safe_meili_results.append({"content": str(doc), "score": "N/A", "title": "Raw Result"})
                elif isinstance(meili_results, str):
                    safe_meili_results.append({"content": meili_results, "score": "N/A", "title": "String Result"})
            
            transformation_time = (time.time() - transformation_start) * 1000
            log3("[PERFORMANCE_TRANSFORMATION]", f"Temps transformation données: {transformation_time:.2f}ms")
            
            # === 2. DOCUMENTS SUPABASE COMPLETS ===
            if safe_supabase_results:
                supabase_debug = f"TOTAL: {len(safe_supabase_results)} documents\n\n"
                for i, doc in enumerate(safe_supabase_results[:2]): # Limiter l'aperçu à 2 documents
                    supabase_debug += f"--- DOCUMENT {i+1} ---\n"
                    supabase_debug += f"Score: {doc.get('score', 'N/A')}\n"
                    supabase_debug += f"Titre: {doc.get('title', 'N/A')}\n"
                    supabase_debug += f"Contenu aperçu: {doc.get('content', '')}\n\n"
                debug_log_hallucination("DOCUMENTS SUPABASE TROUVÉS", supabase_debug)
            else:
                debug_log_hallucination("DOCUMENTS SUPABASE TROUVÉS", "Aucun document trouvé.")
            
            # === 3. DOCUMENTS MEILISEARCH COMPLETS ===
            if safe_meili_results:
                meili_debug = f"TOTAL: {len(safe_meili_results)} documents\n\n"
                for i, doc in enumerate(safe_meili_results[:2]): # Limiter l'aperçu à 2 documents
                    meili_debug += f"--- DOCUMENT {i+1} ---\n"
                    meili_debug += f"Score: {doc.get('score', 'N/A')}\n"
                    meili_debug += f"Titre: {doc.get('title', 'N/A')}\n"
                    meili_debug += f"Contenu aperçu: {doc.get('content', '')[:100]}...\n\n"
                debug_log_hallucination("DOCUMENTS MEILISEARCH TROUVÉS", meili_debug)
            else:
                debug_log_hallucination("DOCUMENTS MEILISEARCH TROUVÉS", "Aucun document trouvé.")

            # Log détaillé des documents trouvés
            log3("[DOCUMENTS_TROUVES_SUPABASE]", {
                "nombre_documents": len(supabase_results),
                "documents": [
                    {
                        "index": i+1,
                        "score": doc.get("score", "N/A"),
                        "title": doc.get("title", "Sans titre"),
                        "content_preview": doc.get("content", ""),
                        "metadata": doc.get("metadata", {})
                    }
                    for i, doc in enumerate(supabase_results[:3])  # Limite à 3 pour lisibilité
                ]
            })
            
            log3("[DOCUMENTS_TROUVES_MEILI]", {
                "nombre_documents": len(safe_meili_results),
                "documents": [
                    {
                        "index": i+1,
                        "id": doc.get("id", "N/A"),
                        "type": doc.get("type", "N/A"),
                        "content_preview": doc.get("content", "")
                    }
                    for i, doc in enumerate(safe_meili_results[:3])
                ]
            })

            log3("[DUAL_SEARCH]", {
                "supabase_results": len(supabase_results),
                "meili_results": len(safe_meili_results),
                "context_length": len(supabase_context),
                "hyde_enhanced": True
            })
            
            # Fusion des contextes MeiliSearch + Supabase
            merged_context = self.merge_contexts(supabase_context, safe_meili_results)
            
            return supabase_results, safe_meili_results, merged_context
            
        except Exception as e:
            log3("[DUAL_SEARCH]", f"💥 Erreur générale: {str(e)}")
            return [], [], ""

    def merge_contexts(self, supabase_context: str, meili_results) -> str:
        """
        🔗 FUSION INTELLIGENTE DES CONTEXTES
        Combine les résultats Supabase et MeiliSearch de manière optimale
        """
        contexts = []
        
        if supabase_context and supabase_context.strip():
            contexts.append(f"=== CONTEXTE SÉMANTIQUE ===\n{supabase_context}")
        
        if meili_results and isinstance(meili_results, list):
            meili_formatted = []
            for i, doc in enumerate(meili_results, 1):
                if isinstance(doc, dict):
                    doc_text = f"=== PRODUIT {i} ===\n"
                    doc_text += f"ID: {doc.get('id', 'N/A')}\n"
                    doc_text += f"Type: {doc.get('type', 'N/A')}\n"
                    if doc.get('content'):
                        doc_text += f"Contenu: {doc.get('content', '')}\n"
                    if doc.get('metadata'):
                        doc_text += f"Métadonnées: {doc.get('metadata', {})}\n"
                    meili_formatted.append(doc_text)
            
            if meili_formatted:
                contexts.append(f"=== RECHERCHE TEXTUELLE ===\n" + "\n".join(meili_formatted))
        
        return "\n\n".join(contexts) if contexts else ""

    async def generate_response(self, query: str, context: str, company_id: str, conversation_history: str = "") -> str:
        """
        Génère une réponse en utilisant le LLM avec le contexte fourni et l'historique.
        """
        start_time = datetime.now()
        
        # Récupérer le prompt système personnalisé
        prompt_data = await self.prompt_manager.get_active_prompt(company_id)
        system_prompt = "Vous êtes un assistant IA spécialisé dans l'analyse de documents d'entreprise."
        
        if prompt_data:
            system_prompt = prompt_data.get('prompt_template', system_prompt)
            log3("[RAG SIMPLIFIED] Prompt personnalisé", f"Version: {prompt_data.get('version', 'N/A')}")
        
        # Construction du prompt complet avec historique
        history_section = ""
        if conversation_history and conversation_history.strip():
            history_section = f"\n\nHistorique de la conversation:\n{conversation_history[-1000:]}\n"  # Limiter à 1000 chars
        
        full_prompt = f"""{system_prompt}

Contexte:
{context}{history_section}

Question: {query}

Réponse:"""
        
        # Logger le prompt complet pour debugging
        await self.log_prompt_to_supabase(company_id, query, full_prompt, context, conversation_history)
        
        log3("[RAG SIMPLIFIED] Prompt construit", f"Taille: {len(full_prompt)} caractères")
        
        try:
            # Configuration du modèle LLM principal (70B avec fallback automatique)
            main_model = os.getenv("GROQ_LLM_MODEL", "llama-3.3-70b-versatile")
            
            response = await self.llm_client.complete(
                prompt=full_prompt,
                model_name=main_model,  # Utilise le LLM principal 70B
                temperature=0.2,
                max_tokens=500
            )
            
            generation_time = (datetime.now() - start_time).total_seconds()
            # === 5. RÉPONSE FINALE DU LLM ===
            debug_log_hallucination("RÉPONSE FINALE DU LLM", response)
            log3("[RAG SIMPLIFIED] Réponse générée", f"Temps: {generation_time:.2f}s | Taille: {len(response)} chars")
            
            return response
            
        except Exception as e:
            log3("[RAG SIMPLIFIED] Erreur génération", f"{type(e).__name__}: {str(e)}")
            return "Désolé, une erreur s'est produite lors de la génération de la réponse."

    async def log_prompt_to_supabase(self, company_id: str, user_query: str, full_prompt: str, context: str, history: str) -> None:
        """
        Enregistre le prompt complet dans Supabase pour debugging et analyse.
        """
        try:
            from config import SUPABASE_URL, SUPABASE_KEY
            import requests
            
            log_entry = {
                "id": str(uuid.uuid4()),
                "company_id": company_id,
                "user_query": user_query,
                "full_prompt": full_prompt,
                "context_used": context,
                "conversation_history": history,
                "timestamp": datetime.utcnow().isoformat(),
                "prompt_length": len(full_prompt),
                "context_length": len(context),
                "history_length": len(history)
            }
            
            url = f"{SUPABASE_URL}/rest/v1/prompt_logs"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json"
            }
            
            # Utiliser requests au lieu de httpx
            response = requests.post(url, json=log_entry, headers=headers, timeout=10)
            if response.status_code == 201:
                log3("[PROMPT LOG] Enregistré", f"ID: {log_entry['id'][:8]}...")
            else:
                log3("[PROMPT LOG] Erreur", f"HTTP {response.status_code}")
                    
        except Exception as e:
            log3("[PROMPT LOG] Exception", f"{type(e).__name__}: {str(e)}")

    def get_cache_key(self, message: str, company_id: str) -> str:
        """Génère une clé de cache unique"""
        key_data = f"{company_id}:{message}"
        return f"rag_simple:{hashlib.md5(key_data.encode()).hexdigest()}"

    async def process_message(self, message: str, company_id: str, user_id: str) -> str:
        """
        Traite un message utilisateur avec le RAG engine simplifié.
        Retourne la réponse générée par le LLM.
        """
        start_time = datetime.now()
        
        # Validation des entrées
        if not message or not message.strip():
            return "Je n'ai pas reçu de message. Pouvez-vous reformuler votre question ?"
        
        if not company_id:
            return "Erreur: company_id manquant."
        
        # === 1. QUESTION INITIALE ===
        debug_log_hallucination("QUESTION INITIALE", f"Utilisateur: {message}")
        
        # Sauvegarder le message utilisateur
        await save_message(company_id, user_id, "user", message)
        
        # Récupérer l'historique des conversations
        conversation_history = await get_history(company_id, user_id)
        log3("[RAG SIMPLIFIED] Historique", f"Chargé: {len(conversation_history)} caractères")
        
        # Désactiver le cache pour les tests
        cache_disabled = True
        if cache_disabled:
            log3("[RAG SIMPLIFIED] Cache désactivé", "Mode test actif")
        
        try:
            # 🎯 DÉTECTION D'INTENTIONS POUR ROUTAGE INTELLIGENT
            intentions = intention_router.detect_intentions(message)
            log3("[INTENTION_ROUTER]", {
                "primary_intention": intentions.primary,
                "all_intentions": list(intentions.intentions.keys()) if intentions.intentions else [],
                "confidence": intentions.confidence_score,
                "target_indexes": intention_router.get_target_indexes(company_id, intentions)
            })
            
            # 🚀 OPTIMISATION: Éviter la recherche si pas nécessaire
            skip_search = self.hallucination_guard.should_skip_search(message, company_id)
            
            if skip_search:
                log3("[RAG_OPTIMIZATION]", "🚀 Recherche évitée - Requête sociale/conversationnelle")
                supabase_results, supabase_context = [], ""
                meili_context = ""
            else:
                # 1. Génération d'hypothèse HYDE avancée
                try:
                    logger.info(f"[RAG_ADVANCED] 🧠 Génération d'hypothèse HYDE")
                    
                    # Détection d'intention pour HYDE
                    if any(word in message.lower() for word in ['vendez', 'produits', 'services', 'catalogue', 'offre']):
                        intent_type = "product_inquiry"
                    elif any(word in message.lower() for word in ['prix', 'coût', 'tarif', 'combien']):
                        intent_type = "pricing_info"
                    elif any(word in message.lower() for word in ['livraison', 'délai', 'transport', 'expédition']):
                        intent_type = "delivery_info"
                    elif any(word in message.lower() for word in ['contact', 'téléphone', 'email', 'aide', 'support']):
                        intent_type = "support_contact"
                    elif any(word in message.lower() for word in ['entreprise', 'société', 'qui', 'à propos']):
                        intent_type = "company_info"
                    else:
                        intent_type = "general"
                    
                    # Génération d'hypothèse selon l'intention
                    if intent_type == "product_inquiry":
                        hyde_hypothesis = f"""Informations sur nos produits et services :

PRODUITS ET SERVICES :
- Nous proposons une gamme de produits et services
- Catalogue de produits disponibles
- Services associés et accompagnement
- Offres commerciales et promotions

INFORMATIONS COMMERCIALES :
- Modes de paiement disponibles
- Conditions de vente et livraison
- Support client et assistance
- Contact commercial et informations

POUR PLUS D'INFORMATIONS :
- Consultez notre catalogue
- Contactez notre équipe commerciale
- Découvrez nos offres spéciales
- Informations sur nos produits"""
                    else:
                        hyde_hypothesis = f"""Document hypothétique pour: {message}

Ce document contient des informations détaillées sur le sujet demandé, incluant :
- Contexte et explications
- Détails techniques et pratiques
- Exemples et cas d'usage
- Ressources et références

Pour toute question complémentaire, n'hésitez pas à nous contacter."""
                    
                    logger.info(f"[RAG_ADVANCED] 🧠 Hypothèse HYDE générée: {intent_type} ({len(hyde_hypothesis)} caractères)")
                    
                    # Recherche Supabase avec la méthode qui fonctionne
                    supabase_engine = SupabaseVectorSearch()
                    await supabase_engine.initialize()
                    
                    # Génération embedding avec la même méthode que le test
                    embedding = await supabase_engine.generate_embedding(hyde_hypothesis)
                    
                    supabase_results = await supabase_engine.search_vectors(
                        query_embedding=embedding,
                        company_id=company_id,
                        top_k=5,
                        min_score=0.3
                    )
                    
                    # Extraire le contexte des résultats
                    context_parts = []
                    for result in supabase_results:
                        context_parts.append(result.content)
                    supabase_context = "\n\n".join(context_parts)
                    
                    logger.info(f"[RAG_ADVANCED] Contexte Supabase trouvé: {len(supabase_context)} caractères")
                except Exception as e:
                    logger.warning(f"[RAG_ADVANCED] Erreur HYDE/Supabase: {e}")
                    supabase_context = ""
                
                # 2. Recherche MeiliSearch avec routage intelligent par intentions
                # FILTRAGE STOP WORDS: Appliquer le système de filtrage avant MeiliSearch
                filtered_query = filter_query_for_meilisearch(message)
                logger.info(f"[STOP_WORDS_FILTER] 🔍 FILTRAGE STOP WORDS APPLIQUÉ (RAG_ADVANCED):")
                logger.info(f"[STOP_WORDS_FILTER] - Query originale: '{message}'")
                logger.info(f"[STOP_WORDS_FILTER] - Query filtrée: '{filtered_query}'")
                logger.info(f"[STOP_WORDS_FILTER] - Réduction: {len(message)} → {len(filtered_query)} caractères")
                
                meili_results_docs = await search_meili_keywords(filtered_query, company_id)
                print('DEBUG TYPE MEILI:', type(meili_results_docs), meili_results_docs)
                if not isinstance(meili_results_docs, list):
                    print('BUG: MeiliSearch returned non-list!', type(meili_results_docs), meili_results_docs)
                    meili_results_docs = []
                # Construction du meili_context à partir des documents sélectionnés
                meili_context_parts = []
                for i, doc in enumerate(meili_results_docs):
                    content = doc.get('searchable_text') or doc.get('content_fr') or doc.get('content')
                    matched_combo = doc.get('matched_query_combo', ["N/A"])
                    index_source = doc.get('index_source', "N/A")
                    doc_id = doc.get('id', f"doc_{i+1}")

                    formatted_doc_content = content # Contenu par défaut
                    content_type_label = "INFORMATIONS GÉNÉRALES"

                    # Déterminer le type de contenu et appliquer un formatage spécifique si nécessaire
                    if "products" in index_source.lower():
                        content_type_label = "INFORMATIONS PRODUITS"
                    elif "delivery" in index_source.lower():
                        content_type_label = "INFORMATIONS DE LIVRAISON"
                        if content:
                            extracted_cost = _extract_delivery_cost(content)
                            extracted_time = _extract_delivery_time(content)
                            extracted_zones = _extract_zones_from_text(content)
                            formatted_doc_content = (
                                f"Zones concernées: {', '.join(extracted_zones) if extracted_zones else 'N/A'}\n"
                                f"Coût de livraison: {extracted_cost} FCFA\n"
                                f"Délais de livraison: {extracted_time}\n\n"
                                f"{content}" # Inclure le contenu original aussi
                            )
                    elif "support_paiement" in index_source.lower():
                        content_type_label = "INFORMATIONS SUPPORT PAIEMENT"
                    elif "localisation" in index_source.lower():
                        content_type_label = "INFORMATIONS DE LOCALISATION"
                    elif "company_docs" in index_source.lower():
                        content_type_label = "INFORMATIONS D'ENTREPRISE"


                    if formatted_doc_content:
                        formatted_doc = (
                            f"=== DOCUMENT {i+1} (ID: {doc_id}) ===\n"
                            f"TYPE DE CONTENU : {content_type_label}\n"
                            f"COMBINAISON(S) DE RECHERCHE : {matched_combo}\n"
                            f"INDEX SOURCE : {index_source}\n\n"
                            f"CONTENU DU DOCUMENT :\n{formatted_doc_content}\n\n"
                            f"--- FIN DOCUMENT {i+1} ---"
                        )
                        meili_context_parts.append(formatted_doc)
                meili_context = "\n\n".join(meili_context_parts)
                
                # Logs supprimés pour clarifier diagnostic Supabase

                # Les meili_results sont maintenant une liste de documents complets, plus besoin de post-traitement complexe ici
                meili_results = meili_results_docs # Pour compatibilité avec les logs existants si nécessaire
            
            # Convertir en format résultats standardisé
            safe_meili_results = [{"content": meili_context, "type": "meilisearch"}] if meili_context else []
            
            # Le contexte Supabase est déjà fourni par la fonction
            
            log3("[RAG SIMPLIFIED] Résultats extraits", {
                "supabase_results": len(supabase_results) if supabase_results else 0,
                "meili_results_count": len(safe_meili_results),
                "supabase_context_length": len(supabase_context) if supabase_context else 0
            })
            
            # 3. 🧠 FUSION INTELLIGENTE AVEC MÉMOIRE CONVERSATIONNELLE
            log3("[FUSION_INTELLIGENTE]", "Début fusion contextes avec mémoire conversationnelle")
            
            # Fusionner tous les contextes intelligemment
            intelligent_context = fuse_all_contexts(
                supabase_results=supabase_results,
                meilisearch_results=safe_meili_results,
                user_message=message,
                user_id=user_id,
                company_id=company_id
            )
            
            # Enrichir avec suggestions intelligentes
            enhanced_context = enhance_context_with_suggestions(
                context=intelligent_context,
                user_message=message,
                user_id=user_id,
                company_id=company_id
            )
            
            # === 4. FUSION DES CONTEXTES ===
            debug_log_hallucination("CONTEXTE FUSIONNÉ POUR LE LLM", enhanced_context)
            
            # 4. Génération de la réponse avec historique
            response = await self.generate_response(message, enhanced_context, company_id, conversation_history)
            
            # 🛡️ VALIDATION ANTI-HALLUCINATION INTELLIGENTE
            hallucination_check = await self.hallucination_guard.evaluate_response(
                user_query=message,
                ai_response=response,
                company_id=company_id,
                supabase_results=supabase_results,
                meili_results=safe_meili_results,
                supabase_context=supabase_context,
                meili_context=meili_context
            )
            
            log3("[HALLUCINATION_GUARD]", {
                "is_safe": hallucination_check.is_safe,
                "confidence": hallucination_check.confidence_score,
                "intention": hallucination_check.intention_detected,
                "search_required": hallucination_check.search_required,
                "documents_found": hallucination_check.documents_found,
                "judge_decision": hallucination_check.judge_decision,
                "processing_time_ms": hallucination_check.processing_time_ms
            })
            
            # Si la réponse est rejetée, utiliser la réponse suggérée
            if not hallucination_check.is_safe and hallucination_check.suggested_response:
                log3("[HALLUCINATION_GUARD]", f"🚫 Réponse rejetée: {hallucination_check.reason}")
                response = hallucination_check.suggested_response
            
            # 🧠 Mettre à jour la mémoire conversationnelle
            update_conversation_context(
                user_message=message,
                assistant_response=response,
                user_id=user_id,
                company_id=company_id
            )
            
            # Sauvegarder la réponse dans l'historique
            await save_message(
                company_id=company_id,
                user_id=user_id,
                role="assistant",
                content=response
            )
            
            # Métriques finales
            total_time = (datetime.now() - start_time).total_seconds()
            log3("[RAG SIMPLIFIED] Traitement terminé", f"Temps total: {total_time:.2f}s")
            
            return response
            
        except Exception as e:
            log3("[RAG SIMPLIFIED] Erreur traitement", f"{type(e).__name__}: {str(e)}")
            return "Désolé, une erreur s'est produite. Veuillez réessayer."


# Instance globale
rag_engine = SimplifiedRAGEngine()

async def get_rag_response_advanced(
    message: str,
    user_id: str,
    company_id: str,
    conversation_id: str = None,
    use_hyde: bool = True,
    debug: bool = False
) -> Dict[str, Any]:
    """
    🚀 RAG ENGINE AVANCÉ 2024 - VERSION SANS ANTI-HALLUCINATION
    Système simplifié sans validation anti-hallucination pour un fonctionnement direct
    """
    start_time = time.time()
    
    # 📊 DÉMARRAGE DU LOGGING DÉTAILLÉ
    request_data = {
        "user_id": user_id,
        "company_id": company_id,
        "message": message,
        "conversation_id": conversation_id,
        "use_hyde": use_hyde,
        "debug": debug
    }
    request_id = start_detailed_logging(request_data)
    
    # Log de démarrage
    logger.info(f"[DETAILED_LOGGING] 🚀 Logging détaillé activé - Request ID: {request_id}")
    
    try:
        # 🚫 DÉSACTIVATION COMPLÈTE DU SYSTÈME ANTI-HALLUCINATION
        # Plus de classification d'intention, validation, ou scoring de confiance
        
        # 1. Recherche de documents (TOUJOURS activée)
        logger.info(f"[RAG_ADVANCED] 🔍 Étape 1: Recherche de documents")
        
        # Logging détaillé de la recherche
        log_document_search("SUPABASE_SEMANTIC", {"query": message, "company_id": company_id}, [], "")
        
        supabase_results = []
        meili_results = []
        supabase_context = ""
        meili_context = ""
        
        # PRIORITÉ 1: Recherche MeiliSearch multi-index (PRIORITÉ ABSOLUE)
        try:
            logger.info(f"[RAG_ADVANCED] 🔍 Recherche MeiliSearch multi-index (PRIORITÉ)")
            
            # 1. Filtrage des stop words (Module 1)
            filtered_query = filter_query_for_meilisearch(message)
            logger.info(f"[STOP_WORDS_FILTER] Query filtrée: \'{filtered_query}\'")

            # 2. Génération des combinaisons de mots (Module 2)
            query_combinations = generate_query_combinations(filtered_query)
            logger.info(f"[QUERY_COMBINATOR] Combinations générées: {query_combinations}")

            # 3. Orchestration de la recherche MeiliSearch (Module 3)
            meili_results_docs = await search_meili_keywords(filtered_query, company_id)
            print('DEBUG TYPE MEILI:', type(meili_results_docs), meili_results_docs)
            if not isinstance(meili_results_docs, list):
                print('BUG: MeiliSearch returned non-list!', type(meili_results_docs), meili_results_docs)
                meili_results_docs = []
            # Construction du meili_context à partir des documents sélectionnés
            meili_context_parts = []
            for i, doc in enumerate(meili_results_docs):
                content = doc.get('searchable_text') or doc.get('content_fr') or doc.get('content')
                matched_combo = doc.get('matched_query_combo', ["N/A"])
                index_source = doc.get('index_source', "N/A")
                doc_id = doc.get('id', f"doc_{i+1}")

                formatted_doc_content = content # Contenu par défaut
                content_type_label = "INFORMATIONS GÉNÉRALES"

                # Déterminer le type de contenu et appliquer un formatage spécifique si nécessaire
                if "products" in index_source.lower():
                    content_type_label = "INFORMATIONS PRODUITS"
                elif "delivery" in index_source.lower():
                    content_type_label = "INFORMATIONS DE LIVRAISON"
                    if content:
                        extracted_cost = _extract_delivery_cost(content)
                        extracted_time = _extract_delivery_time(content)
                        extracted_zones = _extract_zones_from_text(content)
                        formatted_doc_content = (
                            f"Zones concernées: {', '.join(extracted_zones) if extracted_zones else 'N/A'}\n"
                            f"Coût de livraison: {extracted_cost} FCFA\n"
                            f"Délais de livraison: {extracted_time}\n\n"
                            f"{content}" # Inclure le contenu original aussi
                        )
                elif "support_paiement" in index_source.lower():
                    content_type_label = "INFORMATIONS SUPPORT PAIEMENT"
                elif "localisation" in index_source.lower():
                    content_type_label = "INFORMATIONS DE LOCALISATION"
                elif "company_docs" in index_source.lower():
                    content_type_label = "INFORMATIONS D'ENTREPRISE"


                if formatted_doc_content:
                    formatted_doc = (
                        f"=== DOCUMENT {i+1} (ID: {doc_id}) ===\n"
                        f"TYPE DE CONTENU : {content_type_label}\n"
                        f"COMBINAISON(S) DE RECHERCHE : {matched_combo}\n"
                        f"INDEX SOURCE : {index_source}\n\n"
                        f"CONTENU DU DOCUMENT :\n{formatted_doc_content}\n\n"
                        f"--- FIN DOCUMENT {i+1} ---"
                    )
                    meili_context_parts.append(formatted_doc)
            meili_context = "\n\n".join(meili_context_parts)
            
            logger.info(f"[MEILISEARCH_CONTEXT] Contexte MeiliSearch final: {len(meili_context)} caractères")
            logger.info(f"[MEILISEARCH_CONTEXT] Nombre de documents dans le contexte: {len(meili_results_docs)}")

            # Les meili_results sont maintenant une liste de documents complets, plus besoin de post-traitement complexe ici
            meili_results = meili_results_docs # Pour compatibilité avec les logs existants si nécessaire

        except Exception as e:
            logger.error(f"[RAG_ADVANCED] Erreur MeiliSearch (Orchestrateur): {e}")
            meili_context = ""
            meili_results = [] # S'assurer que c'est vide en cas d'erreur
        
        # 2. Génération de réponse LLM (SANS VALIDATION)
        logger.info(f"[RAG_ADVANCED] 🤖 Étape 2: Génération LLM")
        
        try:
            from .llm_client import GroqLLMClient
            llm_client = GroqLLMClient()
            
            # Construction du prompt contextuel avec fusion intelligente
            context_parts = []
            
            # Contexte Supabase (sémantique)
            if supabase_context and len(supabase_context.strip()) > 0:
                context_parts.append(f"=== INFORMATIONS SÉMANTIQUES ===\n{supabase_context}")
                logger.info(f"[CONTEXT_FUSION] - Contexte Supabase ajouté: {len(supabase_context)} caractères")
            else:
                logger.warning(f"[CONTEXT_FUSION] - Contexte Supabase vide ou manquant")
            
            # Contexte MeiliSearch (textuel)
            if meili_context and len(meili_context.strip()) > 0:
                context_parts.append(f"=== INFORMATIONS TEXTUELLES ===\n{meili_context}")
                logger.info(f"[CONTEXT_FUSION] - Contexte MeiliSearch ajouté: {len(meili_context)} caractères")
            else:
                logger.warning(f"[CONTEXT_FUSION] - Contexte MeiliSearch vide ou manquant")
            
            # Contexte final
            context = "\n\n".join(context_parts) if context_parts else "Aucun contexte disponible"
            
            # Logs de la fusion
            logger.info(f"[CONTEXT_FUSION] 📋 Fusion des contextes:")
            logger.info(f"[CONTEXT_FUSION] - Nombre de sources: {len(context_parts)}")
            logger.info(f"[CONTEXT_FUSION] - Longueur totale: {len(context)} caractères")
            logger.info(f"[CONTEXT_FUSION] - Sources utilisées:")
            if supabase_context and len(supabase_context.strip()) > 0:
                logger.info(f"[CONTEXT_FUSION]   ✓ Supabase: {len(supabase_context)} caractères")
            else:
                logger.info(f"[CONTEXT_FUSION]   ✗ Supabase: vide")
            if meili_context and len(meili_context.strip()) > 0:
                logger.info(f"[CONTEXT_FUSION]   ✓ MeiliSearch: {len(meili_context)} caractères")
            else:
                logger.info(f"[CONTEXT_FUSION]   ✗ MeiliSearch: vide")
            
            # Logs détaillés du contexte final - VERSION TRONQUÉE
            logger.info(f"[FINAL_CONTEXT] 📋 CONTEXTE FINAL ASSEMBLÉ:")
            logger.info(f"[FINAL_CONTEXT] ==========================================")
            logger.info(f"[FINAL_CONTEXT] - Contexte Supabase: {len(supabase_context)} caractères")
            logger.info(f"[FINAL_CONTEXT] - Contexte MeiliSearch: {len(meili_context)} caractères")
            logger.info(f"[FINAL_CONTEXT] - Contexte total: {len(context)} caractères")
            logger.info(f"[FINAL_CONTEXT] - Aperçu du contenu complet: {context}")
            logger.info(f"[FINAL_CONTEXT] ==========================================")
            
            # Logging détaillé de la génération LLM
            log_llm_generation(context, "", "llama-3.3-70b-versatile", 0.7, 300)
            
            # Prompt simple et direct
            # system_prompt = f"""Tu es Gamma, l'assistant client de Rue du Gros.
            # Réponds de manière précise et professionnelle en te basant sur le contexte fourni.
            # 
            # Contexte: {context}
            # Question: {message}
            # 
            # Règles importantes:
            # - Réponds de manière naturelle et professionnelle
            # - Utilise les informations du contexte si disponibles
            # - Si tu n'as pas d'informations, dis-le clairement
            # - Sois précis et factuel"""
            
            # Récupérer le prompt système personnalisé dynamiquement
            from core.prompt_manager import PromptManager
            prompt_manager = PromptManager(get_supabase_client())
            prompt_data = await prompt_manager.get_active_prompt(company_id)
            dynamic_system_prompt = "Tu es Gamma, l'assistant client de Rue du Gros. Réponds de manière précise et professionnelle en te basant sur le contexte fourni. Sois concis."
            
            if prompt_data:
                dynamic_system_prompt = prompt_data.get('prompt_template', dynamic_system_prompt)
                logger.info(f"[RAG_ADVANCED] Prompt personnalisé chargé (version: {prompt_data.get('version', 'N/A')})")

            # Construction du prompt complet avec contexte et message
            system_prompt = f"""{dynamic_system_prompt}

            Contexte:
            {context}

            Question: {message}
            """
            
            # Ajouter les informations de mémoire au prompt principal
            memory_data = None # Initialiser memory_data
            if memory_data and memory_data.get("conversation_summary"):
                summary = memory_data["conversation_summary"]
                completeness = summary.get("completeness_percentage", 0)
                
                memory_context = f"\n\n🧠 CONTEXTE CONVERSATIONNEL ACTUEL:\n"
                memory_context += f"📊 Complétude: {completeness:.1f}%\n"
                
                if summary.get("customer_info"):
                    customer = summary["customer_info"]
                    if customer.get("name"):
                        memory_context += f"👤 Client: {customer['name']}\n"
                    if customer.get("phone"):
                        memory_context += f"📞 Téléphone: {customer['phone']}\n"
                
                if summary.get("delivery_info"):
                    delivery = summary["delivery_info"]
                    if delivery.get("address"):
                        memory_context += f"📍 Adresse: {delivery['address']}\n"
                    if delivery.get("zone"):
                        memory_context += f"🌍 Zone: {delivery['zone']}\n"
                
                if summary.get("order_info"):
                    order = summary["order_info"]
                    if order.get("product_type"):
                        memory_context += f"📦 Produit: {order['product_type']}\n"
                    if order.get("quantity"):
                        memory_context += f"🔢 Quantité: {order['quantity']}\n"
                
                if summary.get("missing_information"):
                    missing = summary["missing_information"]
                    memory_context += f"❓ Informations manquantes: {', '.join(missing)}\n"
                
                system_prompt += memory_context
                logger.info(f"[MEMORY_SYSTEM] ✅ Contexte de mémoire ajouté au prompt")
            
            # 🧮 CALCUL DE PRIX AUTOMATIQUE
            price_info = None
            try:
                # Détecter si la requête concerne un calcul de prix
                price_keywords = [
                    "prix", "coût", "combien", "tarif", "commander", "acheter", "total", "livraison",
                    "voulais", "prendre", "quantité", "montant", "facture", "payer", "panier",
                    "finaliser", "passer commande", "détails commande", "quel est le prix",
                    "facturation", "coûter", "avoir", "proposer", "vendre", "souhaite", "désire",
                    "achat", "articles", "produits", "somme", "calculer", "devis"
                ]
                if any(keyword in message.lower() for keyword in price_keywords):
                    logger.info(f"[PRICE_CALCULATOR] 🧮 Calcul de prix détecté")
                    
                    # Utiliser les informations de mémoire pour améliorer le calcul
                    delivery_zone = None
                    if memory_data and memory_data.get("conversation_summary", {}).get("delivery_info", {}).get("zone"):
                        delivery_zone = memory_data["conversation_summary"]["delivery_info"]["zone"]
                    elif any(zone in message.lower() for zone in ["cocody", "yopougon", "plateau", "adjamé", "abobo", "marcory", "koumassi", "treichville", "angré", "riviera", "bingerville", "port-bouët", "attécoubé"]):
                        delivery_zone = message
                    
                    # Calculer le prix
                    price_info = calculate_order_price(message, company_id, delivery_zone)
                    
                    if price_info and price_info.get("products"):
                        logger.info(f"[PRICE_CALCULATOR] ✅ Prix calculé: {price_info['total']:,} FCFA")
                        
                        # Ajouter les informations de prix au contexte
                        price_context = f"\n\n🧮 INFORMATIONS DE PRIX CALCULÉES AUTOMATIQUEMENT:\n{price_info['breakdown']}\n"
                        system_prompt += price_context
                        
                        logger.info(f"[PRICE_CALCULATOR] 📝 Contexte de prix ajouté au prompt")
                    else:
                        logger.info(f"[PRICE_CALCULATOR] ⚠️ Aucun produit identifié pour le calcul de prix")
                        
            except Exception as e:
                logger.error(f"[PRICE_CALCULATOR] ❌ Erreur calcul prix: {str(e)}")
                price_info = None
            
            ai_response = await llm_client.complete(
                prompt=system_prompt,
                temperature=0.7,
                max_tokens=300
            )
            
            # Logging détaillé de la réponse LLM
            log_llm_generation(system_prompt, ai_response, "llama-3.3-70b-versatile", 0.7, 300)
            
            # Logs détaillés de la réponse LLM - VERSION TRONQUÉE
            logger.info(f"[LLM_RESPONSE] 🤖 RÉPONSE LLM GÉNÉRÉE:")
            logger.info(f"[LLM_RESPONSE] ==========================================")
            logger.info(f"[LLM_RESPONSE] - Longueur: {len(ai_response)} caractères")
            logger.info(f"[LLM_RESPONSE] - Nombre de lignes: {len(ai_response.splitlines())}")
            logger.info(f"[LLM_RESPONSE] - Nombre de mots: {len(ai_response.split())}")
            logger.info(f"[LLM_RESPONSE] - Aperçu du contenu complet: {ai_response}")
            logger.info(f"[LLM_RESPONSE] - Analyse de la réponse: ...") # Laisser l'analyse, elle est concise
            logger.info(f"[LLM_RESPONSE] ==========================================")
            
            # Logs détaillés du prompt final
            logger.info(f"[LLM_PROMPT] 📝 PROMPT COMPLET ENVOYÉ AU LLM:")
            logger.info(f"[LLM_PROMPT] ==========================================")
            logger.info(f"[LLM_PROMPT] - Longueur: {len(system_prompt)} caractères")
            logger.info(f"[LLM_PROMPT] - Nombre de lignes: {len(system_prompt.splitlines())}")
            logger.info(f"[LLM_PROMPT] - Aperçu du contenu complet: {system_prompt}")
            logger.info(f"[LLM_PROMPT] - Paramètres LLM: ...") # Laisser les paramètres, ils sont concis
            logger.info(f"[LLM_PROMPT] ==========================================")
            
        except Exception as e:
            logger.error(f"[RAG_ADVANCED] Erreur LLM: {e}")
            ai_response = "Je rencontre une difficulté technique. Pouvez-vous réessayer ?"

        # 3. Sauvegarde de la conversation
        logger.info(f"[RAG_ADVANCED] 💾 Étape 3: Sauvegarde conversation")
        try:
            await save_message(
                company_id=company_id,
                user_id=user_id,
                role="user",
                content=message
            )
            await save_message(
                company_id=company_id,
                user_id=user_id,
                role="assistant",
                content=ai_response
            )
            logger.info(f"[RAG_ADVANCED] ✅ Conversation sauvegardée")
        except Exception as e:
            logger.warning(f"[RAG_ADVANCED] Erreur sauvegarde: {e}")
        
        # 4. Construction de la réponse finale (SANS VALIDATION)
        logger.info(f"[RAG_ADVANCED] 📤 Étape 4: Construction réponse finale")
        
        # Ajouter les informations de prix à la réponse si calculées
        final_response = ai_response
        recap_info = None
        
        # 🧠 GESTION INTELLIGENTE DE LA CONFIRMATION
        if memory_data and memory_data.get("should_confirm"):
            logger.info(f"[MEMORY_SYSTEM] 🔔 Demande de confirmation détectée")
            confirmation_prompt = memory_data.get("confirmation_prompt", "")
            if confirmation_prompt:
                final_response = confirmation_prompt
                logger.info(f"[MEMORY_SYSTEM] ✅ Prompt de confirmation généré")
        
        elif price_info and price_info.get("products"):
            logger.info(f"[PRICE_CALCULATOR] 📊 Ajout des informations de prix à la réponse")
            
            # Détecter si c'est une demande de récapitulatif
            recap_keywords = ["récapitulatif", "récap", "résumé", "confirmer", "commande", "total", "prix total"]
            is_recap_request = any(keyword in message.lower() for keyword in recap_keywords)
            
            if is_recap_request:
                logger.info(f"[RECAP_TEMPLATE] 📋 Génération de récapitulatif structuré")
                
                # Utiliser les informations de mémoire pour le récapitulatif
                customer_info = {
                    "name": "Client",
                    "phone": "Non fourni",
                    "address": "À confirmer"
                }
                
                delivery_info = {
                    "zone": "Zone à confirmer",
                    "address": "Adresse à confirmer",
                    "delivery_time": "À confirmer"
                }
                
                # Enrichir avec les données de mémoire
                if memory_data and memory_data.get("conversation_summary"):
                    summary = memory_data["conversation_summary"]
                    
                    if summary.get("customer_info"):
                        customer_info.update(summary["customer_info"])
                    
                    if summary.get("delivery_info"):
                        delivery_info.update(summary["delivery_info"])
                
                if price_info.get("delivery_info"):
                    delivery_info.update({
                        "zone": price_info["delivery_info"].zone,
                        "delivery_time": price_info["delivery_info"].delivery_time
                    })
                
                # Générer le récapitulatif complet
                recap_info = generate_order_summary(
                    customer_info=customer_info,
                    products=price_info["products"],
                    delivery_info=delivery_info,
                    price_info=price_info,
                    company_id=company_id,
                    summary_type="full"
                )
                
                final_response = recap_info
                logger.info(f"[RECAP_TEMPLATE] ✅ Récapitulatif généré avec succès")
            else:
                # Ajouter juste le détail des prix
                price_summary = f"\n\n{price_info['breakdown']}"
                final_response += price_summary
        
        response_data = {
            'response': final_response,
            'intent': 'factual_information',  # Toujours factual_information
            'confidence': 1.0,  # Score fixe à 1.0
            'confidence_level': 'high',  # Niveau fixe à high
            'validation_safe': True,  # Toujours sûr
            'requires_documents': True,  # Toujours True
            'documents_found': bool(supabase_context or meili_context),
            'processing_time_ms': (time.time() - start_time) * 1000,
            'price_calculated': price_info is not None,
            'price_info': price_info if price_info else None,
            'memory_data': memory_data if memory_data else None,
            'conversation_completeness': memory_data.get("conversation_summary", {}).get("completeness_percentage", 0) if memory_data else 0,
            'missing_information': memory_data.get("missing_information", []) if memory_data else [],
            'should_confirm': memory_data.get("should_confirm", False) if memory_data else False,
            'debug_info': {
                'validation_mode': 'disabled',  # Désactivé
                'validation_result': 'bypassed',  # Contourné
                'fallback_used': False,  # Jamais de fallback
                'specific_information_detected': [],  # Vide
                'source_verification': {},  # Vide
                'suggested_action': 'none'  # Aucune action
            }
        }
        
        # 💾 SAUVEGARDE AUTOMATIQUE DES LOGS
        try:
            from .detailed_logging_system import save_logs_to_file
            log_file = save_logs_to_file()
            if log_file:
                logger.info(f"[RAG_ADVANCED] 📁 Logs sauvegardés: {log_file}")
        except Exception as e:
            logger.warning(f"[RAG_ADVANCED] Erreur sauvegarde logs: {e}")
        
        # Logs de résumé final - VERSION TRONQUÉE
        logger.info(f"[RAG_SUMMARY] 📊 RÉSUMÉ FINAL DU SYSTÈME DE RECHERCHE:")
        logger.info(f"[RAG_SUMMARY] ==========================================")
        logger.info(f"[RAG_SUMMARY] - Requête reçue: '{message}'")
        logger.info(f"[RAG_SUMMARY] - Longueur requête: {len(message)} caractères")
        logger.info(f"[RAG_SUMMARY] - Documents Supabase trouvés: {len(supabase_results)}")
        logger.info(f"[RAG_SUMMARY] - Contexte Supabase: {len(supabase_context)} caractères")
        logger.info(f"[RAG_SUMMARY] - Documents MeiliSearch trouvés: {len(meili_results_docs) if 'meili_results_docs' in locals() else 'N/A'}")
        logger.info(f"[RAG_SUMMARY] - Contexte MeiliSearch: {len(meili_context)} caractères")
        logger.info(f"[RAG_SUMMARY] - Contexte total: {len(context)} caractères")
        logger.info(f"[RAG_SUMMARY] - Réponse LLM: {len(ai_response)} caractères")
        logger.info(f"[RAG_SUMMARY] - Temps de traitement: {(time.time() - start_time) * 1000:.2f} ms")
        logger.info(f"[RAG_SUMMARY] - Statut: Succès")
        logger.info(f"[RAG_SUMMARY] ==========================================")
        
        logger.info(f"[RAG_ADVANCED] ✅ Réponse générée: 1.000 (high)")
        
        # Logging détaillé de la réponse finale
        log_response_sent(ai_response, {
            "intent": "factual_information",
            "confidence": 1.0,
            "documents_found": len(supabase_results) > 0,
            "processing_time_ms": (time.time() - start_time) * 1000
        })
        
        return response_data
        
    except Exception as e:
        logger.error(f"[RAG_ADVANCED] ❌ Erreur critique: {e}")
        log_error("RAG_ENGINE", "CRITICAL_ERROR", e, {
            "message": message,
            "user_id": user_id,
            "company_id": company_id
        })
        
        # Fallback d'urgence
        logger.warning(f"[RAG_ADVANCED] 🚨 Activation du fallback d'urgence")
        
        emergency_response = {
            'response': "Je rencontre une difficulté technique. Pouvez-vous réessayer ou contacter notre service client ?",
            'intent': 'factual_information',
            'confidence': 1.0,
            'confidence_level': 'high',
            'validation_safe': True,
            'requires_documents': True,
            'documents_found': False,
            'processing_time_ms': (time.time() - start_time) * 1000,
            'debug_info': {
                'error': str(e),
                'emergency_fallback': True
            }
        }
        
        logger.error(f"[RAG_ADVANCED] Fallback d'urgence activé: {str(e)}")
        
        return emergency_response

async def get_rag_response(message: str, company_id: str, user_id: str) -> str:
    """
    🎯 FONCTION PRINCIPALE D'EXPORT (COMPATIBILITÉ)
    Interface simple pour l'intégration avec app.py
    """
    try:
        # Utilisation du nouveau système avancé
        result = await get_rag_response_advanced(
            message=message,
            user_id=user_id,
            company_id=company_id
        )
        
        # Vérifier que result est un dictionnaire et contient 'response'
        if isinstance(result, dict) and 'response' in result:
            return result['response']
        elif isinstance(result, str):
            return result
        else:
            logger.error(f"[RAG_RESPONSE] Format de réponse inattendu: {type(result)}")
            return "Erreur de format de réponse"
            
    except Exception as e:
        logger.error(f"[RAG_RESPONSE] Erreur dans get_rag_response: {str(e)}")
        return "Erreur lors de la génération de la réponse"
