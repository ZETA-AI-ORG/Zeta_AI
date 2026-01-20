# Référentiel centralisé des variantes (attributs) par catégorie/sous-catégorie
# À compléter/étendre selon les besoins du projet

PRODUCT_VARIANTS = {
    "Bébé & Puériculture": {
        "Couches & lingettes": [
            {"nom": "Taille", "valeurs": ["XS", "S", "M", "L", "XL", "XXL", "3-6kg", "6-12kg", "12-25kg"]},
            {"nom": "Type", "valeurs": ["Couches jetables", "Couches lavables", "Lingettes"]},
            {"nom": "Parfum", "valeurs": ["Aloe Vera", "Camomille", "Non parfumé"]}
        ],
        "Produits de soin pour bébé": [
            {"nom": "Format", "valeurs": ["Flacon", "Spray", "Crème", "Lingettes"]}
        ]
    },
    "Auto & Moto": {
        "Casques moto": [
            {"nom": "Taille", "valeurs": ["XS", "S", "M", "L", "XL"]},
            {"nom": "Couleur", "valeurs": ["Noir", "Blanc", "Rouge", "Bleu", "Vert", "Jaune"]},
            {"nom": "Type", "valeurs": ["Intégral", "Jet", "Modulable", "Cross"]}
        ],
        "Accessoires auto / moto": [
            {"nom": "Type", "valeurs": ["Tapis", "Housse", "Chargeur USB", "Support téléphone"]}
        ]
    },
    "Électronique & Informatique": {
        "Vente de téléphones et accessoires": [
            {"nom": "Stockage", "valeurs": ["32Go", "64Go", "128Go", "256Go"]},
            {"nom": "Couleur", "valeurs": ["Noir", "Blanc", "Bleu", "Rouge"]},
            {"nom": "État", "valeurs": ["Neuf", "Reconditionné"]}
        ],
        "Vente de TV / home cinéma": [
            {"nom": "Taille écran", "valeurs": ["32\"", "43\"", "50\"", "55\"", "65\""]},
            {"nom": "Type", "valeurs": ["LED", "OLED", "QLED"]}
        ]
    },
    "Mode & Prêt-à-porter": {
        "Vêtements femme": [
            {"nom": "Taille", "valeurs": ["XS", "S", "M", "L", "XL", "XXL"]},
            {"nom": "Couleur", "valeurs": ["Noir", "Blanc", "Rouge", "Bleu", "Vert", "Jaune", "Rose", "Beige"]},
            {"nom": "Matière", "valeurs": ["Coton", "Polyester", "Soie", "Lin"]}
        ],
        "Chaussures femme": [
            {"nom": "Pointure", "valeurs": ["35", "36", "37", "38", "39", "40", "41", "42"]}
        ]
    },
    "Maison & Électroménager": {
        "Gros électroménager (frigo, cuisinière, congélateur, lave-linge)": [
            {"nom": "Capacité", "valeurs": ["100L", "200L", "300L", "400L+"]},
            {"nom": "Classe énergie", "valeurs": ["A++", "A+", "B"]}
        ]
    }
    # ... Ajouter d'autres catégories/sous-catégories selon la base produits réelle
}
