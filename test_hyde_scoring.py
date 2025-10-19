#!/usr/bin/env python3
"""
Test du système de scoring HyDE dynamique
"""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from core.hyde_word_scorer import HydeWordScorer

async def test_hyde_scoring():
    """Test complet du système de scoring HyDE"""
    
    print("🧠 TEST DU SYSTÈME DE SCORING HYDE DYNAMIQUE")
    print("=" * 70)
    
    scorer = HydeWordScorer()
    
    test_queries = [
        "Bonjour, je veux le casque rouge c'est combien?",
        "Combien coûte le casque rouge?", 
        "Je cherche un casque rouge disponible",
        "Livraison à Cocody avec paiement Wave",
        "Whatsapp contact pour casque rouge",
        "Bonsoir, avez-vous des motos en stock?",
        "Prix casque rouge livraison cocody"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 TEST {i}: '{query}'")
        print("-" * 50)
        
        # 1. Scorer tous les mots
        word_scores = await scorer.score_query_words(query)
        
        # 2. Afficher les scores triés
        print("🎯 SCORES PAR MOT:")
        for word, score in sorted(word_scores.items(), key=lambda x: x[1], reverse=True):
            emoji = "🔥" if score >= 8 else "✅" if score >= 6 else "⚠️" if score >= 3 else "❌"
            print(f"   {emoji} {word}: {score}")
        
        # 3. Tester différents seuils
        print("\n🔍 FILTRAGE PAR SEUILS:")
        for threshold in [8, 6, 4, 2]:
            filtered_words = scorer.filter_by_threshold(word_scores, threshold)
            filtered_query = ' '.join(filtered_words)
            print(f"   Seuil {threshold}: '{filtered_query}'")
        
        # 4. Résultat final avec seuil optimal
        final_query = await scorer.smart_filter_query(query, threshold=6)
        print(f"\n✨ RÉSULTAT FINAL (seuil 6): '{final_query}'")
        
        print("\n" + "=" * 70)

if __name__ == "__main__":
    asyncio.run(test_hyde_scoring())
