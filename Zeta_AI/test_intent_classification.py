#!/usr/bin/env python3
"""
🧪 TEST DE CLASSIFICATION D'INTENTION
Test pour vérifier que "Que vendez vous?" est correctement classifié
"""

import asyncio
import sys
import os

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_intent_classification():
    """Test de classification d'intention"""
    print("🧪 TEST DE CLASSIFICATION D'INTENTION")
    print("=" * 50)
    
    try:
        from core.advanced_intent_classifier import classify_intent_advanced
        
        # Test avec différentes questions
        test_queries = [
            "Que vendez vous?",
            "Quels sont vos produits?",
            "Que proposez-vous?",
            "Montrez-moi votre catalogue",
            "Quels articles avez-vous?",
            "Comment allez-vous?",
            "Bonjour",
            "Combien coûte la livraison?"
        ]
        
        for query in test_queries:
            print(f"\n📝 Question: '{query}'")
            
            result = await classify_intent_advanced(query)
            
            print(f"   Intent: {result.primary_intent.value}")
            print(f"   Confidence: {result.confidence:.3f}")
            print(f"   Requires documents: {result.requires_documents}")
            print(f"   Context hints: {result.context_hints}")
            
            # Vérifier si c'est correct
            if "vendez" in query.lower() or "produits" in query.lower():
                expected = "product_inquiry"
                if result.primary_intent.value == expected:
                    print(f"   ✅ CORRECT")
                else:
                    print(f"   ❌ INCORRECT (attendu: {expected})")
            elif "coûte" in query.lower() or "prix" in query.lower():
                expected = "pricing_info"
                if result.primary_intent.value == expected:
                    print(f"   ✅ CORRECT")
                else:
                    print(f"   ❌ INCORRECT (attendu: {expected})")
            else:
                print(f"   ℹ️  Classification générale")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_intent_classification())
    if success:
        print("\n🎉 TEST TERMINÉ !")
    else:
        print("\n⚠️  TEST ÉCHOUÉ !")
