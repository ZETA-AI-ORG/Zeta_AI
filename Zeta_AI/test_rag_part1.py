#!/usr/bin/env python3
"""
🧪 TEST RAG PARTIE 1/2 (20 questions)
Pour éviter quota Groq
"""
# Copier le contenu de test_rag_optimized.py
# Mais ne garder que:
# - QUESTIONS PRODUITS (10)
# - QUESTIONS LIVRAISON (10)

# Importer tout depuis test_rag_optimized
import sys
sys.path.insert(0, '.')
from test_rag_optimized import *

# Redéfinir OPTIMIZED_TESTS avec seulement partie 1
OPTIMIZED_TESTS = {
    "1. QUESTIONS PRODUITS (10)": [
        {"question": "Avez-vous des couches pour bébé de 7kg ?", "attendu": "taille 2 ou 3", "type": "produit_poids"},
        {"question": "Combien coûtent vos couches culottes ?", "attendu": "13500 ou 24000", "type": "produit_prix"},
        {"question": "Quelles tailles de couches proposez-vous ?", "attendu": "taille 1 à 6", "type": "produit_gamme"},
        {"question": "Les couches sont vendues par combien ?", "attendu": "150 ou 300 pièces", "type": "produit_lot"},
        {"question": "Quelle différence entre couches à pression et culottes ?", "attendu": "type usage", "type": "produit_difference"},
        {"question": "Prix d'un lot de 300 couches taille 4 ?", "attendu": "22500", "type": "produit_prix_specifique"},
        {"question": "Couches pour nouveau-né disponibles ?", "attendu": "taille 1", "type": "produit_age"},
        {"question": "Vendez-vous des couches adultes ?", "attendu": "oui disponible", "type": "produit_categorie"},
        {"question": "Quelle est votre marque de couches ?", "attendu": "nom marque", "type": "produit_marque"},
        {"question": "Les couches sont-elles de bonne qualité ?", "attendu": "qualité garantie", "type": "produit_qualite"},
    ],
    
    "2. QUESTIONS LIVRAISON (10)": [
        {"question": "Frais de livraison pour Cocody ?", "attendu": "1500", "type": "livraison_zone"},
        {"question": "Vous livrez à Bingerville ?", "attendu": "oui 2000-2500", "type": "livraison_zone_periphe"},
        {"question": "Combien pour livrer à Adjamé ?", "attendu": "1500", "type": "livraison_zone_centrale"},
        {"question": "Livraison gratuite possible ?", "attendu": "non payant", "type": "livraison_gratuite"},
        {"question": "Quels sont vos délais de livraison ?", "attendu": "24-48h", "type": "livraison_delai"},
        {"question": "Prix livraison Grand-Bassam ?", "attendu": "2500 ou 3500", "type": "livraison_hors_abidjan"},
        {"question": "Vous livrez dans toute la Côte d'Ivoire ?", "attendu": "oui", "type": "livraison_couverture"},
        {"question": "Livraison express disponible ?", "attendu": "jour même si avant 11h", "type": "livraison_rapide"},
        {"question": "Où êtes-vous situés ?", "attendu": "en ligne uniquement", "type": "livraison_localisation"},
        {"question": "Comment suivre ma livraison ?", "attendu": "contact whatsapp", "type": "livraison_suivi"},
    ],
}

if __name__ == "__main__":
    print(f"\n{'='*80}")
    print(f"🧪 TEST RAG OPTIMISÉ - PARTIE 1/2 (20 questions)")
    print(f"{'='*80}\n")
    asyncio.run(main())
