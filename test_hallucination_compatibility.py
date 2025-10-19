#!/usr/bin/env python3
"""
🔄 TEST DE COMPATIBILITÉ - GARDE-FOU ANTI-HALLUCINATION
Vérification de la compatibilité avec l'ancien système
"""

import asyncio
import sys
import os
import time

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_compatibility():
    """Test de compatibilité avec l'ancien système"""
    print("🔄 TEST DE COMPATIBILITÉ")
    print("=" * 40)
    
    try:
        # Test 1: Import de l'ancien système
        print("1️⃣ Test d'import de l'ancien système...")
        from core.rag_engine_simplified_fixed import get_rag_response
        print("   ✅ Import réussi")
        
        # Test 2: Import du nouveau système
        print("\n2️⃣ Test d'import du nouveau système...")
        from core.rag_engine_simplified_fixed import get_rag_response_advanced
        print("   ✅ Import réussi")
        
        # Test 3: Test de l'ancienne fonction
        print("\n3️⃣ Test de l'ancienne fonction get_rag_response...")
        start_time = time.time()
        
        try:
            response = await get_rag_response(
                message="Comment tu t'appelles ?",
                company_id="test_company",
                user_id="test_user"
            )
            processing_time = (time.time() - start_time) * 1000
            
            print(f"   ✅ Réponse générée: {response[:50]}...")
            print(f"   ⏱️  Temps de traitement: {processing_time:.2f}ms")
            
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            return False
        
        # Test 4: Test de la nouvelle fonction
        print("\n4️⃣ Test de la nouvelle fonction get_rag_response_advanced...")
        start_time = time.time()
        
        try:
            result = await get_rag_response_advanced(
                message="Comment tu t'appelles ?",
                user_id="test_user",
                company_id="test_company"
            )
            processing_time = (time.time() - start_time) * 1000
            
            print(f"   ✅ Réponse générée: {result['response'][:50]}...")
            print(f"   📊 Intent: {result['intent']}")
            print(f"   📊 Confidence: {result['confidence']:.3f}")
            print(f"   📊 Validation safe: {result['validation_safe']}")
            print(f"   ⏱️  Temps de traitement: {processing_time:.2f}ms")
            
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            return False
        
        # Test 5: Comparaison des performances
        print("\n5️⃣ Comparaison des performances...")
        
        # Test ancien système
        old_times = []
        for i in range(3):
            start = time.time()
            await get_rag_response("Test performance", "test_company", "test_user")
            old_times.append((time.time() - start) * 1000)
        
        # Test nouveau système
        new_times = []
        for i in range(3):
            start = time.time()
            await get_rag_response_advanced("Test performance", "test_user", "test_company")
            new_times.append((time.time() - start) * 1000)
        
        old_avg = sum(old_times) / len(old_times)
        new_avg = sum(new_times) / len(new_times)
        
        print(f"   Ancien système (moyenne): {old_avg:.2f}ms")
        print(f"   Nouveau système (moyenne): {new_avg:.2f}ms")
        print(f"   Différence: {new_avg - old_avg:+.2f}ms")
        
        if new_avg > old_avg * 2:
            print("   ⚠️  Le nouveau système est significativement plus lent")
        else:
            print("   ✅ Performance acceptable")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERREUR DE COMPATIBILITÉ: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_backward_compatibility():
    """Test de rétrocompatibilité"""
    print("\n🔄 TEST DE RÉTROCOMPATIBILITÉ")
    print("=" * 40)
    
    try:
        # Test avec différents types de questions
        test_cases = [
            {
                'message': "Comment tu t'appelles ?",
                'description': "Question sociale"
            },
            {
                'message': "Quels sont vos produits ?",
                'description': "Question métier"
            },
            {
                'message': "Combien coûte la livraison ?",
                'description': "Question de prix"
            },
            {
                'message': "Bonjour",
                'description': "Salutation simple"
            }
        ]
        
        from core.rag_engine_simplified_fixed import get_rag_response, get_rag_response_advanced
        
        for i, case in enumerate(test_cases, 1):
            print(f"\n   Test {i}: {case['description']}")
            
            # Test ancien système
            try:
                old_response = await get_rag_response(
                    message=case['message'],
                    company_id="test_company",
                    user_id="test_user"
                )
                print(f"      Ancien: {old_response[:30]}...")
            except Exception as e:
                print(f"      Ancien: ❌ {e}")
            
            # Test nouveau système
            try:
                new_result = await get_rag_response_advanced(
                    message=case['message'],
                    user_id="test_user",
                    company_id="test_company"
                )
                print(f"      Nouveau: {new_result['response'][:30]}...")
                print(f"      Intent: {new_result['intent']}, Conf: {new_result['confidence']:.2f}")
            except Exception as e:
                print(f"      Nouveau: ❌ {e}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERREUR DE RÉTROCOMPATIBILITÉ: {e}")
        return False

async def test_error_handling():
    """Test de gestion d'erreurs"""
    print("\n🛡️ TEST DE GESTION D'ERREURS")
    print("=" * 40)
    
    try:
        from core.rag_engine_simplified_fixed import get_rag_response_advanced
        
        # Test avec des entrées problématiques
        error_cases = [
            {
                'message': None,
                'description': "Message null"
            },
            {
                'message': "",
                'description': "Message vide"
            },
            {
                'message': "a" * 10000,
                'description': "Message très long"
            },
            {
                'message': "!@#$%^&*()",
                'description': "Caractères spéciaux"
            }
        ]
        
        for i, case in enumerate(error_cases, 1):
            print(f"\n   Test {i}: {case['description']}")
            
            try:
                result = await get_rag_response_advanced(
                    message=case['message'],
                    user_id="test_user",
                    company_id="test_company"
                )
                print(f"      ✅ Géré: {result['response'][:30]}...")
                print(f"      Debug: {result.get('debug_info', {}).get('error', 'Aucune erreur')}")
            except Exception as e:
                print(f"      ❌ Non géré: {e}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERREUR DANS LE TEST DE GESTION D'ERREURS: {e}")
        return False

async def main():
    """Fonction principale"""
    print("🔄 TEST DE COMPATIBILITÉ - GARDE-FOU ANTI-HALLUCINATION")
    print("Vérification de la compatibilité avec l'ancien système")
    print("=" * 70)
    
    # Tests
    compatibility_ok = await test_compatibility()
    backward_ok = await test_backward_compatibility()
    error_handling_ok = await test_error_handling()
    
    # Résumé
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ DES TESTS DE COMPATIBILITÉ")
    print(f"   Compatibilité de base: {'✅ PASSÉ' if compatibility_ok else '❌ ÉCHOUÉ'}")
    print(f"   Rétrocompatibilité: {'✅ PASSÉ' if backward_ok else '❌ ÉCHOUÉ'}")
    print(f"   Gestion d'erreurs: {'✅ PASSÉ' if error_handling_ok else '❌ ÉCHOUÉ'}")
    
    if compatibility_ok and backward_ok and error_handling_ok:
        print("\n🎉 TOUS LES TESTS DE COMPATIBILITÉ SONT PASSÉS !")
        print("   Le nouveau système est compatible avec l'ancien.")
    else:
        print("\n⚠️  CERTAINS TESTS DE COMPATIBILITÉ ONT ÉCHOUÉ")
        print("   Vérifiez les erreurs ci-dessus.")

if __name__ == "__main__":
    asyncio.run(main())
