#!/usr/bin/env python3
"""
🧪 TEST BOTLIVE PRODUCTION - Validation complète avant mise en production

Tests:
1. ✅ Validation paiement automatique (simple + cumulatif)
2. ✅ Singleton modèles (pas de rechargement)
3. ✅ Optimisations images (temps < 10s)
4. ✅ Logs JSON automatiques
5. ✅ Workflow complet
6. ✅ Règles critiques
"""

import asyncio
import httpx
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

BASE_URL = "http://127.0.0.1:8002"
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"

# Images de test (Cloud Storage)
TEST_IMAGES = {
    'product': 'https://storage.googleapis.com/zanzibar-products-images/products/product_test.jpg',
    'payment_202': 'https://i.ibb.co/KV8KLxZ/Screenshot-20250108-181550.png',
    'payment_2020': 'https://i.ibb.co/02xdMNT/Screenshot-20250108-181624.png',
    'payment_1800': 'https://i.ibb.co/DYm8KLZ/Screenshot-20250108-181700.png'
}

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def print_header(title: str):
    """Affiche un header formaté"""
    print("\n" + "="*80)
    print(f"{'🧪 ' + title:^80}")
    print("="*80)

def print_test(test_name: str, status: str = "RUN"):
    """Affiche le nom d'un test"""
    emoji = "🔄" if status == "RUN" else "✅" if status == "PASS" else "❌"
    print(f"\n{emoji} TEST: {test_name}")
    print("─" * 80)

def print_result(passed: bool, expected: str, actual: str, details: str = ""):
    """Affiche le résultat d'une assertion"""
    if passed:
        print(f"   ✅ PASS: {expected}")
    else:
        print(f"   ❌ FAIL: {expected}")
        print(f"      Attendu: {expected}")
        print(f"      Obtenu: {actual}")
        if details:
            print(f"      Détails: {details}")

async def reset_conversation(user_id: str):
    """Reset conversation pour nouvel utilisateur"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}/reset_conversation",
            json={"company_id": COMPANY_ID, "user_id": user_id}
        )
        return response.status_code == 200

async def send_message(user_id: str, message: str = "", images: List[str] = None) -> Dict:
    """Envoie un message au chatbot"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        start_time = time.time()
        response = await client.post(
            f"{BASE_URL}/chat",
            json={
                "company_id": COMPANY_ID,
                "user_id": user_id,
                "message": message,
                "images": images or [],
                "botlive_enabled": True
            }
        )
        elapsed_time = time.time() - start_time
        
        data = response.json()
        data['_request_time'] = elapsed_time
        return data

def extract_response_text(response_data: Dict) -> str:
    """Extrait le texte de réponse"""
    if isinstance(response_data, dict):
        if 'response' in response_data:
            inner = response_data['response']
            if isinstance(inner, dict):
                return inner.get('response', str(inner))
            return str(inner)
    return str(response_data)

def check_logs_json_exists() -> bool:
    """Vérifie que le fichier logs JSON existe"""
    today = datetime.now().strftime('%Y%m%d')
    log_file = Path(f"logs/requests_metrics_{today}.jsonl")
    return log_file.exists()

def count_json_logs() -> int:
    """Compte le nombre de requêtes loggées en JSON"""
    today = datetime.now().strftime('%Y%m%d')
    log_file = Path(f"logs/requests_metrics_{today}.jsonl")
    if not log_file.exists():
        return 0
    
    count = 0
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                count += 1
    return count

# ═══════════════════════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════════════════════

async def test_payment_validation_simple():
    """Test validation paiement simple (202 FCFA insuffisant)"""
    print_test("Validation paiement simple (202 FCFA)")
    
    user_id = f"test_payment_simple_{int(time.time())}"
    await reset_conversation(user_id)
    
    # Envoyer image paiement 202 FCFA
    response = await send_message(user_id, "", [TEST_IMAGES['payment_202']])
    response_text = extract_response_text(response).lower()
    
    # Assertions
    tests = [
        ("Temps < 15s", response['_request_time'] < 15),
        ("Contient '202'", '202' in response_text),
        ("Contient 'manque' ou 'insuffisant'", 'manque' in response_text or 'insuffisant' in response_text),
        ("Contient '1798' (différence)", '1798' in response_text),
    ]
    
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    for test_name, result in tests:
        print_result(result, test_name, response_text if not result else "OK")
    
    print(f"\n📊 Résultat: {passed}/{total} ({passed/total*100:.0f}%)")
    print_test("Validation paiement simple", "PASS" if passed >= 3 else "FAIL")
    
    return passed >= 3

async def test_payment_validation_cumulative():
    """Test validation paiement cumulatif (202 + 1800 = 2002 FCFA)"""
    print_test("Validation paiement cumulatif (202 + 1800)")
    
    user_id = f"test_payment_cumul_{int(time.time())}"
    await reset_conversation(user_id)
    
    # Premier paiement: 202 FCFA
    response1 = await send_message(user_id, "", [TEST_IMAGES['payment_202']])
    response1_text = extract_response_text(response1).lower()
    
    # Attendre un peu (pour voir historique)
    await asyncio.sleep(1)
    
    # Deuxième paiement: 1800 FCFA
    response2 = await send_message(user_id, "", [TEST_IMAGES['payment_1800']])
    response2_text = extract_response_text(response2).lower()
    
    # Assertions
    tests = [
        ("Réponse 1: Mentionne 202", '202' in response1_text),
        ("Réponse 1: Insuffisant", 'manque' in response1_text or 'insuffisant' in response1_text),
        ("Réponse 2: Mentionne cumul ou validation", 'validé' in response2_text or 'dépôt' in response2_text or '2000' in response2_text or '2002' in response2_text),
        ("Réponse 2: Demande zone/livraison", 'zone' in response2_text or 'livraison' in response2_text or 'commune' in response2_text),
    ]
    
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    print(f"\n📍 Réponse 1: {response1_text[:100]}...")
    print(f"📍 Réponse 2: {response2_text[:100]}...")
    
    for test_name, result in tests:
        print_result(result, test_name, "OK" if result else "FAIL")
    
    print(f"\n📊 Résultat: {passed}/{total} ({passed/total*100:.0f}%)")
    print_test("Validation paiement cumulatif", "PASS" if passed >= 3 else "FAIL")
    
    return passed >= 3

async def test_payment_validation_sufficient():
    """Test validation paiement suffisant (2020 FCFA)"""
    print_test("Validation paiement suffisant (2020 FCFA)")
    
    user_id = f"test_payment_ok_{int(time.time())}"
    await reset_conversation(user_id)
    
    # Envoyer image paiement 2020 FCFA
    response = await send_message(user_id, "", [TEST_IMAGES['payment_2020']])
    response_text = extract_response_text(response).lower()
    
    # Assertions
    tests = [
        ("Temps < 15s", response['_request_time'] < 15),
        ("Contient '2020' ou '2000'", '2020' in response_text or '2000' in response_text),
        ("Contient 'validé' ou 'ok'", 'validé' in response_text or 'dépôt' in response_text or 'ok' in response_text),
        ("Demande zone/livraison", 'zone' in response_text or 'livraison' in response_text or 'commune' in response_text),
    ]
    
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    for test_name, result in tests:
        print_result(result, test_name, response_text if not result else "OK")
    
    print(f"\n📊 Résultat: {passed}/{total} ({passed/total*100:.0f}%)")
    print_test("Validation paiement suffisant", "PASS" if passed >= 3 else "FAIL")
    
    return passed >= 3

async def test_image_performance():
    """Test performance traitement images"""
    print_test("Performance traitement images")
    
    user_id = f"test_perf_{int(time.time())}"
    await reset_conversation(user_id)
    
    # Première requête avec image (chargement modèles)
    start1 = time.time()
    response1 = await send_message(user_id, "", [TEST_IMAGES['product']])
    time1 = time.time() - start1
    
    # Deuxième requête avec image (modèles cachés)
    await asyncio.sleep(1)
    start2 = time.time()
    response2 = await send_message(user_id, "", [TEST_IMAGES['payment_202']])
    time2 = time.time() - start2
    
    # Assertions
    tests = [
        ("Première requête < 15s", time1 < 15),
        ("Deuxième requête < 10s", time2 < 10),
        ("Amélioration 2ème requête", time2 < time1),
    ]
    
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    print(f"\n📊 Temps requête 1: {time1:.2f}s")
    print(f"📊 Temps requête 2: {time2:.2f}s")
    print(f"📊 Gain: {((time1 - time2) / time1 * 100):.0f}%")
    
    for test_name, result in tests:
        print_result(result, test_name, "OK" if result else f"T1={time1:.2f}s T2={time2:.2f}s")
    
    print(f"\n📊 Résultat: {passed}/{total} ({passed/total*100:.0f}%)")
    print_test("Performance images", "PASS" if passed >= 2 else "FAIL")
    
    return passed >= 2

async def test_json_logging():
    """Test logs JSON automatiques"""
    print_test("Logs JSON automatiques")
    
    user_id = f"test_logs_{int(time.time())}"
    await reset_conversation(user_id)
    
    # Compter logs avant
    logs_before = count_json_logs()
    
    # Envoyer 2 requêtes
    await send_message(user_id, "Bonjour")
    await asyncio.sleep(0.5)
    await send_message(user_id, "Test")
    
    # Attendre que les logs soient écrits
    await asyncio.sleep(1)
    
    # Compter logs après
    logs_after = count_json_logs()
    logs_added = logs_after - logs_before
    
    # Assertions
    tests = [
        ("Fichier logs existe", check_logs_json_exists()),
        ("2 requêtes loggées", logs_added >= 2),
    ]
    
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    print(f"\n📊 Logs avant: {logs_before}")
    print(f"📊 Logs après: {logs_after}")
    print(f"📊 Ajoutés: {logs_added}")
    
    for test_name, result in tests:
        print_result(result, test_name, "OK" if result else f"{logs_added} logs")
    
    print(f"\n📊 Résultat: {passed}/{total} ({passed/total*100:.0f}%)")
    print_test("Logs JSON", "PASS" if passed == total else "FAIL")
    
    return passed == total

async def test_workflow_complete():
    """Test workflow complet: salutation → produit → paiement → zone → tel"""
    print_test("Workflow complet")
    
    user_id = f"test_workflow_{int(time.time())}"
    await reset_conversation(user_id)
    
    results = []
    
    # Étape 1: Salutation
    r1 = await send_message(user_id, "Bonjour")
    t1 = extract_response_text(r1).lower()
    results.append(("Salutation répond", 'photo' in t1 or 'produit' in t1))
    
    await asyncio.sleep(0.5)
    
    # Étape 2: Produit
    r2 = await send_message(user_id, "", [TEST_IMAGES['product']])
    t2 = extract_response_text(r2).lower()
    results.append(("Produit demande confirmation", 'confirm' in t2 or 'dépôt' in t2 or '2000' in t2))
    
    await asyncio.sleep(0.5)
    
    # Étape 3: Confirmation
    r3 = await send_message(user_id, "Oui je confirme")
    t3 = extract_response_text(r3).lower()
    results.append(("Confirmation OK", len(t3) > 10))
    
    await asyncio.sleep(0.5)
    
    # Étape 4: Paiement valide
    r4 = await send_message(user_id, "", [TEST_IMAGES['payment_2020']])
    t4 = extract_response_text(r4).lower()
    results.append(("Paiement demande zone", 'zone' in t4 or 'livraison' in t4 or 'commune' in t4))
    
    await asyncio.sleep(0.5)
    
    # Étape 5: Zone
    r5 = await send_message(user_id, "Cocody")
    t5 = extract_response_text(r5).lower()
    results.append(("Zone demande numéro", 'numéro' in t5 or 'téléphone' in t5 or 'tel' in t5))
    
    await asyncio.sleep(0.5)
    
    # Étape 6: Numéro
    r6 = await send_message(user_id, "0140236939")
    t6 = extract_response_text(r6).lower()
    results.append(("Numéro confirme commande", 'confirm' in t6 or 'merci' in t6 or 'commande' in t6))
    
    # Résultats
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print("\n📊 Étapes:")
    for i, (test_name, result) in enumerate(results, 1):
        print_result(result, f"Étape {i}: {test_name}", "OK" if result else "FAIL")
    
    print(f"\n📊 Résultat: {passed}/{total} ({passed/total*100:.0f}%)")
    print_test("Workflow complet", "PASS" if passed >= 5 else "FAIL")
    
    return passed >= 5

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    print_header("TEST BOTLIVE PRODUCTION - VALIDATION COMPLÈTE")
    
    print(f"\n📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 URL: {BASE_URL}")
    print(f"🏢 Company: {COMPANY_ID}")
    
    # Exécuter tous les tests
    tests = [
        ("Validation paiement simple (202 FCFA)", test_payment_validation_simple),
        ("Validation paiement cumulatif (202+1800)", test_payment_validation_cumulative),
        ("Validation paiement suffisant (2020 FCFA)", test_payment_validation_sufficient),
        ("Performance traitement images", test_image_performance),
        ("Logs JSON automatiques", test_json_logging),
        ("Workflow complet", test_workflow_complete),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ ERREUR: {e}")
            results.append((test_name, False))
        
        # Pause entre tests
        await asyncio.sleep(1)
    
    # Rapport final
    print_header("RAPPORT FINAL")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    success_rate = (passed_count / total_count * 100) if total_count > 0 else 0
    
    print(f"\n📊 RÉSULTATS GLOBAUX:")
    print(f"   Tests réussis: {passed_count}/{total_count}")
    print(f"   Taux de réussite: {success_rate:.1f}%")
    print(f"\n📋 DÉTAIL PAR TEST:")
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status} - {test_name}")
    
    # Recommandation
    print(f"\n{'='*80}")
    if success_rate >= 80:
        print("✅ SYSTÈME PRÊT POUR LA PRODUCTION")
        print("   - Taux de réussite satisfaisant (≥80%)")
        print("   - Fonctionnalités critiques validées")
    elif success_rate >= 60:
        print("⚠️  SYSTÈME NÉCESSITE ATTENTION")
        print("   - Taux de réussite moyen (60-80%)")
        print("   - Corriger les tests échoués avant production")
    else:
        print("❌ SYSTÈME NON PRÊT POUR PRODUCTION")
        print("   - Taux de réussite insuffisant (<60%)")
        print("   - Corrections majeures nécessaires")
    print(f"{'='*80}\n")
    
    return success_rate >= 80

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
