"""
🛡️ GARDE-FOU ANTI-HALLUCINATION INTELLIGENT
Architecture simplifiée basée sur l'intention + LLM Juge unique
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from core.intention_router import intention_router
from core.llm_client import GroqLLMClient

logger = logging.getLogger(__name__)

@dataclass
class IntelligentHallucinationCheck:
    """Résultat de vérification intelligente d'hallucination"""
    is_safe: bool
    confidence_score: float
    intention_detected: str
    search_required: bool
    documents_found: bool
    judge_decision: str
    reason: str
    processing_time_ms: float
    suggested_response: Optional[str] = None

class IntelligentHallucinationGuard:
    """
    🛡️ GARDE-FOU ANTI-HALLUCINATION INTELLIGENT
    
    NOUVELLE ARCHITECTURE SIMPLIFIÉE:
    1. 🧠 Détection d'intention (détermine si recherche nécessaire)
    2. 🎯 Routage intelligent (évite recherches inutiles)
    3. ⚖️ LLM Juge unique (validation basée sur l'intention)
    """
    
    def __init__(self):
        self.llm_client = GroqLLMClient()
        
        # Types d'intentions et leurs besoins en documents
        self.intention_requirements = {
            # Intentions qui NÉCESSITENT des documents
            'product_catalog': {'requires_docs': True, 'critical': True},
            'pricing_info': {'requires_docs': True, 'critical': True},
            'delivery_info': {'requires_docs': True, 'critical': True},
            'support_contact': {'requires_docs': True, 'critical': False},
            'company_identity': {'requires_docs': True, 'critical': False},
            
            # Intentions qui N'ONT PAS BESOIN de documents
            'social_greeting': {'requires_docs': False, 'critical': False},
            'general_conversation': {'requires_docs': False, 'critical': False},
            'politeness': {'requires_docs': False, 'critical': False},
            'off_topic': {'requires_docs': False, 'critical': False}
        }
        
        # Cache des décisions du juge
        self.judge_cache = {}
        self.cache_ttl = 3600  # 1 heure
    
    def analyze_search_necessity(self, intentions_result) -> Dict[str, Any]:
        """
        🎯 ANALYSE SI UNE RECHERCHE EST NÉCESSAIRE
        Basé sur les intentions détectées
        """
        if not intentions_result or not intentions_result.intentions:
            # Pas d'intention claire → recherche par sécurité
            return {
                'search_required': True,
                'reason': 'Intention non détectée',
                'critical_level': 'medium'
            }
        
        primary_intention = intentions_result.primary
        
        # Vérifier si l'intention nécessite des documents
        intention_config = self.intention_requirements.get(primary_intention, {
            'requires_docs': True, 
            'critical': True
        })
        
        search_required = intention_config['requires_docs']
        critical_level = 'high' if intention_config['critical'] else 'low'
        
        logger.info(f"[INTELLIGENT_GUARD] Intention: {primary_intention}, Recherche requise: {search_required}")
        
        return {
            'search_required': search_required,
            'reason': f"Intention '{primary_intention}' {'nécessite' if search_required else 'ne nécessite pas'} de documents",
            'critical_level': critical_level,
            'primary_intention': primary_intention
        }
    
    def create_intelligent_judge_prompt(
        self, 
        user_query: str, 
        ai_response: str, 
        intention: str,
        search_was_required: bool,
        documents_found: bool,
        context: str = ""
    ) -> str:
        """
        🧠 PROMPT INTELLIGENT POUR LE JUGE LLM
        Adapté selon l'intention détectée
        """
        
        if not search_was_required:
            # Cas social/conversationnel - validation allégée
            return f"""Tu es un juge expert pour valider les réponses conversationnelles.

CONTEXTE:
- Question utilisateur: "{user_query}"
- Intention détectée: {intention}
- Type: Conversation sociale (pas de recherche de documents nécessaire)

RÉPONSE À JUGER:
{ai_response}

CRITÈRES DE VALIDATION:
1. La réponse est-elle appropriée et polie ?
2. Reste-t-elle dans le contexte d'un assistant commercial ?
3. N'invente-t-elle pas de fausses informations ?

DÉCISION: Réponds UNIQUEMENT par:
- "ACCEPTER" si la réponse est appropriée
- "REJETER: [raison]" si elle est inappropriée ou invente des faits"""

        else:
            # Cas nécessitant des documents - validation stricte
            doc_status = "DOCUMENTS TROUVÉS" if documents_found else "AUCUN DOCUMENT TROUVÉ"
            
            return f"""Tu es un juge expert anti-hallucination TRÈS STRICT.

CONTEXTE:
- Question utilisateur: "{user_query}"
- Intention détectée: {intention}
- Status documents: {doc_status}
- Type: Requête nécessitant des informations précises

RÉPONSE À JUGER:
{ai_response}

DOCUMENTS DE RÉFÉRENCE:
{context[:800] if context else "AUCUN DOCUMENT DISPONIBLE"}

CRITÈRES STRICTS:
1. Si AUCUN DOCUMENT: la réponse doit rediriger vers le service client
2. Si DOCUMENTS TROUVÉS: tous les faits doivent être dans les documents
3. AUCUNE invention de prix, stock, ou détails techniques
4. Les chiffres doivent être exacts

DÉCISION: Réponds UNIQUEMENT par:
- "ACCEPTER" si la réponse est fidèle aux documents
- "REJETER: [raison précise]" si elle invente ou déforme des informations

Sois IMPITOYABLE - en cas de doute, REJETER."""

    async def evaluate_response(
        self,
        user_query: str,
        ai_response: str,
        company_id: str,
        supabase_results: List[Dict] = None,
        meili_results: List[Dict] = None,
        supabase_context: str = "",
        meili_context: str = ""
    ) -> IntelligentHallucinationCheck:
        """
        🎯 ÉVALUATION INTELLIGENTE COMPLÈTE
        
        Pipeline simplifié:
        1. Détection d'intention
        2. Analyse nécessité de recherche
        3. Validation par LLM Juge intelligent
        """
        start_time = time.time()
        
        logger.info(f"[INTELLIGENT_GUARD] 🛡️ Analyse: {ai_response[:50]}...")
        
        # ÉTAPE 1: Détection d'intention
        intentions_result = intention_router.detect_intentions(user_query)
        primary_intention = intentions_result.primary if intentions_result else "unknown"
        
        # ÉTAPE 2: Analyser si recherche était nécessaire
        search_analysis = self.analyze_search_necessity(intentions_result)
        search_required = search_analysis['search_required']
        
        # ÉTAPE 3: Vérifier si des documents ont été trouvés
        documents_found = bool(
            (supabase_results and len(supabase_results) > 0) or
            (meili_results and len(meili_results) > 0) or
            (supabase_context and len(supabase_context.strip()) > 10) or
            (meili_context and len(meili_context.strip()) > 10)
        )
        
        # ÉTAPE 4: Validation par LLM Juge intelligent
        combined_context = f"{supabase_context}\n{meili_context}".strip()
        
        judge_prompt = self.create_intelligent_judge_prompt(
            user_query=user_query,
            ai_response=ai_response,
            intention=primary_intention,
            search_was_required=search_required,
            documents_found=documents_found,
            context=combined_context
        )
        
        try:
            # Appel du juge LLM
            judge_response = await self.llm_client.complete(
                prompt=judge_prompt,
                temperature=0.0,  # Déterministe pour la validation
                max_tokens=100
            )
            
            # Analyser la décision
            is_accepted = "ACCEPTER" in judge_response.upper()
            judge_decision = judge_response.strip()
            
            # Calcul du score de confiance
            if is_accepted:
                confidence_score = 0.9 if documents_found or not search_required else 0.7
            else:
                confidence_score = 0.1
            
            # Réponse suggérée si rejetée
            suggested_response = None
            if not is_accepted:
                if search_required and not documents_found:
                    suggested_response = "Je n'ai pas d'informations précises sur ce point. Contactez notre service client pour plus de détails."
                elif search_required:
                    suggested_response = "D'après nos informations disponibles, je ne peux pas confirmer ces détails. Veuillez nous contacter directement."
            
            processing_time = (time.time() - start_time) * 1000
            
            logger.info(f"[INTELLIGENT_GUARD] ✅ Décision: {'ACCEPTER' if is_accepted else 'REJETER'} en {processing_time:.1f}ms")
            
            return IntelligentHallucinationCheck(
                is_safe=is_accepted,
                confidence_score=confidence_score,
                intention_detected=primary_intention,
                search_required=search_required,
                documents_found=documents_found,
                judge_decision=judge_decision,
                reason=f"Intention: {primary_intention}, Recherche: {'requise' if search_required else 'non requise'}, Documents: {'trouvés' if documents_found else 'absents'}",
                processing_time_ms=processing_time,
                suggested_response=suggested_response
            )
            
        except Exception as e:
            logger.error(f"[INTELLIGENT_GUARD] Erreur juge LLM: {e}")
            processing_time = (time.time() - start_time) * 1000
            
            return IntelligentHallucinationCheck(
                is_safe=False,
                confidence_score=0.0,
                intention_detected=primary_intention,
                search_required=search_required,
                documents_found=documents_found,
                judge_decision=f"ERREUR: {str(e)}",
                reason=f"Erreur lors de l'évaluation: {str(e)}",
                processing_time_ms=processing_time,
                suggested_response="Une erreur s'est produite. Veuillez réessayer ou contacter notre service client."
            )
    
    def should_skip_search(self, user_query: str, company_id: str) -> bool:
        """
        🎯 DÉCIDER SI ON PEUT ÉVITER LA RECHERCHE
        Optimisation basée sur l'intention
        """
        try:
            intentions_result = intention_router.detect_intentions(user_query)
            search_analysis = self.analyze_search_necessity(intentions_result)
            
            should_skip = not search_analysis['search_required']
            
            if should_skip:
                logger.info(f"[INTELLIGENT_GUARD] 🚀 Recherche évitée pour: {user_query[:30]}...")
            
            return should_skip
            
        except Exception as e:
            logger.error(f"[INTELLIGENT_GUARD] Erreur analyse intention: {e}")
            return False  # Par sécurité, faire la recherche
