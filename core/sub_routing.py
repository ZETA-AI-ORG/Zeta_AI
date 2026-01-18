"""
Sub-routing Python déterministe V5 (post-SetFit)
================================================

Après que SetFit V5 détecte un PÔLE (REASSURANCE, SHOPPING, ACQUISITION, SAV_SUIVI),
ce module affine avec des règles Python pour déterminer:
- sub_intent: sous-catégorie précise (localisation, prix, commande, suivi, etc.)
- action: action suggérée (RESPOND_LOCATION, COLLECT_PHONE, TRANSMISSIONXXX, etc.)

Date: 2025-12-26
Version: V5 (4 pôles)
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def sub_route_pole(pole: str, message: str) -> Dict[str, Any]:
    """
    Sub-routing déterministe après SetFit V5.
    
    Args:
        pole: Pôle détecté par SetFit V5 (REASSURANCE, SHOPPING, ACQUISITION, SAV_SUIVI)
        message: Message utilisateur original
    
    Returns:
        Dict contenant:
        - sub_intent: str (localisation, prix, commande, suivi, etc.)
        - action: str (RESPOND_LOCATION, COLLECT_PHONE, TRANSMISSIONXXX, etc.)
        - keywords_matched: list (keywords qui ont matché, pour debug)
    """
    from core.universal_corpus import POLES_V5
    
    message_lower = (message or "").strip().lower()
    if not message_lower:
        return {
            "sub_intent": "unknown",
            "action": "RESPOND_INFO",
            "keywords_matched": [],
        }
    
    pole_upper = (pole or "").upper()
    if pole_upper not in POLES_V5:
        logger.warning(f"[SUB_ROUTING_V5] Pôle inconnu: {pole}")
        return {
            "sub_intent": "unknown",
            "action": "RESPOND_INFO",
            "keywords_matched": [],
        }
    
    keywords = POLES_V5[pole_upper].get("sub_routing_keywords", {})
    
    # =========================================================================
    # REASSURANCE (Accueil + Info + Livraison + Paiement)
    # =========================================================================
    if pole_upper == "REASSURANCE":
        # Ordre de priorité (du plus spécifique au plus général)
        for sub_intent, kws in keywords.items():
            matched = [kw for kw in kws if kw in message_lower]
            if matched:
                action_map = {
                    "salut": "RESPOND_SOCIAL",
                    "localisation": "RESPOND_LOCATION",
                    "livraison": "RESPOND_DELIVERY",
                    "paiement": "RESPOND_PAYMENT",
                }
                return {
                    "sub_intent": sub_intent,
                    "action": action_map.get(sub_intent, "RESPOND_INFO"),
                    "keywords_matched": matched,
                }
        
        # Défaut REASSURANCE: info générale
        return {
            "sub_intent": "general",
            "action": "RESPOND_INFO",
            "keywords_matched": [],
        }
    
    # =========================================================================
    # SHOPPING (Catalogue + Prix)
    # =========================================================================
    elif pole_upper == "SHOPPING":
        # Ordre de priorité: prix > stock > caractéristiques > catalogue
        for sub_intent in ["prix", "stock", "caracteristiques", "catalogue"]:
            kws = keywords.get(sub_intent, [])
            matched = [kw for kw in kws if kw in message_lower]
            if matched:
                return {
                    "sub_intent": sub_intent,
                    "action": "TRANSMISSIONXXX",  # Jessica LITE ne gère pas SHOPPING
                    "keywords_matched": matched,
                }
        
        # Défaut SHOPPING: catalogue
        return {
            "sub_intent": "catalogue",
            "action": "TRANSMISSIONXXX",
            "keywords_matched": [],
        }
    
    # =========================================================================
    # ACQUISITION (Commande + Contact)
    # =========================================================================
    elif pole_upper == "ACQUISITION":
        # Détection numéro de téléphone (priorité haute)
        digit_count = sum(1 for c in message if c.isdigit())
        if digit_count >= 8:
            return {
                "sub_intent": "contact",
                "action": "COLLECT_PHONE",
                "keywords_matched": ["phone_digits_detected"],
            }
        
        # Sinon: commande
        for sub_intent, kws in keywords.items():
            matched = [kw for kw in kws if kw in message_lower]
            if matched:
                action_map = {
                    "commande": "COLLECT_4_INFOS",
                    "contact": "COLLECT_PHONE",
                }
                return {
                    "sub_intent": sub_intent,
                    "action": action_map.get(sub_intent, "COLLECT_4_INFOS"),
                    "keywords_matched": matched,
                }
        
        # Défaut ACQUISITION: commande
        return {
            "sub_intent": "commande",
            "action": "COLLECT_4_INFOS",
            "keywords_matched": [],
        }
    
    # =========================================================================
    # SAV_SUIVI (Commande existante + Réclamation)
    # =========================================================================
    elif pole_upper == "SAV_SUIVI":
        # POLICY V5: TOUT finit en TRANSMISSIONXXX
        # (Jessica LITE n'a pas accès BDD commandes)
        
        # Ordre de priorité: annulation > réclamation > modification > suivi
        for sub_intent in ["annulation", "reclamation", "modification", "suivi"]:
            kws = keywords.get(sub_intent, [])
            matched = [kw for kw in kws if kw in message_lower]
            if matched:
                return {
                    "sub_intent": sub_intent,
                    "action": "TRANSMISSIONXXX",
                    "keywords_matched": matched,
                }
        
        # Défaut SAV_SUIVI: suivi général
        return {
            "sub_intent": "suivi_general",
            "action": "TRANSMISSIONXXX",
            "keywords_matched": [],
        }
    
    # Fallback (ne devrait jamais arriver)
    return {
        "sub_intent": "unknown",
        "action": "RESPOND_INFO",
        "keywords_matched": [],
    }
