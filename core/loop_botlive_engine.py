"""
🔄 MOTEUR BOTLIVE EN BOUCLE - PYTHON ↔ LLM
Système hybride intelligent où Python et LLM se relaient

PRINCIPE:
┌─────────────────────────────────────────────────────────┐
│ MESSAGE CLIENT                                          │
└──────────────┬──────────────────────────────────────────┘
               │
        ┌──────▼──────┐
        │ DÉCLENCHEUR?│
        │ (4 balises) │
        └──────┬──────┘
               │
    ┌──────────┴──────────┐
    │                     │
  OUI                    NON
    │                     │
    ▼                     ▼
┌─────────┐         ┌──────────┐
│ PYTHON  │         │   LLM    │
│ (auto)  │         │ (guide)  │
└────┬────┘         └─────┬────┘
     │                    │
     └──────────┬─────────┘
                │
                ▼
        ┌───────────────┐
        │ RÉPONSE       │
        │ + CHECKLIST   │
        └───────────────┘

DÉCLENCHEURS (4 balises):
1. Image → BLIP-2 ou OCR
2. Zone → Regex delivery
3. Tel → Regex numéro
4. Confirmation → Mots-clés

SI DÉCLENCHEUR → Python automatique (99.9% fiable)
SI PAS DÉCLENCHEUR → LLM guide vers déclencheur

LLM a TOUJOURS accès à:
- Checklist (photo ✓/✗, paiement ✓/✗, zone ✓/✗, tel ✓/✗)
- Dernière réponse Python
- Historique conversation

→ LLM peut TOUJOURS remettre client sur les rails
"""

import logging
import json
from typing import Dict, Optional, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class LoopBotliveEngine:
    """
    Moteur en boucle : Python (auto) ↔ LLM (guide)
    """
    
    def __init__(self):
        # Legacy: ancien moteur hybride Python↔LLM (désactivé par défaut)
        # Le système de production Botlive utilise désormais BotliveRAGHybrid
        # + HYDE v18. Ce moteur ne doit plus être actif en prod.
        self.enabled = False  # Désactivé par défaut
        self.stats = {
            "python_auto": 0,
            "llm_guide": 0,
            "total": 0
        }
        self.last_python_response = None  # Mémoriser dernière réponse Python
    
    def enable(self):
        """Active le moteur en boucle"""
        self.enabled = True
        logger.info("🔄 [LOOP] Moteur en boucle ACTIVÉ")
    
    def disable(self):
        """Désactive le moteur en boucle"""
        self.enabled = False
        logger.warning("⚠️ [LOOP] Moteur en boucle DÉSACTIVÉ")
    
    def is_enabled(self) -> bool:
        """Vérifie si le moteur est activé"""
        return self.enabled
    
    def process_message(
        self,
        message: str,
        notepad: Dict[str, Any],
        vision_result: Optional[Dict[str, Any]],
        ocr_result: Optional[Dict[str, Any]],
        llm_function: callable
    ) -> Dict[str, Any]:
        """
        Point d'entrée principal - Décide Python ou LLM
        
        Returns:
            {
                "response": str,
                "state": dict,
                "source": "python_auto" ou "llm_guide",
                "checklist": str (visible pour LLM)
            }
        """
        try:
            self.stats["total"] += 1

            # 🔎 Bypass SALUT: réponse Python directe pour politesse simple
            lower = (message or "").strip().lower()
            greet_tokens = ["salut", "bonjour", "bonsoir", "bjr", "slt", "hello", "coucou"]
            if any(lower.startswith(tok) for tok in greet_tokens) or lower in greet_tokens:
                reply = "Bonjour et bienvenue ! En quoi puis-je vous aider svp ?"
                self.stats["python_auto"] += 1
                return {
                    "response": reply,
                    "state": notepad or {},
                    "source": "python_auto",
                    "checklist": "—",
                }
            
            # 1. COLLECTER L'ÉTAT
            state = self._collect_state(vision_result, ocr_result, notepad)
            
            # 2. GÉNÉRER CHECKLIST (visible pour LLM)
            checklist = self._generate_checklist(state)
            
            # 3. DÉTECTER DÉCLENCHEURS (4 balises)
            trigger = self._detect_trigger(message, vision_result, ocr_result, state)
            
            logger.info(f"🔍 [LOOP] Déclencheur détecté: {trigger['type']}")
            
            # 4. VÉRIFIER SI 4/4 COLLECTÉ (PATCH #3) - PRIORITÉ ABSOLUE
            logger.warning(f"🔧 [PATCH#3] État avant vérification completion: {list(state.keys())}")
            logger.warning(f"🔧 [PATCH#3] Aperçu état: photo={bool(state.get('photo', {}).get('collected'))}, paiement={bool(state.get('paiement', {}).get('collected'))}, zone={bool(state.get('zone', {}).get('collected'))}, tel={bool(state.get('tel', {}).get('collected'))}")
            completion_check = self._check_completion(state)
            if completion_check and completion_check.get("action") == "SEND_FINAL_RECAP":
                logger.warning("🎯 [PATCH#3] 4/4 collecté détecté → Récapitulatif final automatique")
                return {
                    "response": completion_check["message"],
                    "state": state,
                    "source": "python_final_recap",
                    "trigger": "completion_detected",
                    "checklist": checklist,
                    "final_data": completion_check["data"],
                    "stats": self.stats
                }
            
            # 5. VÉRIFIER SI CONFIRMATION NÉCESSAIRE (après vérification completion)
            if hasattr(self, 'pending_confirmations') and self.pending_confirmations:
                # ✅ CONFIRMATION REQUISE → DEMANDER AU CLIENT
                from core.intelligent_data_reconciler import IntelligentDataReconciler
                confirmation_message = IntelligentDataReconciler.generate_confirmation_message(self.pending_confirmations)
                
                if confirmation_message:
                    logger.info("❓ [LOOP] Confirmation requise pour changement d'avis")
                    return {
                        "response": confirmation_message,
                        "state": state,
                        "source": "confirmation_required",
                        "trigger": "confirmation",
                        "checklist": checklist,
                        "stats": self.stats
                    }
            
            # 6. CONTINUER AVEC LE FLOW NORMAL
            logger.warning(f"🔧 [PATCH#2] Pas de completion détectée, continuation flow normal")
            
            # 7. ROUTER VERS PYTHON OU LLM
            if trigger["triggered"]:
                # ✅ DÉCLENCHEUR ACTIVÉ → PYTHON AUTOMATIQUE
                response = self._python_auto_response(trigger, state, message)
                
                # IMPORTANT: Si Python retourne "llm_takeover", passer au LLM
                if response == "llm_takeover":
                    logger.info("🔄 [LOOP] Python → LLM takeover (récap/validation)")
                    response = self._llm_guide_response(
                        message, state, checklist, llm_function, mode="recap_validation"
                    )
                    self.stats["llm_guide"] += 1
                    return {
                        "response": response,
                        "state": state,
                        "source": "llm_guide",
                        "trigger": trigger["type"],
                        "checklist": checklist,
                        "stats": self.stats
                    }
                
                self.last_python_response = response
                self.stats["python_auto"] += 1
                
                logger.info(f"✅ [LOOP] Python auto: {response[:100]}...")
                
                return {
                    "response": response,
                    "state": state,
                    "source": "python_auto",
                    "trigger": trigger["type"],
                    "checklist": checklist,
                    "stats": self.stats
                }
            
            else:
                # ⚠️ PAS DE DÉCLENCHEUR → LLM GUIDE
                response = self._llm_guide_response(
                    message, state, checklist, llm_function
                )
                self.stats["llm_guide"] += 1
                
                logger.info(f"🤖 [LOOP] LLM guide: {response[:100]}...")
                
                return {
                    "response": response,
                    "state": state,
                    "source": "llm_guide",
                    "trigger": "none",
                    "checklist": checklist,
                    "stats": self.stats
                }
        
        except Exception as e:
            logger.error(f"❌ [LOOP] Erreur: {e}")
            return {
                "response": "Envoyez photo du paquet 📦",
                "state": {},
                "source": "fallback",
                "checklist": "❌ Erreur système"
            }
    
    def _collect_state(
        self,
        vision_result: Optional[Dict[str, Any]],
        ocr_result: Optional[Dict[str, Any]],
        notepad: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Collecte l'état complet avec RÉCONCILIATION INTELLIGENTE
        
        Utilise le système de réconciliation pour gérer les changements d'avis
        et les conflits de données en temps réel
        """
        
        try:
            from core.intelligent_data_reconciler import IntelligentDataReconciler
            
            # ✅ RÉCONCILIATION INTELLIGENTE DES DONNÉES
            reconciled_state = IntelligentDataReconciler.reconcile_data(
                vision_result, ocr_result, notepad
            )
            
            # Ajouter les données produit depuis notepad
            reconciled_state["produit"] = {
                "collected": bool(notepad.get("products")),
                "data": notepad.get("last_product_mentioned", "Couches")
            }
            
            # Stocker les confirmations nécessaires pour usage ultérieur
            self.pending_confirmations = reconciled_state.get("confirmations_needed", [])
            self.data_conflicts = reconciled_state.get("conflicts", [])
            
            # 🔧 SIGNALER SI NOTEPAD MODIFIÉ PAR RÉCONCILIATEUR
            self.notepad_updated_by_reconciler = reconciled_state.get("notepad_updated", False)
            
            # Log des résultats de réconciliation
            if self.pending_confirmations:
                logger.info(f"⚠️ [STATE] {len(self.pending_confirmations)} confirmation(s) nécessaire(s)")
            if self.data_conflicts:
                logger.info(f"🔄 [STATE] {len(self.data_conflicts)} conflit(s) détecté(s)")
            if self.notepad_updated_by_reconciler:
                logger.warning(f"💾 [STATE] Notepad modifié par réconciliateur → Sauvegarde requise")
            
            return reconciled_state
            
        except Exception as e:
            logger.error(f"❌ [STATE] Erreur réconciliation: {e}")
            # Fallback vers l'ancienne méthode
            fallback_state = self._collect_state_fallback(vision_result, ocr_result, notepad)
            logger.info(f"🔧 [PATCH#2] Utilisation fallback state pour vérification completion")
            return fallback_state
    
    def _collect_state_fallback(
        self,
        vision_result: Optional[Dict[str, Any]],
        ocr_result: Optional[Dict[str, Any]],
        notepad: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Méthode fallback si réconciliation échoue
        
        🔧 PATCH #1: Priorité au notepad persisté pour éviter perte de données
        """
        
        # ✅ PHOTO : PRIORITÉ AU NOTEPAD PERSISTÉ
        photo_collected = False
        photo_data = None
        
        # PATCH #1: Vérifier d'abord le notepad (données persistées)
        if notepad.get("photo_produit") or notepad.get("photo_produit_description"):
            photo_collected = True
            photo_data = notepad.get("photo_produit") or notepad.get("photo_produit_description")
            logger.info(f"📋 [PATCH#1] Photo depuis notepad: {photo_data[:50] if photo_data else 'N/A'}...")
        elif vision_result and vision_result.get("description"):
            # Seulement si pas de données persistées
            desc = vision_result["description"]
            is_product = any(kw in desc.lower() for kw in ["bag", "diaper", "couche", "paquet", "wipe", "lingette"])
            is_screenshot = any(kw in desc.lower() for kw in ["screenshot", "app", "screen", "capture", "phone"])
            
            if is_product and not is_screenshot:
                photo_collected = True
                photo_data = desc
                logger.info(f"✅ [STATE] Photo produit actuelle détectée: {desc[:50]}...")
        elif notepad.get("photo_produit"):
            photo_collected = True
            photo_data = notepad.get("photo_produit")
            logger.info(f"📋 [STATE] Photo depuis notepad: {photo_data[:50]}...")
        
        # ✅ PAIEMENT : PRIORITÉ AU NOTEPAD PERSISTÉ
        paiement_collected = False
        paiement_data = None
        
        # PATCH #1: Vérifier d'abord le notepad (données persistées)
        if notepad.get("paiement"):
            paiement_collected = True
            paiement_data = notepad.get("paiement", {}).get("montant")
            logger.info(f"📋 [PATCH#1] Paiement depuis notepad: {paiement_data}F")
        elif ocr_result and ocr_result.get("valid"):
            # Seulement si pas de données persistées
            paiement_collected = True
            paiement_data = ocr_result.get("amount", 0)
            logger.info(f"✅ [STATE] Paiement actuel détecté: {paiement_data}F")
        
        return {
            "photo": {
                "collected": photo_collected,
                "data": photo_data
            },
            "produit": {
                "collected": bool(notepad.get("products")),
                "data": notepad.get("last_product_mentioned", "Couches")
            },
            "paiement": {
                "collected": paiement_collected,
                "data": paiement_data
            },
            "zone": {
                "collected": bool(notepad.get("delivery_zone")),
                "data": notepad.get("delivery_zone"),
                "cost": notepad.get("delivery_cost", 1500)
            },
            "tel": {
                "collected": bool(notepad.get("phone_number")),
                "data": notepad.get("phone_number"),
                "valid": self._validate_phone(notepad.get("phone_number"))
            }
        }
    
    def _check_completion(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        🔧 PATCH #3: Vérifie si 4/4 éléments sont collectés et génère récapitulatif final automatique
        
        Returns:
            Dict avec message final hardcodé si tout collecté, None sinon
        """
        try:
            # Gestion robuste des différentes structures de données
            photo_ok = state.get("photo", {}).get("collected", False)
            payment_ok = state.get("paiement", {}).get("collected", False) 
            zone_ok = state.get("zone", {}).get("collected", False)
            tel_collected = state.get("tel", {}).get("collected", False)
            tel_valid = state.get("tel", {}).get("valid", False)
            tel_ok = tel_collected and tel_valid
            
            # Log détaillé pour debug
            logger.warning(f"🔍 [PATCH#2] Vérification 4/4:")
            logger.warning(f"   📸 Photo: {photo_ok}")
            logger.warning(f"   💳 Paiement: {payment_ok}")
            logger.warning(f"   📍 Zone: {zone_ok}")
            logger.warning(f"   📞 Téléphone: {tel_ok} (collected={tel_collected}, valid={tel_valid})")
            
            if photo_ok and payment_ok and zone_ok and tel_ok:
                logger.warning("✅ [PATCH#3] 4/4 collectés → Génération récapitulatif final automatique")
                
                # 🎯 FORMAT HARDCODÉ AVEC PLACEHOLDERS INTELLIGENTS
                montant = state.get("paiement", {}).get("data", 2000)
                
                # ✅ UTILISER LE MÊME SYSTÈME QUE DELIVERY_ZONE_EXTRACTOR
                try:
                    from core.timezone_helper import is_same_day_delivery_possible
                    delai = "aujourd'hui" if is_same_day_delivery_possible() else "demain"
                    logger.warning(f"🕐 [DEBUG] Délai calculé via timezone_helper: {delai}")
                except Exception as e:
                    # Fallback si timezone_helper échoue
                    heure_actuelle = datetime.now().hour
                    delai = "aujourd'hui" if heure_actuelle < 13 else "demain"
                    logger.warning(f"🕐 [DEBUG] Fallback - Heure actuelle: {heure_actuelle}h - Délai calculé: {delai}")
                    logger.error(f"❌ Erreur timezone_helper: {e}")
                
                message_final = f"""✅PARFAIT Commande confirmée 😊
Livraison prévue {delai}, acompte de {montant} F déjà versé.
Nous vous rappellerons bientôt pour les détails et le coût total.
Veuillez ne pas répondre à ce message."""
                
                return {
                    "action": "SEND_FINAL_RECAP",
                    "message": message_final,
                    "data": {
                        "montant": montant,
                        "delai": delai,
                        "photo": state.get("photo", {}).get("data", ""),
                        "zone": state.get("zone", {}).get("data", ""),
                        "telephone": state.get("tel", {}).get("data", "")
                    }
                }
            
            missing_count = sum([not photo_ok, not payment_ok, not zone_ok, not tel_ok])
            logger.warning(f"⚠️ [PATCH#2] {4-missing_count}/4 collectés, {missing_count} manquant(s)")
            
            return None
            
        except Exception as e:
            logger.error(f"❌ [PATCH#2] Erreur vérification completion: {e}")
            logger.error(f"❌ [PATCH#2] Structure state: {list(state.keys())}")
            return None
    
    def _validate_phone(self, phone: Optional[str]) -> bool:
        """Valide format téléphone (10 chiffres)"""
        if not phone:
            return False
        digits = ''.join(filter(str.isdigit, str(phone)))
        return len(digits) == 10
    
    def _generate_checklist(self, state: Dict[str, Any]) -> str:
        """
        Génère checklist ENRICHIE avec données exactes (pour LLM et logs)
        
        Format:
        ✅ Photo reçue: "a bag of sanitary wipes on a white background"
        ✅ Paiement validé: 2020F (OCR confirmé)
        ✅ Zone: Port-Bouët (2000F)
        ✅ Téléphone: 0102034567
        """
        
        lines = []
        
        # Photo (avec description BLIP-2)
        if state["photo"]["collected"]:
            desc = state["photo"]["data"]
            # Tronquer si trop long
            desc_short = desc[:50] + "..." if len(desc) > 50 else desc
            lines.append(f'✅ Photo reçue: "{desc_short}"')
        else:
            lines.append("❌ Photo manquante")
        
        # Paiement (avec montant OCR exact)
        if state["paiement"]["collected"]:
            montant = state["paiement"]["data"]
            lines.append(f"✅ Paiement validé: {montant}F (OCR confirmé)")
        else:
            lines.append("❌ Paiement manquant")
        
        # Zone (avec frais exacts)
        if state["zone"]["collected"]:
            zone = state["zone"]["data"]
            frais = state["zone"]["cost"]
            lines.append(f"✅ Zone: {zone} ({frais}F)")
        else:
            lines.append("❌ Zone manquante")
        
        # Téléphone (numéro exact)
        if state["tel"]["collected"] and state["tel"]["valid"]:
            tel = state["tel"]["data"]
            lines.append(f"✅ Téléphone: {tel}")
        elif state["tel"]["collected"] and not state["tel"]["valid"]:
            tel = state["tel"]["data"]
            lines.append(f"⚠️ Téléphone invalide: {tel} (format incorrect)")
        else:
            lines.append("❌ Téléphone manquant")

        # Bloc machine-readable pour le LLM (source de vérité Python)
        try:
            json_state = {
                "photo_collected": bool(state.get("photo", {}).get("collected")),
                "photo_description": state.get("photo", {}).get("data"),
                "paiement_collected": bool(state.get("paiement", {}).get("collected")),
                "paiement_montant": state.get("paiement", {}).get("data"),
                "zone_collected": bool(state.get("zone", {}).get("collected")),
                "zone_nom": state.get("zone", {}).get("data"),
                "zone_frais": state.get("zone", {}).get("cost"),
                "tel_collected": bool(state.get("tel", {}).get("collected")),
                "tel_valide": bool(state.get("tel", {}).get("valid")),
                "tel_numero": state.get("tel", {}).get("data"),
            }
            lines.append("---")
            lines.append("JSON_STATE:")
            lines.append(json.dumps(json_state, ensure_ascii=False))
        except Exception as e:
            logger.error(f"❌ [CHECKLIST] Erreur génération JSON_STATE: {e}")
        
        return "\n".join(lines)
    
    def _detect_trigger(
        self,
        message: str,
        vision_result: Optional[Dict[str, Any]],
        ocr_result: Optional[Dict[str, Any]],
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Détecte si un des 4 déclencheurs est activé
        
        DÉCLENCHEURS:
        1. Image → BLIP-2 détecte produit OU OCR détecte paiement
        2. Zone → Regex détecte commune Abidjan
        3. Tel → Regex détecte 10 chiffres
        4. Confirmation → Mots-clés (oui, ok, confirme)
        """
        
        message_lower = message.lower()
        
        # DÉCLENCHEUR 1: Image (BLIP-2 ou OCR)
        if vision_result:
            desc = vision_result.get("description", "")
            confidence = vision_result.get("confidence", 0.0)
            error = vision_result.get("error", None)
            
            # ✅ DONNÉES COMPLÈTES POUR PYTHON
            photo_data = {
                "description": desc,
                "confidence": confidence,
                "error": error,
                "valid": bool(desc and len(desc.strip()) > 3),
                "product_detected": bool(desc and any(kw in desc.lower() for kw in ["bag", "diaper", "couche", "paquet", "wipe", "lingette"]))
            }
            
            if photo_data["product_detected"]:
                return {"triggered": True, "type": "photo_produit", "data": photo_data}
        
        if ocr_result:
            # ✅ DONNÉES COMPLÈTES POUR PYTHON - TOUS LES CAS
            paiement_data = {
                "amount": ocr_result.get("amount", 0),
                "valid": ocr_result.get("valid", False),
                "error": ocr_result.get("error", None),
                "currency": ocr_result.get("currency", "FCFA"),
                "transactions": ocr_result.get("all_transactions", []),
                "raw_text": ocr_result.get("raw_text", ""),
                "sufficient": ocr_result.get("amount", 0) >= 2000 if ocr_result.get("amount") else False
            }
            
            # Déclencher même si invalide pour que Python puisse gérer l'erreur
            return {"triggered": True, "type": "paiement_ocr", "data": paiement_data}
        
        # DÉCLENCHEUR 2: Zone (système intelligent avec délai calculé)
        try:
            from core.delivery_zone_extractor import extract_delivery_zone_and_cost
            zone_info = extract_delivery_zone_and_cost(message)
            if zone_info:
                return {
                    "triggered": True, 
                    "type": "zone_detectee", 
                    "data": zone_info  # Toutes les données (nom, coût, délai calculé)
                }
        except Exception as e:
            logger.warning(f"⚠️ Erreur détection zone intelligente: {e}")
            # Fallback vers détection simple
            zones_abidjan = ["abobo", "adjamé", "attécoubé", "cocody", "koumassi", "marcory", "plateau", "port-bouët", "treichville", "yopougon", "bingerville", "songon", "anyama"]
            for zone in zones_abidjan:
                if zone in message_lower:
                    return {"triggered": True, "type": "zone_detectee", "data": zone.capitalize()}
        
        # DÉCLENCHEUR 3: Téléphone (regex) - PRIORITÉ HAUTE
        import re
        phone_patterns = [
            r'\b0[0-9]{9}\b',  # Format standard: 0787360757
            r'\b0[0-9]{2}\s*[0-9]{2}\s*[0-9]{2}\s*[0-9]{2}\s*[0-9]{2}\b',  # Avec espaces: 07 87 36 07 57
            r'\b\+225\s*[0-9]{2}\s*[0-9]{2}\s*[0-9]{2}\s*[0-9]{2}\s*[0-9]{2}\b'  # Avec code pays
        ]
        
        phone_match = None
        raw_phone = ""
        for pattern in phone_patterns:
            phone_match = re.search(pattern, message)
            if phone_match:
                raw_phone = phone_match.group(0)
                break
        
        if phone_match:
            # ✅ DONNÉES COMPLÈTES POUR PYTHON
            tel_clean = ''.join(filter(str.isdigit, raw_phone))[-10:]  # 10 derniers chiffres
            
            tel_data = {
                "raw": raw_phone,
                "clean": tel_clean,
                "valid": len(tel_clean) == 10 and tel_clean.startswith('0'),
                "length": len(tel_clean),
                "format_error": None
            }
            
            # Détecter le type d'erreur si invalide
            if not tel_data["valid"]:
                if len(tel_clean) < 10:
                    tel_data["format_error"] = "TOO_SHORT"
                elif len(tel_clean) > 10:
                    tel_data["format_error"] = "TOO_LONG"
                elif not tel_clean.startswith('0'):
                    tel_data["format_error"] = "WRONG_PREFIX"
                else:
                    tel_data["format_error"] = "INVALID_FORMAT"
            
            # Si c'est le dernier élément manquant → Récap direct
            if state["photo"]["collected"] and state["paiement"]["collected"] and state["zone"]["collected"]:
                return {"triggered": True, "type": "telephone_final", "data": tel_data}
            else:
                return {"triggered": True, "type": "telephone_detecte", "data": tel_data}
        
        # DÉCLENCHEUR 4: Toutes données collectées → RÉCAP AUTOMATIQUE
        if state["photo"]["collected"] and state["paiement"]["collected"] and \
           state["zone"]["collected"] and state["tel"]["collected"] and state["tel"]["valid"]:
            # Si toutes les 4 données sont collectées → Récap automatique
            return {"triggered": True, "type": "recap_auto", "data": "toutes_donnees_collectees"}
        
        # DÉCLENCHEUR 5: Confirmation après récap (mots-clés)
        if state["photo"]["collected"] and state["paiement"]["collected"] and \
           state["zone"]["collected"] and state["tel"]["collected"]:
            # Détecter confirmation (mots-clés + variantes)
            confirmation_keywords = [
                "oui", "ok", "confirme", "valide", "d'accord", "daccord",
                "je confirme", "je valide", "c'est bon", "cest bon",
                "parfait", "nickel", "go", "allons-y", "envoie"
            ]
            if any(kw in message_lower for kw in confirmation_keywords):
                # IMPORTANT: Passer au LLM pour validation finale chaleureuse
                return {"triggered": False, "type": "confirmation_llm", "data": "validation"}
        
        # Aucun déclencheur
        return {"triggered": False, "type": "none", "data": None}
    
    def _python_auto_response(
        self,
        trigger: Dict[str, Any],
        state: Dict[str, Any],
        message: str
    ) -> str:
        """
        Génère réponse automatique Python (99.9% fiable) avec gestion d'erreur complète
        """
        
        trigger_type = trigger["type"]
        trigger_data = trigger.get("data")
        
        # ✅ VALIDATION DES DONNÉES REÇUES
        try:
            from core.trigger_validator import validate_trigger_before_python
            if not validate_trigger_before_python(trigger_type, trigger_data):
                logger.error(f"❌ [PYTHON_AUTO] Données déclencheur invalides pour {trigger_type}")
                return "Petit souci technique de mon côté 😅 Pouvez-vous réessayer dans un instant ? 🔄"
        except Exception as e:
            logger.warning(f"⚠️ [PYTHON_AUTO] Validation échouée: {e}")
            # Continue quand même (fallback gracieux)
        
        # ✅ GESTION D'ERREUR GLOBALE
        try:
            return self._generate_response_by_type(trigger_type, trigger, state, message)
        except Exception as e:
            logger.error(f"❌ [PYTHON_AUTO] Erreur génération réponse: {e}")
            return "Oops, une erreur s'est glissée 😅 Pouvez-vous renvoyer votre message ? 🔄"
    
    def _generate_response_by_type(
        self,
        trigger_type: str,
        trigger: Dict[str, Any],
        state: Dict[str, Any],
        message: str
    ) -> str:
        """Génère la réponse selon le type de déclencheur avec gestion d'erreur"""
        
        # Photo produit détectée
        if trigger_type == "photo_produit":
            # ✅ GESTION COMPLÈTE BASÉE SUR LES DONNÉES STRUCTURÉES
            photo_data = trigger.get("data", {})
            
            # Cas d'erreur spécifiques
            if photo_data.get("error"):
                error_type = photo_data["error"]
                if error_type == "image_too_small":
                    return "La photo est un peu floue 😅 Pouvez-vous reprendre une image plus nette du produit ? 📸"
                elif error_type == "empty_caption":
                    return "Je ne distingue pas bien le produit sur cette photo 😕 Pouvez-vous la reprendre plus claire ? 📸"
                elif error_type == "unsupported_format":
                    return "Ce format d'image n'est pas reconnu 😅 Essayez plutôt en JPG ou PNG 📸"
                else:
                    return "Je n'arrive pas à bien analyser la photo 😕 Pouvez-vous en prendre une plus nette ? 📸"
            
            # Vérifier si produit détecté
            if not photo_data.get("product_detected", False):
                return "Je ne vois pas de produit sur cette photo 😅 Pouvez-vous photographier le bon article ? 📦"
            
            # Confiance faible
            if photo_data.get("confidence", 0) < 0.6:
                return "Je vois le produit, mais la photo est un peu floue 😅 Pouvez-vous la reprendre plus nette ? 📸"
            
            # Photo OK → Continuer le processus
            if not state["paiement"]["collected"]:
                return "Parfait ! Une avance de 2000F via Wave au +225 0787360757 comme dépôt de validation est requise 💳. Une fois envoyée, envoyez-moi la capture s'il vous plaît."
            elif not state["zone"]["collected"]:
                return "Super, j'ai bien reçu ! 📸\nOn vous livre où précisément ( commune et quartier précis ) ? 📍"
            elif not state["tel"]["collected"]:
                return "Photo ok ! 📸\nIl me faut maintenant votre numéro pour la livraison 📞"
            else:
                return self._generate_recap(state)
        
        # Paiement validé OCR
        elif trigger_type == "paiement_ocr":
            # ✅ GESTION COMPLÈTE BASÉE SUR LES DONNÉES STRUCTURÉES
            paiement_data = trigger.get("data", {})
            
            # Cas d'erreur spécifiques
            if paiement_data.get("error"):
                error_type = paiement_data["error"]
                if error_type == "NUMERO_ABSENT":
                    return "Je ne vois pas de paiement vers notre numéro. Vérifiez bien que c'est +225 0787360757 💳"
                elif error_type == "OCR_NOT_LOADED":
                    return "Petit souci de lecture 🔄 Réessayez d'envoyer la capture dans un instant."
                elif error_type == "EMPTY_FILE":
                    return "L'image semble vide ou illisible 😅 Pouvez-vous renvoyer la capture ? 📱"
                else:
                    return "Je ne parviens pas à lire votre capture 😅 Pouvez-vous prendre une photo plus claire ? 📱"
            
            # Vérifier validité
            if not paiement_data.get("valid", False):
                return "Je ne détecte pas de paiement valide 😕 Assurez-vous que c'est bien un reçu Wave 📱"
            
            # Vérifier montant
            montant = paiement_data.get("amount", 0)
            if not montant or montant <= 0:
                return "Je n'arrive pas à lire le montant sur votre capture 😅 Pouvez-vous refaire la photo ? 📱"
            
            # Vérifier suffisance
            if not paiement_data.get("sufficient", False):
                manque = 2000 - montant
                return f"Reçu {montant}F ✅, mais il manque encore {manque}F pour atteindre 2000F minimum 💳\nPouvez-vous compléter le paiement ?"
            
            # Paiement OK → Continuer le processus
            if not state["zone"]["collected"]:
                return f"Super ! Paiement de {montant}F bien reçu 🎉\nDans quelle zone d'Abidjan êtes-vous pour la livraison ? 📍"
            elif not state["tel"]["collected"]:
                return f"Excellent ! Paiement de {montant}F confirmé 🎉\nPouvez-vous me donner votre numéro pour la livraison ? 📞"
            else:
                return self._generate_recap(state)
        
        # Zone détectée
        elif trigger_type == "zone_detectee":
            zone_data = trigger["data"]
            
            # Si c'est les nouvelles données complètes (dict)
            if isinstance(zone_data, dict):
                zone_nom = zone_data["name"]
                frais = zone_data["cost"]
                delai = zone_data.get("delai_calcule", "selon délais standard")
            else:
                # Fallback pour compatibilité (string simple)
                zone_nom = zone_data
                zones_peripheriques = ["port-bouët", "attécoubé", "bingerville", "songon", "anyama"]
                frais = 2000 if zone_nom.lower() in zones_peripheriques else 1500
                delai = "selon délais standard"
            
            if not state["tel"]["collected"]:
                return f"Noté 👍 Livraison à {zone_nom} → {frais}F 🚚\nLivraison prévue {delai}.\nDernière info : votre numéro de téléphone ? 📞"
            else:
                return self._generate_recap(state)
        
        # Téléphone détecté (pas le dernier)
        elif trigger_type == "telephone_detecte":
            # ✅ GESTION COMPLÈTE BASÉE SUR LES DONNÉES STRUCTURÉES
            tel_data = trigger.get("data", {})
            
            # Cas d'erreur spécifiques
            if tel_data.get("format_error"):
                error_type = tel_data["format_error"]
                if error_type == "TOO_SHORT":
                    return f"Le numéro est incomplet ({tel_data.get('length', 0)} chiffres). Il faut 10 chiffres, ex: 0787360757 📞"
                elif error_type == "TOO_LONG":
                    return f"Le numéro semble trop long ({tel_data.get('length', 0)} chiffres). Il doit faire 10 chiffres exacts 📞"
                elif error_type == "WRONG_PREFIX":
                    return "Le numéro doit commencer par 0, ex: 0787360757 📞"
                else:
                    return "Format de numéro invalide 😅 Il me faut 10 chiffres commençant par 0 📞"
            
            # Vérifier validité
            if not tel_data.get("valid", False):
                return "Je n'ai pas pu détecter de numéro valide 😕 Pouvez-vous l'écrire clairement (ex: 0787360757) ? 📞"
            
            # Numéro OK
            tel_clean = tel_data.get("clean", "")
            return f"Parfait 👍 {tel_clean} bien noté ! 📞\nEncore un petit détail et on finalise la commande."
        
        # Téléphone final (dernier élément) → PASSER AU LLM POUR RÉCAP CHALEUREUX
        elif trigger_type == "telephone_final":
            tel_data = trigger.get("data", {})
            
            # Vérifier validité
            if not tel_data.get("valid", False):
                error_type = tel_data.get("format_error", "INVALID_FORMAT")
                if error_type == "TOO_SHORT":
                    return f"Le numéro est incomplet ({tel_data.get('length', 0)} chiffres). Il faut 10 chiffres, ex: 0787360757 📞"
                elif error_type == "TOO_LONG":
                    return f"Le numéro semble trop long ({tel_data.get('length', 0)} chiffres). Il doit faire 10 chiffres exacts 📞"
                elif error_type == "WRONG_PREFIX":
                    return "Le numéro doit commencer par 0, ex: 0787360757 📞"
                else:
                    return "Format de numéro invalide 😅 Il me faut 10 chiffres commençant par 0 📞"
            
            # Numéro OK → PASSER AU LLM POUR RÉCAP CHALEUREUX
            return "llm_takeover"  # Signal spécial pour passer au LLM
        
        # RÉCAP AUTOMATIQUE (4/4 collecté) → PASSER AU LLM
        elif trigger_type == "recap_auto":
            return "llm_takeover"  # Signal spécial pour passer au LLM
        
        # Confirmation → NE DEVRAIT JAMAIS ARRIVER ICI (géré par LLM)
        elif trigger_type == "confirmation":
            return "llm_takeover"  # Signal spécial pour passer au LLM
        
        # Fallback
        else:
            return "Envoyez photo du paquet 📦"
    
    def _llm_guide_response(
        self,
        message: str,
        state: Dict[str, Any],
        checklist: str,
        llm_function: callable,
        mode: str = "guide"
    ) -> str:
        """
        LLM guide le client vers les déclencheurs OU génère récap/validation finale
        
        Args:
            mode: "guide" (défaut) ou "recap_validation" (tout collecté)
        """
        
        # MODE RÉCAP/VALIDATION: Tout est collecté, LLM fait récap chaleureux
        if mode == "recap_validation":
            zone = state["zone"]["data"] or "N/A"
            tel = state["tel"]["data"] or "N/A"
            # IMPORTANT: Ne JAMAIS inventer un montant, utiliser celui de l'OCR
            montant = state["paiement"]["data"] if state["paiement"]["data"] else "[ERREUR]"
            frais = state["zone"]["cost"] if state["zone"]["cost"] else 1500
            # Récupérer les détails du produit depuis le notepad
            produit = state["produit"]["data"] or "Couches"
            
            # Détecter si c'est une confirmation ou première présentation récap
            confirmation_keywords = [
                "oui", "ok", "confirme", "valide", "d'accord", "daccord",
                "je confirme", "je valide", "c'est bon", "cest bon",
                "parfait", "nickel", "go"
            ]
            is_confirmation = any(kw in message.lower() for kw in confirmation_keywords)
            
            if is_confirmation:
                # CLIENT CONFIRME → VALIDATION FINALE
                from core.timezone_helper import get_current_time_ci, is_same_day_delivery_possible
                now = get_current_time_ci()
                delai = "aujourd'hui" if is_same_day_delivery_possible() else "demain"
                
                prompt = f"""Tu es Jessica, assistante commerciale chaleureuse.

LE CLIENT VIENT DE CONFIRMER SA COMMANDE ! 🎉

DONNÉES COLLECTÉES:
- 📦 Produit: {produit}
- 📍 Zone: {zone} (Frais: {frais}F)
- 📞 Téléphone: {tel}
- 💳 Acompte: {montant}F
- ⏰ Livraison: {delai}

MISSION:
1. ACCUSER RÉCEPTION de la confirmation avec ENTHOUSIASME
2. Présenter récapitulatif CLAIR et RASSURANT
3. Indiquer délai de livraison ({delai})
4. Terminer par message chaleureux
5. Ajouter "⚠️ NE PAS RÉPONDRE À CE MESSAGE ⚠️" à la fin

TON: Chaleureux, professionnel, rassurant (comme une vraie assistante humaine)
MAX: 80 mots

EXEMPLE:
"Parfait ! 🎉 Votre commande est bien enregistrée !

📋 RÉCAPITULATIF:
📦 {produit}
📍 Livraison {zone} - {frais}F
💳 Acompte: {montant}F
📞 Contact: {tel}
⏰ Livraison: {delai}

On vous rappelle très bientôt pour confirmer l'heure exacte ! 😊

⚠️ NE PAS RÉPONDRE À CE MESSAGE ⚠️"

RÉPONSE:"""
            else:
                # PREMIÈRE PRÉSENTATION RÉCAP → DEMANDER CONFIRMATION
                prompt = f"""Tu es Jessica, assistante commerciale chaleureuse.

TOUTES LES INFOS SONT COLLECTÉES ! Il faut maintenant présenter le récap au client.

DONNÉES COLLECTÉES:
- 📦 Produit: Couches
- 📍 Zone: {zone} (Frais: {frais}F)
- 📞 Téléphone: {tel}
- 💳 Acompte: {montant}F

MESSAGE CLIENT:
{message}

MISSION:
1. ACCUSER RÉCEPTION du dernier message (zone OU téléphone)
2. Présenter récapitulatif CLAIR
3. DEMANDER CONFIRMATION explicite ("Vous confirmez ?" ou "C'est bon pour vous ?")

TON: Chaleureux, professionnel, rassurant
MAX: 60 mots

EXEMPLE:
"Super, {tel} bien noté ! 📞

Voici le récapitulatif de votre commande :
📦 Couches
📍 Livraison {zone} - {frais}F
💳 Acompte: {montant}F
📞 Contact: {tel}

Tout est correct ? Vous confirmez ? 😊"

RÉPONSE:"""
        
        # MODE GUIDE: Infos manquantes, LLM guide vers prochaine étape
        else:
            prompt = f"""Tu es Jessica, assistante commerciale chaleureuse.

MISSION: Guider le client pour collecter 4 infos (photo, paiement, zone, tel).

CHECKLIST ACTUELLE:
{checklist}

DERNIÈRE RÉPONSE AUTOMATIQUE:
{self.last_python_response or "Aucune"}

MESSAGE CLIENT:
{message}

RÈGLES:
1. TOUJOURS commencer par ACCUSER RÉCEPTION du message ("Bien reçu !", "Compris !", "Noté !")
2. Si hors-sujet (SAV, réclamation) → Rediriger +225 0787360757 avec empathie
3. Si négociation prix → Refuser avec douceur (2000F min obligatoire)
4. Sinon → Guider vers prochaine info manquante avec TON CHALEUREUX
5. Max 30 mots, ton naturel et rassurant

EXEMPLES:
- "Bien reçu ! 😊 Maintenant, envoyez-moi la photo du paquet 📦"
- "Compris ! Pour la zone, vous êtes où exactement à Abidjan ? 📍"
- "Noté ! Dernier détail : votre numéro de téléphone ? 📞"

RÉPONSE:"""
        
        try:
            response = llm_function(prompt)
            return response
        except Exception as e:
            logger.error(f"❌ [LOOP] LLM erreur: {e}")
            # Fallback: demander prochaine info manquante
            return self._fallback_guide(state)
    
    def _fallback_guide(self, state: Dict[str, Any]) -> str:
        """Fallback si LLM échoue: demander prochaine info manquante"""
        
        if not state["photo"]["collected"]:
            return "Pouvez-vous m'envoyer la photo du produit souhaité ? 📦"
        elif not state["paiement"]["collected"]:
            return "Parfait ! Une avance de 2000F via Wave au +225 0787360757 comme dépôt de validation est requise 💳. Une fois envoyée, envoyez-moi la capture s'il vous plaît."
        elif not state["zone"]["collected"]:
            return "Dans quelle communes êtes-vous ? 📍"
        elif not state["tel"]["collected"]:
            return "Pouvez-vous me donner votre numéro (10 chiffres) ? 📞"
        else:
            return self._generate_recap(state)
    
    def _generate_recap(self, state: Dict[str, Any]) -> str:
        """Génère récapitulatif automatique"""
        
        zone = state["zone"]["data"] or "N/A"
        tel = state["tel"]["data"] or "N/A"
        # IMPORTANT: Ne JAMAIS inventer un montant, utiliser celui de l'OCR
        montant = state["paiement"]["data"] if state["paiement"]["data"] else "[ERREUR]"
        frais = state["zone"]["cost"] if state["zone"]["cost"] else 1500
        
        return f"""📦 Couches | 📍 {zone} ({frais}F) | 📞 {tel} | 💳 {montant}F
Confirmez pour valider."""
    
    def _generate_validation(self, state: Dict[str, Any]) -> str:
        """Génère message validation finale"""
        
        zone = state["zone"]["data"] or "N/A"
        tel = state["tel"]["data"] or "N/A"
        # IMPORTANT: Ne JAMAIS inventer un montant, utiliser celui de l'OCR
        montant = state["paiement"]["data"] if state["paiement"]["data"] else "[ERREUR]"
        frais = state["zone"]["cost"] if state["zone"]["cost"] else 1500
        
        from datetime import datetime
        now = datetime.now()
        delai = "aujourd'hui" if now.hour < 13 else "demain"
        
        return f"""✅ Commande validée ! Récapitulatif:
📦 Couches - [Prix] F
🚚 Livraison {zone} - {frais}F
💳 Acompte: {montant}F
📞 Contact: {tel}
⏰ Livraison: {delai}

On te rappelle ! 😊

⚠️ NE PAS RÉPONDRE À CE MESSAGE ⚠️"""
    
    def get_stats(self) -> Dict[str, int]:
        """Retourne les statistiques"""
        return self.stats


# Instance globale (singleton)
_loop_engine = None

def get_loop_engine() -> LoopBotliveEngine:
    """Retourne l'instance singleton"""
    global _loop_engine
    if _loop_engine is None:
        _loop_engine = LoopBotliveEngine()
    return _loop_engine
