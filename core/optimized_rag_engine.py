"""
🚀 RAG ENGINE OPTIMISÉ - ARCHITECTURE NOUVELLE GÉNÉRATION
Remplace complètement l'ancien rag_engine.py avec une approche moderne et performante
"""
import asyncio
import time
import uuid
from typing import Dict, List, Optional, Any, Tuple

from core.semantic_search_engine import semantic_search, SearchConfig, SearchStrategy
from core.llm_client import GroqLLMClient
from database.supabase_client import get_company_system_prompt, get_company_context
from core.conversation import get_history, save_message
from core.cache_manager import cache_manager
from utils import log3, timing_metric, validate_context


class OptimizedRAGEngine:
    """
    🎯 MOTEUR RAG OPTIMISÉ
    
    Caractéristiques :
    - Architecture simplifiée et modulaire
    - Performance maximisée
    - Cache intelligent
    - Logs structurés
    - Gestion d'erreurs robuste
    """
    
    def __init__(self):
        self.llm_client = GroqLLMClient()
        self.request_cache: Dict[str, Any] = {}
    
    async def preprocess_query(self, message: str, chat_history: List[Dict]) -> str:
        """
        🔄 PRÉTRAITEMENT INTELLIGENT DE LA REQUÊTE
        Enrichit la requête avec le contexte conversationnel
        """
        try:
            # Si historique disponible, enrichir la requête
            if chat_history and len(chat_history) > 0:
                # Prendre les 3 derniers échanges pour le contexte
                recent_context = []
                for exchange in chat_history[-3:]:
                    if exchange.get('user_message'):
                        recent_context.append(f"User: {exchange['user_message']}")
                    if exchange.get('assistant_message'):
                        recent_context.append(f"Assistant: {exchange['assistant_message'][:100]}...")
                
                context_str = "\n".join(recent_context)
                
                # Enrichissement contextuel simple
                enriched_query = f"Contexte récent:\n{context_str}\n\nNouvelle question: {message}"
                
                log3("[QUERY_PREPROCESSING]", f"✅ Requête enrichie avec {len(chat_history)} échanges d'historique")
                return enriched_query
            
            return message
            
        except Exception as e:
            log3("[QUERY_PREPROCESSING]", f"⚠️ Erreur prétraitement: {str(e)}")
            return message
    
    async def generate_response(
        self, 
        query: str, 
        context: str, 
        company_id: str
    ) -> str:
        """
        🤖 GÉNÉRATION DE RÉPONSE LLM OPTIMISÉE
        """
        try:
            # Récupération du prompt système
            system_prompt = await get_company_system_prompt(company_id)
            company_context = await get_company_context(company_id)
            
            # Construction du prompt optimisé
            company_name = company_context.get('companyName', 'Notre entreprise')
            ai_name = company_context.get('aiName', 'Assistant')
            
            # Prompt structuré
            full_prompt = f"""Tu es {ai_name}, l'assistant IA de {company_name}.

CONTEXTE DOCUMENTAIRE:
{context}

INSTRUCTIONS:
- Réponds uniquement en te basant sur le contexte fourni
- Si l'information n'est pas dans le contexte, dis-le clairement
- Sois précis, utile et professionnel
- Utilise le nom de l'entreprise quand c'est pertinent

QUESTION: {query}

RÉPONSE:"""

            # Génération avec le LLM
            response = await self.llm_client.complete(
                prompt=full_prompt,
                max_tokens=500,
                temperature=0.1  # Réponses plus déterministes
            )
            
            log3("[LLM_RESPONSE]", f"✅ Réponse générée: {len(response)} caractères")
            return response
            
        except Exception as e:
            log3("[LLM_RESPONSE]", f"💥 Erreur génération: {type(e).__name__}: {str(e)}")
            return "Je rencontre une difficulté technique. Pouvez-vous reformuler votre question ?"
    
    def should_use_cache(self, query: str, company_id: str, user_id: str) -> Optional[str]:
        """
        🗄️ VÉRIFICATION CACHE INTELLIGENT
        """
        try:
            # Clé de cache basée sur la requête normalisée
            normalized_query = query.lower().strip()
            cache_key = f"rag_response:{company_id}:{hash(normalized_query)}"
            
            cached_response = cache_manager.get(cache_key)
            if cached_response:
                log3("[CACHE]", f"✅ Cache hit pour requête: {query[:50]}...")
                return cached_response
            
            return None
            
        except Exception as e:
            log3("[CACHE]", f"⚠️ Erreur cache: {str(e)}")
            return None
    
    def cache_response(self, query: str, company_id: str, response: str):
        """
        💾 MISE EN CACHE DE LA RÉPONSE
        """
        try:
            normalized_query = query.lower().strip()
            cache_key = f"rag_response:{company_id}:{hash(normalized_query)}"
            
            # Cache pour 1 heure
            cache_manager.set(cache_key, response, ttl_seconds=3600)
            log3("[CACHE]", f"✅ Réponse mise en cache: {cache_key}")
            
        except Exception as e:
            log3("[CACHE]", f"⚠️ Erreur mise en cache: {str(e)}")
    
    @timing_metric("rag_total_optimized")
    async def process_request(
        self, 
        company_id: str, 
        user_id: str, 
        message: str
    ) -> str:
        """
        🚀 TRAITEMENT PRINCIPAL OPTIMISÉ
        Point d'entrée unique pour le traitement RAG
        """
        request_id = str(uuid.uuid4())[:8]
        
        log3("[RAG_OPTIMIZED]", {
            "request_id": request_id,
            "company_id": company_id,
            "user_id": user_id,
            "message_preview": message[:100],
            "message_length": len(message)
        })
        
        try:
            # 1. Validation des entrées
            if not message or not message.strip():
                return "Veuillez poser une question."
            
            # 2. Vérification cache
            cached_response = self.should_use_cache(message, company_id, user_id)
            if cached_response:
                return cached_response
            
            # 3. Récupération historique
            start_time = time.time()
            chat_history = await get_history(company_id, user_id)
            history_time = time.time() - start_time
            
            # 4. Prétraitement de la requête
            start_time = time.time()
            processed_query = await self.preprocess_query(message, chat_history)
            preprocess_time = time.time() - start_time
            
            # 5. Recherche sémantique
            start_time = time.time()
            search_results, formatted_context = await semantic_search(
                query=processed_query,
                company_id=company_id,
                top_k=5,
                min_score=0.3
            )
            search_time = time.time() - start_time
            
            # 6. Vérification des résultats
            if not formatted_context or len(search_results) == 0:
                log3("[RAG_OPTIMIZED]", f"❌ Aucun contexte trouvé pour: {message[:50]}...")
                
                # Gestion de la relance
                relance_key = f"no_context:{company_id}:{user_id}"
                if cache_manager.get(relance_key):
                    cache_manager.delete(relance_key)
                    return "Je vous mets en relation avec un conseiller qui pourra mieux vous aider."
                
                cache_manager.set(relance_key, "1", ttl_seconds=600)
                return "Je n'ai pas trouvé d'information précise. Pouvez-vous reformuler votre question ?"
            
            # 7. Génération de la réponse
            start_time = time.time()
            response = await self.generate_response(
                query=message,  # Requête originale pour la réponse
                context=formatted_context,
                company_id=company_id
            )
            generation_time = time.time() - start_time
            
            # 8. Sauvegarde en cache
            self.cache_response(message, company_id, response)
            
            # 9. Sauvegarde de la conversation
            try:
                await save_message(company_id, user_id, message, response)
            except Exception as e:
                log3("[CONVERSATION_SAVE]", f"⚠️ Erreur sauvegarde: {str(e)}")
            
            # 10. Métriques finales
            total_time = history_time + preprocess_time + search_time + generation_time
            
            log3("[RAG_OPTIMIZED]", {
                "request_id": request_id,
                "success": True,
                "results_count": len(search_results),
                "context_length": len(formatted_context),
                "response_length": len(response),
                "timing": {
                    "history_ms": round(history_time * 1000, 2),
                    "preprocess_ms": round(preprocess_time * 1000, 2),
                    "search_ms": round(search_time * 1000, 2),
                    "generation_ms": round(generation_time * 1000, 2),
                    "total_ms": round(total_time * 1000, 2)
                }
            })
            
            return response
            
        except Exception as e:
            log3("[RAG_OPTIMIZED]", {
                "request_id": request_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "success": False
            })
            
            return "Je rencontre une difficulté technique momentanée. Veuillez réessayer."


# Instance globale
_rag_engine: Optional[OptimizedRAGEngine] = None

def get_rag_engine() -> OptimizedRAGEngine:
    """Factory pour obtenir l'instance du moteur RAG"""
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = OptimizedRAGEngine()
    return _rag_engine


# API de compatibilité avec l'ancien système
async def get_rag_response(company_id: str, user_id: str, message: str) -> str:
    """
    🎯 API PRINCIPALE POUR COMPATIBILITÉ
    Remplace l'ancienne fonction get_rag_response
    """
    engine = get_rag_engine()
    return await engine.process_request(company_id, user_id, message)


# Fonction de nettoyage
async def cleanup_rag_engine():
    """Nettoyage des ressources"""
    global _rag_engine
    if _rag_engine:
        # Nettoyage si nécessaire
        pass
