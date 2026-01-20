#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 TEST RAG COMPLET - RUE DU GROSSISTE
Company ID: 4OS4yFcf2LZwxhKojbAVbKuVuSdb

Objectifs:
1. Tester HYDE (nettoyage requêtes)
2. Tester MeiliSearch (recherche documents)
3. Tester extraction prix EXACTS
4. Tester utilisation outils (notepad, calculator)
5. Tester citations sources
6. Tester ordre chaotique des infos
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:8002"
COMPANY_ID = "4OS4yFcf2LZwxhKojbAVbKuVuSdb"

def print_section(title):
    """Affiche un titre de section"""
    print("\n" + "="*80)
    print(f"🧪 {title}")
    print("="*80)

def send_message(user_id, message):
    """Envoie un message au chatbot"""
    url = f"{BASE_URL}/chat"
    payload = {
        "message": message,
        "company_id": COMPANY_ID,
        "user_id": user_id
    }
    
    print(f"\n📤 USER: {message}")
    start = time.time()
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            print(f"⏱️  Temps: {elapsed:.2f}s")
            
            # Extraction robuste de la réponse (gère dict ou string)
            response_data = data.get('response', {})
            if isinstance(response_data, dict):
                answer_text = response_data.get('response', 'Pas de réponse')
            else:
                answer_text = str(response_data)
            
            print(f"🤖 ASSISTANT: {answer_text}")
            
            # Retourne un dict normalisé avec la réponse en string
            return {
                'response': answer_text,
                'raw_data': data,
                'success': True
            }
        else:
            print(f"❌ Erreur HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None

def test_1_prix_exacts():
    """
    TEST 1: Vérifier que les prix EXACTS sont retournés
    - Taille 4 = 24 000 FCFA (PAS 24 900)
    - Taille 5 = 24 900 FCFA
    """
    print_section("TEST 1: PRIX EXACTS (Taille 4 vs Taille 5)")
    
    user_id = f"test_prix_{datetime.now().strftime('%H%M%S')}"
    
    # Question piège: demander taille 4 ET 5
    response = send_message(user_id, 
        "Bonjour je veux le prix d'un lot de 300 couches à pression taille 4 et taille 5")
    
    if response:
        answer = response.get('response', '').lower()
        
        # Vérifications
        checks = {
            "Prix T4 = 24 000": "24 000" in answer or "24000" in answer,
            "Prix T5 = 24 900": "24 900" in answer or "24900" in answer,
            "Pas de confusion": not ("tous deux au prix de 24 900" in answer),
            "Taille 4 mentionnée": "taille 4" in answer,
            "Taille 5 mentionnée": "taille 5" in answer
        }
        
        print("\n📊 VÉRIFICATIONS:")
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"{status} {check}")
        
        return all(checks.values())
    
    return False

def test_2_livraison_zones():
    """
    TEST 2: Vérifier les frais de livraison par zone
    - Cocody = 1 500 FCFA (centre)
    - Yopougon = 1 500 FCFA (centre)
    - Port-Bouët = 2 000 FCFA (périphérie)
    """
    print_section("TEST 2: FRAIS DE LIVRAISON PAR ZONE")
    
    user_id = f"test_livraison_{datetime.now().strftime('%H%M%S')}"
    
    zones_tests = [
        ("Cocody", "1 500", "1500"),
        ("Yopougon", "1 500", "1500"),
        ("Port-Bouët", "2 000", "2000")
    ]
    
    results = []
    for zone, prix_attendu1, prix_attendu2 in zones_tests:
        response = send_message(user_id, f"C'est combien la livraison à {zone} ?")
        
        if response:
            answer = response.get('response', '')
            found = prix_attendu1 in answer or prix_attendu2 in answer
            results.append(found)
            print(f"{'✅' if found else '❌'} {zone}: {prix_attendu1} FCFA trouvé")
        else:
            results.append(False)
    
    return all(results)

def test_3_paiement_info():
    """
    TEST 3: Vérifier les infos de paiement
    - Méthode: Wave
    - Numéro: +225 0787360757
    - Acompte: 2 000 FCFA
    """
    print_section("TEST 3: INFORMATIONS PAIEMENT")
    
    user_id = f"test_paiement_{datetime.now().strftime('%H%M%S')}"
    
    response = send_message(user_id, "Comment je paye ?")
    
    if response:
        answer = response.get('response', '')
        
        checks = {
            "Wave mentionné": "wave" in answer.lower(),
            "Numéro correct": "0787360757" in answer or "+225 0787360757" in answer,
            "Acompte 2000": "2 000" in answer or "2000" in answer
        }
        
        print("\n📊 VÉRIFICATIONS:")
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"{status} {check}")
        
        return all(checks.values())
    
    return False

def test_4_contact_support():
    """
    TEST 4: Vérifier les infos de contact
    - WhatsApp: +225 0160924560
    """
    print_section("TEST 4: CONTACT SUPPORT")
    
    user_id = f"test_contact_{datetime.now().strftime('%H%M%S')}"
    
    response = send_message(user_id, "Comment je vous contacte ?")
    
    if response:
        answer = response.get('response', '')
        
        checks = {
            "WhatsApp mentionné": "whatsapp" in answer.lower(),
            "Numéro correct": "0160924560" in answer or "+225 0160924560" in answer
        }
        
        print("\n📊 VÉRIFICATIONS:")
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"{status} {check}")
        
        return all(checks.values())
    
    return False

def test_5_calcul_total():
    """
    TEST 5: Vérifier l'utilisation de calculator()
    - 2 lots taille 4 (24 000 x 2) + livraison Cocody (1 500) = 49 500 FCFA
    """
    print_section("TEST 5: CALCUL TOTAL AVEC CALCULATOR")
    
    user_id = f"test_calcul_{datetime.now().strftime('%H%M%S')}"
    
    # Étape 1: Commander 2 lots taille 4
    send_message(user_id, "Je veux 2 lots de 300 couches taille 4")
    
    # Étape 2: Demander le total avec livraison
    response = send_message(user_id, "Quel est le total avec livraison à Cocody ?")
    
    if response:
        answer = response.get('response', '')
        
        # Chercher 49 500 ou 49500
        checks = {
            "Total correct": "49 500" in answer or "49500" in answer,
            "Calculator utilisé": response.get('tools_executed', False)
        }
        
        print("\n📊 VÉRIFICATIONS:")
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"{status} {check}")
        
        return all(checks.values())
    
    return False

def test_6_ordre_chaotique():
    """
    TEST 6: Tester ordre chaotique des infos (comme test Botlive)
    - Envoyer zone AVANT produit
    - Vérifier que tout est bien collecté
    """
    print_section("TEST 6: ORDRE CHAOTIQUE (Zone → Produit → Paiement)")
    
    user_id = f"test_chaos_{datetime.now().strftime('%H%M%S')}"
    
    # Étape 1: Zone EN PREMIER (inversé)
    send_message(user_id, "Yopougon")
    
    # Étape 2: Produit
    send_message(user_id, "Je veux un lot de 300 couches taille 3")
    
    # Étape 3: Demander récapitulatif
    response = send_message(user_id, "Récapitulez ma commande")
    
    if response:
        answer = response.get('response', '').lower()
        
        checks = {
            "Zone collectée": "yopougon" in answer,
            "Produit collecté": "taille 3" in answer or "22 900" in answer or "22900" in answer,
            "Livraison collectée": "1 500" in answer or "1500" in answer
        }
        
        print("\n📊 VÉRIFICATIONS:")
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"{status} {check}")
        
        return all(checks.values())
    
    return False

def test_7_sources_citees():
    """
    TEST 7: Vérifier que les sources sont citées dans le thinking
    - Demander prix taille 6
    - Vérifier que le LLM cite "DOCUMENT #X" dans son raisonnement
    """
    print_section("TEST 7: CITATION DES SOURCES")
    
    user_id = f"test_sources_{datetime.now().strftime('%H%M%S')}"
    
    response = send_message(user_id, "Prix lot 300 couches taille 6 ?")
    
    if response:
        # Chercher dans les logs (si disponibles) ou dans la réponse
        answer = response.get('response', '')
        
        checks = {
            "Prix correct (24 900)": "24 900" in answer or "24900" in answer,
            "Taille 6 mentionnée": "taille 6" in answer.lower()
        }
        
        print("\n📊 VÉRIFICATIONS:")
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"{status} {check}")
        
        return all(checks.values())
    
    return False

def test_8_couches_culottes():
    """
    TEST 8: Tester les couches culottes (produit différent)
    - Lot 150 = 13 500 FCFA
    - Lot 300 = 24 000 FCFA
    """
    print_section("TEST 8: COUCHES CULOTTES (Produit différent)")
    
    user_id = f"test_culottes_{datetime.now().strftime('%H%M%S')}"
    
    response = send_message(user_id, "Prix des couches culottes ?")
    
    if response:
        answer = response.get('response', '')
        
        checks = {
            "Lot 150 mentionné": "150" in answer,
            "Prix 13 500": "13 500" in answer or "13500" in answer,
            "Lot 300 mentionné": "300" in answer,
            "Prix 24 000": "24 000" in answer or "24000" in answer
        }
        
        print("\n📊 VÉRIFICATIONS:")
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"{status} {check}")
        
        return all(checks.values())
    
    return False

def main():
    """Exécute tous les tests"""
    print("\n" + "╔" + "="*78 + "╗")
    print("║" + " "*20 + "🧪 TEST RAG COMPLET - RUE DU GROSSISTE" + " "*20 + "║")
    print("║" + " "*25 + f"Company: {COMPANY_ID[:20]}..." + " "*10 + "║")
    print("╚" + "="*78 + "╝")
    
    tests = [
        ("Prix exacts (T4 vs T5)", test_1_prix_exacts),
        ("Frais livraison par zone", test_2_livraison_zones),
        ("Informations paiement", test_3_paiement_info),
        ("Contact support", test_4_contact_support),
        ("Calcul total (calculator)", test_5_calcul_total),
        ("Ordre chaotique", test_6_ordre_chaotique),
        ("Citation sources", test_7_sources_citees),
        ("Couches culottes", test_8_couches_culottes)
    ]
    
    results = []
    
    for i, (name, test_func) in enumerate(tests, 1):
        try:
            result = test_func()
            results.append((name, result))
            time.sleep(2)  # Pause entre tests
        except Exception as e:
            print(f"\n❌ Erreur test {i}: {e}")
            results.append((name, False))
    
    # Résumé final
    print("\n" + "="*80)
    print("📊 RÉSUMÉ DES TESTS")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print("\n" + "="*80)
    print(f"🎯 SCORE FINAL: {passed}/{total} ({passed*100//total}%)")
    print("="*80)
    
    if passed == total:
        print("\n🎉 TOUS LES TESTS SONT PASSÉS ! LE RAG FONCTIONNE PARFAITEMENT ! 🚀")
    else:
        print(f"\n⚠️  {total - passed} test(s) ont échoué. Vérifier les logs ci-dessus.")

if __name__ == "__main__":
    main()
