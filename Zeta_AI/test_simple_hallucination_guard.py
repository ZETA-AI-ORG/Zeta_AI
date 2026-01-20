#!/usr/bin/env python3
"""
🧪 TEST DU GARDE-FOU ANTI-HALLUCINATION SIMPLE
Test du nouveau système simple et adaptatif
"""

import sys
import os

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_simple_hallucination_guard():
    """Test du garde-fou anti-hallucination simple"""
    print("🧪 TEST DU GARDE-FOU ANTI-HALLUCINATION SIMPLE")
    print("=" * 60)
    
    try:
        from core.simple_adaptive_hallucination_guard import check_hallucination_simple
        
        # Cas de test
        test_cases = [
            # Questions sur les produits
            {
                "query": "Que vendez-vous?",
                "response": "Nous vendons des produits de qualité",
                "documents_found": True,
                "expected_safe": True
            },
            {
                "query": "Que vendez-vous?",
                "response": "Je n'ai pas d'informations sur nos produits",
                "documents_found": False,
                "expected_safe": True
            },
            {
                "query": "Que vendez-vous?",
                "response": "Nous vendons des voitures de luxe",  # Inventé
                "documents_found": False,
                "expected_safe": False
            },
            
            # Questions sociales
            {
                "query": "Bonjour",
                "response": "Bonjour ! Comment puis-je vous aider ?",
                "documents_found": False,
                "expected_safe": True
            },
            {
                "query": "Comment allez-vous?",
                "response": "Très bien, merci !",
                "documents_found": False,
                "expected_safe": True
            },
            
            # Questions générales
            {
                "query": "Qu'est-ce que c'est?",
                "response": "C'est une question intéressante",
                "documents_found": False,
                "expected_safe": True
            },
            
            # Questions de prix
            {
                "query": "Combien coûte la livraison?",
                "response": "La livraison coûte 5€",
                "documents_found": True,
                "expected_safe": True
            },
            {
                "query": "Combien coûte la livraison?",
                "response": "Je n'ai pas cette information",
                "documents_found": False,
                "expected_safe": True
            }
        ]
        
        print("📝 RÉSULTATS DES TESTS:")
        print("-" * 60)
        
        passed = 0
        total = len(test_cases)
        
        for i, case in enumerate(test_cases, 1):
            print(f"\n{i}. Question: '{case['query']}'")
            print(f"   Réponse: '{case['response']}'")
            print(f"   Documents trouvés: {case['documents_found']}")
            
            result = check_hallucination_simple(
                case['query'], 
                case['response'], 
                case['documents_found']
            )
            
            print(f"   Type détecté: {result['question_type']}")
            print(f"   Sûr: {result['is_safe']} (conf: {result['confidence']:.2f})")
            
            if result['rejection_reason']:
                print(f"   Raison rejet: {result['rejection_reason']}")
            
            if result['suggested_action']:
                print(f"   Action suggérée: {result['suggested_action']}")
            
            # Vérifier si le résultat est attendu
            if result['is_safe'] == case['expected_safe']:
                print(f"   ✅ CORRECT")
                passed += 1
            else:
                print(f"   ❌ INCORRECT (attendu: {case['expected_safe']})")
        
        print(f"\n📊 RÉSULTATS FINAUX:")
        print(f"   Tests passés: {passed}/{total}")
        print(f"   Taux de réussite: {passed/total*100:.1f}%")
        
        if passed == total:
            print("🎉 TOUS LES TESTS SONT PASSÉS !")
            return True
        else:
            print("⚠️  CERTAINS TESTS ONT ÉCHOUÉ")
            return False
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_simple_hallucination_guard()
    if success:
        print("\n✅ SYSTÈME ANTI-HALLUCINATION SIMPLE VALIDÉ !")
    else:
        print("\n❌ SYSTÈME ANTI-HALLUCINATION SIMPLE À CORRIGER !")
