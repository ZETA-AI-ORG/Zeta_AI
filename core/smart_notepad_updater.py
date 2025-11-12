#!/usr/bin/env python3
"""
🧠 SMART NOTEPAD UPDATER
========================

Gère intelligemment les changements d'avis des clients en temps réel.
Met à jour le notepad quand de nouvelles données sont détectées.

OBJECTIF: Éviter les incohérences quand le client change d'avis.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class SmartNotepadUpdater:
    """Gestionnaire intelligent des mises à jour notepad"""
    
    @staticmethod
    def should_update_photo(vision_result: Optional[Dict], notepad: Dict) -> bool:
        """Détermine si la photo doit être mise à jour"""
        
        if not vision_result or not vision_result.get("description"):
            return False
        
        # Nouvelle photo produit détectée
        new_desc = vision_result["description"]
        is_new_product = any(kw in new_desc.lower() for kw in ["bag", "diaper", "couche", "paquet", "wipe", "lingette"])
        
        if not is_new_product:
            return False
        
        # Pas d'ancienne photo → Mise à jour
        if not notepad.get("photo_produit"):
            logger.info("📸 [SMART] Première photo produit détectée")
            return True
        
        # Photo différente → Changement d'avis détecté
        old_desc = notepad.get("photo_produit", "")
        if new_desc != old_desc:
            logger.info(f"🔄 [SMART] Changement photo détecté: '{old_desc[:30]}...' → '{new_desc[:30]}...'")
            return True
        
        # Photo ancienne (> 10 min) → Rafraîchir
        photo_date = notepad.get("photo_produit_date")
        if photo_date:
            try:
                if isinstance(photo_date, str):
                    photo_datetime = datetime.fromisoformat(photo_date)
                else:
                    photo_datetime = photo_date
                
                if datetime.now() - photo_datetime > timedelta(minutes=10):
                    logger.info("⏰ [SMART] Photo ancienne (>10min), rafraîchissement")
                    return True
            except:
                pass
        
        return False
    
    @staticmethod
    def should_update_payment(ocr_result: Optional[Dict], notepad: Dict) -> bool:
        """Détermine si le paiement doit être mis à jour"""
        
        if not ocr_result or not ocr_result.get("valid"):
            return False
        
        new_amount = ocr_result.get("amount", 0)
        
        # Pas d'ancien paiement → Mise à jour
        if not notepad.get("paiement"):
            logger.info(f"💳 [SMART] Premier paiement détecté: {new_amount}F")
            return True
        
        # Montant différent → Changement détecté
        old_amount = notepad.get("paiement", {}).get("montant", 0)
        if new_amount != old_amount:
            logger.info(f"🔄 [SMART] Changement paiement détecté: {old_amount}F → {new_amount}F")
            return True
        
        # Paiement ancien (> 5 min) → Rafraîchir
        payment_date = notepad.get("paiement", {}).get("date")
        if payment_date:
            try:
                if isinstance(payment_date, str):
                    payment_datetime = datetime.fromisoformat(payment_date)
                else:
                    payment_datetime = payment_date
                
                if datetime.now() - payment_datetime > timedelta(minutes=5):
                    logger.info("⏰ [SMART] Paiement ancien (>5min), rafraîchissement")
                    return True
            except:
                pass
        
        return False
    
    @staticmethod
    def update_notepad_smart(
        vision_result: Optional[Dict],
        ocr_result: Optional[Dict],
        notepad: Dict,
        user_id: str,
        company_id: str
    ) -> Dict[str, Any]:
        """
        Met à jour intelligemment le notepad selon les nouvelles données
        
        Returns:
            Dict avec les changements détectés
        """
        changes = {
            "photo_updated": False,
            "payment_updated": False,
            "changes_detected": []
        }
        
        current_time = datetime.now().isoformat()
        
        # ✅ MISE À JOUR PHOTO
        if SmartNotepadUpdater.should_update_photo(vision_result, notepad):
            old_photo = notepad.get("photo_produit", "Aucune")
            new_photo = vision_result["description"]
            
            # Sauvegarder dans notepad
            try:
                from core.persistent_collector import get_collector
                collector = get_collector()
                collector.update_photo_product(user_id, company_id, new_photo)
                
                changes["photo_updated"] = True
                changes["changes_detected"].append(f"Photo: '{old_photo[:30]}...' → '{new_photo[:30]}...'")
                logger.info(f"✅ [SMART] Photo mise à jour pour {user_id}")
                
            except Exception as e:
                logger.error(f"❌ [SMART] Erreur mise à jour photo: {e}")
        
        # ✅ MISE À JOUR PAIEMENT
        if SmartNotepadUpdater.should_update_payment(ocr_result, notepad):
            old_amount = notepad.get("paiement", {}).get("montant", 0)
            new_amount = ocr_result["amount"]
            
            # Sauvegarder dans notepad
            try:
                from core.persistent_collector import get_collector
                collector = get_collector()
                collector.update_payment(user_id, company_id, new_amount, "Wave", "+225 0787360757")
                
                changes["payment_updated"] = True
                changes["changes_detected"].append(f"Paiement: {old_amount}F → {new_amount}F")
                logger.info(f"✅ [SMART] Paiement mis à jour pour {user_id}")
                
            except Exception as e:
                logger.error(f"❌ [SMART] Erreur mise à jour paiement: {e}")
        
        return changes
    
    @staticmethod
    def detect_client_confusion(notepad: Dict, message: str) -> Optional[str]:
        """Détecte si le client semble confus par des données obsolètes"""
        
        message_lower = message.lower()
        
        # Client mentionne un produit différent de celui enregistré
        if notepad.get("photo_produit"):
            recorded_product = notepad["photo_produit"].lower()
            
            # Mots-clés produits
            if "couche" in message_lower and "lingette" in recorded_product:
                return "Vous parlez de couches mais j'ai enregistré des lingettes. Voulez-vous changer ?"
            elif "lingette" in message_lower and "couche" in recorded_product:
                return "Vous parlez de lingettes mais j'ai enregistré des couches. Voulez-vous changer ?"
        
        # Client mentionne un montant différent
        if notepad.get("paiement"):
            recorded_amount = notepad["paiement"].get("montant", 0)
            
            import re
            amounts_in_message = re.findall(r'(\d+)\s*f', message_lower)
            for amount_str in amounts_in_message:
                try:
                    amount = int(amount_str)
                    if amount != recorded_amount and amount > 1000:
                        return f"Vous mentionnez {amount}F mais j'ai enregistré {recorded_amount}F. Lequel est correct ?"
                except:
                    pass
        
        return None

def integrate_smart_updates():
    """Guide d'intégration dans le système principal"""
    
    integration_code = '''
    # Dans app.py, après analyse vision/OCR :
    
    from core.smart_notepad_updater import SmartNotepadUpdater
    
    # Mettre à jour le notepad intelligemment
    changes = SmartNotepadUpdater.update_notepad_smart(
        vision_result, ocr_result, notepad_data, user_id, company_id
    )
    
    # Détecter confusion client
    confusion = SmartNotepadUpdater.detect_client_confusion(notepad_data, message)
    if confusion:
        # Demander clarification avant de continuer
        return {"response": confusion, "source": "smart_clarification"}
    
    # Informer des changements détectés
    if changes["changes_detected"]:
        logger.info(f"🔄 [SMART] Changements: {changes['changes_detected']}")
    '''
    
    return integration_code

# Tests
if __name__ == "__main__":
    print("🧪 TESTS SMART NOTEPAD UPDATER")
    print("="*50)
    
    # Test changement photo
    notepad = {"photo_produit": "a bag of diapers", "photo_produit_date": "2025-11-12T09:00:00"}
    vision_new = {"description": "a pack of baby wipes", "confidence": 0.90}
    
    should_update = SmartNotepadUpdater.should_update_photo(vision_new, notepad)
    print(f"Changement photo détecté: {should_update}")
    
    # Test changement paiement
    notepad_payment = {"paiement": {"montant": 2000, "date": "2025-11-12T09:00:00"}}
    ocr_new = {"valid": True, "amount": 2500}
    
    should_update_payment = SmartNotepadUpdater.should_update_payment(ocr_new, notepad_payment)
    print(f"Changement paiement détecté: {should_update_payment}")
    
    # Test détection confusion
    confusion = SmartNotepadUpdater.detect_client_confusion(
        {"photo_produit": "diapers"}, 
        "Je veux des lingettes finalement"
    )
    print(f"Confusion détectée: {confusion}")
    
    print("✅ Tests terminés")
