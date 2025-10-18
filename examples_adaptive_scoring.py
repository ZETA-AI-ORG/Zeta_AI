#!/usr/bin/env python3
"""
Exemples concrets de scoring adaptatif par secteur d'activité
"""

# === EXEMPLES DE SCORING PAR SECTEUR ===

AUTO_MOTO_SCORING = {
    # Produits (Score 10)
    "casque": 10, "moto": 10, "scooter": 10, "vélo": 10,
    "pneu": 10, "huile": 10, "batterie": 10, "frein": 10,
    
    # Attributs techniques (Score 8-9)
    "intégral": 9, "modulaire": 8, "jet": 8, "cross": 8,
    "rouge": 9, "noir": 9, "blanc": 9, "bleu": 8,
    "cylindrée": 8, "puissance": 8, "vitesse": 7,
    
    # Services (Score 7-8)
    "réparation": 8, "entretien": 8, "révision": 7,
    "installation": 7, "garantie": 8,
    
    # Actions (Score 6-7)
    "essayer": 6, "tester": 6, "comparer": 6,
    
    # Stop words (Score 0-2)
    "je": 0, "veux": 4, "cherche": 3
}

ELECTRONIQUE_SCORING = {
    # Produits (Score 10)
    "téléphone": 10, "smartphone": 10, "tablette": 10,
    "ordinateur": 10, "laptop": 10, "écran": 10,
    
    # Marques (Score 9)
    "samsung": 9, "iphone": 9, "apple": 9, "huawei": 9,
    "xiaomi": 9, "oppo": 8, "tecno": 8,
    
    # Spécifications (Score 8)
    "gigaoctet": 8, "mémoire": 8, "stockage": 8,
    "batterie": 8, "chargeur": 8, "écouteurs": 8,
    "caméra": 8, "photo": 7, "vidéo": 7,
    
    # Attributs (Score 7-8)
    "neuf": 8, "occasion": 7, "reconditionné": 7,
    "garantie": 8, "original": 8, "copie": 3
}

MODE_BEAUTE_SCORING = {
    # Vêtements (Score 10)
    "robe": 10, "chemise": 10, "pantalon": 10, "chaussure": 10,
    "sac": 10, "montre": 10, "bijou": 10,
    
    # Beauté (Score 10)
    "parfum": 10, "maquillage": 10, "crème": 10,
    "rouge": 9, "fond": 8, "mascara": 8,
    
    # Attributs (Score 8-9)
    "taille": 9, "couleur": 9, "style": 8, "tendance": 8,
    "marque": 8, "designer": 7, "collection": 7,
    "petit": 8, "moyen": 8, "grand": 8, "xl": 8,
    
    # Matières (Score 7)
    "coton": 7, "soie": 7, "cuir": 7, "synthétique": 6
}

ALIMENTATION_SCORING = {
    # Produits de base (Score 10)
    "riz": 10, "huile": 10, "sucre": 10, "farine": 10,
    "poisson": 10, "viande": 10, "poulet": 10,
    
    # Légumes/Fruits (Score 10)
    "tomate": 10, "oignon": 10, "carotte": 10,
    "banane": 10, "orange": 10, "ananas": 10,
    
    # Qualité (Score 8-9)
    "frais": 9, "bio": 8, "local": 8, "importé": 7,
    "qualité": 8, "premium": 7,
    
    # Unités (Score 8)
    "kilogramme": 8, "kg": 8, "litre": 8, "paquet": 7,
    "sac": 7, "boîte": 7, "bouteille": 7
}

# === EXEMPLES DE REQUÊTES ET SCORING ===

EXEMPLES_SCORING = {
    "auto_moto": {
        "requete": "je veux casque intégral noir combien",
        "scores": {"je": 0, "veux": 4, "casque": 10, "intégral": 9, "noir": 9, "combien": 10},
        "filtre_seuil_6": "casque intégral noir combien",
        "resultat": "Parfait pour recherche produits moto"
    },
    
    "electronique": {
        "requete": "samsung galaxy s24 prix disponible",
        "scores": {"samsung": 9, "galaxy": 8, "s24": 8, "prix": 10, "disponible": 10},
        "filtre_seuil_6": "samsung galaxy s24 prix disponible",
        "resultat": "Recherche précise smartphone"
    },
    
    "mode": {
        "requete": "robe rouge taille m prix",
        "scores": {"robe": 10, "rouge": 9, "taille": 9, "m": 8, "prix": 10},
        "filtre_seuil_6": "robe rouge taille m prix",
        "resultat": "Requête mode optimale"
    },
    
    "alimentation": {
        "requete": "riz local 25kg prix livraison",
        "scores": {"riz": 10, "local": 8, "25kg": 8, "prix": 10, "livraison": 10},
        "filtre_seuil_6": "riz local 25kg prix livraison",
        "resultat": "Recherche alimentaire complète"
    }
}

# === APPRENTISSAGE AUTOMATIQUE ===

APPRENTISSAGE_EXEMPLE = {
    "nouveau_mot": "bluetooth",
    "contexte": "écouteurs bluetooth sans fil",
    "secteur": "electronique",
    "hyde_prompt": """
    Secteur: Électronique
    Requête: "écouteurs bluetooth sans fil"
    Mot: "bluetooth"
    
    Note 0-10 pour pertinence électronique:
    Réponse HyDE: 8
    """,
    "sauvegarde": "learned_scores_TechStore.json → bluetooth: 8",
    "reutilisation": "Prochaine requête avec 'bluetooth' → Score 8 instantané"
}

if __name__ == "__main__":
    print("🎯 EXEMPLES DE SCORING ADAPTATIF PAR SECTEUR")
    print("=" * 60)
    
    for secteur, exemple in EXEMPLES_SCORING.items():
        print(f"\n📱 SECTEUR: {secteur.upper()}")
        print(f"Requête: '{exemple['requete']}'")
        print("Scores:", exemple['scores'])
        print(f"Filtré: '{exemple['filtre_seuil_6']}'")
        print(f"→ {exemple['resultat']}")
    
    print(f"\n🧠 APPRENTISSAGE AUTOMATIQUE:")
    print(f"Nouveau mot: {APPRENTISSAGE_EXEMPLE['nouveau_mot']}")
    print(f"HyDE score: 8 → Sauvegardé pour réutilisation")
