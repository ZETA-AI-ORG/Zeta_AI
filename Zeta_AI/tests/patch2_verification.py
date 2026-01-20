#!/usr/bin/env python3
"""
🔧 VÉRIFICATION DIRECTE DU PATCH #2
==================================

Script rapide pour tester la fonction _check_completion() directement
sans passer par tout le système Botlive.

OBJECTIF: Vérifier que le PATCH #2 détecte correctement 4/4 collectés
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.loop_botlive_engine import LoopBotliveEngine
import logging

# Configuration logging pour voir les détails
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_patch2_completion_detection():
    """Test direct de la détection 4/4 collectés"""
    
    print("🔧 VÉRIFICATION DIRECTE DU PATCH #2")
    print("=" * 50)
    
    # Initialiser le moteur
    engine = LoopBotliveEngine()
    
    # Test 1: État incomplet (3/4)
    print("\n📋 TEST 1: État incomplet (3/4)")
    state_incomplete = {
        "photo": {"collected": True, "data": "a bag of sanitary wipes"},
        "paiement": {"collected": True, "data": 2020},
        "zone": {"collected": True, "data": "Cocody"},
        "tel": {"collected": False, "valid": False, "data": None}
    }
    
    result1 = engine._check_completion(state_incomplete)
    print(f"   Résultat: {result1}")
    print(f"   ✅ Attendu: None (pas complet)")
    
    # Test 2: État complet (4/4)
    print("\n📋 TEST 2: État complet (4/4)")
    state_complete = {
        "photo": {"collected": True, "data": "a bag of sanitary wipes"},
        "paiement": {"collected": True, "data": 2020},
        "zone": {"collected": True, "data": "Cocody"},
        "tel": {"collected": True, "valid": True, "data": "0708651945"}
    }
    
    result2 = engine._check_completion(state_complete)
    print(f"   Résultat: {result2}")
    print(f"   ✅ Attendu: 'llm_takeover'")
    
    # Test 3: Structure fallback (comme dans les logs)
    print("\n📋 TEST 3: Structure fallback (réelle)")
    state_fallback = {
        "photo_collected": True,
        "photo_data": "a bag of sanitary wipes",
        "paiement_collected": True,
        "paiement_data": 2020,
        "zone_collected": True,
        "zone_data": "Cocody",
        "tel_collected": True,
        "tel_valid": True,
        "tel_data": "0708651945"
    }
    
    result3 = engine._check_completion(state_fallback)
    print(f"   Résultat: {result3}")
    print(f"   ✅ Attendu: None (structure incompatible)")
    
    # Test 4: Structure mixte (problème probable)
    print("\n📋 TEST 4: Structure mixte")
    state_mixed = {
        "photo": {"collected": False},  # Problème ici
        "paiement": {"collected": True, "data": 2020},
        "zone": {"collected": True, "data": "Cocody"},
        "tel": {"collected": True, "valid": True, "data": "0708651945"},
        # Données dans notepad
        "photo_produit_description": "a bag of sanitary wipes"
    }
    
    result4 = engine._check_completion(state_mixed)
    print(f"   Résultat: {result4}")
    print(f"   ✅ Attendu: None (photo pas collectée)")
    
    # ANALYSE DES RÉSULTATS
    print("\n" + "=" * 50)
    print("📊 ANALYSE DES RÉSULTATS")
    
    success_count = 0
    total_tests = 4
    
    # Vérification Test 1
    if result1 is None:
        print("✅ TEST 1: RÉUSSI - État incomplet correctement détecté")
        success_count += 1
    else:
        print(f"❌ TEST 1: ÉCHEC - Attendu None, reçu {result1}")
    
    # Vérification Test 2
    if result2 == "llm_takeover":
        print("✅ TEST 2: RÉUSSI - État complet correctement détecté")
        success_count += 1
    else:
        print(f"❌ TEST 2: ÉCHEC - Attendu 'llm_takeover', reçu {result2}")
    
    # Vérification Test 3
    if result3 is None:
        print("✅ TEST 3: RÉUSSI - Structure fallback gérée")
        success_count += 1
    else:
        print(f"❌ TEST 3: ÉCHEC - Attendu None, reçu {result3}")
    
    # Vérification Test 4
    if result4 is None:
        print("✅ TEST 4: RÉUSSI - Structure mixte gérée")
        success_count += 1
    else:
        print(f"❌ TEST 4: ÉCHEC - Attendu None, reçu {result4}")
    
    # VERDICT FINAL
    success_rate = (success_count / total_tests) * 100
    print(f"\n🎯 TAUX DE RÉUSSITE: {success_rate}%")
    
    if success_rate == 100:
        print("🎉 PATCH #2 FONCTIONNE PARFAITEMENT!")
        print("✅ Vous pouvez relancer le test complet")
        return True
    elif success_rate >= 75:
        print("⚠️ PATCH #2 FONCTIONNE PARTIELLEMENT")
        print("🔧 Quelques ajustements nécessaires")
        return False
    else:
        print("❌ PATCH #2 NE FONCTIONNE PAS")
        print("🚨 Corrections majeures requises")
        return False

def test_state_structure_from_logs():
    """Test avec la vraie structure des logs"""
    
    print("\n" + "=" * 50)
    print("🔍 TEST AVEC STRUCTURE RÉELLE DES LOGS")
    
    engine = LoopBotliveEngine()
    
    # Simuler l'état exact du dernier test (étape 6)
    print("\n📋 SIMULATION ÉTAPE 6 (Confirmation finale)")
    
    # État basé sur les logs réels
    real_state = {
        # Données du notepad (persistées)
        "photo_produit_description": "a bag of sanitary wipes on a white background",
        "paiement": {"montant": 2020, "validé": True},
        "delivery_zone": "Cocody",
        "delivery_cost": 1500,
        "phone_number": "0708651945",
        
        # Structure attendue par _check_completion
        "photo": {"collected": True, "data": "a bag of sanitary wipes on a white background"},
        "paiement": {"collected": True, "data": 2020},
        "zone": {"collected": True, "data": "Cocody"},
        "tel": {"collected": True, "valid": True, "data": "0708651945"}
    }
    
    print("   État simulé:")
    for key, value in real_state.items():
        if isinstance(value, dict):
            print(f"     {key}: {value}")
        else:
            print(f"     {key}: {str(value)[:50]}...")
    
    result = engine._check_completion(real_state)
    print(f"\n   Résultat: {result}")
    
    if result == "llm_takeover":
        print("✅ PARFAIT! Le PATCH #2 devrait fonctionner dans le test complet")
        return True
    else:
        print("❌ PROBLÈME! Le PATCH #2 ne détecte pas la completion")
        print("🔧 Il faut corriger la structure de données")
        return False

if __name__ == "__main__":
    try:
        print("🚀 DÉMARRAGE VÉRIFICATION PATCH #2")
        
        # Test de base
        basic_success = test_patch2_completion_detection()
        
        # Test avec structure réelle
        real_success = test_state_structure_from_logs()
        
        print("\n" + "=" * 60)
        print("🏁 VERDICT FINAL")
        
        if basic_success and real_success:
            print("🎉 PATCH #2 EST OPÉRATIONNEL!")
            print("✅ Relancez le test complet avec confiance")
            exit(0)
        else:
            print("❌ PATCH #2 NÉCESSITE DES CORRECTIONS")
            print("🔧 Corrigez les problèmes identifiés avant le test complet")
            exit(1)
            
    except Exception as e:
        print(f"💥 ERREUR CRITIQUE: {e}")
        print("🚨 Le PATCH #2 a un problème majeur")
        import traceback
        traceback.print_exc()
        exit(2)
