#!/usr/bin/env python3
"""
🎯 AUTO-LEARNING WRAPPER - Intégration Simple dans RAG

Wrapper léger pour intégrer auto-learning sans modifier le code existant.
Appel unique: track_rag_execution()

Usage:
    from core.auto_learning_wrapper import track_rag_execution
    
    # Après exécution RAG
    await track_rag_execution(
        company_id=company_id,
        user_id=user_id,
        query=query,
        thinking_data=thinking_parsed,
        documents_used=search_results,
        response_time_ms=duration,
        llm_model="llama-3.3-70b"
    )
"""

import logging
from typing import Dict, List, Optional
import asyncio

logger = logging.getLogger(__name__)

# Flag global pour activer/désactiver
_auto_learning_enabled = False

def init_auto_learning():
    """
    Initialise le système d'auto-learning
    Appelé au démarrage de l'app
    """
    global _auto_learning_enabled
    
    try:
        from config_performance import ENABLE_AUTO_LEARNING
        _auto_learning_enabled = ENABLE_AUTO_LEARNING
        
        if _auto_learning_enabled:
            logger.info("🧠 Auto-Learning System: ACTIVÉ")
        else:
            logger.info("💤 Auto-Learning System: DÉSACTIVÉ (set ENABLE_AUTO_LEARNING=true)")
            
    except ImportError:
        logger.warning("⚠️ config_performance non trouvé, auto-learning désactivé")
        _auto_learning_enabled = False


async def track_rag_execution(
    company_id: str,
    user_id: str,
    query: str,
    thinking_data: Dict,
    documents_used: List[Dict],
    response_time_ms: int,
    llm_model: str,
    conversation_id: str = None
):
    """
    🎯 Track une exécution RAG complète pour auto-learning
    
    Cette fonction fait TOUT:
    - Track thinking analytics
    - Track document usage
    - Track LLM performance
    - Détecte nouveaux patterns
    - Génère recommandations si nécessaire
    
    Args:
        company_id: ID entreprise
        user_id: ID utilisateur
        query: Question posée
        thinking_data: <thinking> parsé du LLM
        documents_used: Documents retournés par recherche
        response_time_ms: Temps de réponse total
        llm_model: Modèle LLM utilisé
        conversation_id: ID conversation (optionnel)
    """
    if not _auto_learning_enabled:
        return  # Skip silencieusement
    
    try:
        from core.supabase_learning_engine import get_learning_engine
        from config_performance import (
            LEARNING_THINKING,
            LEARNING_DOCUMENTS,
            LEARNING_LLM_PERF,
            LEARNING_PATTERNS
        )
        
        engine = get_learning_engine()
        if not engine.supabase:
            logger.debug("⚠️ Supabase non disponible, skip auto-learning")
            return
        
        # ========== 1. THINKING ANALYTICS ==========
        if LEARNING_THINKING and thinking_data:
            try:
                await engine.store_thinking_analytics(
                    company_id=company_id,
                    user_id=user_id,
                    thinking_data=thinking_data,
                    response_time_ms=response_time_ms,
                    llm_model=llm_model,
                    conversation_id=conversation_id
                )
                logger.debug(f"📊 Thinking tracked: {company_id}")
            except Exception as e:
                logger.error(f"❌ Erreur track thinking: {e}")
        
        # ========== 2. DOCUMENT INTELLIGENCE ==========
        if LEARNING_DOCUMENTS and documents_used:
            try:
                # Déterminer quels docs ont été utilisés dans le thinking
                thinking_text = str(thinking_data)
                
                for doc in documents_used:
                    doc_id = doc.get('id', doc.get('document_id', 'unknown'))
                    doc_content = doc.get('content', doc.get('text', ''))
                    
                    # Simple heuristique: si contenu du doc apparaît dans thinking
                    was_used = False
                    if doc_content and len(doc_content) > 20:
                        # Chercher un extrait du doc dans le thinking
                        excerpt = doc_content[:50]
                        was_used = excerpt.lower() in thinking_text.lower()
                    
                    await engine.track_document_usage(
                        company_id=company_id,
                        document_id=doc_id,
                        was_used_by_llm=was_used,
                        document_source=doc.get('source', 'meilisearch')
                    )
                
                logger.debug(f"📚 {len(documents_used)} docs tracked")
            except Exception as e:
                logger.error(f"❌ Erreur track documents: {e}")
        
        # ========== 3. LLM PERFORMANCE ==========
        if LEARNING_LLM_PERF:
            try:
                # Classifier type de tâche
                task_type = _classify_task_type(query, thinking_data)
                
                # Mesure succès basée sur confiance
                confidence = thinking_data.get('confiance', {}).get('score', 0)
                success = confidence >= 80
                
                # Estimer coût (approximatif)
                cost = _estimate_cost(llm_model, response_time_ms)
                
                await engine.track_llm_performance(
                    company_id=company_id,
                    llm_model=llm_model,
                    task_type=task_type,
                    response_time_ms=response_time_ms,
                    cost=cost,
                    success=success
                )
                logger.debug(f"⚡ LLM perf tracked: {llm_model} on {task_type}")
            except Exception as e:
                logger.error(f"❌ Erreur track LLM: {e}")
        
        # ========== 4. PATTERN DETECTION ==========
        if LEARNING_PATTERNS:
            try:
                # Détecter nouveaux patterns depuis nouvelles_donnees
                nouvelles_donnees = thinking_data.get('nouvelles_donnees', [])
                
                for data in nouvelles_donnees:
                    # Si confiance haute et valeur non vide
                    confiance_val = data.get('confiance', '').upper()
                    if confiance_val in ['HAUTE', 'HIGH'] and data.get('valeur'):
                        cle = data.get('cle', 'unknown')
                        valeur = data.get('valeur', '')
                        
                        # Créer pattern simple
                        pattern_name = f"auto_{cle}_{hash(valeur) % 10000}"
                        pattern_regex = _generate_simple_pattern(valeur)
                        
                        if pattern_regex:
                            await engine.store_learned_pattern(
                                company_id=company_id,
                                pattern_name=pattern_name,
                                pattern_regex=pattern_regex,
                                category=cle,
                                occurrences=1,
                                metadata={
                                    'source': 'thinking_auto_detection',
                                    'example': valeur,
                                    'query': query
                                }
                            )
                            logger.debug(f"🎯 Pattern détecté: {pattern_name}")
                
            except Exception as e:
                logger.error(f"❌ Erreur détection patterns: {e}")
        
    except Exception as e:
        logger.error(f"❌ Erreur générale auto-learning: {e}")


def _classify_task_type(query: str, thinking_data: Dict) -> str:
    """Classifie le type de tâche depuis query + thinking"""
    intentions = thinking_data.get('intentions', {})
    
    if not intentions:
        return 'general'
    
    # Trouver intention max
    max_intent = max(intentions.items(), key=lambda x: x[1], default=('general', 0))
    intent_name, score = max_intent
    
    if score < 50:
        return 'general'
    
    mapping = {
        'demande_prix': 'prix',
        'demande_livraison': 'livraison',
        'demande_produit': 'produit',
        'demande_contact': 'contact',
        'demande_paiement': 'paiement'
    }
    
    return mapping.get(intent_name, 'autre')


def _estimate_cost(llm_model: str, response_time_ms: int) -> float:
    """Estime coût approximatif d'un appel LLM"""
    # Coûts approximatifs par 1M tokens
    cost_per_million = {
        'llama-3.3-70b-versatile': 0.79,  # Groq
        'llama-3.1-8b-instant': 0.05,     # Groq
        'gpt-4': 30.0,                     # OpenAI
        'gpt-3.5-turbo': 1.5               # OpenAI
    }
    
    base_cost = cost_per_million.get(llm_model, 1.0)
    
    # Estimation tokens basée sur temps de réponse (très approximatif)
    estimated_tokens = (response_time_ms / 1000) * 500  # ~500 tokens/sec
    
    return (estimated_tokens / 1_000_000) * base_cost


def _generate_simple_pattern(value: str) -> Optional[str]:
    """
    Génère un pattern regex simple depuis une valeur
    
    Exemples:
    - "13500 FCFA" → r"13500\s*FCFA"
    - "Yopougon" → r"Yopougon"
    - "77 123 45 67" → r"\d{2}\s*\d{3}\s*\d{2}\s*\d{2}"
    """
    import re
    
    if not value or len(value) < 3:
        return None
    
    # Si contient chiffres → généraliser
    if any(c.isdigit() for c in value):
        # Téléphone pattern
        if len(value) >= 8 and value.replace(' ', '').replace('-', '').isdigit():
            return r'\d{2}\s*\d{3}\s*\d{2}\s*\d{2}'
        
        # Prix pattern
        if 'FCFA' in value.upper() or 'EUR' in value.upper() or '€' in value:
            # Extraire nombre
            number = re.search(r'\d+(?:[.,]\d+)?', value)
            if number:
                num_val = number.group()
                devise = 'FCFA' if 'FCFA' in value.upper() else '€' if '€' in value else 'EUR'
                return f"{num_val}\\s*{devise}"
    
    # Sinon, pattern exact (escaping caractères spéciaux)
    return re.escape(value)


# ========================================
# ANALYTICS & INSIGHTS
# ========================================

async def get_company_insights(company_id: str, days: int = 7) -> Dict:
    """
    📊 Récupère insights d'auto-learning pour une company
    
    Returns:
        {
            'patterns_learned': [...],
            'thinking_analytics': {...},
            'top_documents': [...],
            'llm_recommendations': {...},
            'pending_improvements': [...]
        }
    """
    if not _auto_learning_enabled:
        return {'enabled': False}
    
    try:
        from core.supabase_learning_engine import get_learning_engine
        engine = get_learning_engine()
        
        if not engine.supabase:
            return {'enabled': False, 'error': 'Supabase non disponible'}
        
        # Récupérer toutes les données
        patterns = await engine.get_active_patterns(company_id)
        thinking = await engine.analyze_thinking_patterns(company_id, days)
        top_docs = await engine.get_top_documents(company_id, limit=10)
        improvements = await engine.get_pending_improvements(company_id)
        
        return {
            'enabled': True,
            'company_id': company_id,
            'period_days': days,
            'patterns_learned': patterns,
            'thinking_analytics': thinking,
            'top_documents': top_docs,
            'pending_improvements': improvements,
            'summary': {
                'total_patterns': len(patterns),
                'total_conversations': thinking.get('total_conversations', 0),
                'avg_confidence': thinking.get('avg_confidence', 0),
                'pending_improvements_count': len(improvements)
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur récupération insights: {e}")
        return {'enabled': True, 'error': str(e)}
