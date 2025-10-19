#!/usr/bin/env python3
"""
🎯 TEST DE VALIDATION AUTO-DÉTECTION
Vérifie que chaque champ est correctement auto-détecté selon la spec
"""
import httpx
import time
from datetime import datetime

BASE_URL = "http://127.0.0.1:8002"
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"

# Images de test
IMAGE_PRODUIT = "https://scontent.xx.fbcdn.net/v/t1.15752-9/553786504_1339650347521010_7584722332323008254_n.jpg?_nc_cat=108&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=iZMvAIEg5agQ7kNvwGVnL0m&_nc_oc=AdmmEA2PGIddOYXbqVDCtoX-X4unHqUgSUBz44wJJhMV4B_RX4_vz3-hfIf0Gg1DYt44ejVZAGHX_fHccpiQMA8g&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent.xx&oh=03_Q7cD3gH1On4PnpZDZQ4CYayHguk94A069j97-Eai6X-5Lw48_Q&oe=6911CDDA"
IMAGE_PAIEMENT = "https://scontent.xx.fbcdn.net/v/t1.15752-9/556908482_1314851517042795_6410429215345539018_n.jpg?_nc_cat=105&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=FGYA3tLaNB8Q7kNvwEFLtNy&_nc_oc=AdnhSYhxtPMknvUViCVLIxdq0psdWOZ9d5lLqoGBIzM4BwPMJfxTWbgDf2rraR9cbl-xHoxCoLL8X0Hf8rR18N30&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent.xx&oh=03_Q7cD3gGKjKR_xt29vtVgdJSUwjCSgV-A-H0IdCphHvF0MvGBow&oe=6911C04A"

def send_message(user_id: str, message: str = "", image_url: str = None):
    """Envoie un message au chatbot BOTLIVE"""
    payload = {
        "company_id": COMPANY_ID,
        "user_id": user_id,
        "message": message,
        "botlive_enabled": True  # ← CRITIQUE: Active le système Botlive
    }
    if image_url:
        payload["images"] = [image_url]  # ← FORMAT CORRECT: liste d'URLs
    
    try:
        resp = httpx.post(f"{BASE_URL}/chat", json=payload, timeout=30)
        return resp.json()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None

def check_state(user_id: str):
    """Récupère l'état de la commande via check_state.py"""
    import subprocess
    result = subprocess.run(
        ["python3", "check_state.py", user_id],
        capture_output=True,
        text=True
    )
    return result.stdout

def test_case(name: str, user_id: str, steps: list, expected: dict):
    """
    Exécute un cas de test
    
    Args:
        name: Nom du test
        user_id: ID utilisateur unique
        steps: Liste de tuples (message, image_url)
        expected: État attendu {'produit': bool, 'paiement': bool, 'zone': bool, 'numero': bool, 'completion': int}
    """
    print(f"\n{'='*80}")
    print(f"🧪 TEST: {name}")
    print(f"{'='*80}")
    print(f"👤 user_id: {user_id}")
    
    # Exécuter les étapes
    for i, (message, image_url) in enumerate(steps, 1):
        print(f"\n📍 Étape {i}/{len(steps)}")
        if image_url:
            print(f"   📸 Image: {image_url[:50]}...")
        if message:
            print(f"   💬 Message: {message}")
        
        send_message(user_id, message, image_url)
        time.sleep(2)  # Attendre traitement
    
    # Vérifier l'état
    print(f"\n🔍 Vérification état...")
    state_output = check_state(user_id)
    print(state_output)
    
    # Analyser les résultats
    has_produit = "✅ PRODUIT:" in state_output and "❌ VIDE" not in state_output.split("✅ PRODUIT:")[1].split("\n")[0]
    has_paiement = "✅ PAIEMENT:" in state_output and "❌ VIDE" not in state_output.split("✅ PAIEMENT:")[1].split("\n")[0]
    has_zone = "✅ ZONE:" in state_output and "❌ VIDE" not in state_output.split("✅ ZONE:")[1].split("\n")[0]
    has_numero = "✅ NUMÉRO:" in state_output and "❌ VIDE" not in state_output.split("✅ NUMÉRO:")[1].split("\n")[0]
    
    # Extraire complétion
    completion_line = [line for line in state_output.split("\n") if "Complétion:" in line]
    completion = int(completion_line[0].split(":")[1].strip().replace("%", "")) if completion_line else 0
    
    # Comparer avec attendu
    results = {
        'produit': has_produit == expected['produit'],
        'paiement': has_paiement == expected['paiement'],
        'zone': has_zone == expected['zone'],
        'numero': has_numero == expected['numero'],
        'completion': completion == expected['completion']
    }
    
    # Afficher résultats
    print(f"\n📊 RÉSULTATS:")
    print(f"   PRODUIT:    {'✅' if results['produit'] else '❌'} (attendu: {expected['produit']}, obtenu: {has_produit})")
    print(f"   PAIEMENT:   {'✅' if results['paiement'] else '❌'} (attendu: {expected['paiement']}, obtenu: {has_paiement})")
    print(f"   ZONE:       {'✅' if results['zone'] else '❌'} (attendu: {expected['zone']}, obtenu: {has_zone})")
    print(f"   NUMÉRO:     {'✅' if results['numero'] else '❌'} (attendu: {expected['numero']}, obtenu: {has_numero})")
    print(f"   COMPLÉTION: {'✅' if results['completion'] else '❌'} (attendu: {expected['completion']}%, obtenu: {completion}%)")
    
    success = all(results.values())
    print(f"\n{'✅ TEST RÉUSSI' if success else '❌ TEST ÉCHOUÉ'}")
    
    return success

def main():
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                   🎯 VALIDATION AUTO-DÉTECTION                             ║
║                                                                            ║
║  Tests basés sur AUTO_DETECT_SPEC.md                                      ║
╚════════════════════════════════════════════════════════════════════════════╝
""")
    
    results = {}
    
    # TEST 1: Produit seul (25%)
    results['test1'] = test_case(
        name="Produit seul (25%)",
        user_id=f"test_produit_{datetime.now().strftime('%H%M%S')}",
        steps=[
            ("Bonsoir", None),
            ("", IMAGE_PRODUIT)
        ],
        expected={
            'produit': True,
            'paiement': False,
            'zone': False,
            'numero': False,
            'completion': 25
        }
    )
    
    time.sleep(3)
    
    # TEST 2: Produit + Paiement (50%)
    results['test2'] = test_case(
        name="Produit + Paiement (50%)",
        user_id=f"test_paiement_{datetime.now().strftime('%H%M%S')}",
        steps=[
            ("Bonsoir", None),
            ("", IMAGE_PRODUIT),
            ("", IMAGE_PAIEMENT)
        ],
        expected={
            'produit': True,
            'paiement': True,
            'zone': False,
            'numero': False,
            'completion': 50
        }
    )
    
    time.sleep(3)
    
    # TEST 3: Produit + Paiement + Zone (75%)
    results['test3'] = test_case(
        name="Produit + Paiement + Zone (75%)",
        user_id=f"test_zone_{datetime.now().strftime('%H%M%S')}",
        steps=[
            ("Bonsoir", None),
            ("", IMAGE_PRODUIT),
            ("", IMAGE_PAIEMENT),
            ("Yopougon", None)
        ],
        expected={
            'produit': True,
            'paiement': True,
            'zone': True,
            'numero': False,
            'completion': 75
        }
    )
    
    time.sleep(3)
    
    # TEST 4: Commande complète (100%)
    results['test4'] = test_case(
        name="Commande complète (100%)",
        user_id=f"test_complet_{datetime.now().strftime('%H%M%S')}",
        steps=[
            ("Bonsoir", None),
            ("", IMAGE_PRODUIT),
            ("", IMAGE_PAIEMENT),
            ("Yopougon 0709876543", None)
        ],
        expected={
            'produit': True,
            'paiement': True,
            'zone': True,
            'numero': True,
            'completion': 100
        }
    )
    
    # Résumé final
    print(f"\n\n{'='*80}")
    print(f"📊 RÉSUMÉ FINAL")
    print(f"{'='*80}")
    
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    
    for test_name, passed in results.items():
        status = "✅ RÉUSSI" if passed else "❌ ÉCHOUÉ"
        print(f"{test_name}: {status}")
    
    print(f"\n{'='*80}")
    print(f"TOTAL: {passed_tests}/{total_tests} tests réussis ({passed_tests/total_tests*100:.0f}%)")
    print(f"{'='*80}")
    
    if passed_tests == total_tests:
        print("\n🎉 TOUS LES TESTS RÉUSSIS ! AUTO-DÉTECTION VALIDÉE ✅")
    else:
        print(f"\n⚠️ {total_tests - passed_tests} test(s) échoué(s). Vérifier les logs.")

if __name__ == "__main__":
    main()
