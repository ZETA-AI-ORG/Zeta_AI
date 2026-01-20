#!/usr/bin/env python3
"""
🧪 TEST DU GARDE-FOU ANTI-HALLUCINATION ADAPTATIF
Test du système en 2 modes : conversations simples + informations factuelles
"""

import sys
import os

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_adaptive_hallucination_guard():
    """Test du garde-fou anti-hallucination adaptatif"""
    print("🧪 TEST DU GARDE-FOU ANTI-HALLUCINATION ADAPTATIF")
    print("=" * 70)
    
    try:
        from core.adaptive_hallucination_guard import check_hallucination_adaptive
        
        # Cas de test
        test_cases = [
            # === MODE 1 : CONVERSATIONS SIMPLES ===
            {
                "name": "Conversation simple - Bonjour",
                "query": "Bonjour",
                "response": "Bonjour ! Comment puis-je vous aider ?",
                "sources": None,
                "expected_mode": "simple_conversation",
                "expected_safe": True
            },
            {
                "name": "Conversation simple - Nom",
                "query": "Comment tu t'appelles ?",
                "response": "Je m'appelle Gamma, votre assistant client",
                "sources": None,
                "expected_mode": "simple_conversation",
                "expected_safe": True
            },
            {
                "name": "Conversation simple avec info spécifique inappropriée",
                "query": "Bonjour",
                "response": "Bonjour ! Le prix de notre produit est de 25€",
                "sources": None,
                "expected_mode": "simple_conversation",
                "expected_safe": False
            },
            
            # === MODE 2 : INFORMATIONS FACTUELLES ===
            {
                "name": "Information factuelle - Adresse avec sources",
                "query": "Où êtes-vous situé ?",
                "response": "Nous sommes situés au 123 rue de la Paix, 75001 Paris",
                "sources": ["Adresse: 123 rue de la Paix, 75001 Paris", "Contact: 01 23 45 67 89"],
                "expected_mode": "factual_information",
                "expected_safe": True
            },
            {
                "name": "Information factuelle - Prix avec sources",
                "query": "Quel est le prix ?",
                "response": "Le prix est de 25€",
                "sources": ["Prix: 25€", "Tarifs disponibles"],
                "expected_mode": "factual_information",
                "expected_safe": True
            },
            {
                "name": "Information factuelle - Prix incohérent",
                "query": "Quel est le prix ?",
                "response": "Le prix est de 50€",
                "sources": ["Prix: 25€", "Tarifs disponibles"],
                "expected_mode": "factual_information",
                "expected_safe": False
            },
            {
                "name": "Information factuelle - Sans sources",
                "query": "Quel est votre téléphone ?",
                "response": "Notre téléphone est le 01 23 45 67 89",
                "sources": None,
                "expected_mode": "factual_information",
                "expected_safe": False
            },
            {
                "name": "Information factuelle - Email avec sources",
                "query": "Quel est votre email ?",
                "response": "Notre email est contact@rue-du-gros.com",
                "sources": ["Email: contact@rue-du-gros.com", "Contact commercial"],
                "expected_mode": "factual_information",
                "expected_safe": True
            },
            
            # === CAS LIMITES ===
            {
                "name": "Question générale sans info spécifique",
                "query": "Qu'est-ce que c'est ?",
                "response": "C'est une question intéressante",
                "sources": None,
                "expected_mode": "simple_conversation",
                "expected_safe": True
            },
            {
                "name": "Question générale avec info spécifique",
                "query": "Qu'est-ce que c'est ?",
                "response": "C'est notre produit X qui coûte 100€",
                "sources": None,
                "expected_mode": "factual_information",
                "expected_safe": False
            }
        ]
        
        print("📝 RÉSULTATS DES TESTS:")
        print("-" * 70)
        
        passed = 0
        total = len(test_cases)
        
        for i, case in enumerate(test_cases, 1):
            print(f"\n{i}. {case['name']}")
            print(f"   Question: '{case['query']}'")
            print(f"   Réponse: '{case['response']}'")
            if case['sources']:
                print(f"   Sources: {case['sources']}")
            else:
                print(f"   Sources: Aucune")
            
            result = check_hallucination_adaptive(
                case['query'], 
                case['response'], 
                case['sources']
            )
            
            print(f"   Mode détecté: {result['validation_mode']}")
            print(f"   Sûr: {result['is_safe']} (conf: {result['confidence']:.2f})")
            
            if result['specific_information_detected']:
                print(f"   Infos détectées: {result['specific_information_detected']}")
            
            if result['source_verification']:
                print(f"   Vérification sources: {result['source_verification']}")
            
            if result['rejection_reason']:
                print(f"   Raison rejet: {result['rejection_reason']}")
            
            if result['suggested_action']:
                print(f"   Action suggérée: {result['suggested_action']}")
            
            # Vérifier si le résultat est attendu
            mode_correct = result['validation_mode'] == case['expected_mode']
            safety_correct = result['is_safe'] == case['expected_safe']
            
            if mode_correct and safety_correct:
                print(f"   ✅ CORRECT")
                passed += 1
            else:
                print(f"   ❌ INCORRECT")
                if not mode_correct:
                    print(f"      Mode attendu: {case['expected_mode']}, obtenu: {result['validation_mode']}")
                if not safety_correct:
                    print(f"      Sécurité attendue: {case['expected_safe']}, obtenue: {result['is_safe']}")
        
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

def test_mode_detection():
    """Test spécifique de la détection de mode"""
    print("\n🔍 TEST DE DÉTECTION DE MODE")
    print("-" * 40)
    
    try:
        from core.adaptive_hallucination_guard import AdaptiveHallucinationGuard
        
        guard = AdaptiveHallucinationGuard()
        
        test_cases = [
            ("Bonjour", "Bonjour !", "simple_conversation"),
            ("Comment tu t'appelles ?", "Je m'appelle Gamma", "simple_conversation"),
            ("Où êtes-vous ?", "Nous sommes à Paris", "factual_information"),
            ("Quel est le prix ?", "Le prix est de 25€", "factual_information"),
            ("Bonjour", "Bonjour ! Le prix est de 25€", "factual_information"),  # Info spécifique détectée
        ]
        
        for query, response, expected_mode in test_cases:
            mode, confidence = guard.detect_validation_mode(query, response)
            print(f"Q: '{query}' | R: '{response}'")
            print(f"Mode détecté: {mode.value} (conf: {confidence:.2f})")
            print(f"Attendu: {expected_mode}")
            print(f"✅ {'CORRECT' if mode.value == expected_mode else 'INCORRECT'}")
            print("-" * 30)
        
    except Exception as e:
        print(f"❌ Erreur test détection: {e}")

if __name__ == "__main__":
    success1 = test_adaptive_hallucination_guard()
    success2 = test_mode_detection()
    
    if success1 and success2:
        print("\n✅ SYSTÈME ANTI-HALLUCINATION ADAPTATIF VALIDÉ !")
    else:
        print("\n❌ SYSTÈME ANTI-HALLUCINATION ADAPTATIF À CORRIGER !")
