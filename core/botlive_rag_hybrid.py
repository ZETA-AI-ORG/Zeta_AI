#!/usr/bin/env python3
"""
🤖 BOTLIVE RAG HYBRID - Système hybride DeepSeek V3 + Groq 70B
Intégration du routeur intelligent avec prompts spécialisés et outils
"""

import os
import re
import json
import logging
import asyncio
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

# Imports locaux
from .hyde_smart_router import hyde_router
from .botlive_prompts_supabase import get_prompts_manager  # ← NOUVEAU: Supabase au lieu de hardcodé
from .botlive_tools import execute_tools_in_response, should_suggest_calculator, should_suggest_notepad

logger = logging.getLogger(__name__)

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
            'deepseek_requests': 0,
            'groq_requests': 0,
            'tools_used': 0,
            'fallbacks': 0
        }
        
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
        print("\n========== DEBUG BOTLIVE SUPABASE ==========")
        print(f"SUPABASE_URL: {os.getenv('SUPABASE_URL')}")
        print(f"SUPABASE_SERVICE_KEY: {os.getenv('SUPABASE_SERVICE_KEY')}")
        print(f"prompts_manager: {self.prompts_manager}")
        print(f"company_id reçu: {company_id} | self.company_id: {self.company_id}")
        print("============================================\n")

        start_time = datetime.now()
        timings = {}  # Track temps par étape
        
        try:
            # ═══ ÉTAPE 1: ROUTAGE INTELLIGENT ═══
            step_start = datetime.now()
            llm_choice, routing_reason, router_metrics = await self.router.route_request(
                user_id, message, context, conversation_history
            )
            timings['routing'] = (datetime.now() - step_start).total_seconds()
            
            logger.info(f"🎯 Routage: {llm_choice} - Raison: {routing_reason}")
            
            # ═══ ÉTAPE 1.5: VALIDATION AUTOMATIQUE PAIEMENT ═══
            payment_validation = None
            if context.get('filtered_transactions'):
                from core.payment_validator import validate_payment_cumulative, format_payment_for_prompt
                
                # Extraire montant requis du contexte (dynamique)
                expected_deposit_str = context.get('expected_deposit', '2000 FCFA')
                try:
                    import re
                    m = re.search(r'(\d+)', expected_deposit_str)
                    required_amount = int(m.group(1)) if m else 2000
                except:
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
            
            # ═══ ÉTAPE 1.7: SYSTÈME DELIVERY (DÉTECTION + INJECTION) ═══
            delivery_context = ""
            try:
                from core.delivery_zone_extractor import extract_delivery_zone_and_cost, format_delivery_info
                
                # Détecter si la question concerne la livraison
                zone_info = extract_delivery_zone_and_cost(message)
                
                if zone_info:
                    # Zone détectée → Formater le contexte avec heure CI
                    delivery_context = format_delivery_info(zone_info)
                    logger.info(f"🚚 [DELIVERY] Zone détectée: {zone_info['name']} = {zone_info['cost']} FCFA")
                    logger.info(f"📋 [DELIVERY] Contexte injecté dans le prompt ({len(delivery_context)} chars)")
                    
                    # Ajouter au contexte pour le prompt
                    context['delivery_info'] = zone_info
                    context['delivery_context'] = delivery_context
            except Exception as e:
                logger.warning(f"⚠️ [DELIVERY] Erreur extraction: {e}")
            
            # ═══ ÉTAPE 2: GÉNÉRATION PROMPT SPÉCIALISÉ ═══
            step_start = datetime.now()
            
            # Préparer les données pour le prompt
            formatted_transactions = self._format_transactions(context.get('filtered_transactions', []))
            
            # Si paiement validé automatiquement, enrichir le prompt
            if payment_validation:
                validation_message = format_payment_for_prompt(payment_validation)
                formatted_transactions += validation_message
                logger.info(f"💳 Message validation ajouté au prompt: {validation_message[:150]}...")
            
            logger.debug(f"📋 TRANSACTIONS envoyées au LLM: {formatted_transactions[:300]}...")
            
            # ═══ RÉCUPÉRATION ÉTAT COMMANDE (MÉMOIRE CONTEXTE) ═══
            from core.order_state_tracker import order_tracker
            state = order_tracker.get_state(user_id)
            missing = state.get_missing_fields()
            
            # Créer résumé état pour le LLM
            state_resume = f"""
📊 ÉTAT ACTUEL COMMANDE (NE PAS REDEMANDER CE QUI EST ✅):
- PRODUIT: {"✅ " + state.produit if state.produit else "❌ manquant"}
- PAIEMENT: {"✅ " + state.paiement if state.paiement else "❌ manquant"}
- ZONE: {"✅ " + state.zone if state.zone else "❌ manquant"}
- NUMÉRO: {"✅ " + state.numero if state.numero else "❌ manquant"}

⚠️ RÈGLES MÉMOIRE CRITIQUE:
1. Si champ = ✅ → NE JAMAIS redemander, juste confirmer si client corrige
2. Si client corrige info ✅ → Accuser réception SANS redemander ("Parfait, j'ai mis à jour")
3. Demander UNIQUEMENT les champs ❌ manquants
4. Si tous ✅ → Finaliser: "Commande OK ! on vous reviens pour la livraison 😊"
"""
            
            logger.info(f"📊 [ORDER_STATE] État pour {user_id}:")
            logger.info(f"   - Produit: {state.produit or 'NON COLLECTÉ'}")
            logger.info(f"   - Paiement: {state.paiement or 'NON COLLECTÉ'}")
            logger.info(f"   - Zone: {state.zone or 'NON COLLECTÉ'}")
            logger.info(f"   - Numéro: {state.numero or 'NON COLLECTÉ'}")
            
            # ← NOUVEAU: Récupérer prompt depuis Supabase
            # Utiliser company_id du paramètre ou de l'instance
            active_company_id = company_id or self.company_id
            if not active_company_id:
                raise ValueError("❌ company_id requis pour récupérer les prompts Botlive")
            
            # Injecter le contexte delivery dans la question si disponible
            question_with_delivery = message
            if delivery_context:
                question_with_delivery = f"{delivery_context}\n\n{message}"
                logger.info(f"📋 [DELIVERY] Question enrichie avec contexte delivery ({len(question_with_delivery)} chars)")

            # 🔹 HYDE-LIKE: Ajouter une hypothèse d'intent pour guider le LLM (sans retrieval)
            try:
                from core.intent_hypothesis import build_intent_hypothesis
                hyp = build_intent_hypothesis(message)
                if hyp:
                    question_with_delivery = f"{hyp}\n\n{question_with_delivery}"
                    logger.info(f"🧭 [HYPOTHESIS] Bloc intent ajouté ({len(hyp)} chars)")
            except Exception as e:
                logger.warning(f"⚠️ [HYPOTHESIS] Erreur injection: {e}")
            
            logger.info(f"🔍 [BOTLIVE] Récupération prompt pour company_id={active_company_id}, llm={llm_choice}")
            
            # Vérifier si prompts_manager est disponible
            if not self.prompts_manager:
                logger.error("❌ [BOTLIVE] prompts_manager est None - Impossible de récupérer le prompt")
                raise ValueError("Prompts manager non initialisé - Utiliser fallback _botlive_handle")
            
            # ═══ RÉCUPÉRATION PROMPT AVEC DEBUG COMPLET ═══
            try:
                print(f"[DEBUG] Avant appel format_prompt...")
                prompt = self.prompts_manager.format_prompt(
                    company_id=active_company_id,
                    llm_choice=llm_choice,
                    conversation_history=conversation_history,
                    question=question_with_delivery,  # ← UTILISER QUESTION ENRICHIE AVEC DELIVERY
                    detected_objects=self._format_detected_objects(context.get('detected_objects', [])),
                    filtered_transactions=formatted_transactions,
                    expected_deposit=context.get('expected_deposit', '2000'),
                    order_state=state_resume  # ← AJOUT MÉMOIRE CONTEXTE
                )
                print(f"[DEBUG] Après appel format_prompt: {len(prompt)} chars")
                
                # Vérifier que le prompt n'est pas vide ou trop court
                if not prompt or len(prompt) < 100:
                    raise ValueError(f"❌ Prompt Supabase invalide ou vide: {len(prompt) if prompt else 0} chars")
                
                print(f"[DEBUG] ✅ Prompt Supabase valide: {len(prompt)} chars")
                
            except Exception as prompt_error:
                import traceback
                print(f"\n{'='*80}")
                print(f"❌ [ERREUR RÉCUPÉRATION PROMPT SUPABASE]")
                print(f"{'='*80}")
                print(f"Company ID: {active_company_id}")
                print(f"LLM Choice: {llm_choice}")
                print(f"Erreur: {prompt_error}")
                print(f"Type: {type(prompt_error).__name__}")
                print(f"\nTraceback complet:")
                traceback.print_exc()
                print(f"{'='*80}\n")
                logger.error(f"❌ Erreur récupération prompt Supabase: {prompt_error}", exc_info=True)
                raise
            
            logger.info(f"✅ [BOTLIVE] Prompt récupéré: {len(prompt)} caractères")
            # === PRINT PROMPT EFFECTIF (stdout, visible même si niveau de logs élevé) ===
            try:
                print("\n" + "="*100)
                print(f"PROMPT (EFFECTIF) → {llm_choice}: {len(prompt)} chars")
                print("="*100 + "\n")
                print(prompt)
                print("\n" + "="*100 + "\n")
            except Exception:
                pass
            timings['prompt_generation'] = (datetime.now() - step_start).total_seconds()
            
            # ═══════════════════════════════════════════════════════════════
            # 🌸 AFFICHAGE COMPLET DU PROMPT FINAL ENVOYÉ AU LLM (EN ROSE)
            # ═══════════════════════════════════════════════════════════════
            MAGENTA = '\033[95m'
            BOLD = '\033[1m'
            RESET = '\033[0m'
            logger.info(f"\n{MAGENTA}{BOLD}{'='*100}{RESET}")
            logger.info(f"{MAGENTA}{BOLD}🌸 PROMPT COMPLET ENVOYÉ À {llm_choice.upper()} ({len(prompt)} caractères, ~{len(prompt)//4} tokens){RESET}")
            logger.info(f"{MAGENTA}{BOLD}{'='*100}{RESET}")
            logger.info(f"{MAGENTA}{prompt}{RESET}")
            logger.info(f"{MAGENTA}{BOLD}{'='*100}{RESET}\n")
            
            # ═══ ÉTAPE 3: APPEL LLM ═══
            step_start = datetime.now()
            if llm_choice == "deepseek-v3":
                response_data = await self._call_deepseek(prompt, user_id)
                self.stats['deepseek_requests'] += 1
            else:  # groq-70b
                response_data = await self._call_groq(prompt, user_id)
                self.stats['groq_requests'] += 1
            timings['llm_call'] = (datetime.now() - step_start).total_seconds()
            
            # ═══ ÉTAPE 4: VALIDATION RÉPONSE ═══
            if not self._is_valid_response(response_data, llm_choice):
                # Fallback automatique vers Groq si DeepSeek échoue
                if llm_choice == "deepseek-v3":
                    logger.warning(f"🔄 Fallback DeepSeek → Groq pour {user_id}")
                    self.router.record_failure(user_id, "deepseek-v3")
                    
                    # Nouveau prompt Groq depuis Supabase
                    groq_prompt = self.prompts_manager.format_prompt(
                        company_id=self.company_id,
                        llm_choice="groq-70b",
                        conversation_history=conversation_history,
                        question=message,
                        detected_objects=self._format_detected_objects(context.get('detected_objects', [])),
                        filtered_transactions=self._format_transactions(context.get('filtered_transactions', [])),
                        expected_deposit=context.get('expected_deposit', '2000')
                    )
                    
                    # 🌸 AFFICHAGE PROMPT GROQ FALLBACK (EN ROSE)
                    logger.info(f"\n{MAGENTA}{BOLD}{'='*100}{RESET}")
                    logger.info(f"{MAGENTA}{BOLD}🌸 PROMPT FALLBACK GROQ-70B ({len(groq_prompt)} caractères, ~{len(groq_prompt)//4} tokens){RESET}")
                    logger.info(f"{MAGENTA}{BOLD}{'='*100}{RESET}")
                    logger.info(f"{MAGENTA}{groq_prompt}{RESET}")
                    logger.info(f"{MAGENTA}{BOLD}{'='*100}{RESET}\n")
                    
                    response_data = await self._call_groq(groq_prompt, user_id)
                    llm_choice = "groq-70b"  # Mise à jour pour les stats
                    self.stats['fallbacks'] += 1
            
            # ═══ ÉTAPE 5: EXTRACTION THINKING/RESPONSE ═══
            step_start = datetime.now()
            raw_response = response_data.get('response', '')
            thinking = response_data.get('thinking', '')
            final_response = raw_response
            
            # Extraire thinking et response si format structuré
            if "<thinking>" in raw_response and "</thinking>" in raw_response:
                import re
                thinking_match = re.search(r'<thinking>(.*?)</thinking>', raw_response, re.DOTALL)
                response_match = re.search(r'<response>(.*?)</response>', raw_response, re.DOTALL)
                
                if thinking_match:
                    thinking = thinking_match.group(1).strip()
                    # ✅ CRITIQUE: Exécuter les outils dans <thinking> (notepad, calculator)
                    # Ne pas garder le résultat (juste pour side-effects comme sync state tracker)
                    execute_tools_in_response(thinking, user_id)
                    logger.debug(f"🧠 [THINKING] Outils exécutés pour {user_id}")
                    
                if response_match:
                    final_response = response_match.group(1).strip()
                else:
                    # Si pas de balise response, prendre tout après thinking
                    final_response = re.sub(r'<thinking>.*?</thinking>', '', raw_response, flags=re.DOTALL).strip()
            
            # ═══ ÉTAPE 6: VALIDATION ANTI-HALLUCINATION ═══
            from core.llm_response_validator import validator as llm_validator
            from core.order_state_tracker import order_tracker
            
            validation_result = llm_validator.validate(
                response=final_response,
                thinking=thinking,
                order_state=order_tracker.get_state(user_id),
                payment_validation=payment_validation,
                context_documents=[context.get('context_used', '')]
            )
            
            # Si hallucination détectée, régénérer
            if validation_result.should_regenerate:
                logger.warning(f"🚨 [HALLUCINATION] Régénération requise pour {user_id}")
                logger.warning(f"   Erreurs: {validation_result.errors}")
                
                # Régénérer avec prompt corrigé
                corrected_prompt = prompt + "\n\n" + validation_result.correction_prompt
                
                logger.info(f"🔄 [REGENERATION] Appel LLM avec correction...")
                if llm_choice == "deepseek-v3":
                    response_data = await self._call_deepseek(corrected_prompt, user_id)
                else:
                    response_data = await self._call_groq(corrected_prompt, user_id)
                
                # Extraire nouvelle réponse
                raw_response = response_data.get('response', '')
                thinking_match = re.search(r'<thinking>(.*?)</thinking>', raw_response, re.DOTALL)
                response_match = re.search(r'<response>(.*?)</response>', raw_response, re.DOTALL)
                
                if thinking_match:
                    thinking = thinking_match.group(1).strip()
                if response_match:
                    final_response = response_match.group(1).strip()
                else:
                    final_response = re.sub(r'<thinking>.*?</thinking>', '', raw_response, flags=re.DOTALL).strip()
                
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
                import re
                
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
                
                # 1. PRODUIT détecté dans VISION ou DETECTED_OBJECTS
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
                                obj_text = obj.split('objet:')[1].split('~')[0] if '~' in obj else obj.split('objet:')[1]
                            
                            # FORMAT 3: String simple
                            elif isinstance(obj, str):
                                obj_text = obj
                            
                            # FORMAT 4: Autre (fallback)
                            else:
                                obj_text = str(obj)
                            
                            if obj_text:
                                obj_str = obj_text.lower()
                                # Exclure les montants et strings "montant:..."
                                if not re.search(r'\d+\s*f', obj_str) and not obj_str.startswith('montant:') and len(obj_str) > 2:
                                    produit = f"{obj_text[:50]}[VISION]" if len(obj_text) > 50 else f"{obj_text}[VISION]"
                                    order_tracker.update_produit(user_id, produit)
                                    logger.info(f"📦 [AUTO-DETECT] Produit: {produit}")
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
                        if 'fcfa' in obj_str or re.search(r'\d+\s*f\b', obj_str):
                            # Extraire montant
                            montant_match = re.search(r'(\d+)\s*f', obj_str)
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
                        zone_formatted = f"{zone.capitalize()}-1500F[MESSAGE]"
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
                    match = re.search(pattern, message_text) if message_text else None
                    if match:
                        if len(match.groups()) == 1:
                            # Format simple
                            numero = f"0{match.group(1)}[MESSAGE]" if not match.group(1).startswith('0') else f"{match.group(1)}[MESSAGE]"
                        else:
                            # Format avec espaces
                            numero = f"0{''.join(match.groups())}[MESSAGE]"
                        break
                
                if numero:
                    order_tracker.update_numero(user_id, numero)
                    logger.info(f"📞 [AUTO-DETECT] Numéro: {numero}")
                    
            except Exception as e:
                logger.error(f"⚠️ Auto-détection échouée: {e}")
            
            # ═══ ÉTAPE 6.5: FINALISATION FORCÉE SI COMMANDE COMPLÈTE ═══
            try:
                from core.order_state_tracker import order_tracker
                state = order_tracker.get_state(user_id)
                if state.is_complete():
                    processed_response = "Commande OK ! on vous reviens pour la livraison 😊 Si tout es ok. Ne réponds pas à ce message."
                    logger.info(f"✅ [FINALISATION AUTO] Commande complète pour {user_id}")
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
                'thinking': thinking,
                'llm_used': llm_choice,
                'validation': {  # ← NOUVEAU: Résultats validation
                    'valid': validation_result.valid,
                    'errors': validation_result.errors,
                    'warnings': validation_result.warnings,
                    'should_regenerate': validation_result.should_regenerate
                } if 'validation_result' in locals() else None,
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
            return {
                'response': "Désolé, erreur technique. Réessayez s'il vous plaît.",
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
        import re
        # Supprimer notepad(...) et contenu associé
        response = re.sub(r'notepad\([^)]*\)\s*puis\s*[^\s]+', '', response)
        response = re.sub(r'notepad\([^)]*\)', '', response)
        response = re.sub(r'calculator\([^)]*\)', '', response)
        # Supprimer traces ✅CHAMP:valeur[SOURCE]
        response = re.sub(r'✅\w+:[^\s\|]+\[\w+\]', '', response)
        # Supprimer blocs XML internes (<thinking>, <response>, <answer>)
        response = re.sub(r'<thinking>.*?</thinking>', '', response, flags=re.DOTALL | re.IGNORECASE)
        response = re.sub(r'</?response>', '', response, flags=re.IGNORECASE)
        response = re.sub(r'</?answer>', '', response, flags=re.IGNORECASE)
        # Nettoyer espaces multiples
        response = re.sub(r'\s{2,}', ' ', response).strip()
        return response
    
    async def _call_deepseek(self, prompt: str, user_id: str) -> Dict[str, Any]:
        """
        Appel API DeepSeek V3
        
        Args:
            prompt: Prompt formaté
            user_id: ID utilisateur
        
        Returns:
            Dict: Réponse DeepSeek avec métadonnées
        """
        try:
            # Import du bon module Groq
            from core.llm_client_groq import complete
            
            logger.debug(f"📡 Appel DeepSeek V3 pour {user_id}")
            
            # Pour l'instant, utiliser Groq en attendant l'API DeepSeek
            # TODO: Remplacer par vraie API DeepSeek quand disponible
            content, token_info = await complete(
                prompt=prompt,
                model_name="llama-3.3-70b-versatile",  # Temporaire
                max_tokens=500,
                temperature=0.1
            )
            
            return {
                'response': content,
                'thinking': '',  # Extraire si format <thinking>
                'prompt_tokens': token_info.get('prompt_tokens', 600),
                'completion_tokens': token_info.get('completion_tokens', 50),
                'total_cost': 0.0003,  # Coût DeepSeek simulé
                'model': 'deepseek-chat'
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur DeepSeek API: {e}")
            raise
    
    async def _call_groq(self, prompt: str, user_id: str) -> Dict[str, Any]:
        """
        Appel API Groq 70B
        
        Args:
            prompt: Prompt formaté
            user_id: ID utilisateur
        
        Returns:
            Dict: Réponse Groq avec métadonnées
        """
        try:
            # Import du bon module Groq
            from core.llm_client_groq import complete
            
            logger.debug(f"📡 Appel Groq 70B pour {user_id}")
            
            # Appel API Groq réel
            content, token_info = await complete(
                prompt=prompt,
                model_name="llama-3.3-70b-versatile",
                max_tokens=1000,
                temperature=0.1
            )
            
            # Extraire thinking/response si format spécialisé
            thinking = ""
            response = content
            
            if "<thinking>" in content and "</thinking>" in content:
                import re
                thinking_match = re.search(r'<thinking>(.*?)</thinking>', content, re.DOTALL)
                response_match = re.search(r'<response>(.*?)</response>', content, re.DOTALL)
                
                if thinking_match:
                    thinking = thinking_match.group(1).strip()
                if response_match:
                    response = response_match.group(1).strip()
            
            return {
                'response': response,
                'thinking': thinking,
                'prompt_tokens': token_info.get('prompt_tokens', 800),
                'completion_tokens': token_info.get('completion_tokens', 150),
                'total_cost': self._calculate_groq_cost(token_info),
                'model': token_info.get('model', 'llama-3.3-70b-versatile')
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur Groq API: {e}")
            raise
    
    def _calculate_groq_cost(self, token_info: Dict) -> float:
        """Calcule le coût Groq selon les tokens utilisés"""
        prompt_tokens = token_info.get('prompt_tokens', 0)
        completion_tokens = token_info.get('completion_tokens', 0)
        
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
        
        # 3. Format thinking/response respecté (pour Groq)
        if llm_used == "groq-70b":
            if "<thinking>" in response and "</thinking>" not in response:
                logger.warning(f"⚠️ Format thinking malformé de {llm_used}")
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
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retourne les statistiques du système hybride
        
        Returns:
            Dict: Statistiques complètes
        """
        router_stats = self.router.get_stats()
        
        return {
            **self.stats,
            **router_stats,
            'deepseek_percentage': (self.stats['deepseek_requests'] / max(self.stats['total_requests'], 1)) * 100,
            'groq_percentage': (self.stats['groq_requests'] / max(self.stats['total_requests'], 1)) * 100,
            'tools_usage_rate': (self.stats['tools_used'] / max(self.stats['total_requests'], 1)) * 100,
            'fallback_rate': (self.stats['fallbacks'] / max(self.stats['total_requests'], 1)) * 100
        }
    
    def reset_stats(self):
        """Remet à zéro les statistiques"""
        self.stats = {
            'total_requests': 0,
            'deepseek_requests': 0,
            'groq_requests': 0,
            'tools_used': 0,
            'fallbacks': 0
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
