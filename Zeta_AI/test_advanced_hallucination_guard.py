"""
🧪 TEST ADVANCED HALLUCINATION GUARD
Test du nouveau système hybride de détection d'hallucination
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.advanced_hallucination_guard import AdvancedHallucinationGuard

async def test_advanced_hallucination_guard():
    """Test du système hybride de détection d'hallucination"""
    
    print("🧪 TEST ADVANCED HALLUCINATION GUARD")
    print("=" * 50)
    
    guard = AdvancedHallucinationGuard()
    
    # Test 1: Cas avec documents et réponse correcte
    print("\n📋 TEST 1: Réponse correcte avec documents")
    
    supabase_results = [
        {"content": "Taille 2 - 3 à 8 kg - 300 couches | 18.900 F CFA", "score": 0.8}
    ]
    meili_results = [
        {"content": "Couches à pression disponibles taille 2", "score": 0.9}
    ]
    supabase_context = "Taille 2 - 3 à 8 kg - 300 couches | 18.900 F CFA"
    meili_context = "Couches à pression disponibles taille 2"
    
    query = "Avez-vous des couches taille 2 ?"
    response = "Oui, nous avons des couches taille 2 pour enfants de 3 à 8 kg au prix de 18.900 F CFA."
    
    result = await guard.check_response(
        user_query=query,
        ai_response=response,
        supabase_results=supabase_results,
        meili_results=meili_results,
        supabase_context=supabase_context,
        meili_context=meili_context
    )
    
    print(f"✅ Documents trouvés: {result.documents_found}")
    print(f"✅ Corrélation: {result.correlation_score:.2f}")
    print(f"✅ Fidélité: {result.faithfulness_score:.2f}")
    print(f"✅ Score final: {result.confidence_score:.2f}")
    print(f"✅ Sécurisé: {result.is_safe}")
    print(f"✅ Issues: {result.issues_detected}")
    
    # Test 2: Cas sans documents (hallucination probable)
    print("\n📋 TEST 2: Réponse sans documents")
    
    result2 = await guard.check_response(
        user_query="Avez-vous des casques violets ?",
        ai_response="Oui, nous avons des casques violets à 25.000 FCFA",
        supabase_results=[],
        meili_results=[],
        supabase_context="",
        meili_context=""
    )
    
    print(f"❌ Documents trouvés: {result2.documents_found}")
    print(f"❌ Score final: {result2.confidence_score:.2f}")
    print(f"❌ Sécurisé: {result2.is_safe}")
    print(f"❌ Suggestion: {result2.suggested_response}")
    
    # Test 3: Cas avec documents mais réponse incorrecte
    print("\n📋 TEST 3: Réponse incorrecte malgré documents")
    
    result3 = await guard.check_response(
        user_query="Quel est le prix des couches taille 2 ?",
        ai_response="Les couches taille 2 coûtent 50.000 FCFA",
        supabase_results=supabase_results,
        meili_results=meili_results,
        supabase_context=supabase_context,
        meili_context=meili_context
    )
    
    print(f"⚠️ Documents trouvés: {result3.documents_found}")
    print(f"⚠️ Corrélation: {result3.correlation_score:.2f}")
    print(f"⚠️ Fidélité: {result3.faithfulness_score:.2f}")
    print(f"⚠️ Score final: {result3.confidence_score:.2f}")
    print(f"⚠️ Sécurisé: {result3.is_safe}")
    print(f"⚠️ Issues: {result3.issues_detected}")
    
    print("\n🎯 RÉSUMÉ DES TESTS:")
    print(f"Test 1 (Correct): {'✅ PASSÉ' if result.is_safe else '❌ ÉCHOUÉ'}")
    print(f"Test 2 (Sans docs): {'✅ BLOQUÉ' if not result2.is_safe else '❌ RATÉ'}")
    print(f"Test 3 (Prix faux): {'✅ DÉTECTÉ' if not result3.is_safe else '❌ RATÉ'}")

if __name__ == "__main__":
    asyncio.run(test_advanced_hallucination_guard())
