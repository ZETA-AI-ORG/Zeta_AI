#!/usr/bin/env python3
"""
✅ VALIDATEUR DE RÉCAPITULATIF FINAL
====================================

Vérifie que le récapitulatif LLM contient TOUTES les informations obligatoires
pour une commande complète et prête pour la production.
"""

import re
from typing import Dict, List, Tuple


def validate_final_recap(response: str, collected_data: Dict) -> Tuple[bool, List[str]]:
    """
    Valide que le récapitulatif final contient toutes les infos obligatoires
    
    Args:
        response: Réponse LLM (récapitulatif)
        collected_data: Données collectées pendant la conversation
        
    Returns:
        (is_valid, missing_elements)
    """
    missing = []
    response_lower = response.lower()
    
    # ═══════════════════════════════════════════════════════════════
    # ÉLÉMENTS OBLIGATOIRES DANS LE RÉCAPITULATIF
    # ═══════════════════════════════════════════════════════════════
    
    # 1. PRODUIT (type + quantité)
    if not any(word in response_lower for word in ['couche', 'culotte', 'produit']):
        missing.append("❌ PRODUIT non mentionné")
    
    if not any(word in response_lower for word in ['lot', '100', '200', '300', 'taille']):
        missing.append("❌ QUANTITÉ/LOT non mentionné")
    
    # 2. PRIX (montant produit)
    price_pattern = r'\d{2}[.,\s]?\d{3}\s*(?:fcfa|f\b)'
    if not re.search(price_pattern, response_lower):
        missing.append("❌ PRIX PRODUIT non mentionné")
    
    # 3. ZONE DE LIVRAISON
    zones = ['yopougon', 'cocody', 'plateau', 'adjamé', 'abobo', 'marcory', 
             'koumassi', 'treichville', 'angré', 'riviera', 'anyama', 
             'port-bouët', 'attécoubé', 'bingerville', 'songon', 'grand-bassam']
    if not any(zone in response_lower for zone in zones):
        missing.append("❌ ZONE LIVRAISON non mentionnée")
    
    # 4. FRAIS DE LIVRAISON
    if not any(word in response_lower for word in ['livraison', 'frais']):
        missing.append("❌ FRAIS LIVRAISON non mentionnés")
    
    # 5. TÉLÉPHONE CLIENT
    phone_pattern = r'07\d{8}|0[1-9]\d{8}|\+225\s*\d{10}'
    if not re.search(phone_pattern, response):
        missing.append("❌ TÉLÉPHONE CLIENT non mentionné")
    
    # 6. PAIEMENT (validation acompte)
    if not any(word in response_lower for word in ['dépôt', 'acompte', 'paiement', 'validé', '2000']):
        missing.append("❌ PAIEMENT/ACOMPTE non mentionné")
    
    # 7. DÉLAI DE LIVRAISON
    if not any(word in response_lower for word in ['demain', 'jour', 'délai', '24h', 'livraison']):
        missing.append("❌ DÉLAI LIVRAISON non mentionné")
    
    # 8. CONFIRMATION/VALIDATION
    if not any(word in response_lower for word in ['confirmé', 'validé', 'commande', 'ok', 'parfait']):
        missing.append("❌ CONFIRMATION non mentionnée")
    
    # ═══════════════════════════════════════════════════════════════
    # VÉRIFICATIONS ANTI-ERREURS
    # ═══════════════════════════════════════════════════════════════
    
    # Vérifier cohérence des montants
    amounts = re.findall(r'(\d{2,3})[.,\s]?(\d{3})', response)
    if amounts:
        # Convertir en entiers
        amounts_int = [int(a[0] + a[1]) for a in amounts]
        
        # Vérifier que les montants sont réalistes
        for amount in amounts_int:
            if amount < 1000 or amount > 100000:
                missing.append(f"⚠️ MONTANT SUSPECT: {amount} FCFA")
    
    # Vérifier pas de contradictions
    contradictions = [
        ('gratuit', 'fcfa'),  # "gratuit" + prix = contradiction
        ('pas de frais', 'livraison.*\d+'),  # "pas de frais" + montant
    ]
    
    for word1, word2 in contradictions:
        if re.search(word1, response_lower) and re.search(word2, response_lower):
            missing.append(f"⚠️ CONTRADICTION: '{word1}' ET '{word2}'")
    
    # ═══════════════════════════════════════════════════════════════
    # RÉSULTAT
    # ═══════════════════════════════════════════════════════════════
    
    is_valid = len(missing) == 0
    
    return is_valid, missing


def validate_conversation_completeness(turns: List[Dict]) -> Dict:
    """
    Valide la complétude de toute la conversation
    
    Args:
        turns: Liste des tours de conversation
        
    Returns:
        {
            'completeness_score': 0-100,
            'collected_data': {...},
            'missing_data': [...],
            'final_recap_valid': bool
        }
    """
    collected = {
        'produit': False,
        'quantite': False,
        'zone': False,
        'telephone': False,
        'paiement': False
    }
    
    # Analyser tous les tours
    all_text = ""
    for turn in turns:
        user_msg = turn.get('user_message', '')
        bot_msg = turn.get('llm_response', '')
        all_text += f" {user_msg} {bot_msg}"
    
    all_text_lower = all_text.lower()
    
    # Vérifier chaque donnée
    if any(word in all_text_lower for word in ['couche', 'culotte', 'taille']):
        collected['produit'] = True
    
    if any(word in all_text_lower for word in ['lot', '100', '200', '300']):
        collected['quantite'] = True
    
    zones = ['yopougon', 'cocody', 'plateau', 'adjamé', 'abobo', 'anyama']
    if any(zone in all_text_lower for zone in zones):
        collected['zone'] = True
    
    if re.search(r'07\d{8}', all_text):
        collected['telephone'] = True
    
    if any(word in all_text_lower for word in ['validé', 'dépôt', '2000']):
        collected['paiement'] = True
    
    # Calculer score
    completeness_score = (sum(collected.values()) / len(collected)) * 100
    
    # Vérifier récap final (dernier tour)
    final_recap_valid = False
    if turns:
        last_response = turns[-1].get('llm_response', '')
        final_recap_valid, _ = validate_final_recap(last_response, collected)
    
    return {
        'completeness_score': completeness_score,
        'collected_data': collected,
        'missing_data': [k for k, v in collected.items() if not v],
        'final_recap_valid': final_recap_valid
    }


# ============================================================================
# TESTS
# ============================================================================

if __name__ == "__main__":
    print("🧪 TEST VALIDATEUR RÉCAPITULATIF\n")
    
    # Test 1: Récap complet
    print("Test 1: Récapitulatif COMPLET")
    recap_complet = """
    Parfait ! ✅ Commande validée:
    📦 Couches à pression Taille 3 (lot 300) - 22.900 FCFA
    🚚 Livraison Anyama - 2.500 FCFA
    💳 Acompte validé: 2.000 FCFA
    📞 Contact: 0701234567
    ⏰ Livraison prévue: Demain (jour ouvré)
    
    On te confirme par WhatsApp ! 😊
    """
    is_valid, missing = validate_final_recap(recap_complet, {})
    print(f"   Valid: {is_valid}")
    if missing:
        for m in missing:
            print(f"   {m}")
    else:
        print("   ✅ TOUS LES ÉLÉMENTS PRÉSENTS")
    print()
    
    # Test 2: Récap incomplet
    print("Test 2: Récapitulatif INCOMPLET")
    recap_incomplet = """
    Ok ! Commande de couches.
    On te livre demain.
    """
    is_valid, missing = validate_final_recap(recap_incomplet, {})
    print(f"   Valid: {is_valid}")
    for m in missing:
        print(f"   {m}")
    print()
    
    # Test 3: Récap avec contradiction
    print("Test 3: Récapitulatif avec CONTRADICTION")
    recap_contradiction = """
    Commande validée !
    Livraison gratuite à Cocody - 1500 FCFA
    """
    is_valid, missing = validate_final_recap(recap_contradiction, {})
    print(f"   Valid: {is_valid}")
    for m in missing:
        print(f"   {m}")
    print()
    
    print("✅ TESTS TERMINÉS")
