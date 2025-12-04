# ==============================================================================
# CORPUS E-COMMERCE UNIVERSEL - SCALABLE POUR 1 À 1000 ENTREPRISES
# ==============================================================================
# Secteurs couverts : E-commerce, Vente en ligne, Boutique physique, 
#                     Achat-revente, Marketplace, Commerce de détail/gros
# ==============================================================================

INTENT_DEFINITIONS = {
    # GROUPE A - CONVERSATIONNELS → PROMPT A
    "SALUT_POLITESSE": {
        "id": 1,
        "name": "Salut / Politesse",
        "group": "A",
        "score": 3,
        "definition": "Message social d'ouverture ou de clôture (bonjour, merci, compliments) sans demande précise.",
    },
    "INFO_GENERALE": {
        "id": 2,
        "name": "Demande d'information générale / Localisation",
        "group": "A",
        "score": 10,
        "definition": "Questions sur l'entreprise ou le service en général (où, comment ça marche, horaires, zone), sans parler de prix ou de stock.",
    },
    "CLARIFICATION": {
        "id": 3,
        "name": "Compréhension / Clarification",
        "group": "A",
        "score": 8,
        "definition": "Le client ne comprend pas ou demande de réexpliquer (hein ?, j'ai pas compris, expliquez mieux).",
    },

    # GROUPE B - ACHAT / PRODUITS → PROMPT B
    "CATALOGUE": {
        "id": 4,
        "name": "Demande catalogue / liste produits",
        "group": "B",
        "score": 8,
        "definition": "Le client veut une vue d'ensemble des produits (qu'est-ce que vous vendez ?, types de produits, gammes).",
    },
    "PRODUIT_PRECIS": {
        "id": 5,
        "name": "Recherche produit précis",
        "group": "B",
        "score": 10,
        "definition": "Le client parle d'un produit ou besoin concret (taille, marque, produit vu en live, type de couche).",
        "action": "REDIRECT_LIVE",
    },
    "PRIX_PROMO": {
        "id": 6,
        "name": "Question prix / promo",
        "group": "B",
        "score": 10,
        "definition": "Questions sur les montants, promotions, réductions (c'est combien ?, y a une promo ?, prix du paquet).",
        "action": "REDIRECT_LIVE",
    },
    "DISPONIBILITE_STOCK": {
        "id": 7,
        "name": "Disponibilité / stock",
        "group": "B",
        "score": 10,
        "definition": "Demandes sur la présence ou quantité disponible du produit (vous en avez ?, encore en stock ?, rupture ?).",
        "action": "REDIRECT_LIVE",
    },

    # GROUPE C - COMMANDE → PROMPT C
    "COMMANDE": {
        "id": 8,
        "name": "Demande de commande",
        "group": "C",
        "score": 10,
        "definition": "Volonté explicite de commander ou de finaliser (je veux commander, je prends, note ma commande).",
        "action": "COLLECT_4_INFOS",
    },
    "LIVRAISON_INFO": {
        "id": 9,
        "name": "Informations de livraison",
        "group": "C",
        "score": 9,
        "definition": "Questions ou informations sur la zone, l'adresse, les frais et les délais de livraison.",
    },
    "PAIEMENT_TRANSACTION": {
        "id": 10,
        "name": "Moyens de paiement / Dépôt / Transaction",
        "group": "C",
        "score": 9,
        "definition": "Questions ou confirmations sur le paiement, l'acompte, la preuve de transaction, le numéro de Wave.",
    },

    # GROUPE D - APRÈS-VENTE → PROMPT D
    "SUIVI_COMMANDE": {
        "id": 11,
        "name": "Suivi de commande / livraison",
        "group": "D",
        "score": 8,
        "definition": "Le client suit une commande existante (où est ma commande ?, le livreur n'est pas venu, retard).",
    },
    "PROBLEME_RECLAMATION": {
        "id": 12,
        "name": "Problème / Réclamation",
        "group": "D",
        "score": 10,
        "definition": "Plainte, insatisfaction, erreur, produit abîmé, demande de correction, retour ou remboursement.",
        "action": "ESCALATE_SAV",
    },
}

UNIVERSAL_ECOMMERCE_INTENT_CORPUS = {
    # ==========================================================================
    # GROUPE A - CONVERSATIONNELS (Intents 1-3)
    # ==========================================================================
    
    1: {
        "label": "Salutation/Politesse",
        "mode": "A",
        "description": "Salutations, remerciements, politesse basique",
        "exemples_universels": [
            # Salutations standard (12 exemples)
            "Bonjour", "Bonsoir", "Salut", "Hello", "Hey", "Coucou",
            "Bonne journée", "Bon après-midi", "Bonne soirée",
            "Bonjour à tous", "Salut la boutique", "Bonjour monsieur/madame",

            # Salutations informelles Afrique francophone (12 exemples)
            "Yo", "Wesh", "Ça va ?", "Comment tu vas ?", "Tu es là ?",
            "C'est comment ?", "On fait comment ?", "Top",
            "Bien ou bien ?", "Ça dit quoi ?", "Tu me reçois ?", "On se parle ?",

            # Remerciements (12 exemples)
            "Merci", "Merci beaucoup", "Merci infiniment", "Merci bien",
            "Ok merci", "D'accord merci", "C'est gentil", "Merci hein",
            "Merci à vous", "Je vous remercie", "Grand merci", "Merci pour tout",

            # Réponses polies (12 exemples)
            "De rien", "Avec plaisir", "Pas de souci", "Ok", "D'accord",
            "Entendu", "Compris", "Ça marche", "Ok top", "Cool",
            "C'est noté", "Parfait",

            # Départ/Fin (10 exemples)
            "Au revoir", "Bye", "À plus tard", "À bientôt", "Tchao",
            "Je reviens", "À tout à l'heure", "Bonne continuation", "Take care", "Ciao"
        ],
        "patterns_regex": [
            r"\b(bon(jour|soir)|salut|hey|coucou|yo|wesh)\b",
            r"\b(merci|thanks|gratitude)\b",
            r"\b(au revoir|bye|tchao)\b"
        ]
    },
    
    2: {
        "label": "Information générale entreprise",
        "mode": "A",
        "description": "Questions sur l'entreprise, présentation, localisation",
        "exemples_universels": [
            # Présentation entreprise (12 exemples)
            "Vous vendez quoi ?", "C'est quoi votre boutique ?",
            "Qu'est-ce que vous faites ?", "Vous proposez quoi ?",
            "Présentez-vous", "Parlez-moi de vous", "C'est quoi ici ?",
            "Vous êtes spécialisés dans quoi ?", "Votre domaine c'est quoi ?",
            "Qu'est-ce que je peux trouver chez vous ?", "Quelle est votre activité ?",
            "Vous faites dans quoi exactement ?",

            # Localisation (12 exemples)
            "Vous êtes où ?", "C'est où votre boutique ?",
            "Vous avez une adresse ?", "Localisation",
            "Vous êtes dans quelle zone ?", "Quel quartier ?",
            "Boutique physique ?", "Vous avez un magasin ?",
            "Je peux venir sur place ?", "Adresse complète svp",
            "Quelle ville ?", "Vous êtes basés où ?",

            # Généralités (12 exemples)
            "Comment ça marche ?", "C'est quoi le principe ?",
            "Expliquez-moi", "Je découvre", "Première fois",
            "Comment on fait ?", "Ça fonctionne comment ?",
            "Processus d'achat ?", "C'est simple ?", "Mode d'emploi",
            "Guide du client", "Les étapes pour acheter",

            # Horaires/Contact (12 exemples)
            "Horaires d'ouverture ?", "Vous ouvrez à quelle heure ?",
            "Contact ?", "Numéro de téléphone ?", "WhatsApp ?",
            "Vous fermez quand ?", "Ouvert le dimanche ?",
            "Horaires de la boutique ?", "Joignable comment ?",
            "Email de contact ?", "Réseaux sociaux ?", "Comment vous contacter ?"
        ],
        "patterns_regex": [
            r"\b(vous (vendez|proposez|faites) quoi|qu'est-ce que vous)\b",
            r"\b(où|localisation|adresse|boutique|magasin)\b",
            r"\b(comment (ça marche|on fait|fonctionn))\b"
        ]
    },
    
    3: {
        "label": "Clarification/Incompréhension",
        "mode": "A",
        "description": "Messages flous, demandes de répétition",
        "exemples_universels": [
            # Incompréhension (12 exemples)
            "Hein ?", "Quoi ?", "Comment ?", "Pardon ?",
            "J'ai pas compris", "Je comprends pas", "C'est pas clair",
            "Répétez", "Réexpliquez", "Expliquez encore",
            "Je ne saisis pas", "Pas clair du tout",

            # Demande précision (12 exemples)
            "Expliquez un peu", "Détaillez", "Plus de détails",
            "C'est-à-dire ?", "Ça veut dire quoi ?",
            "Soyez plus clair", "Je suis perdu",
            "Précisez svp", "Développez", "Clarifiez",
            "Je ne vois pas", "Exemple concret ?",

            # Messages vagues (10 exemples)
            "Euh", "Bon", "Alors", "Hmm", "Ben",
            "Je sais pas trop", "Peut-être", "On verra",
            "Bof", "Mouais"
        ],
        "patterns_regex": [
            r"\b(hein|quoi|comment|pardon)\s*\??",
            r"\b(pas compris|comprends pas|j'ai rien compris)\b",
            r"\b(répét|réexpliqu|expliqu)\b"
        ]
    },
    
    # ==========================================================================
    # GROUPE B - PRODUITS/CATALOGUE (Intents 4-7)
    # ==========================================================================
    
    4: {
        "label": "Catalogue/Liste produits",
        "mode": "B",
        "description": "Demande globale de catalogue sans produit précis",
        "exemples_universels": [
            # Catalogue général (12 exemples)
            "Catalogue", "Liste des produits", "Qu'est-ce que vous avez ?",
            "Montrez-moi vos produits", "Vous proposez quoi ?",
            "Vos articles", "Gamme de produits",
            "Tous les produits", "Catalogue complet", "Menu",
            "Les articles disponibles", "Inventaire",

            # Exploration (12 exemples)
            "Je veux voir", "Montrez-moi", "Faites-moi découvrir",
            "Qu'est-ce que vous vendez ?", "Quels types de produits ?",
            "Variétés disponibles", "Références disponibles",
            "Présentez vos produits", "J'aimerais voir ce que vous avez",
            "Qu'avez-vous en boutique ?", "Vos offres", "Découvrir vos articles",

            # Catégories (12 exemples)
            "Quelles catégories ?", "Types de produits",
            "Les différents modèles", "Vos gammes",
            "Collections disponibles", "Séries de produits",
            "Rubriques", "Sections du catalogue",
            "Classement par catégorie", "Groupes de produits",
            "Familles d'articles", "Gammes proposées",

            # Live/Promo (10 exemples)
            "Qu'est-ce qu'il y a dans le live ?",
            "Les produits du live", "Vente flash aujourd'hui",
            "Promos du jour", "Articles en promo",
            "Offres spéciales actuelles", "Nouveautés",
            "Arrivages récents", "Best-sellers", "Coups de cœur"
        ],
        "patterns_regex": [
            r"\b(catalogue|liste|gamme|références)\b",
            r"\b(qu'est-ce que (vous avez|vous vendez|vous proposez))\b",
            r"\b(montrez|voir|découvrir)\b.*\b(produit|article)\b"
        ]
    },
    
    5: {
        "label": "Recherche produit spécifique",
        "mode": "B",
        "description": "Client cherche un produit précis ou vu en live",
        "exemples_universels": [
            # Recherche précise (12 exemples)
            "Je cherche [PRODUIT]", "Vous avez [PRODUIT] ?",
            "Le [PRODUIT] de la photo", "Celui du live",
            "Le produit montré", "L'article numéro X",
            "Où trouver [PRODUIT] ?", "Disponibilité de [PRODUIT]",
            "Je veux [PRODUIT] précisément", "[PRODUIT] en stock ?",
            "Recherche [PRODUIT] spécifique", "Besoin de [PRODUIT]",

            # Caractéristiques (12 exemples)
            "En quelle couleur ?", "Quelle taille ?",
            "Les modèles disponibles", "Versions existantes",
            "Le [COULEUR] [PRODUIT]", "Taille [X]",
            "Quelles options ?", "Caractéristiques disponibles",
            "Variantes de couleur", "Dimensions disponibles",
            "Format disponible", "Spécifications techniques",

            # Références visuelles (12 exemples)
            "Celui-là", "Celui de l'image", "Le rouge",
            "Le petit", "Le grand format", "Version [X]",
            "Le même que", "Identique à",
            "Celui montré en story", "Sur la vidéo",
            "Dans le post", "Sur votre page",

            # Marques/Références (10 exemples)
            "Marque [X]", "Référence [X]", "Modèle [X]",
            "Original ou copie ?", "Authentique ?",
            "Version originale", "Marque officielle",
            "C'est du vrai ?", "Produit original ?", "Certification ?"
        ],
        "patterns_regex": [
            r"\b(je cherche|vous avez|il y a)\b.*\b(produit|article|modèle)\b",
            r"\b(celui|celle|ceux|celles)\b.*(là|du live|de la photo)\b",
            r"\b(quelle (taille|couleur|version))\b"
        ]
    },
    
    6: {
        "label": "Prix/Promotions/Tarifs",
        "mode": "B",
        "description": "Demandes sur les prix, remises, promos",
        "exemples_universels": [
            # Prix direct (12 exemples)
            "C'est combien ?", "Quel est le prix ?", "Combien ça coûte ?",
            "Prix de [PRODUIT]", "Tarif", "Coût",
            "Ça fait combien ?", "Montant",
            "Valeur de [PRODUIT]", "Prix unitaire",
            "Coût total", "Combien je paye ?",

            # Monnaie locale adaptable (12 exemples)
            "Prix en FCFA", "Combien de F ?", "En franc",
            "Prix en [MONNAIE]",
            "Montant en CFA", "En euros ?", "Dollars ?",
            "Prix local", "Tarif en devise locale",
            "Conversion en [MONNAIE]", "Équivalent en [MONNAIE]",
            "C'est combien en francs ?",

            # Promotions (12 exemples)
            "Vous avez des promos ?", "Réductions ?", "Soldes ?",
            "Remise ?", "Prix barré ?", "Promo en cours ?",
            "Vente flash", "Offres spéciales", "Réduction de prix",
            "Rabais disponible ?", "Code promo ?", "Bon de réduction ?",

            # Négociation (12 exemples)
            "Dernier prix", "Prix cadeau", "Vous faites combien ?",
            "On peut négocier ?", "Baisse de prix possible ?",
            "Prix de gros", "Tarif revendeur",
            "Meilleur prix possible", "Geste commercial ?",
            "Ristourne ?", "Réduction si j'achète plusieurs ?",
            "Prix d'ami",

            # Comparaison (10 exemples)
            "Moins cher où ?", "Meilleur prix ?",
            "C'est cher", "Trop cher", "Prix excessif",
            "Pourquoi ce prix ?", "Prix justifié ?",
            "Plus abordable ailleurs ?", "Prix compétitif ?",
            "Rapport qualité-prix ?"
        ],
        "patterns_regex": [
            r"\b(combien|prix|tarif|coût|montant)\b",
            r"\b(promo|réduction|solde|remise|offre)\b",
            r"\b(cher|moins cher|dernier prix|négoci)\b"
        ]
    },
    
    7: {
        "label": "Disponibilité/Stock",
        "mode": "B",
        "description": "Questions sur la disponibilité immédiate",
        "exemples_universels": [
            # Stock basique (12 exemples)
            "Vous avez en stock ?", "C'est disponible ?",
            "Il en reste ?", "Vous avez encore ?",
            "Stock disponible", "Dispo maintenant ?",
            "En stock actuellement ?", "Disponibilité immédiate ?",
            "Je peux acheter maintenant ?", "Vous en avez ?",
            "C'est accessible ?", "Produit en rayon ?",

            # Rupture (12 exemples)
            "Rupture ?", "Rupture de stock ?", "Plus en stock ?",
            "Épuisé ?", "En attente de réappro ?",
            "Stock vide ?", "Plus disponible ?",
            "Tout vendu ?", "Plus rien ?",
            "En pénurie ?", "Manquant ?", "Indisponible ?",

            # Quantité (12 exemples)
            "Combien il en reste ?", "Quantité disponible ?",
            "Vous en avez beaucoup ?", "Stock limité ?",
            "Dernières pièces ?",
            "Nombre d'unités dispo", "Inventaire restant",
            "Quelle quantité en stock ?", "Combien d'exemplaires ?",
            "Stock suffisant ?", "Assez en stock ?", "Unités restantes ?",

            # Délai réappro (12 exemples)
            "Quand vous en aurez ?", "Retour en stock quand ?",
            "Prochaine arrivage ?", "Restockage",
            "Date de réapprovisionnement ?", "Quand ça revient ?",
            "Livraison fournisseur prévue ?", "Bientôt disponible ?",
            "Prochaine disponibilité", "Réappro prévu quand ?",
            "Dans combien de temps ?", "Futur arrivage ?",

            # Vérification (10 exemples)
            "Vérifiez le stock svp", "Confirmez la dispo",
            "C'est sûr que c'est dispo ?",
            "Pouvez-vous checker ?", "Vérification stock",
            "Confirmez la disponibilité", "C'est certain ?",
            "Garantie de dispo ?", "Assuré d'avoir ?", "Dispo garanti ?"
        ],
        "patterns_regex": [
            r"\b(stock|dispo|disponible|reste|encore)\b",
            r"\b(rupture|épuisé|plus en stock)\b",
            r"\b(combien (il en reste|vous en avez))\b"
        ]
    },
    
    # ==========================================================================
    # GROUPE C - COMMANDE/TRANSACTION (Intents 8-10)
    # ==========================================================================
    
    8: {
        "label": "Intention de commander",
        "mode": "C",
        "description": "Client veut passer une commande",
        "exemples_universels": [
            # Commande directe (12 exemples)
            "Je veux commander", "Je commande", "Je prends",
            "Mettez-moi ça", "Je valide", "J'achète",
            "Commandez pour moi", "Enregistrez ma commande",
            "Je veux acheter", "Passez ma commande",
            "Validez ma commande", "Commande ferme",

            # Réservation (12 exemples)
            "Réservez-moi [PRODUIT]", "Mettez de côté",
            "Gardez-moi ça", "Bloquez-moi [QUANTITÉ]",
            "Réservation produit", "Mise de côté svp",
            "Tenez-moi [PRODUIT]", "Sécurisez-moi ça",
            "Réservation ferme", "Je réserve",
            "Gardez jusqu'à demain", "Bloquez le stock",

            # Procédure (12 exemples)
            "Comment passer commande ?", "Procédure de commande",
            "Étapes pour commander", "Comment faire pour acheter ?",
            "Je fais comment pour prendre ?",
            "Process d'achat ?", "Démarche à suivre ?",
            "Guide de commande", "Processus achat",
            "Marche à suivre ?", "Comment procéder ?",
            "Expliquez la commande",

            # Intention ferme (12 exemples)
            "C'est décidé", "Je le veux", "Je le prends",
            "Allez-y", "On y va", "Go", "Validez",
            "Banco", "Top départ", "Je suis partant",
            "C'est bon pour moi", "Lancez la commande",

            # Plusieurs produits (10 exemples)
            "Je prends plusieurs articles", "Commande groupée",
            "Je veux commander tout ça",
            "Plusieurs produits à commander", "Commande multiple",
            "Je prends tout", "Liste de courses",
            "Panier complet", "Achat groupé", "Commande en lot"
        ],
        "patterns_regex": [
            r"\b(je (veux commander|commande|prends|valide|achète))\b",
            r"\b(réserv|mettez de côté|gardez-moi)\b",
            r"\b(comment (commander|passer commande))\b"
        ]
    },
    
    9: {
        "label": "Livraison/Adresse/Délais",
        "mode": "C",
        "description": "Questions logistiques de livraison",
        "exemples_universels": [
            # Zones de livraison (12 exemples)
            "Vous livrez où ?", "Zones de livraison ?",
            "Vous livrez à [VILLE] ?", "Livraison dans [QUARTIER] ?",
            "Vous couvrez [ZONE] ?", "Livraison nationale ?",
            "Livraison internationale ?",
            "Périmètre de livraison", "Secteurs desservis",
            "Zones géographiques couvertes", "Livrez-vous partout ?",
            "Couverture territoriale ?",

            # Frais livraison (12 exemples)
            "Combien la livraison ?", "Frais de livraison ?",
            "Prix du transport ?", "Livraison gratuite ?",
            "Livraison payante ?", "C'est inclus ?",
            "Coût de port ?", "Frais de transport",
            "Tarif livraison", "Prix du shipping",
            "Livraison offerte ?", "Montant livraison ?",

            # Délais (12 exemples)
            "Ça prend combien de temps ?", "Délai de livraison ?",
            "Quand ça arrive ?", "Livraison rapide ?",
            "Livré en combien de jours ?", "Express possible ?",
            "Livraison le jour même ?",
            "Temps de livraison estimé", "Date de réception",
            "Combien de jours d'attente ?", "Livraison sous combien ?",
            "Délai moyen",

            # Modalités (12 exemples)
            "Comment ça se passe ?", "Processus de livraison ?",
            "Le livreur appelle avant ?", "Suivi de colis ?",
            "Numéro de tracking ?",
            "Procédure de réception", "Livraison à domicile ?",
            "Mode de livraison", "Options de livraison",
            "Notification de livraison ?", "Appel préalable ?",
            "Traçabilité du colis ?",

            # Adresse (10 exemples)
            "Je dois donner mon adresse ?", "Adresse exacte ?",
            "Point de retrait ?", "Retrait en boutique ?",
            "Livraison à quelle adresse ?", "Précision localisation",
            "Coordonnées GPS ?", "Indications lieu",
            "Adresse complète nécessaire ?", "Point relais ?"
        ],
        "patterns_regex": [
            r"\b(livr|livraison|délai|transport)\b",
            r"\b(combien (de temps|de jours)|quand (ça arrive|livré))\b",
            r"\b(vous livrez (où|à|dans))\b"
        ]
    },
    
    10: {
        "label": "Paiement/Transaction",
        "mode": "C",
        "description": "Moyens de paiement, acompte, preuves",
        "exemples_universels": [
            # Moyens de paiement (12 exemples)
            "Comment payer ?", "Vous acceptez quoi ?",
            "Moyens de paiement ?", "Je paye comment ?",
            "Modes de paiement acceptés ?",
            "Options de paiement", "Quels modes de règlement ?",
            "Paiement par quoi ?", "Vous prenez quoi comme paiement ?",
            "Méthodes de paiement dispo", "Solutions de paiement",
            "Comment régler ?",

            # Mobile money Afrique (12 exemples)
            "Wave ?", "Orange Money ?", "MTN Mobile Money ?",
            "Moov Money ?", "Vous prenez Wave ?",
            "Numéro Wave ?", "Numéro Orange Money ?",
            "Mobile Money accepté ?", "Paiement mobile",
            "Free Money ?", "E-money ?", "Transfert mobile ?",

            # Paiement classique (12 exemples)
            "Espèces ?", "Cash ?", "Carte bancaire ?",
            "Visa ?", "MasterCard ?", "Virement ?",
            "PayPal ?", "Paiement en ligne ?",
            "Chèque ?", "Paiement CB", "Carte bleue ?",
            "Paiement électronique ?",

            # Acompte (12 exemples)
            "Acompte obligatoire ?", "Combien d'acompte ?",
            "Je paye tout maintenant ?", "Avance à verser ?",
            "Dépôt requis ?", "Minimum à payer ?",
            "Arrhes nécessaires ?", "Montant de l'acompte",
            "Paiement partiel ?", "Avance demandée",
            "Pourcentage d'acompte", "Caution à verser ?",

            # Confirmation paiement (12 exemples)
            "J'ai payé", "Paiement envoyé", "Voici mon paiement",
            "Capture du paiement", "Reçu de paiement",
            "Preuve de transfert", "J'envoie la preuve",
            "Screenshot du paiement", "Justificatif",
            "Confirmation de virement", "Paiement effectué",
            "Reçu transaction",

            # Sécurité (10 exemples)
            "Paiement sécurisé ?", "Garantie de paiement ?",
            "C'est sûr ?", "Fiable ?",
            "Sécurité des transactions", "Protection acheteur",
            "Paiement crypté ?", "Données protégées ?",
            "Transaction sûre ?", "Système sécurisé ?"
        ],
        "patterns_regex": [
            r"\b(comment pay|moyen|mode) de paiement\b",
            r"\b(wave|orange money|mtn|moov|mobile money)\b",
            r"\b(acompte|avance|dépôt|minimum)\b",
            r"\b(j'ai payé|paiement envoyé|voici (mon paiement|la preuve))\b"
        ]
    },
    
    # ==========================================================================
    # GROUPE D - APRÈS-VENTE/SAV (Intents 11-12)
    # ==========================================================================
    
    11: {
        "label": "Suivi de commande",
        "mode": "D",
        "description": "Suivi logistique d'une commande en cours",
        "exemples_universels": [
            # Localisation colis (12 exemples)
            "Où est ma commande ?", "Où en est le colis ?",
            "Tracking", "Suivi de commande", "Numéro de suivi",
            "Ma commande arrive quand ?",
            "Position du colis", "Localisation livraison",
            "Géolocalisation commande", "État actuel colis",
            "Où se trouve mon paquet ?", "Tracking number",

            # État avancement (12 exemples)
            "Ça avance ?", "État de ma commande ?",
            "Commande en cours ?", "C'est parti ?",
            "Expédié ?", "En route ?", "En préparation ?",
            "Statut commande", "Progression livraison",
            "Avancement du traitement", "Étape actuelle",
            "Phase de commande ?",

            # Livreur (12 exemples)
            "Le livreur est où ?", "Le livreur arrive quand ?",
            "Numéro du livreur", "Contact livreur",
            "Il est en chemin ?",
            "Coordonnées livreur", "Joindre le livreur",
            "Livreur contactable ?", "Info livreur",
            "Nom du livreur ?", "Tel du coursier",
            "Position du livreur",

            # Livraison (12 exemples)
            "C'est livré ?", "J'ai pas encore reçu",
            "Toujours pas livré", "Quand je reçois ?",
            "Livraison aujourd'hui ?",
            "Déjà arrivé ?", "Reçu la commande ?",
            "Date de réception", "Heure de livraison prévue",
            "Livraison effectuée ?", "Colis reçu ?",
            "Pas encore là",

            # Retard (10 exemples)
            "Pourquoi le retard ?", "C'est en retard",
            "Délai dépassé", "Trop long", "Ça traîne",
            "Retard de livraison", "Problème de délai ?",
            "Livraison tardive", "Dépassement délai",
            "Explication du retard ?"
        ],
        "patterns_regex": [
            r"\b(où (est|en est)|suivi|tracking|localisation)\b.*\b(commande|colis)\b",
            r"\b(arrive quand|état|avancement|en cours)\b",
            r"\b(livreur|livré|reçu|livraison)\b"
        ]
    },
    
    12: {
        "label": "Problème/Réclamation/SAV",
        "mode": "D",
        "description": "Problèmes post-achat, réclamations",
        "exemples_universels": [
            # Problème produit (12 exemples)
            "Produit défectueux", "Ça marche pas", "C'est cassé",
            "Produit abîmé", "Endommagé", "En mauvais état",
            "Pas conforme", "Pas comme sur la photo",
            "Défaut de fabrication", "Vice caché",
            "Problème qualité", "Produit non fonctionnel",

            # Erreur commande (12 exemples)
            "C'est pas le bon produit", "Erreur de commande",
            "J'ai reçu autre chose", "Pas ce que j'ai commandé",
            "Mauvais article", "Erreur de livraison",
            "Produit incorrect", "Commande mélangée",
            "Article différent", "Erreur de référence",
            "Mauvaise taille reçue", "Couleur erronée",

            # Manquant (10 exemples)
            "Il manque un article", "Incomplet", "Pas tout reçu",
            "Où est le reste ?", "Quantité incorrecte",
            "Pièce manquante", "Un article absent",
            "Partie non livrée", "Manque dans le colis",
            "Accessoire absent",

            # Réclamation (12 exemples)
            "Je veux me plaindre", "Réclamation",
            "Pas satisfait", "Déçu", "Mauvaise qualité",
            "Service client", "Porter plainte",
            "Plainte officielle", "Je conteste",
            "Litige achat", "Médiation ?", "SAV svp",

            # Retour/Remboursement (12 exemples)
            "Je veux retourner", "Retour produit",
            "Remboursement", "Rembourser", "Je veux mon argent",
            "Échange possible ?", "Changer le produit",
            "Retour sous garantie", "Procédure de retour ?",
            "Délais de remboursement ?", "Bon d'achat possible ?",
            "Échange standard ?",

            # Annulation (10 exemples)
            "Annuler ma commande", "Annulation",
            "Je ne veux plus", "J'annule tout",
            "Annulez svp", "Stoppez la commande",
            "Annulation immédiate", "Je me rétracte",
            "Droit de rétractation", "Annuler avant envoi"
        ],
        "patterns_regex": [
            r"\b(problème|défectueux|cassé|abîmé|mauvais état)\b",
            r"\b(pas (le bon|conforme|comme)|erreur)\b",
            r"\b(réclamation|plainte|insatisfait|déçu)\b",
            r"\b(retour|rembours|échang|annul)\b"
        ]
    }
}
