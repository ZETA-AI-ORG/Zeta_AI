#!/usr/bin/env python3
"""
🧪 TEST UNITAIRE - ThinkingParser
Test rapide de validation du parser YAML
"""

from core.thinking_parser import get_thinking_parser

# Exemple de réponse LLM avec <thinking> complet
SAMPLE_LLM_RESPONSE = """
<thinking>
PHASE 1: EXTRACTION
question_exacte: "Combien coûte le lot de 300 couches taille 4 livraison Angré?"
intentions:
  - demande_prix: 90%
  - demande_livraison: 80%
mots_cles: [prix, lot, 300, couche, taille 4, livraison, Angré]
sources_utilisees:
  context: true
  history: true
  contexte_collecte: false

PHASE 2: COLLECTE
deja_collecte:
  type_produit: "Couches à pression taille 4"
  quantite: "300"
  zone: "Angré"
  telephone: null
  paiement: null
nouvelles_donnees:
  - cle: type_produit
    valeur: "Couches à pression taille 4"
    source: question
    confiance: HAUTE
  - cle: quantite
    valeur: "300"
    source: question
    confiance: HAUTE
  - cle: zone
    valeur: "Angré"
    source: question
    confiance: HAUTE
actions:
  - action: "notepad('write', 'type_produit: Couches à pression taille 4')"
    statut: execute
    resultat: success

PHASE 3: VALIDATION
verification:
  prix_produits_livraison:
    source_obligatoire: context
    trouve: true
    ligne_exacte: "VARIANTE: Taille 4 - 9 à 14 kg - 300 couches | 24.000 F CFA"
    valeur: 24000
  ambiguite:
    detectee: false
    raison: null
confiance_globale:
  score: 95%
  raison: "Toutes les informations principales sont disponibles"

PHASE 4: ANTI-RÉPÉTITION
check_repetition:
  type_produit: true
  quantite: true
  zone: true
  telephone: false
  paiement: false
regle: "Info true → NE PAS redemander"

PHASE 5: DÉCISION
progression:
  completude: 3/5
  prochaine_etape:
    type: calcul
    action: "Calculer prix total avec livraison"
strategie_qualification:
  phase: interet
  objectif: creer_urgence
  technique: livraison_rapide
</thinking>

<response>
📦 Le lot de 300 couches à pression taille 4 coûte 24 000 FCFA.
🚚 Livraison à Angré: 1 500 FCFA.
Total: 25 500 FCFA 💰
</response>
"""


def test_extraction_thinking_block():
    """Test 1: Extraction du bloc <thinking>"""
    print("\n" + "="*80)
    print("🧪 TEST 1: Extraction bloc <thinking>")
    print("="*80)
    
    parser = get_thinking_parser()
    thinking = parser.extract_thinking_block(SAMPLE_LLM_RESPONSE)
    
    assert thinking is not None, "❌ Bloc thinking non extrait"
    assert "PHASE 1" in thinking, "❌ PHASE 1 manquante"
    assert "PHASE 5" in thinking, "❌ PHASE 5 manquante"
    
    print(f"✅ Bloc extrait: {len(thinking)} caractères")
    print(f"✅ Contient toutes les phases")


def test_deja_collecte():
    """Test 2: Extraction deja_collecte"""
    print("\n" + "="*80)
    print("🧪 TEST 2: Extraction deja_collecte")
    print("="*80)
    
    parser = get_thinking_parser()
    thinking = parser.extract_thinking_block(SAMPLE_LLM_RESPONSE)
    deja_collecte = parser.extract_deja_collecte(thinking)
    
    print(f"📦 deja_collecte: {deja_collecte}")
    
    assert deja_collecte["type_produit"] == "Couches à pression taille 4", "❌ type_produit incorrect"
    assert deja_collecte["quantite"] == "300", "❌ quantite incorrecte"
    assert deja_collecte["zone"] == "Angré", "❌ zone incorrecte"
    assert deja_collecte["telephone"] is None, "❌ telephone devrait être None"
    assert deja_collecte["paiement"] is None, "❌ paiement devrait être None"
    
    print("✅ Tous les champs deja_collecte corrects")


def test_nouvelles_donnees():
    """Test 3: Extraction nouvelles_donnees"""
    print("\n" + "="*80)
    print("🧪 TEST 3: Extraction nouvelles_donnees")
    print("="*80)
    
    parser = get_thinking_parser()
    thinking = parser.extract_thinking_block(SAMPLE_LLM_RESPONSE)
    nouvelles_donnees = parser.extract_nouvelles_donnees(thinking)
    
    print(f"📋 nouvelles_donnees: {len(nouvelles_donnees)} items")
    for item in nouvelles_donnees:
        print(f"  - {item['cle']}: {item['valeur']} (confiance: {item['confiance']})")
    
    assert len(nouvelles_donnees) == 3, f"❌ Attendu 3 items, reçu {len(nouvelles_donnees)}"
    assert nouvelles_donnees[0]["cle"] == "type_produit", "❌ Première clé incorrecte"
    assert nouvelles_donnees[0]["confiance"] == "HAUTE", "❌ Confiance incorrecte"
    
    print("✅ nouvelles_donnees correctement extraites")


def test_confiance_globale():
    """Test 4: Extraction confiance_globale"""
    print("\n" + "="*80)
    print("🧪 TEST 4: Extraction confiance_globale")
    print("="*80)
    
    parser = get_thinking_parser()
    thinking = parser.extract_thinking_block(SAMPLE_LLM_RESPONSE)
    score, raison = parser.extract_confiance_globale(thinking)
    
    print(f"🎯 Confiance: {score}%")
    print(f"📝 Raison: {raison}")
    
    assert score == 95, f"❌ Score attendu 95%, reçu {score}%"
    assert "informations principales" in raison.lower(), "❌ Raison incorrecte"
    
    print("✅ confiance_globale correctement extraite")


def test_completude():
    """Test 5: Extraction completude"""
    print("\n" + "="*80)
    print("🧪 TEST 5: Extraction completude")
    print("="*80)
    
    parser = get_thinking_parser()
    thinking = parser.extract_thinking_block(SAMPLE_LLM_RESPONSE)
    completude = parser.extract_completude(thinking)
    
    print(f"📊 Complétude: {completude}")
    
    assert completude == "3/5", f"❌ Complétude attendue '3/5', reçu '{completude}'"
    
    print("✅ completude correctement extraite")


def test_prochaine_etape():
    """Test 6: Extraction prochaine_etape"""
    print("\n" + "="*80)
    print("🧪 TEST 6: Extraction prochaine_etape")
    print("="*80)
    
    parser = get_thinking_parser()
    thinking = parser.extract_thinking_block(SAMPLE_LLM_RESPONSE)
    prochaine_etape = parser.extract_prochaine_etape(thinking)
    
    print(f"🎯 Prochaine étape:")
    print(f"  - Type: {prochaine_etape['type']}")
    print(f"  - Action: {prochaine_etape['action']}")
    
    assert prochaine_etape["type"] == "calcul", f"❌ Type attendu 'calcul', reçu '{prochaine_etape['type']}'"
    assert "prix total" in prochaine_etape["action"].lower(), "❌ Action incorrecte"
    
    print("✅ prochaine_etape correctement extraite")


def test_strategie_qualification():
    """Test 7: Extraction strategie_qualification"""
    print("\n" + "="*80)
    print("🧪 TEST 7: Extraction strategie_qualification")
    print("="*80)
    
    parser = get_thinking_parser()
    thinking = parser.extract_thinking_block(SAMPLE_LLM_RESPONSE)
    strategie = parser.extract_strategie_qualification(thinking)
    
    print(f"🎭 Stratégie:")
    print(f"  - Phase: {strategie['phase']}")
    print(f"  - Objectif: {strategie['objectif']}")
    print(f"  - Technique: {strategie['technique']}")
    
    assert strategie["phase"] == "interet", f"❌ Phase attendue 'interet', reçu '{strategie['phase']}'"
    assert strategie["objectif"] == "creer_urgence", "❌ Objectif incorrect"
    
    print("✅ strategie_qualification correctement extraite")


def test_parse_full():
    """Test 8: Parse complet"""
    print("\n" + "="*80)
    print("🧪 TEST 8: Parse complet")
    print("="*80)
    
    parser = get_thinking_parser()
    result = parser.parse_full_thinking(SAMPLE_LLM_RESPONSE)
    
    print(f"📦 Résultat parse complet:")
    print(f"  - Success: {result['success']}")
    print(f"  - Confiance: {result['confiance']['score']}%")
    print(f"  - Complétude: {result['progression']['completude']}")
    print(f"  - Nouvelles données: {len(result['nouvelles_donnees'])} items")
    print(f"  - Erreurs parsing: {len(result['parsing_errors'])}")
    
    assert result["success"] is True, "❌ Parse devrait réussir"
    assert result["confiance"]["score"] == 95, "❌ Score confiance incorrect"
    assert result["progression"]["completude"] == "3/5", "❌ Complétude incorrecte"
    assert len(result["nouvelles_donnees"]) == 3, "❌ Nombre nouvelles_donnees incorrect"
    
    print("✅ Parse complet réussi")


def test_fallback_missing_thinking():
    """Test 9: Fallback si <thinking> absent"""
    print("\n" + "="*80)
    print("🧪 TEST 9: Fallback sans <thinking>")
    print("="*80)
    
    parser = get_thinking_parser()
    response_sans_thinking = "<response>Juste une réponse sans thinking</response>"
    
    result = parser.parse_full_thinking(response_sans_thinking)
    
    print(f"📦 Résultat fallback:")
    print(f"  - Success: {result['success']}")
    print(f"  - Confiance: {result['confiance']['score']}%")
    print(f"  - Complétude: {result['progression']['completude']}")
    
    assert result["success"] is False, "❌ Success devrait être False"
    assert result["confiance"]["score"] == 50, "❌ Score fallback devrait être 50%"
    assert result["progression"]["completude"] == "0/5", "❌ Complétude fallback incorrecte"
    
    print("✅ Fallback fonctionne correctement")


def run_all_tests():
    """Lance tous les tests"""
    print("\n" + "="*80)
    print("🚀 LANCEMENT DES TESTS - ThinkingParser")
    print("="*80)
    
    tests = [
        test_extraction_thinking_block,
        test_deja_collecte,
        test_nouvelles_donnees,
        test_confiance_globale,
        test_completude,
        test_prochaine_etape,
        test_strategie_qualification,
        test_parse_full,
        test_fallback_missing_thinking
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ ÉCHEC: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ ERREUR: {e}")
            failed += 1
    
    print("\n" + "="*80)
    print("📊 RÉSULTATS")
    print("="*80)
    print(f"✅ Tests réussis: {passed}/{len(tests)}")
    print(f"❌ Tests échoués: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 TOUS LES TESTS SONT PASSÉS !")
    else:
        print(f"\n⚠️ {failed} test(s) ont échoué")
    
    print("="*80)


if __name__ == "__main__":
    run_all_tests()
