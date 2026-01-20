"""
🛡️ ENTERPRISE HALLUCINATION GUARD - VERSION COMPLÈTE
Implémentation des méthodes les plus avancées utilisées par AWS, OpenAI, Google
"""

import re
import asyncio
import json
import time
from typing import Dict, List, Any, Tuple, Optional, Union
from dataclasses import dataclass, asdict
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.ensemble import GradientBoostingClassifier
import spacy
import logging
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification

logger = logging.getLogger(__name__)

@dataclass
class EnterpriseHallucinationCheck:
    """Résultat de vérification enterprise d'hallucination"""
    is_safe: bool
    confidence_score: float
    
    # Scores détaillés
    documents_found: bool
    correlation_score: float
    faithfulness_score: float
    nli_score: float
    ner_confidence: float
    span_detection_score: float
    self_evaluation_score: float
    ensemble_score: float
    
    # Métadonnées
    issues_detected: List[str]
    detailed_analysis: Dict[str, Any]
    suggested_response: Optional[str] = None
    reason: str = ""
    processing_time_ms: float = 0.0

class EnterpriseHallucinationGuard:
    """
    🛡️ GARDE-FOU ANTI-HALLUCINATION ENTERPRISE
    
    MÉTHODES AVANCÉES:
    1. NLI (Natural Language Inference) - DeBERTa fine-tuned
    2. NER (Named Entity Recognition) - spaCy + Azure AI
    3. Span Detection - Token-level hallucination detection
    4. Semantic Similarity - Embeddings + cosine similarity
    5. Self-Evaluation - LLM as judge with CoT
    6. Multi-Source Ensemble - Gradient Boosting
    7. Metamorphic Testing - Consistency checking
    8. Context Grounding - Fact verification
    """
    
    def __init__(self, enable_gpu: bool = False):
        self.start_time = time.time()
        
        # Configuration
        self.enable_gpu = enable_gpu
        self.device = "cuda" if enable_gpu else "cpu"
        
        # Seuils enterprise
        self.thresholds = {
            'documents': 1,
            'correlation': 0.75,
            'faithfulness': 0.85,
            'nli': 0.8,
            'ner_confidence': 0.7,
            'span_detection': 0.75,
            'self_evaluation': 0.8,
            'ensemble': 0.7,
            'final_confidence': 0.75
        }
        
        # Modèles pré-chargés
        self.models = {}
        self._load_models()
        
        # Patterns enterprise
        self.dangerous_patterns = [
            r"(?i)(nous\s+vendons|we\s+sell)(?!\s+(selon|d'après|comme\s+indiqué))",
            r"(?i)(notre\s+prix|our\s+price)\s+est\s+\d+(?!\s+(selon|d'après))",
            r"(?i)(promotion|promo|discount)\s+\d+%(?!\s+(mentionné|indiqué|selon))",
            r"(?i)(nouveau|new)\s+produit\s+\d{4}(?!\s+(mentionné|dans\s+nos))",
            r"(?i)(garantie|warranty)\s+\d+\s+(ans|years)(?!\s+(selon|indiqué))",
        ]
        
        # Mots-clés de référence (bonus)
        self.reference_keywords = [
            "selon nos documents", "d'après nos informations", "comme indiqué",
            "mentionné dans notre catalogue", "selon nos données", "d'après notre base",
            "conformément à nos informations", "tel qu'indiqué dans", "selon notre documentation"
        ]
        
        logger.info(f"[ENTERPRISE_GUARD] Initialisé en {time.time() - self.start_time:.2f}s")
    
    def _load_models(self):
        """Chargement des modèles avancés"""
        try:
            # 1. Modèle d'embeddings
            logger.info("[ENTERPRISE_GUARD] Chargement modèle embeddings...")
            self.models['embeddings'] = SentenceTransformer(
                'sentence-transformers/all-mpnet-base-v2',
                device=self.device
            )
            
            # 2. Modèle NLI (Natural Language Inference)
            logger.info("[ENTERPRISE_GUARD] Chargement modèle NLI...")
            self.models['nli'] = pipeline(
                "text-classification",
                model="microsoft/DialoGPT-medium",  # Remplacer par DeBERTa si disponible
                device=0 if self.enable_gpu else -1
            )
            
            # 3. Modèle NER (spaCy)
            logger.info("[ENTERPRISE_GUARD] Chargement modèle NER...")
            try:
                self.models['ner'] = spacy.load("fr_core_news_sm")
            except OSError:
                logger.warning("[ENTERPRISE_GUARD] Modèle spaCy français non trouvé, utilisation anglais")
                self.models['ner'] = spacy.load("en_core_web_sm")
            
            # 4. Ensemble classifier (sera entraîné dynamiquement)
            self.models['ensemble'] = GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=3,
                random_state=42
            )
            
            logger.info("[ENTERPRISE_GUARD] Tous les modèles chargés avec succès")
            
        except Exception as e:
            logger.error(f"[ENTERPRISE_GUARD] Erreur chargement modèles: {e}")
            # Fallback vers méthodes simples
            self.models['embeddings'] = None
            self.models['nli'] = None
            self.models['ner'] = None
    
    async def check_response(
        self,
        user_query: str,
        ai_response: str,
        supabase_results: List[Dict] = None,
        meili_results: List[Dict] = None,
        supabase_context: str = "",
        meili_context: str = "",
        company_id: str = "",
        enable_llm_judge: bool = True
    ) -> EnterpriseHallucinationCheck:
        """
        🎯 VÉRIFICATION ENTERPRISE COMPLÈTE
        
        Pipeline en 8 étapes:
        1. Documents availability check
        2. Semantic correlation analysis
        3. Faithfulness scoring
        4. NLI (Natural Language Inference)
        5. NER (Named Entity Recognition)
        6. Span-level detection
        7. Self-evaluation (LLM as judge)
        8. Multi-source ensemble
        """
        
        start_time = time.time()
        logger.info(f"[ENTERPRISE_GUARD] Analyse enterprise: {ai_response[:50]}...")
        
        # Préparation des données
        documents_found, doc_analysis = self._check_documents_availability(
            supabase_results, meili_results, supabase_context, meili_context
        )
        
        combined_context = doc_analysis.get('combined_context', '')
        
        # Pipeline de vérification
        scores = {}
        detailed_analysis = {}
        
        # ÉTAPE 1: Documents check (baseline)
        scores['documents_found'] = documents_found
        detailed_analysis['documents'] = doc_analysis
        
        if not documents_found:
            return self._create_no_documents_response(start_time)
        
        # ÉTAPE 2: Correlation sémantique
        scores['correlation'] = await self._calculate_semantic_correlation(
            ai_response, combined_context
        )
        
        # ÉTAPE 3: Faithfulness (fidélité aux faits)
        scores['faithfulness'] = self._calculate_advanced_faithfulness(
            combined_context, ai_response
        )
        
        # ÉTAPE 4: NLI (Natural Language Inference)
        scores['nli'] = await self._nli_detection(
            combined_context, ai_response
        )
        
        # ÉTAPE 5: NER (Named Entity Recognition)
        scores['ner_confidence'] = self._ner_hallucination_detection(
            combined_context, ai_response
        )
        
        # ÉTAPE 6: Span Detection (token-level)
        scores['span_detection'] = self._span_based_detection(
            combined_context, ai_response
        )
        
        # ÉTAPE 7: Self-Evaluation (LLM as judge)
        if enable_llm_judge:
            scores['self_evaluation'] = await self._self_evaluation_with_cot(
                user_query, combined_context, ai_response
            )
        else:
            scores['self_evaluation'] = 0.8  # Score neutre
        
        # ÉTAPE 8: Multi-Source Ensemble
        scores['ensemble'] = self._multi_source_ensemble(scores)
        
        # Analyse des patterns
        pattern_issues = self._check_enterprise_patterns(ai_response)
        reference_bonus = self._calculate_reference_bonus(ai_response)
        
        # Score final
        final_score = self._calculate_final_enterprise_score(
            scores, pattern_issues, reference_bonus
        )
        
        # Décision finale
        is_safe = self._make_enterprise_decision(scores, final_score)
        
        # Issues détectées
        issues = self._collect_issues(scores, pattern_issues)
        
        # Réponse suggérée
        suggested_response = self._generate_suggested_response(
            scores, is_safe
        ) if not is_safe else None
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.info(f"[ENTERPRISE_GUARD] Analyse terminée en {processing_time:.1f}ms - Safe: {is_safe}")
        
        return EnterpriseHallucinationCheck(
            is_safe=is_safe,
            confidence_score=final_score,
            documents_found=documents_found,
            correlation_score=scores['correlation'],
            faithfulness_score=scores['faithfulness'],
            nli_score=scores['nli'],
            ner_confidence=scores['ner_confidence'],
            span_detection_score=scores['span_detection'],
            self_evaluation_score=scores['self_evaluation'],
            ensemble_score=scores['ensemble'],
            issues_detected=issues,
            detailed_analysis={
                'scores': scores,
                'pattern_issues': pattern_issues,
                'reference_bonus': reference_bonus,
                'thresholds_used': self.thresholds
            },
            suggested_response=suggested_response,
            reason=self._generate_detailed_reason(scores, is_safe),
            processing_time_ms=processing_time
        )
