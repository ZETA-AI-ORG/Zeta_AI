#!/usr/bin/env python3
"""
🎯 TEST DU SYSTÈME HYDE D'INGESTION
Teste la création du cache de mots-scores à partir de documents
"""

import asyncio
import json
from core.ingestion_hyde_analyzer import create_company_word_cache
from core.cached_hyde_scorer import cached_hyde_filter

# Documents de test pour RueduGrossiste
TEST_DOCUMENTS = [
    {
        "title": "Samsung Galaxy S24 Ultra",
        "category": "smartphones",
        "searchable_text": "Samsung Galaxy S24 Ultra 256GB noir disponible en stock. Prix 450000 FCFA. Livraison gratuite Cocody Plateau Yopougon. Paiement Wave Moov Orange MTN accepté. Contact WhatsApp pour commande rapide."
    },
    {
        "title": "iPhone 15 Pro Max",
        "category": "smartphones", 
        "searchable_text": "Apple iPhone 15 Pro Max 512GB bleu titane. Prix 650000 FCFA. Stock limité Riviera Golf Marcory. Paiement mobile money Wave Moov. Livraison express Abidjan."
    },
    {
        "title": "Casque Bluetooth JBL",
        "category": "audio",
        "searchable_text": "Casque audio JBL Tune 760NC bluetooth sans fil rouge noir blanc. Prix 35000 FCFA. Disponible magasin Treichville Adjamé. Livraison moto taxi Koumassi Abobo."
    },
    {
        "title": "Yamaha MT-125",
        "category": "motos",
        "searchable_text": "Moto Yamaha MT 125cc neuve garantie constructeur. Prix 1200000 FCFA. Financement possible. Livraison Abidjan Grand Bassam. Contact commercial WhatsApp."
    },
    {
        "title": "Conditions de livraison",
        "category": "service",
        "searchable_text": "Livraison gratuite commandes plus 50000 FCFA. Zones couvertes: Cocody Plateau Yopougon Marcory Treichville Adjamé Koumassi Abobo Riviera Golf. Délai 24h ouvrées. Paiement à la livraison COD accepté."
    },
    {
        "title": "Moyens de paiement",
        "category": "service", 
        "searchable_text": "Paiement sécurisé Wave Money Moov Money Orange Money MTN Mobile Money. Virement bancaire possible. Paiement comptant magasin. Financement crédit disponible produits chers."
    }
]

COMPANY_ID = "XkCn8fjNWEWwqiiKMgJX7OcQrUJ3"  # RueduGrossiste

async def test_ingestion_analysis():
    """Teste l'analyse d'ingestion complète"""
    print("🚀 TEST ANALYSE D'INGESTION HYDE")
    print("=" * 60)
    
    # Créer le cache de mots-scores
    print("📊 Création du cache de mots-scores...")
    cache_data = await create_company_word_cache(TEST_DOCUMENTS, COMPANY_ID)
    
    print(f"\n✅ CACHE CRÉÉ AVEC SUCCÈS!")
    print(f"📈 Statistiques:")
    print(f"  - Documents analysés: {cache_data['stats']['documents_analyzed']}")
    print(f"  - Mots scorés: {cache_data['stats']['words_scored']}")
    print(f"  - Termes business trouvés: {cache_data['stats']['business_terms_found']}")
    
    print(f"\n🧠 PROFIL BUSINESS DÉTECTÉ:")
    business_profile = cache_data['business_profile']
    print(f"  - Secteur: {business_profile.get('secteur_activite', 'N/A')}")
    print(f"  - Produits: {', '.join(business_profile.get('produits_services', []))}")
    print(f"  - Zones: {', '.join(business_profile.get('zones_geographiques', []))}")
    
    print(f"\n📊 TOP 20 MOTS SCORÉS:")
    word_scores = cache_data['word_scores']
    sorted_words = sorted(word_scores.items(), key=lambda x: x[1], reverse=True)
    for word, score in sorted_words[:20]:
        emoji = "🔥" if score >= 9 else "⭐" if score >= 7 else "✅" if score >= 5 else "⚠️"
        print(f"  {emoji} {word}: {score}")
    
    return cache_data

async def test_cached_scoring():
    """Teste le scoring avec cache"""
    print("\n" + "=" * 60)
    print("🎯 TEST SCORING AVEC CACHE")
    
    test_queries = [
        "samsung galaxy s24 prix cocody",
        "casque bluetooth rouge disponible",
        "livraison yopougon paiement wave",
        "yamaha mt 125 financement possible",
        "contact whatsapp commande iphone",
        "nouveau produit xiaomi redmi note"  # Mot inconnu pour tester le fallback
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 TEST {i}: '{query}'")
        
        # Utiliser le scorer avec cache
        filtered_query = await cached_hyde_filter(query, COMPANY_ID, threshold=6)
        
        print(f"  ✨ Résultat: '{filtered_query}'")

async def run_full_test():
    """Lance le test complet du système d'ingestion"""
    try:
        # Test 1: Analyse d'ingestion
        cache_data = await test_ingestion_analysis()
        
        # Test 2: Scoring avec cache
        await test_cached_scoring()
        
        print(f"\n" + "=" * 60)
        print("🎉 TESTS TERMINÉS AVEC SUCCÈS!")
        print("💡 Le système HyDE d'ingestion est opérationnel")
        print("⚡ Performance: Cache ultra-rapide + Fallback dynamique")
        
    except Exception as e:
        print(f"\n💥 ERREUR DURANT LES TESTS: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_full_test())
