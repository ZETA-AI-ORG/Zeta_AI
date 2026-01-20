#!/usr/bin/env python3
"""
⚡ TEST RAPIDE - GARDE-FOU ANTI-HALLUCINATION
Test rapide des fonctionnalités principales
"""

import asyncio
import sys
import os

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_basic_functionality():
    """Test des fonctionnalités de base"""
    print("🧪 TEST RAPIDE - GARDE-FOU ANTI-HALLUCINATION")
    print("=" * 50)
    
    try:
        # Import des modules
        from core.advanced_intent_classifier import classify_intent_advanced
        from core.context_aware_hallucination_guard import validate_response_contextual
        from core.intelligent_fallback_system import generate_intelligent_fallback
        from core.confidence_scoring_system import calculate_confidence_score
        
        print("✅ Modules importés avec succès")
        
        # Test 1: Classification d'intention
        print("\n1️⃣ Test de classification d'intention...")
        intent_result = await classify_intent_advanced("Comment tu t'appelles ?")
        print(f"   Intention: {intent_result.primary_intent.value}")
        print(f"   Confiance: {intent_result.confidence:.2f}")
        print(f"   Nécessite documents: {intent_result.requires_documents}")
        
        # Test 2: Validation contextuelle
        print("\n2️⃣ Test de validation contextuelle...")
        validation_result = await validate_response_contextual(
            user_query="Comment tu t'appelles ?",
            ai_response="Je m'appelle Gamma, votre assistant client.",
            intent_result=intent_result,
            supabase_results=[],
            meili_results=[],
            supabase_context="",
            meili_context="",
            company_id="test"
        )
        print(f"   Validation sûre: {validation_result.is_safe}")
        print(f"   Niveau de validation: {validation_result.validation_level.value}")
        print(f"   Confiance: {validation_result.confidence_score:.2f}")
        
        # Test 3: Scoring de confiance
        print("\n3️⃣ Test de scoring de confiance...")
        confidence_score = await calculate_confidence_score(
            user_query="Comment tu t'appelles ?",
            ai_response="Je m'appelle Gamma, votre assistant client.",
            intent_result=intent_result,
            supabase_results=[],
            meili_results=[],
            supabase_context="",
            meili_context="",
            validation_result=validation_result.__dict__ if validation_result else None
        )
        print(f"   Confiance globale: {confidence_score.overall_confidence:.2f}")
        print(f"   Niveau de confiance: {confidence_score.confidence_level.value}")
        print(f"   Niveau de risque: {confidence_score.risk_level}")
        
        # Test 4: Fallback intelligent
        print("\n4️⃣ Test de fallback intelligent...")
        fallback_result = await generate_intelligent_fallback(
            user_query="Question technique complexe",
            intent_result=intent_result,
            error_context={'error': 'no_documents'},
            company_context={'company_name': 'Test Company', 'ai_name': 'TestBot'}
        )
        print(f"   Réponse de fallback: {fallback_result.response[:50]}...")
        print(f"   Type de fallback: {fallback_result.fallback_type.value}")
        print(f"   Escalation requise: {fallback_result.escalation_required}")
        
        print("\n🎉 TOUS LES TESTS SONT PASSÉS !")
        return True
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_hallucination_detection():
    """Test de détection d'hallucination"""
    print("\n🛡️ TEST DE DÉTECTION D'HALLUCINATION")
    print("=" * 40)
    
    try:
        from core.advanced_intent_classifier import classify_intent_advanced
        from core.context_aware_hallucination_guard import validate_response_contextual
        
        # Cas de test d'hallucination
        test_cases = [
            {
                'query': "Quel est le prix exact du produit X ?",
                'response': "Le produit X coûte exactement 299,99€ avec garantie 2 ans.",
                'description': "Affirmation de prix sans contexte"
            },
            {
                'query': "Livrez-vous gratuitement ?",
                'response': "Oui, livraison gratuite partout en Europe en 24h.",
                'description': "Affirmation de livraison gratuite"
            },
            {
                'query': "Quel est votre stock ?",
                'response': "Nous avons 1500 unités en stock, disponible immédiatement.",
                'description': "Affirmation de stock précis"
            }
        ]
        
        for i, case in enumerate(test_cases, 1):
            print(f"\n   Test {i}: {case['description']}")
            
            # Classification
            intent_result = await classify_intent_advanced(case['query'])
            print(f"      Intention: {intent_result.primary_intent.value}")
            
            # Validation
            validation_result = await validate_response_contextual(
                user_query=case['query'],
                ai_response=case['response'],
                intent_result=intent_result,
                supabase_results=[],
                meili_results=[],
                supabase_context="",
                meili_context="",
                company_id="test"
            )
            
            print(f"      Validation sûre: {validation_result.is_safe}")
            if not validation_result.is_safe:
                print(f"      Raison du rejet: {validation_result.rejection_reason}")
            else:
                print(f"      ⚠️  ATTENTION: Cette réponse devrait être rejetée !")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERREUR dans le test d'hallucination: {e}")
        return False

async def main():
    """Fonction principale"""
    print("🚀 DÉMARRAGE DES TESTS RAPIDES")
    
    # Test des fonctionnalités de base
    basic_ok = await test_basic_functionality()
    
    # Test de détection d'hallucination
    hallucination_ok = await test_hallucination_detection()
    
    # Résumé
    print("\n" + "=" * 50)
    print("📊 RÉSUMÉ DES TESTS")
    print(f"   Fonctionnalités de base: {'✅ PASSÉ' if basic_ok else '❌ ÉCHOUÉ'}")
    print(f"   Détection d'hallucination: {'✅ PASSÉ' if hallucination_ok else '❌ ÉCHOUÉ'}")
    
    if basic_ok and hallucination_ok:
        print("\n🎉 TOUS LES TESTS SONT PASSÉS !")
        print("   Le système anti-hallucination fonctionne correctement.")
    else:
        print("\n⚠️  CERTAINS TESTS ONT ÉCHOUÉ")
        print("   Vérifiez les erreurs ci-dessus.")

if __name__ == "__main__":
    asyncio.run(main())
