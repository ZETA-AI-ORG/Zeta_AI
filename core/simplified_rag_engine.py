"""
🎯 MOTEUR RAG SIMPLIFIÉ - ARCHITECTURE RADICALE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Philosophie : Abandon de la recherche complexe Meili/Supabase
- ✅ Prompt statique avec infos entreprise
- ✅ Injection dynamique minimale (regex + Gemini + Meili coûts/stock)
- ✅ Checklist commande intégrée
- ✅ Token usage réel depuis OpenRouter
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import time
import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import re

from config import LLM_TRANSMISSION_TOKEN


CONFIDENCE_THRESHOLD = 0.8

from core.order_state_tracker import order_tracker
from core.payment_validator import validate_payment_cumulative, format_payment_for_prompt

from core.simplified_prompt_system import get_simplified_prompt_system
from core.price_calculator import UniversalPriceCalculator
from core.dynamic_context_injector import get_dynamic_context_injector
from core.llm_client import get_llm_client
from core.company_catalog_v2_loader import get_company_catalog_v2


@dataclass
class SimplifiedRAGResult:
    """Résultat du moteur RAG simplifié"""
    response: str
    confidence: float
    processing_time_ms: float
    checklist_state: str
    next_step: str
    detected_location: Optional[str]
    shipping_fee: Optional[str]
    
    # Métriques LLM (OpenRouter)
    usage: Optional[Dict[str, Any]] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    model: str = ""
    
    # Thinking
    thinking: str = ""


class SimplifiedRAGEngine:
    """Moteur RAG simplifié avec prompt statique + injection dynamique minimale"""
    
    def __init__(self):
        """Initialise le moteur RAG simplifié"""
        self.prompt_system = get_simplified_prompt_system()
        self.context_injector = get_dynamic_context_injector()
        self.llm_client = None
    
    async def initialize(self):
        """Initialise le client LLM"""
        if self.llm_client is None:
            self.llm_client = get_llm_client()
            print("✅ [SIMPLIFIED RAG] LLM client initialisé")
    
    async def process_query(
        self,
        query: str,
        user_id: str,
        company_id: str,
        company_name: str = "Rue du Grossiste",
        images: Optional[List[str]] = None,
        request_id: str = "unknown"
    ) -> SimplifiedRAGResult:
        """
        Traite une requête avec le système simplifié
        
        Pipeline:
        1. Collecte contexte dynamique (regex + Gemini + Meili)
        2. Construction prompt (statique + dynamique)
        3. Génération LLM avec token tracking
        4. Extraction thinking + response
        
        Args:
            query: Question utilisateur
            user_id: ID utilisateur
            company_id: ID entreprise
            company_name: Nom entreprise
            images: URLs images (optionnel)
            request_id: ID requête pour tracking
        
        Returns:
            SimplifiedRAGResult avec réponse + métriques
        """
        start_time = time.time()

        # Si un handoff a été déclenché, on met le bot en pause pour éviter qu'il réponde pendant l'intervention humaine.
        # (Le frontend/humain peut reprendre la conversation via un autre canal.)
        try:
            if order_tracker.get_flag(user_id, "bot_paused"):
                paused_msg = (os.getenv("SIMPLIFIED_RAG_PAUSED_MESSAGE") or "Je t'ai passé le responsable, il revient vers toi.").strip()
                processing_time = (time.time() - start_time) * 1000
                checklist = self.prompt_system.get_checklist_state(user_id, company_id)
                print("⏸️ [SIMPLIFIED RAG] bot_paused=True -> short-circuit")
                return SimplifiedRAGResult(
                    response=paused_msg,
                    confidence=1.0,
                    processing_time_ms=processing_time,
                    checklist_state=checklist.to_string(),
                    next_step=checklist.get_next_step(),
                    detected_location=None,
                    shipping_fee=None,
                    usage=None,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    cost=0.0,
                    model="paused",
                    thinking="",
                )
        except Exception:
            pass

        # ANSI colors (console)
        C_RESET = "\033[0m"
        C_YELLOW = "\033[33m"
        C_RED = "\033[31m"
        C_GREEN = "\033[32m"
        
        print(f"\n🎯 [SIMPLIFIED RAG] Début traitement: '{query[:50]}...'")
        print(f"🏢 Company: {company_id[:12]}... | User: {user_id[:12]}...")
        
        try:
            current_turn = 0
            try:
                current_turn = order_tracker.bump_turn(user_id)
            except Exception as _turn_e:
                print(f"⚠️ [ORDER_STATE] bump_turn_error: {type(_turn_e).__name__}: {_turn_e}")

            # 1. Initialisation LLM si nécessaire
            if self.llm_client is None:
                await self.initialize()
            
            # 2. Collecte contexte dynamique en parallèle
            print("📦 [CONTEXT] Collecte contexte dynamique...")
            dynamic_context = await self.context_injector.collect_dynamic_context(
                query=query,
                user_id=user_id,
                company_id=company_id
            )

            # Fallback persistance livraison (zone/frais) :
            # si le message courant ne contient pas la zone, on réutilise la dernière zone connue.
            try:
                if (not dynamic_context.get("detected_location")) and int(current_turn or 0) > 1:
                    slot_meta = order_tracker.get_slot_meta(user_id)
                    zone_meta = None
                    try:
                        zone_meta = (slot_meta.get("slot_meta") or {}).get("ZONE")
                    except Exception:
                        zone_meta = None

                    zone_source = str((zone_meta or {}).get("source") or "").strip().upper()
                    zone_conf = (zone_meta or {}).get("confidence")
                    try:
                        zone_conf_f = float(zone_conf) if zone_conf is not None else 0.0
                    except Exception:
                        zone_conf_f = 0.0

                    if zone_source and (zone_source not in {"CONTEXT_INFERRED", "UNKNOWN"}) and zone_conf_f >= 0.8:
                        st_prev = order_tracker.get_state(user_id)
                        prev_zone = str(getattr(st_prev, "zone", "") or "").strip()
                        if prev_zone:
                            z_name, z_info = self.context_injector.resolve_zone_info(prev_zone)
                            if z_name:
                                dynamic_context["detected_location"] = z_name
                            if z_info:
                                fee = z_info.get("fee")
                                if isinstance(fee, int):
                                    dynamic_context["shipping_fee"] = f"{fee} FCFA"
                                else:
                                    dynamic_context["shipping_fee"] = str(fee)
                                dynamic_context["delivery_time"] = z_info.get("delay")
            except Exception as e:
                print(f"⚠️ [CONTEXT] Fallback zone/frais: {type(e).__name__}: {e}")

            # 2.b Vision (Gemini ONLY) si images[] présent
            # NOTE: le chemin Simplified RAG ne doit plus dépendre d'OCR legacy.
            vision_summary = ""
            payment_verdict_line = ""
            has_image = bool(images and len(images) > 0)
            if has_image:
                try:
                    analyze_product_with_gemini = None
                    try:
                        from Zeta_AI.vision_gemini import analyze_product_with_gemini as _analyze_product_with_gemini

                        analyze_product_with_gemini = _analyze_product_with_gemini
                        print("🖼️ [VISION][GEMINI] import=Zeta_AI.vision_gemini")
                    except Exception as _imp_e1:
                        try:
                            from vision_gemini import analyze_product_with_gemini as _analyze_product_with_gemini

                            analyze_product_with_gemini = _analyze_product_with_gemini
                            print("🖼️ [VISION][GEMINI] import=vision_gemini")
                        except Exception as _imp_e2:
                            raise ModuleNotFoundError(
                                f"vision_gemini import failed: {type(_imp_e1).__name__}: {_imp_e1} | {type(_imp_e2).__name__}: {_imp_e2}"
                            )

                    image_url = str((images or [""])[0] or "").strip()
                    if image_url:
                        default_company_phone = (os.getenv("WAVE_PHONE") or os.getenv("COMPANY_WAVE_PHONE") or "0787360757").strip()
                        try:
                            default_required_amount = int(str(os.getenv("EXPECTED_DEPOSIT") or "2000").strip())
                        except Exception:
                            default_required_amount = 2000

                        print(f"🖼️ [VISION][GEMINI] start | image_url={image_url[:120]}... | phone={default_company_phone} | required={default_required_amount}")
                        gemini_result, gemini_meta = await analyze_product_with_gemini(
                            image_url=image_url,
                            user_message=query,
                            company_phone=default_company_phone,
                            required_amount=default_required_amount,
                        )

                        # Logs robustesse (raw + parsed)
                        try:
                            raw_txt = str((gemini_result or {}).get("raw") or "")
                            raw_short = raw_txt[:600] + ("..." if len(raw_txt) > 600 else "")
                            meta_short = {}
                            if isinstance(gemini_meta, dict):
                                for k in ["model", "provider", "usage", "prompt_tokens", "completion_tokens", "total_tokens", "total_cost"]:
                                    if k in gemini_meta:
                                        meta_short[k] = gemini_meta.get(k)
                            print(f"🖼️ [VISION][GEMINI] meta={json.dumps(meta_short, ensure_ascii=False)}")
                            if raw_short:
                                print(f"🖼️ [VISION][GEMINI] raw(600)=\n{raw_short}")
                        except Exception as _log_e:
                            print(f"🖼️ [VISION][GEMINI] log_error: {type(_log_e).__name__}: {_log_e}")

                        # Normaliser vers 2 sorties: produit + transactions
                        detected_objects: List[Dict[str, Any]] = []
                        filtered_transactions: List[Dict[str, Any]] = []

                        # Produit
                        try:
                            product_name = str((gemini_result or {}).get("name") or "").strip()
                            conf = (gemini_result or {}).get("confidence")
                            is_product_image = (gemini_result or {}).get("is_product_image")
                            if isinstance(is_product_image, bool) and is_product_image and product_name:
                                try:
                                    conf_f = float(conf) if conf is not None else 0.0
                                except Exception:
                                    conf_f = 0.0
                                detected_objects.append({"label": product_name, "confidence": conf_f, "source": "gemini"})
                                order_tracker.update_produit(user_id, product_name, source="VISION_GEMINI", confidence=max(0.0, min(1.0, conf_f)))
                                print(f"📦 [VISION][GEMINI] produit='{product_name}' conf={conf}")
                        except Exception as _prod_e:
                            print(f"🖼️ [VISION][GEMINI] product_parse_error: {type(_prod_e).__name__}: {_prod_e}")

                        # Paiement
                        try:
                            payment = (gemini_result or {}).get("payment")
                            if isinstance(payment, dict):
                                error_code = str(payment.get("error_code") or "").strip() or None
                                amount = payment.get("amount")
                                try:
                                    amount_i = int(float(amount)) if amount is not None else 0
                                except Exception:
                                    amount_i = 0

                                if error_code:
                                    print(f"💳 [VISION][GEMINI] payment_error_code={error_code}")

                                    # Cas spécial: montant insuffisant = on a un montant détecté, donc c'est INSUFFICIENT (pas REFUSED)
                                    if str(error_code).upper() == "MONTANT_INSUFFISANT" and amount_i > 0:
                                        diff_i = amount_i - int(default_required_amount or 0)
                                        missing_i = abs(diff_i) if diff_i < 0 else 0
                                        payment_verdict_line = (
                                            "PAYMENT_VERDICT"
                                            f"|status=INSUFFICIENT"
                                            f"|received={amount_i}"
                                            f"|required={default_required_amount}"
                                            f"|diff={diff_i}"
                                            f"|missing={missing_i}"
                                            f"|message=GEMINI_ERROR:{error_code}"
                                        )
                                        # Persister un état explicite (INSUFFICIENT)
                                        try:
                                            order_tracker.update_paiement(
                                                user_id,
                                                f"insuffisant_{amount_i}F",
                                                source="VERDICT",
                                                confidence=0.95,
                                            )
                                        except Exception:
                                            pass
                                    else:
                                        filtered_transactions.append({"amount": 0, "currency": "FCFA", "error_message": f"GEMINI_ERROR:{error_code}"})
                                        payment_verdict_line = (
                                            "PAYMENT_VERDICT"
                                            f"|status=REFUSED"
                                            f"|received=0"
                                            f"|required={default_required_amount}"
                                            f"|diff={-default_required_amount}"
                                            f"|missing={default_required_amount}"
                                            f"|message=GEMINI_ERROR:{error_code}"
                                        )

                                        # Persister un état explicite (REFUSED) pour transparence
                                        try:
                                            order_tracker.update_paiement(
                                                user_id,
                                                f"refusé_GEMINI_ERROR:{error_code}",
                                                source="VERDICT",
                                                confidence=0.95,
                                            )
                                        except Exception:
                                            pass

                                    # NV3: tracer la source même si on ne persiste pas un paiement valide
                                    try:
                                        order_tracker.set_slot_meta(user_id, "PAIEMENT", source="VISION_GEMINI", confidence=0.8)
                                    except Exception:
                                        pass
                                elif amount_i > 0:
                                    filtered_transactions.append({"amount": amount_i, "currency": str(payment.get("currency") or "FCFA"), "reference": str(payment.get("reference") or "")})
                                    print(f"💳 [VISION][GEMINI] payment_amount={amount_i} {payment.get('currency') or 'FCFA'}")

                                    try:
                                        order_tracker.set_slot_meta(user_id, "PAIEMENT", source="VISION_GEMINI", confidence=0.9)
                                    except Exception:
                                        pass

                                try:
                                    if filtered_transactions and not error_code:
                                        validation = validate_payment_cumulative(
                                            current_transactions=filtered_transactions,
                                            conversation_history=str(dynamic_context.get('conversation_history') or ''),
                                            required_amount=default_required_amount,
                                        )
                                        payment_verdict_line = format_payment_for_prompt(validation)
                                        if validation and validation.get("status") == "VALID":
                                            total_received = int(validation.get("total_received") or 0)
                                            order_tracker.update_paiement(user_id, f"validé_{total_received}F", source="VERDICT", confidence=1.0)
                                            print(f"💾 [ORDER_STATE][PAYMENT] saved validé_{total_received}F")
                                        else:
                                            try:
                                                st = str(validation.get("status") or "").upper()
                                                total_received = int(validation.get("total_received") or 0)
                                            except Exception:
                                                st = ""
                                                total_received = 0
                                            if st:
                                                # Persister les états non-validants
                                                # - INSUFFICIENT -> insuffisant_XXXXF
                                                # - REFUSED -> refusé
                                                # - NONE -> (ne rien persister)
                                                try:
                                                    if st == "INSUFFICIENT" and total_received > 0:
                                                        order_tracker.update_paiement(
                                                            user_id,
                                                            f"insuffisant_{total_received}F",
                                                            source="VERDICT",
                                                            confidence=0.95,
                                                        )
                                                        print(f"💾 [ORDER_STATE][PAYMENT] saved insuffisant_{total_received}F")
                                                    elif st == "REFUSED":
                                                        # Conserver une valeur courte et stable
                                                        order_tracker.update_paiement(
                                                            user_id,
                                                            "refusé",
                                                            source="VERDICT",
                                                            confidence=0.95,
                                                        )
                                                        print("💾 [ORDER_STATE][PAYMENT] saved refusé")
                                                    else:
                                                        print(
                                                            f"💾 [ORDER_STATE][PAYMENT] not saved ({st} received={total_received} required={default_required_amount})"
                                                        )
                                                except Exception as _st_save_e:
                                                    print(f"💾 [ORDER_STATE][PAYMENT] state_save_error: {type(_st_save_e).__name__}: {_st_save_e}")
                                except Exception as _pv_e:
                                    print(f"🖼️ [VISION][GEMINI] payment_verdict_error: {type(_pv_e).__name__}: {_pv_e}")
                        except Exception as _pay_e:
                            print(f"🖼️ [VISION][GEMINI] payment_parse_error: {type(_pay_e).__name__}: {_pay_e}")

                        # Injecter un résumé compact dans le prompt (même si LLM n'a pas "vu" l'image)
                        try:
                            prod_s = detected_objects[0]["label"] if detected_objects else "∅"
                            pay_s = "∅"
                            if filtered_transactions:
                                t0 = filtered_transactions[0]
                                if t0.get("amount"):
                                    pay_s = f"{t0.get('amount')}F"
                                elif t0.get("error_message"):
                                    pay_s = str(t0.get("error_message"))
                            vision_summary = f"VISION_GEMINI: produit={prod_s} | paiement={pay_s}"
                            print(f"🧩 [VISION][GEMINI] summary='{vision_summary}'")
                        except Exception:
                            vision_summary = ""
                except Exception as e:
                    print(f"🖼️ [VISION][GEMINI] fatal_error: {type(e).__name__}: {e}")

            # Mise à jour OrderStateTracker via signaux déterministes (sans RAG retrieval)
            try:
                detected_location = dynamic_context.get('detected_location')
                if detected_location:
                    order_tracker.update_zone(user_id, str(detected_location), source="CONTEXT_INFERRED", confidence=0.7)
            except Exception as e:
                print(f"⚠️ [ORDER_STATE] Erreur update zone: {e}")

            phone_match = None
            try:
                msg_lower = str(query or "").lower()

                # Téléphone CI (heuristique simple)
                # On persiste les numéros au format 0XXXXXXXXX (10 chiffres), y compris si fournis en +225.
                normalized_phone = ""
                try:
                    from FIX_CONTEXT_LOSS_COMPLETE import validate_phone_ci

                    v = validate_phone_ci(str(query or ""))
                    if isinstance(v, dict) and v.get("valid") and v.get("normalized"):
                        normalized_phone = str(v.get("normalized") or "").strip()
                except Exception:
                    normalized_phone = ""

                if normalized_phone and re.fullmatch(r"0\d{9}", normalized_phone):
                    phone_match = True
                    order_tracker.update_numero(user_id, normalized_phone, source="USER_TEXT", confidence=1.0)
                else:
                    phone_match = re.search(r"\b(0\d{9})\b", str(query or ""))
                    if phone_match:
                        order_tracker.update_numero(user_id, phone_match.group(1), source="USER_TEXT", confidence=1.0)

                # Quantité (carton/paquets) - persistance (slot obligatoire)
                qty_match = re.search(
                    r"\b(\d+)\s*(cartons?|carton|paquets?|packs?|unit[ée]s?)\b",
                    str(query or ""),
                    flags=re.IGNORECASE,
                )
                if qty_match:
                    q = str(query or "")
                    q_low = q.lower()

                    # On ne valide pas une quantité si c'est une question/hypothèse (devis)
                    is_interrogative = (
                        "?" in q
                        or "ça fait combien" in q_low
                        or "ca fait combien" in q_low
                        or q_low.strip().startswith("et si")
                        or q_low.strip().startswith("si je")
                        or "combien" in q_low
                    )

                    # On valide uniquement si intention d'achat explicite
                    has_commit_verb = bool(
                        re.search(
                            r"\b(je\s+(prends|veux|commande|confirme|ach[eè]te)|mets\s*moi|met\s*moi|envoie|envoyez|ok\s+pour|c['’]?est\s+bon\s+pour|on\s+part\s+sur)\b",
                            q_low,
                            flags=re.IGNORECASE,
                        )
                    )

                    if (not is_interrogative) and has_commit_verb:
                        n = qty_match.group(1)
                        u = qty_match.group(2)
                        order_tracker.update_quantite(user_id, f"{n} {u}".strip(), source="USER_TEXT", confidence=1.0)
            except Exception as e:
                print(f"⚠️ [ORDER_STATE] Erreur update téléphone/paiement: {e}")

            phone_verdict_line = ""
            location_verdict_line = ""
            validation_errors_block = ""

            def _kv_get(line: str) -> Dict[str, str]:
                out: Dict[str, str] = {}
                try:
                    for part in str(line or "").split("|"):
                        p = part.strip()
                        if not p:
                            continue
                        if "=" in p:
                            k, v = p.split("=", 1)
                            out[k.strip().lower()] = v.strip()
                except Exception:
                    return {}
                return out

            def _xml_escape(s: str) -> str:
                s = str(s or "")
                return (
                    s.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                )

            def _build_validation_errors_xml(payment_line: str, phone_issue: Dict[str, str]) -> str:
                blocks: List[str] = []

                # Paiement
                pv = _kv_get(payment_line)
                pv_status = (pv.get("status") or "").strip().upper()
                if pv_status in {"INSUFFICIENT", "REFUSED"}:
                    detected_amount = (pv.get("received") or "").strip()
                    required_amount = (pv.get("required") or "").strip()
                    missing_amount = (pv.get("missing") or "").strip()
                    message = (pv.get("message") or "").strip() or pv_status
                    blocks.append(
                        "  <PAIEMENT>\n"
                        f"    <status>{_xml_escape(pv_status)}</status>\n"
                        f"    <detected_amount>{_xml_escape((detected_amount + 'F') if detected_amount and not detected_amount.endswith('F') else detected_amount)}</detected_amount>\n"
                        f"    <required_amount>{_xml_escape((required_amount + 'F') if required_amount and not required_amount.endswith('F') else required_amount)}</required_amount>\n"
                        f"    <missing_amount>{_xml_escape((missing_amount + 'F') if missing_amount and not missing_amount.endswith('F') else missing_amount)}</missing_amount>\n"
                        f"    <message>{_xml_escape(message)}</message>\n"
                        "  </PAIEMENT>"
                    )

                # Téléphone
                if phone_issue:
                    status = str(phone_issue.get("status") or "").strip()
                    detected_value = str(phone_issue.get("detected_value") or "").strip()
                    expected_format = str(phone_issue.get("expected_format") or "").strip()
                    message = str(phone_issue.get("message") or "").strip()
                    blocks.append(
                        "  <TÉLÉPHONE>\n"
                        f"    <status>{_xml_escape(status)}</status>\n"
                        f"    <detected_value>{_xml_escape(detected_value)}</detected_value>\n"
                        f"    <expected_format>{_xml_escape(expected_format)}</expected_format>\n"
                        f"    <message>{_xml_escape(message)}</message>\n"
                        "  </TÉLÉPHONE>"
                    )

                return "\n".join(blocks)

            # Détecter un téléphone invalide (texte contient des chiffres mais pas 0XXXXXXXXX)
            phone_issue: Dict[str, str] = {}
            try:
                raw_q = str(query or "")
                digits = re.sub(r"\D+", "", raw_q)
                has_phone_like = bool(digits) and ("tel" in raw_q.lower() or "num" in raw_q.lower() or len(digits) >= 6)
                if has_phone_like and not phone_match:
                    # Exemple: 070000, +225..., 7 chiffres, etc.
                    # On renvoie une erreur de format, sans persister.
                    phone_issue = {
                        "status": "INVALID_FORMAT",
                        "detected_value": digits[:16],
                        "expected_format": "10 chiffres (07XXXXXXXX ou 01XXXXXXXX)",
                        "message": "Numéro incomplet ou format non reconnu",
                    }
            except Exception:
                phone_issue = {}

            try:
                state = order_tracker.get_state(user_id)
                numero = str(getattr(state, "numero", "") or "").strip()
                zone = str(getattr(state, "zone", "") or "").strip()
                quantite = str(getattr(state, "quantite", "") or "").strip()

                if numero:
                    phone_verdict_line = f"PHONE_VERDICT|status=OK|value={numero}"
                else:
                    if phone_issue:
                        phone_verdict_line = f"PHONE_VERDICT|status=INVALID_FORMAT|value={phone_issue.get('detected_value','')}|expected={phone_issue.get('expected_format','')}|message={phone_issue.get('message','')}"
                    else:
                        phone_verdict_line = "PHONE_VERDICT|status=MISSING"

                if zone and zone != "Non détecté":
                    location_verdict_line = f"LOCATION_VERDICT: [PRESENT] value={zone}"
                else:
                    location_verdict_line = "LOCATION_VERDICT: [MISSING]"

                # Quantité verdict simple (présence/absence) - pour guider Jessica
                quantite_verdict_line = ""
                if quantite:
                    quantite_verdict_line = f"QUANTITE_VERDICT: [PRESENT] value={quantite}"
                else:
                    quantite_verdict_line = "QUANTITE_VERDICT: [MISSING]"

                # Construire validation_errors_block à partir des signaux déterministes
                try:
                    validation_errors_block = _build_validation_errors_xml(payment_verdict_line, phone_issue)
                except Exception:
                    validation_errors_block = ""
            except Exception as e:
                print(f"⚠️ [CTX_VERDICTS] state_error: {type(e).__name__}: {e}")
            
            print(f"✅ [CONTEXT] Zone: {dynamic_context.get('detected_location', 'N/A')}")
            print(f"✅ [CONTEXT] Frais: {dynamic_context.get('shipping_fee', 'N/A')}")

            # 2.c Instruction immédiate (Python -> Jessica)
            instruction_block = ""
            try:
                instruction_mode = (os.getenv("INSTRUCTION_MODE") or "rigid").strip().lower()

                # Mode d'ablation: couper entièrement l'instruction_immediate
                if instruction_mode in {"off", "none", "0", "false"}:
                    instruction_block = ""
                    raise RuntimeError("INSTRUCTION_MODE_OFF")

                st_now = order_tracker.get_state(user_id)
                next_field = order_tracker.get_next_required_field(user_id, current_turn=current_turn)

                slot_meta_bundle = None
                try:
                    slot_meta_bundle = order_tracker.get_slot_meta(user_id)
                except Exception:
                    slot_meta_bundle = {"turn": current_turn, "ask_counts": {}, "last_asked": {}, "slot_meta": {}}

                msg_lower = str(query or "").lower()

                def _detect_user_question(q: str) -> Dict[str, str]:
                    qt = str(q or "").strip()
                    ql = qt.lower()
                    is_question = (
                        ("?" in qt)
                        or ("combien" in ql)
                        or ("prix" in ql)
                        or ("ça fait combien" in ql)
                        or ("ca fait combien" in ql)
                        or ("livraison" in ql)
                        or ("livrez" in ql)
                        or ("delai" in ql)
                        or ("délai" in ql)
                    )

                    topic = ""
                    if any(k in ql for k in ["livraison", "livrez", "livrer", "frais", "commune", "quartier", "adresse"]):
                        topic = "DELIVERY"
                    elif any(k in ql for k in ["combien", "prix", "tarif", "coût", "cout", "fcfa"]):
                        topic = "PRICE"
                    elif any(k in ql for k in ["dispo", "disponible", "stock"]):
                        topic = "AVAILABILITY"
                    elif any(k in ql for k in ["délai", "delai", "quand", "heure", "aujourd", "demain"]):
                        topic = "DELIVERY_TIME"
                    return {
                        "is_question": "true" if is_question else "false",
                        "topic": topic,
                        "text": qt,
                    }

                def _infer_intent(q: str) -> Dict[str, str]:
                    qt = str(q or "").strip()
                    ql = qt.lower()

                    is_hypo = bool(
                        ("si je" in ql)
                        or ("et si" in ql)
                        or ("suppos" in ql)
                        or ("imagin" in ql)
                    )
                    has_commit = bool(
                        re.search(
                            r"\b(je\s+(prends|veux|commande|confirme|ach[eè]te)|on\s+part\s+sur|mets?\s*moi|mettez\s*moi|ok\s+pour|c['’]?est\s+bon\s+pour|envoie|envoyez)\b",
                            ql,
                            flags=re.IGNORECASE,
                        )
                    )

                    user_q = _detect_user_question(qt)
                    topic = user_q.get("topic") or ""

                    intent = ""
                    reformulation = ""

                    if user_q.get("is_question") == "true" and topic == "DELIVERY":
                        intent = "ASK_DELIVERY_INFO"
                        reformulation = "Le client demande les informations de livraison."
                    elif user_q.get("is_question") == "true" and topic in {"PRICE", "AVAILABILITY"}:
                        intent = "ASK_PRODUCT_INFO"
                        reformulation = "Le client demande une information sur le produit (prix/disponibilité)."
                    elif user_q.get("is_question") == "true" and topic == "DELIVERY_TIME":
                        intent = "ASK_DELIVERY_TIME"
                        reformulation = "Le client demande le délai de livraison."
                    elif any(k in ql for k in ["paiement", "payer", "paye", "paye", "acompte", "wave", "transfert"]):
                        intent = "PAYMENT_DISCUSSION"
                        reformulation = "Le client parle du paiement (intention ou preuve)."
                    elif has_commit:
                        intent = "COMMIT_ORDER"
                        reformulation = "Le client exprime un engagement d'achat/commande."
                    else:
                        intent = "CONTINUE_ORDER"
                        reformulation = "Le client continue la conversation de commande."

                    certainty = "PROBABLE"
                    if user_q.get("is_question") == "true":
                        certainty = "CERTAIN"
                    elif is_hypo:
                        certainty = "HYPOTHESE"
                    elif has_commit:
                        certainty = "CERTAIN"

                    return {
                        "intent": intent,
                        "certainty": certainty,
                        "reformulation": reformulation,
                        "user_question_is_question": user_q.get("is_question") or "false",
                        "user_question_topic": topic,
                        "user_question_text": user_q.get("text") or "",
                    }

                def _build_historique_compact(
                    ask_counts: Dict[str, Any],
                    last_asked: Dict[str, Any],
                    turn: int,
                ) -> Dict[str, str]:
                    cooldowns = {
                        "PRODUIT": 2,
                        "SPECS": 2,
                        "QUANTITE": 1,
                        "ZONE": 1,
                        "NUMERO": 2,
                        "PAIEMENT": 2,
                    }

                    def _norm(k: str) -> str:
                        kk = str(k or "").upper().strip()
                        if kk in {"TELEPHONE", "TÉLÉPHONE", "TEL", "NUMERO", "NUMÉRO"}:
                            return "NUMERO"
                        if kk in {"QUANTITE", "QUANTITÉ"}:
                            return "QUANTITE"
                        return kk

                    # Normaliser les dictionnaires entrants pour consolider les variantes (accents / legacy)
                    norm_ask_counts: Dict[str, int] = {}
                    for k, v in (ask_counts or {}).items():
                        try:
                            nk = _norm(k)
                            norm_ask_counts[nk] = norm_ask_counts.get(nk, 0) + int(v or 0)
                        except Exception:
                            continue

                    norm_last_asked: Dict[str, int] = {}
                    for k, v in (last_asked or {}).items():
                        try:
                            nk = _norm(k)
                            norm_last_asked[nk] = max(norm_last_asked.get(nk, 0), int(v or 0))
                        except Exception:
                            continue

                    asked_sorted = []
                    for k, v in (norm_last_asked or {}).items():
                        try:
                            asked_sorted.append((_norm(k), int(v or 0)))
                        except Exception:
                            continue
                    asked_sorted.sort(key=lambda x: x[1], reverse=True)
                    asked_sorted = asked_sorted[:6]

                    recent_xml = "\n".join(
                        [
                            f"      <q slot=\"{k}\" turn=\"{t}\" asked=\"{int((norm_ask_counts or {}).get(k) or 0)}\"/>"
                            for (k, t) in asked_sorted
                        ]
                    )
                    if recent_xml:
                        recent_xml = "    <recent_questions>\n" + recent_xml + "\n    </recent_questions>"
                    else:
                        recent_xml = "    <recent_questions></recent_questions>"

                    bans = []
                    for slot, cd in cooldowns.items():
                        last_t = None
                        try:
                            last_t = int((norm_last_asked or {}).get(slot) or 0)
                        except Exception:
                            last_t = 0
                        delta = int(turn or 0) - int(last_t or 0)
                        if int(cd or 0) > 0 and int(last_t or 0) > 0 and delta < int(cd or 0):
                            bans.append((slot, int(cd) - delta))

                    bans_xml = "\n".join([f"      <ban slot=\"{s}\" remaining=\"{rem}\"/>" for (s, rem) in bans])
                    if bans_xml:
                        bans_xml = "    <cooldown_bans>\n" + bans_xml + "\n    </cooldown_bans>"
                    else:
                        bans_xml = "    <cooldown_bans></cooldown_bans>"

                    return {"recent": recent_xml, "bans": bans_xml}

                def _is_triggered() -> bool:
                    # Triggers visés: paiement (verdict), tel (regex), zone (regex)
                    if bool(payment_verdict_line):
                        return True
                    # Intention paiement sans preuve (ex: "je vais faire l'acompte")
                    if any(k in msg_lower for k in ["acompte", "wave", "payer", "payé", "paye", "paiement", "transfert", "envoyé", "envoye"]):
                        return True
                    if bool(re.search(r"\b(0\d{9})\b", str(query or ""))):
                        return True
                    if bool(dynamic_context.get("detected_location")):
                        return True
                    return False

                triggered = _is_triggered()

                def _next_question_for(field: Optional[str]) -> str:
                    f = str(field or "").upper().strip()
                    if f == "PRODUIT":
                        return "Tu veux quel produit exactement (marque/modèle) stp ?"
                    if f == "SPECS":
                        return "Tu veux quelle taille et quel type exactement (ex: T3, T4 / pants ou adhésive) ?"
                    if f == "QUANTITÉ":
                        return "Tu veux combien (1 carton, 2 cartons, ou combien de paquets) ?"
                    if f == "ZONE":
                        return "Tu es dans quelle commune/quartier pour la livraison stp ?"
                    if f in {"NUMÉRO", "NUMERO", "TELEPHONE", "TÉLÉPHONE"}:
                        return "Ton numéro WhatsApp pour le livreur stp ?"
                    if f == "PAIEMENT":
                        return "Tu peux envoyer l’acompte Wave de 2000 FCFA et la capture stp ?"
                    return ""

                trigger_type = "NONE"
                if payment_verdict_line:
                    trigger_type = "PAYMENT"
                elif any(k in msg_lower for k in ["acompte", "wave", "payer", "payé", "paye", "paiement", "transfert", "envoyé", "envoye"]):
                    trigger_type = "PAYMENT"
                elif re.search(r"\b(0\d{9})\b", str(query or "")):
                    trigger_type = "TEL"
                elif dynamic_context.get("detected_location"):
                    trigger_type = "ZONE"

                if triggered:
                    # Construire instruction XML minimaliste
                    ack_type = ""
                    ack_status = ""
                    if trigger_type == "PAYMENT":
                        ack_type = "paiement"
                        # Extraire status depuis line si possible
                        # Support 2 formats:
                        # - legacy: PAYMENT_VERDICT: [VALID] ...
                        # - kv: PAYMENT_VERDICT|status=VALID|...
                        m = re.search(r"\[(VALID|INSUFFICIENT|REFUSED|NONE)\]", str(payment_verdict_line or ""), re.IGNORECASE)
                        if m:
                            ack_status = m.group(1).upper()
                        else:
                            m2 = re.search(r"\bstatus\s*=\s*(VALID|INSUFFICIENT|REFUSED|NONE)\b", str(payment_verdict_line or ""), re.IGNORECASE)
                            ack_status = (m2.group(1).upper() if m2 else "PENDING")
                    elif trigger_type == "TEL":
                        ack_type = "telephone"
                        ack_status = "OK" if getattr(st_now, "numero", None) else "DETECTED"
                    elif trigger_type == "ZONE":
                        ack_type = "zone"
                        ack_status = "OK" if getattr(st_now, "zone", None) else "DETECTED"

                    question = _next_question_for(next_field)
                    field_xml = str(next_field or "").strip()

                    try:
                        if next_field:
                            order_tracker.record_asked(user_id, str(next_field), int(current_turn or 0))
                    except Exception:
                        pass

                    ask_counts = slot_meta_bundle.get("ask_counts") if isinstance(slot_meta_bundle, dict) else {}
                    ask_counts = ask_counts if isinstance(ask_counts, dict) else {}
                    last_asked = slot_meta_bundle.get("last_asked") if isinstance(slot_meta_bundle, dict) else {}
                    last_asked = last_asked if isinstance(last_asked, dict) else {}
                    slot_meta = slot_meta_bundle.get("slot_meta") if isinstance(slot_meta_bundle, dict) else {}
                    slot_meta = slot_meta if isinstance(slot_meta, dict) else {}

                    intent_pack = _infer_intent(str(query or ""))
                    hist_pack = _build_historique_compact(ask_counts, last_asked, int(current_turn or 0))
                    must_answer = (intent_pack.get("user_question_is_question") or "false") == "true"

                    intention_xml = (
                        "    <intention_client>\n"
                        f"      <intent>{intent_pack.get('intent') or ''}</intent>\n"
                        f"      <certainty>{intent_pack.get('certainty') or ''}</certainty>\n"
                        f"      <reformulation>{intent_pack.get('reformulation') or ''}</reformulation>\n"
                        f"      <user_question topic=\"{intent_pack.get('user_question_topic') or ''}\">{intent_pack.get('user_question_text') or ''}</user_question>\n"
                        "    </intention_client>"
                    )

                    # Simplified: only intention_client, no priorite_reponse or historique_compact

                    try:
                        missing_now = sorted(list(st_now.get_missing_fields()))
                    except Exception:
                        missing_now = []
                    missing_set = set([str(m).upper().strip() for m in (missing_now or [])])

                    def _v(attr: str) -> str:
                        return str(getattr(st_now, attr, "") or "").strip()

                    def _slot_xml(field: str, value: str) -> str:
                        f = str(field or "").upper().strip()
                        status = "PRESENT" if value else ("MISSING" if f in missing_set else "UNKNOWN")
                        asked = int(ask_counts.get(f) or 0)
                        last = int(last_asked.get(f) or 0)
                        meta = slot_meta.get(f) if isinstance(slot_meta.get(f), dict) else {}
                        src = str((meta or {}).get("source") or "")
                        conf = (meta or {}).get("confidence")
                        vv = str(value or "").replace("&", "and")
                        return (
                            f"      <slot name=\"{f}\" status=\"{status}\" asked=\"{asked}\" last_asked_turn=\"{last}\" source=\"{src}\" confidence=\"{conf}\">{vv}</slot>"
                        )

                    slots_block = (
                        "    <status_slots>\n"
                        + "\n".join(
                            [
                                _slot_xml("PRODUIT", _v("produit")),
                                _slot_xml("SPECS", _v("produit_details")),
                                _slot_xml("QUANTITÉ", _v("quantite")),
                                _slot_xml("ZONE", _v("zone")),
                                _slot_xml("NUMÉRO", _v("numero")),
                                _slot_xml("PAIEMENT", _v("paiement")),
                            ]
                        )
                        + "\n    </status_slots>"
                    )

                    tracking_block = (
                        "    <tracking>\n"
                        f"      <turn>{int(current_turn or 0)}</turn>\n"
                        "    </tracking>"
                    )

                    # Mode "soft": fournir un état + intention, sans imposer de question au modèle.
                    # (Ablation utile pour vérifier si le bégaiement vient d'un must_do trop rigide)
                    is_soft = instruction_mode in {"soft", "status_only", "status", "advisory"}

                    # Si complet, on laisse Jessica gérer la finalisation, mais on garde une consigne simple.
                    if not next_field:
                        if is_soft:
                            instruction_block = (
                                "    <triggered>true</triggered>\n"
                                f"    <trigger_type>{trigger_type}</trigger_type>\n"
                                f"{intention_xml}\n"
                                "    <intent>FINALIZE_OR_RECAP</intent>\n"
                                "    <must_ack>\n"
                                f"      <what>{ack_type or 'signal'}</what>\n"
                                f"      <status>{ack_status or 'OK'}</status>\n"
                                "    </must_ack>\n"
                                f"    <status_next>NONE</status_next>\n"
                                f"{tracking_block}\n"
                                f"{slots_block}\n"
                                "    <constraints>\n"
                                "      <one_question>true</one_question>\n"
                                "      <no_validation_loop>true</no_validation_loop>\n"
                                "    </constraints>"
                            )
                        else:
                            instruction_block = (
                                "    <triggered>true</triggered>\n"
                                f"    <trigger_type>{trigger_type}</trigger_type>\n"
                                f"{intention_xml}\n"
                                "    <must_ack>\n"
                                f"      <what>{ack_type or 'signal'}</what>\n"
                                f"      <status>{ack_status or 'OK'}</status>\n"
                                "    </must_ack>\n"
                                "    <must_do>\n"
                                "      <action>FINALIZE_OR_RECAP</action>\n"
                                "      <field>NONE</field>\n"
                                "      <question></question>\n"
                                "    </must_do>\n"
                                f"{tracking_block}\n"
                                f"{slots_block}\n"
                                "    <constraints>\n"
                                "      <one_question>true</one_question>\n"
                                "      <no_validation_loop>true</no_validation_loop>\n"
                                "    </constraints>"
                            )
                    else:
                        if is_soft:
                            instruction_block = (
                                "    <triggered>true</triggered>\n"
                                f"    <trigger_type>{trigger_type}</trigger_type>\n"
                                f"{intention_xml}\n"
                                "    <intent>ASK_NEXT_MISSING_FIELD</intent>\n"
                                "    <must_ack>\n"
                                f"      <what>{ack_type or 'signal'}</what>\n"
                                f"      <status>{ack_status or 'OK'}</status>\n"
                                "    </must_ack>\n"
                                f"    <status_next>{field_xml}</status_next>\n"
                                f"    <suggested_question>{question}</suggested_question>\n"
                                f"{tracking_block}\n"
                                f"{slots_block}\n"
                                "    <constraints>\n"
                                "      <one_question>true</one_question>\n"
                                "      <no_validation_loop>true</no_validation_loop>\n"
                                "    </constraints>"
                            )
                        else:
                            instruction_block = (
                                "    <triggered>true</triggered>\n"
                                f"    <trigger_type>{trigger_type}</trigger_type>\n"
                                f"{intention_xml}\n"
                                "    <must_ack>\n"
                                f"      <what>{ack_type or 'signal'}</what>\n"
                                f"      <status>{ack_status or 'OK'}</status>\n"
                                "    </must_ack>\n"
                                "    <must_do>\n"
                                "      <action>ASK_NEXT_MISSING_FIELD</action>\n"
                                f"      <field>{field_xml}</field>\n"
                                f"      <question>{question}</question>\n"
                                "    </must_do>\n"
                                f"{tracking_block}\n"
                                f"{slots_block}\n"
                                "    <constraints>\n"
                                "      <one_question>true</one_question>\n"
                                "      <no_validation_loop>true</no_validation_loop>\n"
                                "    </constraints>"
                            )
                else:
                    intent_pack = _infer_intent(str(query or ""))
                    intention_xml = (
                        "    <intention_client>\n"
                        f"      <intent>{intent_pack.get('intent') or ''}</intent>\n"
                        f"      <certainty>{intent_pack.get('certainty') or ''}</certainty>\n"
                        f"      <reformulation>{intent_pack.get('reformulation') or ''}</reformulation>\n"
                        f"      <user_question topic=\"{intent_pack.get('user_question_topic') or ''}\">{intent_pack.get('user_question_text') or ''}</user_question>\n"
                        "    </intention_client>"
                    )
                    instruction_block = (
                        "    <triggered>false</triggered>\n"
                        f"{intention_xml}"
                    )

                short_instr = instruction_block.replace("\n", " ")
                if len(short_instr) > 220:
                    short_instr = short_instr[:220] + "..."
                print(f"🧭 [INSTRUCTION] triggered={'OUI' if triggered else 'NON'} | next_field={next_field or 'NONE'} | {short_instr}")
            except Exception as e:
                instruction_block = "    <triggered>false</triggered>"
                print(f"⚠️ [INSTRUCTION] error: {type(e).__name__}: {e}")
            
            # 3. Construction prompt complet
            print("🔨 [PROMPT] Construction prompt...")

            # Ajouter un bloc vision compact au contexte (pour forcer l'action LLM sur des données validées)
            try:
                verdict_lines = []
                if payment_verdict_line:
                    verdict_lines.append(payment_verdict_line)
                if phone_verdict_line:
                    verdict_lines.append(phone_verdict_line)
                if location_verdict_line:
                    verdict_lines.append(location_verdict_line)
                if 'quantite_verdict_line' in locals() and quantite_verdict_line:
                    verdict_lines.append(quantite_verdict_line)
                if vision_summary:
                    verdict_lines.append(vision_summary)

                if verdict_lines:
                    prev_pc = str(dynamic_context.get('product_context', '') or '')
                    inject = "\n".join([v for v in verdict_lines if v])
                    dynamic_context['product_context'] = (prev_pc + "\n" + inject).strip() if prev_pc else inject
            except Exception:
                pass
            
            price_calculation_block = ""
            try:
                st_for_price = order_tracker.get_state(user_id)
                produit_val = str(getattr(st_for_price, "produit", "") or "").strip()
                specs_val = str(getattr(st_for_price, "produit_details", "") or "").strip()
                quantite_val = str(getattr(st_for_price, "quantite", "") or "").strip()
                zone_val = str(dynamic_context.get("detected_location") or getattr(st_for_price, "zone", "") or "").strip()

                # Option A (cart-first): si on a déjà un panier (detected_items) confirmé, on calcule le prix
                # sur ce panier plutôt que sur les slots mono-produit (qui peuvent être obsolètes).
                try:
                    detected_items_pre = order_tracker.get_custom_meta(user_id, "detected_items", default=[])
                except Exception:
                    detected_items_pre = []

                def _extract_quantity_value(text: str) -> str:
                    try:
                        m = re.search(
                            r"\b(\d+)\s*(cartons?|carton|paquets?|packs?|unit[ée]s?)\b",
                            str(text or ""),
                            flags=re.IGNORECASE,
                        )
                        if not m:
                            return ""
                        n = m.group(1)
                        u = m.group(2)
                        return f"{n} {u}".strip()
                    except Exception:
                        return ""

                def _parse_fee(v) -> Optional[int]:
                    if v is None:
                        return None
                    if isinstance(v, (int, float)):
                        return int(v)
                    s = str(v)
                    m = re.search(r"(\d+)", s)
                    return int(m.group(1)) if m else None

                delivery_fee_fcfa = _parse_fee(dynamic_context.get("shipping_fee"))

                def _validate_cart_items(items) -> bool:
                    if not isinstance(items, list) or not items:
                        return False

                    try:
                        catalog_v2 = get_company_catalog_v2(company_id)
                    except Exception:
                        catalog_v2 = None

                    if not isinstance(catalog_v2, dict):
                        return False
                    if str(catalog_v2.get("pricing_strategy") or "").upper() != "UNIT_AS_ATOMIC":
                        return False

                    vtree = catalog_v2.get("v")
                    if not isinstance(vtree, dict) or not vtree:
                        return False

                    canonical_units = catalog_v2.get("canonical_units")
                    if not isinstance(canonical_units, list):
                        canonical_units = []
                    canonical_units = [str(u).strip() for u in canonical_units if str(u).strip()]
                    if not canonical_units:
                        return False

                    def _match_key_case_insensitive(keys: List[str], target: str) -> Optional[str]:
                        t = str(target or "").strip().lower()
                        if not t:
                            return None
                        for k in keys:
                            if str(k or "").strip().lower() == t:
                                return str(k)
                        return None

                    def _find_variant_key(product_raw: str) -> Optional[str]:
                        product_s = str(product_raw or "").strip()
                        if not product_s:
                            return None
                        keys = [str(k) for k in vtree.keys()]
                        exact = _match_key_case_insensitive(keys, product_s)
                        if exact:
                            return exact
                        p_low = product_s.lower()
                        for k in keys:
                            k_low = str(k or "").lower()
                            if p_low and (p_low in k_low or k_low in p_low):
                                return str(k)
                        return None

                    def _extract_t_number(specs_raw: str) -> Optional[int]:
                        s = str(specs_raw or "").strip().upper()
                        m = re.search(r"\bT\s*([1-9]\d*)\b", s)
                        if m:
                            try:
                                return int(m.group(1))
                            except Exception:
                                return None
                        m2 = re.search(r"\bTAILLE\s*([1-9]\d*)\b", s)
                        if m2:
                            try:
                                return int(m2.group(1))
                            except Exception:
                                return None
                        return None

                    def _spec_key_matches(sub_key: str, requested_specs: str) -> bool:
                        if not sub_key:
                            return False
                        keys = [str(sub_key)]
                        exact = _match_key_case_insensitive(keys, requested_specs)
                        if exact:
                            return True

                        req_n = _extract_t_number(requested_specs)
                        if req_n is None:
                            return False

                        # Range support: parse all T numbers in the key and see if req_n fits in min..max
                        nums = [int(x) for x in re.findall(r"T\s*([1-9]\d*)", str(sub_key).upper()) if x.isdigit()]
                        if not nums:
                            return False
                        lo, hi = min(nums), max(nums)
                        return lo <= req_n <= hi

                    def _find_subvariant_key(node_s: Dict[str, Any], specs_raw: str) -> Optional[str]:
                        if not isinstance(node_s, dict):
                            return None
                        specs_s = str(specs_raw or "").strip()
                        if not specs_s:
                            return None
                        sub_keys = [str(k) for k in node_s.keys()]
                        exact = _match_key_case_insensitive(sub_keys, specs_s)
                        if exact:
                            return exact
                        for k in sub_keys:
                            if _spec_key_matches(k, specs_s):
                                return str(k)
                        # Soft match last
                        s_low = specs_s.lower()
                        for k in sub_keys:
                            k_low = str(k or "").lower()
                            if s_low and (s_low in k_low or k_low in s_low):
                                return str(k)
                        return None

                    for it in items:
                        if not isinstance(it, dict):
                            return False
                        product_raw = str(it.get("product") or "").strip()
                        specs_raw = str(it.get("specs") or "").strip()
                        unit = str(it.get("unit") or "").strip()
                        qty = it.get("qty")
                        conf = it.get("confidence")
                        try:
                            conf_f = float(conf) if conf is not None else 0.0
                        except Exception:
                            conf_f = 0.0

                        if unit not in canonical_units:
                            return False

                        variant_key = _find_variant_key(product_raw)
                        node = vtree.get(variant_key) if variant_key else None
                        if not isinstance(node, dict):
                            return False

                        # If the catalog defines sub-variants (node.s), specs must match one of its keys (including ranges)
                        node_s = node.get("s")
                        if isinstance(node_s, dict) and node_s:
                            sub_key = _find_subvariant_key(node_s, specs_raw)
                            if not sub_key:
                                return False
                            sub_node = node_s.get(sub_key)
                            if not isinstance(sub_node, dict):
                                return False
                            u_map = sub_node.get("u")
                            if not isinstance(u_map, dict) or unit not in u_map:
                                return False
                        else:
                            u_map = node.get("u")
                            if not isinstance(u_map, dict) or unit not in u_map:
                                return False

                        if qty is None or (not isinstance(qty, int)) or qty <= 0:
                            return False
                        if conf_f < float(CONFIDENCE_THRESHOLD):
                            return False
                    return True

                if _validate_cart_items(detected_items_pre) and zone_val:
                    pc_inner_cart = UniversalPriceCalculator.build_price_calculation_block_from_detected_items(
                        company_id=company_id,
                        items=detected_items_pre,
                        zone=zone_val,
                        delivery_fee_fcfa=delivery_fee_fcfa,
                    )
                    if str(pc_inner_cart or "").strip():
                        price_calculation_block = str(pc_inner_cart)
                        print(f"✅ [PRICE_CART_FIRST] pre_llm injected | items={len(detected_items_pre)} | zone='{zone_val}'")
                        raise StopIteration("skip_mono_price_calc_due_to_cart")

                # Fallback quantité/specs AVANT le LLM:
                # OrderStateTracker est alimenté principalement APRÈS parsing du <thinking>,
                # donc au 1er tour la quantité peut être vide alors qu'elle est présente dans le message.
                if not quantite_val:
                    quantite_val = _extract_quantity_value(query)
                if not specs_val:
                    # Si le client écrit "taille 4" ou "T4" on le garde en specs (utile pour pressions).
                    m_sz = re.search(r"\b(?:taille\s*|t)([1-7])\b", str(query or ""), flags=re.IGNORECASE)
                    if m_sz:
                        specs_val = f"taille {m_sz.group(1)}"

                # Fallback product detection (scalable, non spécifique entreprise):
                # uniquement pour calculer le prix quand le LLM n'a pas rempli PRODUIT.
                msg_l = str(query or "").lower()
                # Si le client indique explicitement un changement ("finalement", "à la place"...),
                # on autorise le switch produit même si un ancien produit est déjà en mémoire.
                change_markers = ["finalement", "a la place", "à la place", "plutot", "plutôt", "change", "remplace"]
                is_switch = any(m in msg_l for m in change_markers)
                if (not produit_val) or is_switch:
                    if "culott" in msg_l:
                        produit_val = "culottes"
                    elif "pression" in msg_l or "press" in msg_l:
                        produit_val = "pressions"

                # Pré-remplissage tracker AVANT LLM (évite missing=QUANTITÉ alors que présent dans le message)
                try:
                    st_pre = order_tracker.get_state(user_id)
                    # Si le message courant apporte une nouvelle valeur, on autorise la mise à jour même si
                    # une ancienne valeur existe (cas: "finalement", correction, changement de produit).
                    if produit_val and str(getattr(st_pre, "produit", "") or "").strip() != produit_val:
                        order_tracker.update_produit(user_id, produit_val, source="CONTEXT_INFERRED", confidence=0.8)

                        # Pivot produit: on tue immédiatement les attributs du produit précédent.
                        # Sinon le pré-calcul envoie une chimère (ex: produit=pressions + specs=T4 + quantite=3 paquet).
                        try:
                            specs_val = ""
                            quantite_val = ""
                            order_tracker.update_produit_details(user_id, "", source="CONTEXT_INFERRED", confidence=0.6)
                            order_tracker.update_quantite(user_id, "", source="CONTEXT_INFERRED", confidence=0.6)
                            print("🧹 [ORDER_STATE] SPECS+QUANTITÉ cleared (pre_llm_pivot)")
                        except Exception:
                            pass

                    if specs_val and str(getattr(st_pre, "produit_details", "") or "").strip() != specs_val:
                        order_tracker.update_produit_details(user_id, specs_val, source="CONTEXT_INFERRED", confidence=0.8)

                    # Quantité: si détectée dans le message, elle doit remplacer l'ancienne (sinon on recycle une
                    # quantité obsolète sur un nouveau produit et le price_calc part sur INVALID_QUANTITY).
                    if quantite_val and str(getattr(st_pre, "quantite", "") or "").strip() != quantite_val:
                        order_tracker.update_quantite(user_id, quantite_val, source="CONTEXT_INFERRED", confidence=0.8)

                    # Si on switch produit et que le message parle de lots/plusieurs tailles,
                    # la quantité globale précédente ne doit jamais rester (elle devient incohérente).
                    try:
                        if is_switch and (" lot" in msg_l or " lots" in msg_l) and str(getattr(st_pre, "quantite", "") or "").strip():
                            order_tracker.update_quantite(user_id, "", source="CONTEXT_INFERRED", confidence=0.6)
                            quantite_val = ""
                            print("🧹 [ORDER_STATE] QUANTITÉ cleared (pre_llm_switch)")
                    except Exception:
                        pass
                except Exception:
                    pass

                # Si le message ressemble à un panier multi-items (lots + plusieurs tailles),
                # ne pas faire de pré-calcul: on attend detected_items_json du LLM.
                pre_llm_price_calc_allowed = True
                try:
                    if is_switch and (" lot" in msg_l or " lots" in msg_l):
                        pre_llm_price_calc_allowed = False
                        specs_val = ""
                        quantite_val = ""
                except Exception:
                    pass

                try:
                    print(
                        "🧾 [PRICE_CALC][INPUTS] "
                        + f"produit='{produit_val}' specs='{specs_val}' quantite='{quantite_val}' "
                        + f"zone='{zone_val}' shipping_fee='{dynamic_context.get('shipping_fee')}'"
                    )
                except Exception:
                    pass

                # Injection prix: ne dépend pas d'un company_id hardcodé.
                # Si produit+quantité sont détectés, on calcule avec les règles du catalogue/tiers actif.
                if pre_llm_price_calc_allowed:
                    price_calculation_block = UniversalPriceCalculator.build_price_calculation_block_for_rue_du_grossiste(
                        company_id=company_id,
                        produit=produit_val,
                        specs=specs_val,
                        quantite=quantite_val,
                        zone=zone_val,
                        delivery_fee_fcfa=delivery_fee_fcfa,
                    )
                else:
                    price_calculation_block = ""

                # Persister le pricing mono-produit dès qu'il est calculé, même si le LLM rend un <response> valide.
                # Sinon, PRICE_GUARD / post-processing peuvent croire (à tort) qu'aucun prix n'est validé.
                try:
                    pc_inner = str(price_calculation_block or "").strip()
                    if pc_inner:
                        order_tracker.set_custom_meta(
                            user_id,
                            "price_calculation_block",
                            "<price_calculation>\n" + pc_inner + "\n</price_calculation>",
                        )
                except Exception:
                    pass

                try:
                    if str(price_calculation_block or "").strip():
                        short_pc = str(price_calculation_block).replace("\n", " ")
                        if len(short_pc) > 300:
                            short_pc = short_pc[:300] + "..."
                        print(f"🧮 [PRICE_CALC] computed | produit='{produit_val}' specs='{specs_val}' quantite='{quantite_val}' fee='{delivery_fee_fcfa}' | {short_pc}")
                    else:
                        print(f"🧮 [PRICE_CALC] EMPTY | produit='{produit_val}' specs='{specs_val}' quantite='{quantite_val}' zone='{zone_val}' fee='{delivery_fee_fcfa}'")
                except Exception:
                    pass
            except Exception as _pc_e:
                print(f"⚠️ [PRICE_CALC] error: {type(_pc_e).__name__}: {_pc_e}")

            try:
                pc_meta_now = str(order_tracker.get_custom_meta(user_id, "price_calculation_block", default="") or "").strip()
                snap_now = _snapshot_from_price_block(pc_meta_now)
                if snap_now:
                    order_tracker.set_custom_meta(user_id, "last_total_snapshot", snap_now)
            except Exception:
                pass

            try:
                snap = order_tracker.get_custom_meta(user_id, "last_total_snapshot", default=None)
            except Exception:
                snap = None
            if isinstance(snap, dict) and (snap.get("total") is not None):
                try:
                    prev_pr = str(dynamic_context.get('pricing_context', '') or '')
                except Exception:
                    prev_pr = ""
                try:
                    snap_txt = json.dumps(snap, ensure_ascii=False)
                except Exception:
                    snap_txt = "{}"
                inject = f"LAST_TOTAL_SNAPSHOT_JSON: {snap_txt}"
                dynamic_context['pricing_context'] = (prev_pr + "\n" + inject).strip() if prev_pr else inject

            final_prompt = await self.prompt_system.build_prompt(
                query=query,
                user_id=user_id,
                company_id=company_id,
                detected_location=dynamic_context.get('detected_location'),
                shipping_fee=dynamic_context.get('shipping_fee'),
                delivery_time=dynamic_context.get('delivery_time'),
                product_context=dynamic_context.get('product_context', ''),
                pricing_context=dynamic_context.get('pricing_context', ''),
                conversation_history=str(dynamic_context.get('conversation_history') or ''),
                instruction_block=instruction_block,
                validation_errors_block=validation_errors_block,
                price_calculation_block=price_calculation_block,
                catalogue_reference_block=(
                    "\n".join(
                        [
                            ln
                            for ln in str(dynamic_context.get('product_context', '') or '').splitlines()
                            if ln.strip()
                            and (not str(ln).upper().startswith('PAYMENT_VERDICT'))
                            and (not str(ln).upper().startswith('PHONE_VERDICT'))
                            and (not str(ln).upper().startswith('LOCATION_VERDICT'))
                            and (not str(ln).upper().startswith('VISION_GEMINI'))
                        ]
                    ).strip()
                ),
                has_image=bool(images and len(images) > 0),
            )
            
            print(f"✅ [PROMPT] Prompt construit: {len(final_prompt)} chars")
            
            # Affichage prompt pour debug
            print(f"\n{'='*80}")
            print(f"🧠 PROMPT COMPLET ENVOYÉ AU LLM")
            print(f"{'='*80}")
            print(final_prompt[:1000] + "..." if len(final_prompt) > 1000 else final_prompt)
            print(f"{'='*80}\n")
            
            # 4. Génération LLM avec tracking tokens
            print("🤖 [LLM] Génération réponse...")

            # Choix modèle: fallback sur env (OpenRouter) si rien n'est piloté par ailleurs.
            model_name = (
                os.getenv("SIMPLIFIED_RAG_MODEL")
                or os.getenv("LLM_MODEL")
                or "google/gemini-2.5-flash-lite"
            ).strip()

            max_tokens_cfg = int(os.getenv("SIMPLIFIED_RAG_MAX_TOKENS", "900"))
            print(f"🧪 [LLM_CONFIG] model='{model_name}' | max_tokens={max_tokens_cfg}")
            
            llm_result = await self.llm_client.complete(
                prompt=final_prompt,
                model_name=model_name,
                temperature=0.2,
                top_p=0.7,
                # 320-420 peut couper la fermeture </response> quand le <thinking> est long.
                # Rendre configurable (env) + augmenter le défaut pour éviter "<response> tag not found".
                max_tokens=max_tokens_cfg,
                frequency_penalty=0.0,
            )
            
            # 5. Extraction métriques tokens
            token_usage = {}
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0
            total_cost = 0.0
            model_used = "unknown"
            
            if isinstance(llm_result, dict):
                response = llm_result.get("response", llm_result)
                token_usage = llm_result.get("usage", {}) or {}
                model_used = llm_result.get("model", "unknown")
                
                try:
                    if isinstance(token_usage, dict):
                        prompt_tokens = int(token_usage.get("prompt_tokens") or 0)
                        completion_tokens = int(token_usage.get("completion_tokens") or 0)
                        total_tokens = int(token_usage.get("total_tokens") or (prompt_tokens + completion_tokens) or 0)
                        total_cost = float(
                            token_usage.get("total_cost")
                            if token_usage.get("total_cost") is not None
                            else (token_usage.get("cost") or 0.0)
                        )
                except Exception as e:
                    print(f"⚠️ [TOKENS] Erreur extraction: {e}")
                    prompt_tokens = 0
                    completion_tokens = 0
                    total_tokens = 0
                    total_cost = 0.0
            else:
                response = llm_result

            # Garder la sortie brute du LLM (avant extraction <thinking>/<response>) pour diagnostics/failsafes.
            raw_llm_output = str(response or "")
            
            print(f"✅ [LLM] Réponse générée: {len(str(response))} chars")
            print(
                f"{C_GREEN}💰 [TOKENS] Prompt: {prompt_tokens} | Completion: {completion_tokens} | Total: {total_tokens} | Cost: ${total_cost:.6f} | Model: {model_used}{C_RESET}"
            )
            
            # 6. Extraction thinking + response
            thinking = ""
            thinking_parsed: Dict[str, Any] = {}

            def _norm_text(s: str) -> str:
                try:
                    import unicodedata

                    t = str(s or "")
                    t = unicodedata.normalize("NFKD", t)
                    t = "".join(ch for ch in t if not unicodedata.combining(ch))
                    t = t.lower()
                    t = re.sub(r"[^a-z0-9\s]", " ", t)
                    t = re.sub(r"\s+", " ", t).strip()
                    return t
                except Exception:
                    return str(s or "").lower().strip()

            def _is_value_mentioned(message: str, value: str) -> bool:
                """Vérification conservative: n'accepte que si la valeur est réellement mentionnée.

                But: empêcher que le LLM invente PRODUIT/SPECS/QUANTITÉ dans <thinking>.
                """
                mv = _norm_text(value)
                mm = _norm_text(message)
                if not mv or mv in {"∅", "o", "ok", "oui", "non", "na", "n a"}:
                    return False
                if not mm:
                    return False

                # Quantités: exiger présence du chiffre dans le message.
                d = re.findall(r"\b\d+\b", mv)
                if d:
                    return any(re.search(rf"\b{re.escape(x)}\b", mm) for x in d)

                # Sinon: match tokens significatifs (>=3 chars), au moins 1 token présent.
                tokens = [t for t in mv.split() if len(t) >= 3]
                if not tokens:
                    return mv in mm
                return any(re.search(rf"\b{re.escape(t)}\b", mm) for t in tokens)

            def _extract_tag(text: str, tag: str) -> str:
                m = re.search(rf'<{tag}>(.*?)</{tag}>', text or "", re.DOTALL | re.IGNORECASE)
                return m.group(1).strip() if m else ""

            def _parse_thinking_schema(thinking_text: str) -> Dict[str, Any]:
                t = thinking_text or ""

                def pick(pattern: str) -> str:
                    m = re.search(pattern, t, re.IGNORECASE)
                    return m.group(1).strip() if m else ""

                def pick_tag(tag: str) -> str:
                    m = re.search(rf"<{tag}>\s*(?:\[([^\]]+)\]|(.*?))\s*</{tag}>", t, re.IGNORECASE | re.DOTALL)
                    if not m:
                        return ""
                    return (m.group(1) or m.group(2) or "").strip()

                def pick_field(label: str) -> str:
                    m = re.search(rf"-\s*{label}:\s*(?:\[([^\]]+)\]|(.+))", t, re.IGNORECASE)
                    if not m:
                        return ""
                    return (m.group(1) or m.group(2) or "").strip()

                intent = pick_tag("intent")
                priority = pick_tag("priority")
                next_step = pick(r"<next>\s*(.*?)\s*</next>")

                produit = pick_field("PRODUIT")
                specs = pick_field("SPECS")
                quantite = pick_field("QUANTIT[ÉE]")
                prix_cite = pick_field("PRIX_CIT[ÉE]")

                zone = pick_field("ZONE")
                telephone = pick_field("T[ÉE]L[ÉE]PHONE")
                paiement = pick_field("PAIEMENT")

                # Fallback: format compact (ex: 'Le produit est "culottes" et la quantité "3 paquets".')
                # Ce format est fréquent avec certains prompts; on extrait de façon conservative.
                if not produit:
                    m_prod = re.search(r"\bproduit\s+est\s+\"([^\"]+)\"", t, re.IGNORECASE)
                    if m_prod:
                        produit = (m_prod.group(1) or "").strip()
                if not quantite:
                    m_qty = re.search(r"\bquantit[ée]\s+\"([^\"]+)\"", t, re.IGNORECASE)
                    if m_qty:
                        quantite = (m_qty.group(1) or "").strip()
                if not zone:
                    m_zone = re.search(r"\bzone\s+\"([^\"]+)\"", t, re.IGNORECASE)
                    if m_zone:
                        zone = (m_zone.group(1) or "").strip()

                urgence = pick_tag("signal_urgence")

                def clean(v: str) -> str:
                    vv = str(v or "").strip()
                    if vv in {"∅", "Ø", "N/A", "NA", "none", "null", ""}:
                        return ""
                    return vv

                return {
                    "intent": clean(intent),
                    "priority": clean(priority),
                    "next": clean(next_step),
                    "signal_urgence": clean(urgence),
                    "detection": {
                        "produit": clean(produit),
                        "specs": clean(specs),
                        "quantite": clean(quantite),
                        "prix_cite": clean(prix_cite),
                        "zone": clean(zone),
                        "telephone": clean(telephone),
                        "paiement": clean(paiement),
                    },
                }

            # Extraire <thinking>
            thinking_match = re.search(r'<thinking>(.*?)</thinking>', raw_llm_output, re.DOTALL | re.IGNORECASE)
            if thinking_match:
                thinking = thinking_match.group(1).strip()
                thinking_parsed = _parse_thinking_schema(thinking)
                print(f"{C_YELLOW}🧠 [THINKING] {len(thinking)} chars{C_RESET}")
                print(f"{C_YELLOW}{'='*80}{C_RESET}")
                print(f"{C_YELLOW}{thinking}{C_RESET}")
                print(f"{C_YELLOW}{'='*80}{C_RESET}")

                def _normalize_packaging_items(items: List[Dict[str, Any]], message: str) -> List[Dict[str, Any]]:
                    """Normalise des formulations type "lot/pack/carton/colis de N".

                    Objectif: éviter les erreurs qty/unit quand le client exprime un conditionnement.
                    Ex: "LOT de 6 paquets" => qty=1, unit="lot" (si le LLM a renvoyé qty=6, unit="paquet").

                    Règle générique (scalable): uniquement basée sur le texte utilisateur.
                    """
                    try:
                        msg = str(message or "")
                        msg_l = msg.lower()

                        m = re.search(r"\b(lot|pack|carton|colis)\s*(?:de\s*)?(\d+)\b", msg_l)
                        if not m:
                            return items

                        pack_unit = str(m.group(1) or "").strip().lower()
                        pack_n = int(m.group(2))

                        normalized: List[Dict[str, Any]] = []
                        for it in items:
                            if not isinstance(it, dict):
                                continue
                            qty = it.get("qty")
                            unit = str(it.get("unit") or "").strip().lower()

                            if isinstance(qty, int) and qty == pack_n and unit in {"paquet", "paquets", "pack", "packs"}:
                                it2 = dict(it)
                                it2["qty"] = 1
                                it2["unit"] = pack_unit
                                normalized.append(it2)
                            else:
                                normalized.append(it)

                        return normalized
                    except Exception:
                        return items

                # Extraire <detected_items_json> (JSON strict) et persister pour validation/pricing
                try:
                    detected_items_json_text = _extract_tag(thinking, "detected_items_json")
                    if detected_items_json_text:
                        try:
                            txt = str(detected_items_json_text or "").strip()
                            parsed_items = json.loads(txt)
                            if isinstance(parsed_items, list):
                                parsed_items = _normalize_packaging_items(parsed_items, query)
                                order_tracker.set_custom_meta(user_id, "detected_items", parsed_items)
                                order_tracker.set_custom_meta(user_id, "detected_items_raw", detected_items_json_text)
                                order_tracker.set_custom_meta(user_id, "detected_items_parse_error", "")
                                print(f"✅ [ITEMS_JSON] parsed_items={len(parsed_items)}")

                                # Source de vérité: dériver un résumé de slots depuis items.
                                # Mono item => remplir PRODUIT/SPECS/QUANTITÉ.
                                # Multi items => remplir PRODUIT/SPECS (résumé) et vider QUANTITÉ globale.
                                try:
                                    items_summary: Dict[str, Any] = {
                                        "has_items": False,
                                        "count": 0,
                                        "produit": "",
                                        "specs": "",
                                        "quantite": "",
                                        "is_multi": False,
                                    }

                                    clean_items = [it for it in parsed_items if isinstance(it, dict)]
                                    items_summary["has_items"] = bool(clean_items)
                                    items_summary["count"] = len(clean_items)
                                    items_summary["is_multi"] = len(clean_items) > 1

                                    def _norm(s: Any) -> str:
                                        return str(s or "").strip()

                                    if len(clean_items) == 1:
                                        it0 = clean_items[0]
                                        items_summary["produit"] = _norm(it0.get("product")).lower()
                                        items_summary["specs"] = _norm(it0.get("specs")).upper()
                                        q = it0.get("qty")
                                        u = _norm(it0.get("unit")).lower()
                                        if isinstance(q, int) and q > 0 and u:
                                            items_summary["quantite"] = f"{q} {u}".strip()
                                    elif len(clean_items) > 1:
                                        prods = []
                                        specs_list = []
                                        for it in clean_items:
                                            p = _norm(it.get("product")).lower()
                                            s = _norm(it.get("specs")).upper()
                                            if p:
                                                prods.append(p)
                                            if s:
                                                specs_list.append(s)

                                        uniq_prods = sorted(list({p for p in prods if p}))
                                        items_summary["produit"] = " + ".join(uniq_prods)
                                        items_summary["specs"] = ", ".join([s for s in specs_list if s])
                                        items_summary["quantite"] = ""  # multi-items => quantité globale vide

                                    order_tracker.set_custom_meta(user_id, "items_slot_summary", items_summary)
                                except Exception as _sum_e:
                                    order_tracker.set_custom_meta(user_id, "items_slot_summary", {})
                                    print(f"⚠️ [ITEMS_JSON] summary error: {type(_sum_e).__name__}: {_sum_e}")
                            else:
                                order_tracker.set_custom_meta(user_id, "detected_items", [])
                                order_tracker.set_custom_meta(user_id, "detected_items_raw", detected_items_json_text)
                                order_tracker.set_custom_meta(user_id, "detected_items_parse_error", "not_a_list")
                                print(f"⚠️ [ITEMS_JSON] not a list")
                        except Exception as e:
                            # Tolérance: certains modèles mettent des commentaires/texte dans le tag.
                            # On tente d'extraire le premier tableau JSON [...] avant de fallback.
                            try:
                                txt2 = str(detected_items_json_text or "")
                                start = txt2.find("[")
                                end = txt2.rfind("]")
                                if start != -1 and end != -1 and end > start:
                                    cand = txt2[start : end + 1]
                                    parsed_items = json.loads(cand)
                                    if isinstance(parsed_items, list):
                                        parsed_items = _normalize_packaging_items(parsed_items, query)
                                        order_tracker.set_custom_meta(user_id, "detected_items", parsed_items)
                                        order_tracker.set_custom_meta(user_id, "detected_items_raw", cand)
                                        order_tracker.set_custom_meta(user_id, "detected_items_parse_error", "")
                                        print(f"✅ [ITEMS_JSON] parsed_items={len(parsed_items)}")
                                    else:
                                        order_tracker.set_custom_meta(user_id, "detected_items", [])
                                        order_tracker.set_custom_meta(user_id, "detected_items_raw", "")
                                        order_tracker.set_custom_meta(user_id, "detected_items_parse_error", "not_a_list")
                                else:
                                    order_tracker.set_custom_meta(user_id, "detected_items", [])
                                    order_tracker.set_custom_meta(user_id, "detected_items_raw", "")
                                    order_tracker.set_custom_meta(user_id, "detected_items_parse_error", "")
                            except Exception:
                                order_tracker.set_custom_meta(user_id, "detected_items", [])
                                order_tracker.set_custom_meta(user_id, "detected_items_raw", "")
                                order_tracker.set_custom_meta(user_id, "detected_items_parse_error", "")
                    else:
                        order_tracker.set_custom_meta(user_id, "detected_items_raw", "")
                except Exception as e:
                    print(f"⚠️ [ITEMS_JSON] extraction error: {type(e).__name__}: {e}")

                # Mise à jour OrderStateTracker depuis le thinking avec fusion intelligente
                try:
                    det = thinking_parsed.get("detection") if isinstance(thinking_parsed, dict) else {}
                    if isinstance(det, dict):
                        # Récupérer l'état actuel pour fusion intelligente
                        current_state = order_tracker.get_state(user_id)

                        # Si le LLM a détecté plusieurs items (multi-produits/tailles),
                        # la quantité globale ne doit pas rester (sinon carryover: "3 paquets").
                        try:
                            di = order_tracker.get_custom_meta(user_id, "detected_items", default=[])
                            if isinstance(di, list) and len(di) > 1:
                                if str(getattr(current_state, "quantite", "") or "").strip():
                                    order_tracker.update_quantite(user_id, "", source="LLM_INFERRED", confidence=0.6)
                                    print("🧹 [ORDER_STATE] QUANTITÉ cleared (multi_items)")
                        except Exception:
                            pass
                        
                        # Hiérarchie stricte:
                        # - Si detected_items_json est présent => SOURCE DE VÉRITÉ pour PRODUIT/SPECS/QUANTITÉ.
                        # - <detection> ne sert qu'au reste (ZONE/TÉLÉPHONE/PAIEMENT) et au résumé humain.
                        try:
                            items_summary = order_tracker.get_custom_meta(user_id, "items_slot_summary", default={})
                        except Exception:
                            items_summary = {}

                        use_items_as_truth = bool(isinstance(items_summary, dict) and items_summary.get("has_items"))

                        produit = str(items_summary.get("produit") or "").strip() if use_items_as_truth else str(det.get("produit") or "").strip()
                        specs = str(items_summary.get("specs") or "").strip() if use_items_as_truth else str(det.get("specs") or "").strip()
                        quantite = str(items_summary.get("quantite") or "").strip() if use_items_as_truth else str(det.get("quantite") or "").strip()
                        prix_cite = str(det.get("prix_cite") or "").strip()

                        zone = str(det.get("zone") or "").strip()
                        telephone = str(det.get("telephone") or "").strip()
                        paiement = str(det.get("paiement") or "").strip()

                        def _normalize_ci_phone(raw: str) -> str:
                            try:
                                s = str(raw or "").strip()
                                if not s or s in {"∅", "Ø", "N/A"}:
                                    return ""
                                digits = re.sub(r"\D+", "", s)
                                if not digits:
                                    return ""

                                # Cas +225XXXXXXXXXX (13 digits)
                                if digits.startswith("225") and len(digits) == 13:
                                    digits = digits[3:]  # -> 10 digits (ex: 0160824536)

                                # Accepter uniquement le format local 0XXXXXXXXX
                                if re.fullmatch(r"0\d{9}", digits):
                                    return digits
                                return ""
                            except Exception:
                                return ""
                        
                        # PRODUIT: si items JSON => on trust (pas besoin de preuve substring).
                        if produit and produit != "∅":
                            if use_items_as_truth:
                                order_tracker.update_produit(user_id, produit, source="ITEMS_JSON", confidence=0.9)
                            else:
                                if _is_value_mentioned(query or "", produit):
                                    order_tracker.update_produit(user_id, produit, source="LLM_INFERRED", confidence=0.6)
                        
                        # QUANTITÉ: persistance directe si LLM détecte une valeur non-vide
                        # Le LLM a déjà validé l'intention dans <thinking>, on fait confiance
                        ql = str(quantite or "").strip().lower()
                        q_is_nullish = (
                            (not ql)
                            or ql in {"∅", "ø", "n/a"}
                            or "null" in ql
                            or "correction" in ql
                            or "invalide" in ql
                        )

                        # Si le LLM indique explicitement une quantité inconnue/null/correction nécessaire,
                        # on efface la quantité persistée pour éviter de recalculer sur une ancienne valeur.
                        if q_is_nullish:
                            try:
                                if str(current_state.quantite or "").strip():
                                    order_tracker.update_quantite(user_id, "", source="LLM_INFERRED", confidence=0.4)
                                    print("🧹 [ORDER_STATE] QUANTITÉ cleared (thinking_nullish)")
                            except Exception:
                                pass

                        if (not q_is_nullish) and quantite and quantite != "∅" and (use_items_as_truth or _is_value_mentioned(query or "", quantite)):
                            # Nettoyer la quantité (enlever parenthèses, commentaires)
                            quantite_clean = re.sub(r"\s*\(.*?\)\s*", "", quantite).strip()
                            if quantite_clean and quantite_clean != str(getattr(current_state, "quantite", "") or "").strip():
                                order_tracker.update_quantite(user_id, quantite_clean, source="LLM_INFERRED", confidence=0.8)
                                print(f"✅ [ORDER_STATE] QUANTITÉ persistée (overwrite): {quantite_clean}")
                        # FUSION: garde l'ancienne quantité si nouvelle = vide
                        
                        # SPECS: nettoyer TOUTE mention de Quantité/Prix
                        if specs and specs != "∅" and (use_items_as_truth or _is_value_mentioned(query or "", specs)):
                            # Supprimer toute mention de "Quantité:" ou "Prix:" dans specs
                            specs_clean = specs
                            # Split par | et ne garder que les parties sans "quantité" ni "prix"
                            parts = [p.strip() for p in specs_clean.split("|")]
                            parts_filtered = []
                            for p in parts:
                                p_low = p.lower()
                                if "quantité" not in p_low and "quantite" not in p_low and "prix" not in p_low:
                                    # Supprimer aussi les commentaires entre parenthèses
                                    p_clean = re.sub(r"\s*\(.*?\)\s*", "", p).strip()
                                    if p_clean:
                                        parts_filtered.append(p_clean)
                            
                            if parts_filtered:
                                specs_final = ", ".join(parts_filtered)
                                # Éviter doublons: ne pas re-sauvegarder si identique
                                if specs_final != current_state.produit_details:
                                    order_tracker.update_produit_details(user_id, specs_final, source="LLM_INFERRED", confidence=0.6)
                        
                        # ZONE: fallback depuis thinking si le tracker ne l'a pas persistée
                        if zone and zone != "∅":
                            zone_clean = re.sub(r"\s*\(.*?\)\s*", "", zone).strip()
                            if zone_clean and not current_state.zone:
                                try:
                                    from core.delivery_zone_extractor import extract_delivery_zone_and_cost, normalize_text

                                    q_norm = normalize_text(str(query or ""))
                                    zone_proof = extract_delivery_zone_and_cost(str(query or ""))
                                    zone_name = str((zone_proof or {}).get("name") or "").strip()
                                    if zone_proof and zone_name:
                                        # Zone reconnue par notre extracteur sur le message utilisateur → preuve suffisante
                                        order_tracker.update_zone(user_id, zone_name, source="CONTEXT_INFERRED", confidence=0.7)
                                        print(f"✅ [ORDER_STATE] ZONE persistée (proof=extractor): {zone_name}")
                                    else:
                                        # Ville/zone non répertoriée: persister uniquement si le texte apparaît dans le message client
                                        zone_norm = normalize_text(zone_clean)
                                        if zone_norm and (zone_norm in q_norm):
                                            order_tracker.update_zone(user_id, zone_clean, source="USER_EXTRACTED", confidence=0.7)
                                            print(f"✅ [ORDER_STATE] ZONE persistée (proof=substring): {zone_clean}")
                                        else:
                                            print(f"⚠️ [ORDER_STATE] ZONE ignorée (no proof in user query): {zone_clean}")
                                except Exception as e:
                                    print(f"⚠️ [ORDER_STATE] ZONE fallback error: {type(e).__name__}: {e}")

                        # TÉLÉPHONE: fallback depuis thinking uniquement si on peut normaliser
                        phone_norm = _normalize_ci_phone(telephone)
                        if phone_norm and not current_state.numero:
                            order_tracker.update_numero(user_id, phone_norm, source="LLM_INFERRED", confidence=0.7)
                            print(f"✅ [ORDER_STATE] NUMÉRO persisté (thinking): {phone_norm}")
                        
                        # PAIEMENT: PROTÉGER les paiements validés (validé_XXXF)
                        # Ne JAMAIS écraser un paiement validé par une valeur générique
                        if current_state.paiement and current_state.paiement.startswith("validé_"):
                            pass  # Paiement déjà validé, ne pas toucher
                        # Sinon, on laisse le système de vision gérer le paiement

                        # Fallback ultra-conservateur: si le thinking fournit déjà un format verdict stable,
                        # on peut le persister uniquement si le tracker est vide.
                        if (not current_state.paiement) and paiement and paiement != "∅":
                            p_low = paiement.lower()
                            if p_low.startswith("validé_") or p_low.startswith("valide_"):
                                order_tracker.update_paiement(user_id, paiement, source="LLM_INFERRED", confidence=0.6)
                            elif p_low.startswith("insuffisant_") or p_low.startswith("refus"):
                                # Utile pour aligner l'état si le verdict a été perdu (sans dire que c'est validé)
                                order_tracker.update_paiement(user_id, paiement, source="LLM_INFERRED", confidence=0.5)
                            
                except Exception as e:
                    print(f"⚠️ [ORDER_STATE] Erreur update depuis thinking: {e}")

            # Afficher l'avancement OrderStateTracker
            try:
                st = order_tracker.get_state(user_id)
                missing = sorted(list(st.get_missing_fields()))
                missing_str = ", ".join(missing) if missing else "Aucun"
                completion = st.get_completion_rate() if hasattr(st, "get_completion_rate") else 0.0
                print(f"{C_YELLOW}📊 [ORDER_STATUS] completion={completion:.2f} | missing={C_RED}{missing_str}{C_YELLOW}{C_RESET}")
                try:
                    collected = st.to_notepad_format() if hasattr(st, "to_notepad_format") else ""
                    if collected:
                        print(f"{C_YELLOW}📌 [ORDER_STATUS] {collected}{C_RESET}")
                except Exception:
                    pass
            except Exception as e:
                print(f"⚠️ [ORDER_STATUS] Erreur lecture state: {e}")

            # Extraire <response>
            response_match = re.search(r'<response>(.*?)</response>', raw_llm_output, re.DOTALL | re.IGNORECASE)
            if response_match:
                response = response_match.group(1).strip()
                print(f"✅ [RESPONSE] Extrait: {len(response)} chars")
                try:
                    _prev = str(response or "").replace("\n", " ").strip()
                    if len(_prev) > 220:
                        _prev = _prev[:220] + "..."
                    print(f"🧪 [RESPONSE_PREVIEW] {_prev}")
                except Exception:
                    pass

                try:
                    detected_items_chk = order_tracker.get_custom_meta(user_id, "detected_items", default=[])
                    qty_nullish = False
                    if isinstance(detected_items_chk, list) and detected_items_chk:
                        try:
                            qty_nullish = any(isinstance(it, dict) and (it.get("qty") is None) for it in detected_items_chk)
                        except Exception:
                            qty_nullish = False
                    if _is_packsize_question(str(query or "")) and qty_nullish:
                        if re.search(r"\b\d+\b", str(response or "")):
                            response = "Le catalogue ne précise pas le nombre de pièces dans 1 lot. Tu parles d’un lot de combien de pièces exactement stp ?"
                except Exception:
                    pass
            else:
                validated_price_single = False
                try:
                    raw_preview = str(raw_llm_output or "")
                    raw_preview_short = raw_preview[:600] + ("..." if len(raw_preview) > 600 else "")
                    print(f"⚠️ [RESPONSE] <response> tag not found. raw(600)=\n{raw_preview_short}")
                except Exception:
                    pass

                # Si on a déjà un prix calculé côté Python (mono-produit), on priorise ready_to_send.
                try:
                    pc_block = str(price_calculation_block or "").strip()
                    if pc_block:
                        ready_single = _extract_tag(pc_block, "ready_to_send")
                        if ready_single:
                            response = str(ready_single).strip()
                            order_tracker.set_custom_meta(user_id, "price_calculation_block", "<price_calculation>\n" + pc_block + "\n</price_calculation>")
                            validated_price_single = True
                except Exception:
                    pass

                # Fallback robuste:
                # - Supprimer le bloc <thinking>...
                # - Supprimer les code fences (```xml / ```)
                # - Si la sortie ne contient que du XML, forcer une question utile
                if not validated_price_single:
                    response = re.sub(r'<thinking>.*?</thinking>', '', str(response or ''), flags=re.DOTALL | re.IGNORECASE).strip()
                    response = re.sub(r"```[a-zA-Z0-9_-]*\s*", "", response).strip()
                    response = response.replace("```", "").strip()

                # Si le modèle a rendu un <response> sans fermeture, récupérer le contenu après la balise.
                # (sinon on risque de renvoyer littéralement "<response>" au client)
                resp_l = str(response or "")
                if re.search(r"<response\b", resp_l, re.IGNORECASE) and not re.search(r"</response>", resp_l, re.IGNORECASE):
                    parts = re.split(r"<response\b[^>]*>", resp_l, flags=re.IGNORECASE)
                    if len(parts) >= 2:
                        response = parts[-1].strip()
                # Nettoyage final: enlever une éventuelle balise fermante qui traîne.
                response = re.sub(r"</response>", "", str(response or ""), flags=re.IGNORECASE).strip()

                # Si on détecte encore des balises XML, c'est que le modèle a fuité le format -> fallback question
                if (not str(response or "").strip()) or str(response or "").strip().lower() in {"<response>", "</response>", "<response/>"} or re.search(r"</?(thinking|q_exact|intention_client|comprehension|detection|intent|priority|next|response)\b", response, re.IGNORECASE):
                    nf = order_tracker.get_next_required_field(user_id, current_turn=current_turn)

                    def _fallback_question(field: Optional[str]) -> str:
                        f = str(field or "").upper().strip()
                        if f == "PRODUIT":
                            return "Pressions ou culottes stp ?"
                        if f == "SPECS":
                            return "Tu veux quelle taille exactement stp ?"
                        if f == "QUANTITÉ":
                            return "Tu en veux combien (carton/paquets) stp ?"
                        if f == "ZONE":
                            return "Tu es dans quelle commune/quartier stp ?"
                        if f in {"NUMÉRO", "NUMERO"}:
                            return "Ton numéro WhatsApp pour le livreur stp ?"
                        if f == "PAIEMENT":
                            return "Tu peux envoyer l’acompte Wave de 2000F et la capture stp ?"
                        return "Tu peux préciser stp ?"

                    response = _fallback_question(nf)
                    print(f"🛡️ [RESPONSE_FALLBACK] xml_leak_detected | next={nf}")

            # 6.0 SAV/HUMAN HANDOFF (RAG): si le LLM sort le token de transmission, on notifie et on stoppe.
            # IMPORTANT: déclenché AVANT toute post-transformation (pricing, guards) pour éviter de polluer le message.
            try:
                token = (LLM_TRANSMISSION_TOKEN or "TRANSMISSIONXXX").strip()
                resp_text = str(response or "")
                raw_text = str(raw_llm_output or "")
                has_token = bool(token) and (token.lower() in resp_text.lower() or token.lower() in raw_text.lower())
                if has_token:
                    from core.human_notification_service import HumanNotificationService

                    # Permettre un message client optionnel avant le token (séparateur §§).
                    # Exemple LLM: "Un instant je te passe le responsable. §§ TRANSMISSIONXXX"
                    cleaned = resp_text
                    if token.lower() in cleaned.lower():
                        parts = re.split(re.escape(token), cleaned, flags=re.IGNORECASE)
                        cleaned = (parts[0] or "").strip()
                    cleaned = cleaned.replace("§§", "").strip()

                    if not cleaned:
                        cleaned = os.getenv(
                            "SIMPLIFIED_RAG_HANDOFF_CUSTOMER_MESSAGE",
                            "Un instant, je te passe le responsable pour régler ça."
                        ).strip()

                    try:
                        order_tracker.set_flag(user_id, "bot_paused", True)
                        order_tracker.set_custom_meta(user_id, "handoff_reason", "SAV")
                        order_tracker.set_custom_meta(user_id, "handoff_trigger", token)
                    except Exception:
                        pass

                    try:
                        st = order_tracker.get_state(user_id)
                        ctx = {
                            "company_name": company_name,
                            "zone": str(getattr(st, "zone", "") or ""),
                            "phone": str(getattr(st, "numero", "") or ""),
                        }
                    except Exception:
                        ctx = {"company_name": company_name}

                    try:
                        notifier = HumanNotificationService()
                        await notifier.notify_vendor(
                            company_id=company_id,
                            user_id=user_id,
                            user_name=user_id,
                            question=query,
                            reason="SAV_TRANSMISSION",
                            context=ctx,
                        )
                        print("🔔 [SAV_HANDOFF] notification sent")
                    except Exception as _hn_e:
                        print(f"⚠️ [SAV_HANDOFF] notify failed: {type(_hn_e).__name__}: {_hn_e}")

                    response = cleaned
            except Exception as _handoff_e:
                print(f"⚠️ [SAV_HANDOFF] error: {type(_handoff_e).__name__}: {_handoff_e}")

            # 6.a Pricing multi-items (post LLM): validation + injection du ready_to_send
            validated_price = False
            try:
                detected_items = order_tracker.get_custom_meta(user_id, "detected_items", default=[])
                detected_items_raw = order_tracker.get_custom_meta(user_id, "detected_items_raw", default="")

                def _has_valid_price_meta() -> bool:
                    try:
                        pc_meta = str(order_tracker.get_custom_meta(user_id, "price_calculation_block", default="") or "").strip()
                        if not pc_meta:
                            return False
                        status = str(_extract_tag(pc_meta, "status") or "").strip().upper()
                        ready = str(_extract_tag(pc_meta, "ready_to_send") or "").strip()
                        return (status == "OK") and bool(ready)
                    except Exception:
                        return False

                def _is_price_request(msg: str) -> bool:
                    m = str(msg or "").lower()
                    if _is_packsize_question(m):
                        return False
                    return any(k in m for k in ["prix", "total", "ça fait combien", "ca fait combien", "montant"])

                def _is_packsize_question(m: str) -> bool:
                    t = str(m or "").lower()
                    if any(k in t for k in ["dans un lot", "dans le lot", "dans 1 lot", "dans un paquet", "dans le paquet", "dans 1 paquet"]):
                        return True
                    if any(k in t for k in ["combien de pieces", "combien de pièces", "nombre de pieces", "nombre de pièces", "ça contient combien", "ca contient combien"]):
                        return True
                    if re.search(r"\b(quantité|qte)\s*(par|dans)\s*(lot|paquet)\b", t):
                        return True
                    return False

                def _validate_items(items) -> Dict[str, Any]:
                    out = {
                        "ok": False,
                        "confirmed": [],
                        "unconfirmed": [],
                        "invalid": [],
                        "reasons": [],
                    }
                    if not isinstance(items, list) or not items:
                        out["reasons"].append("no_items")
                        return out

                    try:
                        catalog_v2 = get_company_catalog_v2(company_id)
                    except Exception:
                        catalog_v2 = None

                    if not isinstance(catalog_v2, dict) or str(catalog_v2.get("pricing_strategy") or "").upper() != "UNIT_AS_ATOMIC":
                        out["reasons"].append("catalog_unavailable")
                        return out

                    vtree = catalog_v2.get("v")
                    if not isinstance(vtree, dict) or not vtree:
                        out["reasons"].append("catalog_unavailable")
                        return out

                    canonical_units = catalog_v2.get("canonical_units")
                    if not isinstance(canonical_units, list):
                        canonical_units = []
                    canonical_units = [str(u).strip() for u in canonical_units if str(u).strip()]
                    if not canonical_units:
                        out["reasons"].append("catalog_unavailable")
                        return out

                    def _match_key_case_insensitive(keys: List[str], target: str) -> Optional[str]:
                        t = str(target or "").strip().lower()
                        if not t:
                            return None
                        for k in keys:
                            if str(k or "").strip().lower() == t:
                                return str(k)
                        return None

                    def _find_variant_key(product_raw: str) -> Optional[str]:
                        product_s = str(product_raw or "").strip()
                        if not product_s:
                            return None
                        keys = [str(k) for k in vtree.keys()]
                        exact = _match_key_case_insensitive(keys, product_s)
                        if exact:
                            return exact
                        p_low = product_s.lower()
                        for k in keys:
                            k_low = str(k or "").lower()
                            if p_low and (p_low in k_low or k_low in p_low):
                                return str(k)
                        return None

                    def _extract_t_number(specs_raw: str) -> Optional[int]:
                        s = str(specs_raw or "").strip().upper()
                        m = re.search(r"\bT\s*([1-9]\d*)\b", s)
                        if m:
                            try:
                                return int(m.group(1))
                            except Exception:
                                return None
                        m2 = re.search(r"\bTAILLE\s*([1-9]\d*)\b", s)
                        if m2:
                            try:
                                return int(m2.group(1))
                            except Exception:
                                return None
                        return None

                    def _spec_key_matches(sub_key: str, requested_specs: str) -> bool:
                        if not sub_key:
                            return False
                        keys = [str(sub_key)]
                        exact = _match_key_case_insensitive(keys, requested_specs)
                        if exact:
                            return True

                        req_n = _extract_t_number(requested_specs)
                        if req_n is None:
                            return False

                        nums = [int(x) for x in re.findall(r"T\s*([1-9]\d*)", str(sub_key).upper()) if x.isdigit()]
                        if not nums:
                            return False
                        lo, hi = min(nums), max(nums)
                        return lo <= req_n <= hi

                    def _find_subvariant_key(node_s: Dict[str, Any], specs_raw: str) -> Optional[str]:
                        if not isinstance(node_s, dict):
                            return None
                        specs_s = str(specs_raw or "").strip()
                        if not specs_s:
                            return None
                        sub_keys = [str(k) for k in node_s.keys()]
                        exact = _match_key_case_insensitive(sub_keys, specs_s)
                        if exact:
                            return exact
                        for k in sub_keys:
                            if _spec_key_matches(k, specs_s):
                                return str(k)
                        s_low = specs_s.lower()
                        for k in sub_keys:
                            k_low = str(k or "").lower()
                            if s_low and (s_low in k_low or k_low in s_low):
                                return str(k)
                        return None

                    for it in items:
                        if not isinstance(it, dict):
                            out["invalid"].append({"item": it, "reason": "not_dict"})
                            continue
                        product_raw = str(it.get("product") or "").strip()
                        specs_raw = str(it.get("specs") or "").strip()
                        unit = str(it.get("unit") or "").strip()
                        confidence = it.get("confidence")
                        qty = it.get("qty")

                        if unit not in canonical_units:
                            out["invalid"].append({"item": it, "reason": "bad_unit"})
                            continue

                        variant_key = _find_variant_key(product_raw)
                        node = vtree.get(variant_key) if variant_key else None
                        if not isinstance(node, dict):
                            out["invalid"].append({"item": it, "reason": "bad_product"})
                            continue

                        node_s = node.get("s")
                        if isinstance(node_s, dict) and node_s:
                            sub_key = _find_subvariant_key(node_s, specs_raw)
                            if not sub_key:
                                out["invalid"].append({"item": it, "reason": "bad_specs"})
                                continue
                            sub_node = node_s.get(sub_key)
                            if not isinstance(sub_node, dict):
                                out["invalid"].append({"item": it, "reason": "bad_specs"})
                                continue
                            u_map = sub_node.get("u")
                            if not isinstance(u_map, dict) or unit not in u_map:
                                out["invalid"].append({"item": it, "reason": "bad_unit"})
                                continue
                        else:
                            u_map = node.get("u")
                            if not isinstance(u_map, dict) or unit not in u_map:
                                out["invalid"].append({"item": it, "reason": "bad_unit"})
                                continue

                        try:
                            conf_f = float(confidence) if confidence is not None else 0.0
                        except Exception:
                            conf_f = 0.0

                        if qty is None:
                            out["unconfirmed"].append({"item": it, "reason": "qty_null"})
                            continue
                        if not isinstance(qty, int) or qty <= 0:
                            out["invalid"].append({"item": it, "reason": "qty_invalid"})
                            continue

                        if conf_f < float(CONFIDENCE_THRESHOLD):
                            out["unconfirmed"].append({"item": it, "reason": "low_confidence", "confidence": conf_f})
                            continue

                        out["confirmed"].append(it)

                    if out["invalid"]:
                        out["reasons"].append("invalid_items")
                        return out
                    if out["unconfirmed"]:
                        out["reasons"].append("unconfirmed_items")
                        return out
                    out["ok"] = True
                    return out

                validation = _validate_items(detected_items)
                order_tracker.set_custom_meta(user_id, "detected_items_validation", validation)
                if validation.get("ok"):
                    st_for_zone = order_tracker.get_state(user_id)
                    zone_for_price = str(getattr(st_for_zone, "zone", "") or "").strip() or str(dynamic_context.get("detected_location") or "").strip()

                    def _norm_amt(s: str) -> str:
                        return re.sub(r"\D+", "", str(s or ""))

                    def _parse_fee(v) -> Optional[int]:
                        if v is None:
                            return None
                        if isinstance(v, (int, float)):
                            return int(v)
                        s = str(v)
                        m = re.search(r"(\d+)", s)
                        return int(m.group(1)) if m else None

                    delivery_fee_fcfa = _parse_fee(dynamic_context.get("shipping_fee"))
                    pc_inner = UniversalPriceCalculator.build_price_calculation_block_from_detected_items(
                        company_id=company_id,
                        items=detected_items,
                        zone=zone_for_price,
                        delivery_fee_fcfa=delivery_fee_fcfa,
                    )
                    if str(pc_inner or "").strip():
                        price_block = "<price_calculation>\n" + str(pc_inner).strip() + "\n</price_calculation>"
                        order_tracker.set_custom_meta(user_id, "price_calculation_block", price_block)
                        validated_price = True
                        ready = _extract_tag(price_block, "ready_to_send")
                        if ready:
                            llm_resp = str(response or "").strip()
                            ready_txt = str(ready).strip()

                            # Anti-répétition: ne pas ré-afficher le total à chaque tour.
                            # - On affiche le ready_to_send si: (a) le client demande le prix/total, ou (b) le panier/prix vient de changer.
                            # - Sinon, on laisse le LLM guider sur le prochain slot (numéro/paiement/etc.) sans répéter le montant.
                            try:
                                current_sig = "|".join(
                                    [
                                        _norm_amt(_extract_tag(price_block, "total_fcfa") or ""),
                                        _norm_amt(_extract_tag(price_block, "product_subtotal_fcfa") or ""),
                                        _norm_amt(_extract_tag(price_block, "delivery_fee_fcfa") or ""),
                                        str(zone_for_price or "").strip().lower(),
                                    ]
                                )
                                last_sig = str(
                                    order_tracker.get_custom_meta(user_id, "last_price_signature_shown", default="") or ""
                                ).strip()
                                price_requested_now = bool(_is_price_request(query or ""))
                                allow_show_price = price_requested_now or (not last_sig) or (last_sig != current_sig)
                            except Exception:
                                current_sig = ""
                                allow_show_price = True

                            orientation_marker = "§§"
                            llm_calc_part = llm_resp
                            llm_orientation_part = ""
                            if orientation_marker in llm_resp:
                                parts = llm_resp.split(orientation_marker, 1)
                                llm_calc_part = (parts[0] or "").strip()
                                llm_orientation_part = (parts[1] or "").strip()

                            total_fcfa = str(_extract_tag(price_block, "total_fcfa") or "").strip()
                            subtotal_fcfa = str(_extract_tag(price_block, "product_subtotal_fcfa") or "").strip()
                            delivery_fcfa = str(_extract_tag(price_block, "delivery_fee_fcfa") or "").strip()

                            expected_amounts = {
                                a
                                for a in (
                                    _norm_amt(total_fcfa),
                                    _norm_amt(subtotal_fcfa),
                                    _norm_amt(delivery_fcfa),
                                )
                                if a
                            }

                            money_pattern = re.compile(r"\b\d[\d\s.,]*\s*(?:fcfa|f)\b", re.IGNORECASE)
                            llm_amounts = [_norm_amt(m.group(0)) for m in money_pattern.finditer(llm_calc_part)]
                            llm_amounts = [a for a in llm_amounts if a]

                            if not llm_amounts:
                                tail = llm_orientation_part or llm_resp
                                tail = tail.replace(orientation_marker, "").strip()
                                if allow_show_price:
                                    if tail and tail.lower() != ready_txt.lower():
                                        response = (ready_txt + "\n" + tail).strip()
                                    else:
                                        response = ready_txt
                                    try:
                                        if current_sig:
                                            order_tracker.set_custom_meta(user_id, "last_price_signature_shown", current_sig)
                                    except Exception:
                                        pass
                                else:
                                    # Prix déjà affiché sur ce panier: ne pas le répéter.
                                    response = tail or llm_resp
                            else:
                                mismatch = False
                                if expected_amounts:
                                    for a in llm_amounts:
                                        if a not in expected_amounts:
                                            mismatch = True
                                            break
                                else:
                                    mismatch = True

                                if not mismatch:
                                    # Le LLM a cité des montants cohérents: on accepte uniquement si on veut ré-afficher le prix.
                                    if allow_show_price:
                                        response = llm_resp.replace(orientation_marker, "").strip()
                                        try:
                                            if current_sig:
                                                order_tracker.set_custom_meta(user_id, "last_price_signature_shown", current_sig)
                                        except Exception:
                                            pass
                                    else:
                                        # On garde seulement la partie orientation (question) pour éviter la répétition du total.
                                        response = (llm_orientation_part or "").strip() or llm_resp
                                        response = response.replace(orientation_marker, "").strip()
                                else:
                                    if allow_show_price:
                                        if llm_orientation_part:
                                            response = (ready_txt + "\n" + llm_orientation_part).strip()
                                        else:
                                            response = ready_txt
                                        try:
                                            if current_sig:
                                                order_tracker.set_custom_meta(user_id, "last_price_signature_shown", current_sig)
                                        except Exception:
                                            pass
                                    else:
                                        response = (llm_orientation_part or "").strip() or llm_resp
                                        response = response.replace(orientation_marker, "").strip()
                        print(f"✅ [PRICE_MULTI] injected | items={len(detected_items)} | zone='{zone_for_price}'")
                    else:
                        print(f"⚠️ [PRICE_MULTI] calc returned empty | raw_items_len={len(str(detected_items_raw or ''))}")
                else:
                    print(f"🧾 [PRICE_MULTI] skipped | reasons={validation.get('reasons')}")
                    if _is_price_request(query or ""):
                        order_tracker.set_custom_meta(user_id, "price_requested", True)

                        # Si un pricing mono-produit est déjà calculé et valide, ne JAMAIS remplacer la réponse
                        # par une recap Oui/Non (ça casse le flux et supprime la réponse LLM parfaite).
                        if _has_valid_price_meta():
                            raise StopIteration("skip_clarify_due_to_valid_single_price")

                        # Clarification (1 seule) si le client demande le prix mais que les items sont flous.
                        try:
                            already_clarified = order_tracker.get_flag(user_id, "clarification_attempted")

                            def _build_closed_clarification(v: Dict[str, Any]) -> Optional[str]:
                                unconf = v.get("unconfirmed") if isinstance(v.get("unconfirmed"), list) else []
                                inv = v.get("invalid") if isinstance(v.get("invalid"), list) else []
                                target = None
                                target_reason = None

                                if unconf:
                                    first = unconf[0] if isinstance(unconf[0], dict) else {}
                                    target = first.get("item") if isinstance(first.get("item"), dict) else None
                                    target_reason = str(first.get("reason") or "").strip().lower()
                                elif inv:
                                    first = inv[0] if isinstance(inv[0], dict) else {}
                                    target = first.get("item") if isinstance(first.get("item"), dict) else None
                                    target_reason = str(first.get("reason") or "").strip().lower()

                                if not isinstance(target, dict):
                                    return None

                                prod = str(target.get("product") or "").strip().lower()
                                specs = str(target.get("specs") or "").strip().upper()
                                unit = str(target.get("unit") or "").strip().lower()
                                qty = target.get("qty")

                                # Question fermée (Oui/Non) pour valider le panier détecté.
                                # On évite toute nouvelle extraction ou calcul.
                                if target_reason in {"qty_null", "qty_invalid"}:
                                    if unit == "lot":
                                        return f"Je confirme: c’est {prod} {specs} en 1 lot ? (Oui/Non)"
                                    if unit == "paquet":
                                        return f"Je confirme: c’est {prod} {specs} en 1 paquet ? (Oui/Non)"
                                    return f"Je confirme: c’est {prod} {specs} ? (Oui/Non)"

                                if prod and specs and unit and isinstance(qty, int) and qty > 0:
                                    return f"Je confirme: {qty} {unit}(s) de {prod} {specs} ? (Oui/Non)"

                                if prod and specs:
                                    return f"Je confirme: {prod} {specs} ? (Oui/Non)"

                                if prod:
                                    return f"Je confirme: {prod} ? (Oui/Non)"

                                return None

                            # Si on est au stade 'tout sauf paiement' mais items non confirmés -> on force une recap courte.
                            st_now = order_tracker.get_state(user_id)
                            missing_now = sorted(list(st_now.get_missing_fields()))

                            if (not already_clarified) and (not _is_packsize_question(str(query or ""))) and ("unconfirmed_items" in (validation.get("reasons") or []) or "invalid_items" in (validation.get("reasons") or [])):
                                recap_gate = (missing_now == ["PAIEMENT"]) or (missing_now == ["PAIEMENT"])

                                msg = _build_closed_clarification(validation)
                                if msg:
                                    response = msg
                                    order_tracker.set_flag(user_id, "clarification_attempted", True)
                                    print("❓ [CLARIFY] asked_once_for_items")

                                # Si on est à 1 étape du paiement, on évite de demander paiement tant que panier non confirmé.
                                if recap_gate and not msg:
                                    response = "Je récapitule: tu veux bien les couches notées ci-dessus ? (Oui/Non)"
                                    order_tracker.set_flag(user_id, "clarification_attempted", True)
                                    print("🧾 [RECAP_GATE] basket_confirm_before_payment")
                        except Exception as _cl_e:
                            print(f"⚠️ [CLARIFY] error: {type(_cl_e).__name__}: {_cl_e}")
            except Exception as e:
                if isinstance(e, StopIteration):
                    print(f"❓ [CLARIFY] SKIP: {e}")
                else:
                    print(f"⚠️ [PRICE_MULTI] error: {type(e).__name__}: {e}")

            # Failsafe: si le modèle a rendu un output incomplet (ex: pas de <response> car max_tokens atteint),
            # mais que Python a un ready_to_send valide (mono ou multi), on le renvoie quoi qu'il arrive.
            try:
                resp_missing = bool(re.search(r"<response\b", str(raw_llm_output or ""), re.IGNORECASE)) is False
                if resp_missing:
                    pc_meta = str(order_tracker.get_custom_meta(user_id, "price_calculation_block", default="") or "").strip()
                    if pc_meta:
                        ready_any = _extract_tag(pc_meta, "ready_to_send")
                        if ready_any:
                            response = str(ready_any).strip()
                            print("🛟 [RESPONSE_FAILSAFE] used_ready_to_send")
            except Exception as _rf_e:
                print(f"⚠️ [RESPONSE_FAILSAFE] error: {type(_rf_e).__name__}: {_rf_e}")

            # Anti-hallucination prix: si un montant est présent mais aucun pricing validé, on neutralise.
            try:
                # 6.a Hallucination Guard: enlever les mentions de prix non validées
                has_money = bool(re.search(r"\b\d[\d\s.,]*\s*(?:fcfa|f)\b", str(response or ""), re.IGNORECASE))
                is_price_request_now = _is_price_request(query or "")
                price_is_validated = bool(validated_price or ("validated_price_single" in locals() and validated_price_single))
                if not price_is_validated:
                    try:
                        pc_meta = str(order_tracker.get_custom_meta(user_id, "price_calculation_block", default="") or "").strip()
                        if pc_meta:
                            status = str(_extract_tag(pc_meta, "status") or "").strip().upper()
                            ready = str(_extract_tag(pc_meta, "ready_to_send") or "").strip()
                            if status == "OK" and ready:
                                price_is_validated = True
                    except Exception:
                        pass
                if has_money and is_price_request_now and (not price_is_validated):
                    response = re.sub(r"\b\d[\d\s.,]*\s*(?:fcfa|f)\b", "", str(response or ""), flags=re.IGNORECASE)
                    response = re.sub(r"\s+", " ", response).strip()
                    print("⚠️ [PRICE_GUARD] hallucination prevented")
            except Exception as _hg_e:
                print(f"⚠️ [PRICE_GUARD] error: {type(_hg_e).__name__}: {_hg_e}")

            # 6.b Failsafe anti-validation fantôme (Python)
            # Si des slots obligatoires manquent, on interdit les formulations de validation/confirmation.
            try:
                st_chk = order_tracker.get_state(user_id)
                missing_now = sorted(list(st_chk.get_missing_fields()))
                if missing_now:
                    resp_low = str(response or "").lower()
                    # Gardes: ne jamais écraser une vraie clarification/question en cours.
                    if "?" in str(response or ""):
                        raise StopIteration("skip_failsafe_question")
                    try:
                        if isinstance(thinking_parsed, dict) and str(thinking_parsed.get("priority") or "").strip().upper() == "CLARIFY":
                            raise StopIteration("skip_failsafe_clarify")
                    except StopIteration:
                        raise
                    except Exception:
                        pass

                    if re.search(r"\b(on\s+valide|je\s+valide|je\s+confirme|on\s+confirme|commande\s+confirm|commande\s+valid|c['’]?est\s+bon)\b", resp_low):
                        # Rediriger vers le prochain champ manquant
                        nf = order_tracker.get_next_required_field(user_id, current_turn=current_turn)

                        def _fallback_question(field: Optional[str]) -> str:
                            f = str(field or "").upper().strip()
                            if f == "PRODUIT":
                                return "Tu veux quel produit exactement stp ?"
                            if f == "SPECS":
                                return "Tu veux quelle taille et quel type stp ?"
                            if f == "QUANTITÉ":
                                return "Tu veux combien (carton/paquets) stp ?"
                            if f == "ZONE":
                                return "Tu es dans quelle commune/quartier stp ?"
                            if f in {"NUMÉRO", "NUMERO"}:
                                return "Ton numéro WhatsApp pour le livreur stp ?"
                            if f == "PAIEMENT":
                                return "Tu peux envoyer l’acompte Wave de 2000 FCFA et la capture stp ?"
                            return "Tu peux préciser stp ?"

                        response = _fallback_question(nf)
                        print(f"🛡️ [FAILSAFE] validation_phantom_blocked | missing={','.join(missing_now)} | next={nf}")
            except StopIteration as _skip_fs:
                print(f"🛡️ [FAILSAFE] SKIP: {_skip_fs}")
            except Exception as _fs_e:
                print(f"⚠️ [FAILSAFE] error: {type(_fs_e).__name__}: {_fs_e}")

            try:
                response = str(response or "").replace("§§", "").strip()
            except Exception:
                pass

            # Replace ##RECAP## marker by a structured recap built from price_calculation/last_total_snapshot.
            try:
                if "##RECAP##" in str(response or ""):
                    price_block = ""
                    try:
                        price_block = str(order_tracker.get_custom_meta(user_id, "price_calculation_block", default="") or "")
                    except Exception:
                        price_block = ""

                    def _extract_local(tag: str) -> str:
                        try:
                            m = re.search(rf"<{re.escape(tag)}>(.*?)</{re.escape(tag)}>", price_block, flags=re.IGNORECASE | re.DOTALL)
                            return (m.group(1) if m else "").strip()
                        except Exception:
                            return ""

                    def _int_or_none(v: str) -> Optional[int]:
                        try:
                            if not v:
                                return None
                            m = re.search(r"(\d+)", str(v))
                            return int(m.group(1)) if m else None
                        except Exception:
                            return None

                    recap_lines = []
                    try:
                        items = []
                        try:
                            items = order_tracker.get_custom_meta(user_id, "detected_items", default=[])
                        except Exception:
                            items = []
                        if isinstance(items, list) and items:
                            for it in items:
                                if not isinstance(it, dict):
                                    continue
                                p = str(it.get("product") or "").strip().lower()
                                specs = str(it.get("specs") or "").strip().upper()
                                unit = str(it.get("unit") or "").strip().lower()
                                qty = it.get("qty")
                                if p == "pressions" and specs and unit == "lot" and isinstance(qty, int) and qty > 0:
                                    # Try read unit price from price_block, else show only subtotal if present.
                                    unit_price = _int_or_none(_extract_local("unit_price_fcfa"))
                                    subtotal = _int_or_none(_extract_local("product_subtotal_fcfa"))
                                    if unit_price:
                                        line = f"- Produit: pressions {specs} × {qty} lot ({UniversalPriceCalculator._fmt_fcfa(unit_price * qty)}F)"
                                    elif subtotal:
                                        line = f"- Produit: pressions {specs} × {qty} lot ({UniversalPriceCalculator._fmt_fcfa(subtotal)}F)"
                                    else:
                                        line = f"- Produit: pressions {specs} × {qty} lot"
                                    recap_lines.append(line)
                                elif p == "culottes" and specs and unit == "paquet" and isinstance(qty, int) and qty > 0:
                                    subtotal = _int_or_none(_extract_local("product_subtotal_fcfa"))
                                    if subtotal:
                                        line = f"- Produit: culottes {specs} × {qty} paquet ({UniversalPriceCalculator._fmt_fcfa(subtotal)}F)"
                                    else:
                                        line = f"- Produit: culottes {specs} × {qty} paquet"
                                    recap_lines.append(line)
                    except Exception:
                        recap_lines = []

                    if not recap_lines:
                        # fallback to totals only
                        snap = None
                        try:
                            snap = order_tracker.get_custom_meta(user_id, "last_total_snapshot", default=None)
                        except Exception:
                            snap = None
                        if isinstance(snap, dict):
                            subtotal = snap.get("product_subtotal")
                            zone = str(snap.get("zone") or "").strip()
                            fee = snap.get("delivery_fee")
                            total = snap.get("total")
                            if subtotal is not None:
                                recap_lines.append(f"- Produits: {UniversalPriceCalculator._fmt_fcfa(int(subtotal))}F")
                            if zone and fee is not None:
                                recap_lines.append(f"- Livraison: {zone} ({UniversalPriceCalculator._fmt_fcfa(int(fee))}F)")
                            if total is not None:
                                recap_lines.append(f"- Total: {UniversalPriceCalculator._fmt_fcfa(int(total))}F")

                    recap_block = "\n".join(recap_lines).strip()
                    response = str(response or "").replace("##RECAP##", recap_block).strip()
            except Exception:
                pass

            try:
                st_tel = order_tracker.get_state(user_id)
                tel_val = str(getattr(st_tel, "numero", "") or "").strip() or str(getattr(st_tel, "telephone", "") or "").strip()
                tel_digits = re.sub(r"[^\d]", "", tel_val)
                if len(tel_digits) == 10 and tel_digits.startswith("0"):
                    resp_low = str(response or "").lower()
                    if "pas au bon format" in resp_low or "n'est pas au bon format" in resp_low or "n’est pas au bon format" in resp_low:
                        parts = re.split(r"(?<=[.!?])\s+", str(response or "").strip())
                        kept = [p for p in parts if not re.search(r"(pas au bon format|n['’]est pas au bon format)", p, re.IGNORECASE)]
                        response = " ".join(kept).strip() or response
            except Exception:
                pass
            
            # 7. Récupérer état checklist
            checklist = self.prompt_system.get_checklist_state(user_id, company_id)
            
            # 8. Calcul temps traitement
            processing_time = (time.time() - start_time) * 1000
            
            print(f"✅ [SIMPLIFIED RAG] Terminé en {processing_time:.0f}ms")
            
            # 9. Construction résultat
            return SimplifiedRAGResult(
                response=response,
                confidence=0.95,  # Confiance élevée car prompt statique
                processing_time_ms=processing_time,
                checklist_state=checklist.to_string(),
                next_step=checklist.get_next_step(),
                detected_location=dynamic_context.get('detected_location'),
                shipping_fee=dynamic_context.get('shipping_fee'),
                usage=token_usage if isinstance(token_usage, dict) else None,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=total_cost,
                model=str(model_used),
                thinking=thinking
            )
        
        except Exception as e:
            print(f"❌ [SIMPLIFIED RAG] Erreur: {e}")
            import traceback
            traceback.print_exc()
            
            # Retour fallback
            processing_time = (time.time() - start_time) * 1000
            return SimplifiedRAGResult(
                response="Je rencontre une difficulté technique. Pouvez-vous reformuler votre question ?",
                confidence=0.0,
                processing_time_ms=processing_time,
                checklist_state="Erreur",
                next_step="Réessayer",
                detected_location=None,
                shipping_fee=None
            )


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTION PUBLIQUE (COMPATIBLE AVEC L'API)
# ═══════════════════════════════════════════════════════════════════════════════

_simplified_rag_engine: Optional[SimplifiedRAGEngine] = None

def get_simplified_rag_engine() -> SimplifiedRAGEngine:
    """Retourne le singleton du moteur RAG simplifié"""
    global _simplified_rag_engine
    if _simplified_rag_engine is None:
        _simplified_rag_engine = SimplifiedRAGEngine()
    return _simplified_rag_engine


async def get_simplified_rag_response(
    query: str,
    company_id: str,
    user_id: str,
    company_name: str = "Rue du Grossiste",
    images: Optional[List[str]] = None,
    request_id: str = "unknown"
) -> Dict[str, Any]:
    """
    Interface publique compatible avec l'API existante
    
    Args:
        query: Question utilisateur
        company_id: ID entreprise
        user_id: ID utilisateur
        company_name: Nom entreprise
        images: URLs images (optionnel)
        request_id: ID requête
    
    Returns:
        Dict avec response + métriques (compatible avec ancien format)
    """
    msg = str(query or "").strip()

    def _is_affirmation(s: str) -> bool:
        t = str(s or "").strip().lower()
        return t in {"oui", "ok", "okay", "d'accord", "dac", "c'est bon", "valide", "validé", "validee", "validé", "go"}

    def _is_negation(s: str) -> bool:
        t = str(s or "").strip().lower()
        return t in {"non", "nop", "pas", "annule", "annuler", "stop"}

    def _is_simple_ack(s: str) -> bool:
        t = str(s or "").strip().lower()
        return t in {"ok", "okay", "merci", "thanks", "d'accord", "dac", "reçu", "recu", "cool"}

    def _looks_like_new_request(s: str) -> bool:
        t = str(s or "").strip().lower()
        if len(t) >= 8 and any(k in t for k in ["ajoute", "changer", "finalement", "annule", "annuler", "modifier", "je veux", "je prend", "je prends", "rajoute", "plus", "encore"]):
            return True
        if any(k in t for k in ["pressions", "culottes", "taille", "t1", "t2", "t3", "t4", "t5", "t6", "t7", "lot", "paquet", "livraison"]):
            return True
        return False

    def _is_price_request_local(msg: str) -> bool:
        m = str(msg or "").lower()
        return any(k in m for k in ["prix", "total", "ça fait combien", "ca fait combien", "combien", "montant"])

    def _is_total_request_local(msg: str) -> bool:
        m = str(msg or "").lower()
        if not m.strip():
            return False
        # If the user explicitly asks about a product, do NOT short-circuit to last_total_snapshot.
        if any(k in m for k in ["pressions", "culotte", "culottes", "couche", "couches", "taille", "t1", "t2", "t3", "t4", "t5", "t6", "t7", "lot", "paquet", "paquets", "carton", "cartons"]):
            return False
        # Otherwise, only accept explicit cart/total wording.
        return any(
            k in m
            for k in [
                "total",
                "montant",
                "à payer",
                "a payer",
                "prix total",
                "au total",
                "ça fait combien",
                "ca fait combien",
            ]
        )

    def _extract_tag_local(xml: str, tag: str) -> str:
        try:
            m = re.search(rf"<{re.escape(tag)}>(.*?)</{re.escape(tag)}>", str(xml or ""), flags=re.IGNORECASE | re.DOTALL)
            return (m.group(1) if m else "")
        except Exception:
            return ""

    def _parse_int_amount(s: str) -> Optional[int]:
        try:
            if s is None:
                return None
            txt = str(s)
            m = re.search(r"(\d+)", txt.replace(" ", ""))
            return int(m.group(1)) if m else None
        except Exception:
            return None

    def _snapshot_from_price_block(pc_meta: str) -> Optional[Dict[str, Any]]:
        pc = str(pc_meta or "").strip()
        if not pc:
            return None
        status = str(_extract_tag_local(pc, "status") or "").strip().upper()
        if status and status != "OK":
            return None
        total_fcfa = _parse_int_amount(_extract_tag_local(pc, "total_fcfa"))
        subtotal_fcfa = _parse_int_amount(_extract_tag_local(pc, "product_subtotal_fcfa"))
        delivery_fcfa = _parse_int_amount(_extract_tag_local(pc, "delivery_fee_fcfa"))
        zone = str(_extract_tag_local(pc, "zone") or "").strip() or None
        if total_fcfa is None and subtotal_fcfa is None and delivery_fcfa is None:
            return None
        try:
            items = order_tracker.get_custom_meta(user_id, "detected_items", default=[])
        except Exception:
            items = []
        return {
            "items": items if isinstance(items, list) else [],
            "zone": zone,
            "delivery_fee": delivery_fcfa,
            "product_subtotal": subtotal_fcfa,
            "total": total_fcfa,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _mini_route_confirmation(message: str) -> str:
        from core.llm_client import complete as mini_complete

        msg_txt = str(message or "").strip()
        prompt = (
            "Tu es un classificateur. Retourne uniquement du JSON valide.\n"
            "But: classifier la réponse client après une question de validation de commande.\n"
            "Sortie JSON: {\"action\": \"CONFIRM|CANCEL|EDIT_REQUEST|NEW_REQUEST|ACK|UNKNOWN\", \"confidence\": 0-1, \"reason\": \"...\"}.\n"
            "Règles: \n"
            "- CONFIRM si le client confirme/valide la commande.\n"
            "- CANCEL si le client refuse/annule.\n"
            "- ACK si simple acquittement (ok/merci/d'accord) sans demande.\n"
            "- EDIT_REQUEST si il veut changer quelque chose mais sans préciser un nouveau panier complet.\n"
            "- NEW_REQUEST si il formule une nouvelle demande (nouveau produit/qté/zone, etc.).\n"
            "- UNKNOWN sinon.\n"
            f"MESSAGE_CLIENT: {json.dumps(msg_txt, ensure_ascii=False)}\n"
        )

        try:
            raw = await mini_complete(
                prompt=prompt,
                model_name=os.getenv("CONFIRM_ROUTER_MODEL", "google/gemini-2.5-flash-lite"),
                temperature=0.0,
                max_tokens=int(os.getenv("CONFIRM_ROUTER_MAX_TOKENS", "120")),
            )
        except Exception:
            return "UNKNOWN"

        raw_s = str(raw or "").strip()
        try:
            data = json.loads(raw_s)
        except Exception:
            if "{" in raw_s and "}" in raw_s:
                try:
                    cand = raw_s[raw_s.find("{") : raw_s.rfind("}") + 1]
                    data = json.loads(cand)
                except Exception:
                    return "UNKNOWN"
            else:
                return "UNKNOWN"

        act = str((data or {}).get("action") or "").strip().upper()
        if act in {"CONFIRM", "CANCEL", "EDIT_REQUEST", "NEW_REQUEST", "ACK", "UNKNOWN"}:
            return act
        return "UNKNOWN"

    awaiting_code = str(order_tracker.get_custom_meta(user_id, "awaiting_confirmation_code", default="") or "").strip()
    confirmed_code = str(order_tracker.get_custom_meta(user_id, "order_confirmed_code", default="") or "").strip()

    async def _mini_smalltalk_reply(message: str) -> str:
        from core.llm_client import complete as mini_complete

        msg_txt = str(message or "").strip()
        prompt = (
            "Tu es un assistant WhatsApp très bref.\n"
            "But: répondre aux messages de politesse/ack (merci, ok, super, d'accord) après une commande.\n"
            "Règles: 0-6 mots, max 1 emoji, pas de question, pas de prix, pas de nouveaux sujets.\n"
            "Si une réponse n'est pas nécessaire, réponds exactement: SILENCE\n"
            f"MESSAGE_CLIENT: {json.dumps(msg_txt, ensure_ascii=False)}\n"
        )
        try:
            raw = await mini_complete(
                prompt=prompt,
                model_name=os.getenv("POST_CONFIRM_MINI_MODEL", "google/gemini-2.5-flash-lite"),
                temperature=0.2,
                max_tokens=int(os.getenv("POST_CONFIRM_MINI_MAX_TOKENS", "40")),
            )
        except Exception:
            return ""
        out = str(raw or "").strip()
        if out.upper() == "SILENCE":
            return ""
        return out

    if awaiting_code and not confirmed_code:
        # We are waiting for the client's explicit YES/NO.
        if _is_affirmation(msg):
            order_tracker.set_custom_meta(user_id, "order_confirmed_code", awaiting_code)
            order_tracker.set_custom_meta(user_id, "awaiting_confirmation_code", "")
            return {
                "response": f"Commande validée ✅ (code: {awaiting_code}).\n\nVeuillez ne pas répondre à ce message (sauf problème). Merci 🙏",
                "confidence": 1.0,
                "documents_found": True,
                "processing_time_ms": 0,
                "search_method": "short_circuit",
                "context_used": "order_confirmation",
                "thinking": "",
                "validation": None,
                "usage": {},
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost": 0.0,
                "model": "none",
                "checklist_state": "CONFIRMED",
                "next_step": "STOP",
                "detected_location": None,
                "shipping_fee": None,
            }
        if _is_negation(msg):
            order_tracker.set_custom_meta(user_id, "awaiting_confirmation_code", "")
            return {
                "response": "D'accord 👍 Dis-moi juste ce que tu veux changer (produit, taille, quantité ou livraison).",
                "confidence": 1.0,
                "documents_found": True,
                "processing_time_ms": 0,
                "search_method": "short_circuit",
                "context_used": "order_confirmation",
                "thinking": "",
                "validation": None,
                "usage": {},
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost": 0.0,
                "model": "none",
                "checklist_state": "EDIT",
                "next_step": "CONTINUE",
                "detected_location": None,
                "shipping_fee": None,
            }

        if _is_simple_ack(msg) and (not _looks_like_new_request(msg)):
            return {
                "response": "OK ✅",
                "confidence": 1.0,
                "documents_found": True,
                "processing_time_ms": 0,
                "search_method": "short_circuit",
                "context_used": "order_confirmation",
                "thinking": "",
                "validation": None,
                "usage": {},
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost": 0.0,
                "model": "none",
                "checklist_state": "AWAITING_CONFIRMATION",
                "next_step": "WAIT_CONFIRMATION",
                "detected_location": None,
                "shipping_fee": None,
            }

    # Post-confirmation trivial messages -> mini model (cheap) to save tokens.
    if confirmed_code:
        if _is_simple_ack(msg) and (not _looks_like_new_request(msg)):
            mini_ans = await _mini_smalltalk_reply(msg)
            if mini_ans:
                return {
                    "response": str(mini_ans).strip(),
                    "confidence": 1.0,
                    "documents_found": True,
                    "processing_time_ms": 0,
                    "search_method": "mini_llm",
                    "context_used": "post_confirmation_smalltalk",
                    "thinking": "",
                    "validation": None,
                    "usage": {},
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "cost": 0.0,
                    "model": "none",
                    "checklist_state": "CONFIRMED",
                    "next_step": "STOP",
                    "detected_location": None,
                    "shipping_fee": None,
                }

    if confirmed_code and (not _looks_like_new_request(msg)) and _is_simple_ack(msg):
        # After confirmation, ignore pure acknowledgements without hitting the LLM.
        return {
            "response": "Merci ✅",
            "confidence": 1.0,
            "documents_found": True,
            "processing_time_ms": 0,
            "search_method": "short_circuit",
            "context_used": "post_confirmation_ack",
            "thinking": "",
            "validation": None,
            "usage": {},
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cost": 0.0,
            "model": "none",
            "checklist_state": "CONFIRMED",
            "next_step": "STOP",
            "detected_location": None,
            "shipping_fee": None,
        }

    # Re-open flow on real new request after confirmation.
    if confirmed_code and _looks_like_new_request(msg):
        try:
            order_tracker.set_custom_meta(user_id, "order_confirmed_code", "")
        except Exception:
            pass

    engine = get_simplified_rag_engine()
    
    result = await engine.process_query(
        query=query,
        user_id=user_id,
        company_id=company_id,
        company_name=company_name,
        images=images,
        request_id=request_id
    )

    try:
        result.response = str(result.response or "").replace("§§", "").strip()
    except Exception:
        pass

    try:
        pc_meta = str(order_tracker.get_custom_meta(user_id, "price_calculation_block", default="") or "").strip()
        snap = _snapshot_from_price_block(pc_meta)
        if snap:
            order_tracker.set_custom_meta(user_id, "last_total_snapshot", snap)
    except Exception:
        pass
    try:
        st_after = order_tracker.get_state(user_id)
        is_complete = bool(getattr(st_after, "is_complete", lambda: False)())
    except Exception:
        is_complete = False

    try:
        resp_l = str(result.response or "").lower()
        asks_validation = bool(re.search(r"\b(on\s+valide|on\s+confirme|c['’]?est\s+bien\s+ça)\b", resp_l)) and ("?" in str(result.response or ""))
        already_waiting = bool(str(order_tracker.get_custom_meta(user_id, "awaiting_confirmation_code", default="") or "").strip())
        already_confirmed = bool(str(order_tracker.get_custom_meta(user_id, "order_confirmed_code", default="") or "").strip())
        if is_complete and asks_validation and (not already_waiting) and (not already_confirmed):
            code = uuid.uuid4().hex[:8]
            order_tracker.set_custom_meta(user_id, "awaiting_confirmation_code", code)

            pc_meta = str(order_tracker.get_custom_meta(user_id, "price_calculation_block", default="") or "").strip()
            snap = _snapshot_from_price_block(pc_meta) or (order_tracker.get_custom_meta(user_id, "last_total_snapshot", default=None) or None)
            zone = None
            delivery_fee = None
            product_subtotal = None
            total = None
            if isinstance(snap, dict):
                zone = snap.get("zone")
                delivery_fee = snap.get("delivery_fee")
                product_subtotal = snap.get("product_subtotal")
                total = snap.get("total")

            try:
                st_now = order_tracker.get_state(user_id)
                phone = str(getattr(st_now, "numero", "") or getattr(st_now, "telephone", "") or "").strip()
            except Exception:
                phone = ""

            try:
                pay = str(order_tracker.get_custom_meta(user_id, "paiement", default="") or "").strip()
            except Exception:
                pay = ""

            lines = []
            lines.append("📋 Résumé commande:")

            try:
                items = order_tracker.get_custom_meta(user_id, "detected_items", default=[])
            except Exception:
                items = []
            if isinstance(items, list) and items:
                for it in items:
                    if not isinstance(it, dict):
                        continue
                    p = str(it.get("product") or "").strip().lower()
                    specs = str(it.get("specs") or "").strip().upper()
                    unit = str(it.get("unit") or "").strip().lower()
                    qty = it.get("qty")
                    if p and isinstance(qty, int) and qty > 0:
                        sfx = f" {specs}" if specs else ""
                        ufx = f" {unit}" if unit else ""
                        lines.append(f"- Produit: {p}{sfx} × {qty}{ufx}")

            if zone:
                if delivery_fee is not None:
                    lines.append(f"- Livraison: {zone} ({UniversalPriceCalculator._fmt_fcfa(int(delivery_fee))}F)")
                else:
                    lines.append(f"- Livraison: {zone}")
            if total is not None:
                if product_subtotal is not None and delivery_fee is not None:
                    lines.append(
                        f"- Total: {UniversalPriceCalculator._fmt_fcfa(int(total))}F (produits {UniversalPriceCalculator._fmt_fcfa(int(product_subtotal))}F + livraison {UniversalPriceCalculator._fmt_fcfa(int(delivery_fee))}F)"
                    )
                else:
                    lines.append(f"- Total: {UniversalPriceCalculator._fmt_fcfa(int(total))}F")
            if phone:
                lines.append(f"- Numéro: {phone}")
            if pay:
                lines.append(f"- Paiement: {pay}")

            recap = "\n".join([str(x).strip() for x in lines if str(x).strip()])
            return {
                "response": f"{recap}\n\nC'est bon pour toi ? Réponds juste OUI pour confirmer.",
                "confidence": 1.0,
                "documents_found": True,
                "processing_time_ms": result.processing_time_ms,
                "search_method": "python_recap",
                "context_used": f"Checklist: {result.checklist_state}",
                "thinking": result.thinking,
                "validation": None,
                "usage": result.usage,
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "total_tokens": result.total_tokens,
                "cost": result.cost,
                "model": result.model,
                "checklist_state": result.checklist_state,
                "next_step": "WAIT_CONFIRMATION",
                "detected_location": result.detected_location,
                "shipping_fee": result.shipping_fee,
            }
    except Exception:
        pass
    
    # Format compatible avec l'ancien système
    return {
        "response": result.response,
        "confidence": result.confidence,
        "documents_found": True,  # Toujours True car prompt statique
        "processing_time_ms": result.processing_time_ms,
        "search_method": "simplified_prompt_system",
        "context_used": f"Checklist: {result.checklist_state}",
        "thinking": result.thinking,
        "validation": None,
        
        # Métriques LLM
        "usage": result.usage,
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
        "total_tokens": result.total_tokens,
        "cost": result.cost,
        "model": result.model,
        
        # Infos supplémentaires
        "checklist_state": result.checklist_state,
        "next_step": result.next_step,
        "detected_location": result.detected_location,
        "shipping_fee": result.shipping_fee
    }
