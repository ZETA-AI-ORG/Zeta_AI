#!/usr/bin/env python3
"""
Test du système HyDE modifié pour vérifier:
1. Que tous les nombres reçoivent un score de 0
2. Que les logs détaillés fonctionnent correctement
3. Que la classification par score est correcte
"""

import asyncio
import sys
import os

# Ajouter le répertoire parent au path pour les imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.hyde_word_scorer import HydeWordScorer

async def test_numbers_scoring():
    """Test spécifique pour vérifier que les nombres sont scorés à 0"""
    
    scorer = HydeWordScorer()
    
    test_queries_with_numbers = [
        "Bonjour, je veux le casque rouge à 3500 FCFA",
        "Combien coûte le casque? 5000 ou 6500?", 
        "Livraison à Cocody pour 1500fcfa",
        "Prix casque rouge 3500f disponible?",
        "Contact WhatsApp pour casque 6500 FCFA",
        "Je cherche un produit à 2500cfa maximum",
        "Paiement Wave de 4000 FCFA possible?",
        "Casque noir à €50 ou $75 disponible?"
    ]
    
    print("🧪 TEST SCORING NOMBRES = 0")
    print("=" * 60)
    
    for i, query in enumerate(test_queries_with_numbers, 1):
        print(f"\n📝 TEST {i}: '{query}'")
        print("-" * 50)
        
        # Scorer les mots avec logs détaillés
        word_scores = await scorer.score_query_words(query)
        
        # Vérifier que tous les nombres ont un score de 0
        numbers_found = []
        for word, score in word_scores.items():
            if scorer._is_numeric(word):
                numbers_found.append((word, score))
                if score != 0:
                    print(f"❌ ERREUR: Le nombre '{word}' a un score de {score} au lieu de 0!")
                else:
                    print(f"✅ OK: Le nombre '{word}' a bien un score de 0")
        
        if not numbers_found:
            print("ℹ️  Aucun nombre détecté dans cette requête")
        
        print(f"📊 Total mots: {len(word_scores)}, Nombres détectés: {len(numbers_found)}")

async def test_detailed_logging():
    """Test pour vérifier les logs détaillés"""
    
    scorer = HydeWordScorer()
    
    test_query = "Bonjour, je veux le casque rouge à 3500 FCFA livraison Cocody"
    
    print("\n\n🔍 TEST LOGS DÉTAILLÉS")
    print("=" * 60)
    print(f"Requête test: '{test_query}'")
    print("-" * 50)
    
    # Cette fonction va automatiquement générer les logs détaillés
    word_scores = await scorer.score_query_words(test_query)
    
    # Affichage manuel pour vérification
    sorted_scores = sorted(word_scores.items(), key=lambda x: x[1], reverse=True)
    
    print("\n📋 RÉSUMÉ MANUEL DES SCORES:")
    for word, score in sorted_scores:
        emoji = "🔥" if score == 10 else "✅" if score >= 8 else "⚠️" if score >= 6 else "🔸" if score >= 3 else "❌"
        number_flag = " [NOMBRE]" if scorer._is_numeric(word) else ""
        print(f"  {emoji} {word}: {score}{number_flag}")

async def test_numeric_detection():
    """Test pour vérifier la détection des nombres"""
    
    scorer = HydeWordScorer()
    
    test_words = [
        # Nombres purs
        "3500", "5000", "1500", "250",
        # Montants FCFA
        "3500fcfa", "5000f", "1500cfa", "2500fcf",
        # Préfixes
        "fcfa3500", "f5000",
        # Autres devises
        "50€", "$75", "£100", "¥500",
        # Devises préfixe
        "€50", "$75", "£100", "¥500",
        # Mots normaux (ne doivent PAS être détectés)
        "casque", "rouge", "livraison", "cocody", "wave",
        # Mots avec chiffres mais pas que des chiffres
        "casque3", "rouge2", "v2", "iphone12"
    ]
    
    print("\n\n🔢 TEST DÉTECTION NUMÉRIQUE")
    print("=" * 60)
    
    for word in test_words:
        is_numeric = scorer._is_numeric(word)
        status = "✅ NOMBRE" if is_numeric else "❌ PAS NOMBRE"
        print(f"{status}: '{word}'")

async def main():
    """Fonction principale de test"""
    
    print("🚀 DÉMARRAGE DES TESTS HYDE AMÉLIORÉ")
    print("=" * 80)
    
    await test_numbers_scoring()
    await test_detailed_logging() 
    await test_numeric_detection()
    
    print("\n\n✨ TESTS TERMINÉS")
    print("Vérifiez les logs [HYDE_SCORER_DETAILED] pour voir les détails complets!")

if __name__ == "__main__":
    asyncio.run(main())
