#!/usr/bin/env python3
"""
🔄 SYSTÈME DE HANDOFF INTELLIGENT RAG ↔ BOTLIVE
================================================

Architecture:
1. RAG NORMAL détecte besoin validation paiement
2. HANDOFF vers Botlive (OCR + BLIP-2)
3. Botlive valide et retourne résultat
4. RAG NORMAL reprend avec confirmation

"""
import sys
import os
from typing import Dict, Any, Optional

# Ajouter le répertoire parent au path pour imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from utils import log3
except ImportError:
    # Fallback si utils non disponible
    def log3(tag, message):
        print(f"[{tag}] {message}")


class RAGBotliveHandoff:
    """
    Gestionnaire de handoff entre RAG Normal et Botlive
    """
    
    def __init__(self):
        self.handoff_active = False
        self.waiting_for_payment_proof = False
        
    def should_handoff_to_botlive(
        self,
        user_message: str,
        thinking_data: Dict[str, Any],
        has_image: bool
    ) -> bool:
        """
        Détermine si on doit passer la main à Botlive
        
        Args:
            user_message: Message utilisateur
            thinking_data: Données du <thinking> LLM
            has_image: True si image attachée
            
        Returns:
            True si handoff nécessaire
        """
        # Cas 1: Image envoyée alors qu'on attend une preuve de paiement
        if has_image and self.waiting_for_payment_proof:
            log3("[HANDOFF]", "✅ Image détectée + attente paiement → HANDOFF vers Botlive")
            return True
        
        # Cas 2: LLM demande explicitement une preuve de paiement
        if thinking_data:
            prochaine_etape = thinking_data.get("prochaine_etape", "")
            if "paiement" in prochaine_etape.lower() or "dépôt" in prochaine_etape.lower():
                self.waiting_for_payment_proof = True
                log3("[HANDOFF]", "⏳ RAG demande preuve paiement → En attente image")
        
        # Cas 3: Image envoyée + mots-clés paiement dans message
        if has_image:
            payment_keywords = ["envoyé", "payé", "dépôt", "wave", "orange", "mtn", "moov"]
            if any(kw in user_message.lower() for kw in payment_keywords):
                log3("[HANDOFF]", "✅ Image + mots-clés paiement → HANDOFF vers Botlive")
                return True
        
        return False
    
    def format_botlive_result_for_rag(
        self,
        botlive_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Formate le résultat Botlive pour injection dans le RAG
        
        Args:
            botlive_result: Résultat brut de Botlive
            
        Returns:
            Format standardisé pour RAG
        """
        # Extraire les données importantes
        payment_data = botlive_result.get("payment_data", {})
        validation = botlive_result.get("validation", {})
        
        # Format pour injection dans le contexte RAG
        formatted = {
            "paiement_status": "validé" if validation.get("is_valid") else "rejeté",
            "montant_detecte": payment_data.get("amount"),
            "operateur": payment_data.get("operator", "Wave"),
            "numero_transaction": payment_data.get("transaction_id"),
            "confiance_ocr": payment_data.get("confidence", 0),
            "message_confirmation": self._generate_confirmation_message(
                validation.get("is_valid"),
                payment_data.get("amount"),
                payment_data.get("operator")
            )
        }
        
        log3("[HANDOFF]", f"📦 Résultat Botlive formaté: {formatted}")
        
        # Réinitialiser l'attente
        self.waiting_for_payment_proof = False
        
        return formatted
    
    def _generate_confirmation_message(
        self,
        is_valid: bool,
        amount: Optional[float],
        operator: Optional[str]
    ) -> str:
        """
        Génère message de confirmation pour le RAG
        
        Returns:
            Message à injecter dans le contexte
        """
        if is_valid:
            return (
                f"✅ PAIEMENT VALIDÉ: {amount} FCFA via {operator or 'Wave'} "
                f"détecté et vérifié par le système OCR. "
                f"Le dépôt est confirmé, tu peux continuer la qualification."
            )
        else:
            return (
                f"❌ PAIEMENT NON VALIDÉ: "
                f"Le montant détecté ({amount} FCFA) ne correspond pas à l'acompte attendu (2000 FCFA) "
                f"ou le screenshot n'est pas lisible. "
                f"Demande au client de renvoyer une capture claire."
            )
    
    def inject_payment_confirmation_in_context(
        self,
        current_context: str,
        botlive_result: Dict[str, Any]
    ) -> str:
        """
        Injecte la confirmation de paiement dans le contexte RAG
        
        Args:
            current_context: Contexte actuel du RAG
            botlive_result: Résultat formaté de Botlive
            
        Returns:
            Contexte enrichi
        """
        confirmation_block = f"""

📋 VALIDATION PAIEMENT (Botlive OCR):
{botlive_result['message_confirmation']}

Détails techniques:
- Montant: {botlive_result['montant_detecte']} FCFA
- Opérateur: {botlive_result['operateur']}
- Confiance OCR: {botlive_result['confiance_ocr']}%
- Status: {botlive_result['paiement_status'].upper()}

"""
        
        # Injecter au début du contexte pour que le LLM le voie en premier
        enriched_context = confirmation_block + current_context
        
        log3("[HANDOFF]", f"✅ Contexte enrichi avec validation paiement ({len(confirmation_block)} chars)")
        
        return enriched_context


# ============================================================================
# SINGLETON
# ============================================================================

_handoff_manager = None

def get_handoff_manager() -> RAGBotliveHandoff:
    """Retourne l'instance singleton du gestionnaire de handoff"""
    global _handoff_manager
    if _handoff_manager is None:
        _handoff_manager = RAGBotliveHandoff()
    return _handoff_manager


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def should_activate_botlive(
    user_message: str,
    thinking_data: Dict[str, Any],
    has_image: bool
) -> bool:
    """
    Point d'entrée simple pour vérifier si Botlive doit être activé
    
    Usage dans universal_rag_engine.py:
        if should_activate_botlive(message, thinking, bool(images)):
            # Appeler Botlive
    """
    manager = get_handoff_manager()
    return manager.should_handoff_to_botlive(user_message, thinking_data, has_image)


def format_botlive_for_rag(botlive_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formate résultat Botlive pour RAG
    
    Usage:
        formatted = format_botlive_for_rag(botlive_raw_result)
    """
    manager = get_handoff_manager()
    return manager.format_botlive_result_for_rag(botlive_result)


def inject_payment_in_context(context: str, botlive_result: Dict[str, Any]) -> str:
    """
    Injecte validation paiement dans contexte RAG
    
    Usage:
        enriched_context = inject_payment_in_context(current_context, botlive_result)
    """
    manager = get_handoff_manager()
    return manager.inject_payment_confirmation_in_context(context, botlive_result)


if __name__ == "__main__":
    # Test du système
    print("🧪 TEST HANDOFF SYSTEM\n")
    
    manager = RAGBotliveHandoff()
    
    # Test 1: Détection besoin paiement
    print("Test 1: LLM demande preuve paiement")
    thinking = {"prochaine_etape": "Demander dépôt Wave"}
    result = manager.should_handoff_to_botlive("Ok", thinking, False)
    print(f"   → Handoff: {result} (attendu: False, mais waiting_for_payment activé)\n")
    
    # Test 2: Image envoyée après demande
    print("Test 2: Client envoie image après demande")
    result = manager.should_handoff_to_botlive("J'ai envoyé", {}, True)
    print(f"   → Handoff: {result} (attendu: True)\n")
    
    # Test 3: Formatage résultat Botlive
    print("Test 3: Formatage résultat Botlive")
    botlive_raw = {
        "payment_data": {
            "amount": 2000,
            "operator": "Wave",
            "confidence": 95
        },
        "validation": {
            "is_valid": True
        }
    }
    formatted = manager.format_botlive_result_for_rag(botlive_raw)
    print(f"   → Status: {formatted['paiement_status']}")
    print(f"   → Message: {formatted['message_confirmation'][:80]}...\n")
    
    print("✅ Tests terminés!")
