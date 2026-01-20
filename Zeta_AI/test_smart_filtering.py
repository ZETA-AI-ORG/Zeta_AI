#!/usr/bin/env python3
"""
Test du nouveau système de filtrage intelligent pour MeiliSearch
Vérifie que les requêtes problématiques sont maintenant correctement filtrées
"""

import os
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.append(str(Path(__file__).parent))

from core.smart_stopwords import filter_query_for_meilisearch

def test_smart_filtering():
    """Test du nouveau système de filtrage intelligent"""
    
    print("🧠 TEST DU FILTRAGE INTELLIGENT")
    print("=" * 60)
    
    # Requêtes problématiques identifiées dans les tests précédents
    test_cases = [
        {
            "query": "Bonjour, je veux le casque rouge c'est combien?",
            "expected_keywords": ["casque", "rouge", "combien"],
            "should_remove": ["bonjour", "je", "veux", "le", "c'est"]
        },
        {
            "query": "Je cherche un casque rouge disponible",
            "expected_keywords": ["casque", "rouge", "disponible"],
            "should_remove": ["je", "cherche", "un"]
        },
        {
            "query": "Prix casque rouge livraison cocody",
            "expected_keywords": ["prix", "casque", "rouge", "livraison", "cocody"],
            "should_remove": []
        },
        {
            "query": "Whatsapp contact casque rouge",
            "expected_keywords": ["whatsapp", "contact", "casque", "rouge"],
            "should_remove": []
        },
        {
            "query": "Bonsoir, avez-vous des motos en stock?",
            "expected_keywords": ["motos", "stock"],
            "should_remove": ["bonsoir", "avez", "vous", "des", "en"]
        },
        {
            "query": "Livraison à Cocody avec paiement Wave",
            "expected_keywords": ["livraison", "cocody", "paiement", "wave"],
            "should_remove": ["à", "avec"]
        },
        {
            "query": "Je cherche casque rouge disponible à Yopougon",
            "expected_keywords": ["casque", "rouge", "disponible", "yopougon"],
            "should_remove": ["je", "cherche", "à"]
        },
        {
            "query": "Paiement Moov Money accepté pour livraison Plateau?",
            "expected_keywords": ["paiement", "moov", "money", "livraison", "plateau"],
            "should_remove": ["accepté", "pour"]
        },
        {
            "query": "Transport vers Abobo avec Orange Money",
            "expected_keywords": ["transport", "abobo", "orange", "money"],
            "should_remove": ["vers", "avec"]
        },
        {
            "query": "Livraison Riviera-Golf paiement MTN Mobile Money",
            "expected_keywords": ["livraison", "riviera-golf", "paiement", "mtn", "mobile", "money"],
            "should_remove": []
        }
    ]
    
    success_count = 0
    total_tests = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        query = test_case["query"]
        expected = test_case["expected_keywords"]
        should_remove = test_case["should_remove"]
        
        print(f"\n📝 TEST {i}: '{query}'")
        print("-" * 40)
        
        # Appliquer le filtrage
        filtered = filter_query_for_meilisearch(query)
        filtered_words = filtered.lower().split()
        
        print(f"Original: {query}")
        print(f"Filtré:   {filtered}")
        
        # Vérifier que les mots essentiels sont conservés
        missing_keywords = []
        for keyword in expected:
            if keyword.lower() not in filtered_words:
                missing_keywords.append(keyword)
        
        # Vérifier que les mots indésirables sont supprimés
        unwanted_present = []
        for unwanted in should_remove:
            if unwanted.lower() in filtered_words:
                unwanted_present.append(unwanted)
        
        # Évaluer le résultat
        if not missing_keywords and not unwanted_present:
            print("✅ SUCCÈS - Filtrage correct")
            success_count += 1
        else:
            print("❌ ÉCHEC")
            if missing_keywords:
                print(f"   Mots-clés manquants: {missing_keywords}")
            if unwanted_present:
                print(f"   Mots indésirables présents: {unwanted_present}")
    
    print("\n" + "=" * 60)
    print(f"📊 RÉSULTATS: {success_count}/{total_tests} tests réussis")
    
    if success_count == total_tests:
        print("🎉 TOUS LES TESTS RÉUSSIS - Le filtrage intelligent fonctionne!")
    else:
        print("⚠️  Certains tests ont échoué - Ajustements nécessaires")
    
    return success_count == total_tests

def test_edge_cases():
    """Test des cas limites"""
    
    print("\n🔍 TEST DES CAS LIMITES")
    print("=" * 60)
    
    edge_cases = [
        "",  # Requête vide
        "bonjour",  # Que des stop words
        "le la les",  # Que des articles
        "combien",  # Un seul mot-clé essentiel
        "casque rouge prix disponible livraison cocody",  # Que des mots-clés
    ]
    
    for query in edge_cases:
        filtered = filter_query_for_meilisearch(query)
        print(f"'{query}' → '{filtered}'")

if __name__ == "__main__":
    # Test principal
    success = test_smart_filtering()
    
    # Test des cas limites
    test_edge_cases()
    
    print(f"\n{'🎉 FILTRAGE INTELLIGENT VALIDÉ' if success else '⚠️ AJUSTEMENTS NÉCESSAIRES'}")
