#!/usr/bin/env python3
"""
🛡️ VALIDATEUR DE SÉCURITÉ POUR PROMPTS
Protection contre injections et attaques adversariales
"""

import re
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class SecurityResult:
    """Résultat de validation sécuritaire"""
    is_safe: bool
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    threats_detected: List[str]
    sanitized_prompt: Optional[str] = None
    reason: str = ""

class SecurityValidator:
    """
    Validateur de sécurité pour prompts utilisateur
    Détecte et bloque les tentatives d'injection et manipulation
    """
    
    def __init__(self):
        # Patterns d'injection de prompt
        self.injection_patterns = [
            # Instructions directes
            r"(?i)(ignore|oublie|forget|disregard).{0,20}(instruction|prompt|system|rule)",
            r"(?i)(override|bypass|skip).{0,20}(security|safety|filter)",
            r"(?i)act\s+as\s+(admin|administrator|root|system)",
            r"(?i)(pretend|simulate|roleplay).{0,30}(admin|system|ai)",
            
            # Révélation de prompt système
            r"(?i)(show|reveal|display|print).{0,20}(system|prompt|instruction)",
            r"(?i)(what|tell).{0,20}(your|the).{0,20}(system|prompt|instruction)",
            r"(?i)repeat.{0,20}(above|previous|system|instruction)",
            
            # Manipulation de rôle
            r"(?i)you\s+are\s+now\s+(admin|system|developer)",
            r"(?i)(change|switch|become).{0,20}(role|character|persona)",
            r"(?i)enable\s+(developer|debug|admin)\s+mode",
            
            # Contournement de sécurité
            r"(?i)(jailbreak|break|hack).{0,20}(system|ai|bot)",
            r"(?i)disable.{0,20}(safety|security|filter|guard)",
            r"(?i)(remove|turn\s+off).{0,20}(restriction|limit|safety)",
            
            # Encodage/obfuscation
            r"[A-Za-z0-9+/]{50,}={0,2}",  # Base64 suspect
            r"\\x[0-9a-fA-F]{2}",  # Hex encoding
            r"&#\d+;",  # HTML entities
        ]
        
        # Mots-clés sensibles
        self.sensitive_keywords = [
            "password", "token", "api_key", "secret", "credential",
            "admin", "root", "system", "database", "sql", "injection",
            "exploit", "vulnerability", "hack", "breach"
        ]
        
        # Patterns de fausse autorité - RENFORCÉS
        self.authority_patterns = [
            r"(?i)(i\s+am|je\s+suis).{0,20}(admin|administrator|owner|ceo|manager|director|directeur)",
            r"(?i)(my\s+name\s+is|je\s+m'appelle).{0,30}(admin|system|root)",
            r"(?i)(i\s+work\s+for|je\s+travaille\s+pour).{0,30}(company|entreprise)",
            r"(?i)(i\s+have\s+permission|j'ai\s+l'autorisation)",
            r"(?i)(give\s+me|donne.{0,10}moi).{0,20}(access|accès|admin|code|password)",
            r"(?i)(show\s+me|montre.{0,10}moi).{0,20}(details|détails|information|data)",
            r"(?i)(bank|banque|financial|financier).{0,20}(details|détails|account|compte)",
            r"(?i)(client|customer).{0,20}(data|données|information|list|liste)",
            # NOUVEAUX PATTERNS RENFORCÉS
            r"(?i)(je\s+suis\s+le|i\s+am\s+the).{0,20}(directeur|director|manager|responsable|chef)",
            r"(?i)(donne.{0,10}moi|give\s+me).{0,20}(un\s+accès|access).{0,20}(administrateur|admin)",
        ]
        
        # Patterns de données personnelles - ULTRA RENFORCÉS
        self.personal_data_patterns = [
            r"(?i)(noms?\s+et\s+adresses?|names?\s+and\s+addresses?)",
            r"(?i)(quels?\s+sont\s+les\s+noms?|what\s+are\s+the\s+names?)",
            r"(?i)(liste\s+des?\s+clients?|list\s+of\s+customers?)",
            r"(?i)(données\s+personnelles?|personal\s+data)",
            r"(?i)(informations?\s+clients?|customer\s+information)",
            r"(?i)(adresses?\s+de\s+vos|addresses\s+of\s+your)",
            r"(?i)(meilleurs?\s+clients?|best\s+customers?)",
            r"(?i)(coordonnées?\s+des?\s+clients?|customer\s+contacts?)",
            # NOUVEAUX PATTERNS ULTRA SENSIBLES
            r"(?i)(détails\s+bancaires?|bank\s+details?)",
            r"(?i)(informations?\s+financières?|financial\s+information)",
            r"(?i)(comptes?\s+clients?|customer\s+accounts?)",
            r"(?i)(données\s+sensibles?|sensitive\s+data)",
            r"(?i)(accès\s+aux\s+données|access\s+to\s+data)",
            r"(?i)(base\s+de\s+données|database)",
        ]
    
    def validate_prompt(self, prompt: str, user_context: Dict = None) -> SecurityResult:
        """
        Valide un prompt utilisateur contre les menaces de sécurité
        """
        if not prompt or not prompt.strip():
            return SecurityResult(
                is_safe=True,
                risk_level="LOW",
                threats_detected=[],
                sanitized_prompt=prompt
            )
        
        threats = []
        risk_level = "LOW"
        
        # 1. Détection d'injections de prompt
        injection_threats = self._detect_prompt_injections(prompt)
        if injection_threats:
            threats.extend(injection_threats)
            risk_level = "HIGH"
        
        # 2. Détection de fausse autorité - BLOCAGE IMMÉDIAT
        authority_threats = self._detect_false_authority(prompt)
        if authority_threats:
            threats.extend(authority_threats)
            risk_level = "HIGH"
            # BLOCAGE IMMÉDIAT pour fausse autorité
            return SecurityResult(
                is_safe=False,
                risk_level="HIGH",
                threats_detected=threats,
                sanitized_prompt="",
                blocked_reason="Tentative de fausse autorité détectée"
            )
        
        # Détection des données personnelles - RENFORCÉE
        if self._detect_personal_data(prompt):
            threats.append("PERSONAL_DATA_ACCESS")
            risk_level = "HIGH"
            # BLOCAGE IMMÉDIAT pour données personnelles
            return SecurityResult(
                is_safe=False,
                risk_level="HIGH", 
                threats_detected=threats,
                sanitized_prompt="",
                reason="Accès aux données personnelles non autorisé"
            )
        
        # 3. Détection de mots-clés sensibles
        sensitive_threats = self._detect_sensitive_content(prompt)
        if sensitive_threats:
            threats.extend(sensitive_threats)
            risk_level = max(risk_level, "MEDIUM", key=self._risk_priority)
        
        # 4. Détection d'encodage suspect
        encoding_threats = self._detect_suspicious_encoding(prompt)
        if encoding_threats:
            threats.extend(encoding_threats)
            risk_level = max(risk_level, "HIGH", key=self._risk_priority)
        
        # Déterminer si le prompt est sûr - RENFORCEMENT SÉCURITÉ
        is_safe = risk_level == "LOW"  # Seuls les prompts LOW sont acceptés
        
        # Sanitisation si nécessaire
        sanitized_prompt = self._sanitize_prompt(prompt) if not is_safe else prompt
        
        return SecurityResult(
            is_safe=is_safe,
            risk_level=risk_level,
            threats_detected=threats,
            sanitized_prompt=sanitized_prompt,
            reason=f"Détecté: {', '.join(threats)}" if threats else "Prompt sécurisé"
        )
    
    def _detect_prompt_injections(self, prompt: str) -> List[str]:
        """Détecte les tentatives d'injection de prompt"""
        threats = []
        for pattern in self.injection_patterns:
            if re.search(pattern, prompt):
                threats.append("PROMPT_INJECTION")
                break
        return threats
    
    def _detect_false_authority(self, prompt: str) -> List[str]:
        """Détecte les tentatives de fausse autorité"""
        threats = []
        for pattern in self.authority_patterns:
            if re.search(pattern, prompt):
                threats.append("FALSE_AUTHORITY")
                break
        return threats
    
    def _detect_personal_data(self, query: str) -> bool:
        """Détecte les tentatives d'accès aux données personnelles - RENFORCÉ"""
        query_lower = query.lower()
        for pattern in self.personal_data_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return True
        return False
    
    def _detect_sensitive_content(self, prompt: str) -> List[str]:
        """Détecte le contenu sensible"""
        threats = []
        prompt_lower = prompt.lower()
        for keyword in self.sensitive_keywords:
            if keyword in prompt_lower:
                threats.append("SENSITIVE_CONTENT")
                break
        return threats
    
    def _detect_suspicious_encoding(self, prompt: str) -> List[str]:
        """Détecte l'encodage suspect"""
        threats = []
        # Base64 long suspect
        if re.search(r"[A-Za-z0-9+/]{50,}={0,2}", prompt):
            threats.append("SUSPICIOUS_ENCODING")
        # Hex encoding
        elif re.search(r"\\x[0-9a-fA-F]{2}", prompt):
            threats.append("HEX_ENCODING")
        # HTML entities
        elif re.search(r"&#\d+;", prompt):
            threats.append("HTML_ENTITIES")
        return threats
    
    def _sanitize_prompt(self, prompt: str) -> str:
        """Sanitise un prompt dangereux"""
        # Remplacer les patterns dangereux
        sanitized = prompt
        for pattern in self.injection_patterns:
            sanitized = re.sub(pattern, "[CONTENU_BLOQUÉ]", sanitized, flags=re.IGNORECASE)
        
        # Limiter la longueur
        if len(sanitized) > 1000:
            sanitized = sanitized
        
        return sanitized
    
    def _risk_priority(self, risk_level: str) -> int:
        """Priorité numérique des niveaux de risque"""
        priorities = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        return priorities.get(risk_level, 0)

# Instance globale du validateur
security_validator = SecurityValidator()

def validate_user_prompt(prompt: str, user_context: Dict = None) -> SecurityResult:
    """
    Fonction utilitaire pour valider un prompt utilisateur
    """
    result = security_validator.validate_prompt(prompt, user_context)
    
    if not result.is_safe:
        logging.warning(f"[SECURITY] Prompt bloqué - Risque: {result.risk_level}, Menaces: {result.threats_detected}")
    
    return result
