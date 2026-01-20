"""
🏷️ CATEGORY ATTRIBUTES - Attributs par catégorie e-commerce
Basé sur recherches approfondies des standards e-commerce internationaux
"""

from typing import Dict, List

# ═══════════════════════════════════════════════════════════════════════════════
# ATTRIBUTS PAR CATÉGORIE PRINCIPALE
# ═══════════════════════════════════════════════════════════════════════════════

CATEGORY_ATTRIBUTES: Dict[str, List[str]] = {
    
    # ═══════════════════════════════════════════════════════════
    # MODE & ACCESSOIRES
    # ═══════════════════════════════════════════════════════════
    "Mode & Accessoires": [
        "taille",           # XS, S, M, L, XL, XXL, 36, 38, 40, etc.
        "couleur",          # Noir, Blanc, Rouge, Bleu, etc.
        "matiere",          # Coton, Polyester, Soie, Cuir, etc.
        "genre",            # Homme, Femme, Mixte, Enfant
        "marque",           # Nike, Adidas, Zara, etc.
        "coupe",            # Slim, Regular, Loose, Oversize
        "longueur",         # Court, Mi-long, Long
        "style",            # Casual, Formel, Sport, Traditionnel
        "saison",           # Été, Hiver, Mi-saison, Toute saison
        "pointure",         # 36, 37, 38, 39, 40, 41, 42, etc.
        "largeur",          # Standard, Large, Étroit
        "type_fermeture",   # Boutons, Zip, Élastique, Lacets
        "motif",            # Uni, Rayé, Imprimé, Fleuri
        "col",              # Rond, V, Polo, Chemise
        "manche",           # Courte, Longue, Sans manche, 3/4
    ],
    
    # ═══════════════════════════════════════════════════════════
    # BEAUTÉ & SANTÉ
    # ═══════════════════════════════════════════════════════════
    "Beauté & Santé": [
        "type_peau",        # Normale, Sèche, Grasse, Mixte, Sensible
        "type_cheveux",     # Normaux, Secs, Gras, Bouclés, Crépus
        "volume",           # 50ml, 100ml, 250ml, 500ml, 1L
        "contenance",       # Même que volume
        "marque",           # L'Oréal, Nivea, Dove, etc.
        "parfum",           # Floral, Fruité, Boisé, Oriental
        "spf",              # SPF 15, SPF 30, SPF 50
        "teinte",           # Claire, Moyenne, Foncée, Ébène
        "finition",         # Mat, Brillant, Satiné, Nude
        "format",           # Crème, Gel, Huile, Spray, Poudre
        "age",              # Bébé, Enfant, Adulte, Senior
        "bio",              # Oui, Non
        "vegan",            # Oui, Non
        "sans_parabene",    # Oui, Non
        "dermatologique",   # Testé, Non testé
    ],
    
    # ═══════════════════════════════════════════════════════════
    # ÉLECTRONIQUE & HIGH-TECH
    # ═══════════════════════════════════════════════════════════
    "Électronique & High-Tech": [
        "marque",           # Apple, Samsung, Xiaomi, HP, etc.
        "modele",           # iPhone 15, Galaxy S24, etc.
        "ram",              # 4GB, 8GB, 16GB, 32GB
        "stockage",         # 64GB, 128GB, 256GB, 512GB, 1TB
        "processeur",       # Intel i5, i7, i9, AMD Ryzen
        "taille_ecran",     # 5.5", 6.1", 13", 15.6", 27"
        "resolution",       # HD, Full HD, 4K, 8K
        "systeme",          # Android, iOS, Windows, macOS
        "couleur",          # Noir, Blanc, Bleu, Or, etc.
        "batterie",         # 3000mAh, 4000mAh, 5000mAh
        "connectivite",     # 4G, 5G, WiFi, Bluetooth
        "appareil_photo",   # 12MP, 48MP, 108MP
        "etat",             # Neuf, Reconditionné, Occasion
        "garantie",         # 6 mois, 1 an, 2 ans
        "capacite",         # Pour disques durs, batteries
    ],
    
    # ═══════════════════════════════════════════════════════════
    # MAISON & DÉCORATION
    # ═══════════════════════════════════════════════════════════
    "Maison & Décoration": [
        "dimensions",       # 200x150cm, 80x60x40cm
        "longueur",         # 200cm, 150cm, etc.
        "largeur",          # 90cm, 120cm, etc.
        "hauteur",          # 75cm, 180cm, etc.
        "matiere",          # Bois, Métal, Plastique, Tissu, Verre
        "couleur",          # Blanc, Noir, Beige, Marron, etc.
        "style",            # Moderne, Classique, Scandinave, Africain
        "nombre_places",    # 2, 3, 5, 7 places (canapés)
        "capacite",         # Pour rangements, réfrigérateurs
        "puissance",        # 1000W, 1500W, 2000W (électroménager)
        "classe_energie",   # A+++, A++, A+, A, B
        "volume",           # 200L, 300L (réfrigérateurs)
        "poids",            # 5kg, 10kg, 20kg
        "montage",          # Monté, À monter
        "lavable",          # Oui, Non (textiles)
    ],
    
    # ═══════════════════════════════════════════════════════════
    # ALIMENTATION & BOISSONS
    # ═══════════════════════════════════════════════════════════
    "Alimentation & Boissons": [
        "poids",            # 500g, 1kg, 2kg, 5kg
        "volume",           # 250ml, 500ml, 1L, 1.5L
        "marque",           # Nestlé, Danone, Coca-Cola, etc.
        "origine",          # Côte d'Ivoire, France, Sénégal, etc.
        "bio",              # Oui, Non
        "sans_gluten",      # Oui, Non
        "vegan",            # Oui, Non
        "halal",            # Oui, Non
        "date_expiration",  # JJ/MM/AAAA
        "conditionnement",  # Sachet, Bouteille, Boîte, Carton
        "saveur",           # Vanille, Chocolat, Fraise, Nature
        "type",             # Entier, Demi-écrémé, Écrémé
        "degre_alcool",     # 0%, 5%, 12%, 40% (boissons)
        "format",           # Pack, Unité, Lot
        "conservation",     # Frais, Ambiant, Surgelé
    ],
    
    # ═══════════════════════════════════════════════════════════
    # BÉBÉ & PUÉRICULTURE
    # ═══════════════════════════════════════════════════════════
    "Bébé & Puériculture": [
        "age",              # 0-3 mois, 3-6 mois, 6-12 mois, 1-2 ans
        "taille",           # 1, 2, 3, 4, 5, 6 (couches)
        "poids",            # 0-4kg, 3-8kg, 6-11kg, etc.
        "quantite",         # 30, 50, 100, 150, 300 pcs
        "marque",           # Pampers, Huggies, Nestlé, etc.
        "type",             # Couches, Culottes, Lingettes
        "genre",            # Mixte, Garçon, Fille
        "materiau",         # Coton, Plastique, Silicone
        "capacite",         # 150ml, 250ml, 330ml (biberons)
        "norme",            # CE, ISO, FDA
        "hypoallergenique", # Oui, Non
        "sans_parfum",      # Oui, Non
        "pliable",          # Oui, Non (poussettes)
        "lavable",          # Oui, Non
    ],
    
    # ═══════════════════════════════════════════════════════════
    # LIVRES, MUSIQUE & FILMS
    # ═══════════════════════════════════════════════════════════
    "Livres, Musique & Films": [
        "auteur",           # Nom auteur
        "editeur",          # Maison d'édition
        "langue",           # Français, Anglais, Arabe, etc.
        "nombre_pages",     # 200, 300, 500 pages
        "format",           # Poche, Broché, Relié, Numérique
        "isbn",             # Code ISBN
        "annee",            # 2020, 2021, 2022, etc.
        "genre",            # Roman, Thriller, Science-fiction, etc.
        "artiste",          # Nom artiste (musique)
        "duree",            # 90min, 120min (films)
        "classification",   # Tout public, -12, -16, -18
        "support",          # CD, DVD, Blu-ray, Vinyle, Streaming
        "sous_titres",      # Français, Anglais, etc.
        "edition",          # Standard, Collector, Limitée
    ],
    
    # ═══════════════════════════════════════════════════════════
    # SPORTS & LOISIRS
    # ═══════════════════════════════════════════════════════════
    "Sports & Loisirs": [
        "taille",           # XS, S, M, L, XL, XXL
        "couleur",          # Couleurs équipe, etc.
        "marque",           # Nike, Adidas, Puma, etc.
        "sport",            # Football, Basketball, Running, etc.
        "genre",            # Homme, Femme, Mixte, Enfant
        "materiau",         # Cuir, Synthétique, Caoutchouc
        "poids",            # 5kg, 10kg, 20kg (haltères)
        "diametre",         # 5cm, 10cm (ballons)
        "circonference",    # 68-70cm (ballons)
        "niveau",           # Débutant, Intermédiaire, Expert
        "capacite",         # 2 personnes, 4 personnes (tentes)
        "resistance",       # Eau, Choc, UV
        "pliable",          # Oui, Non
        "reglable",         # Oui, Non
    ],
    
    # ═══════════════════════════════════════════════════════════
    # FOURNITURES SCOLAIRES & BUREAU
    # ═══════════════════════════════════════════════════════════
    "Fournitures Scolaires & Bureau": [
        "nombre_pages",     # 48, 96, 192, 288 pages
        "format",           # A4, A5, A6
        "reglure",          # Grands carreaux, Petits carreaux, Lignes
        "couleur",          # Couleurs variées
        "marque",           # Bic, Pilot, Stabilo, etc.
        "type",             # Stylo, Crayon, Feutre, Marqueur
        "quantite",         # Pack de 10, 20, 50
        "materiau",         # Plastique, Tissu, Cuir
        "capacite",         # 20L, 30L, 40L (sacs)
        "compartiments",    # 1, 2, 3 compartiments
        "rechargeable",     # Oui, Non
        "effacable",        # Oui, Non
        "niveau",           # Primaire, Collège, Lycée, Université
        "fonction",         # Scientifique, Graphique (calculatrices)
    ],
    
    # ═══════════════════════════════════════════════════════════
    # AUTO & MOTO
    # ═══════════════════════════════════════════════════════════
    "Auto & Moto": [
        "marque",           # Michelin, Bridgestone, Total, etc.
        "modele",           # Modèle compatible
        "dimension",        # 195/65 R15 (pneus)
        "capacite",         # 5L, 10L (huiles)
        "voltage",          # 12V, 24V (batteries)
        "amperage",         # 45Ah, 60Ah, 75Ah
        "type",             # Essence, Diesel, Hybride
        "materiau",         # Caoutchouc, Cuir, Tissu
        "couleur",          # Noir, Gris, Beige, etc.
        "taille",           # S, M, L, XL, XXL (casques, gants)
        "norme",            # CE, DOT, ECE
        "saison",           # Été, Hiver, Toute saison (pneus)
        "compatible",       # Liste véhicules compatibles
        "garantie",         # 6 mois, 1 an, 2 ans
    ],
    
    # ═══════════════════════════════════════════════════════════
    # BRICOLAGE & JARDINAGE
    # ═══════════════════════════════════════════════════════════
    "Bricolage & Jardinage": [
        "type",             # Électrique, Manuel, Sans fil
        "puissance",        # 500W, 1000W, 1500W
        "voltage",          # 12V, 18V, 220V
        "materiau",         # Acier, Aluminium, Plastique
        "longueur",         # 30cm, 50cm, 100cm
        "poids",            # 1kg, 5kg, 10kg
        "capacite",         # 10L, 20L, 50L (terreaux)
        "hauteur",          # 2m, 3m, 4m (échelles)
        "marque",           # Bosch, Black & Decker, etc.
        "batterie",         # Lithium, NiMH
        "autonomie",        # 1h, 2h, 4h
        "type_plante",      # Fleur, Légume, Arbre, Arbuste
        "exposition",       # Soleil, Mi-ombre, Ombre
        "arrosage",         # Faible, Moyen, Abondant
    ],
    
    # ═══════════════════════════════════════════════════════════
    # CADEAUX & OCCASIONS
    # ═══════════════════════════════════════════════════════════
    "Cadeaux & Occasions": [
        "occasion",         # Anniversaire, Mariage, Naissance, etc.
        "destinataire",     # Homme, Femme, Enfant, Bébé
        "age",              # 0-2 ans, 3-12 ans, 13-17 ans, Adulte
        "budget",           # 5000-10000, 10000-25000, 25000-50000 FCFA
        "type",             # Physique, Numérique, Carte cadeau
        "valeur",           # 5000, 10000, 25000, 50000 FCFA
        "personnalisable",  # Oui, Non
        "emballage",        # Inclus, Non inclus
        "message",          # Avec carte, Sans carte
        "livraison",        # Express, Standard
    ],
    
    # ═══════════════════════════════════════════════════════════
    # BIJOUX & MONTRES
    # ═══════════════════════════════════════════════════════════
    "Bijoux & Montres": [
        "materiau",         # Or, Argent, Acier, Cuivre, Perles
        "carats",           # 9K, 14K, 18K, 24K
        "pierre",           # Diamant, Rubis, Émeraude, Saphir
        "taille",           # 50, 52, 54, 56, 58 (bagues)
        "longueur",         # 40cm, 45cm, 50cm (colliers)
        "genre",            # Homme, Femme, Mixte
        "marque",           # Rolex, Casio, Fossil, etc.
        "type_mouvement",   # Quartz, Automatique, Mécanique
        "etanche",          # 30m, 50m, 100m, 200m
        "bracelet",         # Cuir, Métal, Silicone, Tissu
        "diametre_cadran",  # 38mm, 40mm, 42mm, 44mm
        "couleur",          # Or, Argent, Noir, Blanc, etc.
        "style",            # Classique, Sport, Moderne, Vintage
        "garantie",         # 1 an, 2 ans, 5 ans
    ],
    
    # ═══════════════════════════════════════════════════════════
    # ANIMAUX
    # ═══════════════════════════════════════════════════════════
    "Animaux": [
        "animal",           # Chien, Chat, Oiseau, Poisson
        "race",             # Labrador, Siamois, Canari, etc.
        "age",              # Chiot, Adulte, Senior
        "poids",            # 1kg, 5kg, 10kg, 20kg
        "type",             # Croquettes, Pâtée, Friandises
        "saveur",           # Poulet, Bœuf, Poisson, Légumes
        "taille",           # S, M, L, XL (colliers, vêtements)
        "materiau",         # Plastique, Métal, Tissu, Bois
        "capacite",         # 50L, 100L, 200L (aquariums)
        "dimensions",       # 60x40x40cm (cages)
        "special",          # Hypoallergénique, Bio, Sans céréales
        "marque",           # Royal Canin, Purina, etc.
    ],
    
    # ═══════════════════════════════════════════════════════════
    # ART & ARTISANAT
    # ═══════════════════════════════════════════════════════════
    "Art & Artisanat": [
        "type",             # Peinture, Sculpture, Textile, Bijoux
        "materiau",         # Bois, Métal, Tissu, Perles, Argile
        "technique",        # Aquarelle, Huile, Acrylique, Batik
        "dimensions",       # 30x40cm, 50x70cm, etc.
        "origine",          # Côte d'Ivoire, Sénégal, Mali, etc.
        "artiste",          # Nom artiste
        "fait_main",        # Oui, Non
        "unique",           # Pièce unique, Série limitée, Production
        "style",            # Traditionnel, Moderne, Contemporain
        "couleur",          # Couleurs dominantes
        "usage",            # Décoration, Utilitaire, Collection
        "certificat",       # Avec, Sans
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTION HELPER
# ═══════════════════════════════════════════════════════════════════════════════

def get_attributes_for_category(category: str) -> List[str]:
    """
    Récupère les attributs pour une catégorie donnée
    
    Args:
        category: Nom de la catégorie
        
    Returns:
        Liste des attributs applicables
    """
    return CATEGORY_ATTRIBUTES.get(category, [])


def get_all_unique_attributes() -> List[str]:
    """Retourne tous les attributs uniques (dédupliqués)"""
    all_attrs = set()
    for attrs in CATEGORY_ATTRIBUTES.values():
        all_attrs.update(attrs)
    return sorted(list(all_attrs))


def search_categories_by_attribute(attribute: str) -> List[str]:
    """Trouve toutes les catégories utilisant un attribut donné"""
    categories = []
    for category, attrs in CATEGORY_ATTRIBUTES.items():
        if attribute in attrs:
            categories.append(category)
    return categories


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("📊 STATISTIQUES ATTRIBUTS:")
    print(f"- Catégories: {len(CATEGORY_ATTRIBUTES)}")
    print(f"- Attributs uniques: {len(get_all_unique_attributes())}")
    
    print("\n🔍 EXEMPLE - Mode & Accessoires:")
    attrs = get_attributes_for_category("Mode & Accessoires")
    print(f"  Attributs: {', '.join(attrs[:10])}...")
    
    print("\n🔍 EXEMPLE - Bébé & Puériculture:")
    attrs = get_attributes_for_category("Bébé & Puériculture")
    print(f"  Attributs: {', '.join(attrs)}")
    
    print("\n🔍 Catégories utilisant 'taille':")
    cats = search_categories_by_attribute("taille")
    print(f"  {len(cats)} catégories: {', '.join(cats[:5])}...")
