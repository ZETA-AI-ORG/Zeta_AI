#!/usr/bin/env python3
"""
🤖 BOTLIVE RAG HYBRID - Système hybride DeepSeek V3 + Groq 70B
Intégration du routeur intelligent avec prompts spécialisés et outils
"""

import os
import re
import re as regex
import json
import logging
import asyncio
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from app_utils import log3
from core.timezone_helper import (
    get_current_time_ci,
    is_same_day_delivery_possible,
    get_delivery_context_with_time,
)

# Imports locaux
from .hyde_smart_router import hyde_router
from .botlive_prompts_supabase import get_prompts_manager  # ← NOUVEAU: Supabase au lieu de hardcodé
from .botlive_tools import execute_tools_in_response, should_suggest_calculator, should_suggest_notepad
from core.loop_botlive_engine import get_loop_engine

logger = logging.getLogger(__name__)

# Activation du court-circuit Python (forcé à True pour Botlive)
ENABLE_PYTHON_DIRECT = False

class BotliveRAGHybrid:
    """
    Système RAG hybride pour Botlive avec routage intelligent
    """
    
    def __init__(self, company_id: str = None):
        self.router = hyde_router
        self.company_id = company_id  # ← NOUVEAU: Stocker company_id
        
        # Initialiser le gestionnaire de prompts avec fallback
        try:
            self.prompts_manager = get_prompts_manager()
            if self.prompts_manager:
                logger.info("✅ [BOTLIVE_HYBRID] Prompts manager Supabase activé")
            else:
                logger.warning("⚠️ [BOTLIVE_HYBRID] Prompts manager None - Utilisation hardcodés")
        except Exception as e:
            logger.error(f"❌ [BOTLIVE_HYBRID] Erreur init prompts_manager: {e}")
            self.prompts_manager = None
        
        self.stats = {
            'total_requests': 0,
            'primary_llm_requests': 0,  # Groq 70B principal
            'fallback_llm_requests': 0,  # Fallback éventuel
            'tools_used': 0,
            'fallbacks': 0
        }
    
    def _categorize_post_order_message(self, message: str) -> str:
        """Catégorise un message post-commande sans LLM."""
        msg = (message or "").lower().strip()

        if any(w in msg for w in ["ok", "merci", "oui", "d'accord", "👍", "✅"]) and len(msg) < 25:
            return "CONFIRMATION"

        if any(w in msg for w in ["quand", "délai", "delai", "livraison", "livré", "livre", "arriver", "recevoir"]):
            return "DELAI"

        if any(w in msg for w in ["paiement", "payer", "avant", "après", "apres", "modalité", "modalite"]):
            return "PAIEMENT"

        if any(w in msg for w in ["récap", "recap", "résumé", "resume", "confirmez", "confirmation", "c'est bon", "cest bon"]):
            return "RECAP"

        if len(msg) < 3 or msg in [".", "..", "..."]:
            return "SILENCE"

        return "AUTRE"
        
    async def process_request(self, 
                            user_id: str,
                            message: str, 
                            context: Dict[str, Any],
                            conversation_history: str = "",
                            company_id: str = None) -> Dict[str, Any]:
        """
        Traite une requête avec le système hybride
        
        Args:
            user_id: Identifiant utilisateur
            message: Message utilisateur
            context: Contexte (vision, transactions, etc.)
            conversation_history: Historique conversation
        
        Returns:
            Dict: Réponse complète avec métadonnées
        """
        import os

        # Propager le company_id reçu dans l'instance (utile pour logs et fallback)
        if company_id and company_id != self.company_id:
            self.company_id = company_id

        print("\n========== DEBUG BOTLIVE SUPABASE ==========")
        print(f"SUPABASE_URL: {os.getenv('SUPABASE_URL')}")
        _svc = os.getenv('SUPABASE_SERVICE_KEY')
        if _svc and len(_svc) > 12:
            _svc = _svc[:6] + "..." + _svc[-4:]
        print(f"SUPABASE_SERVICE_KEY: {_svc if _svc else 'MISSING'}")
        print(f"prompts_manager: {self.prompts_manager}")
        print(f"company_id reçu: {company_id} | self.company_id: {self.company_id}")
        print("============================================\n")

        # Sécuriser le contexte
        if context is None:
            context = {}

        # Délai de livraison dynamique (aujourd'hui/demain) basé sur l'heure CI
        try:
            now_ci = get_current_time_ci()
            delai = "aujourd'hui" if is_same_day_delivery_possible() else "demain"
        except Exception:
            now_ci = None
            delai = ""

        try:
            delivery_context_val = get_delivery_context_with_time()
        except Exception:
            delivery_context_val = ""

        if delai:
            context.setdefault("delai_message", delai)
        if delivery_context_val:
            context.setdefault("delivery_context", delivery_context_val)

        start_time = datetime.now()
        timings = {}  # Track temps par étape
        python_short_circuit = False
        
        try:
            # ═══ ÉTAPE 1: LLM FIXE POUR BOTLIVE (Groq 70B) ═══
            step_start = datetime.now()
            llm_choice = "openrouter" if os.getenv("OPENROUTER_API_KEY") else "groq-70b"
            prompt_llm_choice = "groq-70b"
            routing_reason = "botlive_openrouter" if llm_choice == "openrouter" else "botlive_fixed_groq_70b"
            router_metrics: Dict[str, Any] = {}
            timings["routing"] = (datetime.now() - step_start).total_seconds()
            
            logger.info(f"🎯 [BOTLIVE] Routage fixe: {llm_choice}")
            
            # ═══ ÉTAPE 1.5: VALIDATION AUTOMATIQUE PAIEMENT ═══
            payment_validation = None
            if context.get('filtered_transactions'):
                from core.payment_validator import validate_payment_cumulative, format_payment_for_prompt
                
                # Extraire montant requis du contexte (dynamique)
                expected_deposit_str = context.get('expected_deposit', '2000 FCFA')
                try:
                    m = regex.search(r'(\d+)', expected_deposit_str)
                    required_amount = int(m.group(1)) if m else 2000
                except Exception:
                    required_amount = 2000
                
                payment_validation = validate_payment_cumulative(
                    current_transactions=context.get('filtered_transactions', []),
                    conversation_history=conversation_history,
                    required_amount=required_amount
                )
                
                logger.info(f"💰 Validation paiement: {payment_validation['message']}")
                
                # Ajouter au contexte pour le prompt
                context['payment_validation'] = payment_validation
                
                # 🔥 CORRECTION CRITIQUE: Persister le paiement validé dans order_state
                if payment_validation.get('valid'):
                    from core.order_state_tracker import order_tracker
                    total_received = payment_validation.get('total_received', 0)
                    order_tracker.update_paiement(user_id, f"validé_{total_received}F")
                    logger.info(f"✅ [PERSISTENCE] Paiement {total_received}F sauvegardé pour {user_id}")
            
            # === DÉTECTION DIRECTE ET COURT-CIRCUIT PYTHON ===
            from core.delivery_zone_extractor import extract_delivery_zone_and_cost
            from core.order_state_tracker import order_tracker as _ot
            from core.loop_botlive_engine import get_loop_engine
            state = _ot.get_state(user_id)

            # 0. Intent embeddings "délai de livraison" → Python si score ≥ 0.80 (commande en cours)
            delay_similarity = 0.0
            try:
                from core.botlive_intent_router import get_delivery_delay_similarity
                delay_similarity = float(get_delivery_delay_similarity(message))
            except Exception:
                delay_similarity = 0.0

            if (not state.is_complete()) and delay_similarity >= 0.80:
                try:
                    delai_auto = "aujourd'hui" if is_same_day_delivery_possible() else "demain"
                except Exception:
                    from datetime import datetime as _dt
                    heure_tmp = _dt.now().hour
                    delai_auto = "aujourd'hui" if heure_tmp < 13 else "demain"

                zone_name = state.zone or "votre zone"
                processed_response = (
                    f"Pour une commande standard, la livraison pour {zone_name} est généralement prévue {delai_auto}. "
                    "Le livreur vous contactera pour préciser l'heure exacte 😊"
                )

                end_time = datetime.now()
                processing_time = (end_time - start_time).total_seconds()

                return {
                    'response': processed_response,
                    'thinking': "",
                    'llm_used': 'python',
                    'validation': None,
                    'routing_reason': 'python_delivery_delay_high_conf',
                    'processing_time': processing_time,
                    'timings': timings,
                    'router_metrics': {'delivery_delay_similarity': delay_similarity},
                    'tools_executed': False,
                    'prompt_tokens': 0,
                    'completion_tokens': 0,
                    'total_cost': 0,
                    'success': True
                }

            # Court-circuit post-commande : 100% géré par Python (sans LLM)
            if state.is_complete():
                intent_post = self._categorize_post_order_message(message)

                # Construction réponses Python simples
                if intent_post == "CONFIRMATION":
                    processed_response = "Parfait ! On vous rappelle très vite 😊"
                elif intent_post == "DELAI":
                    zone_name = state.zone or "votre zone"
                    processed_response = f"Livraison {zone_name} sous 24-48h. On confirme avec vous."
                elif intent_post == "PAIEMENT":
                    montant = 0
                    try:
                        paiement_str = state.paiement or ""
                        m = regex.search(r"(\d+)", str(paiement_str))
                        montant = int(m.group(1)) if m else 0
                    except Exception:
                        pass
                    if montant > 0:
                        processed_response = f"Paiement avant livraison. Votre acompte de {montant}F est validé ✅"
                    else:
                        processed_response = "Paiement avant livraison. Votre acompte est bien validé ✅"
                elif intent_post == "RECAP":
                    montant = 0
                    try:
                        paiement_str = state.paiement or ""
                        m = regex.search(r"(\d+)", str(paiement_str))
                        montant = int(m.group(1)) if m else 0
                    except Exception:
                        pass
                    try:
                        delai_po = "aujourd'hui" if is_same_day_delivery_possible() else "demain"
                    except Exception:
                        from datetime import datetime as _dt
                        heure_actuelle_po = _dt.now().hour
                        delai_po = "aujourd'hui" if heure_actuelle_po < 13 else "demain"
                    if montant <= 0:
                        montant = 2000
                    processed_response = (
                        f"✅PARFAIT Commande confirmée 😊\n"
                        f"Livraison prévue {delai_po}, acompte de {montant} F déjà versé.\n"
                        "Nous vous rappellerons bientôt pour les détails et le coût total.\n"
                        "Veuillez ne pas répondre à ce message."
                    )
                elif intent_post == "SILENCE":
                    processed_response = ""
                else:  # AUTRE → escalade opérateur
                    processed_response = "Un collègue reprend avec vous sous peu pour finaliser."

                end_time = datetime.now()
                processing_time = (end_time - start_time).total_seconds()

                return {
                    'response': processed_response,
                    'thinking': "",
                    'llm_used': 'python',
                    'validation': None,
                    'routing_reason': f'post_order_{intent_post.lower()}',
                    'processing_time': processing_time,
                    'timings': timings,
                    'router_metrics': {'post_order_intent': intent_post},
                    'tools_executed': False,
                    'prompt_tokens': 0,
                    'completion_tokens': 0,
                    'total_cost': 0,
                    'success': True
                }

            # Helpers
            def _safe_conf(val, default: float = 0.6) -> float:
                try:
                    if val is None:
                        return default
                    if isinstance(val, (int, float)):
                        return float(val)
                    s = str(val).strip().lower()
                    if s in ("high", "haut", "élevé", "eleve"):
                        return 0.9
                    if s in ("medium", "moyen"):
                        return 0.7
                    if s in ("low", "faible"):
                        return 0.5
                    return float(s)
                except Exception:
                    return default

            def _required_amount_from_context(ctx: Dict[str, Any]) -> int:
                try:
                    expected_deposit_str = ctx.get('expected_deposit', '2000 FCFA')
                    m = regex.search(r'(\d+)', str(expected_deposit_str))
                    return int(m.group(1)) if m else 2000
                except Exception:
                    return 2000

            # 1. Détection zone
            zone_info = extract_delivery_zone_and_cost(message)
            if zone_info and zone_info.get('name'):
                zone_name = zone_info['name']
                cost = zone_info.get('cost', 1500)
                _ot.update_zone(user_id, zone_name)
                logger.info(f"[PYTHON_DIRECT][ZONE] Zone détectée: {zone_name} ({cost}F)")
                engine = get_loop_engine()
                # Ajout des champs obligatoires pour TriggerValidator
                periph = {"port-bouët", "attécoubé", "bingerville", "songon", "anyama", "port-bouet", "attecoube"}
                centrale_zones = {"plateau", "cocody", "marcory", "koumassi", "treichville"}
                if zone_name and zone_name.lower() in centrale_zones:
                    category = "centrale"
                elif zone_name and zone_name.lower() in periph:
                    category = "peripherique"
                else:
                    category = "expedition"
                source = "delivery_info" if isinstance(zone_info, dict) else "regex_message"
                confidence = _safe_conf(zone_info.get('confidence'), 0.9) if isinstance(zone_info, dict) else 0.6
                trigger = {
                    'type': 'zone_detectee',
                    'data': {
                        'zone': zone_name,
                        'cost': cost,
                        'name': zone_name,
                        'category': category,
                        'source': source,
                        'confidence': confidence,
                    }
                }
                loop_state = self._build_loop_state(_ot.get_state(user_id), context)
                python_resp = engine._python_auto_response(trigger, loop_state, message)
                if python_resp and python_resp != "llm_takeover":
                    return {
                        'response': python_resp,
                        'thinking': '',
                        'llm_used': 'python',
                        'routing_reason': 'python_direct_zone',
                        'processing_time': 0.0,
                        'timings': timings,
                        'router_metrics': {'python_direct_zone': True},
                        'tools_executed': False,
                        'prompt_tokens': 0,
                        'completion_tokens': 0,
                        'total_cost': 0,
                        'success': True
                    }

            # 2. Détection numéro
            message_text = context.get('message', message) or ''
            import re as regex
            numero_patterns = [
                r'\+225\s?0?([157]\d{8})',
                r'\b(0[157]\d{8})\b',
                r'\b0([157])\s?(\d{2})\s?(\d{2})\s?(\d{2})\s?(\d{2})\b'
            ]
            numero = None
            for pattern in numero_patterns:
                match = regex.search(pattern, message_text)
                if match:
                    if len(match.groups()) == 1:
                        numero = f"0{match.group(1)}" if not match.group(1).startswith('0') else f"{match.group(1)}"
                    else:
                        numero = f"0{''.join(match.groups())}"
                    break
            if numero:
                _ot.update_numero(user_id, numero)
                logger.info(f"[PYTHON_DIRECT][TEL] Numéro détecté: {numero}")
                engine = get_loop_engine()
                after_state = _ot.get_state(user_id)
                tel_len = len(numero)
                tel_valid = bool(tel_len == 10 and numero.startswith('0'))
                tel_data = {
                    'raw': message_text,
                    'clean': numero,
                    'valid': tel_valid,
                    'length': tel_len,
                    'format_error': None,
                }
                if not tel_valid:
                    if tel_len < 10:
                        tel_data['format_error'] = 'TOO_SHORT'
                    elif tel_len > 10:
                        tel_data['format_error'] = 'TOO_LONG'
                    elif not numero.startswith('0'):
                        tel_data['format_error'] = 'WRONG_PREFIX'
                    else:
                        tel_data['format_error'] = 'INVALID_FORMAT'
                trigger_type = 'telephone_final' if (tel_valid and after_state.produit and after_state.paiement and after_state.zone) else 'telephone_detecte'
                trigger = {'type': trigger_type, 'data': tel_data}
                loop_state = self._build_loop_state(after_state, context)
                python_resp = engine._python_auto_response(trigger, loop_state, message)
                if python_resp and python_resp != "llm_takeover":
                    return {
                        'response': python_resp,
                        'thinking': '',
                        'llm_used': 'python',
                        'routing_reason': 'python_direct_tel',
                        'processing_time': 0.0,
                        'timings': timings,
                        'router_metrics': {'python_direct_tel': True},
                        'tools_executed': False,
                        'prompt_tokens': 0,
                        'completion_tokens': 0,
                        'total_cost': 0,
                        'success': True
                    }

            # 3. Détection PRODUIT depuis contexte (BLIP déjà exécuté en amont)
            detected_objects_ctx = context.get('detected_objects') or context.get('vision_objects') or []
            if isinstance(detected_objects_ctx, list) and detected_objects_ctx:
                def _obj_conf(o):
                    try:
                        if isinstance(o, dict):
                            return _safe_conf(o.get('confidence'), 0.8)
                        return 0.0
                    except Exception:
                        return 0.0
                # Normaliser name/label
                def _obj_name(o):
                    if isinstance(o, dict):
                        return o.get('name') or o.get('label') or o.get('type') or 'Produit détecté'
                    return str(o)
                best = max(detected_objects_ctx, key=_obj_conf)
                best_conf = _obj_conf(best)
                if best_conf >= 0.7:
                    produit_name = _obj_name(best)
                    _ot.update_produit(user_id, produit_name)
                    logger.info(f"[PYTHON_DIRECT][PHOTO] Produit détecté (ctx): {produit_name} ({best_conf:.2f})")
                    engine = get_loop_engine()
                    photo_data = {
                        'description': produit_name,
                        'confidence': best_conf,
                        'error': None,
                        'valid': True,
                        'product_detected': True,
                    }
                    trigger = {'type': 'photo_produit', 'data': photo_data}
                    loop_state = self._build_loop_state(_ot.get_state(user_id), context)
                    python_resp = engine._python_auto_response(trigger, loop_state, message)
                    if python_resp and python_resp != "llm_takeover":
                        return {
                            'response': python_resp,
                            'thinking': '',
                            'llm_used': 'python',
                            'routing_reason': 'python_direct_photo_ctx',
                            'processing_time': 0.0,
                            'timings': timings,
                            'router_metrics': {'python_direct_photo': True},
                            'tools_executed': False,
                            'prompt_tokens': 0,
                            'completion_tokens': 0,
                            'total_cost': 0,
                            'success': True
                        }

            # 3bis. Détection PAIEMENT depuis contexte (OCR déjà exécuté en amont)
            filtered_ctx = context.get('filtered_transactions') or []
            if isinstance(filtered_ctx, list) and filtered_ctx:
                try:
                    montant_ctx = int((filtered_ctx[0] or {}).get('amount', 0) or 0)
                except Exception:
                    try:
                        montant_ctx = int(str((filtered_ctx[0] or {}).get('amount', '0')).strip())
                    except Exception:
                        montant_ctx = 0
                _ot.update_paiement(user_id, f"{montant_ctx}F")
                logger.info(f"[PYTHON_DIRECT][PAIEMENT] Montant détecté (ctx): {montant_ctx}F")
                engine = get_loop_engine()
                req_amt = _required_amount_from_context(context)
                sufficient_ctx = bool(montant_ctx >= req_amt)
                pay_data_ctx = {
                    'amount': montant_ctx,
                    'valid': bool(montant_ctx > 0),
                    'error': None,
                    'currency': 'FCFA',
                    'transactions': filtered_ctx or [],
                    'raw_text': '',
                    'sufficient': sufficient_ctx,
                }
                trigger = {'type': 'paiement_ocr', 'data': pay_data_ctx}
                loop_state = self._build_loop_state(_ot.get_state(user_id), context)
                python_resp = engine._python_auto_response(trigger, loop_state, message)
                if python_resp and python_resp != "llm_takeover":
                    return {
                        'response': python_resp,
                        'thinking': '',
                        'llm_used': 'python',
                        'routing_reason': 'python_direct_paiement_ctx',
                        'processing_time': 0.0,
                        'timings': timings,
                        'router_metrics': {'python_direct_paiement': True},
                        'tools_executed': False,
                        'prompt_tokens': 0,
                        'completion_tokens': 0,
                        'total_cost': 0,
                        'success': True
                    }

            # 4. Détection images (produit/paiement) si non fourni par contexte
            images = context.get('images', [])
            if images:
                vision_result = await self._process_images(images, context)
                detected_objects = vision_result.get('detected_objects', [])
                filtered_transactions = vision_result.get('filtered_transactions', [])
                # Produit
                if detected_objects:
                    best_product = max(detected_objects, key=lambda x: x.get('confidence', 0))
                    if best_product.get('confidence', 0) >= 0.7:
                        produit_name = best_product.get('name', 'Produit détecté')
                        _ot.update_produit(user_id, produit_name)
                        logger.info(f"[PYTHON_DIRECT][PHOTO] Produit détecté: {produit_name}")
                        engine = get_loop_engine()
                        conf_val = _safe_conf(best_product.get('confidence'), 0.8)
                        photo_data = {
                            'description': produit_name,
                            'confidence': conf_val,
                            'error': None,
                            'valid': True,
                            'product_detected': True,
                        }
                        trigger = {'type': 'photo_produit', 'data': photo_data}
                        loop_state = self._build_loop_state(_ot.get_state(user_id), context)
                        python_resp = engine._python_auto_response(trigger, loop_state, message)
                        if python_resp and python_resp != "llm_takeover":
                            return {
                                'response': python_resp,
                                'thinking': '',
                                'llm_used': 'python',
                                'routing_reason': 'python_direct_photo',
                                'processing_time': 0.0,
                                'timings': timings,
                                'router_metrics': {'python_direct_photo': True},
                                'tools_executed': False,
                                'prompt_tokens': 0,
                                'completion_tokens': 0,
                                'total_cost': 0,
                                'success': True
                            }
                # Paiement
                if filtered_transactions:
                    best_payment = filtered_transactions[0]
                    try:
                        montant = int(best_payment.get('amount', 0) or 0)
                    except Exception:
                        try:
                            montant = int(str(best_payment.get('amount', '0')).strip())
                        except Exception:
                            montant = 0
                    _ot.update_paiement(user_id, f"{montant}F")
                    logger.info(f"[PYTHON_DIRECT][PAIEMENT] Montant détecté: {montant}F")
                    engine = get_loop_engine()
                    req_amt = _required_amount_from_context(context)
                    sufficient = bool(montant >= req_amt)
                    pay_data = {
                        'amount': montant,
                        'valid': bool(montant > 0),
                        'error': None,
                        'currency': 'FCFA',
                        'transactions': filtered_transactions or [],
                        'raw_text': '',
                        'sufficient': sufficient,
                    }
                    trigger = {'type': 'paiement_ocr', 'data': pay_data}
                    loop_state = self._build_loop_state(_ot.get_state(user_id), context)
                    python_resp = engine._python_auto_response(trigger, loop_state, message)
                    if python_resp and python_resp != "llm_takeover":
                        return {
                            'response': python_resp,
                            'thinking': '',
                            'llm_used': 'python',
                            'routing_reason': 'python_direct_paiement',
                            'processing_time': 0.0,
                            'timings': timings,
                            'router_metrics': {'python_direct_paiement': True},
                            'tools_executed': False,
                            'prompt_tokens': 0,
                            'completion_tokens': 0,
                            'total_cost': 0,
                            'success': True
                        }
            # Si aucune détection, continuer flow (LLM)
            
            # ═══ ÉTAPE 2: GÉNÉRATION PROMPT SPÉCIALISÉ ═══
            step_start = datetime.now()
            
            # Préparer les données pour le prompt (optimisé tokens)
            raw_transactions = context.get('filtered_transactions', [])
            # Transactions COMPACTES (top 2)
            if isinstance(raw_transactions, list) and raw_transactions:
                top = raw_transactions[:2]
                compact_entries = []
                for t in top:
                    try:
                        amt = str(t.get('amount', '0'))
                        phone = str(t.get('phone', ''))
                        phone_short = f"…{phone[-4:]}" if phone and len(phone) >= 4 else phone
                        compact_entries.append(f"{amt}F:+225{phone_short}")
                    except Exception:
                        continue
                compact_transactions = ", ".join(compact_entries) if compact_entries else "0F"
            else:
                compact_transactions = "0F"

            # Si paiement validé automatiquement, enrichir le prompt
            if payment_validation:
                validation_message = format_payment_for_prompt(payment_validation)
                compact_transactions = f"{compact_transactions} | {validation_message}" if compact_transactions else validation_message
                logger.info(f"💳 Message validation ajouté au prompt: {validation_message[:150]}...")

            logger.debug(f"📋 TRANSACTIONS envoyées au LLM (compact): {compact_transactions[:300]}...")
            
            # ═══ RÉCUPÉRATION ÉTAT COMMANDE (MÉMOIRE CONTEXTE) ═══
            from core.order_state_tracker import order_tracker
            state = order_tracker.get_state(user_id)
            state_before = state
            state_was_complete = bool(state.is_complete())
            missing = state.get_missing_fields()
            
            # Résumé état COMPACT (éviter doublons avec règles Jessica)
            state_resume = (
                "ETAT_COMMANDE:\n"
                f"- produit:{'✅ ' + state.produit if state.produit else '❌'}  "
                f"- paiement:{'✅ ' + state.paiement if state.paiement else '❌'}  "
                f"- zone:{'✅ ' + state.zone if state.zone else '❌'}  "
                f"- tel:{'✅ ' + state.numero if state.numero else '❌'}\n"
            )

            # Checklist COMPACTE
            missing_list = []
            if not state.produit:
                missing_list.append('photo')
            if not state.paiement:
                missing_list.append('paiement')
            if not state.zone:
                missing_list.append('zone')
            if not (state.numero and getattr(state, 'tel_valide', False)):
                missing_list.append('tel')
            compact_checklist = f"CHECKLIST: MISSING=[{', '.join(missing_list) if missing_list else 'aucun'}]"
            
            logger.info(f"📊 [ORDER_STATE] État pour {user_id}:")
            logger.info(f"   - Produit: {state.produit or 'NON COLLECTÉ'}")
            logger.info(f"   - Paiement: {state.paiement or 'NON COLLECTÉ'}")
            logger.info(f"   - Zone: {state.zone or 'NON COLLECTÉ'}")
            logger.info(f"   - Numéro: {state.numero or 'NON COLLECTÉ'}")
            
            # 06a NOUVEAU: Re9cupe9rer prompt brut depuis Supabase (Jessica)
            # Utiliser company_id du parame8tre ou de l'instance
            active_company_id = company_id or self.company_id
            if not active_company_id:
                raise ValueError("10 company_id requis pour re9cupe9rer les prompts Botlive")

            # Injecter le contexte delivery dans la question si disponible
            delivery_context = context.get('delivery_context', '')
            question_with_delivery = message
            if delivery_context:
                question_with_delivery = f"{delivery_context}\n\n{message}"
                logger.info(f"8 [DELIVERY] Question enrichie avec contexte delivery ({len(question_with_delivery)} chars)")

            # 02 HYDE-LIKE: Ajouter une hypothe8se d'intent pour guider le LLM (sans retrieval)
            try:
                from core.intent_hypothesis import build_intent_hypothesis
                hyp = build_intent_hypothesis(message)
                if hyp:
                    question_with_delivery = f"{hyp}\n\n{question_with_delivery}"
                    logger.info(f"8 [HYPOTHESIS] Bloc intent ajoute9 ({len(hyp)} chars)")
            except Exception as e:
                logger.warning(f"1f [HYPOTHESIS] Erreur injection: {e}")

            logger.info(f" [BOTLIVE] Re9cupe9ration prompt (Jessica) pour company_id={active_company_id}, llm={prompt_llm_choice}")

            # Ve9rifier si prompts_manager est disponible
            if not self.prompts_manager:
                logger.error(" [BOTLIVE] prompts_manager est None - Impossible de re9cupe9rer le prompt")
                raise ValueError("Prompts manager non initialise9 - Utiliser fallback _botlive_handle")

            # 06a Re9cupe9ration PROMPT + ROUTER EMBEDDINGS + JESSICA + HYDE SECOUR X 06a
            try:
                from core.botlive_intent_router import route_botlive_intent
                from core.jessica_prompt_segmenter import build_jessica_prompt_segment
                from core.hyde_secour_x import run_hyde_secour_x

                # 1) Template brut Supabase pour Jessica (sans formatage global)
                # llm_choice="groq-70b" → lit prompt_botlive_groq_70b dans company_rag_configs
                base_prompt_template = self.prompts_manager.get_prompt(active_company_id, prompt_llm_choice)
                base_prompt_template = base_prompt_template

                # 2) Construire state_compact pour le router embeddings
                state_compact = {
                    "photo_collected": bool(state.produit),
                    "paiement_collected": bool(state.paiement),
                    "zone_collected": bool(state.zone),
                    "tel_collected": bool(state.numero),
                    "tel_valide": bool(state.numero),
                    "collected_count": int(
                        bool(state.produit)
                        + bool(state.paiement)
                        + bool(state.zone)
                        + bool(state.numero)
                    ),
                    "is_complete": bool(state.is_complete()),
                }

                routing = await route_botlive_intent(
                    company_id=active_company_id,
                    user_id=user_id,
                    message=message,
                    conversation_history=conversation_history or "",
                    state_compact=state_compact,
                )

                logger.info(
                    " [EMB_ROUTER] intent=%s mode=%s conf=%.3f missing=%s",
                    routing.intent,
                    routing.mode,
                    routing.confidence,
                    routing.missing_fields,
                )
                try:
                    log3(
                        "EMB_ROUTER",
                        {
                            "intent": routing.intent,
                            "confidence": routing.confidence,
                            "mode": routing.mode,
                            "missing_fields": routing.missing_fields,
                            "state_compact": routing.state,
                            "intent_score": routing.debug.get("intent_score"),
                            "raw_message": routing.debug.get("raw_message"),
                        },
                    )
                except Exception:
                    pass

                # hyde_result structure compatible avec build_jessica_prompt_segment
                hyde_result = {
                    "success": True,
                    "intent": routing.intent,
                    "confidence": routing.confidence,
                    "mode": routing.mode,
                    "missing_fields": routing.missing_fields,
                    "state": routing.state,
                    "raw": routing.debug.get("raw_message", ""),
                    "token_info": {
                        "source": "router_embeddings",
                        "intent_score": routing.debug.get("intent_score"),
                    },
                }

                # 3) Premier passage Jessica pour obtenir le gating_path
                detected_objects_str = self._format_detected_objects(
                    context.get("detected_objects", [])
                )
                expected_deposit_str = context.get("expected_deposit", "2000 FCFA")

                # Troncature HISTORY (≈200 tokens ≈ 800 chars)
                truncated_history = (conversation_history or "")
                if len(truncated_history) > 800:
                    truncated_history = "…" + truncated_history[-800:]

                segment = build_jessica_prompt_segment(
                    base_prompt_template=base_prompt_template,
                    hyde_result=hyde_result,
                    question_with_context=question_with_delivery,
                    conversation_history=truncated_history,
                    detected_objects_str=detected_objects_str,
                    filtered_transactions_str=compact_transactions or "0F",
                    expected_deposit_str=expected_deposit_str,
                    enriched_checklist="",
                    routing=routing,
                    delai_message=context.get("delai_message", ""),
                )

                gating_path = segment.get("gating_path", "standard")
                logger.info(
                    " [JESSICA] gating_path=%s letter=%s conf=%.3f",
                    gating_path,
                    segment.get("segment_letter"),
                    float(segment.get("confidence") or 0.0),
                )

                # 4) HYDE SECOUR X si gating_path == "hyde"
                if gating_path == "hyde":
                    try:
                        required_amount = required_amount if "required_amount" in locals() else 2000
                    except Exception:
                        required_amount = 2000

                    try:
                        hyde_raw = await run_hyde_secour_x(
                            base_prompt_template=base_prompt_template,
                            question=message,
                            conversation_history=conversation_history or "",
                            checklist=routing.state,
                            state=routing.state,
                            intent=routing.intent,
                            confidence=routing.confidence,
                            mode=routing.mode,
                            missing_fields=routing.missing_fields,
                            detected_objects=detected_objects_str,
                            filtered_transactions=compact_transactions or "0F",
                            expected_deposit=str(required_amount),
                        )

                        # Parse JSON minimal: {"hyde_question": "..."}
                        hyde_payload = None
                        try:
                            json_start = hyde_raw.find("{")
                            json_end = hyde_raw.rfind("}")
                            if (
                                json_start != -1
                                and json_end != -1
                                and json_end > json_start
                            ):
                                import json as _json

                                hyde_payload = _json.loads(
                                    hyde_raw[json_start : json_end + 1]
                                )
                        except Exception as parse_e:
                            logger.warning(
                                " [HYDE_X] Erreur parse JSON HYDE SECOUR X: %s",
                                parse_e,
                            )

                        if isinstance(hyde_payload, dict):
                            hyde_question = hyde_payload.get("hyde_question")
                            if isinstance(hyde_question, str) and hyde_question.strip():
                                original_text = (message or "").strip()
                                original_lower = original_text.lower()
                                hq = hyde_question.strip()
                                hq_lower = hq.lower()

                                allow = True

                                has_photo = bool(state_compact.get("photo_collected", False))
                                has_payment = bool(state_compact.get("paiement_collected", False))

                                purchase_markers = [
                                    "commander",
                                    "acheter",
                                    "passer commande",
                                    "passe commande",
                                    "je prends",
                                    "je veux commander",
                                ]
                                orig_has_purchase = any(m in original_lower for m in purchase_markers)
                                hyde_has_purchase = any(m in hq_lower for m in purchase_markers)
                                if hyde_has_purchase and (not orig_has_purchase) and (not has_photo) and (not has_payment):
                                    allow = False

                                if ("couch" in original_lower or "lait" in original_lower) and not (
                                    ("couch" in hq_lower) or ("lait" in hq_lower)
                                ):
                                    allow = False

                                import re as _re
                                orig_digits = _re.findall(r"\d{6,}", original_text)
                                if orig_digits and not any(d in hq for d in orig_digits):
                                    allow = False

                                if ("où" in original_lower or "sit" in original_lower) and (
                                    "adresse" in hq_lower and ("vous" not in hq_lower)
                                ):
                                    allow = False

                                # Reroute embeddings sur la reformulation HYDE, sans HYDE_PRE (évite boucle LLM)
                                try:
                                    if allow:
                                        reroute = await route_botlive_intent(
                                            company_id=active_company_id,
                                            user_id=user_id,
                                            message=hq,
                                            conversation_history=conversation_history or "",
                                            state_compact=state_compact,
                                            hyde_pre_enabled=False,
                                        )

                                        base_conf = float(routing.confidence or 0.0)
                                        new_conf = float(reroute.confidence or 0.0)
                                        base_intent = str(routing.intent or "").upper()
                                        new_intent = str(reroute.intent or "").upper()

                                        accept = True
                                        if new_intent != base_intent and new_conf < base_conf + 0.05:
                                            accept = False
                                        if new_conf < base_conf - 0.02:
                                            accept = False

                                        if accept:
                                            hyde_result["intent"] = reroute.intent
                                            hyde_result["confidence"] = new_conf
                                            hyde_result["mode"] = reroute.mode
                                            hyde_result["missing_fields"] = reroute.missing_fields

                                            logger.info(
                                                " [HYDE_X] Reroute accepté: %s(%.3f) -> %s(%.3f) | q=%s",
                                                base_intent,
                                                base_conf,
                                                new_intent,
                                                new_conf,
                                                hq[:120],
                                            )
                                        else:
                                            logger.info(
                                                " [HYDE_X] Reroute refusé: %s(%.3f) -> %s(%.3f) | q=%s",
                                                base_intent,
                                                base_conf,
                                                new_intent,
                                                new_conf,
                                                hq[:120],
                                            )
                                    else:
                                        logger.info(" [HYDE_X] Reformulation refusée (garde-fou) | q=%s", hq[:120])
                                except Exception as reroute_e:
                                    logger.warning(" [HYDE_X] Erreur reroute embeddings post-HYDE: %s", reroute_e)

                            # Attacher au router_metrics pour logs JSON
                            if isinstance(router_metrics, dict):
                                router_metrics["hyde_json"] = hyde_payload
                                router_metrics["hyde_raw"] = hyde_raw

                            # Recalculer le segment Jessica avec le routage raffiné
                            segment = build_jessica_prompt_segment(
                                base_prompt_template=base_prompt_template,
                                hyde_result=hyde_result,
                                question_with_context=question_with_delivery,
                                conversation_history=truncated_history,
                                detected_objects_str=detected_objects_str,
                                filtered_transactions_str=compact_transactions or "0F",
                                expected_deposit_str=expected_deposit_str,
                                enriched_checklist="",
                                routing=routing,
                                delai_message=context.get("delai_message", ""),
                            )
                    except Exception as hyde_e:
                        logger.error(
                            " [HYDE_X] Erreur exe9cution HYDE SECOUR X: %s",
                            hyde_e,
                        )

                # Prompt final venant du segment Jessica
                prompt = segment.get("prompt", "")

                if not prompt or len(prompt) < 100:
                    raise ValueError(
                        f" Prompt Jessica invalide ou vide: {len(prompt) if prompt else 0} chars"
                    )

                timings["prompt_generation"] = (
                    datetime.now() - step_start
                ).total_seconds()

                logger.info(
                    " [BOTLIVE] Prompt Jessica construit: %s caracte8res",
                    len(prompt),
                )

            except Exception as prompt_error:
                import traceback

                print(f"\n{'='*80}")
                print(f" [ERREUR PROMPT JESSICA]")
                print(f"{'='*80}")
                print(f"Company ID: {active_company_id}")
                print(f"LLM Choice: {llm_choice}")
                print(f"Erreur: {prompt_error}")
                print(f"Type: {type(prompt_error).__name__}")
                print(f"\nTraceback complet:")
                traceback.print_exc()
                print(f"{'='*80}\n")
                logger.error(
                    f" Erreur construction prompt Jessica: {prompt_error}",
                    exc_info=True,
                )
                raise

            # ═══════════════════════════════════════════════════════════════
            # 🌸 LOG PROMPT BOTLIVE (SEGMENT JESSICA EFFECTIF, VERSION RÉSUMÉE)
            # ═══════════════════════════════════════════════════════════════
            MAGENTA = '\033[95m'
            BOLD = '\033[1m'
            RESET = '\033[0m'
            safe_prompt = prompt or ""
            first_line = safe_prompt.splitlines()[0] if safe_prompt else ""
            logger.info(f"{MAGENTA}{BOLD}[BOTLIVE_PROMPT] LLM={llm_choice.upper()} len={len(safe_prompt)} chars (~{len(safe_prompt)//4} tokens){RESET}")
            if first_line:
                logger.info(f"{MAGENTA}[BOTLIVE_PROMPT_FIRST_LINE] {first_line[:200]}{RESET}")
            
            # ═══ ÉTAPE 3: APPEL LLM ═══
            step_start = datetime.now()
            if llm_choice == "openrouter":
                response_data = await self._call_openrouter(prompt, user_id)
            else:
                response_data = await self._call_groq(prompt, user_id)
            self.stats['primary_llm_requests'] += 1
            timings['llm_call'] = (datetime.now() - step_start).total_seconds()
            
            # ═══ ÉTAPE 4: VALIDATION RÉPONSE ═══
            if not self._is_valid_response(response_data, llm_choice):
                # Fallback possible (à activer si on ajoute un deuxième LLM)
                logger.warning(f"🔄 [BOTLIVE] Réponse LLM jugée invalide pour {user_id}, pas de second LLM configuré (Groq 70B unique)")
                self.router.record_failure(user_id, llm_choice)
                self.stats['fallbacks'] += 1
            
            # ═══ ÉTAPE 5: EXTRACTION THINKING/RESPONSE ═══
            step_start = datetime.now()
            raw_response = response_data.get('response', '')
            thinking = response_data.get('thinking', '')
            final_response = raw_response

            # Extraire thinking et response si format structuré
            meta_match = None
            meta_tag = None
            if raw_response and ("<meta>" in raw_response.lower() or "<thinking>" in raw_response.lower()):
                meta_match = regex.search(r'<meta>(.*?)</meta>', raw_response, regex.DOTALL | regex.IGNORECASE)
                if meta_match:
                    meta_tag = "meta"
                else:
                    meta_match = regex.search(r'<thinking>(.*?)</thinking>', raw_response, regex.DOTALL | regex.IGNORECASE)
                    if meta_match:
                        meta_tag = "thinking"

            response_match = None
            if raw_response and "<response>" in raw_response.lower():
                response_match = regex.search(r'<response>(.*?)</response>', raw_response, regex.DOTALL | regex.IGNORECASE)

            if meta_match:
                thinking = meta_match.group(1).strip()
                if meta_tag == "thinking":
                    execute_tools_in_response(thinking, user_id)
                    logger.debug(f"🧠 [THINKING] Outils exécutés pour {user_id}")

            if response_match:
                final_response = response_match.group(1).strip()
            elif meta_match:
                cleaned = raw_response
                cleaned = regex.sub(r'<meta>.*?</meta>', '', cleaned, flags=regex.DOTALL | regex.IGNORECASE)
                cleaned = regex.sub(r'<thinking>.*?</thinking>', '', cleaned, flags=regex.DOTALL | regex.IGNORECASE)
                cleaned = cleaned.strip()
                final_response = cleaned or raw_response.strip()
            
            # ═══ ÉTAPE 6: VALIDATION ANTI-HALLUCINATION ═══
            validation_enabled = os.getenv("BOTLIVE_VALIDATION_ENABLED", "false").strip().lower() in {"1", "true", "yes", "y", "on"}
            validation_result = None
            if validation_enabled:
                from core.llm_response_validator import validator as llm_validator
                from core.order_state_tracker import order_tracker
                
                validation_result = llm_validator.validate(
                    response=final_response,
                    thinking=thinking,
                    order_state=order_tracker.get_state(user_id),
                    payment_validation=payment_validation,
                    context_documents=[context.get('context_used', '')]
                )
                
                # Si hallucination détectée, régénérer (DEBUG uniquement)
                if validation_result.should_regenerate:
                    logger.warning(f"🚨 [HALLUCINATION] Régénération requise pour {user_id}")
                    logger.warning(f"   Erreurs: {validation_result.errors}")
                    
                    # Régénérer avec prompt corrigé
                    corrected_prompt = prompt + "\n\n" + validation_result.correction_prompt
                    
                    logger.info(f"🔄 [REGENERATION] Appel LLM avec correction...")
                    # Botlive : toujours Groq 70B pour la régénération
                    response_data = await self._call_groq(corrected_prompt, user_id)
                    
                    # Extraire nouvelle réponse
                    raw_response = response_data.get('response', '')

                    meta_match = regex.search(r'<meta>(.*?)</meta>', raw_response, regex.DOTALL | regex.IGNORECASE)
                    if meta_match:
                        thinking = meta_match.group(1).strip()
                    else:
                        thinking_match = regex.search(r'<thinking>(.*?)</thinking>', raw_response, regex.DOTALL | regex.IGNORECASE)
                        if thinking_match:
                            thinking = thinking_match.group(1).strip()

                    response_match = regex.search(r'<response>(.*?)</response>', raw_response, regex.DOTALL | regex.IGNORECASE)
                    if response_match:
                        final_response = response_match.group(1).strip()
                    else:
                        cleaned = raw_response
                        cleaned = regex.sub(r'<meta>.*?</meta>', '', cleaned, flags=regex.DOTALL | regex.IGNORECASE)
                        cleaned = regex.sub(r'<thinking>.*?</thinking>', '', cleaned, flags=regex.DOTALL | regex.IGNORECASE)
                        final_response = cleaned.strip() or raw_response.strip()
                    
                    # Valider à nouveau
                    validation_result2 = llm_validator.validate(
                        response=final_response,
                        thinking=thinking,
                        order_state=order_tracker.get_state(user_id),
                        payment_validation=payment_validation,
                        context_documents=[context.get('context_used', '')]
                    )
                    
                    if not validation_result2.valid:
                        logger.error("❌ [REGENERATION] Échec après correction, réponse conservée")
            
            # ═══ ÉTAPE 7: EXÉCUTION OUTILS ═══
            processed_response = execute_tools_in_response(final_response, user_id)
            timings['tools_execution'] = (datetime.now() - step_start).total_seconds()
            
            if processed_response != final_response:
                self.stats['tools_used'] += 1
                logger.debug(f"🧠 Outils exécutés pour {user_id}")
            
            # ═══ ÉTAPE 6.4: DÉTECTION AUTOMATIQUE ET SAUVEGARDE (OPTIMISÉE) ═══
            try:
                from core.order_state_tracker import order_tracker
                
                # Détecter et sauvegarder automatiquement les données
                vision_objects = context.get('vision_objects', [])
                detected_objects = context.get('detected_objects', [])
                message_text = context.get('message', message)  # Utiliser message du paramètre si pas dans context
                message_lower = message_text.lower() if message_text else ""
                
                # 🔍 DEBUG: Voir ce qui arrive vraiment
                logger.info(f"🔍 [AUTO-DETECT DEBUG] user_id={user_id}")
                logger.info(f"🔍 [AUTO-DETECT DEBUG] vision_objects={vision_objects}")
                logger.info(f"🔍 [AUTO-DETECT DEBUG] detected_objects={detected_objects}")
                logger.info(f"🔍 [AUTO-DETECT DEBUG] message_text={message_text[:100] if message_text else 'VIDE'}")
                logger.info(f"🔍 [AUTO-DETECT DEBUG] context.keys()={list(context.keys())}")
                
                # 1. PRODUIT détecté dans VISION (BLIP) SEULEMENT
                # ⚠️ IMPORTANT: Sans validation BLIP, on ne peut pas fiabiliser les noms de produits
                # pour des milliers d'entreprises. Seule la vision validée est acceptée.
                
                if vision_objects or detected_objects:
                    # Fusionner les deux sources
                    all_objects = vision_objects + detected_objects
                    if all_objects:
                        # Détecter le produit (tout objet non monétaire)
                        for obj in all_objects:
                            obj_text = None
                            
                            # FORMAT 1: Dict {'label': '...', 'confidence': 0.85}
                            if isinstance(obj, dict) and 'label' in obj:
                                obj_text = obj['label']
                            
                            # FORMAT 2: String "objet:lingettes~0.85"
                            elif isinstance(obj, str) and obj.startswith('objet:'):
                                # Extraire le label entre "objet:" et "~"
                                parts = obj.split('~')
                                if len(parts) > 0:
                                    obj_text = parts[0].replace('objet:', '')
                            
                            # Valider et sauvegarder (VISION BLIP SEULEMENT)
                            if obj_text:
                                obj_str = str(obj_text).lower()
                                if not regex.search(r'\d+\s*f', obj_str) and len(obj_str) > 2:
                                    produit = obj_text[:50]
                                    order_tracker.update_produit(user_id, produit)
                                    logger.info(f"📦 [AUTO-DETECT] Produit (BLIP vision): {produit}")
                                    break
                        
                # 2. PAIEMENT détecté dans TRANSACTIONS (prioritaire) ou vision
                filtered_transactions = context.get('filtered_transactions', [])
                if filtered_transactions:
                    # Transactions OCR détectées
                    first_transaction = filtered_transactions[0]
                    montant = f"{first_transaction.get('amount', 'INCONNU')}F[TRANSACTIONS]"
                    order_tracker.update_paiement(user_id, montant)
                    logger.info(f"💰 [AUTO-DETECT] Paiement (OCR): {montant}")
                else:
                    # Sinon chercher dans vision
                    for obj in vision_objects + detected_objects:
                        obj_str = str(obj).lower()
                        if 'fcfa' in obj_str or regex.search(r'\d+\s*f\b', obj_str):
                            # Extraire montant
                            montant_match = regex.search(r'(\d+)\s*f', obj_str)
                            if montant_match:
                                montant = f"{montant_match.group(1)}F[VISION]"
                                order_tracker.update_paiement(user_id, montant)
                                logger.info(f"💰 [AUTO-DETECT] Paiement (vision): {montant}")
                                break
                
                # 3. ZONE détectée dans message
                zones = ["yopougon", "cocody", "plateau", "adjamé", "abobo", "marcory", 
                         "koumassi", "treichville", "angré", "riviera", "port-bouet", "attécoubé"]
                for zone in zones:
                    if zone in message_lower:
                        zone_formatted = f"{zone.capitalize()}"
                        order_tracker.update_zone(user_id, zone_formatted)
                        logger.info(f"📍 [AUTO-DETECT] Zone: {zone_formatted}")
                        break
                
                # 4. NUMÉRO détecté dans message (4 formats)
                numero_patterns = [
                    r'\+225\s?0?([157]\d{8})',  # +2250787360757 ou +225 0787360757
                    r'\b(0[157]\d{8})\b',        # 0787360757
                    r'\b0([157])\s?(\d{2})\s?(\d{2})\s?(\d{2})\s?(\d{2})\b'  # 07 87 36 07 57
                ]
                
                numero = None
                for pattern in numero_patterns:
                    match = regex.search(pattern, message_text) if message_text else None
                    if match:
                        if len(match.groups()) == 1:
                            # Format simple
                            numero = f"0{match.group(1)}" if not match.group(1).startswith('0') else f"{match.group(1)}"
                        else:
                            # Format avec espaces
                            numero = f"0{''.join(match.groups())}"
                        break
                
                if numero:
                    order_tracker.update_numero(user_id, numero)
                    logger.info(f"📞 [AUTO-DETECT] Numéro: {numero}")
                    
            except Exception as e:
                logger.error(f"⚠️ Auto-détection échouée: {e}")
            
            # ═══ ÉTAPE 6.45: PYTHON DIRECT (court-circuit si déclencheur actif) ═══
            try:
                if ENABLE_PYTHON_DIRECT:
                    from core.order_state_tracker import order_tracker as _ot
                    state_after = _ot.get_state(user_id)
                    trigger = self._build_loop_trigger(state_before, state_after, context, message)
                    if trigger:
                        loop_state = self._build_loop_state(state_after, context)
                        engine = get_loop_engine()
                        python_resp = engine._python_auto_response(trigger, loop_state, message)
                        if python_resp and python_resp != "llm_takeover":
                            processed_response = python_resp
                            thinking = ""
                            python_short_circuit = True
                            if isinstance(router_metrics, dict):
                                router_metrics["python_direct"] = True
            except Exception as e:
                logger.debug(f"⚠️ [PYTHON_DIRECT] Ignoré (erreur non bloquante): {e}")
            
            # ═══ ÉTAPE 6.5: FINALISATION FORCÉE SI COMMANDE COMPLÈTE (TRANSITION) ═══
            try:
                from core.order_state_tracker import order_tracker
                state_after = order_tracker.get_state(user_id)

                became_complete = bool(state_after.is_complete()) and not bool(state_was_complete)

                if became_complete and not python_short_circuit:
                    montant = 2000
                    try:
                        paiement_str = getattr(state_after, "paiement", "") or ""
                        m = regex.search(r"(\d+)", str(paiement_str))
                        montant = int(m.group(1)) if m else montant
                    except Exception:
                        pass

                    try:
                        delai = "aujourd'hui" if is_same_day_delivery_possible() else "demain"
                    except Exception:
                        from datetime import datetime as _dt
                        heure_actuelle = _dt.now().hour
                        delai = "aujourd'hui" if heure_actuelle < 13 else "demain"

                    processed_response = (
                        f"✅PARFAIT Commande confirmée 😊\n"
                        f"Livraison prévue {delai}, acompte de {montant} F déjà versé.\n"
                        "Nous vous rappellerons bientôt pour les détails et le coût total.\n"
                        "Veuillez ne pas répondre à ce message."
                    )
                    logger.info(
                        f"✅ [FINALISATION AUTO] Commande complétée sur ce tour pour {user_id} "
                        f"(montant={montant}, delai={delai})"
                    )
            except Exception as e:
                logger.debug(f"⚠️ Vérification finalisation échouée: {e}")
            
            # ═══ ÉTAPE 6.6: NETTOYAGE TRACES TECHNIQUES ═══
            processed_response = self._clean_response(processed_response)
            
            # ═══ ÉTAPE 7: ENREGISTREMENT SUCCÈS ═══
            self.router.record_success(user_id, llm_choice)
            
            # ═══ ÉTAPE 8: CONSTRUCTION RÉPONSE FINALE ═══
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            self.stats['total_requests'] += 1
            
            return {
                'response': processed_response,
                'thinking': "" if python_short_circuit else thinking,
                'llm_used': 'python' if python_short_circuit else llm_choice,
                'validation': {  # ← NOUVEAU: Résultats validation
                    'valid': validation_result.valid if validation_result is not None else None,
                    'errors': validation_result.errors if validation_result is not None else None,
                    'warnings': validation_result.warnings if validation_result is not None else None,
                    'should_regenerate': validation_result.should_regenerate if validation_result is not None else None
                },
                'routing_reason': routing_reason,
                'processing_time': processing_time,
                'timings': timings,
                'router_metrics': router_metrics,
                'tools_executed': processed_response != final_response,
                'prompt_tokens': response_data.get('prompt_tokens', 0),
                'completion_tokens': response_data.get('completion_tokens', 0),
                'total_cost': response_data.get('total_cost', 0),
                'success': True
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur traitement requête {user_id}: {e}")
            # Réponse d'erreur plus humaine et légèrement variée
            import random

            error_messages = [
                "Désolé, erreur technique. Réessayez s'il vous plaît.",
                "Un souci technique est survenu. Pouvez-vous reformuler ?",
                "Oups, petit problème de connexion. Essayons à nouveau.",
                "Erreur temporaire. Retentons ensemble dans un instant.",
            ]

            friendly_error = random.choice(error_messages)

            return {
                'response': friendly_error,
                'thinking': '',
                'llm_used': 'error',
                'routing_reason': f'Erreur: {str(e)}',
                'processing_time': (datetime.now() - start_time).total_seconds(),
                'tools_executed': False,
                'success': False
            }
    
    def _clean_response(self, response: str) -> str:
        """
        Nettoie la réponse pour enlever toute trace technique
        (notepad, calculator, etc.)
        
        Args:
            response: Réponse brute du LLM
        
        Returns:
            str: Réponse nettoyée
        """
        # Supprimer notepad(...) et contenu associé
        response = regex.sub(r"notepad\([^)]*\)\s*puis\s*[^\s]+", "", response)
        response = regex.sub(r"notepad\([^)]*\)", "", response)
        response = regex.sub(r"calculator\([^)]*\)", "", response)
        # Supprimer traces ✅CHAMP:valeur[SOURCE]
        response = regex.sub(r"✅\w+:[^\s\|]+\[\w+\]", "", response)
        # Supprimer blocs XML internes (<thinking>, <response>, <answer>)
        response = regex.sub(
            r"<thinking>.*?</thinking>", "", response, flags=regex.DOTALL | regex.IGNORECASE
        )
        response = regex.sub(
            r"<meta>.*?</meta>", "", response, flags=regex.DOTALL | regex.IGNORECASE
        )
        response = regex.sub(r"</?response>", "", response, flags=regex.IGNORECASE)
        response = regex.sub(r"</?answer>", "", response, flags=regex.IGNORECASE)
        # Nettoyer espaces multiples
        response = regex.sub(r"\s{2,}", " ", response).strip()
        return response

    async def _process_images(self, images: list, context: Dict[str, Any]) -> Dict[str, Any]:
        """Wrapper vision: utilise Zeta_AI.app._process_botlive_vision pour chaque image.
        Normalise les clés pour correspondre au format attendu par le moteur (name/confidence).
        """
        result: Dict[str, Any] = {'detected_objects': [], 'filtered_transactions': []}
        if not images:
            return result
        # Import local pour éviter hard dependency si module absent
        try:
            from Zeta_AI.app import _process_botlive_vision
        except Exception as e:
            logger.debug(f"[VISION_WRAPPER] Module indisponible: {e}")
            return result

        company_phone = context.get('company_phone')
        for img in images:
            try:
                vision = await _process_botlive_vision(img, company_phone=company_phone)
                if not isinstance(vision, dict):
                    continue
                # Normaliser objets détectés
                objs = []
                for o in vision.get('detected_objects', []) or []:
                    if isinstance(o, dict):
                        name = o.get('name') or o.get('label') or o.get('type') or 'Produit détecté'
                        conf = o.get('confidence', 0)
                        try:
                            conf = float(conf)
                        except Exception:
                            conf = 0.0
                        objs.append({'name': name, 'confidence': conf})
                    else:
                        objs.append({'name': str(o), 'confidence': 0.0})
                if objs:
                    result['detected_objects'].extend(objs)

                # Transactions OCR filtrées
                txs = vision.get('filtered_transactions', [])
                if isinstance(txs, list) and txs:
                    result['filtered_transactions'].extend(txs)
            except Exception as e:
                logger.debug(f"[VISION_WRAPPER] Erreur traitement image: {e}")
                continue
        return result

    async def _call_deepseek(self, prompt: str, user_id: str) -> Dict[str, Any]:
        """Appel API DeepSeek V3 (actuellement proxifié via Groq 70B)."""
        try:
            # Import du bon module Groq
            from core.llm_client_groq import complete

            logger.debug(f"📡 Appel DeepSeek V3 pour {user_id}")

            # Pour l'instant, utiliser Groq en attendant l'API DeepSeek
            content, token_info = await complete(
                prompt=prompt,
                model_name="llama-3.3-70b-versatile",  # Temporaire
                max_tokens=500,
                temperature=0.1,
            )

            prompt_tokens = int(token_info.get("prompt_tokens", 0) or 0)
            completion_tokens = int(token_info.get("completion_tokens", 0) or 0)
            total_tokens = int(
                token_info.get("total_tokens", prompt_tokens + completion_tokens) or 0
            )
            cost = self._calculate_groq_cost(token_info)
            model = token_info.get("model", "llama-3.3-70b-versatile")

            try:
                log3("[LLM]", f"Groq {model} (via DeepSeek) | {len(prompt)} chars")
                cached_tokens = 0
                try:
                    cached_tokens = int(
                        usage.get("cached_tokens")
                        or (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
                        or 0
                    )
                except Exception:
                    cached_tokens = 0
                token_msg = f"{prompt_tokens} + {completion_tokens} = {total_tokens} tokens (cost=${cost:.6f})"
                if cached_tokens:
                    token_msg = f"{token_msg} | cached_prompt_tokens={cached_tokens}"
                log3("[LLM][TOKENS]", token_msg)
                log3("[LLM][RAW]", content, max_lines=40, max_length=4000)
            except Exception:
                pass

            return {
                "response": content,
                "thinking": "",
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_cost": cost,
                # On conserve le label logique DeepSeek côté métriques
                "model": "deepseek-chat",
            }
        except Exception as e:
            logger.error(f"❌ Erreur DeepSeek API: {e}")
            raise

    async def _call_openrouter(self, prompt: str, user_id: str) -> Dict[str, Any]:
        try:
            from core.llm_client_openrouter import complete

            model_name = os.getenv(
                "OPENROUTER_BOTLIVE_MODEL",
                os.getenv("LLM_MODEL", "mistralai/mistral-small-3.2-24b-instruct"),
            )
            max_tokens = int(os.getenv("BOTLIVE_MAX_TOKENS", "600"))
            temperature = float(os.getenv("BOTLIVE_TEMPERATURE", "0.3"))
            top_p = float(os.getenv("BOTLIVE_TOP_P", "0.9"))

            logger.debug(f"📡 Appel OpenRouter ({model_name}) pour {user_id}")

            content, token_info = await complete(
                prompt=prompt,
                model_name=model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            )

            prompt_tokens = int(token_info.get("prompt_tokens", 0) or 0)
            completion_tokens = int(token_info.get("completion_tokens", 0) or 0)
            total_tokens = int(token_info.get("total_tokens", prompt_tokens + completion_tokens) or 0)
            model = token_info.get("model", model_name)

            try:
                log3("[LLM]", f"OpenRouter {model} | {len(prompt)} chars")
                log3("[LLM][TOKENS]", f"{prompt_tokens} + {completion_tokens} = {total_tokens} tokens")
                log3("[LLM][RAW]", content, max_lines=40, max_length=4000)
            except Exception:
                pass

            return {
                "response": content,
                "thinking": "",
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_cost": 0.0,
                "model": model,
            }
        except Exception as e:
            logger.error(f"❌ Erreur OpenRouter API: {e}")
            raise

    async def _call_groq(self, prompt: str, user_id: str) -> Dict[str, Any]:
        """Appel API Groq 70B."""
        try:
            # Import du bon module Groq
            from core.llm_client_groq import complete

            logger.debug(f"📡 Appel Groq 70B pour {user_id}")

            # Appel API Groq réel
            content, token_info = await complete(
                prompt=prompt,
                model_name="llama-3.3-70b-versatile",
                max_tokens=1000,
                temperature=0.1,
            )

            prompt_tokens = int(token_info.get("prompt_tokens", 0) or 0)
            completion_tokens = int(token_info.get("completion_tokens", 0) or 0)
            total_tokens = int(
                token_info.get("total_tokens", prompt_tokens + completion_tokens) or 0
            )
            cost = self._calculate_groq_cost(token_info)
            model = token_info.get("model", "llama-3.3-70b-versatile")

            try:
                log3("[LLM]", f"Groq {model} | {len(prompt)} chars")
                cached_tokens = 0
                try:
                    cached_tokens = int(
                        usage.get("cached_tokens")
                        or (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
                        or 0
                    )
                except Exception:
                    cached_tokens = 0
                token_msg = f"{prompt_tokens} + {completion_tokens} = {total_tokens} tokens (cost=${cost:.6f})"
                if cached_tokens:
                    token_msg = f"{token_msg} | cached_prompt_tokens={cached_tokens}"
                log3("[LLM][TOKENS]", token_msg)
                log3("[LLM][RAW]", content, max_lines=40, max_length=4000)
            except Exception:
                pass

            # Extraire thinking/response si format spécialisé
            thinking = ""
            response = content

            if "<thinking>" in content and "</thinking>" in content:
                thinking_match = regex.search(r"<thinking>(.*?)</thinking>", content, regex.DOTALL)
                response_match = regex.search(r"<response>(.*?)</response>", content, regex.DOTALL)

                if thinking_match:
                    thinking = thinking_match.group(1).strip()
                    try:
                        log3("[LLM][THINKING]", thinking, max_lines=40, max_length=4000)
                    except Exception:
                        pass
                if response_match:
                    response = response_match.group(1).strip()
                    try:
                        log3("[LLM][RESPONSE]", response, max_lines=40, max_length=4000)
                    except Exception:
                        pass

            return {
                "response": response,
                "thinking": thinking,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_cost": cost,
                "model": model,
            }
        except Exception as e:
            logger.error(f"❌ Erreur Groq API: {e}")
            raise

    def _calculate_groq_cost(self, token_info: Dict[str, Any]) -> float:
        """Calcule le coût Groq selon les tokens utilisés (USD)."""
        prompt_tokens = int(token_info.get("prompt_tokens", 0) or 0)
        completion_tokens = int(token_info.get("completion_tokens", 0) or 0)

        # Tarifs Groq 70B (USD)
        input_cost = (prompt_tokens / 1_000_000) * 0.59
        output_cost = (completion_tokens / 1_000_000) * 0.79

        return input_cost + output_cost
    
    def _is_valid_response(self, response_data: Dict, llm_used: str) -> bool:
        """
        Valide la qualité d'une réponse LLM
        
        Args:
            response_data: Données de réponse
            llm_used: LLM utilisé
        
        Returns:
            bool: True si réponse valide
        """
        response = response_data.get('response', '')
        
        # 1. Réponse non vide
        if not response or len(response.strip()) < 5:
            logger.warning(f"⚠️ Réponse vide de {llm_used}")
            return False
        
        # 2. Pas de réponse générique répétitive (pour DeepSeek)
        if llm_used == "deepseek-v3":
            generic_responses = [
                "salut 👋 envoie photo produit",
                "envoie photo du produit",
                "impossible de télécharger"
            ]

            if any(generic.lower() in response.lower() for generic in generic_responses):
                # Acceptable pour DeepSeek si c'est approprié au contexte
                pass

        # 3. Format thinking/meta respecté
        if llm_used == "groq-70b":
            if "<thinking>" in response and "</thinking>" not in response:
                logger.warning(f" Format thinking malformé de {llm_used}")
                return False
        if llm_used == "openrouter":
            if "<meta>" in response.lower() and "</meta>" not in response.lower():
                logger.warning(f" Format meta malformé de {llm_used}")
                return False

        return True

    def _format_detected_objects(self, detected_objects: list) -> str:
        """Formate les objets détectés pour le prompt"""
        if not detected_objects:
            return "[AUCUN OBJET DÉTECTÉ]"

        
        formatted = []
        for obj in detected_objects:
            if isinstance(obj, str):
                formatted.append(obj)
            elif isinstance(obj, dict):
                # Support pour format BLIP-2: {'label': 'nom', 'confidence': 0.85}
                label = obj.get('label', obj.get('type', obj.get('description', 'objet inconnu')))
                confidence = obj.get('confidence', 0)
                if confidence > 0:
                    formatted.append(f"{label} (confiance: {confidence:.0%})")
                else:
                    formatted.append(label)
        
        return ", ".join(formatted) if formatted else "[AUCUN OBJET DÉTECTÉ]"
    
    def _format_transactions(self, transactions: list) -> str:
        """Formate les transactions pour le prompt (optimisé tokens)"""
        if not transactions:
            return "0F"
        
        formatted = []
        for trans in transactions:
            if isinstance(trans, dict):
                amount = trans.get('amount', '0')
                phone = trans.get('phone', '')
                # Tronquer numéro pour économiser tokens (garder 4 derniers chiffres)
                if phone and len(phone) >= 4:
                    phone_short = f"...{phone[-4:]}"
                else:
                    phone_short = phone
                formatted.append(f"{amount}F -> +225{phone_short}")
        
        return ", ".join(formatted) if formatted else "0F"
    
    def _build_loop_state(self, order_state: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Construit l'état attendu par LoopBotliveEngine à partir de OrderState + contexte."""
        def _extract_amount(p: Optional[str]) -> int:
            if not p:
                return 0
            try:
                m = regex.search(r'(\d+)', str(p))
                return int(m.group(1)) if m else 0
            except Exception:
                return 0

        # Coût livraison selon zone détectée
        zone_name = order_state.zone or ""
        periph = {"port-bouët", "attécoubé", "bingerville", "songon", "anyama", "port-bouet", "attecoube"}
        default_cost = 2000 if zone_name.lower() in periph else 1500
        if isinstance(context.get('delivery_info'), dict):
            try:
                default_cost = int(context['delivery_info'].get('cost', default_cost) or default_cost)
            except Exception:
                pass

        tel_valide = bool(order_state.numero and len(order_state.numero) == 10 and order_state.numero.startswith('0'))

        return {
            "photo": {"collected": bool(order_state.produit), "data": order_state.produit},
            "produit": {"collected": bool(order_state.produit), "data": order_state.produit},
            "paiement": {"collected": bool(order_state.paiement), "data": _extract_amount(order_state.paiement)},
            "zone": {"collected": bool(order_state.zone), "data": order_state.zone, "cost": default_cost},
            "tel": {"collected": bool(order_state.numero), "data": order_state.numero, "valid": tel_valide},
        }

    def _build_loop_trigger(
        self,
        before: Any,
        after: Any,
        context: Dict[str, Any],
        message: str,
    ) -> Optional[Dict[str, Any]]:
        """Construit le déclencheur pour LoopBotliveEngine en comparant before/after."""
        def _extract_amount(p: Optional[str]) -> int:
            if not p:
                return 0
            try:
                m = regex.search(r'(\d+)', str(p))
                return int(m.group(1)) if m else 0
            except Exception:
                return 0

        # Déterminer le montant requis
        expected_deposit_str = context.get('expected_deposit', '2000 FCFA')
        try:
            mm = regex.search(r'(\d+)', str(expected_deposit_str))
            required_amount = int(mm.group(1)) if mm else 2000
        except Exception:
            required_amount = 2000

        changed_produit = bool(after.produit and not before.produit)
        changed_paiement = bool(after.paiement and not before.paiement)
        changed_zone = bool(after.zone and not before.zone)
        changed_tel = bool(after.numero and not before.numero)
        completed_now = bool(after.is_complete() and not before.is_complete())

        # Téléphone d'abord (peut être final)
        if changed_tel:
            tel_clean = after.numero or ""
            tel_len = len(tel_clean)
            tel_valid = bool(tel_len == 10 and tel_clean.startswith('0'))
            all_others_collected = bool(after.produit and after.paiement and after.zone)
            # Payload complet attendu par TriggerValidator.validate_telephone_trigger
            base_tel_data = {
                "raw": message,
                "clean": tel_clean,
                "valid": tel_valid,
                "length": tel_len,
                "format_error": None,
            }

            if not tel_valid:
                if tel_len < 10:
                    base_tel_data["format_error"] = "TOO_SHORT"
                elif tel_len > 10:
                    base_tel_data["format_error"] = "TOO_LONG"
                elif not tel_clean.startswith('0'):
                    base_tel_data["format_error"] = "WRONG_PREFIX"
                else:
                    base_tel_data["format_error"] = "INVALID_FORMAT"

            if all_others_collected:
                # Téléphone final → déclencheur telephone_final
                return {"type": "telephone_final", "data": base_tel_data}

            # Sinon, téléphone détecté mais pas final
            return {"type": "telephone_detecte", "data": base_tel_data}

        # Paiement via OCR/transactions
        if changed_paiement:
            amt = _extract_amount(after.paiement)
            # Payload complet attendu par TriggerValidator.validate_paiement_trigger
            data = {
                "amount": amt,
                "valid": bool(amt > 0),
                "error": None,
                "currency": "FCFA",
                "transactions": context.get('filtered_transactions', []) or [],
                "raw_text": "",
                "sufficient": bool(amt >= required_amount),
            }
            return {"type": "paiement_ocr", "data": data}

        # Zone détectée
        if changed_zone:
            zone_name = after.zone
            periph = {"port-bouët", "attécoubé", "bingerville", "songon", "anyama", "port-bouet", "attecoube"}
            cost = 2000 if (zone_name and zone_name.lower() in periph) else 1500
            if isinstance(context.get('delivery_info'), dict):
                try:
                    cost = int(context['delivery_info'].get('cost', cost) or cost)
                except Exception:
                    pass
            # Payload complet attendu par TriggerValidator.validate_zone_trigger
            zone_info = context.get('delivery_info') if isinstance(context.get('delivery_info'), dict) else None
            # Catégorie heuristique
            centrale_zones = {"plateau", "cocody", "marcory", "koumassi", "treichville"}
            if zone_name and zone_name.lower() in centrale_zones:
                category = "centrale"
            elif zone_name and zone_name.lower() in periph:
                category = "peripherique"
            else:
                category = "expedition"

            data = {
                "zone": zone_name,
                "cost": cost,
                "category": category,
                "name": zone_name,
                "source": "delivery_info" if zone_info else "regex_message",
                "confidence": float(zone_info.get('confidence', 0.9)) if zone_info else 0.6,
            }
            return {"type": "zone_detectee", "data": data}

        # Photo/produit détecté
        if changed_produit:
            conf = 0.8
            try:
                det = context.get('detected_objects', []) or []
                for obj in det:
                    if isinstance(obj, dict) and str(obj.get('label', '')).lower() in str(after.produit or '').lower():
                        if 'confidence' in obj:
                            conf = float(obj['confidence'])
                            break
            except Exception:
                pass
            # Payload complet attendu par TriggerValidator.validate_photo_trigger
            photo_data = {
                "description": after.produit or "",
                "confidence": conf,
                "error": None,
                "valid": True,
                "product_detected": True,
            }
            return {"type": "photo_produit", "data": photo_data}

        # Récap automatique si complété sur ce tour
        if completed_now:
            return {"type": "recap_auto", "data": None}

        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retourne les statistiques du système hybride
        
        Returns:
            Dict: Statistiques complètes
        """
        router_stats = self.router.get_stats()

        total = max(self.stats['total_requests'], 1)
        return {
            **self.stats,
            **router_stats,
            'primary_llm_percentage': (self.stats['primary_llm_requests'] / total) * 100,
            'fallback_llm_percentage': (self.stats['fallback_llm_requests'] / total) * 100,
            'tools_usage_rate': (self.stats['tools_used'] / total) * 100,
            'fallback_rate': (self.stats['fallbacks'] / total) * 100,
        }
    
    def reset_stats(self):
        """Remet à zéro les statistiques"""
        self.stats = {
            'total_requests': 0,
            'primary_llm_requests': 0,
            'fallback_llm_requests': 0,
            'tools_used': 0,
            'fallbacks': 0,
        }

# Instance globale
botlive_hybrid = BotliveRAGHybrid()

# ═══════════════════════════════════════════════════════════════════════════════
# 🧪 FONCTIONS DE TEST
# ═══════════════════════════════════════════════════════════════════════════════

async def test_hybrid_system():
    """Test rapide du système hybride"""
    print("🧪 Test système hybride Botlive")
    
    # Test cas simple (DeepSeek attendu)
    print("\n1. Test cas simple:")
    result1 = await botlive_hybrid.process_request(
        user_id="test_user_1",
        message="Bonjour",
        context={},
        conversation_history=""
    )
    print(f"LLM: {result1['llm_used']} | Réponse: {result1['response']}")
    
    # Test cas complexe (Groq attendu)
    print("\n2. Test cas complexe:")
    result2 = await botlive_hybrid.process_request(
        user_id="test_user_2", 
        message="Validation paiement",
        context={
            'filtered_transactions': [{'amount': '2020', 'phone': '0787360757'}],
            'expected_deposit': '2000 FCFA'
        },
        conversation_history="Photo reçue ! Confirmes ?"
    )
    print(f"LLM: {result2['llm_used']} | Réponse: {result2['response']}")
    
    # Affichage stats
    print(f"\n📊 Stats: {botlive_hybrid.get_stats()}")

if __name__ == "__main__":
    asyncio.run(test_hybrid_system())
