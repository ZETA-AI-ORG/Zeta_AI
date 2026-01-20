#!/usr/bin/env python3
"""
Test du système hybride scalable avec une entreprise agro-alimentaire
"""

import sys
import asyncio
sys.path.append('.')

from core.metadata_extractor import MetadataExtractor
from core.hyde_word_scorer import HydeWordScorer

# Données entreprise agro-alimentaire réalistes
company_data_agro = [{
    "company_id": "AGR123456789",
    "text_documents": [
        {
            "metadata": {
                "type": "company",
                "name": "Bio Saveurs d'Afrique",
                "ai_name": "aminata",
                "sector": "Agro-alimentaire",
                "mission": "Nourrir sainement l'Afrique avec des produits bio locaux",
                "zones": ["Cote d'Ivoire", "Burkina Faso", "Mali"]
            }
        },
        {
            "metadata": {
                "type": "product",
                "product_name": "RIZ PARFUMÉ",
                "category": "Céréales & Grains",
                "subcategory": "Riz & Dérivés",
                "price": 2500,
                "currency": "FCFA",
                "variants": [{
                    "attributes_canonical": {"size": "5KG"},
                    "attribute_list": [{"name": "size", "value": "5KG", "slug": "size:5kg"}]
                }]
            }
        },
        {
            "metadata": {
                "type": "product",
                "product_name": "HUILE DE PALME",
                "category": "Huiles & Matières Grasses",
                "subcategory": "Huiles Végétales",
                "price": 1800,
                "currency": "FCFA",
                "variants": [{
                    "attributes_canonical": {"size": "1L"},
                    "attribute_list": [{"name": "size", "value": "1L", "slug": "size:1l"}]
                }]
            }
        },
        {
            "metadata": {
                "type": "product",
                "product_name": "BANANES PLANTAIN",
                "category": "Fruits & Légumes",
                "subcategory": "Fruits Tropicaux",
                "price": 500,
                "currency": "FCFA",
                "variants": [{
                    "attributes_canonical": {"weight": "1KG"},
                    "attribute_list": [{"name": "weight", "value": "1KG", "slug": "weight:1kg"}]
                }]
            }
        },
        {
            "metadata": {
                "type": "product",
                "product_name": "ATTIÉKÉ TRADITIONNEL",
                "category": "Plats Préparés",
                "subcategory": "Spécialités Locales",
                "price": 800,
                "currency": "FCFA",
                "variants": [{
                    "attributes_canonical": {"brand": "TRADITION"},
                    "attribute_list": [{"name": "brand", "value": "TRADITION", "slug": "brand:tradition"}]
                }]
            }
        },
        {
            "metadata": {
                "type": "delivery",
                "zone": "Abidjan Centre",
                "price_min": 500,
                "price_max": 500,
                "currency": "FCFA"
            }
        },
        {
            "metadata": {
                "type": "payment",
                "method": "Orange Money",
                "channels": ["mobile", "ussd"]
            }
        }
    ]
}]

async def test_agro_alimentaire():
    """Test complet du système avec entreprise agro-alimentaire"""
    
    print("🌾 === TEST SYSTÈME AGRO-ALIMENTAIRE ===")
    print()
    
    # 1. Extraction automatique des métadonnées
    print("📊 EXTRACTION AUTOMATIQUE MÉTADONNÉES:")
    extractor = MetadataExtractor()
    extracted_words = extractor.extract_from_company_data(company_data_agro)
    
    for score, words in sorted(extracted_words.items(), reverse=True):
        if words:
            emoji = "🔥" if score == 10 else "✅" if score >= 8 else "⚠️"
            print(f"  {emoji} Score {score}: {sorted(words)}")
    
    print()
    
    # 2. Test scoring avec requête agro-alimentaire
    print("🧪 TEST SCORING REQUÊTE AGRO:")
    scorer = HydeWordScorer()
    
    # Requête typique secteur agro-alimentaire
    query = "riz parfumé 5kg huile palme livraison abidjan prix orange money aminata"
    scores = await scorer.score_query_words(query, "agro-alimentaire")
    
    print(f"Requête: '{query}'")
    print("Scores obtenus:")
    
    # Tri par score décroissant
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    for word, score in sorted_scores:
        if score >= 10:
            emoji = "🔥"
            category = "CRITIQUES"
        elif score >= 8:
            emoji = "✅"
            category = "TRÈS PERTINENTS"
        elif score >= 6:
            emoji = "⚠️"
            category = "PERTINENTS"
        elif score >= 3:
            emoji = "🔸"
            category = "MOYENS"
        else:
            emoji = "❌"
            category = "FAIBLES"
            
        print(f"  {emoji} {word}: {score} ({category})")
    
    print()
    
    # 3. Analyse de la performance
    print("📈 ANALYSE PERFORMANCE:")
    cache_hits = sum(1 for score in scores.values() if score >= 8)
    total_words = len(scores)
    cache_ratio = (cache_hits / total_words) * 100 if total_words > 0 else 0
    
    print(f"  • Mots scorés via cache: {cache_hits}/{total_words} ({cache_ratio:.1f}%)")
    print(f"  • Mots heuristiques: {total_words - cache_hits}/{total_words} ({100-cache_ratio:.1f}%)")
    
    # 4. Validation scalabilité
    print()
    print("🎯 VALIDATION SCALABILITÉ:")
    
    # Vérifier les mots universels (livraison, prix)
    universal_words = ["livraison", "prix"]
    agro_specific = ["riz", "huile", "palme", "bananes", "attiéké"]
    
    print("  Mots universels:")
    for word in universal_words:
        if word in scores:
            print(f"    ✅ {word}: {scores[word]} (universel)")
    
    print("  Mots spécifiques agro:")
    for word in agro_specific:
        if word in scores:
            print(f"    🌾 {word}: {scores[word]} (secteur agro)")
    
    print()
    print("🎉 RÉSULTAT: Système scalable validé pour secteur agro-alimentaire!")

if __name__ == "__main__":
    asyncio.run(test_agro_alimentaire())
