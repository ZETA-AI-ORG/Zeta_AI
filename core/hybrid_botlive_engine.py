"""
🎯 MOTEUR HYBRIDE BOTLIVE - SYSTÈME PARALLÈLE
Architecture: Python (logique) + LLM (formulation)

SÉCURITÉ:
- Système complètement séparé
- Fallback automatique vers ancien système
- Rollback instantané via variable d'env
"""

import json
import logging
from typing import Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class HybridBotliveEngine:
    """
    Moteur hybride séparant logique (Python) et formulation (LLM)
    
    PRINCIPE:
    1. Python calcule l'état (photo, paiement, zone, tel)
    2. Python décide de l'action (ask_photo, ask_payment, etc.)
    3. LLM formule la réponse en style Jessica
    """
    
    def __init__(self):
        self.enabled = False  # Désactivé par défaut
        self.fallback_count = 0
        self.success_count = 0
        
        # Templates de secours (si LLM échoue)
        self.fallback_templates = {
            "ask_photo": "Envoyez-moi la photo du paquet s'il vous plaît 📦",
            "ask_payment": "Parfait ! Maintenant envoyez 2000F sur +225 0787360757, puis partagez la capture 💳",
            "ask_zone": "Dans quelle zone d'Abidjan êtes-vous ? 📍",
            "ask_tel": "Votre numéro de téléphone pour la livraison ? (10 chiffres) 📞",
            "ask_tel_invalid": "Le format n'est pas correct. Il me faut 10 chiffres (ex: 0787360757) 📞",
            "recap": "📦 {produit} | 📍 {zone} | 📞 {tel} | 💳 {montant}F\nTout est correct ? 😊",
            "validation": """✅ Parfait ! Votre commande est validée ! 🎉

📋 RÉCAPITULATIF:
📦 {produit}
🚚 Livraison {zone} - {frais}F
💳 Acompte: {montant}F
📞 Contact: {tel}
⏰ Livraison: {delai}

On vous rappelle très bientôt ! 😊

⚠️ NE PAS RÉPONDRE À CE MESSAGE ⚠️""",
            "hors_role": "Je m'occupe des nouvelles commandes. Pour le SAV, contactez +225 0787360757. Une nouvelle commande ? 😊",
            "negociation": "Désolée, l'acompte de 2000F est obligatoire. Souhaitez-vous continuer ? 😊"
        }
    
    def enable(self):
        """Active le moteur hybride"""
        self.enabled = True
        logger.info("🚀 [HYBRID] Moteur hybride ACTIVÉ")
    
    def disable(self):
        """Désactive le moteur hybride (rollback)"""
        self.enabled = False
        logger.warning("⚠️ [HYBRID] Moteur hybride DÉSACTIVÉ (rollback)")
    
    def is_enabled(self) -> bool:
        """Vérifie si le moteur est activé"""
        return self.enabled
    
    def get_stats(self) -> Dict[str, int]:
        """Retourne les statistiques d'utilisation"""
        return {
            "enabled": self.enabled,
            "success": self.success_count,
            "fallback": self.fallback_count,
            "total": self.success_count + self.fallback_count
        }
    
    def calculate_state(
        self,
        notepad: Dict[str, Any],
        vision_result: Optional[Dict[str, Any]],
        ocr_result: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calcule l'état de collecte (Python strict - jamais d'erreur)
        
        Returns:
            {
                "photo": bool,
                "paiement": bool,
                "zone": bool,
                "tel": bool,
                "tel_valid": bool,
                "details": {...}
            }
        """
        try:
            # Photo
            photo_ok = False
            photo_desc = None
            if vision_result:
                desc = vision_result.get("description", "")
                if desc and ("bag of" in desc.lower() or "diaper" in desc.lower() or "couche" in desc.lower()):
                    photo_ok = True
                    photo_desc = desc
            
            # Paiement
            paiement_ok = False
            montant = 0
            if ocr_result:
                paiement_ok = ocr_result.get("valid", False)
                montant = ocr_result.get("amount", 0)
            
            # Zone
            zone_ok = False
            zone = None
            if notepad.get("delivery_zone"):
                zone_ok = True
                zone = notepad.get("delivery_zone")
            
            # Téléphone
            tel_ok = False
            tel_valid = False
            tel = None
            if notepad.get("phone_number"):
                tel = notepad.get("phone_number")
                tel_ok = True
                # Validation format (10 chiffres)
                tel_clean = ''.join(filter(str.isdigit, str(tel)))
                tel_valid = len(tel_clean) == 10
            
            state = {
                "photo": photo_ok,
                "paiement": paiement_ok,
                "zone": zone_ok,
                "tel": tel_ok,
                "tel_valid": tel_valid,
                "details": {
                    "photo_desc": photo_desc,
                    "montant": montant,
                    "zone": zone,
                    "tel": tel
                }
            }
            
            logger.info(f"📊 [HYBRID] État calculé: {json.dumps(state, ensure_ascii=False)}")
            return state
            
        except Exception as e:
            logger.error(f"❌ [HYBRID] Erreur calcul état: {e}")
            # État par défaut (tout manquant)
            return {
                "photo": False,
                "paiement": False,
                "zone": False,
                "tel": False,
                "tel_valid": False,
                "details": {}
            }
    
    def decide_next_action(
        self,
        state: Dict[str, Any],
        message: str
    ) -> Dict[str, Any]:
        """
        Décide de la prochaine action (Python strict - jamais d'erreur)
        
        Returns:
            {
                "action": str,  # ask_photo, ask_payment, ask_zone, ask_tel, recap, validation, hors_role, negociation
                "priority": str,  # X/4 ou COMPLET ou BLOQUER ou HORS-RÔLE
                "reason": str
            }
        """
        try:
            message_lower = message.lower()
            
            # Détection hors-rôle (SAV, réclamation)
            hors_role_keywords = ["pas arrivé", "pas reçu", "problème", "réclamation", "sav", "retard"]
            if any(kw in message_lower for kw in hors_role_keywords):
                return {
                    "action": "hors_role",
                    "priority": "HORS-RÔLE",
                    "reason": "Question SAV détectée"
                }
            
            # Détection négociation prix
            negociation_keywords = ["1000f", "1500f", "moins cher", "réduction", "discount"]
            if any(kw in message_lower for kw in negociation_keywords):
                return {
                    "action": "negociation",
                    "priority": "BLOQUER",
                    "reason": "Tentative négociation acompte"
                }
            
            # Logique de collecte (ordre strict)
            if not state["photo"]:
                return {
                    "action": "ask_photo",
                    "priority": "1/4",
                    "reason": "Photo manquante"
                }
            
            if not state["paiement"]:
                return {
                    "action": "ask_payment",
                    "priority": "2/4",
                    "reason": "Paiement manquant"
                }
            
            if not state["zone"]:
                return {
                    "action": "ask_zone",
                    "priority": "3/4",
                    "reason": "Zone manquante"
                }
            
            if not state["tel"]:
                return {
                    "action": "ask_tel",
                    "priority": "4/4",
                    "reason": "Téléphone manquant"
                }
            
            # Téléphone invalide (format)
            if state["tel"] and not state["tel_valid"]:
                return {
                    "action": "ask_tel_invalid",
                    "priority": "BLOQUER",
                    "reason": "Format téléphone invalide"
                }
            
            # Tout collecté → Récap ou validation
            if "oui" in message_lower or "confirme" in message_lower or "ok" in message_lower:
                return {
                    "action": "validation",
                    "priority": "FINALISER",
                    "reason": "Confirmation reçue"
                }
            else:
                return {
                    "action": "recap",
                    "priority": "COMPLET (4/4)",
                    "reason": "Tout collecté, attente confirmation"
                }
        
        except Exception as e:
            logger.error(f"❌ [HYBRID] Erreur décision action: {e}")
            # Action par défaut (demander photo)
            return {
                "action": "ask_photo",
                "priority": "1/4",
                "reason": "Erreur décision, restart"
            }
    
    def format_response_with_llm(
        self,
        action: str,
        state: Dict[str, Any],
        llm_function: callable
    ) -> str:
        """
        Formule la réponse via LLM (avec fallback template)
        
        Args:
            action: Action à formuler
            state: État actuel
            llm_function: Fonction LLM à appeler
        
        Returns:
            Réponse formatée
        """
        try:
            # Prompt minimal pour LLM
            prompt = self._build_minimal_prompt(action, state)
            
            # Appel LLM
            response = llm_function(prompt)
            
            # Validation longueur (max 15 mots sauf recap/validation)
            if action not in ["recap", "validation"]:
                word_count = len(response.split())
                if word_count > 20:
                    logger.warning(f"⚠️ [HYBRID] Réponse LLM trop longue ({word_count} mots), fallback template")
                    return self._get_fallback_template(action, state)
            
            self.success_count += 1
            logger.info(f"✅ [HYBRID] LLM formulation OK: {response[:100]}...")
            return response
        
        except Exception as e:
            logger.error(f"❌ [HYBRID] Erreur LLM formulation: {e}")
            self.fallback_count += 1
            return self._get_fallback_template(action, state)
    
    def _build_minimal_prompt(self, action: str, state: Dict[str, Any]) -> str:
        """Construit un prompt minimal pour le LLM"""
        
        action_descriptions = {
            "ask_photo": "Demander la photo du produit",
            "ask_payment": "Demander le paiement (2000F sur +225 0787360757)",
            "ask_zone": "Demander la zone de livraison",
            "ask_tel": "Demander le numéro de téléphone (10 chiffres)",
            "ask_tel_invalid": "Rejeter téléphone invalide, exiger 10 chiffres",
            "recap": "Récapitulatif commande, demander confirmation",
            "validation": "Message de validation finale",
            "hors_role": "Rediriger vers SAV +225 0787360757",
            "negociation": "Refuser négociation, rappeler 2000F minimum"
        }
        
        prompt = f"""Tu es Jessica, assistante commerciale.

ACTION: {action_descriptions.get(action, action)}
ÉTAT: {json.dumps(state, ensure_ascii=False)}

RÈGLES:
- Style direct, courtois
- Max 15 mots (sauf recap/validation)
- 1 question par message

RÉPONSE:"""
        
        return prompt
    
    def _get_fallback_template(self, action: str, state: Dict[str, Any]) -> str:
        """Retourne le template de secours"""
        
        template = self.fallback_templates.get(action, "Envoyez photo du paquet 📦")
        
        # Remplacement variables si nécessaire
        if action in ["recap", "validation"]:
            details = state.get("details", {})
            template = template.format(
                zone=details.get("zone", "N/A"),
                tel=details.get("tel", "N/A"),
                montant=details.get("montant", 2000),
                prix="N/A",
                frais=1500,
                delai="demain"
            )
        
        logger.info(f"🔄 [HYBRID] Fallback template utilisé: {action}")
        return template
    
    def process_message(
        self,
        message: str,
        notepad: Dict[str, Any],
        vision_result: Optional[Dict[str, Any]],
        ocr_result: Optional[Dict[str, Any]],
        llm_function: callable
    ) -> Dict[str, Any]:
        """
        Point d'entrée principal du moteur hybride
        
        Returns:
            {
                "response": str,
                "state": dict,
                "action": dict,
                "source": str  # "hybrid" ou "fallback"
            }
        """
        try:
            # 1. Calculer l'état (Python strict)
            state = self.calculate_state(notepad, vision_result, ocr_result)
            
            # 2. Décider de l'action (Python strict)
            action = self.decide_next_action(state, message)
            
            # 3. Formuler la réponse (LLM + fallback)
            response = self.format_response_with_llm(
                action["action"],
                state,
                llm_function
            )
            
            return {
                "response": response,
                "state": state,
                "action": action,
                "source": "hybrid",
                "stats": self.get_stats()
            }
        
        except Exception as e:
            logger.error(f"❌ [HYBRID] Erreur critique: {e}")
            # Fallback complet
            return {
                "response": "Envoyez photo du paquet 📦",
                "state": {"photo": False, "paiement": False, "zone": False, "tel": False},
                "action": {"action": "ask_photo", "priority": "1/4", "reason": "Erreur système"},
                "source": "fallback_critical",
                "stats": self.get_stats()
            }


# Instance globale (singleton)
_hybrid_engine = None

def get_hybrid_engine() -> HybridBotliveEngine:
    """Retourne l'instance singleton du moteur hybride"""
    global _hybrid_engine
    if _hybrid_engine is None:
        _hybrid_engine = HybridBotliveEngine()
    return _hybrid_engine
