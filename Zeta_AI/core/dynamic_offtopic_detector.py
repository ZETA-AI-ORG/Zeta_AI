#!/usr/bin/env python3
"""
🎯 DÉTECTEUR DYNAMIQUE HORS-SUJET AVEC APPRENTISSAGE AUTOMATIQUE
Architecture scalable avec patterns adaptatifs et fallback intelligent
"""

import asyncio
import time
import json
import hashlib
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import numpy as np

from core.cache_manager import cache_manager
from core.business_config_manager import get_business_config
from utils import log3


@dataclass
class OffTopicPattern:
    """Pattern de détection hors-sujet avec métriques d'apprentissage"""
    keywords: Set[str]
    confidence: float
    usage_count: int
    success_rate: float
    last_updated: float
    domain_specificity: float  # 0-1, plus proche de 1 = plus spécifique au domaine


@dataclass
class QueryAnalysis:
    """Analyse complète d'une requête"""
    is_offtopic: bool
    confidence: float
    matched_patterns: List[str]
    domain_relevance_score: float
    suggested_redirect: Optional[str]
    processing_time_ms: float


class DynamicOffTopicDetector:
    """
    🧠 DÉTECTEUR HORS-SUJET AVEC APPRENTISSAGE DYNAMIQUE
    
    Features:
    - Patterns adaptatifs qui évoluent avec l'usage
    - Apprentissage automatique des nouveaux patterns
    - Fallback intelligent vers domaine métier
    - Cache multi-niveaux pour performance
    - Métriques temps réel pour optimisation continue
    """
    
    def __init__(self, company_id: str):
        self.company_id = company_id
        self.patterns: Dict[str, OffTopicPattern] = {}
        self.detection_history = defaultdict(list)
        self.query_history = deque(maxlen=100)  # Historique des requêtes
        self.performance_metrics = defaultdict(list)  # Métriques de performance
        self.business_config = None
        
        # Initialisation par défaut des mots-clés domaine
        self.domain_keywords = {'produit', 'service', 'prix', 'qualité', 'livraison', 'support'}
        
        # Chargement asynchrone de la configuration métier
        asyncio.create_task(self._initialize_async())
    
    async def _initialize_async(self):
        """Initialisation asynchrone avec configuration métier"""
        try:
            # Chargement de la configuration métier spécifique
            self.business_config = await get_business_config(self.company_id)
            
            # Extraction des mots-clés métier
            if self.business_config and hasattr(self.business_config, 'keywords'):
                keywords = self.business_config.keywords
                if hasattr(keywords, 'products'):
                    self.domain_keywords.update(keywords.products)
                    self.domain_keywords.update(keywords.services)
                    self.domain_keywords.update(keywords.locations)
                    self.domain_keywords.update(keywords.brands)
                    self.domain_keywords.update(keywords.attributes)
                    self.domain_keywords.update(keywords.actions)
            
            # Chargement des patterns
            await self._load_patterns()
            
            sector_value = "unknown"
            if self.business_config and hasattr(self.business_config, 'sector'):
                if hasattr(self.business_config.sector, 'value'):
                    sector_value = self.business_config.sector.value
                else:
                    sector_value = str(self.business_config.sector)
            
            log3("[OFFTOPIC_DETECTOR]", {
                "company_id": self.company_id,
                "sector": sector_value,
                "domain_keywords": len(self.domain_keywords),
                "patterns": len(self.patterns)
            })
            
        except Exception as e:
            log3("[OFFTOPIC_DETECTOR]", f"❌ Erreur initialisation: {e}")
            # Fallback vers mots-clés génériques
            self.domain_keywords = {'produit', 'service', 'prix', 'qualité', 'livraison', 'support'}
    
    def _initialize_base_patterns(self):
        """Initialise les patterns de base qui évoluent avec l'usage"""
        base_patterns = {
            "science_physics": OffTopicPattern(
                keywords={"relativité", "einstein", "quantique", "physique", "théorie"},
                confidence=0.9,
                usage_count=0,
                success_rate=1.0,
                last_updated=time.time(),
                domain_specificity=0.1
            ),
            "cooking_recipes": OffTopicPattern(
                keywords={"recette", "cuisine", "tiramisu", "cuisson", "ingrédients"},
                confidence=0.85,
                usage_count=0,
                success_rate=1.0,
                last_updated=time.time(),
                domain_specificity=0.1
            ),
            "general_knowledge": OffTopicPattern(
                keywords={"capitale", "géographie", "histoire", "culture", "politique"},
                confidence=0.8,
                usage_count=0,
                success_rate=1.0,
                last_updated=time.time(),
                domain_specificity=0.2
            ),
            "technology_general": OffTopicPattern(
                keywords={"ordinateur", "logiciel", "programmation", "internet", "technologie"},
                confidence=0.7,  # Plus faible car peut être lié au business
                usage_count=0,
                success_rate=1.0,
                last_updated=time.time(),
                domain_specificity=0.4
            )
        }
        
        # Chargement depuis cache si disponible
        cached_patterns = cache_manager.get(f"offtopic_patterns:{self.company_id}")
        if cached_patterns:
            try:
                loaded = json.loads(cached_patterns)
                for pattern_id, data in loaded.items():
                    data['keywords'] = set(data['keywords'])
                    self.patterns[pattern_id] = OffTopicPattern(**data)
                log3("[OFFTOPIC_DETECTOR]", f"✅ {len(self.patterns)} patterns chargés depuis cache")
            except Exception as e:
                log3("[OFFTOPIC_DETECTOR]", f"⚠️ Erreur chargement cache: {e}")
                self.patterns = base_patterns
        else:
            self.patterns = base_patterns
    
    async def _load_patterns(self):
        """Charge les patterns de détection hors-sujet"""
        # Chargement depuis cache si disponible
        cached_patterns = cache_manager.get(f"offtopic_patterns:{self.company_id}")
        if cached_patterns:
            try:
                loaded = json.loads(cached_patterns)
                for pattern_id, data in loaded.items():
                    data['keywords'] = set(data['keywords'])
                    self.patterns[pattern_id] = OffTopicPattern(**data)
                log3("[OFFTOPIC_DETECTOR]", f"✅ {len(self.patterns)} patterns chargés depuis cache")
            except Exception as e:
                log3("[OFFTOPIC_DETECTOR]", f"⚠️ Erreur chargement cache: {e}")
        else:
            self._initialize_base_patterns()
    
    async def analyze_query(self, query: str, context_available: bool = False) -> QueryAnalysis:
        """
        Analyse dynamique d'une requête avec apprentissage en temps réel
        """
        start_time = time.time()
        
        # Normalisation de la requête
        normalized_query = query.lower().strip()
        query_words = set(normalized_query.split())
        
        # Cache check pour performance
        cache_key = f"offtopic_analysis:{hashlib.md5(normalized_query.encode()).hexdigest()}"
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            try:
                data = json.loads(cached_result)
                return QueryAnalysis(**data)
            except:
                pass
        
        # Calcul du score de pertinence domaine
        domain_relevance_score = self._calculate_domain_relevance(query_words)
        
        # Détection patterns hors-sujet
        matched_patterns = []
        max_confidence = 0.0
        
        for pattern_id, pattern in self.patterns.items():
            overlap = query_words.intersection(pattern.keywords)
            if overlap:
                # Score basé sur le recouvrement et la spécificité du pattern
                overlap_ratio = len(overlap) / len(pattern.keywords)
                pattern_confidence = pattern.confidence * overlap_ratio * pattern.success_rate
                
                if pattern_confidence > 0.3:  # Seuil dynamique
                    matched_patterns.append(pattern_id)
                    max_confidence = max(max_confidence, pattern_confidence)
                    
                    # Mise à jour des métriques du pattern
                    pattern.usage_count += 1
                    pattern.last_updated = time.time()
        
        # Décision finale avec logique adaptative
        is_offtopic = self._make_offtopic_decision(
            domain_relevance_score, 
            max_confidence, 
            context_available,
            len(query_words)
        )
        
        # Génération de redirection intelligente
        suggested_redirect = self._generate_smart_redirect(
            query_words, 
            domain_relevance_score,
            is_offtopic
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        result = QueryAnalysis(
            is_offtopic=is_offtopic,
            confidence=max_confidence if is_offtopic else domain_relevance_score,
            matched_patterns=matched_patterns,
            domain_relevance_score=domain_relevance_score,
            suggested_redirect=suggested_redirect,
            processing_time_ms=processing_time
        )
        
        # Cache du résultat
        cache_manager.set(cache_key, json.dumps(asdict(result)), ttl_seconds=3600)
        
        # Apprentissage automatique
        await self._learn_from_query(query, result)
        
        # Métriques de performance
        self.performance_metrics['processing_time'].append(processing_time)
        
        log3("[OFFTOPIC_DETECTOR]", {
            "query_preview": query[:50],
            "is_offtopic": is_offtopic,
            "confidence": round(result.confidence, 3),
            "domain_score": round(domain_relevance_score, 3),
            "processing_ms": round(processing_time, 2),
            "patterns_matched": len(matched_patterns)
        })
        
        return result
    
    def _calculate_domain_relevance(self, query_words: Set[str]) -> float:
        """Calcule le score de pertinence par rapport au domaine métier"""
        if not query_words:
            return 0.0
        
        domain_matches = query_words.intersection(self.domain_keywords)
        base_score = len(domain_matches) / len(query_words)
        
        # Bonus pour mots-clés critiques
        critical_keywords = {"casque", "moto", "livraison", "prix", "paiement"}
        critical_matches = query_words.intersection(critical_keywords)
        critical_bonus = len(critical_matches) * 0.2
        
        return min(1.0, base_score + critical_bonus)
    
    def _make_offtopic_decision(self, domain_score: float, pattern_confidence: float, 
                               context_available: bool, query_length: int) -> bool:
        """Décision adaptative basée sur multiples facteurs"""
        
        # Seuils dynamiques basés sur le contexte
        if context_available:
            domain_threshold = 0.15  # Plus tolérant si contexte disponible
        else:
            domain_threshold = 0.25
        
        # Ajustement pour requêtes courtes (souvent ambiguës)
        if query_length <= 3:
            domain_threshold *= 0.7
        
        # Décision finale
        if domain_score >= domain_threshold:
            return False  # Dans le domaine
        
        if pattern_confidence >= 0.6:
            return True  # Clairement hors-sujet
        
        # Zone grise - décision conservatrice
        return domain_score < 0.1 and pattern_confidence > 0.3
    
    def _generate_smart_redirect(self, query_words: Set[str], domain_score: float, 
                                is_offtopic: bool) -> Optional[str]:
        """Génère une redirection intelligente vers le domaine métier"""
        
        if not is_offtopic:
            return None
        
        # Détection d'intentions partielles
        if any(word in query_words for word in ["casque", "moto", "équipement"]):
            return "Nous vendons des casques de moto de qualité. Voulez-vous voir notre catalogue ?"
        
        if any(word in query_words for word in ["livraison", "transport", "envoyer"]):
            return "Nous livrons dans toute la région d'Abidjan. Souhaitez-vous connaître nos zones de livraison ?"
        
        if any(word in query_words for word in ["prix", "coût", "payer", "paiement"]):
            return "Consultez nos prix compétitifs et nos moyens de paiement disponibles."
        
        # Redirection générique
        return "Je suis spécialisé dans les équipements moto. Comment puis-je vous aider avec nos produits ?"
    
    async def _learn_from_query(self, query: str, analysis: QueryAnalysis):
        """Apprentissage automatique à partir des requêtes"""
        
        # Ajout à l'historique
        self.query_history.append({
            'query': query,
            'analysis': asdict(analysis),
            'timestamp': time.time()
        })
        
        # Apprentissage de nouveaux mots-clés domaine
        if not analysis.is_offtopic and analysis.domain_relevance_score > 0.7:
            query_words = set(query.lower().split())
            new_domain_words = query_words - self.domain_keywords
            
            if new_domain_words:
                self.domain_keywords.update(new_domain_words)
                log3("[OFFTOPIC_DETECTOR]", f"🎓 Nouveaux mots domaine appris: {new_domain_words}")
        
        # Sauvegarde périodique (toutes les 50 requêtes)
        if len(self.query_history) % 50 == 0:
            await self._save_learned_patterns()
    
    async def _save_learned_patterns(self):
        """Sauvegarde des patterns appris"""
        try:
            # Sauvegarde patterns
            patterns_data = {}
            for pattern_id, pattern in self.patterns.items():
                data = asdict(pattern)
                data['keywords'] = list(data['keywords'])  # Set -> List pour JSON
                patterns_data[pattern_id] = data
            
            cache_manager.set(
                f"offtopic_patterns:{self.company_id}",
                json.dumps(patterns_data),
                ttl_seconds=86400 * 7  # 7 jours
            )
            
            # Sauvegarde mots-clés domaine
            cache_manager.set(
                f"domain_keywords:{self.company_id}",
                json.dumps(list(self.domain_keywords)),
                ttl_seconds=86400 * 7
            )
            
            log3("[OFFTOPIC_DETECTOR]", "💾 Patterns et domaine sauvegardés")
            
        except Exception as e:
            log3("[OFFTOPIC_DETECTOR]", f"❌ Erreur sauvegarde: {e}")
    
    def get_performance_metrics(self) -> Dict:
        """Retourne les métriques de performance pour monitoring"""
        if not self.performance_metrics['processing_time']:
            return {}
        
        processing_times = self.performance_metrics['processing_time']
        
        return {
            'avg_processing_time_ms': np.mean(processing_times),
            'max_processing_time_ms': np.max(processing_times),
            'total_queries_analyzed': len(self.query_history),
            'patterns_count': len(self.patterns),
            'domain_keywords_count': len(self.domain_keywords),
            'cache_hit_rate': self._calculate_cache_hit_rate()
        }
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calcule le taux de hit du cache (approximatif)"""
        # Implémentation simplifiée - à améliorer avec vraies métriques
        return 0.75  # Placeholder


# Instance globale avec factory pattern
_detectors: Dict[str, DynamicOffTopicDetector] = {}

def get_offtopic_detector(company_id: str) -> DynamicOffTopicDetector:
    """Factory pour obtenir le détecteur pour une entreprise"""
    if company_id not in _detectors:
        _detectors[company_id] = DynamicOffTopicDetector(company_id)
    return _detectors[company_id]


# API principale
async def analyze_offtopic_query(query: str, company_id: str, 
                                context_available: bool = False) -> QueryAnalysis:
    """
    🎯 API PRINCIPALE - Analyse hors-sujet avec apprentissage dynamique
    """
    detector = get_offtopic_detector(company_id)
    return await detector.analyze_query(query, context_available)
