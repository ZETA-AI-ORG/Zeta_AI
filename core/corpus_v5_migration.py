# ==============================================================================
# CORPUS E-COMMERCE UNIVERSEL V5 - 4 PÔLES
# ==============================================================================
# Date: 2025-12-27
# Source: Migration automatique depuis V4 (10 intents → 4 pôles)
# Réduction: -60% complexité
# Accuracy target: 96-98%
# ==============================================================================

from typing import Dict, List
import json

# ==============================================================================
# MAPPING V4 → V5 (RÈGLE DE FUSION)
# ==============================================================================

POLE_MAPPING_V4_TO_V5 = {
    1: "REASSURANCE",   # SALUT_POLITESSE
    2: "REASSURANCE",   # INFO_GENERALE
    3: "SHOPPING",      # PRODUIT_GLOBAL
    4: "SHOPPING",      # PRIX_PROMO
    5: "ACQUISITION",   # COMMANDE
    6: "REASSURANCE",   # LIVRAISON_INFO
    7: "REASSURANCE",   # PAIEMENT_TRANSACTION
    8: "ACQUISITION",   # CONTACT_COORDONNEES
    9: "SAV_SUIVI",     # COMMANDE_EXISTANTE
    10: "SAV_SUIVI",    # PROBLEME_RECLAMATION
}

# ==============================================================================
# CORPUS V4 SOURCE (copié depuis universal_corpus.py)
# ==============================================================================

UNIVERSAL_ECOMMERCE_INTENT_CORPUS_V4 = {
    1: {
        "label": "SALUT_POLITESSE",
        "mode": "A",
        "exemples": [
            "Bonjour", "Bonsoir", "Salut", "Hello", "Hey", "Coucou",
            "Slt", "Bjr", "Bnsr", "Yo", "Wesh",
            "Merci", "Merci beaucoup", "Ok merci", "Grand merci", "Thanks",
            "De rien", "Avec plaisir", "Pas de souci", "Ok", "D'accord",
            "Compris", "Ça marche", "Parfait", "Bien reçu",
            "Au revoir", "Bye", "À plus tard", "À bientôt", "Tchao",
            "Bonne continuation", "Bonne journée",
            "Ça va ?", "Comment allez-vous ?", "Comment tu vas ?",
            "Vous allez bien ?", "La famille va bien ?",
            "Salut comment allez-vous",
            "Bonsoir j'espère que vous allez bien",
            "Bjr madame désolé du dérangement",
            "Hey j'espère que tout va bien de votre côté",
            "Yo c'est comment là",
            "Bonjour pardon de vous déranger à cette heure",
            "Salut j'espère la famille va bien",
            "Bondjour coment sa va",
            "Bonsoir j'espère que tout va bien chez vous",
            "Hey salut ça dit quoi de ton côté",
            "Merci beaucoup pour votre aide",
        ]
    },
    
    2: {
        "label": "INFO_GENERALE",
        "mode": "A",
        "exemples": [
            "Vous vendez quoi ?", "C'est quoi votre boutique ?",
            "Qu'est-ce que vous faites ?", "Présentez-vous",
            "Votre domaine c'est quoi ?", "Vous êtes dans quel secteur ?",
            "Pouvez-vous m'en dire plus sur votre entreprise ?",
            "Je veux en savoir plus sur votre entreprise",
            "Puis-je en savoir plus sur votre entreprise ?",
            "Vous êtes où ?", "Vous êtes situés où ?",
            "Vous êtes situés où exactement ?", "Vous êtes situés où svp ?",
            "C'est où votre boutique ?", "Vous êtes basés où ?",
            "Vous avez une adresse ?", "Vous avez un magasin physique ?",
            "Où vous trouvez-vous ?",
            "Quel quartier ?", "Quelle commune ?",
            "Vous êtes à quel quartier d'Abidjan ?", "C'est où exactement ?",
            "Je peux venir sur place ?", "Boutique physique ou en ligne ?",
            "Adresse de la boutique svp",
            "Horaires d'ouverture ?", "Vous ouvrez à quelle heure ?",
            "Vous fermez quand ?", "Ouvert le dimanche ?",
            "Vous êtes ouvert maintenant ?", "Ouvert quand ?",
            "Comment ça marche ?", "Expliquez-moi le processus",
            "Ça fonctionne comment ?",
            "Le système c'est comment ?",
            "Hein ?", "Quoi ?", "Comment ?", "Pardon ?",
            "J'ai pas compris", "Je comprends pas", "C'est pas clair",
            "Répétez", "Expliquez encore", "Précisez svp",
            "C'est-à-dire ?", "Développez",
            "Bonjour vous êtes où exactement ?",
            "Salut c'est où votre boutique ?",
            "Bonsoir vous avez une adresse ?",
            "Hey vous êtes situés où ?",
            "Bonjour j'espère la famille va bien, vous êtes situés où exactement ?",
        ]
    },
    
    3: {
        "label": "PRODUIT_GLOBAL",
        "mode": "B",
        "exemples": [
            "Catalogue", "Liste des produits", "Qu'est-ce que vous avez ?",
            "Montrez-moi vos produits", "Vos articles", "Tous les produits",
            "Menu", "Je veux voir", "Faites-moi découvrir",
            "Quelles catégories ?", "Types de produits ?", "Gamme complète",
            "Qu'est-ce qu'il y a dans le live ?", "Promos du jour",
            "Nouveautés", "Vous avez quel type de produits",
            "Je cherche un produit", "Vous avez des couches ?",
            "Le produit de la photo", "Celui du live",
            "En quelle couleur ?", "Quelle taille ?",
            "Les modèles disponibles", "Il y a une garantie avec ?",
            "C'est pour quel âge ce produit ?", "C'est quelle marque ?",
            "Quelle référence ?", "Original ou copie ?", "Quelle version ?",
            "C'est quoi les caractéristiques", "La composition c'est quoi",
            "Vous avez la référence du produit", "C'est fabriqué où",
            "Le produit fait combien de grammes", "Quelle est la taille exacte",
            "Vous avez en stock ?", "C'est disponible ?",
            "Il en reste ?", "Vous avez encore ?", "Dispo maintenant ?",
            "Vous avez le produit X en stock ?", "C'est disponible maintenant ?",
            "Vous n'avez plus ce modèle ?", "C'est en rupture ou pas ?",
            "Rupture ?", "Plus en stock ?", "Combien il en reste ?",
            "Quand vous en aurez ?", "Vous allez recevoir quand ?",
            "Il reste des paquets", "C'est dispo pour aujourd'hui",
            "Vous avez combien de pièces disponibles",
            "Il y a combien de modèles disponibles",
            "C'est disponible en quelle couleur",
            "Quand ça revient en stock",
            "Bjr comment tu vas, c'est disponible en stock",
        ]
    },
    
    4: {
        "label": "PRIX_PROMO",
        "mode": "B",
        "exemples": [
            "C'est combien ?", "Quel est le prix ?", "Prix de ce produit",
            "Tarif", "Coût", "Quel est le prix du paquet ?",
            "Combien ça coûte ?", "Prix en FCFA", "En franc",
            "Pouvez-vous vérifier le prix d'un produit ?",
            "Pouvez-vous vérifier le prix d'un produit ?",
            "Pouvez-vous verifier le prix d'un produit ?",
            "Vous avez des promotions en ce moment ?",
            "C'est le même prix partout ?", "Vous avez des promos ?",
            "Réductions ?", "Soldes ?", "Dernier prix", "Prix cadeau",
            "On peut négocier ?", "C'est cher", "Trop cher",
            "Vous pouvez baisser ?", "Le prix a augmenté ou pas",
            "Vous avez un prix gros", "Vous faites combien pour ce produit",
            "C'est à combien le paquet", "Le prix unitaire c'est quoi",
            "Il y a une réduction si j'achète beaucoup", "C'est en solde actuellement",
            "Vous faites des remises",
            "Salut j'espère que vous allez bien, c'est combien le paquet",
        ]
    },
    
    5: {
        "label": "COMMANDE",
        "mode": "C",
        "exemples": [
            "Je veux commander", "Je commande", "Je prends",
            "Je veux acheter", "Mettez-moi ça", "Je valide",
            "Réservez-moi ce produit", "Gardez-moi ça",
            "Comment passer commande ?", "C'est décidé", "Je le veux",
            "Allez-y", "Je veux acheter ce produit", "Je veux 3 paquets",
            "Prenez ma commande", "Comment je fais pour passer commande",
            "Je prends 3 unités", "Mets-moi 2 paquets svp",
            "Je commande pour demain", "Garde-moi 4 paquets",
            "Je réserve 2 articles", "Comment passer ma commande",
            "Je veux passer ma commande maintenant",
            "Comment je fais pour commander svp",
            "Je souhaite commander maintenant",
            "Hey j'espère que tout va bien, je veux commander 5 paquets",
            "Comment on fait pour commander ?",
            "Je veux ce produit précisément",
            "Je voudrais acheter 5 paquets",
            "Je veux 6 paquets de couche culotte xxxl",
        ]
    },
    
    6: {
        "label": "LIVRAISON_INFO",
        "mode": "C",
        "exemples": [
            "Vous livrez où ?", "Zones de livraison ?",
            "Vous livrez à Yopougon ?", "Vous livrez à Cocody ?",
            "Combien la livraison ?", "Frais de livraison ?",
            "Coût de livraison ?", "Livraison gratuite ?",
            "Ça prend combien de temps ?", "Délai de livraison ?",
            "Quand ça arrive ?", "Livraison rapide ?",
            "Je serai livré quand exactement ?",
            "Vous livrez aujourd'hui ou demain ?",
            "Comment ça se passe la livraison ?",
            "Je dois donner mon adresse de livraison ?",
            "Vous livrez le week-end ?", "Vous livrez dans quel quartier",
            "Combien pour livrer à Cocody", "La livraison prend combien de temps",
            "Ça arrive quand la livraison", "Les frais de livraison c'est combien",
            "La livraison est gratuite",
            "Bonjour madame désolé du dérangement, vous livrez à Abobo",
            "Salut pardon oh, les frais de livraison c'est combien",
        ]
    },
    
    7: {
        "label": "PAIEMENT_TRANSACTION",
        "mode": "C",
        "exemples": [
            "Paiement", "Comment payer ?", "Modes de paiement",
            "Vous acceptez Wave ?", "Vous acceptez Orange Money ?", "Vous acceptez MTN ?",
            "Je peux payer par Mobile Money ?",
            "Je peux payer en espèces ?", "Je peux payer en liquide ?",
            "Je peux payer par carte ?",
            "C'est possible de payer après ?", "Je dois payer avant la livraison ?",
            "Je viens de payer", "J'ai payé", "Voici mon paiement",
            "Capture du paiement", "Preuve de paiement", "Je vous envoie le reçu",
            "Paiement sécurisé ?", "Je veux une facture",
            "Paiement à la livraison c'est possible",
            "Bonjour pardon de te déranger, vous acceptez Mobile Money",
            "Le paiement Wave est obligatoire ?",
            "Je peux payer autrement ?", "Autres options de paiement ?",
        ]
    },
    
    8: {
        "label": "CONTACT_COORDONNEES",
        "mode": "C",
        "exemples": [
            "Mon numéro c'est 0707070707",
            "Appelez-moi sur le 01 02 03 04 05",
            "WhatsApp moi au 05 05 05 05 05",
            "Voici mon numéro +2250707070707",
            "Mon numéro de téléphone est le 0707070707",
            "Vous pouvez me joindre au 01 02 03 04 05",
            "Pour me contacter : 0160724570",
            "Mon contact c'est 0787360757",
            "Joignez-moi au 07 07 07 07 07",
            "Mon WhatsApp c'est 0707070707",
            "Écris-moi sur WhatsApp au 0707070707",
            "Voici mon numéro WhatsApp : 0707070707",
            "Tu peux m'appeler au 0707070707",
            "Numéro : 0707070707",
            "Comment je peux vous joindre", "Quel est votre numéro WhatsApp",
            "Je suis joignable sur WhatsApp au 0505050505",
            "Voici mes coordonnées : +225 07 87 36 07 57",
            "Appelez-moi sur ce numéro : 07 07 07 07 07",
            "Tu peux me joindre au 01 02 03 04 05",
            "Mon contact WhatsApp : +225 07 87 36 07 57",
        ]
    },
    
    9: {
        "label": "COMMANDE_EXISTANTE",
        "mode": "D",
        "exemples": [
            "Où est ma commande ?", "Où en est le colis ?",
            "Où en est ma commande ?",
            "Tracking", "Suivi de commande", "Ma commande arrive quand ?",
            "Le livreur est où ?", "Le livreur arrive quand ?",
            "Le livreur ne m'a pas appelé",
            "Ma commande actuelle",
            "C'est livré ?", "J'ai pas encore reçu", "Toujours pas livré",
            "Je n'ai pas encore reçu",
            "Pourquoi le retard ?", "C'est en retard", "Ça traîne",
            "Quand arrive ma commande", "Le livreur est où exactement",
            "Quel est le statut de ma livraison", "Ma commande a été expédiée",
            "C'est en cours de livraison", "Le suivi de ma commande svp",
            "Ça n'est pas arrivé",
            "Yo la forme, où est mon colis svp",
            "Salut ça dit quoi, quand ça arrive ma commande",
            "Je veux modifier ma commande", "Changer la quantité de ma commande",
            "Ajouter 2 paquets à ma commande", "Enlever un article de la commande",
            "Modifier ce que j'ai commandé hier", "Changer l'adresse de livraison",
            "Modifier l'adresse svp", "Changer la date de livraison",
            "Bjr chef, je veux modifier ma commande d'hier",
            "Je veux annuler ma commande", "Je veux annuler ma commande svp",
            "Je ne veux plus la commande", "Supprimer ma commande d'hier",
            "Annuler ma commande",
        ]
    },
    
    10: {
        "label": "PROBLEME_RECLAMATION",
        "mode": "D",
        "exemples": [
            "Produit défectueux", "Ça marche pas", "C'est cassé",
            "Produit abîmé", "Endommagé", "C'est pas le bon produit",
            "Erreur de commande", "J'ai reçu autre chose",
            "Il manque un article", "Incomplet", "Je veux me plaindre",
            "Réclamation", "Pas satisfait", "Déçu",
            "Je veux retourner", "Retour produit", "Remboursement",
            "Je veux mon argent",
        ]
    }
}

# ==============================================================================
# MIGRATION AUTOMATIQUE V4 → V5
# ==============================================================================

def migrate_corpus_v4_to_v5() -> Dict[str, List[str]]:
    """
    Migre automatiquement le corpus V4 (10 intents) vers V5 (4 pôles)
    """
    corpus_v5 = {
        "REASSURANCE": [],
        "SHOPPING": [],
        "ACQUISITION": [],
        "SAV_SUIVI": []
    }
    
    print("🔄 Migration corpus V4 → V5...")
    print("-" * 60)
    
    for intent_id, data in UNIVERSAL_ECOMMERCE_INTENT_CORPUS_V4.items():
        pole_v5 = POLE_MAPPING_V4_TO_V5[intent_id]
        label_v4 = data["label"]
        exemples = data.get("exemples", [])
        
        print(f"Intent {intent_id:2d} ({label_v4:25s}) → {pole_v5:15s} : {len(exemples):3d} exemples")
        
        corpus_v5[pole_v5].extend(exemples)
    
    print("-" * 60)
    print("\n🔧 Déduplication...")
    
    for pole in corpus_v5:
        avant = len(corpus_v5[pole])
        corpus_v5[pole] = list(set(corpus_v5[pole]))
        apres = len(corpus_v5[pole])
        if avant > apres:
            print(f"  {pole:15s}: {avant} → {apres} ({avant-apres} doublons supprimés)")
    
    print("\n📊 Corpus V5 final :")
    print("-" * 60)
    total = 0
    for pole, exemples in corpus_v5.items():
        print(f"  {pole:15s}: {len(exemples):3d} exemples")
        total += len(exemples)
    print("-" * 60)
    print(f"  {'TOTAL':15s}: {total:3d} exemples")
    
    return corpus_v5


# ==============================================================================
# DÉFINITIONS V5 (STRUCTURE COMPLÈTE)
# ==============================================================================

POLES_V5 = {
    "REASSURANCE": {
        "id": 1,
        "name": "Réassurance (Accueil + Info + Livraison + Paiement)",
        "intents_v4_fusionnés": [1, 2, 6, 7],
        "mission": "Gérer accueil, localisation, frais livraison, modes paiement",
        "prompt_mode": "REASSURANCE",
        "action_jessica": "MODE SOCIAL ou répondre brièvement + relancer COLLECTE",
        "sub_routing_keywords": {
            "salut": ["bonjour", "salut", "merci", "bye", "bonsoir"],
            "localisation": ["où", "situé", "adresse", "boutique"],
            "livraison": ["livrez", "frais", "délai", "zone", "livraison"],
            "paiement": ["payer", "wave", "orange money", "espèce", "paiement"],
        },
    },
    "SHOPPING": {
        "id": 2,
        "name": "Shopping (Catalogue + Prix)",
        "intents_v4_fusionnés": [3, 4],
        "mission": "Catalogue, stock, tailles, prix, promos",
        "prompt_mode": "SHOPPING",
        "action_jessica": "[IN-SCOPE] Rappeler live TikTok + pivoter vers COLLECTE",
        "sub_routing_keywords": {
            "catalogue": ["catalogue", "liste", "avez quoi", "menu"],
            "stock": ["stock", "disponible", "reste", "dispo"],
            "caracteristiques": ["taille", "couleur", "marque", "âge"],
            "prix": ["combien", "prix", "tarif", "promo", "réduction"],
        },
    },
    "ACQUISITION": {
        "id": 3,
        "name": "Acquisition (Commande + Contact)",
        "intents_v4_fusionnés": [5, 8],
        "mission": "Passage à l'acte (je veux commander + numéro)",
        "prompt_mode": "ACQUISITION",
        "action_jessica": "MODE COLLECTE (Photo/Zone/Tel)",
        "sub_routing_keywords": {
            "commande": ["commander", "prends", "réserve", "acheter"],
            "contact": ["numéro", "téléphone", "whatsapp", "joindre"],
        },
    },
    "SAV_SUIVI": {
        "id": 4,
        "name": "SAV & Suivi (Commande existante + Réclamation)",
        "intents_v4_fusionnés": [9, 10],
        "mission": "Gestion post-commande → TRANSMISSIONXXX",
        "prompt_mode": "SAV_SUIVI",
        "action_jessica": "[OUT-SCOPE] TRANSMISSIONXXX immédiat",
        "sub_routing_keywords": {
            "suivi": ["où est", "tracking", "livreur", "arrive quand"],
            "modification": ["modifier", "changer", "ajouter", "enlever"],
            "annulation": ["annuler", "supprimer", "ne veux plus"],
            "reclamation": ["abîmé", "défectueux", "retourner", "remboursement"],
        },
    },
}


# ==============================================================================
# GÉNÉRATION CORPUS V5
# ==============================================================================

CORPUS_V5_AUTO = migrate_corpus_v4_to_v5()


# ==============================================================================
# MAPPING PÔLE → MODE JESSICA
# ==============================================================================

POLE_TO_JESSICA_MODE = {
    "REASSURANCE": "SOCIAL",        # Intents 1,2 → Accueil/Info
    "SHOPPING": "COLLECTE",          # Intents 3,4 → Redirect live + collecte
    "ACQUISITION": "COLLECTE",       # Intents 5,8 → Collecte pure
    "SAV_SUIVI": "DISJONCTEUR",      # Intents 9,10 → [OUT-SCOPE]
}


# ==============================================================================
# HELPER FUNCTIONS V5
# ==============================================================================

def get_corpus_v5_for_training():
    """Retourne corpus formaté pour entraînement SetFit V5."""
    training_data = []
    for pole, exemples in CORPUS_V5_AUTO.items():
        for exemple in exemples:
            training_data.append({
                "text": exemple,
                "label": pole,
                "mode_jessica": POLE_TO_JESSICA_MODE[pole],
            })
    return training_data


def map_pole_to_jessica_action(pole: str, message: str) -> dict:
    """
    Mappe un pôle V5 vers une action Jessica
    """
    base_mode = POLE_TO_JESSICA_MODE[pole]
    
    if pole == "REASSURANCE":
        # Sub-routing
        msg_lower = message.lower()
        if any(kw in msg_lower for kw in ["bonjour", "salut", "merci"]):
            return {"verdict": "[IN-SCOPE]", "mode": "SOCIAL", "action": "Saluer + orienter"}
        elif any(kw in msg_lower for kw in ["où", "situé", "adresse"]):
            return {"verdict": "[IN-SCOPE]", "mode": "SOCIAL", "action": "Répondre localisation + relancer collecte"}
        else:
            return {"verdict": "[IN-SCOPE]", "mode": "SOCIAL", "action": "Répondre brièvement + collecte"}
    
    elif pole == "SHOPPING":
        return {"verdict": "[IN-SCOPE]", "mode": "COLLECTE", "action": "Rappeler live TikTok + demander photo"}
    
    elif pole == "ACQUISITION":
        return {"verdict": "[IN-SCOPE]", "mode": "COLLECTE", "action": "Démarrer collecte Photo/Zone/Tel"}
    
    elif pole == "SAV_SUIVI":
        return {"verdict": "[OUT-SCOPE]", "mode": "DISJONCTEUR", "action": "TRANSMISSIONXXX"}
    
    return {"verdict": "[IN-SCOPE]", "mode": base_mode, "action": "Gérer selon contexte"}


def validate_corpus_v5():
    """Valide la cohérence du corpus V5"""
    issues = []
    
    # Check 1: 4 pôles présents
    expected_poles = ["REASSURANCE", "SHOPPING", "ACQUISITION", "SAV_SUIVI"]
    for pole in expected_poles:
        if pole not in CORPUS_V5_AUTO:
            issues.append(f"Pôle manquant: {pole}")
    
    # Check 2: Minimum 20 exemples par pôle
    for pole, exemples in CORPUS_V5_AUTO.items():
        if len(exemples) < 20:
            issues.append(f"{pole}: seulement {len(exemples)} exemples (< 20)")
    
    # Check 3: Total doit être > 400
    total = sum(len(ex) for ex in CORPUS_V5_AUTO.values())
    if total < 400:
        issues.append(f"Total exemples: {total} (< 400 attendu)")
    
    # Check 4: Pas de doublons inter-pôles
    all_examples = {}
    for pole, exemples in CORPUS_V5_AUTO.items():
        for ex in exemples:
            key = ex.strip().lower()
            if key in all_examples and all_examples[key] != pole:
                issues.append(f"Doublon: '{ex}' dans {all_examples[key]} et {pole}")
            all_examples[key] = pole
    
    return {"ok": len(issues) == 0, "issues": issues}


# ==============================================================================
# EXPORT JSON
# ==============================================================================

def export_corpus_v5_json(filepath: str = "corpus_v5_migrated.json"):
    """Exporte le corpus V5 en JSON"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(CORPUS_V5_AUTO, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Corpus V5 exporté : {filepath}")


# ==============================================================================
# STATS FINALES
# ==============================================================================

CORPUS_V5_STATS = {
    "total_poles": 4,
    "reduction_vs_v4": "60%",  # 10 intents → 4 pôles
    "total_exemples": sum(len(ex) for ex in CORPUS_V5_AUTO.values()),
    "accuracy_target": "96-98%",
    "distance_embedding_target": "0.50-0.70",
    "compatibility_jessica": "100%",
}


if __name__ == "__main__":
    # Migration automatique
    corpus = migrate_corpus_v4_to_v5()
    
    # Validation
    validation = validate_corpus_v5()
    print("\n🔍 Validation du corpus V5 :")
    if validation["ok"]:
        print("✅ Corpus valide")
    else:
        print("❌ Problèmes détectés :")
        for issue in validation["issues"]:
            print(f"  - {issue}")
    
    # Export
    export_corpus_v5_json()
    
    # Stats
    print("\n📊 Statistiques finales :")
    for key, value in CORPUS_V5_STATS.items():
        print(f"  {key}: {value}")