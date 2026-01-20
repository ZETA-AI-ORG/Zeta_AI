#!/usr/bin/env python3
"""
Test des améliorations MeiliSearch pour vérifier que les requêtes problématiques
fonctionnent maintenant avec le filtrage amélioré et les fallbacks.
"""

import os
import sys
import asyncio
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.append(str(Path(__file__).parent))

from database.vector_store import search_meili_keywords
from core.preprocessing import universal_preprocessor
from utils import log3

# Configuration pour les tests
os.environ["DEBUG_PREPROCESS"] = "1"

async def test_meili_improvements():
    """Test des améliorations MeiliSearch"""
    
    # Company ID de test (RUEDUGROSSISTE)
    company_id = "XkCn8fjNWEWwqiiKMgJX7OcQrUJ3"
    
    # Requêtes de test problématiques
    test_queries = [
        "bonsoir je veux le casque rouge c est combien?",
        "casque rouge prix",
        "combien coûte casque rouge",
        "je cherche casque rouge disponible",
        "prix casque rouge livraison cocody",
        "casque rouge wave paiement",
        "whatsapp contact casque rouge"
    ]
    
    print("🔍 TEST DES AMÉLIORATIONS MEILISEARCH")
    print("=" * 60)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 TEST {i}: '{query}'")
        print("-" * 40)
        
        # Test du preprocessing amélioré
        print("🔧 PREPROCESSING:")
        # Utiliser le système de scoring HyDE amélioré
        from core.improved_hyde_scorer import improved_hyde_filter
        processed = await improved_hyde_filter(query, "RueduGrossiste", threshold=6)
        print(f"  Original: {query}")
        print(f"  Filtré:   {processed}")
        
        # Test de la recherche MeiliSearch
        print("\n🔍 RECHERCHE MEILISEARCH:")
        try:
            start_time = asyncio.get_event_loop().time()
            
            # Recherche avec fallbacks
            results = await search_meili_keywords(query, company_id)
            
            end_time = asyncio.get_event_loop().time()
            duration = (end_time - start_time) * 1000
            
            if results and results.strip():
                print(f"  ✅ SUCCÈS ({duration:.1f}ms)")
                print(f"  📄 Résultats: {len(results)} caractères")
                # Afficher un extrait des résultats
                preview = results[:200] + "..." if len(results) > 200 else results
                print(f"  📋 Aperçu: {preview}")
            else:
                print(f"  ❌ ÉCHEC ({duration:.1f}ms) - Aucun résultat")
                
        except Exception as e:
            print(f"  💥 ERREUR: {e}")
        
        print("\n" + "=" * 60)

def test_business_words():
    """Test des nouveaux mots-clés business"""
    
    print("\n🎯 TEST DES MOTS-CLÉS BUSINESS")
    print("=" * 60)
    
    test_words = [
        "combien", "veux", "rouge", "casque", "prix", "wave", 
        "whatsapp", "cocody", "livraison", "disponible"
    ]
    
    for word in test_words:
        # Utiliser le système de scoring HyDE amélioré
        try:
            from core.improved_hyde_scorer import ImprovedHydeScorer
            scorer = ImprovedHydeScorer("RueduGrossiste")
            score = scorer.score_word(word)
            is_business = score >= 5  # Seuil de pertinence business
            status = "✅" if is_business else "❌"
            print(f"  {status} '{word}' -> Score: {score} ({'Business' if is_business else 'Non-business'})")
        except Exception as e:
            print(f"  ⚠️ '{word}' -> Erreur: {e}")

if __name__ == "__main__":
    # Test des mots-clés business
    test_business_words()
    
    # Test des améliorations MeiliSearch
    asyncio.run(test_meili_improvements())
    
    print("\n🎉 TESTS TERMINÉS")
