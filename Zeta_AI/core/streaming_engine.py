"""
🚀 MOTEUR DE STREAMING POUR RÉPONSES TEMPS RÉEL
Système parallèle à l'existant - ZÉRO RISQUE
"""

import asyncio
import json
import time
from typing import AsyncGenerator, Dict, Any
from fastapi.responses import StreamingResponse
from core.rag_engine_simplified_fixed import get_rag_response_advanced
from database.vector_store_clean import search_meili_keywords
from database.supabase_client import match_documents_via_rpc
from core.llm_client import GroqLLMClient
import logging

logger = logging.getLogger(__name__)

class StreamingRAGEngine:
    """
    🎯 MOTEUR RAG AVEC STREAMING
    - Réponses token par token comme ChatGPT
    - Updates de progression en temps réel
    - Parallèle à l'existant - pas de modification du code actuel
    """
    
    def __init__(self):
        self.llm_client = GroqLLMClient()
    
    async def stream_search_progress(self, query: str, company_id: str) -> AsyncGenerator[str, None]:
        """Streaming de la progression de recherche"""
        
        # 1. Début de recherche
        yield self._format_sse({
            'type': 'search_start',
            'message': '🔍 Recherche en cours...',
            'timestamp': time.time()
        })
        
        # 2. Recherche MeiliSearch
        yield self._format_sse({
            'type': 'search_meilisearch',
            'message': '📂 Recherche dans la base de documents...',
            'timestamp': time.time()
        })
        
        start_time = time.time()
        available_indexes = [
            f"products_{company_id}",
            f"delivery_{company_id}",
            f"support_paiement_{company_id}",
            f"company_docs_{company_id}",
            f"localisation_{company_id}"
        ]
        
        try:
            meili_results = await search_meili_keywords(
                query=query,
                company_id=company_id,
                target_indexes=available_indexes
            )
            meili_time = (time.time() - start_time) * 1000
            
            # Analyser la qualité
            context = ""
            search_source = ""
            
            if isinstance(meili_results, str) and len(meili_results.strip()) > 100:
                context = meili_results.strip()
                search_source = "MeiliSearch"
                
                yield self._format_sse({
                    'type': 'search_success',
                    'message': f'✅ Documents trouvés ({len(context)} caractères)',
                    'source': 'MeiliSearch',
                    'time_ms': meili_time,
                    'timestamp': time.time()
                })
                
            else:
                # Fallback Supabase
                yield self._format_sse({
                    'type': 'search_fallback',
                    'message': '🔄 Recherche sémantique de fallback...',
                    'timestamp': time.time()
                })
                
                # Cache d'embedding si pas déjà fait
                if not hasattr(self, '_embedding_model_cache'):
                    from embedding_models import get_embedding_model
                    self._embedding_model_cache = get_embedding_model()
                
                model = self._embedding_model_cache
                embedding = model.encode(query).tolist()
                
                supabase_results = await match_documents_via_rpc(
                    embedding=embedding,
                    company_id=company_id,
                    top_k=2,
                    min_score=0.2,
                    original_query=query
                )
                
                if supabase_results:
                    context_parts = []
                    for result in supabase_results:
                        if isinstance(result, dict) and 'content' in result:
                            content_text = result['content'].strip()
                            if len(content_text) > 50:
                                context_parts.append(content_text)
                    
                    if context_parts:
                        context = "\n\n".join(context_parts)
                        search_source = "Supabase (Fallback)"
                        
                        yield self._format_sse({
                            'type': 'search_success',
                            'message': f'✅ Documents trouvés via recherche sémantique',
                            'source': 'Supabase',
                            'timestamp': time.time()
                        })
            
            # 3. Début de génération
            if context:
                yield self._format_sse({
                    'type': 'generation_start',
                    'message': '🤖 Génération de la réponse...',
                    'context_length': len(context),
                    'source': search_source,
                    'timestamp': time.time()
                })
                
                # 4. Streaming de la génération LLM
                async for token_chunk in self._stream_llm_generation(query, context, company_id):
                    yield token_chunk
                    
                # 5. Fin
                yield self._format_sse({
                    'type': 'complete',
                    'message': '✅ Réponse terminée',
                    'timestamp': time.time()
                })
                
            else:
                yield self._format_sse({
                    'type': 'error',
                    'message': '❌ Aucun document pertinent trouvé',
                    'timestamp': time.time()
                })
                
        except Exception as e:
            logger.error(f"[STREAMING] Erreur: {e}")
            yield self._format_sse({
                'type': 'error',
                'message': f'❌ Erreur: {str(e)}',
                'timestamp': time.time()
            })
    
    async def _stream_llm_generation(self, query: str, context: str, company_id: str) -> AsyncGenerator[str, None]:
        """Streaming de la génération LLM token par token"""
        
        try:
            # Prompt optimisé
            system_prompt = f"""Tu es Gamma, l'assistant client de Rue du Gros.
Réponds de manière précise et professionnelle en te basant sur le contexte fourni.

CONTEXTE:
{context}

INSTRUCTIONS:
- Réponds uniquement avec les informations du contexte
- Sois précis et professionnel
- Si l'information n'est pas dans le contexte, dis-le clairement
"""
            
            # Simulation du streaming (Groq supporte le streaming)
            full_response = await self.llm_client.complete(
                prompt=f"{system_prompt}\n\nQuestion: {query}\n\nRéponse:",
                model_name="llama-3.3-70b-versatile",
                temperature=0.3,
                max_tokens=500
            )
            
            # Simuler le streaming mot par mot
            words = full_response.split()
            current_response = ""
            
            for i, word in enumerate(words):
                current_response += word + " "
                
                yield self._format_sse({
                    'type': 'token',
                    'content': word + " ",
                    'full_response': current_response.strip(),
                    'progress': (i + 1) / len(words),
                    'timestamp': time.time()
                })
                
                # Délai réaliste pour simulation streaming
                await asyncio.sleep(0.05)  # 50ms entre mots
                
        except Exception as e:
            logger.error(f"[STREAMING_LLM] Erreur: {e}")
            yield self._format_sse({
                'type': 'error',
                'message': f'❌ Erreur génération: {str(e)}',
                'timestamp': time.time()
            })
    
    def _format_sse(self, data: Dict[str, Any]) -> str:
        """Formate les données pour Server-Sent Events"""
        return f"data: {json.dumps(data)}\n\n"

# Instance globale
streaming_engine = StreamingRAGEngine()




