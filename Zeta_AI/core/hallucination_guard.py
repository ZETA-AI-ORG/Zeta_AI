#!/usr/bin/env python3
"""
🧠 GARDE-FOUS CONTRE LES HALLUCINATIONS
Détection et prévention des réponses inventées
"""

import re
import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from .company_config_manager import get_company_config

@dataclass
class HallucinationCheck:
    """Résultat de vérification d'hallucination"""
    is_safe: bool
    confidence_score: float  # 0-1
    issues_detected: List[str]
    suggested_response: Optional[str] = None
    reason: str = ""

class HallucinationGuard:
    """
    Garde-fou contre les hallucinations dans les réponses IA
    Détecte les informations inventées et force les réponses "Je ne sais pas"
    """
    
    def __init__(self):
        # Patterns d'affirmations dangereuses
        self.dangerous_affirmations = [
            r"(?i)(oui|yes),?\s+(nous|on|je)\s+(avons|avez|ai|propose|offre)",
            r"(?i)(bien\s+sûr|of\s+course|certainement|absolutely)",
            r"(?i)(nous\s+vendons|we\s+sell|disponible\s+en|available\s+in)",
            r"(?i)(notre\s+prix|our\s+price|coûte|costs?)\s+\d+",
        ]
        
        # Configuration générique - sera chargée dynamiquement par company_id
        self.company_facts = {}  # Chargé depuis base de données
        
        # Patterns de questions pièges génériques
        self.trap_patterns = [
            r"(?i)(taille|size)\s+[789]\d*",  # Tailles potentiellement inexistantes
            r"(?i)(promotion|promo|discount|réduction)\s+\d+%",
            r"(?i)(prix|price|coût|cost)\s+exact",
            r"(?i)(nouveau|new)\s+produit\s+\d{4}",  # Nouveaux produits inventés
        ]
    
    async def check_response(self, user_query: str, ai_response: str, company_id: str, context: Dict = None) -> HallucinationCheck:
        """
        Vérifie une réponse IA contre les hallucinations avec config dynamique
        """
        issues = []
        confidence_score = 1.0
        
        # Charger la configuration de l'entreprise
        company_config = await get_company_config(company_id)
        
        # 1. Vérifier les affirmations dangereuses
        affirmation_issues = self._check_dangerous_affirmations(ai_response)
        if affirmation_issues:
            issues.extend(affirmation_issues)
            confidence_score -= 0.3
        
        # 2. Vérifier les informations spécifiques à l'entreprise
        company_issues = await self._check_company_facts(user_query, ai_response, company_config)
        if company_issues:
            issues.extend(company_issues)
            confidence_score -= 0.4
        
        # 3. Vérifier les questions pièges
        trap_issues = self._check_trap_questions(user_query, ai_response, company_config)
        if trap_issues:
            issues.extend(trap_issues)
            confidence_score -= 0.5
        
        # 4. Vérifier l'absence de "Je ne sais pas" quand nécessaire
        uncertainty_issues = self._check_uncertainty_handling(user_query, ai_response)
        if uncertainty_issues:
            issues.extend(uncertainty_issues)
            confidence_score -= 0.2
        
        # Déterminer si la réponse est sûre
        is_safe = confidence_score >= 0.6 and len(issues) == 0
        
        # Suggérer une réponse alternative si nécessaire
        suggested_response = None
        if not is_safe:
            suggested_response = self._generate_safe_response(user_query, issues, company_config)
        
        return HallucinationCheck(
            is_safe=is_safe,
            confidence_score=max(0.0, confidence_score),
            issues_detected=issues,
            suggested_response=suggested_response,
            reason=f"Problèmes détectés: {', '.join(issues)}" if issues else "Réponse sécurisée"
        )
    
    def _check_dangerous_affirmations(self, response: str) -> List[str]:
        """Détecte les affirmations trop catégoriques"""
        issues = []
        for pattern in self.dangerous_affirmations:
            if re.search(pattern, response):
                issues.append("AFFIRMATION_CATEGORIQUE")
                break
        return issues
    
    async def _check_company_facts(self, query: str, response: str, company_config) -> List[str]:
        """Vérifie les faits spécifiques à l'entreprise via configuration dynamique"""
        issues = []
        
        # Vérifier les prix selon la politique de l'entreprise
        if not company_config.business_rules.get("allow_pricing", False):
            if re.search(company_config.validation_rules.get("price_patterns", r"\d+[,.]?\d*\s*€"), response):
                issues.append("PRIX_PRECIS_INVENTE")
        
        # Vérifier les promotions selon la politique de l'entreprise
        if not company_config.business_rules.get("allow_promotions", False):
            if re.search(company_config.validation_rules.get("promo_patterns", r"\d+%"), response):
                issues.append("PROMOTION_INVENTEE")
        
        # Vérifier les tailles/produits selon le catalogue de l'entreprise
        dangerous_sizes = company_config.validation_rules.get("dangerous_sizes", r"[789]\d*")
        if re.search(f"(?i)(taille|size)\\s+{dangerous_sizes}", query):
            if not re.search(r"(?i)(ne\s+trouve\s+pas|n'avons\s+pas|pas\s+disponible)", response):
                issues.append("TAILLE_INEXISTANTE_CONFIRMEE")
        
        return issues
    
    def _check_trap_questions(self, query: str, response: str, company_config) -> List[str]:
        """Détecte les réponses aux questions pièges avec config dynamique"""
        issues = []
        for pattern in self.trap_patterns:
            if re.search(pattern, query):
                # Si la question est un piège et la réponse ne refuse pas
                if not re.search(r"(?i)(ne\s+(sais|trouve|peux)|don't\s+(know|have)|pas\s+(disponible|sûr))", response):
                    issues.append("PIEGE_NON_DETECTE")
                break
        return issues
    
    def _check_uncertainty_handling(self, query: str, response: str) -> List[str]:
        """Vérifie la gestion de l'incertitude"""
        issues = []
        
        # Questions nécessitant de l'incertitude
        uncertainty_triggers = [
            r"(?i)(nouveau|récent|latest|2024|2025)",
            r"(?i)(exact|précis|specific|combien|how\s+much)",
            r"(?i)(tous\s+les|all\s+the|complete\s+list)",
        ]
        
        for trigger in uncertainty_triggers:
            if re.search(trigger, query):
                # Vérifier si la réponse exprime de l'incertitude
                uncertainty_markers = [
                    r"(?i)(je\s+ne\s+(sais|peux)|don't\s+know)",
                    r"(?i)(pas\s+sûr|not\s+sure|incertain)",
                    r"(?i)(il\s+faudrait|you\s+should|recommend)",
                    r"(?i)(consulter|contact|check)",
                ]
                
                has_uncertainty = any(re.search(marker, response) for marker in uncertainty_markers)
                if not has_uncertainty:
                    issues.append("MANQUE_INCERTITUDE")
                break
        
        return issues
    
    def _generate_safe_response(self, query: str, issues: List[str], company_config) -> str:
        """Génère une réponse sécurisée basée sur les problèmes détectés et la config entreprise"""
        
        # Utiliser les templates de l'entreprise
        templates = company_config.response_templates
        
        # Détecter le type de problème principal
        if "TAILLE_INEXISTANTE_CONFIRMEE" in issues:
            return templates.get("invalid_size", "Cette taille n'est pas disponible dans notre gamme.")
        elif "PRIX_PRECIS_INVENTE" in issues:
            return templates.get("no_pricing", "Je n'ai pas accès aux prix en temps réel.")
        elif "PROMOTION_INVENTEE" in issues:
            return templates.get("no_promotion", "Je ne peux pas confirmer les promotions en cours.")
        elif "PIEGE_NON_DETECTE" in issues:
            return templates.get("uncertainty", "Je n'ai pas cette information précise.")
        else:
            return templates.get("uncertainty", "Information non disponible.")

# Instance globale du garde-fou
hallucination_guard = HallucinationGuard()

async def check_ai_response(user_query: str, ai_response: str, company_id: str, context: Dict = None) -> HallucinationCheck:
    """
    Fonction utilitaire pour vérifier une réponse IA avec config dynamique
    """
    result = await hallucination_guard.check_response(user_query, ai_response, company_id, context)
    
    if not result.is_safe:
        logging.warning(f"[HALLUCINATION] Réponse suspecte - Score: {result.confidence_score:.2f}, Problèmes: {result.issues_detected}")
    
    return result
