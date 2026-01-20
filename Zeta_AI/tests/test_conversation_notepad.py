#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 TESTS UNITAIRES - SYSTÈME NOTEPAD CONVERSATIONNEL
Vérifie que la mémoire conversationnelle fonctionne correctement
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.conversation_notepad import (
    get_conversation_notepad,
    reset_conversation_notepad,
    extract_product_info,
    extract_delivery_zone,
    extract_phone_number,
    extract_price_from_response
)


def test_quantity_persistence():
    """Test que les quantités sont bien mémorisées"""
    print("\n🧪 TEST 1: Persistance des quantités")
    
    reset_conversation_notepad()
    notepad = get_conversation_notepad()
    
    # Ajouter 2 lots
    notepad.update_product("test_user", "test_company", 
                          "Couches taille 4", 2, 24000, "Taille 4")
    
    # Vérifier
    np = notepad.get_notepad("test_user", "test_company")
    assert len(np["products"]) == 1, "❌ Produit non ajouté"
    assert np["products"][0]["quantity"] == 2, "❌ Quantité incorrecte"
    assert np["products"][0]["price"] == 24000, "❌ Prix incorrect"
    
    # Calculer total
    calc = notepad.calculate_total("test_user", "test_company")
    assert calc["products_total"] == 48000, f"❌ Total incorrect: {calc['products_total']}"
    
    print("✅ Test 1 réussi: Quantité 2 lots mémorisée, total 48 000 FCFA")


def test_delivery_zone_memory():
    """Test que la zone de livraison est mémorisée"""
    print("\n🧪 TEST 2: Mémoire zone de livraison")
    
    reset_conversation_notepad()
    notepad = get_conversation_notepad()
    
    notepad.update_delivery("test_user2", "test_company", "Cocody", 1500)
    
    np = notepad.get_notepad("test_user2", "test_company")
    assert np["delivery_zone"] == "Cocody", "❌ Zone non enregistrée"
    assert np["delivery_cost"] == 1500, "❌ Coût incorrect"
    
    print("✅ Test 2 réussi: Zone Cocody + 1500 FCFA mémorisés")


def test_total_calculation_with_delivery():
    """Test calcul total produits + livraison"""
    print("\n🧪 TEST 3: Calcul total avec livraison")
    
    reset_conversation_notepad()
    notepad = get_conversation_notepad()
    
    # 2 lots taille 4
    notepad.update_product("test_user3", "test_company", 
                          "Couches taille 4", 2, 24000, "Taille 4")
    
    # Livraison Cocody
    notepad.update_delivery("test_user3", "test_company", "Cocody", 1500)
    
    # Calculer
    calc = notepad.calculate_total("test_user3", "test_company")
    
    expected_total = (2 * 24000) + 1500  # 49 500 FCFA
    assert calc["grand_total"] == expected_total, \
        f"❌ Total incorrect: {calc['grand_total']} au lieu de {expected_total}"
    
    print(f"✅ Test 3 réussi: Total correct = {expected_total:,} FCFA")


def test_summary_generation():
    """Test génération du résumé"""
    print("\n🧪 TEST 4: Génération résumé")
    
    reset_conversation_notepad()
    notepad = get_conversation_notepad()
    
    # Commande complète
    notepad.update_product("test_user4", "test_company", 
                          "Couches taille 3", 1, 22900, "Taille 3")
    notepad.update_delivery("test_user4", "test_company", "Yopougon", 1500)
    notepad.update_phone("test_user4", "test_company", "0787360757")
    
    summary = notepad.get_summary("test_user4", "test_company")
    
    # Vérifications
    assert "Couches taille 3" in summary, "❌ Produit absent du résumé"
    assert "Yopougon" in summary, "❌ Zone absente du résumé"
    assert "1 500" in summary or "1500" in summary, "❌ Frais livraison absents"
    assert "24 400" in summary or "24400" in summary, "❌ Total absent"
    assert "0787360757" in summary, "❌ Téléphone absent"
    
    print("✅ Test 4 réussi: Résumé complet généré")
    print(f"📋 Résumé:\n{summary}")


def test_extraction_product_info():
    """Test extraction automatique infos produit"""
    print("\n🧪 TEST 5: Extraction automatique produit")
    
    test_cases = [
        ("Je veux 2 lots de 300 couches taille 4", 2, "Couches à pression", "Taille 4"),
        ("3 paquets couches culottes", 3, "Couches culottes", None),
        ("1 lot taille 5", 1, "Couches à pression", "Taille 5"),
    ]
    
    for query, expected_qty, expected_type, expected_variant in test_cases:
        result = extract_product_info(query)
        
        assert result is not None, f"❌ Extraction échouée pour: {query}"
        assert result["quantity"] == expected_qty, \
            f"❌ Quantité incorrecte: {result['quantity']} au lieu de {expected_qty}"
        assert result["product_type"] == expected_type, \
            f"❌ Type incorrect: {result['product_type']}"
        
        if expected_variant:
            assert result["variant"] == expected_variant, \
                f"❌ Variante incorrecte: {result['variant']}"
        
        print(f"✅ Extraction OK: '{query}' → {expected_qty}x {expected_type}")


def test_extraction_delivery_zone():
    """Test extraction zone de livraison"""
    print("\n🧪 TEST 6: Extraction zone livraison")
    
    test_cases = [
        ("Livraison à Cocody", "Cocody"),
        ("Je suis à Yopougon", "Yopougon"),
        ("Port-Bouët", "Port Bouet"),
        ("Angré", "Angré"),
    ]
    
    for query, expected_zone in test_cases:
        result = extract_delivery_zone(query)
        
        assert result is not None, f"❌ Zone non détectée: {query}"
        assert result.lower() == expected_zone.lower(), \
            f"❌ Zone incorrecte: {result} au lieu de {expected_zone}"
        
        print(f"✅ Zone détectée: '{query}' → {result}")


def test_extraction_price():
    """Test extraction prix de la réponse LLM"""
    print("\n🧪 TEST 7: Extraction prix")
    
    test_cases = [
        ("Le prix est de 24 000 FCFA", 24000),
        ("Cela coûte 22900 F CFA", 22900),
        ("Prix: 1 500 FCFA", 1500),
        ("Total: 49500 F", 49500),
    ]
    
    for response, expected_price in test_cases:
        result = extract_price_from_response(response)
        
        assert result is not None, f"❌ Prix non extrait: {response}"
        assert result == expected_price, \
            f"❌ Prix incorrect: {result} au lieu de {expected_price}"
        
        print(f"✅ Prix extrait: '{response}' → {result} FCFA")


def test_context_for_llm():
    """Test génération contexte pour LLM"""
    print("\n🧪 TEST 8: Contexte pour LLM")
    
    reset_conversation_notepad()
    notepad = get_conversation_notepad()
    
    # Commande en cours
    notepad.update_product("test_user5", "test_company", 
                          "Couches taille 4", 2, 24000, "Taille 4")
    notepad.update_delivery("test_user5", "test_company", "Cocody", 1500)
    
    context = notepad.get_context_for_llm("test_user5", "test_company")
    
    # Vérifications
    assert "[INFORMATIONS COMMANDE EN COURS]" in context, "❌ Header manquant"
    assert "2x Couches taille 4" in context, "❌ Produit absent"
    assert "Cocody" in context, "❌ Zone absente"
    assert "1 500" in context or "1500" in context, "❌ Frais absents"
    
    print("✅ Test 8 réussi: Contexte LLM généré")
    print(f"📄 Contexte:\n{context}")


def test_update_existing_product():
    """Test mise à jour produit existant"""
    print("\n🧪 TEST 9: Mise à jour produit existant")
    
    reset_conversation_notepad()
    notepad = get_conversation_notepad()
    
    # Ajouter 1 lot
    notepad.update_product("test_user6", "test_company", 
                          "Couches taille 4", 1, 24000, "Taille 4")
    
    # Modifier à 3 lots
    notepad.update_product("test_user6", "test_company", 
                          "Couches taille 4", 3, 24000, "Taille 4")
    
    np = notepad.get_notepad("test_user6", "test_company")
    
    # Doit avoir 1 seul produit avec quantité 3
    assert len(np["products"]) == 1, "❌ Produit dupliqué"
    assert np["products"][0]["quantity"] == 3, "❌ Quantité non mise à jour"
    
    calc = notepad.calculate_total("test_user6", "test_company")
    assert calc["products_total"] == 72000, "❌ Total incorrect après mise à jour"
    
    print("✅ Test 9 réussi: Produit mis à jour (1→3 lots)")


def run_all_tests():
    """Exécute tous les tests"""
    print("="*80)
    print("🧪 TESTS SYSTÈME NOTEPAD CONVERSATIONNEL")
    print("="*80)
    
    tests = [
        test_quantity_persistence,
        test_delivery_zone_memory,
        test_total_calculation_with_delivery,
        test_summary_generation,
        test_extraction_product_info,
        test_extraction_delivery_zone,
        test_extraction_price,
        test_context_for_llm,
        test_update_existing_product
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ ÉCHEC: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ ERREUR: {e}")
            failed += 1
    
    print("\n" + "="*80)
    print(f"📊 RÉSULTATS: {passed}/{len(tests)} tests réussis")
    if failed == 0:
        print("🎉 TOUS LES TESTS SONT PASSÉS!")
    else:
        print(f"⚠️  {failed} test(s) échoué(s)")
    print("="*80)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
