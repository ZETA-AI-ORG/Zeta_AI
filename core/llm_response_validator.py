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

    # ───────────────────────────
    # Helpers de détection
    # ───────────────────────────

    def _is_clarification_question(self, text: str) -> bool:
        """Détecte si le texte est une question de clarification (pas une affirmation factuelle)."""
        if not text:
            return False

        t = text.lower()
        patterns = [
            r"vous (souhaitez|voulez|désirez)",
            r"(quel|quelle|quels|quelles)[^\n\r\?]*\?",
            r"(comment|où|ou|quand|pourquoi)[^\n\r\?]*\?",
            r"pouvez[- ]vous (préciser|me dire|confirmer)",
            r"est-ce que",
        ]
        return any(re.search(p, t) for p in patterns)
    
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
        errors: List[str] = []
        warnings: List[str] = []
        
        logger.info(f"🛡️ [VALIDATION] Analyse réponse ({len(response)} chars)")

        # ✅ FIX: désactiver la validation hallucination si commande complète
        try:
            if order_state is not None and getattr(order_state, "is_complete", None):
                # order_state est un OrderState, on peut appeler is_complete()
                if callable(order_state.is_complete) and order_state.is_complete():
                    logger.info("🛡️ [VALIDATION] Commande complète détectée → skip validation (post-commande)")
                    return ValidationResult(
                        valid=True,
                        errors=[],
                        warnings=[],
                        should_regenerate=False,
                        correction_prompt=None,
                        metrics={
                            'total_validations': self.validation_count,
                            'hallucinations_detected': self.hallucination_count,
                            'source_errors': self.source_errors_count,
                            'regenerations': self.regeneration_count,
                        },
                    )
        except Exception:
            # En cas de problème, ne pas bloquer la validation normale
            pass
        
        # ═══ EXCEPTIONS PRÉCOCES: QUESTIONS DE CLARIFICATION ═══
        if self._is_clarification_question(response) or (
            thinking and "clarifier" in thinking.lower()
        ):
            logger.info("🛡️ [VALIDATION] Réponse de clarification détectée → pas de régénération")
            return ValidationResult(
                valid=True,
                errors=[],
                warnings=[],
                should_regenerate=False,
                correction_prompt=None,
                metrics={
                    'total_validations': self.validation_count,
                    'hallucinations_detected': self.hallucination_count,
                    'source_errors': self.source_errors_count,
                    'regenerations': self.regeneration_count,
                },
            )

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


def build_system_state_check(context: Dict[str, Any]) -> str:
    try:
        ctx = context if isinstance(context, dict) else {}
        verdict_global = ctx.get("verdict_global") if isinstance(ctx, dict) else None
        verdict_global = verdict_global if isinstance(verdict_global, dict) else {}

        def _sym(status: str) -> str:
            s = str(status or "").upper().strip()
            if s == "VALIDATED":
                return "✅"
            if s in {"INVALID", "REFUSED"}:
                return "❌"
            if s == "MISSING":
                return "∅"
            return "⏳"

        photo = verdict_global.get("photo") or {}
        zone = verdict_global.get("zone") or {}
        tel = verdict_global.get("telephone") or verdict_global.get("tel") or {}
        pay = verdict_global.get("paiement") or verdict_global.get("pay") or {}

        photo_status = _sym((photo.get("status") if isinstance(photo, dict) else ""))
        zone_status = _sym((zone.get("status") if isinstance(zone, dict) else ""))
        tel_status = _sym((tel.get("status") if isinstance(tel, dict) else ""))
        payment_status = _sym((pay.get("status") if isinstance(pay, dict) else ""))

        # SPECS: par défaut, on se base sur l'order_state (si présent dans context)
        specs_status = "∅"
        try:
            order_state = ctx.get("order_state")
            if getattr(order_state, "produit_details", None):
                specs_status = "✅"
        except Exception:
            specs_status = "∅"

        next_step = str(verdict_global.get("next_action") or ctx.get("next_step") or "").strip()
        if not next_step:
            next_step = "COLLECT_PHOTO"

        system_state = (
            "CHECKLIST_SYSTEM_STATE\n"
            f"PHOTO: {photo_status}\n"
            f"SPECS: {specs_status}\n"
            f"ZONE: {zone_status}\n"
            f"TEL: {tel_status}\n"
            f"PAY: {payment_status}\n"
            f"NEXT: {next_step}\n"
        )
        return system_state
    except Exception:
        return ""


def extract_system_state_dict(context: Dict[str, Any]) -> Dict[str, str]:
    try:
        ctx = context if isinstance(context, dict) else {}
        verdict_global = ctx.get("verdict_global") if isinstance(ctx, dict) else None
        verdict_global = verdict_global if isinstance(verdict_global, dict) else {}

        def _sym(status: str) -> str:
            s = str(status or "").upper().strip()
            if s == "VALIDATED":
                return "✅"
            if s in {"INVALID", "REFUSED"}:
                return "❌"
            if s == "MISSING":
                return "∅"
            return "⏳"

        photo = verdict_global.get("photo") or {}
        zone = verdict_global.get("zone") or {}
        tel = verdict_global.get("telephone") or verdict_global.get("tel") or {}
        pay = verdict_global.get("paiement") or verdict_global.get("pay") or {}

        # SPECS: fallback sur order_state si disponible
        specs_status = "∅"
        try:
            order_state = ctx.get("order_state")
            if getattr(order_state, "produit_details", None):
                specs_status = "✅"
        except Exception:
            specs_status = "∅"

        next_step = str(verdict_global.get("next_action") or ctx.get("next_step") or "").strip()
        if not next_step:
            next_step = "COLLECT_PHOTO"

        return {
            "photo_status": _sym((photo.get("status") if isinstance(photo, dict) else "")),
            "zone_status": _sym((zone.get("status") if isinstance(zone, dict) else "")),
            "tel_status": _sym((tel.get("status") if isinstance(tel, dict) else "")),
            "payment_status": _sym((pay.get("status") if isinstance(pay, dict) else "")),
            "specs_status": specs_status,
            "next_step": next_step,
        }
    except Exception:
        return {
            "photo_status": "∅",
            "specs_status": "∅",
            "zone_status": "∅",
            "tel_status": "∅",
            "payment_status": "⏳",
            "next_step": "COLLECT_PHOTO",
        }


class ChecklistLLMResponseValidator:
    FORBIDDEN_PATTERNS = {
        "photo": {
            "∅": [
                r"photo.*(?:reçue?|recu|validée?|validee?|ok)",
                r"✅.*(?:photo|image)",
                r"bien reçu.*image",
                r"image.*claire.*reçue?",
                r"j'ai.*(?:photo|image)",
            ],
            "❌": [
                r"photo.*(?:reçue?|validée?|ok)",
                r"✅.*photo",
            ],
        },
        "zone": {
            "∅": [
                r"(?:parfait|super|noté|note).*(?:pour|livraison à).*(?:cocody|yopougon|abobo|marcory|koumassi|adjamé|adjame|port-?bouet|treichville|plateau|attécoubé|attecoube)",
                r"✅.*(?:commune|zone|livraison)",
                r"on livre à",
                r"livraison.*(?:commune|zone).*✅",
                r"noté pour.*commune",
            ],
            "❌": [
                r"parfait.*livraison",
                r"✅.*commune",
            ],
        },
        "tel": {
            "∅": [
                r"✅.*(?:numéro|numero|téléphone|telephone|contact)",
                r"(?:parfait|super|noté|note).*(?:numéro|numero|téléphone|telephone|contact)",
                r"on te joint au.*0[57]\d{8}",
                r"noté.*(?:0[57]\d{8})",
                r"numéro.*enregistré",
                r"numero.*enregistre",
            ],
            "❌": [
                r"✅.*(?:numéro|numero|téléphone|telephone)",
                r"parfait.*contact",
                r"numéro.*(?:ok|bon|validé)",
                r"numero.*(?:ok|bon|valide)",
            ],
        },
        "payment": {
            "∅": [
                r"(?:paiement|avance|dépôt|depot).*(?:reçu|recu|validé|valide)",
                r"✅.*(?:wave|paiement|avance)",
                r"capture.*reçue",
                r"capture.*recu",
                r"paiement.*confirmé",
                r"paiement.*confirme",
            ],
            "❌": [
                r"paiement.*validé",
                r"paiement.*valide",
                r"✅.*wave",
                r"avance.*ok",
            ],
        },
    }

    FALLBACK_MESSAGES = {
        "photo": "J'aurais besoin d'une image claire du produit qui t'intéresse svp 📸",
        "zone": "Quelle commune d'Abidjan pour la livraison ? (Cocody, Yopougon, Abobo...)",
        "tel": "On te joint à quel numéro svp ?",
        "payment": "Envoie {expected_deposit}F via Wave {company_phone}. Puis envoie la capture de dépôt.",
    }

    def validate_response(self, response: str, system_state: Dict[str, str], context: Optional[Dict[str, Any]] = None) -> str:
        if not response:
            return response

        resp_lc = response.lower()
        state = system_state if isinstance(system_state, dict) else {}

        # Si la réponse est une question (collecte/clarification), on évite de la réécrire.
        # Objectif: ne pas casser des réponses LLM déjà bonnes.
        try:
            if "?" in response or re.search(r"\b(quel|quelle|quels|quelles|où|ou|comment|quand|pourquoi|est-ce que|peux-tu|pouvez-vous)\b", resp_lc):
                return response
        except Exception:
            pass

        next_step = str(state.get("next_step") or "")
        if next_step == "COLLECT_PHOTO":
            if any(
                kw in resp_lc
                for kw in [
                    "commune",
                    "zone",
                    "livraison",
                    "numéro",
                    "numero",
                    "téléphone",
                    "telephone",
                    "wave",
                    "paiement",
                ]
            ):
                logger.warning(
                    "🚨 [CHECKLIST_VALIDATION] NEXT_STEP ignored: NEXT=COLLECT_PHOTO but response asks other fields"
                )
                try:
                    if isinstance(context, dict):
                        context["checklist_rewrite_reason"] = "next_step_ignored_collect_photo"
                except Exception:
                    pass
                return self.FALLBACK_MESSAGES["photo"]

        if next_step == "COLLECT_ZONE" and str(state.get("photo_status")) != "✅":
            logger.warning("🚨 [CHECKLIST_VALIDATION] Incoherence: NEXT=COLLECT_ZONE but PHOTO!=✅")
            try:
                if isinstance(context, dict):
                    context["checklist_rewrite_reason"] = "incoherence_collect_zone_photo_missing"
            except Exception:
                pass
            return self.FALLBACK_MESSAGES["photo"]

        if next_step in {"COLLECT_TEL", "VALIDATE_TEL"} and str(state.get("zone_status")) != "✅":
            logger.warning("🚨 [CHECKLIST_VALIDATION] Incoherence: NEXT=%s but ZONE!=✅", next_step)
            try:
                if isinstance(context, dict):
                    context["checklist_rewrite_reason"] = "incoherence_collect_tel_zone_missing"
            except Exception:
                pass
            return self.FALLBACK_MESSAGES["zone"]

        if next_step == "COLLECT_SPECS" and str(state.get("photo_status")) != "✅":
            logger.warning("🚨 [CHECKLIST_VALIDATION] Incoherence: NEXT=COLLECT_SPECS but PHOTO!=✅")
            try:
                if isinstance(context, dict):
                    context["checklist_rewrite_reason"] = "incoherence_collect_specs_photo_missing"
            except Exception:
                pass
            return self.FALLBACK_MESSAGES["photo"]

        # Réécriture uniquement en cas d'affirmation de validation (pas juste un mot "livraison" dans une question).
        validation_markers = ["✅", "validé", "valide", "confirmé", "confirme", "enregistré", "enregistre", "noté", "note", "parfait"]

        for field, status_key in [
            ("photo", "photo_status"),
            ("specs", "specs_status"),
            ("zone", "zone_status"),
            ("tel", "tel_status"),
            ("payment", "payment_status"),
        ]:
            current_status = str(state.get(status_key, "∅"))
            if current_status in {"∅", "❌"}:
                if not any(m in response for m in validation_markers):
                    continue
                patterns = self.FORBIDDEN_PATTERNS.get(field, {}).get(current_status, [])
                for pattern in patterns:
                    if re.search(pattern, resp_lc):
                        logger.warning(
                            "🚨 [CHECKLIST_VALIDATION] Hallucination: field=%s status=%s pattern=%s",
                            field,
                            current_status,
                            pattern,
                        )

                        try:
                            if isinstance(context, dict):
                                context["checklist_rewrite_reason"] = f"hallucination_{field}_{current_status}"
                        except Exception:
                            pass

                        fallback = self.FALLBACK_MESSAGES.get(field, "")
                        if field == "payment":
                            ctx = context if isinstance(context, dict) else {}
                            fallback = fallback.format(
                                expected_deposit=str(ctx.get("expected_deposit") or "2000"),
                                company_phone=str(ctx.get("company_phone") or COMPANY_PHONES.get("wave") or "0787360757"),
                            )
                        return fallback or response

        return response


_checklist_validator = ChecklistLLMResponseValidator()


def validate_llm_response_checklist(
    response: str,
    system_state: Dict[str, str],
    context: Optional[Dict[str, Any]] = None,
) -> str:
    return _checklist_validator.validate_response(response, system_state, context)
