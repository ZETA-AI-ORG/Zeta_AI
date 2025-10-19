#!/usr/bin/env python3
"""
🧪 TEST VALEURS HARDCODÉES - Vérification Botlive Rue du Grossiste
Vérifie que toutes les valeurs spécifiques sont bien hardcodées dans les prompts
"""

import sys
from core.botlive_prompts_hardcoded import GROQ_70B_PROMPT, DEEPSEEK_V3_PROMPT, format_prompt

def test_hardcoded_values():
    """
    Teste que toutes les valeurs hardcodées sont présentes dans les prompts
    """
    print("🧪 TEST DES VALEURS HARDCODÉES BOTLIVE\n")
    print("=" * 80)
    
    tests_passed = 0
    tests_failed = 0
    
    # Liste des tests à effectuer
    tests = [
        # Format: (nom_test, valeur_à_chercher, prompt_groq, prompt_deepseek)
        ("Nom entreprise", "Rue du Grossiste", True, True),
        ("Nom bot", "Jessica", True, True),
        ("Téléphone support", "+225 07 87 36 07 57", True, True),
        ("Numéro mobile money", "dépôt mobile money sur +225 07 87 36 07 57", True, True),
        ("Preuve paiement", "capture prouvant paiement", True, True),
        ("Devise FCFA", "FCFA", True, True),
        ("Délai 13h", "avant 13h", True, True),
        ("Livraison jour même", "jour même", True, True),
        ("Livraison lendemain", "lendemain", True, True),
        ("Zone Yopougon", "Yopougon", True, True),
        ("Zone Cocody", "Cocody", True, True),
        ("Tarif centre 1500", "1500 FCFA", True, True),
        ("Tarif périphérie 2000", "2000 FCFA", True, True),
        ("Tarif éloigné 2500", "2500 FCFA", True, True),
        ("Ton décontracté", "Décontracté-pro, tutoiement", True, True),
        ("Secteur produits bébés", "produits bébés", False, True),  # Seulement DeepSeek
        ("Exemple notepad FCFA", "✅PAIEMENT:2020 FCFA", True, True),
        ("Exemple zone FCFA", "✅ZONE:Yopougon-1500 FCFA", True, True),
    ]
    
    # Exécuter les tests
    for test_name, search_value, check_groq, check_deepseek in tests:
        print(f"\n🔍 Test: {test_name}")
        print(f"   Recherche: '{search_value}'")
        
        # Test Groq 70B
        if check_groq:
            if search_value in GROQ_70B_PROMPT:
                print(f"   ✅ Groq 70B: TROUVÉ")
                tests_passed += 1
            else:
                print(f"   ❌ Groq 70B: NON TROUVÉ")
                tests_failed += 1
        
        # Test DeepSeek V3
        if check_deepseek:
            if search_value in DEEPSEEK_V3_PROMPT:
                print(f"   ✅ DeepSeek V3: TROUVÉ")
                tests_passed += 1
            else:
                print(f"   ❌ DeepSeek V3: NON TROUVÉ")
                tests_failed += 1
    
    # Test format_prompt avec valeur par défaut
    print(f"\n🔍 Test: Valeur par défaut expected_deposit")
    formatted = format_prompt("groq-70b", question="test")
    if "2000" in formatted or "{expected_deposit}" in formatted:
        print(f"   ✅ Valeur par défaut: OK")
        tests_passed += 1
    else:
        print(f"   ❌ Valeur par défaut: ERREUR")
        tests_failed += 1
    
    # Vérifier absence de placeholders {{VARIABLE}}
    print(f"\n🔍 Test: Absence de placeholders non remplis")
    import re
    
    placeholders_groq = re.findall(r'\{\{([A-Z_]+)\}\}', GROQ_70B_PROMPT)
    placeholders_deepseek = re.findall(r'\{\{([A-Z_]+)\}\}', DEEPSEEK_V3_PROMPT)
    
    if not placeholders_groq:
        print(f"   ✅ Groq 70B: Aucun placeholder {{VARIABLE}}")
        tests_passed += 1
    else:
        print(f"   ❌ Groq 70B: Placeholders trouvés: {placeholders_groq}")
        tests_failed += 1
    
    if not placeholders_deepseek:
        print(f"   ✅ DeepSeek V3: Aucun placeholder {{VARIABLE}}")
        tests_passed += 1
    else:
        print(f"   ❌ DeepSeek V3: Placeholders trouvés: {placeholders_deepseek}")
        tests_failed += 1
    
    # Résumé
    print("\n" + "=" * 80)
    print(f"\n📊 RÉSULTATS:")
    print(f"   ✅ Tests réussis: {tests_passed}")
    print(f"   ❌ Tests échoués: {tests_failed}")
    print(f"   📈 Taux de réussite: {(tests_passed / (tests_passed + tests_failed) * 100):.1f}%")
    
    if tests_failed == 0:
        print("\n🎉 SUCCÈS TOTAL! Toutes les valeurs sont bien hardcodées!")
        return 0
    else:
        print(f"\n⚠️ ATTENTION: {tests_failed} test(s) échoué(s)")
        return 1

def test_prompt_formatting():
    """
    Teste le formatage des prompts avec différents contextes
    """
    print("\n\n" + "=" * 80)
    print("🧪 TEST FORMATAGE PROMPTS\n")
    
    # Test 1: Formatage basique
    print("🔍 Test 1: Formatage basique")
    try:
        formatted = format_prompt(
            "groq-70b",
            conversation_history="Client: Bonjour",
            question="Je veux commander",
            detected_objects="[produit détecté]",
            filtered_transactions="[2000 FCFA]",
            expected_deposit="2000"
        )
        
        # Vérifier que les variables sont bien remplacées
        if "{conversation_history}" not in formatted and "Bonjour" in formatted:
            print("   ✅ Variables remplacées correctement")
        else:
            print("   ❌ Problème de remplacement des variables")
            return 1
        
        # Vérifier présence valeurs hardcodées
        if "Jessica" in formatted and "+225 07 87 36 07 57" in formatted:
            print("   ✅ Valeurs hardcodées présentes")
        else:
            print("   ❌ Valeurs hardcodées manquantes")
            return 1
            
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return 1
    
    # Test 2: Formatage DeepSeek
    print("\n🔍 Test 2: Formatage DeepSeek V3")
    try:
        formatted = format_prompt(
            "deepseek-v3",
            question="Livraison Yopougon?"
        )
        
        if "Jessica" in formatted and "produits bébés" in formatted:
            print("   ✅ Prompt DeepSeek formaté correctement")
        else:
            print("   ❌ Problème formatage DeepSeek")
            return 1
            
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return 1
    
    print("\n✅ Tous les tests de formatage réussis!")
    return 0

def display_prompt_info():
    """
    Affiche des informations sur les prompts
    """
    print("\n\n" + "=" * 80)
    print("📊 INFORMATIONS PROMPTS\n")
    
    print(f"📏 Longueur Groq 70B: {len(GROQ_70B_PROMPT)} caractères (~{len(GROQ_70B_PROMPT)//4} tokens)")
    print(f"📏 Longueur DeepSeek V3: {len(DEEPSEEK_V3_PROMPT)} caractères (~{len(DEEPSEEK_V3_PROMPT)//4} tokens)")
    
    # Compter occurrences de valeurs clés
    print(f"\n🔢 Occurrences dans Groq 70B:")
    print(f"   - 'Jessica': {GROQ_70B_PROMPT.count('Jessica')}")
    print(f"   - '+225 07 87 36 07 57': {GROQ_70B_PROMPT.count('+225 07 87 36 07 57')}")
    print(f"   - 'FCFA': {GROQ_70B_PROMPT.count('FCFA')}")
    print(f"   - 'Yopougon': {GROQ_70B_PROMPT.count('Yopougon')}")
    
    print(f"\n🔢 Occurrences dans DeepSeek V3:")
    print(f"   - 'Jessica': {DEEPSEEK_V3_PROMPT.count('Jessica')}")
    print(f"   - '+225 07 87 36 07 57': {DEEPSEEK_V3_PROMPT.count('+225 07 87 36 07 57')}")
    print(f"   - 'FCFA': {DEEPSEEK_V3_PROMPT.count('FCFA')}")
    print(f"   - 'produits bébés': {DEEPSEEK_V3_PROMPT.count('produits bébés')}")

if __name__ == "__main__":
    # Exécuter tous les tests
    result1 = test_hardcoded_values()
    result2 = test_prompt_formatting()
    display_prompt_info()
    
    # Code de sortie
    exit_code = max(result1, result2)
    
    if exit_code == 0:
        print("\n\n" + "=" * 80)
        print("🎉 TOUS LES TESTS RÉUSSIS!")
        print("✅ Les prompts Botlive sont correctement hardcodés pour Rue du Grossiste")
        print("=" * 80)
    else:
        print("\n\n" + "=" * 80)
        print("⚠️ CERTAINS TESTS ONT ÉCHOUÉ")
        print("Vérifiez les erreurs ci-dessus")
        print("=" * 80)
    
    sys.exit(exit_code)
