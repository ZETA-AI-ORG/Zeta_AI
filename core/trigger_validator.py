#!/usr/bin/env python3
"""
🛡️ VALIDATEUR DE DÉCLENCHEURS
=============================

Valide que les 4 déclencheurs envoient toujours des données complètes et cohérentes
à Python pour garantir des réponses intelligentes dans tous les cas.

OBJECTIF: Sécurité et robustesse maximale pour la production.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class TriggerValidator:
    """Validateur pour s'assurer que les déclencheurs envoient des données complètes"""
    
    @staticmethod
    def validate_photo_trigger(trigger_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valide les données du déclencheur PHOTO_PRODUIT
        
        Returns:
            Dict avec 'valid', 'errors', 'warnings'
        """
        errors = []
        warnings = []
        
        # Vérifier structure de base
        if not isinstance(trigger_data, dict):
            errors.append("trigger_data doit être un dictionnaire")
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        # Champs obligatoires
        required_fields = ["description", "confidence", "error", "valid", "product_detected"]
        for field in required_fields:
            if field not in trigger_data:
                errors.append(f"Champ obligatoire manquant: {field}")
        
        # Validation des types
        if "confidence" in trigger_data:
            confidence = trigger_data["confidence"]
            if not isinstance(confidence, (int, float)) or not (0 <= confidence <= 1):
                errors.append("confidence doit être un nombre entre 0 et 1")
        
        if "valid" in trigger_data and not isinstance(trigger_data["valid"], bool):
            errors.append("valid doit être un booléen")
        
        if "product_detected" in trigger_data and not isinstance(trigger_data["product_detected"], bool):
            errors.append("product_detected doit être un booléen")
        
        # Cohérence logique
        if trigger_data.get("error") and trigger_data.get("valid"):
            warnings.append("Incohérence: error présent mais valid=True")
        
        if trigger_data.get("confidence", 0) > 0.8 and not trigger_data.get("product_detected"):
            warnings.append("Incohérence: confiance élevée mais product_detected=False")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    @staticmethod
    def validate_paiement_trigger(trigger_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valide les données du déclencheur PAIEMENT_OCR
        
        Returns:
            Dict avec 'valid', 'errors', 'warnings'
        """
        errors = []
        warnings = []
        
        # Vérifier structure de base
        if not isinstance(trigger_data, dict):
            errors.append("trigger_data doit être un dictionnaire")
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        # Champs obligatoires
        required_fields = ["amount", "valid", "error", "currency", "transactions", "raw_text", "sufficient"]
        for field in required_fields:
            if field not in trigger_data:
                errors.append(f"Champ obligatoire manquant: {field}")
        
        # Validation des types
        if "amount" in trigger_data:
            amount = trigger_data["amount"]
            if not isinstance(amount, (int, float)) or amount < 0:
                errors.append("amount doit être un nombre positif")
        
        if "valid" in trigger_data and not isinstance(trigger_data["valid"], bool):
            errors.append("valid doit être un booléen")
        
        if "sufficient" in trigger_data and not isinstance(trigger_data["sufficient"], bool):
            errors.append("sufficient doit être un booléen")
        
        if "transactions" in trigger_data and not isinstance(trigger_data["transactions"], list):
            errors.append("transactions doit être une liste")
        
        # Cohérence logique
        amount = trigger_data.get("amount", 0)
        sufficient = trigger_data.get("sufficient", False)
        
        if amount >= 2000 and not sufficient:
            warnings.append("Incohérence: amount >= 2000 mais sufficient=False")
        
        if amount < 2000 and sufficient:
            warnings.append("Incohérence: amount < 2000 mais sufficient=True")
        
        if trigger_data.get("error") and trigger_data.get("valid"):
            warnings.append("Incohérence: error présent mais valid=True")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    @staticmethod
    def validate_zone_trigger(trigger_data: Any) -> Dict[str, Any]:
        """
        Valide les données du déclencheur ZONE_DETECTEE
        
        Returns:
            Dict avec 'valid', 'errors', 'warnings'
        """
        errors = []
        warnings = []
        
        # Accepter string pour compatibilité (fallback)
        if isinstance(trigger_data, str):
            if len(trigger_data.strip()) == 0:
                errors.append("Zone string ne peut pas être vide")
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": ["Format string détecté (fallback mode)"]
            }
        
        # Format dict (mode normal)
        if not isinstance(trigger_data, dict):
            errors.append("trigger_data doit être un dictionnaire ou string")
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        # Champs obligatoires
        required_fields = ["zone", "cost", "category", "name", "source", "confidence"]
        for field in required_fields:
            if field not in trigger_data:
                errors.append(f"Champ obligatoire manquant: {field}")
        
        # Validation des types
        if "cost" in trigger_data:
            cost = trigger_data["cost"]
            if not isinstance(cost, (int, float)) or cost <= 0:
                errors.append("cost doit être un nombre positif")
        
        if "category" in trigger_data:
            category = trigger_data["category"]
            valid_categories = ["centrale", "peripherique", "expedition"]
            if category not in valid_categories:
                errors.append(f"category doit être dans {valid_categories}")
        
        # Cohérence logique
        cost = trigger_data.get("cost", 0)
        category = trigger_data.get("category", "")
        
        if category == "centrale" and cost != 1500:
            warnings.append("Incohérence: zone centrale mais cost != 1500")
        
        if category == "peripherique" and cost not in [2000, 2500]:
            warnings.append("Incohérence: zone périphérique mais cost pas dans [2000, 2500]")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    @staticmethod
    def validate_telephone_trigger(trigger_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valide les données du déclencheur TELEPHONE
        
        Returns:
            Dict avec 'valid', 'errors', 'warnings'
        """
        errors = []
        warnings = []
        
        # Vérifier structure de base
        if not isinstance(trigger_data, dict):
            errors.append("trigger_data doit être un dictionnaire")
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        # Champs obligatoires
        required_fields = ["raw", "clean", "valid", "length", "format_error"]
        for field in required_fields:
            if field not in trigger_data:
                errors.append(f"Champ obligatoire manquant: {field}")
        
        # Validation des types
        if "valid" in trigger_data and not isinstance(trigger_data["valid"], bool):
            errors.append("valid doit être un booléen")
        
        if "length" in trigger_data:
            length = trigger_data["length"]
            if not isinstance(length, int) or length < 0:
                errors.append("length doit être un entier positif")
        
        # Cohérence logique
        valid = trigger_data.get("valid", False)
        length = trigger_data.get("length", 0)
        format_error = trigger_data.get("format_error")
        clean = trigger_data.get("clean", "")
        
        if valid and format_error:
            warnings.append("Incohérence: valid=True mais format_error présent")
        
        if not valid and not format_error:
            warnings.append("Incohérence: valid=False mais pas de format_error")
        
        if length == 10 and clean and not clean.startswith('0') and not format_error:
            warnings.append("Incohérence: numéro 10 chiffres ne commence pas par 0 mais pas d'erreur")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    @classmethod
    def validate_trigger(cls, trigger_type: str, trigger_data: Any) -> Dict[str, Any]:
        """
        Valide un déclencheur selon son type
        
        Args:
            trigger_type: Type de déclencheur
            trigger_data: Données du déclencheur
            
        Returns:
            Dict avec résultat de validation
        """
        validators = {
            "photo_produit": cls.validate_photo_trigger,
            "paiement_ocr": cls.validate_paiement_trigger,
            "zone_detectee": cls.validate_zone_trigger,
            "telephone_detecte": cls.validate_telephone_trigger,
            "telephone_final": cls.validate_telephone_trigger
        }
        
        if trigger_type not in validators:
            return {
                "valid": False,
                "errors": [f"Type de déclencheur inconnu: {trigger_type}"],
                "warnings": []
            }
        
        try:
            result = validators[trigger_type](trigger_data)
            
            # Log des résultats
            if not result["valid"]:
                logger.error(f"❌ Validation échouée pour {trigger_type}: {result['errors']}")
            elif result["warnings"]:
                logger.warning(f"⚠️ Avertissements pour {trigger_type}: {result['warnings']}")
            else:
                logger.info(f"✅ Validation réussie pour {trigger_type}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur validation {trigger_type}: {e}")
            return {
                "valid": False,
                "errors": [f"Erreur interne validation: {str(e)}"],
                "warnings": []
            }

def validate_trigger_before_python(trigger_type: str, trigger_data: Any) -> bool:
    """
    Fonction utilitaire pour valider un déclencheur avant de l'envoyer à Python
    
    Args:
        trigger_type: Type de déclencheur
        trigger_data: Données du déclencheur
        
    Returns:
        True si valide, False sinon
    """
    result = TriggerValidator.validate_trigger(trigger_type, trigger_data)
    
    if not result["valid"]:
        logger.error(f"🚫 Déclencheur {trigger_type} invalide - Python ne recevra pas de données cohérentes")
        logger.error(f"   Erreurs: {result['errors']}")
        return False
    
    if result["warnings"]:
        logger.warning(f"⚠️ Déclencheur {trigger_type} avec avertissements: {result['warnings']}")
    
    return True

# Tests unitaires
if __name__ == "__main__":
    print("🧪 TESTS DU VALIDATEUR DE DÉCLENCHEURS")
    print("="*60)
    
    # Test photo valide
    photo_data = {
        "description": "a bag of diapers",
        "confidence": 0.90,
        "error": None,
        "valid": True,
        "product_detected": True
    }
    result = TriggerValidator.validate_photo_trigger(photo_data)
    print(f"Photo valide: {result}")
    
    # Test paiement invalide
    paiement_data = {
        "amount": 1500,
        "valid": True,
        "error": None,
        "currency": "FCFA",
        "transactions": [],
        "raw_text": "",
        "sufficient": True  # Incohérent !
    }
    result = TriggerValidator.validate_paiement_trigger(paiement_data)
    print(f"Paiement incohérent: {result}")
    
    print("\n✅ Tests terminés")
