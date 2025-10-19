#!/usr/bin/env python3
"""
🧪 TEST RAPIDE OCR - DÉCIMALES VS MILLIERS
Valide la détection correcte des montants avec séparateurs
"""

import re

def parse_amount(raw_amount):
    """Parse un montant en distinguant décimales vs milliers"""
    # Nettoyer signes
    raw_amount = raw_amount.replace('-', '').replace('+', '').strip()
    
    # Analyser si c'est des décimales ou des milliers
    # "202.00" → décimales (2 chiffres après) → 202
    # "2.020" → milliers (3 chiffres après) → 2020
    # "10.100" → milliers → 10100
    if '.' in raw_amount or ',' in raw_amount:
        parts = raw_amount.replace(',', '.').split('.')
        if len(parts) == 2:
            if len(parts[1]) == 2:
                # Décimales : ignorer
                return parts[0]
            elif len(parts[1]) == 3:
                # Milliers : concaténer
                return parts[0] + parts[1]
            else:
                return parts[0]
        else:
            return raw_amount.replace('.', '').replace(',', '')
    else:
        return raw_amount

def test_parse_amount():
    """Test la fonction parse_amount"""
    test_cases = [
        # Format: (input, expected, description)
        ("-2.020", "2020", "Milliers avec signe négatif"),
        ("-10.100", "10100", "Milliers 5 chiffres"),
        ("202.00", "202", "Décimales centimes"),
        ("30.000", "30000", "Milliers 5 chiffres"),
        ("5.000", "5000", "Milliers 4 chiffres"),
        ("+2,020", "2020", "Milliers avec virgule"),
        ("3839.00", "3839", "Décimales 4 chiffres"),
        ("100", "100", "Sans séparateur"),
        ("2020", "2020", "Sans séparateur 4 chiffres"),
    ]
    
    print("=" * 70)
    print("🧪 TEST FONCTION parse_amount()")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for input_val, expected, description in test_cases:
        result = parse_amount(input_val)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} | {input_val:>10} → {result:>6} (attendu: {expected:>6}) | {description}")
    
    print("=" * 70)
    print(f"📊 RÉSULTAT: {passed}/{len(test_cases)} tests réussis")
    if failed > 0:
        print(f"❌ {failed} tests échoués")
    else:
        print("✅ TOUS LES TESTS RÉUSSIS !")
    print("=" * 70)
    return failed == 0

def test_patterns():
    """Test les patterns regex sur textes réels"""
    
    test_texts = [
        # Format: (text, expected_amount, description)
        ("À ATTIELO 07 87 36 07 57 -2.020F 07 oct", "2020", "Wave -2.020F"),
        ("À M ABRAZA 01 01 53 87 82 -10.100F 06 oct", "10100", "Wave -10.100F"),
        ("De ATTIELO 07 87 36 07 57 30.000F 05 oct", "30000", "Wave 30.000F"),
        ("Le transfert de 202.00 FCFA vers le 0787360757", "202", "Orange Money 202.00"),
        ("Solde:3839.00 FCFA", "3839", "Solde (pour vérification)"),
        ("transfert de 5.000 FCFA vers 0787360757", "5000", "Transfert milliers"),
    ]
    
    # Pattern générique pour tous les montants
    pattern = r'([-+]?\d{1,5}(?:[.,]\d{2,3})?)\s*f(?:cfa)?'
    
    print("\n" + "=" * 70)
    print("🔍 TEST PATTERNS REGEX SUR TEXTES RÉELS")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for text, expected, description in test_texts:
        m = re.search(pattern, text.lower())
        if m:
            raw_amount = m.group(1)
            result = parse_amount(raw_amount)
            status = "✅ PASS" if result == expected else "❌ FAIL"
            
            if result == expected:
                passed += 1
            else:
                failed += 1
            
            print(f"{status} | Détecté: {result:>6} FCFA (attendu: {expected:>6}) | {description}")
        else:
            failed += 1
            print(f"❌ FAIL | Aucun montant détecté | {description}")
    
    print("=" * 70)
    print(f"📊 RÉSULTAT: {passed}/{len(test_texts)} tests réussis")
    if failed > 0:
        print(f"❌ {failed} tests échoués")
    else:
        print("✅ TOUS LES TESTS RÉUSSIS !")
    print("=" * 70)
    return failed == 0

def test_real_ocr_text():
    """Test sur le texte OCR réel du log"""
    
    ocr_text = """1215 = > A P 
0 ,l 4,/ % 0 
32.075F & 
Transfert 
Paiements 
Banque 
Cadeaux 
Coffre 
À ATTIELO 07 87 36 07 57 
-2.020F 
07 oct , 11.17 
À M ABRAZA 01 01 53 87 82 
-10.100F 
06 oct , 08.38 
De ATTIELO 07 87 36 07 57 
30.OOOF 
05 oct , 18.12"""
    
    print("\n" + "=" * 70)
    print("🎯 TEST SUR TEXTE OCR RÉEL")
    print("=" * 70)
    
    # NETTOYAGE OCR: Corriger O → 0 dans les montants
    print("📝 Nettoyage OCR: O → 0")
    print(f"   Avant: '30.OOOF'")
    ocr_text = re.sub(r'(\d+[.,])O+F', lambda m: m.group(0).replace('O', '0'), ocr_text, flags=re.IGNORECASE)
    ocr_text = re.sub(r'(\d)O(\d)', r'\g<1>0\g<2>', ocr_text)
    print(f"   Après: '30.000F' ✅\n")
    
    # Pattern pour trouver tous les montants
    pattern = r'([-+]?\d{1,5}(?:[.,]\d{2,3})?)\s*[FO](?:\s|$|,)'
    
    matches = re.findall(pattern, ocr_text)
    
    print(f"📋 Montants détectés dans le texte:")
    for i, raw_amount in enumerate(matches, 1):
        parsed = parse_amount(raw_amount)
        print(f"  {i}. {raw_amount:>10} → {parsed:>6} FCFA")
    
    # Vérifications attendues
    expected_amounts = ["32075", "2020", "10100", "30000"]
    parsed_amounts = [parse_amount(m) for m in matches]
    
    print("\n🔍 Vérification des montants attendus:")
    all_ok = True
    for expected in expected_amounts:
        if expected in parsed_amounts:
            print(f"  ✅ {expected} FCFA détecté")
        else:
            print(f"  ❌ {expected} FCFA NON détecté")
            all_ok = False
    
    print("=" * 70)
    if all_ok:
        print("✅ TOUS LES MONTANTS ATTENDUS DÉTECTÉS !")
    else:
        print("❌ CERTAINS MONTANTS MANQUANTS")
    print("=" * 70)
    
    return all_ok

def main():
    """Lance tous les tests"""
    print("\n" + "🚀 " * 20)
    print("🧪 TESTS VALIDATION OCR - DÉCIMALES VS MILLIERS")
    print("🚀 " * 20 + "\n")
    
    results = []
    
    # Test 1: Fonction parse_amount
    results.append(("parse_amount()", test_parse_amount()))
    
    # Test 2: Patterns regex
    results.append(("Patterns regex", test_patterns()))
    
    # Test 3: Texte OCR réel
    results.append(("Texte OCR réel", test_real_ocr_text()))
    
    # Résumé
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ FINAL")
    print("=" * 70)
    
    for test_name, passed in results:
        status = "✅ RÉUSSI" if passed else "❌ ÉCHOUÉ"
        print(f"{status} | {test_name}")
    
    all_passed = all(result for _, result in results)
    
    print("=" * 70)
    if all_passed:
        print("🎉 TOUS LES TESTS SONT RÉUSSIS ! 🎉")
        print("✅ Le système est prêt pour la production")
    else:
        print("❌ CERTAINS TESTS ONT ÉCHOUÉ")
        print("⚠️ Corrections nécessaires avant déploiement")
    print("=" * 70 + "\n")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    exit(main())
