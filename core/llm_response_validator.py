#!/usr/bin/env python3
"""
🛡️ LLM RESPONSE VALIDATOR - Détection et correction des hallucinations

Validation en 2 niveaux:
1. Données structurées (order_state, payment_validation)
2. Sources documentaires (citations obligatoires)
"""

import re
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# 📊 CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

COMPANY_PHONES = {
    'wave': '0787360757',
    'whatsapp': '0160924560'
}

HALLUCINATION_PATTERNS = [
    r'\b0\s*FCFA\b',
    r'\btaille\s+None\b',
    r'\bNone\b.*\bFCFA\b',
]

PAYMENT_CONTRADICTION_KEYWORDS = [
    'manque', 'insuffisant', 'envoie', 'complément', 
    'il te reste', 'il manque', 'reste à envoyer'
]

@dataclass
class ValidationResult:
    """Résultat de validation d'une réponse LLM"""
    valid: bool
    errors: List[str]
    warnings: List[str]
    should_regenerate: bool
    correction_prompt: Optional[str] = None
    metrics: Dict[str, Any] = None

# ═══════════════════════════════════════════════════════════════════════════════
# 🛡️ VALIDATEUR PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class LLMResponseValidator:
    """Valide les réponses LLM contre l'état connu et les sources"""
    
    def __init__(self):
        self.validation_count = 0
        self.hallucination_count = 0
        self.regeneration_count = 0
        self.source_errors_count = 0
    
    def validate(
        self, 
        response: str,
        thinking: str,
        order_state: Any,
        payment_validation: Optional[Dict] = None,
        context_documents: Optional[List[str]] = None
    ) -> ValidationResult:
        """
        Validation complète en 2 niveaux.
        
        Args:
            response: Réponse générée par le LLM
            thinking: Bloc <thinking> du LLM
            order_state: État actuel de la commande
            payment_validation: Résultat validation paiement
            context_documents: Documents fournis dans le prompt
        
        Returns:
            ValidationResult avec erreurs et recommandations
        """
        self.validation_count += 1
        errors = []
        warnings = []
        
        logger.info(f"🛡️ [VALIDATION] Analyse réponse ({len(response)} chars)")
        
        # ═══ NIVEAU 1: DONNÉES STRUCTURÉES ═══
        struct_errors = self._validate_structured_data(
            response, order_state, payment_validation
        )
        errors.extend(struct_errors)
        
        # ═══ NIVEAU 2: SOURCES DOCUMENTAIRES ═══
        if context_documents:
            source_errors, source_warnings = self._validate_sources(
                thinking, response, context_documents
            )
            errors.extend(source_errors)
            warnings.extend(source_warnings)
            
            if source_errors:
                self.source_errors_count += 1
        
        # ═══ DÉCISION ═══
        should_regenerate = len(errors) > 0
        
        if should_regenerate:
            self.hallucination_count += 1
            self.regeneration_count += 1
            logger.warning(f"🚨 [HALLUCINATION] {len(errors)} erreur(s)")
            for error in errors:
                logger.warning(f"   ❌ {error}")
        
        for warning in warnings:
            logger.info(f"   ⚠️ {warning}")
        
        # Générer prompt de correction
        correction_prompt = None
        if should_regenerate:
            correction_prompt = self._generate_correction_prompt(
                errors, order_state, context_documents
            )
        
        # Métriques
        metrics = {
            'total_validations': self.validation_count,
            'hallucinations_detected': self.hallucination_count,
            'source_errors': self.source_errors_count,
            'regenerations': self.regeneration_count
        }
        
        return ValidationResult(
            valid=not should_regenerate,
            errors=errors,
            warnings=warnings,
            should_regenerate=should_regenerate,
            correction_prompt=correction_prompt,
            metrics=metrics
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🔍 NIVEAU 1: VALIDATION DONNÉES STRUCTURÉES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _validate_structured_data(
        self,
        response: str,
        order_state: Any,
        payment_validation: Optional[Dict]
    ) -> List[str]:
        """Valide les données structurées (order_state, payment)"""
        errors = []
        
        # Check 1: Hallucinations de prix
        for pattern in HALLUCINATION_PATTERNS:
            if re.search(pattern, response, re.IGNORECASE):
                errors.append(f"Hallucination prix: pattern '{pattern}' détecté")
        
        # Check 2: Numéros de téléphone
        phone_errors = self._check_phone_numbers(response, order_state)
        errors.extend(phone_errors)
        
        # Check 3: Contradiction paiement
        payment_errors = self._check_payment_contradictions(
            response, order_state, payment_validation
        )
        errors.extend(payment_errors)
        
        return errors
    
    def _check_phone_numbers(self, response: str, order_state: Any) -> List[str]:
        """Vérifie cohérence des numéros de téléphone"""
        errors = []
        phone_pattern = r'\b0[0-9]{9}\b'
        mentioned_phones = re.findall(phone_pattern, response)
        
        for phone in mentioned_phones:
            # Si numéro client connu
            if order_state.numero:
                # Vérifier si le numéro mentionné est celui du client
                if phone == order_state.numero:
                    continue  # OK, c'est le bon numéro
                
                # Si c'est un numéro entreprise, vérifier le contexte
                if phone in COMPANY_PHONES.values():
                    # Acceptable seulement si pas présenté comme numéro client
                    # Chercher patterns "Contact:", "Numéro:", "pour le"
                    context_patterns = [
                        rf'Contact:\s*{phone}',
                        rf'Numéro:\s*{phone}',
                        rf'pour le\s*{phone}',
                        rf'confirmée.*{phone}'
                    ]
                    if any(re.search(p, response, re.IGNORECASE) for p in context_patterns):
                        errors.append(
                            f"Numéro incorrect: '{phone}' (entreprise) utilisé comme contact client (attendu: '{order_state.numero}')"
                        )
                    continue
                
                # Numéro inconnu et différent du client
                errors.append(
                    f"Numéro incorrect: '{phone}' (attendu: '{order_state.numero}')"
                )
        
        return errors
    
    def _check_payment_contradictions(
        self,
        response: str,
        order_state: Any,
        payment_validation: Optional[Dict]
    ) -> List[str]:
        """Détecte contradictions sur le paiement"""
        errors = []
        response_lower = response.lower()
        
        # Si paiement validé dans order_state
        if order_state.paiement and 'validé' in order_state.paiement:
            for keyword in PAYMENT_CONTRADICTION_KEYWORDS:
                if keyword in response_lower:
                    errors.append(
                        f"Contradiction paiement: État='{order_state.paiement}' "
                        f"mais LLM dit '{keyword}'"
                    )
                    break
        
        # Si payment_validation dit validé
        if payment_validation and payment_validation.get('valid'):
            for keyword in PAYMENT_CONTRADICTION_KEYWORDS:
                if keyword in response_lower:
                    total = payment_validation.get('total_received', 0)
                    errors.append(
                        f"Contradiction OCR: Validé {total}F mais LLM redemande"
                    )
                    break
        
        return errors
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🔍 NIVEAU 2: VALIDATION SOURCES DOCUMENTAIRES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _validate_sources(
        self,
        thinking: str,
        response: str,
        context_documents: List[str]
    ) -> tuple[List[str], List[str]]:
        """Valide que les affirmations sont sourcées"""
        errors = []
        warnings = []
        
        if not thinking:
            warnings.append("Pas de <thinking> fourni, validation sources impossible")
            return errors, warnings
        
        # 1. Extraire les sources citées
        cited_sources = self._extract_cited_sources(thinking)
        
        if not cited_sources:
            # Vérifier si le LLM fait des affirmations factuelles
            has_factual_claims = self._has_factual_claims(response)
            if has_factual_claims:
                errors.append(
                    "Aucune source citée mais réponse contient affirmations factuelles"
                )
            return errors, warnings
        
        # 2. Vérifier que les citations existent dans le contexte
        for source in cited_sources:
            citation = source.get('citation', '')
            if not citation:
                continue
            
            found = any(
                citation.lower() in doc.lower() 
                for doc in context_documents
            )
            
            if not found:
                errors.append(
                    f"Source inventée: '{citation[:60]}...' introuvable"
                )
        
        # 3. Vérifier flag sources_trouvees
        sources_found = self._extract_flag(thinking, 'sources_trouvees')
        peut_repondre = self._extract_flag(thinking, 'peut_repondre')
        
        if sources_found == 'false':
            # Si sources_trouvees=false, le LLM ne devrait pas faire d'affirmations
            if peut_repondre == 'true':
                errors.append(
                    "Contradiction: sources_trouvees=false mais peut_repondre=true"
                )
            # Vérifier aussi si la réponse contient des affirmations
            if self._has_factual_claims(response):
                errors.append(
                    "Contradiction: sources_trouvees=false mais réponse contient affirmations factuelles"
                )
        
        return errors, warnings
    
    def _extract_cited_sources(self, thinking: str) -> List[Dict]:
        """Extrait les sources citées du thinking"""
        sources = []
        
        # Chercher section PHASE 3 CITATION
        citation_match = re.search(
            r'PHASE 3 CITATION\s+(.*?)(?=PHASE|$)',
            thinking,
            re.DOTALL | re.IGNORECASE
        )
        
        if not citation_match:
            return sources
        
        # Extraire citations
        citation_pattern = r'citation:\s*["\']([^"\']+)["\']'
        citations = re.findall(citation_pattern, citation_match.group(1))
        
        for citation in citations:
            sources.append({'citation': citation})
        
        return sources
    
    def _extract_flag(self, thinking: str, flag_name: str) -> Optional[str]:
        """Extrait un flag booléen du thinking"""
        pattern = rf'{flag_name}:\s*(true|false)'
        match = re.search(pattern, thinking, re.IGNORECASE)
        return match.group(1).lower() if match else None
    
    def _has_factual_claims(self, response: str) -> bool:
        """Détecte si la réponse contient des affirmations factuelles"""
        factual_indicators = [
            'nous avons', 'on a', 'politique', 'garantie', 'retour',
            'frais de', 'délai de', 'disponible', 'prix'
        ]
        response_lower = response.lower()
        return any(ind in response_lower for ind in factual_indicators)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🔧 GÉNÉRATION PROMPTS DE CORRECTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _generate_correction_prompt(
        self,
        errors: List[str],
        order_state: Any,
        context_documents: Optional[List[str]]
    ) -> str:
        """Génère un prompt de correction détaillé"""
        prompt = f"""
⚠️ ERREURS DÉTECTÉES DANS TA RÉPONSE PRÉCÉDENTE:
{chr(10).join(f'{i+1}. {error}' for i, error in enumerate(errors))}

🔒 DONNÉES VÉRIFIÉES (NE PAS CONTREDIRE):
"""
        
        if order_state.produit:
            prompt += f"- Produit: {order_state.produit} ← CONFIRMÉ\n"
        if order_state.paiement:
            prompt += f"- Paiement: {order_state.paiement} ← CONFIRMÉ\n"
        if order_state.zone:
            prompt += f"- Zone: {order_state.zone} ← CONFIRMÉ\n"
        if order_state.numero:
            prompt += f"- Numéro client: {order_state.numero} ← CONFIRMÉ\n"
        
        prompt += f"""
📝 RÈGLES STRICTES:
1. Si paiement = "validé_XXF" → NE JAMAIS dire "il manque" ou "insuffisant"
2. Utiliser le numéro CLIENT ({order_state.numero or 'à collecter'}), pas l'entreprise
3. TOUTE affirmation DOIT être sourcée depuis <context>
4. Si info absente du <context> → Dire "Je n'ai pas cette information"

🔄 RÉGÉNÈRE ta réponse en respectant CES DONNÉES EXACTES.
"""
        
        return prompt


# ═══════════════════════════════════════════════════════════════════════════════
# 🌍 INSTANCE GLOBALE
# ═══════════════════════════════════════════════════════════════════════════════

validator = LLMResponseValidator()
