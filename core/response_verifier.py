#!/usr/bin/env python3
"""
✅ VÉRIFICATEUR DE RÉPONSES INTELLIGENT
Post-traitement QA, vérification factualité, cohérence et benchmarks
Optimisé pour détecter les erreurs courantes du LLM
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json

logger = logging.getLogger(__name__)

class VerificationLevel(Enum):
    """Niveaux de vérification"""
    BASIC = "basic"
    STANDARD = "standard"
    STRICT = "strict"
    CRITICAL = "critical"

class IssueType(Enum):
    """Types de problèmes détectés"""
    FACTUAL_ERROR = "factual_error"
    PRICE_INCONSISTENCY = "price_inconsistency"
    CONTACT_ERROR = "contact_error"
    CALCULATION_ERROR = "calculation_error"
    COHERENCE_ISSUE = "coherence_issue"
    MISSING_INFO = "missing_info"
    HALLUCINATION = "hallucination"
    TONE_ISSUE = "tone_issue"

@dataclass
class VerificationIssue:
    """Problème détecté lors de la vérification"""
    type: IssueType
    severity: str  # "low", "medium", "high", "critical"
    description: str
    location: str  # Partie de la réponse concernée
    suggestion: str  # Suggestion de correction
    confidence: float

@dataclass
class VerificationResult:
    """Résultat de vérification complet"""
    is_valid: bool
    quality_score: float
    issues: List[VerificationIssue]
    corrected_response: Optional[str]
    verification_metadata: Dict[str, Any]

class ResponseVerifier:
    """
    ✅ VÉRIFICATEUR DE RÉPONSES INTELLIGENT
    
    Fonctionnalités :
    - Vérification factuelle contre le contexte
    - Détection d'incohérences de prix/calculs
    - Validation des informations de contact
    - Détection d'hallucinations
    - Vérification de cohérence conversationnelle
    - Benchmarks qualité automatiques
    """
    
    def __init__(self, verification_level: VerificationLevel = VerificationLevel.STANDARD):
        self.verification_level = verification_level
        self.factual_patterns = self._init_factual_patterns()
        self.price_patterns = self._init_price_patterns()
        self.contact_patterns = self._init_contact_patterns()
        self.quality_benchmarks = self._init_quality_benchmarks()
        
        # Seuils de qualité selon le niveau
        self.quality_thresholds = {
            VerificationLevel.BASIC: 0.6,
            VerificationLevel.STANDARD: 0.7,
            VerificationLevel.STRICT: 0.8,
            VerificationLevel.CRITICAL: 0.9
        }
    
    def _init_factual_patterns(self) -> Dict[str, List[str]]:
        """Initialise les patterns de vérification factuelle"""
        return {
            'phone_numbers': [
                r'\+225\s*\d{2}\s*\d{2}\s*\d{2}\s*\d{2}\s*\d{2}',
                r'0\d{2}\s*\d{2}\s*\d{2}\s*\d{2}\s*\d{2}',
                r'\d{10}'
            ],
            'prices_fcfa': [
                r'(\d+(?:[,\.]\d+)?)\s*(?:fcfa|f\s*cfa|francs?)',
                r'(\d+)\s*(?:mille|k)\s*(?:fcfa|f)'
            ],
            'zones_abidjan': [
                r'\b(cocody|yopougon|plateau|adjamé|abobo|marcory|koumassi|treichville|angré|riviera)\b',
                r'\b(port-bouët|attécoubé|bingerville|songon|anyama)\b'
            ],
            'product_types': [
                r'\b(couches?|culottes?|pression|adultes?|bébé|pampers?|huggies)\b'
            ],
            'sizes': [
                r'\btaille\s*(\d+)\b',
                r'\bt(\d+)\b',
                r'\bsize\s*(\d+)\b'
            ]
        }
    
    def _init_price_patterns(self) -> Dict[str, Any]:
        """Initialise les patterns de vérification des prix"""
        return {
            'valid_ranges': {
                'couches_pression': (15000, 30000),  # FCFA par paquet
                'couches_culottes': (4000, 6000),    # FCFA par paquet
                'couches_adultes': (5000, 7000),     # FCFA par paquet
                'livraison_abidjan': (1000, 2000),   # FCFA
                'livraison_peripherie': (2000, 3000), # FCFA
                'livraison_hors_abidjan': (3000, 6000) # FCFA
            },
            'calculation_patterns': [
                r'(\d+)\s*(?:paquets?|lots?)\s*(?:x|×|\*)\s*(\d+(?:[,\.]\d+)?)\s*(?:fcfa|f)',
                r'total\s*:?\s*(\d+(?:[,\.]\d+)?)\s*(?:fcfa|f)',
                r'sous-total\s*:?\s*(\d+(?:[,\.]\d+)?)\s*(?:fcfa|f)'
            ]
        }
    
    def _init_contact_patterns(self) -> Dict[str, str]:
        """Initialise les patterns de contact valides"""
        return {
            'whatsapp_valid': '+2250160924560',
            'phone_valid': '+2250787360757',
            'wave_valid': '+2250787360757',
            'ai_name_valid': 'Jessica',
            'company_name_valid': 'Rue du Gros'
        }
    
    def _init_quality_benchmarks(self) -> Dict[str, Dict[str, Any]]:
        """Initialise les benchmarks de qualité"""
        return {
            'response_length': {
                'min': 50,
                'optimal_min': 100,
                'optimal_max': 500,
                'max': 1000
            },
            'information_density': {
                'min_facts_per_100_chars': 1,
                'optimal_facts_per_100_chars': 3
            },
            'tone_indicators': {
                'professional': ['je vous', 'nous proposons', 'notre équipe', 'service client'],
                'friendly': ['bonjour', 'bonsoir', 'merci', 'avec plaisir', 'n\'hésitez pas'],
                'commercial': ['offre', 'promotion', 'économie', 'avantage', 'recommande']
            },
            'completeness_indicators': {
                'product_inquiry': ['prix', 'disponibilité', 'caractéristiques'],
                'price_inquiry': ['montant', 'fcfa', 'total'],
                'delivery_inquiry': ['zone', 'délai', 'tarif'],
                'contact_inquiry': ['téléphone', 'whatsapp', 'contact']
            }
        }
    
    def verify_factual_accuracy(self, response: str, context: str) -> List[VerificationIssue]:
        """Vérifie l'exactitude factuelle contre le contexte"""
        issues = []
        
        # Vérification des numéros de téléphone
        phone_issues = self._verify_phone_numbers(response)
        issues.extend(phone_issues)
        
        # Vérification des prix
        price_issues = self._verify_prices(response, context)
        issues.extend(price_issues)
        
        # Vérification des zones géographiques
        zone_issues = self._verify_zones(response, context)
        issues.extend(zone_issues)
        
        # Vérification des informations produits
        product_issues = self._verify_products(response, context)
        issues.extend(product_issues)
        
        return issues
    
    def _verify_phone_numbers(self, response: str) -> List[VerificationIssue]:
        """Vérifie les numéros de téléphone"""
        issues = []
        
        # Extraction des numéros dans la réponse
        phone_pattern = r'(\+?225\s*\d{2}\s*\d{2}\s*\d{2}\s*\d{2}\s*\d{2}|\d{10})'
        found_phones = re.findall(phone_pattern, response)
        
        valid_phones = ['+2250787360757', '+2250160924560', '0787360757', '0160924560']
        
        for phone in found_phones:
            # Normalisation
            normalized_phone = re.sub(r'\s+', '', phone)
            if not normalized_phone.startswith('+'):
                if normalized_phone.startswith('0'):
                    normalized_phone = '+225' + normalized_phone[1:]
                else:
                    normalized_phone = '+225' + normalized_phone
            
            # Vérification
            if normalized_phone not in ['+2250787360757', '+2250160924560']:
                issues.append(VerificationIssue(
                    type=IssueType.CONTACT_ERROR,
                    severity="high",
                    description=f"Numéro de téléphone incorrect: {phone}",
                    location=f"Numéro trouvé: {phone}",
                    suggestion=f"Utiliser +2250787360757 (principal) ou +2250160924560 (WhatsApp)",
                    confidence=0.9
                ))
        
        return issues
    
    def _verify_prices(self, response: str, context: str) -> List[VerificationIssue]:
        """Vérifie la cohérence des prix"""
        issues = []
        
        # Extraction des prix dans la réponse
        price_pattern = r'(\d+(?:[,\.]\d+)?)\s*(?:fcfa|f\s*cfa|francs?)'
        found_prices = re.findall(price_pattern, response.lower())
        
        # Extraction des prix dans le contexte
        context_prices = re.findall(price_pattern, context.lower())
        
        for price_str in found_prices:
            try:
                price = float(price_str.replace(',', '.'))
                
                # Vérification des ranges valides
                price_type = self._detect_price_type(response, price_str)
                valid_range = self.price_patterns['valid_ranges'].get(price_type)
                
                if valid_range and not (valid_range[0] <= price <= valid_range[1]):
                    issues.append(VerificationIssue(
                        type=IssueType.PRICE_INCONSISTENCY,
                        severity="medium",
                        description=f"Prix {price} FCFA hors range valide pour {price_type}",
                        location=f"Prix: {price_str} FCFA",
                        suggestion=f"Vérifier que le prix est dans la range {valid_range[0]}-{valid_range[1]} FCFA",
                        confidence=0.7
                    ))
                
                # Vérification contre le contexte
                if context_prices and price_str not in [p.replace('.', ',') for p in context_prices]:
                    # Tolérance de 5% pour les arrondis
                    context_prices_float = [float(p.replace(',', '.')) for p in context_prices]
                    if not any(abs(price - cp) / cp < 0.05 for cp in context_prices_float):
                        issues.append(VerificationIssue(
                            type=IssueType.FACTUAL_ERROR,
                            severity="high",
                            description=f"Prix {price} FCFA non trouvé dans le contexte",
                            location=f"Prix: {price_str} FCFA",
                            suggestion="Vérifier que le prix correspond aux données disponibles",
                            confidence=0.8
                        ))
                        
            except ValueError:
                continue
        
        return issues
    
    def _detect_price_type(self, response: str, price_str: str) -> str:
        """Détecte le type de prix selon le contexte"""
        response_lower = response.lower()
        
        # Recherche dans un contexte de 50 caractères autour du prix
        price_pos = response_lower.find(price_str.replace(',', '.'))
        if price_pos == -1:
            price_pos = response_lower.find(price_str.replace('.', ','))
        
        if price_pos != -1:
            context_window = response_lower[max(0, price_pos-50):price_pos+50]
            
            if any(word in context_window for word in ['pression', 'couches à']):
                return 'couches_pression'
            elif any(word in context_window for word in ['culottes', 'culotte']):
                return 'couches_culottes'
            elif any(word in context_window for word in ['adulte', 'adultes']):
                return 'couches_adultes'
            elif any(word in context_window for word in ['livraison', 'livrer', 'transport']):
                if any(zone in context_window for zone in ['cocody', 'yopougon', 'plateau']):
                    return 'livraison_abidjan'
                elif any(zone in context_window for zone in ['port-bouët', 'bingerville']):
                    return 'livraison_peripherie'
                else:
                    return 'livraison_hors_abidjan'
        
        return 'unknown'
    
    def _verify_zones(self, response: str, context: str) -> List[VerificationIssue]:
        """Vérifie les zones géographiques"""
        issues = []
        
        # Zones valides par catégorie
        zones_abidjan_centre = ['cocody', 'yopougon', 'plateau', 'adjamé', 'abobo', 'marcory', 'koumassi', 'treichville']
        zones_peripherie = ['port-bouët', 'attécoubé', 'bingerville', 'songon', 'anyama']
        
        response_lower = response.lower()
        
        # Vérification des tarifs de livraison par zone
        for zone in zones_abidjan_centre:
            if zone in response_lower:
                # Recherche du tarif associé
                zone_pos = response_lower.find(zone)
                context_window = response_lower[zone_pos:zone_pos+100]
                
                price_match = re.search(r'(\d+(?:[,\.]\d+)?)\s*(?:fcfa|f)', context_window)
                if price_match:
                    price = float(price_match.group(1).replace(',', '.'))
                    if not (1000 <= price <= 2000):  # Tarif Abidjan centre
                        issues.append(VerificationIssue(
                            type=IssueType.PRICE_INCONSISTENCY,
                            severity="medium",
                            description=f"Tarif livraison {price} FCFA incorrect pour {zone} (zone centre)",
                            location=f"Zone: {zone}, Prix: {price} FCFA",
                            suggestion="Tarif zone centre Abidjan: 1500 FCFA",
                            confidence=0.8
                        ))
        
        return issues
    
    def _verify_products(self, response: str, context: str) -> List[VerificationIssue]:
        """Vérifie les informations produits"""
        issues = []
        
        # Vérification des tailles mentionnées
        size_pattern = r'taille\s*(\d+)'
        found_sizes = re.findall(size_pattern, response.lower())
        
        valid_sizes = ['1', '2', '3', '4', '5', '6', '7']  # Tailles valides pour couches
        
        for size in found_sizes:
            if size not in valid_sizes:
                issues.append(VerificationIssue(
                    type=IssueType.FACTUAL_ERROR,
                    severity="medium",
                    description=f"Taille {size} non valide",
                    location=f"Taille: {size}",
                    suggestion="Tailles valides: 1-7 pour couches",
                    confidence=0.7
                ))
        
        return issues
    
    def verify_calculations(self, response: str) -> List[VerificationIssue]:
        """Vérifie les calculs mathématiques"""
        issues = []
        
        # Pattern pour détecter les calculs
        calc_patterns = [
            r'(\d+)\s*(?:paquets?|lots?)\s*(?:x|×|\*)\s*(\d+(?:[,\.]\d+)?)\s*(?:fcfa|f)\s*=\s*(\d+(?:[,\.]\d+)?)\s*(?:fcfa|f)',
            r'(\d+(?:[,\.]\d+)?)\s*\+\s*(\d+(?:[,\.]\d+)?)\s*=\s*(\d+(?:[,\.]\d+)?)',
            r'total\s*:?\s*(\d+(?:[,\.]\d+)?)\s*(?:fcfa|f)'
        ]
        
        for pattern in calc_patterns:
            matches = re.finditer(pattern, response.lower())
            for match in matches:
                groups = match.groups()
                
                if len(groups) >= 3:  # Calcul avec résultat
                    try:
                        if 'x' in pattern or '×' in pattern or '*' in pattern:
                            # Multiplication
                            qty = float(groups[0])
                            price = float(groups[1].replace(',', '.'))
                            result = float(groups[2].replace(',', '.'))
                            expected = qty * price
                            
                            if abs(result - expected) > 0.01:  # Tolérance de 1 centime
                                issues.append(VerificationIssue(
                                    type=IssueType.CALCULATION_ERROR,
                                    severity="high",
                                    description=f"Erreur de calcul: {qty} × {price} = {result} (attendu: {expected})",
                                    location=match.group(0),
                                    suggestion=f"Corriger le résultat: {expected:.0f} FCFA",
                                    confidence=0.95
                                ))
                        
                        elif '+' in pattern:
                            # Addition
                            val1 = float(groups[0].replace(',', '.'))
                            val2 = float(groups[1].replace(',', '.'))
                            result = float(groups[2].replace(',', '.'))
                            expected = val1 + val2
                            
                            if abs(result - expected) > 0.01:
                                issues.append(VerificationIssue(
                                    type=IssueType.CALCULATION_ERROR,
                                    severity="high",
                                    description=f"Erreur d'addition: {val1} + {val2} = {result} (attendu: {expected})",
                                    location=match.group(0),
                                    suggestion=f"Corriger le résultat: {expected:.0f} FCFA",
                                    confidence=0.95
                                ))
                                
                    except ValueError:
                        continue
        
        return issues
    
    def detect_hallucinations(self, response: str, context: str, query: str) -> List[VerificationIssue]:
        """Détecte les hallucinations (informations inventées)"""
        issues = []
        
        # Mots-clés suspects (informations souvent inventées)
        suspicious_patterns = [
            r'\b(?:garantie|warranty)\s+(\d+)\s+(?:ans?|years?|mois)\b',
            r'\b(?:promotion|promo|réduction)\s+(\d+)%\b',
            r'\b(?:stock|disponible)\s*:?\s*(\d+)\s+(?:pièces?|unités?)\b',
            r'\b(?:délai|livraison)\s*:?\s*(\d+)\s+(?:heures?|jours?)\b'
        ]
        
        for pattern in suspicious_patterns:
            matches = re.finditer(pattern, response.lower())
            for match in matches:
                # Vérifier si cette information est dans le contexte
                if match.group(0) not in context.lower():
                    issues.append(VerificationIssue(
                        type=IssueType.HALLUCINATION,
                        severity="medium",
                        description=f"Information potentiellement inventée: {match.group(0)}",
                        location=match.group(0),
                        suggestion="Vérifier que cette information est dans les données disponibles",
                        confidence=0.6
                    ))
        
        # Vérification des noms propres non validés
        proper_nouns = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', response)
        valid_names = ['Jessica', 'Rue', 'Gros', 'Cocody', 'Yopougon', 'Abidjan', 'Wave']
        
        for name in proper_nouns:
            if name not in valid_names and name not in context:
                issues.append(VerificationIssue(
                    type=IssueType.HALLUCINATION,
                    severity="low",
                    description=f"Nom propre non validé: {name}",
                    location=name,
                    suggestion="Vérifier que ce nom est correct",
                    confidence=0.4
                ))
        
        return issues
    
    def calculate_quality_score(self, response: str, issues: List[VerificationIssue]) -> float:
        """Calcule le score de qualité global"""
        base_score = 1.0
        
        # Pénalités par type et sévérité d'issue
        penalties = {
            'critical': 0.3,
            'high': 0.2,
            'medium': 0.1,
            'low': 0.05
        }
        
        for issue in issues:
            penalty = penalties.get(issue.severity, 0.05)
            base_score -= penalty * issue.confidence
        
        # Bonus pour longueur appropriée
        length = len(response)
        if 100 <= length <= 500:
            base_score += 0.1
        elif length > 500:
            base_score += 0.05
        
        # Bonus pour densité d'information
        facts_count = len(re.findall(r'\d+(?:[,\.]\d+)?\s*fcfa|\+225\d+|taille\s*\d+', response.lower()))
        if facts_count > 0:
            density = facts_count / (length / 100)  # Facts per 100 chars
            if density >= 2:
                base_score += 0.1
        
        return max(0.0, min(1.0, base_score))
    
    def suggest_corrections(self, response: str, issues: List[VerificationIssue]) -> str:
        """Suggère des corrections automatiques"""
        corrected = response
        
        # Corrections automatiques pour les issues critiques
        for issue in issues:
            if issue.type == IssueType.CONTACT_ERROR and issue.severity == "high":
                # Correction des numéros de téléphone
                if '+2250787360757' not in corrected:
                    corrected = re.sub(
                        r'\+?225\s*\d{2}\s*\d{2}\s*\d{2}\s*\d{2}\s*\d{2}',
                        '+2250787360757',
                        corrected,
                        count=1
                    )
            
            elif issue.type == IssueType.CALCULATION_ERROR:
                # Correction des calculs (basique)
                if '=' in issue.location:
                    parts = issue.suggestion.split(': ')
                    if len(parts) > 1:
                        correct_result = parts[1]
                        corrected = corrected.replace(issue.location, 
                                                    issue.location.split('=')[0] + '= ' + correct_result)
        
        return corrected
    
    def verify_response(
        self, 
        response: str, 
        context: str, 
        query: str,
        intentions: List[Dict[str, Any]] = None,
        entities: List[Dict[str, Any]] = None
    ) -> VerificationResult:
        """
        ✅ VÉRIFICATION PRINCIPALE DE LA RÉPONSE
        
        Effectue toutes les vérifications et retourne un résultat complet
        """
        logger.info(f"✅ [VERIFY] Début vérification: {len(response)} chars")
        
        all_issues = []
        
        # 1. Vérification factuelle
        factual_issues = self.verify_factual_accuracy(response, context)
        all_issues.extend(factual_issues)
        
        # 2. Vérification des calculs
        calc_issues = self.verify_calculations(response)
        all_issues.extend(calc_issues)
        
        # 3. Détection d'hallucinations
        hallucination_issues = self.detect_hallucinations(response, context, query)
        all_issues.extend(hallucination_issues)
        
        # 4. Calcul du score de qualité
        quality_score = self.calculate_quality_score(response, all_issues)
        
        # 5. Détermination de la validité
        threshold = self.quality_thresholds[self.verification_level]
        is_valid = quality_score >= threshold and not any(
            issue.severity == "critical" for issue in all_issues
        )
        
        # 6. Suggestions de correction
        corrected_response = None
        if not is_valid and any(issue.severity in ["high", "critical"] for issue in all_issues):
            corrected_response = self.suggest_corrections(response, all_issues)
        
        # 7. Métadonnées
        verification_metadata = {
            'verification_level': self.verification_level.value,
            'issues_by_type': {},
            'issues_by_severity': {},
            'response_length': len(response),
            'context_length': len(context),
            'threshold_used': threshold
        }
        
        # Statistiques des issues
        for issue in all_issues:
            issue_type = issue.type.value
            severity = issue.severity
            
            verification_metadata['issues_by_type'][issue_type] = \
                verification_metadata['issues_by_type'].get(issue_type, 0) + 1
            verification_metadata['issues_by_severity'][severity] = \
                verification_metadata['issues_by_severity'].get(severity, 0) + 1
        
        logger.info(f"✅ [VERIFY] Terminé: score={quality_score:.2f}, issues={len(all_issues)}, valid={is_valid}")
        
        return VerificationResult(
            is_valid=is_valid,
            quality_score=quality_score,
            issues=all_issues,
            corrected_response=corrected_response,
            verification_metadata=verification_metadata
        )

# Instance globale
response_verifier = ResponseVerifier()

# Interface simple
def verify_llm_response(
    response: str,
    context: str,
    query: str,
    verification_level: VerificationLevel = VerificationLevel.STANDARD
) -> VerificationResult:
    """Interface simple pour vérification de réponse"""
    verifier = ResponseVerifier(verification_level)
    return verifier.verify_response(response, context, query)

if __name__ == "__main__":
    # Test de vérification
    test_response = """Bonjour ! Pour 3 paquets de couches taille 2, le prix est de 18.900 FCFA par paquet, soit un total de 56.700 FCFA.
    
    Pour la livraison à Cocody, c'est 1500 FCFA.
    
    Total général: 58.200 FCFA
    
    Vous pouvez me contacter au +2250787360757 pour passer commande.
    
    Jessica, votre assistante Rue du Gros"""
    
    test_context = """=== PRODUITS ===
    Couches taille 2: 18.900 FCFA le paquet
    
    === LIVRAISON ===
    Cocody: 1500 FCFA"""
    
    test_query = "3 paquets couches taille 2 livraison Cocody prix total"
    
    result = verify_llm_response(test_response, test_context, test_query)
    
    print(f"\n{'='*60}")
    print(f"TEST VÉRIFICATION RÉPONSE")
    print('='*60)
    print(f"Valide: {result.is_valid}")
    print(f"Score qualité: {result.quality_score:.2f}")
    print(f"Issues détectées: {len(result.issues)}")
    
    for issue in result.issues:
        print(f"- {issue.type.value} ({issue.severity}): {issue.description}")
    
    if result.corrected_response:
        print(f"\nCorrection suggérée:\n{result.corrected_response[:200]}...")
