#!/usr/bin/env python3
"""
💰 PAYMENT VALIDATOR - Validation automatique des paiements
Calcule et valide les paiements avec accumulation intelligente
"""

import re
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

def validate_payment_cumulative(
    current_transactions: List[Dict],
    conversation_history: str,
    required_amount: int = 2000
) -> Dict[str, Any]:
    """
    Valide paiement en cumulant TOUS les paiements de l'historique.
    
    Args:
        current_transactions: Nouvelles transactions détectées par OCR
        conversation_history: Historique conversation pour extraire anciens paiements
        required_amount: Montant requis en FCFA (dynamique, extrait de la config entreprise)
    
    Returns:
        {
            'valid': bool,
            'status': 'VALID' | 'INSUFFICIENT' | 'REFUSED' | 'NONE',
            'required_amount': int,
            'total_received': int,
            'payments_history': [202, 1800],
            'current_payment': int,
            'difference': int,
            'message': str
        }
    """
    
    logger.info(f"💰 Validation paiement - Acompte requis: {required_amount} FCFA")
    
    # 1. EXTRAIRE ANCIENS PAIEMENTS DE L'HISTORIQUE
    previous_payments = extract_previous_payments(conversation_history)
    
    # 2. AJOUTER NOUVEAU PAIEMENT
    current_payment = 0
    if current_transactions and len(current_transactions) > 0:
        current_payment = current_transactions[0].get('amount', 0)
    
    # 3. CALCULER TOTAL CUMULÉ
    all_payments = previous_payments + ([current_payment] if current_payment > 0 else [])
    total_received = sum(all_payments)
    
    # 4. PROTECTION ANTI-FRAUDE
    if len(all_payments) > 3:
        logger.warning(f"⚠️ Trop de paiements fragmentés: {len(all_payments)}")
        return {
            'valid': False,
            'status': 'REFUSED',
            'required_amount': required_amount,
            'total_received': total_received,
            'payments_history': all_payments,
            'current_payment': current_payment,
            'difference': total_received - required_amount,
            'message': "⚠️ Trop de paiements fragmentés. Envoie un seul paiement de 2000 FCFA minimum."
        }
    
    if current_payment > 0 and (current_payment < 50 or current_payment > 100000):
        logger.warning(f"⚠️ Montant suspect: {current_payment}")
        return {
            'valid': False,
            'status': 'REFUSED',
            'required_amount': required_amount,
            'total_received': 0,
            'payments_history': [],
            'current_payment': current_payment,
            'difference': -required_amount,
            'message': f"⚠️ Montant invalide détecté ({current_payment} FCFA). Vérifie ton capture de paiement."
        }
    
    # 5. CALCULER DIFFÉRENCE
    difference = total_received - required_amount
    
    # 6. GÉNÉRER MESSAGE
    if len(all_payments) == 0:
        return {
            'valid': False,
            'status': 'NONE',
            'required_amount': required_amount,
            'total_received': 0,
            'payments_history': [],
            'current_payment': 0,
            'difference': -required_amount,
            'message': f"Aucun paiement détecté. Dépôt requis: {required_amount} FCFA"
        }
    
    if difference >= 0:
        # ✅ PAIEMENT COMPLET
        if len(all_payments) > 1:
            # Paiement multiple
            payments_list = " + ".join([f"{p} FCFA" for p in all_payments])
            message = f"✅ Dépôt complet validé ! Total: {total_received} FCFA ({payments_list})"
        else:
            # Paiement unique
            message = f"✅ Dépôt validé {total_received} FCFA"
        
        logger.info(f"💰 {message}")
        
        return {
            'valid': True,
            'status': 'VALID',
            'required_amount': required_amount,
            'total_received': total_received,
            'payments_history': all_payments,
            'current_payment': current_payment,
            'difference': difference,
            'message': message
        }
    else:
        # ❌ PAIEMENT INSUFFISANT
        manque = abs(difference)
        
        if len(all_payments) > 1:
            # Déjà reçu des paiements avant
            payments_list = " + ".join([f"{p} FCFA" for p in all_payments])
            message = f"❌ Total reçu: {total_received} FCFA ({payments_list}). Il manque encore {manque} FCFA"
        else:
            # Premier paiement
            message = f"❌ Paiement insuffisant ! Client a envoyé {total_received} FCFA mais il manque encore {manque} FCFA"
        
        logger.info(f"💰 {message}")
        
        return {
            'valid': False,
            'status': 'INSUFFICIENT',
            'required_amount': required_amount,
            'total_received': total_received,
            'payments_history': all_payments,
            'current_payment': current_payment,
            'difference': difference,
            'message': message
        }

def extract_previous_payments(conversation_history: str) -> List[int]:
    """
    Extrait tous les montants de paiement déjà mentionnés dans l'historique.
    
    Args:
        conversation_history: Historique conversation
    
    Returns:
        Liste des montants détectés (dédupliqués)
    """
    if not conversation_history or len(conversation_history.strip()) == 0:
        return []
    
    previous_payments = []
    
    # Patterns pour détecter paiements REÇUS (pas les montants manquants)
    payment_patterns = [
        r'(?<!manque\s)(?<!manque encore\s)(?<!il manque\s)paiement.*?(\d+)\s*fcfa',
        r'(?<!manque\s)(?<!il manque\s)envoyé\s*(\d+)\s*fcfa',
        r'(?<!manque\s)(?<!il manque\s)reçu\s*(\d+)\s*fcfa',
        r'transaction.*?(\d+)\s*fcfa',
        r'payé\s*(\d+)\s*fcfa',
        r'versé\s*(\d+)\s*fcfa'
    ]
    
    # Patterns à EXCLURE (montants manquants)
    exclude_patterns = [
        r'manque(?:\s+encore)?\s*(\d+)\s*fcfa',
        r'il\s+manque\s*(\d+)\s*fcfa',
        r'insuffisant.*?(\d+)\s*fcfa'
    ]
    
    history_lower = conversation_history.lower()
    
    # Extraire montants à exclure
    excluded_amounts = set()
    for pattern in exclude_patterns:
        for match in re.finditer(pattern, history_lower):
            try:
                excluded_amounts.add(int(match.group(1)))
            except (ValueError, IndexError):
                continue
    
    logger.debug(f"💰 Montants exclus (manquants): {excluded_amounts}")
    
    # Extraire paiements réels
    for pattern in payment_patterns:
        matches = re.finditer(pattern, history_lower)
        for match in matches:
            try:
                amount = int(match.group(1))
                # Filtrer montants réalistes et non exclus
                if 100 <= amount <= 100000 and amount not in excluded_amounts:
                    previous_payments.append(amount)
            except (ValueError, IndexError):
                continue
    
    # Dédupliquer et trier
    unique_payments = sorted(list(set(previous_payments)))
    
    if unique_payments:
        logger.info(f"💰 Paiements précédents détectés: {unique_payments}")
    
    return unique_payments

def format_payment_for_prompt(validation_result: Dict[str, Any]) -> str:
    """
    Formate le résultat de validation pour l'inclure dans le prompt LLM.
    
    Args:
        validation_result: Résultat de validate_payment_cumulative()
    
    Returns:
        String formaté pour le prompt
    """
    if not validation_result:
        return ""
    
    status = str(validation_result.get('status') or '').strip().upper() or ('VALID' if validation_result.get('valid') else 'INSUFFICIENT')
    required_amount = int(validation_result.get('required_amount') or 0)
    total_received = int(validation_result.get('total_received') or 0)
    difference = int(validation_result.get('difference') or (total_received - required_amount))
    missing = abs(difference) if difference < 0 else 0
    message = str(validation_result.get('message') or '').strip()

    # Format compact & stable pour le LLM (facile à parser via _kv_parse)
    # NOTE: champs séparés par "|".
    return (
        "PAYMENT_VERDICT"
        f"|status={status}"
        f"|received={total_received}"
        f"|required={required_amount}"
        f"|diff={difference}"
        f"|missing={missing}"
        f"|message={message}"
    )

# Tests unitaires
if __name__ == "__main__":
    print("="*80)
    print("🧪 TEST PAYMENT VALIDATOR")
    print("="*80)
    
    # Test 1: Premier paiement insuffisant
    print("\n📍 TEST 1: Premier paiement 202 FCFA")
    result1 = validate_payment_cumulative(
        current_transactions=[{'amount': 202, 'currency': 'FCFA'}],
        conversation_history="",
        required_amount=2000
    )
    print(f"Valid: {result1['valid']}")
    print(f"Total: {result1['total_received']} FCFA")
    print(f"Message: {result1['message']}")
    
    # Test 2: Complément envoyé
    print("\n📍 TEST 2: Complément 1800 FCFA après 202 FCFA")
    result2 = validate_payment_cumulative(
        current_transactions=[{'amount': 1800, 'currency': 'FCFA'}],
        conversation_history="Tu as envoyé 202 FCFA mais il manque encore 1798 FCFA",
        required_amount=2000
    )
    print(f"Valid: {result2['valid']}")
    print(f"Total: {result2['total_received']} FCFA")
    print(f"Paiements: {result2['payments_history']}")
    print(f"Message: {result2['message']}")
    
    # Test 3: Paiement unique suffisant
    print("\n📍 TEST 3: Paiement unique 2020 FCFA")
    result3 = validate_payment_cumulative(
        current_transactions=[{'amount': 2020, 'currency': 'FCFA'}],
        conversation_history="",
        required_amount=2000
    )
    print(f"Valid: {result3['valid']}")
    print(f"Total: {result3['total_received']} FCFA")
    print(f"Message: {result3['message']}")
    
    print("\n" + "="*80)
    print("✅ Tests terminés")
