#!/usr/bin/env python3
"""
🧠 SUPABASE LEARNING ENGINE - Système d'Auto-Apprentissage

Architecture complète pour apprentissage automatique:
- Pattern auto-learning depuis conversations
- Analytics de thinking LLM
- Intelligence documentaire (scoring automatique)
- Performance LLM tracking & auto-sélection
- Recommandations d'amélioration
- FAQ auto-générées

Version: 1.0
Date: 2025-01-20
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("⚠️ supabase-py non installé: pip install supabase")

logger = logging.getLogger(__name__)


class SupabaseLearningEngine:
    """
    🧠 Moteur d'apprentissage centralisé sur Supabase
    
    Fonctionnalités:
    1. Pattern Learning: Apprend patterns depuis conversations
    2. Thinking Analytics: Analyse raisonnements LLM
    3. Document Intelligence: Score utilité documents
    4. LLM Performance: Track & sélectionne meilleur LLM
    5. Auto-Improvements: Génère recommandations
    6. FAQ Auto-Gen: Crée FAQ depuis questions fréquentes
    """
    
    def __init__(self):
        """Initialise connexion Supabase"""
        if not SUPABASE_AVAILABLE:
            logger.warning("⚠️ SupabaseLearningEngine: Module supabase non disponible")
            self.supabase = None
            return
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            logger.warning("⚠️ SupabaseLearningEngine: Variables SUPABASE manquantes")
            self.supabase = None
            return
        
        try:
            self.supabase: Client = create_client(supabase_url, supabase_key)
            logger.info("✅ SupabaseLearningEngine initialisé")
        except Exception as e:
            logger.error(f"❌ Erreur init Supabase: {e}")
            self.supabase = None
    
    # ========================================
    # 1. PATTERN AUTO-LEARNING
    # ========================================
    
    async def store_learned_pattern(
        self, 
        company_id: str,
        pattern_name: str,
        pattern_regex: str,
        category: str,
        occurrences: int = 1,
        metadata: Dict = None
    ) -> Optional[Dict]:
        """
        💾 Stocke un pattern appris automatiquement
        
        Args:
            company_id: ID entreprise
            pattern_name: Nom unique du pattern
            pattern_regex: Expression régulière
            category: 'produit', 'prix', 'zone', etc.
            occurrences: Nombre d'occurrences détectées
            metadata: Contexte additionnel
        """
        if not self.supabase:
            return None
        
        try:
            # Calcul confiance basé sur occurrences
            confidence = min(occurrences / 10, 1.0)
            
            data = {
                'company_id': company_id,
                'pattern_name': pattern_name,
                'pattern_regex': pattern_regex,
                'category': category,
                'occurrences': occurrences,
                'confidence_score': confidence,
                'metadata': metadata or {},
                'last_used_at': datetime.utcnow().isoformat()
            }
            
            # Upsert: si existe, met à jour
            result = self.supabase.table('learned_patterns')\
                .upsert(data, on_conflict='company_id,pattern_name')\
                .execute()
            
            logger.info(f"✅ Pattern stocké: {pattern_name} ({occurrences}x, conf={confidence:.2f})")
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"❌ Erreur stockage pattern: {e}")
            return None
    
    async def get_active_patterns(self, company_id: str) -> List[Dict]:
        """
        📚 Récupère tous les patterns actifs d'une company
        
        Returns:
            Liste de patterns triés par confiance
        """
        if not self.supabase:
            return []
        
        try:
            result = self.supabase.table('learned_patterns')\
                .select('*')\
                .eq('company_id', company_id)\
                .eq('is_active', True)\
                .order('confidence_score', desc=True)\
                .execute()
            
            patterns = result.data or []
            logger.info(f"📚 {len(patterns)} patterns actifs pour {company_id}")
            return patterns
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération patterns: {e}")
            return []
    
    async def increment_pattern_usage(self, company_id: str, pattern_name: str):
        """
        📈 Incrémente compteur usage d'un pattern
        """
        if not self.supabase:
            return
        
        try:
            # Get current
            result = self.supabase.table('learned_patterns')\
                .select('usage_count')\
                .eq('company_id', company_id)\
                .eq('pattern_name', pattern_name)\
                .single()\
                .execute()
            
            if result.data:
                new_count = result.data['usage_count'] + 1
                
                # Update
                self.supabase.table('learned_patterns')\
                    .update({
                        'usage_count': new_count,
                        'last_used_at': datetime.utcnow().isoformat()
                    })\
                    .eq('company_id', company_id)\
                    .eq('pattern_name', pattern_name)\
                    .execute()
                
        except Exception as e:
            logger.error(f"❌ Erreur increment pattern: {e}")
    
    # ========================================
    # 2. THINKING ANALYTICS
    # ========================================
    
    async def store_thinking_analytics(
        self,
        company_id: str,
        user_id: str,
        thinking_data: Dict,
        response_time_ms: int,
        llm_model: str,
        conversation_id: str = None
    ) -> Optional[Dict]:
        """
        📊 Stocke les analytics d'un thinking LLM
        
        Args:
            thinking_data: Contenu complet du <thinking> parsé
            response_time_ms: Temps de réponse
            llm_model: Modèle utilisé (ex: llama-3.3-70b-versatile)
        """
        if not self.supabase:
            return None
        
        try:
            # Extraire infos clés
            deja_collecte = thinking_data.get('deja_collecte', {})
            
            # Identifier données manquantes
            data_missing = {
                k: v for k, v in deja_collecte.items() 
                if v is None or v == 'null' or v == ''
            }
            
            # Classifier type de question
            question_type = self._classify_question_type(thinking_data)
            
            data = {
                'company_id': company_id,
                'user_id': user_id,
                'conversation_id': conversation_id,
                'thinking_data': thinking_data,
                'question_type': question_type,
                'confidence_score': thinking_data.get('confiance', {}).get('score', 0),
                'completude': thinking_data.get('progression', {}).get('completude', '0/5'),
                'phase_qualification': thinking_data.get('strategie_qualification', {}).get('phase', 'decouverte'),
                'data_collected': deja_collecte,
                'data_missing': data_missing,
                'response_time_ms': response_time_ms,
                'llm_model': llm_model
            }
            
            result = self.supabase.table('thinking_analytics')\
                .insert(data)\
                .execute()
            
            logger.debug(f"📊 Thinking analytics stocké: type={question_type}, conf={data['confidence_score']}%")
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"❌ Erreur stockage thinking: {e}")
            return None
    
    async def analyze_thinking_patterns(
        self, 
        company_id: str,
        days: int = 7
    ) -> Dict:
        """
        🔍 Analyse les patterns dans les thinking des X derniers jours
        
        Returns:
            Analytics agrégées: questions fréquentes, données manquantes, etc.
        """
        if not self.supabase:
            return {}
        
        try:
            result = self.supabase.rpc('analyze_thinking_patterns', {
                'p_company_id': company_id,
                'p_days': days
            }).execute()
            
            analytics = result.data or {}
            logger.info(f"🔍 Analyse thinking: {analytics.get('total_conversations', 0)} conversations")
            return analytics
            
        except Exception as e:
            logger.error(f"❌ Erreur analyse thinking: {e}")
            return {}
    
    def _classify_question_type(self, thinking_data: Dict) -> str:
        """Classifie le type de question depuis le thinking"""
        intentions = thinking_data.get('intentions', {})
        
        # Trouver intention principale (score max)
        if not intentions:
            return 'general'
        
        max_intent = max(intentions.items(), key=lambda x: x[1])
        intent_name, score = max_intent
        
        if score < 50:
            return 'general'
        
        # Mapping intentions → types
        intent_mapping = {
            'demande_prix': 'prix',
            'demande_livraison': 'livraison',
            'demande_produit': 'produit',
            'demande_contact': 'contact',
            'demande_paiement': 'paiement'
        }
        
        return intent_mapping.get(intent_name, 'autre')
    
    # ========================================
    # 3. DOCUMENT INTELLIGENCE
    # ========================================
    
    async def track_document_usage(
        self,
        company_id: str,
        document_id: str,
        was_used_by_llm: bool,
        document_source: str = 'meilisearch'
    ):
        """
        📈 Track si un document a été réellement utilisé par le LLM
        
        Args:
            document_id: ID du document
            was_used_by_llm: True si contenu utilisé dans réponse
            document_source: 'meilisearch', 'supabase', 'regex'
        """
        if not self.supabase:
            return
        
        try:
            # Get current stats
            current = self.supabase.table('document_intelligence')\
                .select('times_retrieved, times_used_by_llm')\
                .eq('company_id', company_id)\
                .eq('document_id', document_id)\
                .execute()
            
            if current.data and len(current.data) > 0:
                # Update existing
                times_retrieved = current.data[0]['times_retrieved'] + 1
                times_used = current.data[0]['times_used_by_llm'] + (1 if was_used_by_llm else 0)
            else:
                # Create new
                times_retrieved = 1
                times_used = 1 if was_used_by_llm else 0
            
            # Upsert
            self.supabase.table('document_intelligence').upsert({
                'company_id': company_id,
                'document_id': document_id,
                'document_source': document_source,
                'times_retrieved': times_retrieved,
                'times_used_by_llm': times_used,
                'last_used_at': datetime.utcnow().isoformat()
            }, on_conflict='company_id,document_id').execute()
            
            usage_rate = times_used / times_retrieved if times_retrieved > 0 else 0
            logger.debug(f"📈 Doc tracked: {document_id[:20]}... usage_rate={usage_rate:.2%}")
            
        except Exception as e:
            logger.error(f"❌ Erreur track document: {e}")
    
    async def get_top_documents(self, company_id: str, limit: int = 10) -> List[Dict]:
        """
        🏆 Récupère les documents les plus utiles
        
        Returns:
            Liste documents triés par taux d'utilisation
        """
        if not self.supabase:
            return []
        
        try:
            result = self.supabase.rpc('get_top_documents', {
                'p_company_id': company_id,
                'p_limit': limit
            }).execute()
            
            docs = result.data or []
            logger.info(f"🏆 Top {len(docs)} documents les plus utiles")
            return docs
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération top docs: {e}")
            return []
    
    # ========================================
    # 4. LLM PERFORMANCE TRACKING
    # ========================================
    
    async def track_llm_performance(
        self,
        company_id: str,
        llm_model: str,
        task_type: str,
        response_time_ms: int,
        cost: float,
        success: bool,
        parameters: Dict = None
    ):
        """
        📊 Track performance d'un LLM sur une tâche
        
        Args:
            llm_model: ex: 'llama-3.3-70b-versatile'
            task_type: 'prix', 'livraison', 'produit', 'general'
            success: True si confiance > 80%
        """
        if not self.supabase:
            return
        
        try:
            # Get current stats
            current = self.supabase.table('llm_performance')\
                .select('*')\
                .eq('company_id', company_id)\
                .eq('llm_model', llm_model)\
                .eq('task_type', task_type)\
                .execute()
            
            if current.data and len(current.data) > 0:
                # Calculate new averages
                stats = current.data[0]
                total = stats['total_requests']
                new_total = total + 1
                
                new_success_rate = (
                    (stats['success_rate'] * total + (1 if success else 0)) / new_total
                )
                new_avg_time = (
                    (stats['avg_response_time_ms'] * total + response_time_ms) / new_total
                )
                new_avg_cost = (
                    (stats['avg_cost'] * total + cost) / new_total
                )
                
                # Update
                self.supabase.table('llm_performance').update({
                    'success_rate': new_success_rate,
                    'avg_response_time_ms': int(new_avg_time),
                    'avg_cost': new_avg_cost,
                    'total_requests': new_total,
                    'parameters': parameters or {},
                    'updated_at': datetime.utcnow().isoformat()
                }).eq('id', stats['id']).execute()
                
            else:
                # Insert new
                self.supabase.table('llm_performance').insert({
                    'company_id': company_id,
                    'llm_model': llm_model,
                    'task_type': task_type,
                    'success_rate': 1.0 if success else 0.0,
                    'avg_response_time_ms': response_time_ms,
                    'avg_cost': cost,
                    'total_requests': 1,
                    'parameters': parameters or {}
                }).execute()
            
            logger.debug(f"📊 LLM perf tracked: {llm_model} on {task_type}")
            
        except Exception as e:
            logger.error(f"❌ Erreur track LLM: {e}")
    
    async def get_best_llm_for_task(self, company_id: str, task_type: str) -> str:
        """
        🎯 Retourne le meilleur LLM pour une tâche donnée
        
        Critères: success_rate > response_time
        
        Returns:
            Nom du modèle LLM optimal
        """
        if not self.supabase:
            return 'llama-3.3-70b-versatile'  # Default
        
        try:
            result = self.supabase.rpc('get_best_llm_for_task', {
                'p_company_id': company_id,
                'p_task_type': task_type
            }).execute()
            
            if result.data and len(result.data) > 0:
                best_llm = result.data[0]['llm_model']
                logger.info(f"🎯 Meilleur LLM pour {task_type}: {best_llm}")
                return best_llm
            else:
                return 'llama-3.3-70b-versatile'  # Default
            
        except Exception as e:
            logger.error(f"❌ Erreur sélection LLM: {e}")
            return 'llama-3.3-70b-versatile'
    
    # ========================================
    # 5. AUTO-IMPROVEMENTS
    # ========================================
    
    async def create_auto_improvement(
        self,
        company_id: str,
        improvement_type: str,
        recommendation: str,
        evidence: Dict,
        impact_level: str = 'MEDIUM'
    ) -> Optional[Dict]:
        """
        💡 Crée une recommandation d'amélioration automatique
        
        Args:
            improvement_type: 'pattern', 'prompt', 'llm_switch', 'doc_boost'
            recommendation: Description de l'amélioration
            evidence: Preuves/métriques justifiant
            impact_level: 'HIGH', 'MEDIUM', 'LOW'
        """
        if not self.supabase:
            return None
        
        try:
            data = {
                'company_id': company_id,
                'improvement_type': improvement_type,
                'recommendation': recommendation,
                'evidence': evidence,
                'impact_level': impact_level,
                'status': 'pending'
            }
            
            result = self.supabase.table('auto_improvements')\
                .insert(data)\
                .execute()
            
            logger.info(f"💡 Amélioration suggérée [{impact_level}]: {recommendation[:50]}...")
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"❌ Erreur création amélioration: {e}")
            return None
    
    async def get_pending_improvements(self, company_id: str) -> List[Dict]:
        """
        📋 Récupère les améliorations en attente de validation
        """
        if not self.supabase:
            return []
        
        try:
            result = self.supabase.table('auto_improvements')\
                .select('*')\
                .eq('company_id', company_id)\
                .eq('status', 'pending')\
                .order('impact_level', desc=True)\
                .order('created_at', desc=True)\
                .execute()
            
            improvements = result.data or []
            logger.info(f"📋 {len(improvements)} améliorations en attente")
            return improvements
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération améliorations: {e}")
            return []
    
    # ========================================
    # 6. AUTO-GENERATED FAQ
    # ========================================
    
    async def generate_faq_suggestions(
        self, 
        company_id: str,
        min_occurrences: int = 5
    ) -> List[Dict]:
        """
        🤖 Génère suggestions de FAQ depuis questions fréquentes
        
        Args:
            min_occurrences: Min d'occurrences pour considérer
        """
        if not self.supabase:
            return []
        
        try:
            result = self.supabase.rpc('auto_generate_faq_suggestions', {
                'p_company_id': company_id,
                'p_min_occurrences': min_occurrences
            }).execute()
            
            faqs = result.data or []
            logger.info(f"🤖 {len(faqs)} suggestions FAQ générées")
            return faqs
            
        except Exception as e:
            logger.error(f"❌ Erreur génération FAQ: {e}")
            return []


# ========================================
# SINGLETON GLOBAL
# ========================================
_learning_engine_instance = None

def get_learning_engine() -> SupabaseLearningEngine:
    """
    Retourne l'instance globale du moteur d'apprentissage (singleton)
    """
    global _learning_engine_instance
    if _learning_engine_instance is None:
        _learning_engine_instance = SupabaseLearningEngine()
    return _learning_engine_instance


# ========================================
# FONCTIONS UTILITAIRES
# ========================================
async def quick_store_pattern(company_id: str, pattern_name: str, pattern_regex: str, category: str):
    """Shortcut pour stocker un pattern"""
    engine = get_learning_engine()
    return await engine.store_learned_pattern(company_id, pattern_name, pattern_regex, category)

async def quick_get_patterns(company_id: str) -> List[Dict]:
    """Shortcut pour récupérer patterns"""
    engine = get_learning_engine()
    return await engine.get_active_patterns(company_id)

async def quick_track_thinking(company_id: str, user_id: str, thinking: Dict, time_ms: int, model: str):
    """Shortcut pour tracker thinking"""
    engine = get_learning_engine()
    return await engine.store_thinking_analytics(company_id, user_id, thinking, time_ms, model)
