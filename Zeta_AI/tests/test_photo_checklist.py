#!/usr/bin/env python3
"""
🎯 TEST CIBLÉ - DÉTECTION PHOTO DANS CHECKLIST
==============================================

Test ultra-spécifique pour vérifier que la photo stockée sous 
'photo_produit_description' est correctement détectée dans la checklist.

OBJECTIF: Vérifier que ❌ Photo manquante devient ✅ Photo reçue
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.persistent_collector import get_collector
import logging

# Configuration logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_photo_checklist_detection():
    """Test direct de la détection photo dans la checklist"""
    
    print("🎯 TEST CIBLÉ - DÉTECTION PHOTO CHECKLIST")
    print("=" * 50)
    
    collector = get_collector()
    
    # SIMULATION 1: Notepad SANS photo
    print("\n📋 TEST 1: Notepad vide (sans photo)")
    notepad_vide = {}
    
    result1 = collector.collect_and_persist(
        notepad=notepad_vide,
        vision_result=None,
        ocr_result=None,
        message="test"
    )
    
    print(f"   Checklist générée:")
    print(f"   {result1['checklist']}")
    
    # Vérifier que photo est manquante
    if "❌ Photo manquante" in result1['checklist']:
        print("   ✅ CORRECT: Photo détectée comme manquante")
    else:
        print("   ❌ ERREUR: Photo devrait être manquante")
    
    # SIMULATION 2: Notepad avec photo_produit_description (cas réel)
    print("\n📋 TEST 2: Notepad avec photo_produit_description")
    notepad_avec_photo = {
        "photo_produit_description": "a bag of sanitary wipes on a white background",
        "paiement": {"montant": 2020, "validé": True},
        "delivery_zone": "Cocody",
        "delivery_cost": 1500,
        "phone_number": "0708651945"
    }
    
    result2 = collector.collect_and_persist(
        notepad=notepad_avec_photo,
        vision_result=None,
        ocr_result=None,
        message="test"
    )
    
    print(f"   Checklist générée:")
    print(f"   {result2['checklist']}")
    
    # Vérifier que photo est détectée
    if "✅ Photo reçue" in result2['checklist']:
        print("   ✅ CORRECT: Photo détectée comme présente")
        photo_ok = True
    else:
        print("   ❌ ERREUR: Photo devrait être détectée")
        photo_ok = False
    
    # SIMULATION 3: Notepad avec photo_produit (ancien format)
    print("\n📋 TEST 3: Notepad avec photo_produit (ancien format)")
    notepad_ancien = {
        "photo_produit": "a bag of diapers",
        "paiement": {"montant": 2020, "validé": True},
        "delivery_zone": "Cocody", 
        "delivery_cost": 1500,
        "phone_number": "0708651945"
    }
    
    result3 = collector.collect_and_persist(
        notepad=notepad_ancien,
        vision_result=None,
        ocr_result=None,
        message="test"
    )
    
    print(f"   Checklist générée:")
    print(f"   {result3['checklist']}")
    
    # Vérifier que photo est détectée
    if "✅ Photo reçue" in result3['checklist']:
        print("   ✅ CORRECT: Photo (ancien format) détectée")
        ancien_ok = True
    else:
        print("   ❌ ERREUR: Photo (ancien format) devrait être détectée")
        ancien_ok = False
    
    # VÉRIFICATION CRITIQUE: 4/4 collectés
    print("\n📋 TEST CRITIQUE: Vérification 4/4 collectés")
    
    # Simuler l'état exact du test qui échoue
    notepad_complet = {
        "photo_produit_description": "a bag of sanitary wipes on a white background",
        "paiement": {"montant": 2020, "validé": True},
        "delivery_zone": "Cocody",
        "delivery_cost": 1500,
        "phone_number": "0708651945"
    }
    
    result_final = collector.collect_and_persist(
        notepad=notepad_complet,
        vision_result=None,
        ocr_result=None,
        message="test"
    )
    
    print(f"   État généré:")
    state = result_final['state']
    print(f"     Photo collected: {state['photo']['collected']}")
    print(f"     Paiement collected: {state['paiement']['collected']}")
    print(f"     Zone collected: {state['zone']['collected']}")
    print(f"     Tel collected: {state['tel']['collected']} (valid: {state['tel']['valid']})")
    
    print(f"\n   Checklist finale:")
    print(f"   {result_final['checklist']}")
    
    # Compter les ✅
    checklist_lines = result_final['checklist'].split('\n')
    success_count = sum(1 for line in checklist_lines if line.startswith('✅'))
    
    print(f"\n   Éléments collectés: {success_count}/4")
    
    if success_count == 4:
        print("   🎉 PARFAIT! 4/4 collectés - Le PATCH #2 devrait fonctionner!")
        final_ok = True
    else:
        print(f"   ❌ PROBLÈME: Seulement {success_count}/4 collectés")
        final_ok = False
    
    # VERDICT FINAL
    print("\n" + "=" * 50)
    print("🏁 VERDICT FINAL")
    
    if photo_ok and ancien_ok and final_ok:
        print("🎉 SUCCÈS TOTAL!")
        print("✅ La correction fonctionne parfaitement")
        print("✅ Le test complet devrait maintenant réussir")
        return True
    else:
        print("❌ ÉCHEC PARTIEL")
        if not photo_ok:
            print("❌ Problème avec photo_produit_description")
        if not ancien_ok:
            print("❌ Problème avec photo_produit")
        if not final_ok:
            print("❌ Problème avec la détection 4/4")
        return False

if __name__ == "__main__":
    try:
        print("🚀 DÉMARRAGE TEST CIBLÉ PHOTO")
        success = test_photo_checklist_detection()
        
        if success:
            print("\n🎯 CONCLUSION: Relancez le test complet!")
            exit(0)
        else:
            print("\n🔧 CONCLUSION: Corrections supplémentaires nécessaires")
            exit(1)
            
    except Exception as e:
        print(f"💥 ERREUR: {e}")
        import traceback
        traceback.print_exc()
        exit(2)
