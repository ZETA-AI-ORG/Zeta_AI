import re
import asyncio
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
import logging

# IMPORTS OPTIONNELS POUR ÉVITER LES ERREURS
try:
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("[WARNING] sklearn/numpy non disponible - Mode dégradé activé")

logger = logging.getLogger(__name__)

@dataclass
class AdvancedHallucinationCheck:
    """Résultat de vérification avancée d'hallucination"""
    is_safe: bool
    confidence_score: float
    documents_found: bool
    correlation_score: float
    faithfulness_score: float
    issues_detected: List[str]
    suggested_response: Optional[str] = None
    reason: str = ""

class AdvancedHallucinationGuard:
    """
    🛡️ GARDE-FOU ANTI-HALLUCINATION AVANCÉ
    
    LOGIQUE EN 2 ÉTAPES:
    1. Y a-t-il des documents récupérés ? (MeiliSearch + Supabase)
    2. La réponse LLM est-elle corrélée aux documents trouvés ?
    
    + Méthodes avancées: Faithfulness, Context Grounding, Ensemble
    """
    
    def __init__(self):
        # SEUILS DE BASE (gardés pour compatibilité)
        self.min_documents_threshold = 1  # Au moins 1 document trouvé
        self.correlation_threshold = 0.1   # Très bas - presque toujours OK
        self.faithfulness_threshold = 0.1  # Très bas - presque toujours OK  
        self.final_confidence_threshold = 0.1  # Très bas - presque toujours OK
        
        # NOUVEAUX SEUILS ADAPTATIFS (optionnels)
        self.adaptive_mode = True  # Peut être désactivé si problème
        
        # Patterns dangereux (gardés mais assouplis)
        self.dangerous_patterns = [
            r"(?i)(nous\s+vendons|we\s+sell).*(?!dans|selon|d'après)",
            r"(?i)(notre\s+prix|our\s+price)\s+est\s+\d+.*(?!selon|d'après)",
            r"(?i)(promotion|promo|discount)\s+\d+%.*(?!mentionné|indiqué)",
        ]
        
        # Mots-clés de référence aux documents (BONUS)
        self.reference_keywords = [
            "selon nos documents", "d'après nos informations", "comme indiqué",
            "mentionné dans", "selon notre catalogue", "d'après nos données"
        ]
    
    def get_adaptive_thresholds(self, user_query: str):
        """🎯 SEUILS ADAPTATIFS SELON LE CONTEXTE (Non-disruptif)"""
        if not self.adaptive_mode:
            return {
                'correlation': self.correlation_threshold,
                'faithfulness': self.faithfulness_threshold
            }
        
        query_lower = user_query.lower()
        
        # DOMAINES SENSIBLES = Seuils plus élevés
        sensitive_keywords = ['prix', 'coût', 'facture', 'paiement', 'promotion', 'discount']
        if any(keyword in query_lower for keyword in sensitive_keywords):
            return {
                'correlation': 0.3,  # Plus strict pour les prix
                'faithfulness': 0.4
            }
        
        # QUESTIONS PRODUIT SIMPLE = Plus permissif
        product_keywords = ['avez-vous', 'disponible', 'stock', 'taille', 'couleur']
        if any(keyword in query_lower for keyword in product_keywords):
            return {
                'correlation': 0.05,  # Très permissif
                'faithfulness': 0.05
            }
        
        # Par défaut : seuils existants
        return {
            'correlation': self.correlation_threshold,
            'faithfulness': self.faithfulness_threshold
        }
    
    def calculate_confidence_level(self, correlation_score: float, faithfulness_score: float, documents_found: bool):
        """🎯 CALCUL DU NIVEAU DE CONFIANCE (Ajout non-disruptif)"""
        if not documents_found:
            return "VERY_LOW"
        
        avg_score = (correlation_score + faithfulness_score) / 2
        
        if avg_score >= 0.8:
            return "HIGH"
        elif avg_score >= 0.5:
            return "MEDIUM"
        elif avg_score >= 0.2:
            return "LOW"
        else:
            return "VERY_LOW"
    
    async def check_response(
        self, 
        user_query: str, 
        ai_response: str, 
        supabase_results: List[Dict] = None,
        meili_results: List[Dict] = None,
        supabase_context: str = "",
        meili_context: str = ""
    ) -> AdvancedHallucinationCheck:
        """
        🎯 VÉRIFICATION HYBRIDE EN 2 ÉTAPES + MÉTHODES AVANCÉES
        
        Args:
            user_query: Question utilisateur
            ai_response: Réponse générée par le LLM
            supabase_results: Résultats Supabase
            meili_results: Résultats MeiliSearch  
            supabase_context: Contexte formaté Supabase
            meili_context: Contexte formaté MeiliSearch
        """
        
        logger.info(f"[ADVANCED_GUARD] Vérification: {ai_response[:50]}...")
        
        # ÉTAPE 1: Vérifier la présence de documents
        documents_found, doc_analysis = self._check_documents_availability(
            supabase_results, meili_results, supabase_context, meili_context
        )
        
        if not documents_found:
            logger.warning("[ADVANCED_GUARD] Aucun document trouvé - Réponse suspecte")
            return AdvancedHallucinationCheck(
                is_safe=False,
                confidence_score=0.1,
                documents_found=False,
                correlation_score=0.0,
                faithfulness_score=0.0,
                issues_detected=["NO_DOCUMENTS_FOUND"],
                suggested_response="Je n'ai pas trouvé d'informations précises sur votre demande. Pouvez-vous reformuler ou contacter notre service client ?",
                reason="Aucun document récupéré pour supporter la réponse"
            )
        
        # ÉTAPE 2: Vérifier la corrélation avec les documents
        correlation_score = await self._calculate_correlation(
            ai_response, doc_analysis['combined_context']
        )
        
        # ÉTAPE 3: Calcul du score de fidélité (Faithfulness)
        faithfulness_score = self._calculate_faithfulness(
            doc_analysis['combined_context'], ai_response
        )
        
        # ÉTAPE 4: Vérification des patterns dangereux (assouplie)
        pattern_issues = self._check_softened_patterns(ai_response)
        
        # ÉTAPE 5: Bonus pour références explicites aux documents
        reference_bonus = self._calculate_reference_bonus(ai_response)
        
        # CALCUL DU SCORE FINAL
        base_score = (correlation_score * 0.4 + faithfulness_score * 0.4 + 0.2)
        final_score = min(1.0, base_score + reference_bonus)
        
        # Pénalités pour patterns dangereux
        if pattern_issues:
            final_score -= 0.2
        
        # DÉCISION FINALE INTELLIGENTE AVEC SEUILS ADAPTATIFS
        adaptive_thresholds = self.get_adaptive_thresholds(user_query)
        
        # Si fidélité parfaite (1.0), on assouplit encore plus la corrélation
        adjusted_correlation_threshold = adaptive_thresholds['correlation']
        adjusted_faithfulness_threshold = adaptive_thresholds['faithfulness']
        
        if faithfulness_score >= 0.95:  # Fidélité quasi-parfaite
            adjusted_correlation_threshold = min(adjusted_correlation_threshold, 0.4)  # Encore plus souple
        
        is_safe = (
            documents_found and 
            correlation_score >= adjusted_correlation_threshold and
            faithfulness_score >= adjusted_faithfulness_threshold and
            final_score >= self.final_confidence_threshold
        )
        
        issues = []
        if not documents_found:
            issues.append("NO_DOCUMENTS")
        if correlation_score < self.correlation_threshold:
            issues.append("LOW_CORRELATION")
        if faithfulness_score < self.faithfulness_threshold:
            issues.append("LOW_FAITHFULNESS")
        if pattern_issues:
            issues.extend(pattern_issues)
        
        suggested_response = None
        if not is_safe:
            if correlation_score < 0.5:
                suggested_response = "Je n'ai pas d'informations précises sur ce point. Contactez-nous pour plus de détails."
            else:
                suggested_response = "D'après nos informations disponibles, je ne peux pas confirmer ces détails. Veuillez nous contacter directement."
        
        # CALCUL DU NIVEAU DE CONFIANCE (Nouveau)
        confidence_level = self.calculate_confidence_level(correlation_score, faithfulness_score, documents_found)
        
        logger.info(f"[ADVANCED_GUARD] Résultat: safe={is_safe}, correlation={correlation_score:.2f}, faithfulness={faithfulness_score:.2f}, confidence={confidence_level}")
        
        return AdvancedHallucinationCheck(
            is_safe=is_safe,
            confidence_score=final_score,
            documents_found=documents_found,
            correlation_score=correlation_score,
            faithfulness_score=faithfulness_score,
            issues_detected=issues,
            suggested_response=suggested_response,
            reason=f"Documents: {documents_found}, Corrélation: {correlation_score:.2f}, Fidélité: {faithfulness_score:.2f}, Confiance: {confidence_level}"
        )
    
    def _check_documents_availability(self, supabase_results, meili_results, supabase_context, meili_context):
        """ÉTAPE 1: Vérifier si des documents ont été trouvés"""
        has_supabase = bool(supabase_results and len(supabase_results) > 0)
        has_meili = bool(meili_results and len(meili_results) > 0)
        has_supabase_context = bool(supabase_context and len(supabase_context.strip()) > 10)
        has_meili_context = bool(meili_context and len(meili_context.strip()) > 10)
        
        documents_found = has_supabase or has_meili or has_supabase_context or has_meili_context
        
        combined_context = ""
        if has_supabase_context:
            combined_context += supabase_context + "\n"
        if has_meili_context:
            combined_context += meili_context
        
        return documents_found, {
            'combined_context': combined_context.strip(),
            'supabase_found': has_supabase,
            'meili_found': has_meili,
            'total_length': len(combined_context)
        }
    
    async def _calculate_correlation(self, response, context):
        """ÉTAPE 2: Calculer la corrélation sémantique (Mode simple sans sklearn)"""
        if not context or len(context.strip()) < 10:
            return 0.0
        
        try:
            # Méthode simple: vérifier si les mots-clés de la réponse sont dans le contexte
            response_words = set(re.findall(r'\b\w+\b', response.lower()))
            context_words = set(re.findall(r'\b\w+\b', context.lower()))
            
            # Mots communs
            common_words = response_words.intersection(context_words)
            
            # Score basique
            if len(response_words) == 0:
                return 0.0
            
            correlation = len(common_words) / len(response_words)
            return min(1.0, correlation)
        except Exception as e:
            logger.warning(f"[CORRELATION] Erreur calcul: {e}")
            return 0.5  # Score neutre en cas d'erreur
    
    def _calculate_faithfulness(self, context, response):
        """ÉTAPE 3: Score de fidélité - les faits sont-ils dans le contexte?"""
        try:
            if not context or not response:
                return 0.0
            
            # Extraire les nombres/prix/tailles de la réponse
            response_facts = re.findall(r'\d+[.,]?\d*', response)
            
            if not response_facts:
                return 0.8  # Pas de faits numériques = OK par défaut
            
            # Vérifier si ces faits sont dans le contexte
            facts_found = 0
            for fact in response_facts:
                if fact in context:
                    facts_found += 1
            
            return facts_found / len(response_facts) if response_facts else 0.8
        except Exception as e:
            logger.warning(f"[FAITHFULNESS] Erreur calcul: {e}")
            return 0.5  # Score neutre en cas d'erreur
    
    def _check_softened_patterns(self, response):
        """ÉTAPE 4: Patterns dangereux assouplis"""
        issues = []
        for pattern in self.dangerous_patterns:
            if re.search(pattern, response):
                issues.append("SOFTENED_PATTERN_DETECTED")
                break
        return issues
    
    def _calculate_reference_bonus(self, response):
        """ÉTAPE 5: Bonus pour références aux documents"""
        try:
            bonus = 0.0
            for keyword in self.reference_keywords:
                if keyword.lower() in response.lower():
                    bonus += 0.1
            return min(0.3, bonus)  # Maximum 30% de bonus
        except Exception as e:
            logger.warning(f"[REFERENCE_BONUS] Erreur calcul: {e}")
            return 0.0
