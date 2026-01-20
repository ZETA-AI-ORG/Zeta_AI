#!/usr/bin/env python3
"""
🧠 INTELLIGENT DATA RECONCILER
==============================

Système intelligent de réconciliation des données qui gère les changements d'avis
des clients en temps réel avec confirmation proactive.

RÈGLE D'OR : Les données ACTUELLES priment sur l'historique
SAUF si l'historique est récent (< 5 min) ET cohérent

OBJECTIF : Éviter les conflits de données et gérer les changements d'avis intelligemment.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
import logging
import difflib

logger = logging.getLogger(__name__)

class IntelligentDataReconciler:
    """Réconciliateur intelligent de données avec gestion des changements d'avis"""
    
    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        """Calcule la similarité sémantique entre deux descriptions"""
        if not text1 or not text2:
            return 0.0
        
        # Normaliser les textes
        t1 = text1.lower().strip()
        t2 = text2.lower().strip()
        
        # Similarité basique avec difflib
        similarity = difflib.SequenceMatcher(None, t1, t2).ratio()
        
        # Bonus si mots-clés similaires
        keywords1 = set(t1.split())
        keywords2 = set(t2.split())
        common_keywords = keywords1.intersection(keywords2)
        
        if common_keywords:
            keyword_bonus = len(common_keywords) / max(len(keywords1), len(keywords2))
            similarity = (similarity + keyword_bonus) / 2
        
        return similarity
    
    @staticmethod
    def is_product(vision_result: Dict[str, Any]) -> bool:
        """Vérifie si la vision détecte vraiment un produit"""
        if not vision_result or not vision_result.get("description"):
            return False
        
        desc = vision_result["description"].lower()
        
        # Mots-clés produits
        product_keywords = ["bag", "diaper", "couche", "paquet", "wipe", "lingette", "pack"]
        is_product = any(kw in desc for kw in product_keywords)
        
        # Mots-clés anti-produits (screenshots, etc.)
        anti_keywords = ["screenshot", "app", "screen", "capture", "phone", "text", "message"]
        is_screenshot = any(kw in desc for kw in anti_keywords)
        
        return is_product and not is_screenshot
    
    @staticmethod
    def detect_product_change(new_vision: Dict[str, Any], notepad: Dict[str, Any]) -> Dict[str, Any]:
        """
        Détecte si le client a changé de produit
        
        Returns:
            {
                "changed": bool,
                "old": str,
                "new": str,
                "similarity": float,
                "action": str,
                "confidence": str
            }
        """
        if not IntelligentDataReconciler.is_product(new_vision):
            return {"changed": False, "action": "ignore"}
        
        old_product = notepad.get("photo_produit", "")
        new_product = new_vision.get("description", "")
        
        if not old_product:
            return {
                "changed": False,
                "action": "accept_new",
                "new": new_product,
                "confidence": "high"
            }
        
        # Calculer similarité
        similarity = IntelligentDataReconciler.calculate_similarity(old_product, new_product)
        
        logger.info(f"🔍 [RECONCILER] Similarité produits: {similarity:.2f}")
        logger.info(f"   Ancien: {old_product[:50]}...")
        logger.info(f"   Nouveau: {new_product[:50]}...")
        
        if similarity < 0.3:
            # Produits très différents → Changement d'avis probable
            return {
                "changed": True,
                "old": old_product,
                "new": new_product,
                "similarity": similarity,
                "action": "demander_confirmation",
                "confidence": "high"
            }
        elif similarity < 0.7:
            # Produits moyennement différents → Doute
            return {
                "changed": True,
                "old": old_product,
                "new": new_product,
                "similarity": similarity,
                "action": "demander_clarification",
                "confidence": "medium"
            }
        else:
            # Produits similaires → Même produit, angle différent
            return {
                "changed": False,
                "action": "accept_similar",
                "similarity": similarity,
                "confidence": "high"
            }
    
    @staticmethod
    def reconcile_data(
        vision_result: Optional[Dict[str, Any]],
        ocr_result: Optional[Dict[str, Any]],
        notepad: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Réconcilie intelligemment les données actuelles avec l'historique
        
        RÈGLE D'OR : Les données ACTUELLES priment sur l'historique
        SAUF si l'historique est récent (< 5 min) ET cohérent
        """
        
        current_state = {
            "photo": {"collected": False, "data": None, "source": None, "needs_confirmation": False},
            "paiement": {"collected": False, "data": None, "source": None, "needs_confirmation": False},
            "zone": {"collected": False, "data": None, "source": "notepad"},
            "tel": {"collected": False, "data": None, "source": "notepad"},
            "conflicts": [],
            "confirmations_needed": [],
            "notepad_updated": False  # 🔧 FLAG POUR SIGNALER MODIFICATION NOTEPAD
        }
        
        now = datetime.now()
        
        # ========================================
        # 1. GESTION PHOTO PRODUIT - LOGIQUE BLIP-2 PERSISTANTE
        # ========================================
        
        # 🧠 VÉRIFIER SI BLIP-2 A DÉJÀ PARLÉ (MÉMOIRE PERSISTANTE)
        blip2_verdict_exists = notepad.get("blip2_photo_verdict") is not None
        
        if vision_result and vision_result.get("description"):
            # 🏆 COMPÉTITION OCR vs BLIP-2 → LE MEILLEUR GAGNE !
            
            # 💳 OCR A-T-IL TROUVÉ UN PAIEMENT ?
            ocr_found_payment = ocr_result and ocr_result.get("valid", False)
            
            if ocr_found_payment:
                # 💳 OCR GAGNE → C'est une image de paiement → IGNORER BLIP-2
                logger.info("💳 [RECONCILER] OCR détecte paiement → BLIP-2 ignoré, verdict photo inchangé")
                
                # Utiliser verdict BLIP-2 existant ou défaut
                if blip2_verdict_exists:
                    blip2_verdict = notepad.get("blip2_photo_verdict", False)
                    blip2_data = notepad.get("blip2_photo_data")
                    current_state["photo"]["collected"] = blip2_verdict
                    current_state["photo"]["data"] = blip2_data if blip2_verdict else None
                    current_state["photo"]["source"] = "blip2_persistent_verdict"
                else:
                    current_state["photo"]["collected"] = False
                    current_state["photo"]["data"] = None
                    current_state["photo"]["source"] = "blip2_never_spoke"
                    
            else:
                # 🤖 BLIP-2 GAGNE → BLIP-2 analyse et décide (OUI ou NON)
                logger.info("🤖 [RECONCILER] OCR échoue → BLIP-2 analyse l'image")
                
                # 🔍 BLIP-2 FAIT SON TRAVAIL NORMAL (peut accepter OU refuser)
                description = vision_result["description"].lower()
                is_product = any(kw in description for kw in 
                    ["bag", "diaper", "couche", "paquet", "pack", "wipe", "lingette", 
                     "bottle", "food", "product", "item", "box", "container"])
                
                # 💾 SAUVEGARDER VERDICT BLIP-2 (PERSISTANT)
                notepad["blip2_photo_verdict"] = is_product
                notepad["blip2_photo_data"] = vision_result["description"]
                notepad["blip2_photo_date"] = now.isoformat()
                current_state["notepad_updated"] = True  # 🔧 SIGNALER MODIFICATION
                
                # ✅ APPLIQUER VERDICT À LA CHECKLIST
                current_state["photo"]["collected"] = is_product
                current_state["photo"]["data"] = vision_result["description"] if is_product else None
                current_state["photo"]["source"] = "blip2_fresh_verdict"
                
                verdict_text = "ACCEPTÉE" if is_product else "REFUSÉE"
                logger.info(f"🤖 [RECONCILER] BLIP-2 verdict: Photo {verdict_text}")
            
        elif blip2_verdict_exists:
            # 🧠 PAS DE NOUVELLE IMAGE → UTILISER VERDICT BLIP-2 PERSISTANT
            blip2_verdict = notepad.get("blip2_photo_verdict", False)
            blip2_data = notepad.get("blip2_photo_data")
            
            current_state["photo"]["collected"] = blip2_verdict
            current_state["photo"]["data"] = blip2_data if blip2_verdict else None
            current_state["photo"]["source"] = "blip2_persistent_verdict"
            
            verdict_text = "VALIDÉE" if blip2_verdict else "REFUSÉE"
            logger.info(f"🧠 [RECONCILER] Verdict BLIP-2 persistant: Photo {verdict_text}")
            
        else:
            # 🚫 BLIP-2 N'A JAMAIS PARLÉ → Photo manquante
            current_state["photo"]["collected"] = False
            current_state["photo"]["data"] = None
            current_state["photo"]["source"] = "blip2_never_spoke"
            logger.info("🚫 [RECONCILER] BLIP-2 n'a jamais parlé → Photo manquante")
        
        # ========================================
        # 2. GESTION PAIEMENT
        # ========================================
        
        if ocr_result and ocr_result.get("valid"):
            # NOUVEAU paiement détecté
            new_amount = ocr_result.get("amount", 0)
            old_amount = notepad.get("paiement", {}).get("montant", 0) if notepad.get("paiement") else 0
            
            if old_amount and new_amount != old_amount:
                # Montant différent → Conflit potentiel
                current_state["paiement"]["collected"] = True
                current_state["paiement"]["data"] = new_amount
                current_state["paiement"]["source"] = "ocr_actuel"
                current_state["conflicts"].append({
                    "type": "payment_amount_change",
                    "old": old_amount,
                    "new": new_amount,
                    "message": f"Nouveau paiement détecté: {new_amount}F (précédent: {old_amount}F)"
                })
                logger.info(f"🔄 [RECONCILER] Changement paiement: {old_amount}F → {new_amount}F")
            else:
                # Premier paiement ou même montant
                current_state["paiement"]["collected"] = True
                current_state["paiement"]["data"] = new_amount
                current_state["paiement"]["source"] = "ocr_actuel"
                logger.info(f"✅ [RECONCILER] Paiement accepté: {new_amount}F")
        
        elif notepad.get("paiement"):
            # Pas de nouveau paiement → Vérifier âge
            payment_date = notepad.get("paiement", {}).get("date")
            if payment_date:
                try:
                    if isinstance(payment_date, str):
                        payment_datetime = datetime.fromisoformat(payment_date.replace('Z', '+00:00'))
                    else:
                        payment_datetime = payment_date
                    
                    age_minutes = (now - payment_datetime).total_seconds() / 60
                    
                    if age_minutes < 60:  # 1 heure max pour paiement
                        current_state["paiement"]["collected"] = True
                        current_state["paiement"]["data"] = notepad["paiement"].get("montant")
                        current_state["paiement"]["source"] = "notepad_recent"
                        logger.info(f"📋 [RECONCILER] Paiement notepad récent ({age_minutes:.1f}min)")
                    else:
                        # Paiement trop ancien → Expirer
                        current_state["paiement"]["collected"] = False
                        current_state["paiement"]["source"] = "notepad_expired"
                        logger.info(f"⏰ [RECONCILER] Paiement notepad expiré ({age_minutes:.1f}min)")
                except Exception as e:
                    logger.warning(f"⚠️ [RECONCILER] Erreur parsing date paiement: {e}")
                    current_state["paiement"]["collected"] = bool(notepad.get("paiement"))
                    current_state["paiement"]["data"] = notepad.get("paiement", {}).get("montant")
                    current_state["paiement"]["source"] = "notepad_fallback"
        
        # ========================================
        # 3. ZONE ET TÉLÉPHONE (notepad uniquement)
        # ========================================
        
        current_state["zone"]["collected"] = bool(notepad.get("delivery_zone"))
        current_state["zone"]["data"] = notepad.get("delivery_zone")
        current_state["zone"]["cost"] = notepad.get("delivery_cost", 1500)
        
        current_state["tel"]["collected"] = bool(notepad.get("phone_number"))
        current_state["tel"]["data"] = notepad.get("phone_number")
        current_state["tel"]["valid"] = IntelligentDataReconciler._validate_phone(notepad.get("phone_number"))
        
        return current_state
    
    @staticmethod
    def _validate_phone(phone: Optional[str]) -> bool:
        """Valide format téléphone (10 chiffres)"""
        if not phone:
            return False
        digits = ''.join(filter(str.isdigit, str(phone)))
        return len(digits) == 10 and digits.startswith('0')
    
    @staticmethod
    def generate_confirmation_message(confirmations: list) -> Optional[str]:
        """Génère un message de confirmation si nécessaire"""
        if not confirmations:
            return None
        
        # Prendre la première confirmation (priorité)
        confirmation = confirmations[0]
        return confirmation.get("message")
    
    @staticmethod
    def should_ask_confirmation(current_state: Dict[str, Any]) -> bool:
        """Détermine si une confirmation est nécessaire"""
        return len(current_state.get("confirmations_needed", [])) > 0

# Tests
if __name__ == "__main__":
    print("🧪 TESTS INTELLIGENT DATA RECONCILER")
    print("="*60)
    
    # Test 1: Changement de produit
    print("\n📍 TEST 1: Changement de produit")
    notepad = {
        "photo_produit": "a bag of diapers on white background",
        "photo_produit_date": datetime.now().isoformat()
    }
    vision_new = {
        "description": "a pack of baby wipes",
        "confidence": 0.90
    }
    
    change = IntelligentDataReconciler.detect_product_change(vision_new, notepad)
    print(f"Changement détecté: {change['changed']}")
    print(f"Action: {change['action']}")
    print(f"Similarité: {change.get('similarity', 'N/A')}")
    
    # Test 2: Réconciliation complète
    print("\n📍 TEST 2: Réconciliation complète")
    state = IntelligentDataReconciler.reconcile_data(vision_new, None, notepad)
    print(f"Photo collectée: {state['photo']['collected']}")
    print(f"Confirmations nécessaires: {len(state['confirmations_needed'])}")
    
    if state['confirmations_needed']:
        print(f"Message: {state['confirmations_needed'][0]['message'][:100]}...")
    
    print("\n✅ Tests terminés")
