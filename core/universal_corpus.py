
# ==============================================================================
# CORPUS E-COMMERCE UNIVERSEL V4 REFACTORÉ - CLIENT-CENTRIC
# ==============================================================================
# Date: 2025-12-14
# Changements critiques V3 → V4:
#   - FUSION: CATALOGUE + RECHERCHE_PRODUIT + DISPONIBILITE → PRODUIT_GLOBAL
#   - FUSION: SUIVI_COMMANDE + ANNULATION → COMMANDE_EXISTANTE
#   - RÉDUCTION: 11 intents → 8 intents (-27%)
#   - DISTANCE EMBEDDING: 0.12-0.22 → 0.30-0.45 (target)
#   - ACCURACY ATTENDUE: 70.6% → 92-95%
# ==============================================================================

INTENT_DEFINITIONS_V4 = {
    # GROUPE A - CONVERSATIONNELS → PROMPT A (2 intents - inchangé)
    "SALUT_POLITESSE": {
        "id": 1,
        "name": "Salut / Politesse / Merci",
        "group": "A",
        "mode": "A",
        "score": 3,
        "definition": "Message social PUR (bonjour, merci, compliments) SANS question après.",
        "action": None,
    },
    "INFO_GENERALE": {
        "id": 2,
        "name": "Information générale / Localisation / Clarification",
        "group": "A",
        "mode": "A",
        "score": 10,
        "definition": "Questions sur entreprise, localisation, horaires, fonctionnement OU clarification.",
        "action": None,
    },

    # GROUPE B - PRODUITS → PROMPT B (2 intents - FUSION MAJEURE)
    "PRODUIT_GLOBAL": {
        "id": 3,
        "name": "Produit (catalogue + recherche + stock + caractéristiques)",
        "group": "B",
        "mode": "B",
        "score": 10,
        "definition": "TOUTES questions produit: catalogue, recherche précise, stock, dispo, caractéristiques, marque, âge, taille.",
        "action": "REDIRECT_LIVE",
        "note": "FUSION de CATALOGUE + RECHERCHE_PRODUIT + DISPONIBILITE",
        "sub_routes": {
            "catalogue": ["catalogue", "liste", "gamme", "menu", "qu'est-ce que vous avez"],
            "stock": ["stock", "dispo", "disponible", "reste", "rupture"],
            "caracteristiques": ["taille", "couleur", "âge", "marque", "modèle", "garantie"],
        }
    },
    "PRIX_PROMO": {
        "id": 4,
        "name": "Question prix / promo",
        "group": "B",
        "mode": "B",
        "score": 10,
        "definition": "Prix, tarifs, promotions, réductions, négociation, combien.",
        "action": "REDIRECT_LIVE",
    },

    # GROUPE C - COMMANDE → PROMPT C (4 intents - inchangé)
    "COMMANDE": {
        "id": 5,
        "name": "Demande de commande",
        "group": "C",
        "mode": "C",
        "score": 10,
        "definition": "Volonté EXPLICITE de commander (je veux, je prends, réservez-moi).",
        "action": "COLLECT_4_INFOS",
    },
    "LIVRAISON_INFO": {
        "id": 6,
        "name": "Informations de livraison",
        "group": "C",
        "mode": "C",
        "score": 9,
        "definition": "Zone livraison, adresse livraison, frais, délais, comment ça marche.",
        "action": None,
    },
    "PAIEMENT_TRANSACTION": {
        "id": 7,
        "name": "Moyens de paiement / Dépôt / Transaction",
        "group": "C",
        "mode": "C",
        "score": 9,
        "definition": "Moyens paiement, acompte, preuve transaction, Wave, Orange Money.",
        "action": None,
    },
    "CONTACT_COORDONNEES": {
        "id": 8,
        "name": "Contact / Coordonnées",
        "group": "C",
        "mode": "C",
        "score": 8,
        "definition": "Transmission numéro téléphone/WhatsApp du client.",
        "action": None,
    },

    # GROUPE D - APRÈS-VENTE → PROMPT D (2 intents - FUSION MAJEURE)
    "COMMANDE_EXISTANTE": {
        "id": 9,
        "name": "Commande existante (suivi + modification + annulation)",
        "group": "D",
        "mode": "D",
        "score": 10,
        "definition": "Suivi commande en cours, modification, ajout/retrait articles, annulation, changement adresse.",
        "action": None,
        "note": "FUSION de SUIVI_COMMANDE + ANNULATION + MODIFICATION",
        "sub_routes": {
            "suivi": ["où est", "tracking", "livreur", "retard", "toujours pas"],
            "modification": ["modifier", "changer", "ajouter", "retirer"],
            "annulation": ["annuler", "supprimer", "ne veux plus"],
        }
    },
    "PROBLEME_RECLAMATION": {
        "id": 10,
        "name": "Problème / Réclamation / SAV",
        "group": "D",
        "mode": "D",
        "score": 10,
        "definition": "Plainte, erreur, défaut, retour, remboursement, produit abîmé.",
        "action": "ESCALATE_SAV",
    },
}

# ==============================================================================
# PROTOTYPES V4 - DISTANCE EMBEDDING MAXIMALE
# ==============================================================================

INTENT_PROTOTYPES_V4 = {
    "SALUT_POLITESSE": (
        "bonjour bonsoir salut merci au revoir ça va comment allez-vous bonne journée"
    ),
    
    "INFO_GENERALE": (
        "où êtes-vous situés exactement votre boutique est où adresse localisation quartier "
        "comment fonctionne votre système vous vendez quoi globalement vous êtes ouvert quand "
        "horaires d'ouverture je ne comprends pas expliquez-moi clarifiez répétez"
    ),
    
    # FUSION: Catalogue + Recherche + Stock
    "PRODUIT_GLOBAL": (
        "montrez-moi catalogue liste produits vous avez quoi "
        "je cherche produit spécifique en stock disponible maintenant "
        "caractéristiques taille couleur âge marque modèle rupture "
        "il en reste combien quelle référence garantie composition"
    ),
    
    "PRIX_PROMO": (
        "c'est combien exactement quel est le prix tarif coût "
        "vous avez des promotions réductions soldes dernier prix négocier"
    ),
    
    "COMMANDE": (
        "je veux commander maintenant je prends ce produit réservez-moi "
        "je valide ma commande j'achète comment passer commande"
    ),
    
    "LIVRAISON_INFO": (
        "vous livrez dans quelle zone frais de livraison coût livraison "
        "délai de livraison quand serai-je livré combien de temps transport"
    ),
    
    "PAIEMENT_TRANSACTION": (
        "comment payer modes de paiement acceptés Wave Orange Money Mobile Money "
        "acompte dépôt j'ai payé voici la preuve paiement sécurisé"
    ),
    
    "CONTACT_COORDONNEES": (
        "mon numéro c'est appelez-moi au voici mon contact WhatsApp "
        "téléphone pour me joindre coordonnées"
    ),
    
    # FUSION: Suivi + Modification + Annulation
    "COMMANDE_EXISTANTE": (
        "où est ma commande passée suivi livraison tracking livreur "
        "modifier changer ajouter retirer article quantité adresse "
        "annuler supprimer ne veux plus commande retard toujours pas reçu"
    ),
    
    "PROBLEME_RECLAMATION": (
        "produit défectueux abîmé cassé erreur réclamation plainte "
        "je veux retourner remboursement insatisfait pas le bon"
    ),
}

# ==============================================================================
# CORPUS V4 - OPTIMISÉ CLIENT-CENTRIC
# ==============================================================================

UNIVERSAL_ECOMMERCE_INTENT_CORPUS_V4 = {
    # ==========================================================================
    # GROUPE A - CONVERSATIONNELS (inchangé)
    # ==========================================================================
    
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
            # Entreprise
            "Vous vendez quoi ?", "C'est quoi votre boutique ?",
            "Qu'est-ce que vous faites ?", "Présentez-vous",
            "Votre domaine c'est quoi ?", "Vous êtes dans quel secteur ?",
            "Pouvez-vous m'en dire plus sur votre entreprise ?",
            "Je veux en savoir plus sur votre entreprise",
            "Puis-je en savoir plus sur votre entreprise ?",
            
            # Localisation (CRITIQUE)
            "Vous êtes où ?", "Vous êtes situés où ?",
            "Vous êtes situés où exactement ?", "Vous êtes situés où svp ?",
            "C'est où votre boutique ?", "Vous êtes basés où ?",
            "Vous avez une adresse ?", "Vous avez un magasin physique ?",
            "Où vous trouvez-vous ?",
            "Quel quartier ?", "Quelle commune ?",
            "Vous êtes à quel quartier d'Abidjan ?", "C'est où exactement ?",
            "Je peux venir sur place ?", "Boutique physique ou en ligne ?",
            "Adresse de la boutique svp",
            
            # Horaires
            "Horaires d'ouverture ?", "Vous ouvrez à quelle heure ?",
            "Vous fermez quand ?", "Ouvert le dimanche ?",
            "Vous êtes ouvert maintenant ?", "Ouvert quand ?",
            
            # Fonctionnement
            "Comment ça marche ?", "Expliquez-moi le processus",
            "Comment on fait pour commander ?", "Ça fonctionne comment ?",
            "Le système c'est comment ?",
            
            # Clarification
            "Hein ?", "Quoi ?", "Comment ?", "Pardon ?",
            "J'ai pas compris", "Je comprends pas", "C'est pas clair",
            "Répétez", "Expliquez encore", "Précisez svp",
            "C'est-à-dire ?", "Développez",
            
            # Salut + Question
            "Bonjour vous êtes où exactement ?",
            "Salut c'est où votre boutique ?",
            "Bonsoir vous avez une adresse ?",
            "Hey vous êtes situés où ?",
            "Bonjour j'espère la famille va bien, vous êtes situés où exactement ?",
        ]
    },
    
    # ==========================================================================
    # GROUPE B - PRODUITS (FUSION MAJEURE)
    # ==========================================================================
    
    3: {
        "label": "PRODUIT_GLOBAL",
        "mode": "B",
        "exemples": [
            # ===== CATALOGUE (ancien intent 4) =====
            "Catalogue", "Liste des produits", "Qu'est-ce que vous avez ?",
            "Montrez-moi vos produits", "Vos articles", "Tous les produits",
            "Menu", "Je veux voir", "Faites-moi découvrir",
            "Quelles catégories ?", "Types de produits ?", "Gamme complète",
            "Qu'est-ce qu'il y a dans le live ?", "Promos du jour",
            "Nouveautés", "Vous avez quel type de produits",
            
            # ===== RECHERCHE PRÉCISE (ancien intent 5 - partie 1) =====
            "Je cherche un produit", "Vous avez des couches ?",
            "Le produit de la photo", "Celui du live",
            "Je veux ce produit précisément", "Je voudrais acheter 5 paquets",
            "Je veux 6paquets de couche culotte xxxl",
            "Je veux 6 paquets de couche culotte xxxl",
            
            # ===== CARACTÉRISTIQUES (ancien intent 5 - partie 2) =====
            "En quelle couleur ?", "Quelle taille ?",
            "Les modèles disponibles", "Il y a une garantie avec ?",
            "C'est pour quel âge ce produit ?", "C'est quelle marque ?",
            "Quelle référence ?", "Original ou copie ?", "Quelle version ?",
            "C'est quoi les caractéristiques", "La composition c'est quoi",
            "Vous avez la référence du produit", "C'est fabriqué où",
            "Le produit fait combien de grammes", "Quelle est la taille exacte",
            
            # ===== STOCK/DISPONIBILITÉ (ancien intent 5 - partie 3 + ancien 7) =====
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
            
            # ===== AVEC SALUT (patterns réels) =====
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
            "Pouvez-vous vérifier le prix d’un produit ?",
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
    
    # ==========================================================================
    # GROUPE C - COMMANDE/TRANSACTION (inchangé)
    # ==========================================================================
    
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
            "Le livreur arrive dans combien de temps ?",
            "Vous livrez aujourd'hui ou demain ?",
            "Comment ça se passe la livraison ?",
            "Je dois donner mon adresse de livraison ?",
            "Vous livrez le week-end ?", "Vous livrez dans quel quartier",
            "Combien pour livrer à Cocody", "La livraison prend combien de temps",
            "Ça arrive quand la livraison", "Les frais de livraison c'est combien",
            "La livraison est gratuite", "Reporter la livraison à demain",
            "Livrer à une autre adresse",
            "Je veux modifier mon adresse de livraison",
            "Changer la date de ma livraison svp",
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
            # ===== SUIVI (ancien intent 11) =====
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

            # ===== MODIFICATION (fusions) =====
            "Je veux modifier ma commande", "Changer la quantité de ma commande",
            "Ajouter 2 paquets à ma commande", "Enlever un article de la commande",
            "Modifier ce que j'ai commandé hier", "Changer l'adresse de livraison",
            "Modifier l'adresse svp", "Changer la date de livraison",
            "Bjr chef, je veux modifier ma commande d'hier",

            # ===== ANNULATION (ancien intent séparé fusionné) =====
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
# MIGRATION GUIDE V3 → V4
# ==============================================================================

MIGRATION_MAPPING_V3_TO_V4 = {
    "SALUT_POLITESSE": "SALUT_POLITESSE",  # Inchangé
    "INFO_GENERALE": "INFO_GENERALE",  # Inchangé
    "CATALOGUE": "PRODUIT_GLOBAL",  # FUSIONNÉ
    "RECHERCHE_PRODUIT": "PRODUIT_GLOBAL",  # FUSIONNÉ
    "DISPONIBILITE": "PRODUIT_GLOBAL",  # FUSIONNÉ
    "PRIX_PROMO": "PRIX_PROMO",  # Inchangé
    "COMMANDE": "COMMANDE",  # Inchangé
    "LIVRAISON_INFO": "LIVRAISON_INFO",  # Inchangé
    "PAIEMENT_TRANSACTION": "PAIEMENT_TRANSACTION",  # Inchangé
    "CONTACT_COORDONNEES": "CONTACT_COORDONNEES",  # Inchangé
    "SUIVI_COMMANDE": "COMMANDE_EXISTANTE",  # FUSIONNÉ
    "ANNULATION": "COMMANDE_EXISTANTE",  # FUSIONNÉ
    "PROBLEME_RECLAMATION": "PROBLEME_RECLAMATION",  # Inchangé
}

# ==============================================================================
# SUB-ROUTING PYTHON (post-SetFit)
# ==============================================================================

def sub_route_produit_global(message: str) -> str:
    """
    Après SetFit détecte PRODUIT_GLOBAL, détermine le sous-type
    pour affiner le prompt/comportement
    """
    message_lower = message.lower()
    
    # Stock/Dispo (priorité haute)
    stock_keywords = ["stock", "dispo", "disponible", "reste", "rupture", "en rupture"]
    if any(kw in message_lower for kw in stock_keywords):
        return "stock_disponibilite"
    
    # Caractéristiques
    char_keywords = ["taille", "couleur", "âge", "marque", "modèle", "garantie", 
                     "référence", "composition", "caractéristique", "fabriqué"]
    if any(kw in message_lower for kw in char_keywords):
        return "caracteristiques"
    
    # Catalogue (défaut si rien de précis)
    catalog_keywords = ["catalogue", "liste", "gamme", "menu", "qu'est-ce que", "quoi comme"]
    if any(kw in message_lower for kw in catalog_keywords):
        return "catalogue_general"
    
    # Défaut: recherche générale
    return "recherche_generale"


def sub_route_commande_existante(message: str) -> str:
    """
    Après SetFit détecte COMMANDE_EXISTANTE, détermine si c'est:
    - suivi simple
    - modification
    - annulation
    """
    message_lower = message.lower()
    
    # Annulation (priorité critique)
    annulation_keywords = ["annul", "supprimer", "ne veux plus", "cancel"]
    if any(kw in message_lower for kw in annulation_keywords):
        return "annulation"
    
    # Modification
    modif_keywords = ["modif", "changer", "chang", "ajouter", "ajout", "retirer", 
                      "enlever", "augmenter", "diminuer"]
    if any(kw in message_lower for kw in modif_keywords):
        return "modification"
    
    # Suivi simple (défaut)
    return "suivi_simple"


# ==============================================================================
# VALIDATION & MÉTRIQUES
# ==============================================================================

CORPUS_VALIDATION_TESTS_V4 = {
    "test_localisation": {
        "input": "Vous êtes situés où ?",
        "expected_intent": "INFO_GENERALE",
        "expected_mode": "A",
    },
    "test_prix": {
        "input": "Quel est le prix du paquet ?",
        "expected_intent": "PRIX_PROMO",
        "expected_mode": "B",
    },
    "test_stock": {
        "input": "Vous avez en stock ?",
        "expected_intent": "PRODUIT_GLOBAL",  # Changé
        "expected_mode": "B",
    },
    "test_caracteristiques": {
        "input": "C'est pour quel âge ce produit ?",
        "expected_intent": "PRODUIT_GLOBAL",  # Changé
        "expected_mode": "B",
    },
    "test_catalogue": {
        "input": "Montrez-moi vos produits",
        "expected_intent": "PRODUIT_GLOBAL",  # Changé
        "expected_mode": "B",
    },
    "test_suivi": {
        "input": "Où est ma commande ?",
        "expected_intent": "COMMANDE_EXISTANTE",  # Changé
        "expected_mode": "D",
    },
    "test_modification": {
        "input": "Je veux modifier ma commande",
        "expected_intent": "COMMANDE_EXISTANTE",  # Changé
        "expected_mode": "D",
    },
    "test_annulation": {
        "input": "Je veux annuler",
        "expected_intent": "COMMANDE_EXISTANTE",
        "expected_mode": "D",
    },
}

CORPUS_METRICS_V4 = {
    "total_intents": 10,  # Réduit de 11 à 10
    "total_exemples": 350,
    "exemples_par_intent_min": 20,
    "exemples_par_intent_max": 60,
    "accuracy_target": 0.92,  # 92%+ réaliste
    "fusions_applied": [
        "CATALOGUE + RECHERCHE_PRODUIT + DISPONIBILITE → PRODUIT_GLOBAL",
        "SUIVI + MODIFICATION + ANNULATION → COMMANDE_EXISTANTE",
    ],
    "distance_embedding_target": ">0.30",
    "errors_eliminated": [
        "RECHERCHE↔DISPO (9 erreurs)",
        "CATALOGUE↔RECHERCHE (4 erreurs)",
        "SUIVI↔ANNULATION (3 erreurs)",
    ],
}

# ==============================================================================
# CORPUS V5 - 4 PÔLES FUSION
# ==============================================================================
# Date: 2025-12-26
# Changements V4 → V5:
#   - RÉDUCTION: 10 intents → 4 pôles (-60%)
#   - FUSION REASSURANCE: SALUT + INFO_GENERALE + LIVRAISON + PAIEMENT
#   - FUSION SHOPPING: PRODUIT_GLOBAL + PRIX_PROMO
#   - FUSION ACQUISITION: COMMANDE + CONTACT
#   - FUSION SAV_SUIVI: COMMANDE_EXISTANTE + PROBLEME_RECLAMATION
#   - DISTANCE EMBEDDING: 0.30-0.45 → 0.50-0.70 (target +56%)
#   - ACCURACY ATTENDUE: 92-95% → 96-98%
#   - MODE = POLE (contrat simplifié)
# ==============================================================================

POLES_V5_LABELS = ["REASSURANCE", "SHOPPING", "ACQUISITION", "SAV_SUIVI"]


POLES_V5 = {
    "REASSURANCE": {
        "id": 1,
        "name": "Réassurance (Accueil + Info + Livraison + Paiement)",
        "intents_v4_fusionnés": [1, 2, 6, 7],
        "mission": "Gérer accueil, localisation, frais livraison, modes paiement",
        "prompt_mode": "REASSURANCE",
        "exemples_clés": [
            "Bonjour",
            "Vous êtes où",
            "Vous livrez à Yopougon",
            "Vous acceptez Wave",
            "Horaires d'ouverture",
        ],
        "sub_routing_keywords": {
            "salut": ["bonjour", "salut", "merci", "bye", "bonsoir"],
            "localisation": ["où", "situé", "adresse", "boutique", "situe", "ou sommes"],
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
        "exemples_clés": [
            "Vous avez quoi",
            "C'est combien",
            "En stock",
            "Taille 4",
            "Promotions",
            "Catalogue",
        ],
        "sub_routing_keywords": {
            "catalogue": ["catalogue", "liste", "avez quoi", "menu"],
            "stock": ["stock", "disponible", "reste", "dispo", "rupture"],
            "caracteristiques": ["taille", "couleur", "marque", "âge", "modèle"],
            "prix": ["combien", "prix", "tarif", "promo", "réduction", "coût"],
        },
    },
    "ACQUISITION": {
        "id": 3,
        "name": "Acquisition (Commande + Contact)",
        "intents_v4_fusionnés": [5, 8],
        "mission": "Passage à l'acte (je veux commander + numéro)",
        "prompt_mode": "ACQUISITION",
        "exemples_clés": [
            "Je veux commander",
            "Je prends",
            "Je commande",
            "Réservez-moi",
            "Je valide",
            "Mettez-moi ça",
            "Comment passer commande",
            "Je veux acheter",
            "Prenez ma commande",
            "Mon numéro c'est 0707070707",
            "Appelez-moi au 01 02 03 04 05",
            "WhatsApp moi au 0505050505",
            "Voici mon numéro +2250707070707",
            "Vous pouvez me joindre au",
            "Mon contact c'est",
        ],
        "sub_routing_keywords": {
            "commande": ["commander", "prends", "réserve", "acheter", "veux"],
            "contact": ["numéro", "téléphone", "whatsapp", "joindre", "appel"],
        },
    },
    "SAV_SUIVI": {
        "id": 4,
        "name": "SAV & Suivi (Commande existante + Réclamation)",
        "intents_v4_fusionnés": [9, 10],
        "mission": "Gestion post-commande, problèmes, retours → TRANSMISSIONXXX",
        "prompt_mode": "SAV_SUIVI",
        "exemples_clés": [
            "Où est ma commande",
            "Tracking",
            "Suivi de commande",
            "Le livreur est où",
            "Ma commande arrive quand",
            "Je n'ai pas encore reçu",
            "C'est en retard",
            "Je veux modifier ma commande",
            "Changer la quantité",
            "Ajouter un article",
            "Enlever un produit",
            "Je veux annuler",
            "Supprimer ma commande",
            "Je ne veux plus",
            "Annuler svp",
            "Produit défectueux",
            "Produit abîmé",
            "C'est cassé",
            "Je veux retourner",
            "Remboursement",
            "Réclamation",
            "Pas satisfait",
            "Ce n'est pas le bon produit",
        ],
        "sub_routing_keywords": {
            "suivi": ["où est", "tracking", "livreur", "arrive quand", "ma commande"],
            "modification": ["modifier", "changer", "ajouter", "enlever"],
            "annulation": ["annuler", "supprimer", "ne veux plus", "cancel"],
            "reclamation": ["abîmé", "défectueux", "retourner", "remboursement", "plainte"],
        },
    },
}


CORPUS_V5 = {
    "REASSURANCE": [
        "Bonjour",
        "Bonsoir",
        "Salut",
        "Merci",
        "Au revoir",
        "Ça va",
        "Vous êtes où ?",
        "Vous êtes situés où ?",
        "Vous êtes situés où exactement ?",
        "C'est où votre boutique ?",
        "Adresse svp",
        "Vous avez un magasin physique",
        "Je peux venir sur place",
        "Quel quartier",
        "Quelle commune",
        "Vous livrez où ?",
        "Zones de livraison",
        "Vous livrez à Yopougon",
        "Combien la livraison",
        "Frais de livraison",
        "Délai de livraison",
        "Quand ça arrive",
        "Livraison gratuite",
        "Vous livrez aujourd'hui",
        "Comment payer",
        "Modes de paiement",
        "Vous acceptez Wave",
        "Vous acceptez Orange Money",
        "Je peux payer en espèces",
        "Paiement à la livraison",
        "J'ai payé",
        "Voici mon paiement",
    ],
    "SHOPPING": [
        "Catalogue",
        "Vous avez quoi",
        "Montrez-moi vos produits",
        "Je cherche un produit",
        "Vous avez des couches",
        "Quelle taille",
        "Quelle marque",
        "C'est pour quel âge",
        "En stock",
        "Disponible",
        "Il en reste",
        "Rupture",
        "C'est combien",
        "Quel est le prix",
        "Tarif",
        "Coût",
        "Vous avez des promotions",
        "Réductions",
        "Soldes",
        "Prix en gros",
        "Dernier prix",
        "On peut négocier",
    ],
    "ACQUISITION": [
        "Je veux commander",
        "Je prends",
        "Je commande",
        "Réservez-moi",
        "Je valide",
        "Mettez-moi ça",
        "Comment passer commande",
        "Je veux acheter",
        "Prenez ma commande",
        "Mon numéro c'est 0707070707",
        "Appelez-moi au 01 02 03 04 05",
        "WhatsApp moi au 0505050505",
        "Voici mon numéro +2250707070707",
        "Vous pouvez me joindre au",
        "Mon contact c'est",
    ],
    "SAV_SUIVI": [
        "Où est ma commande",
        "Tracking",
        "Suivi de commande",
        "Le livreur est où",
        "Ma commande arrive quand",
        "Je n'ai pas encore reçu",
        "C'est en retard",
        "Je veux modifier ma commande",
        "Changer la quantité",
        "Ajouter un article",
        "Enlever un produit",
        "Je veux annuler",
        "Supprimer ma commande",
        "Je ne veux plus",
        "Annuler svp",
        "Produit défectueux",
        "Produit abîmé",
        "C'est cassé",
        "Je veux retourner",
        "Remboursement",
        "Réclamation",
        "Pas satisfait",
        "Ce n'est pas le bon produit",
    ],
}


POLE_MAPPING_V4_TO_V5 = {
    1: "REASSURANCE",
    2: "REASSURANCE",
    3: "SHOPPING",
    4: "SHOPPING",
    5: "ACQUISITION",
    6: "REASSURANCE",
    7: "REASSURANCE",
    8: "ACQUISITION",
    9: "SAV_SUIVI",
    10: "SAV_SUIVI",
}


POLE_TO_V4_INTENTS = {
    "REASSURANCE": [1, 2, 6, 7],
    "SHOPPING": [3, 4],
    "ACQUISITION": [5, 8],
    "SAV_SUIVI": [9, 10],
}


# ==============================================================================
# HELPER FUNCTIONS V4
# ==============================================================================

def get_corpus_for_training():
    """Retourne corpus formaté pour entraînement SetFit V4."""
    training_data = []
    for intent_id, data in UNIVERSAL_ECOMMERCE_INTENT_CORPUS_V4.items():  # V4 !
        intent_name = data["label"]
        for exemple in data["exemples"]:
            training_data.append({
                "text": exemple,
                "label": intent_name,
                "intent_id": intent_id,
                "mode": data["mode"],
            })
    return training_data


def get_prototypes_for_centroid():
    """Retourne prototypes V4 pour centroid router."""
    return INTENT_PROTOTYPES_V4  # V4 !


def validate_corpus():
    """Valide que le corpus V4 respecte les contraintes."""
    issues = []
    
    # Check 0: Cohérence des clés
    required_keys = {"label", "mode", "exemples"}
    for intent_id, data in UNIVERSAL_ECOMMERCE_INTENT_CORPUS_V4.items():  # V4 !
        missing = required_keys - set(data.keys())
        if missing:
            issues.append(f"Intent {intent_id}: clés manquantes {sorted(missing)}")
            continue
        if not isinstance(data.get("exemples"), list):
            issues.append(f"Intent {intent_id} ({data.get('label')}): 'exemples' doit être une liste")
    
    # Check 1: Nombre d'exemples
    min_n = int(CORPUS_METRICS_V4.get("exemples_par_intent_min", 0) or 0)  # V4 !
    max_n = int(CORPUS_METRICS_V4.get("exemples_par_intent_max", 10**9) or 10**9)
    for intent_id, data in UNIVERSAL_ECOMMERCE_INTENT_CORPUS_V4.items():  # V4 !
        examples = data.get("exemples") or []
        if len(examples) < min_n:
            issues.append(
                f"Intent {intent_id} ({data.get('label')}): {len(examples)} exemples (< {min_n})"
            )
        if len(examples) > max_n:
            issues.append(
                f"Intent {intent_id} ({data.get('label')}): {len(examples)} exemples (> {max_n})"
            )
    
    # Check 2: Duplicats entre intents
    seen = {}
    for intent_id, data in UNIVERSAL_ECOMMERCE_INTENT_CORPUS_V4.items():  # V4 !
        label = data.get("label")
        for exemple in data.get("exemples") or []:
            key = (exemple or "").strip().lower()
            if not key:
                issues.append(f"Intent {intent_id} ({label}): exemple vide")
                continue
            if key in seen and seen[key] != label:
                issues.append(
                    f"Dupliqué: '{exemple}' → {seen[key]} et {label}"
                )
            else:
                seen[key] = label
    
    # Check 3: Prototypes présents
    for _, data in UNIVERSAL_ECOMMERCE_INTENT_CORPUS_V4.items():  # V4 !
        label = data.get("label")
        if label and label not in INTENT_PROTOTYPES_V4:  # V4 !
            issues.append(f"Prototype manquant: {label}")
    
    # Check 4: Tests critiques
    for test_name, test_data in CORPUS_VALIDATION_TESTS_V4.items():  # V4 !
        input_text = (test_data.get("input") or "").strip()
        if not input_text:
            issues.append(f"Test {test_name}: input vide")
            continue
        
        found = False
        for _, corpus_data in UNIVERSAL_ECOMMERCE_INTENT_CORPUS_V4.items():  # V4 !
            for ex in corpus_data.get("exemples") or []:
                if (ex or "").strip() == input_text:
                    found = True
                    break
            if found:
                break
        if not found:
            issues.append(
                f"Test {test_name}: exemple absent → '{input_text}'"
            )
    
    return {"ok": len(issues) == 0, "issues": issues}


# ==============================================================================
# NOTES DE MIGRATION V3 → V4
# ==============================================================================
"""
CHANGEMENTS MAJEURS V3 → V4:

1. FUSION PRODUIT_GLOBAL:
   CATALOGUE + RECHERCHE_PRODUIT + DISPONIBILITE → 1 intent
   Élimine: 9+4 = 13 erreurs de confusion

2. FUSION COMMANDE_EXISTANTE:
   SUIVI + MODIFICATION + ANNULATION → 1 intent  
   Élimine: 3+2 = 5 erreurs de confusion

3. Total intents: 11 → 10 (-9%)
   Accuracy: 70.6% → 92%+ attendu

4. Sub-routing Python:
   - PRODUIT_GLOBAL → catalogue/stock/caracteristiques
   - COMMANDE_EXISTANTE → suivi/modification/annulation
   - Implémentation déterministe (pas LLM)
"""