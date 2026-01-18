#!/usr/bin/env python3
# ==============================================================================
# VALIDATION CORPUS V4 - DIAGNOSTIC COMPLET
# ==============================================================================
# Usage: python validate_corpus_v4.py
# ==============================================================================

import os
import sys
from collections import Counter

_THIS_DIR = os.path.dirname(__file__)
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

def validate_syntax():
    """Vérifie la syntaxe Python du corpus."""
    print("=" * 80)
    print("1. VALIDATION SYNTAXE")
    print("=" * 80)
    
    try:
        # Importer le corpus
        from core.universal_corpus import (
            INTENT_PROTOTYPES_V4,
            UNIVERSAL_ECOMMERCE_INTENT_CORPUS_V4
        )
        print("✅ Syntaxe Python valide")
        print(f"✅ INTENT_PROTOTYPES_V4: {len(INTENT_PROTOTYPES_V4)} intents")
        print(f"✅ CORPUS_V4: {len(UNIVERSAL_ECOMMERCE_INTENT_CORPUS_V4)} intents")
        return True, INTENT_PROTOTYPES_V4, UNIVERSAL_ECOMMERCE_INTENT_CORPUS_V4
    
    except SyntaxError as e:
        print(f"❌ ERREUR SYNTAXE: {e}")
        print(f"   Ligne {e.lineno}: {e.text}")
        return False, None, None
    
    except Exception as e:
        print(f"❌ ERREUR IMPORT: {e}")
        return False, None, None


def analyze_paiement_bias(corpus):
    """Analyse si PAIEMENT_TRANSACTION est biaisé."""
    print("\n" + "=" * 80)
    print("2. ANALYSE BIAIS PAIEMENT_TRANSACTION")
    print("=" * 80)
    
    paiement_examples = corpus.get(7, {}).get("exemples", [])
    
    # Compteurs
    total = len(paiement_examples)
    with_keyword = 0
    generic = 0
    
    # Mots-clés transactionnels
    payment_keywords = [
        "pay", "paiement", "payer", "argent", "money", "wave", 
        "orange", "mobile", "mtn", "espèce", "carte", "acompte", 
        "dépôt", "facture", "reçu", "preuve", "acceptez", "verser"
    ]
    
    # Salutations génériques
    greetings = ["bonjour", "salut", "merci", "bonsoir"]
    
    print(f"\n📊 Total exemples PAIEMENT: {total}\n")
    
    suspicious = []
    
    for i, ex in enumerate(paiement_examples, 1):
        ex_lower = ex.lower()
        has_kw = any(kw in ex_lower for kw in payment_keywords)
        is_greeting = any(gr in ex_lower for gr in greetings) and len(ex.split()) <= 3
        
        if has_kw:
            with_keyword += 1
        
        if is_greeting:
            generic += 1
            suspicious.append(f"  [{i:02d}] ⚠️  {ex}")
        elif not has_kw:
            suspicious.append(f"  [{i:02d}] ❌ {ex} (AUCUN mot-clé)")
    
    print(f"✅ Avec mot-clé transactionnel: {with_keyword}/{total} ({with_keyword/total*100:.1f}%)")
    print(f"⚠️  Génériques/suspects: {len(suspicious)}/{total} ({len(suspicious)/total*100:.1f}%)")
    
    if suspicious:
        print(f"\n🔍 EXEMPLES SUSPECTS (à retirer):")
        for s in suspicious[:10]:  # Max 10
            print(s)
    
    return len(suspicious) == 0


def analyze_distribution(corpus):
    """Analyse la distribution des exemples."""
    print("\n" + "=" * 80)
    print("3. DISTRIBUTION DES EXEMPLES")
    print("=" * 80)
    
    distribution = {}
    for intent_id, data in corpus.items():
        label = data.get("label", "UNKNOWN")
        count = len(data.get("exemples", []))
        distribution[label] = count
    
    print("\n📊 Nombre d'exemples par intent:\n")
    for label, count in sorted(distribution.items(), key=lambda x: x[1], reverse=True):
        bar = "█" * (count // 2)
        print(f"  {label:25s} | {count:3d} | {bar}")
    
    # Check équilibrage
    counts = list(distribution.values())
    min_count = min(counts)
    max_count = max(counts)
    ratio = max_count / min_count if min_count > 0 else 0
    
    print(f"\n📈 Statistiques:")
    print(f"  Min: {min_count} | Max: {max_count} | Ratio: {ratio:.2f}x")
    
    if ratio > 3:
        print(f"  ⚠️  DÉSÉQUILIBRE détecté (ratio > 3x)")
        return False
    else:
        print(f"  ✅ Distribution acceptable")
        return True


def check_duplicates(corpus):
    """Vérifie les doublons entre intents."""
    print("\n" + "=" * 80)
    print("4. VÉRIFICATION DOUBLONS")
    print("=" * 80)
    
    seen = {}
    duplicates = []
    
    for intent_id, data in corpus.items():
        label = data.get("label", "UNKNOWN")
        for ex in data.get("exemples", []):
            key = ex.strip().lower()
            if key in seen:
                duplicates.append(f"  '{ex}' → {seen[key]} ET {label}")
            else:
                seen[key] = label
    
    if duplicates:
        print(f"\n❌ {len(duplicates)} DOUBLONS détectés:\n")
        for dup in duplicates[:10]:  # Max 10
            print(dup)
        return False
    else:
        print("\n✅ Aucun doublon détecté")
        return True


def analyze_salut_reinforcement(corpus):
    """Vérifie si SALUT a les contre-exemples."""
    print("\n" + "=" * 80)
    print("5. VÉRIFICATION SALUT_POLITESSE")
    print("=" * 80)
    
    salut_examples = corpus.get(1, {}).get("exemples", [])
    
    # Patterns attendus (contre-exemples anti-PAIEMENT)
    expected_patterns = [
        "salut comment allez-vous",
        "bonsoir j'espère que vous allez bien",
        "bjr madame désolé du dérangement",
        "hey j'espère que tout va bien",
        "merci beaucoup pour votre aide"
    ]
    
    found = []
    for pattern in expected_patterns:
        for ex in salut_examples:
            if pattern.lower() in ex.lower():
                found.append(pattern)
                break
    
    print(f"\n📊 Contre-exemples trouvés: {len(found)}/{len(expected_patterns)}\n")
    
    for pattern in expected_patterns:
        status = "✅" if pattern in found else "❌"
        print(f"  {status} '{pattern}'")
    
    return len(found) >= 4  # Au moins 4/5


def main():
    """Exécute toutes les validations."""
    print("\n" + "=" * 80)
    print("VALIDATION CORPUS V4 - DIAGNOSTIC COMPLET")
    print("=" * 80 + "\n")
    
    # Test 1: Syntaxe
    syntax_ok, prototypes, corpus = validate_syntax()
    if not syntax_ok:
        print("\n❌ ÉCHEC: Corriger la syntaxe d'abord")
        sys.exit(1)
    
    # Test 2: Biais PAIEMENT
    paiement_ok = analyze_paiement_bias(corpus)
    
    # Test 3: Distribution
    distribution_ok = analyze_distribution(corpus)
    
    # Test 4: Doublons
    duplicates_ok = check_duplicates(corpus)
    
    # Test 5: SALUT reinforcement
    salut_ok = analyze_salut_reinforcement(corpus)
    
    # Résumé
    print("\n" + "=" * 80)
    print("RÉSUMÉ VALIDATION")
    print("=" * 80 + "\n")
    
    tests = [
        ("Syntaxe Python", syntax_ok),
        ("PAIEMENT purifié", paiement_ok),
        ("Distribution équilibrée", distribution_ok),
        ("Aucun doublon", duplicates_ok),
        ("SALUT renforcé", salut_ok)
    ]
    
    passed = sum(1 for _, ok in tests if ok)
    total = len(tests)
    
    for test_name, ok in tests:
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"  {status} | {test_name}")
    
    print(f"\n📊 Score: {passed}/{total} ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n✅ CORPUS V4 VALIDÉ - Prêt pour prefilter")
        sys.exit(0)
    else:
        print("\n⚠️  CORPUS A DES PROBLÈMES - Appliquer le patch nécessaire")
        sys.exit(1)


if __name__ == "__main__":
    main()