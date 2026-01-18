# -*- coding: utf-8 -*-
"""
PROTOTYPES V6.5 - Phrases de référence pour similarité sémantique

RÈGLES :
- Maximum 8 prototypes par intent
- Uniquement des variantes NON couvertes par V6/V5 keywords
- Contexte ivoirien / français informel
- Validés manuellement (pas d'auto-génération)
"""

# Configuration embeddings
EMBEDDINGS_CONFIG_V65 = {
    "model": "paraphrase-multilingual-MiniLM-L12-v2",
    "threshold_min": 0.75,           # En dessous = ignore, laisse SetFit
    "threshold_suggestion": 0.82,    # Au-dessus = log pour review humaine
    "confidence_max": 0.88,          # Ne jamais dépasser V6/V5
    "max_prototypes_per_intent": 8,  # Limite mémoire
    "cache_enabled": True,           # Performance obligatoire
    "cache_file": "cache/prototype_embeddings_v6_5.pkl",
}

# Mapping similarité → confiance (conservateur)
SIMILARITY_TO_CONFIDENCE = {
    0.75: 0.75,
    0.78: 0.78,
    0.80: 0.80,
    0.82: 0.82,
    0.85: 0.85,
    0.88: 0.88,
    0.90: 0.88,  # Plafonné
    0.95: 0.88,  # Plafonné
    1.00: 0.88,  # Plafonné
}

def similarity_to_confidence(similarity: float) -> float:
    """Convertit similarité cosine en confiance (plafonnée à 0.88)"""
    return min(similarity, EMBEDDINGS_CONFIG_V65["confidence_max"])


# =============================================================================
# PROTOTYPES PAR INTENT (max 8 chacun)
# Objectif : capturer les variantes sémantiques non couvertes par keywords V6/V5
# =============================================================================

INTENT_PROTOTYPES_V65 = {
    # =========================================================================
    # REASSURANCE (Prompt A) - Variantes non V6/V5
    # V6 couvre : paiement (wave/mtn/orange), contact (numéro/appeler)
    # V5 couvre : localisation (où/situé), horaires (ouvert/fermé)
    # =========================================================================
    "REASSURANCE": [
        # Smalltalk étendu (variantes non V5)
        "Comment vous portez-vous aujourd'hui",
        "J'espère que tout va bien de votre côté",
        "Bonne continuation à vous",
        
        # Localisation variantes (backup V5)
        "Vous êtes installés dans quel coin",
        "C'est dans quelle zone votre emplacement",
        
        # Horaires variantes (backup V5)
        "Vous fermez vers quelle heure le soir",
        "Vous bossez aussi le weekend",
        
        # Confiance/Légitimité (nouveau)
        "Vous êtes une entreprise sérieuse",
    ],
    
    # =========================================================================
    # SHOPPING (Prompt B) - Variantes non V6/V5
    # V5 couvre : prix (combien/tarif), catalogue (produits/vendez), stock (dispo)
    # =========================================================================
    "SHOPPING": [
        # Prix variantes (backup V5)
        "Ça se vend à quel montant",
        "C'est facturé comment",
        
        # Stock variantes (backup V5)
        "Il vous en reste encore",
        "C'est toujours en rayon",
        
        # Catalogue variantes (backup V5)
        "Qu'est-ce que vous proposez comme choix",
        "Faites-moi voir ce que vous avez",
        
        # Comparaison (nouveau)
        "Quelle est la différence entre les deux",
        "Lequel vous me conseillez",
    ],
    
    # =========================================================================
    # ACQUISITION (Prompt C) - Variantes non V6/V5
    # V5 couvre : commander/acheter/prendre/réserver + quantités
    # =========================================================================
    "ACQUISITION": [
        # Commande variantes (backup V5)
        "Je souhaite acquérir ce produit",
        "Je désire passer une commande",
        "Je suis preneur pour ça",
        
        # Quantité variantes (backup V5)
        "Mettez-m'en trois s'il vous plaît",
        "J'en prends une douzaine",
        
        # Confirmation achat (nouveau)
        "C'est bon je valide",
        "On part là-dessus",
        "Je confirme ma commande",
    ],
    
    # =========================================================================
    # SAV_SUIVI (Prompt D / Disjoncteur) - Variantes non V6
    # V6 couvre : tracking (mon colis/ma commande/arrive quand/niveau)
    # V6 couvre : problème (abîmé/cassé/défectueux)
    # =========================================================================
    "SAV_SUIVI": [
        # Tracking variantes (backup V6)
        "Je veux savoir où en est ma livraison",
        "Des nouvelles de mon paquet",
        "Ça avance ma commande",
        
        # Problème variantes (backup V6)
        "Ce n'est pas ce que j'avais demandé",
        "La qualité n'est pas au rendez-vous",
        "Il y a une erreur dans ma commande",
        
        # Réclamation (nouveau)
        "Je voudrais faire une réclamation",
        "Je ne suis pas satisfait du tout",
    ],
}

# Validation : max 8 prototypes par intent
for intent, protos in INTENT_PROTOTYPES_V65.items():
    if len(protos) > EMBEDDINGS_CONFIG_V65["max_prototypes_per_intent"]:
        raise ValueError(
            f"Intent {intent} a {len(protos)} prototypes, max autorisé: "
            f"{EMBEDDINGS_CONFIG_V65['max_prototypes_per_intent']}"
        )
