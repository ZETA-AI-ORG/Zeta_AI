#!/usr/bin/env python3
"""
🧪 TEST DE VALIDATION ANTI-HALLUCINATION
Teste tous les cas de figure du système de validation
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.llm_response_validator import LLMResponseValidator
from core.order_state_tracker import OrderState
from dataclasses import dataclass
from typing import Optional

# ═══════════════════════════════════════════════════════════════════════════════
# 🎯 CONFIGURATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TestCase:
    """Cas de test"""
    name: str
    response: str
    thinking: str
    order_state: OrderState
    payment_validation: Optional[dict]
    context_documents: list
    expected_valid: bool
    expected_errors: list
    description: str

# ═══════════════════════════════════════════════════════════════════════════════
# 📋 CAS DE TEST
# ═══════════════════════════════════════════════════════════════════════════════

TEST_CASES = [
    # ═══ TEST 1: CONTRADICTION PAIEMENT ═══
    TestCase(
        name="PAIEMENT_VALIDE_MAIS_LLM_REDEMANDE",
        response="Il te reste 1798 FCFA à envoyer pour compléter ton dépôt.",
        thinking="""
PHASE 2 COLLECTE
deja_collecte:
  paiement: validé_2020F
""",
        order_state=OrderState(
            user_id="test_user",
            paiement="validé_2020F",
            produit="Couches taille 3",
            zone=None,
            numero=None
        ),
        payment_validation={'valid': True, 'total_received': 2020},
        context_documents=[],
        expected_valid=False,
        expected_errors=["Contradiction paiement"],
        description="LLM redemande paiement alors que validé dans order_state"
    ),
    
    # ═══ TEST 2: NUMÉRO INCORRECT ═══
    TestCase(
        name="NUMERO_ENTREPRISE_AU_LIEU_CLIENT",
        response="Super ! Commande confirmée. Contact: 0787360757",
        thinking="",
        order_state=OrderState(
            user_id="test_user",
            numero="0701234567",
            produit="Couches taille 3",
            paiement="validé_2020F",
            zone="Anyama"
        ),
        payment_validation=None,
        context_documents=[],
        expected_valid=False,
        expected_errors=["Numéro incorrect"],
        description="LLM utilise numéro entreprise au lieu du client"
    ),
    
    # ═══ TEST 3: HALLUCINATION PRIX ═══
    TestCase(
        name="PRIX_ZERO_FCFA",
        response="Pour les 2 lots de couches à pression taille None, le prix total est de 0 FCFA.",
        thinking="",
        order_state=OrderState(
            user_id="test_user",
            produit=None,
            paiement=None,
            zone=None,
            numero=None
        ),
        payment_validation=None,
        context_documents=[],
        expected_valid=False,
        expected_errors=["Hallucination prix"],
        description="Prix invalide (0 FCFA) et taille None"
    ),
    
    # ═══ TEST 4: SOURCE INVENTÉE ═══
    TestCase(
        name="SOURCE_INVENTEE",
        response="Oui, nous avons une garantie de 30 jours.",
        thinking="""
PHASE 3 CITATION
sources_consultees:
  - document_id: "politique_garantie"
    contenu: "garantie de 30 jours"
    pertinence: HAUTE
reponse_basee_sur:
  - source: "politique_garantie"
    citation: "garantie de 30 jours"
sources_trouvees: true
""",
        order_state=OrderState(user_id="test_user"),
        payment_validation=None,
        context_documents=["POLITIQUE DE RETOUR: retour sous 24H"],  # Pas de mention de 30 jours
        expected_valid=False,
        expected_errors=["Source inventée"],
        description="Citation introuvable dans le contexte fourni"
    ),
    
    # ═══ TEST 5: RÉPONSE VALIDE ═══
    TestCase(
        name="REPONSE_VALIDE_COMPLETE",
        response="Super ! Paiement validé ✅. Tu es dans quelle zone pour la livraison ?",
        thinking="""
PHASE 2 COLLECTE
deja_collecte:
  paiement: validé_2020F
  produit: "Couches taille 3"
  
PHASE 3 CITATION
sources_trouvees: true
peut_repondre: true

PHASE 6 DECISION
completude: "2/4"
prochaine_etape: "Demander zone livraison"
confiance_globale: 90
""",
        order_state=OrderState(
            user_id="test_user",
            paiement="validé_2020F",
            produit="Couches taille 3",
            zone=None,
            numero=None
        ),
        payment_validation={'valid': True, 'total_received': 2020},
        context_documents=[],
        expected_valid=True,
        expected_errors=[],
        description="Réponse cohérente avec order_state, pas d'hallucination"
    ),
    
    # ═══ TEST 6: CONTRADICTION OCR ═══
    TestCase(
        name="OCR_VALIDE_MAIS_LLM_DIT_INSUFFISANT",
        response="Paiement insuffisant, il manque encore 1798 FCFA.",
        thinking="",
        order_state=OrderState(
            user_id="test_user",
            paiement=None,
            produit="Couches taille 3"
        ),
        payment_validation={'valid': True, 'total_received': 2020, 'message': 'Validé'},
        context_documents=[],
        expected_valid=False,
        expected_errors=["Contradiction OCR"],
        description="OCR valide le paiement mais LLM dit insuffisant"
    ),
    
    # ═══ TEST 7: SOURCES TROUVÉES MAIS RÉPOND QUAND MÊME ═══
    TestCase(
        name="SOURCES_FALSE_MAIS_REPOND",
        response="Oui, nous avons une garantie complète.",
        thinking="""
PHASE 3 CITATION
sources_trouvees: false
peut_repondre: true
raison_si_non: "Aucune info sur garantie"
""",
        order_state=OrderState(user_id="test_user"),
        payment_validation=None,
        context_documents=["POLITIQUE DE RETOUR: retour sous 24H"],
        expected_valid=False,
        expected_errors=["source"],  # Accepter toute erreur de source
        description="LLM répond alors que sources_trouvees=false"
    ),
    
    # ═══ TEST 8: NUMÉRO CLIENT CORRECT ═══
    TestCase(
        name="NUMERO_CLIENT_CORRECT",
        response="Parfait ! Commande confirmée pour le 0701234567.",
        thinking="",
        order_state=OrderState(
            user_id="test_user",
            numero="0701234567",
            produit="Couches taille 3",
            paiement="validé_2020F",
            zone="Anyama"
        ),
        payment_validation=None,
        context_documents=[],
        expected_valid=True,
        expected_errors=[],
        description="Numéro client utilisé correctement"
    ),
    
    # ═══ TEST 9: PAIEMENT PARTIEL CORRECT ═══
    TestCase(
        name="PAIEMENT_PARTIEL_CORRECT",
        response="Tu as envoyé 202 FCFA. Il manque encore 1798 FCFA pour compléter.",
        thinking="",
        order_state=OrderState(
            user_id="test_user",
            paiement=None,  # Pas encore validé
            produit="Couches taille 3"
        ),
        payment_validation={'valid': False, 'total_received': 202, 'message': 'Insuffisant'},
        context_documents=[],
        expected_valid=True,
        expected_errors=[],
        description="LLM demande complément car paiement non validé"
    ),
    
    # ═══ TEST 10: CITATION CORRECTE ═══
    TestCase(
        name="CITATION_CORRECTE",
        response="Oui ! On a une politique de retour sous 24H.",
        thinking="""
PHASE 3 CITATION
sources_consultees:
  - document_id: "politique_retour"
    contenu: "retour sous 24H, sous réserve d'une raison valable"
    pertinence: HAUTE
reponse_basee_sur:
  - source: "politique_retour"
    citation: "retour sous 24H"
sources_trouvees: true
peut_repondre: true
""",
        order_state=OrderState(user_id="test_user"),
        payment_validation=None,
        context_documents=["POLITIQUE DE RETOUR: retour sous 24H, sous réserve d'une raison valable"],
        expected_valid=True,
        expected_errors=[],
        description="Citation trouvée dans le contexte"
    ),
]

# ═══════════════════════════════════════════════════════════════════════════════
# 🧪 EXÉCUTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def run_tests():
    """Exécute tous les tests de validation"""
    validator = LLMResponseValidator()
    
    print("="*100)
    print("🧪 TEST DE VALIDATION ANTI-HALLUCINATION")
    print("="*100)
    print()
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(TEST_CASES, 1):
        print(f"\n{'─'*100}")
        print(f"TEST {i}/{len(TEST_CASES)}: {test.name}")
        print(f"{'─'*100}")
        print(f"📝 Description: {test.description}")
        print(f"\n💬 Réponse LLM:")
        print(f"   {test.response[:100]}...")
        
        # Exécuter validation
        result = validator.validate(
            response=test.response,
            thinking=test.thinking,
            order_state=test.order_state,
            payment_validation=test.payment_validation,
            context_documents=test.context_documents
        )
        
        # Vérifier résultat
        test_passed = True
        
        # Check 1: Valid/Invalid
        if result.valid != test.expected_valid:
            test_passed = False
            print(f"\n❌ ÉCHEC: Attendu valid={test.expected_valid}, obtenu valid={result.valid}")
        
        # Check 2: Erreurs attendues
        if test.expected_errors:
            for expected_error in test.expected_errors:
                # Recherche flexible: accepter si substring présent
                found = any(expected_error.lower() in error.lower() for error in result.errors)
                if not found:
                    test_passed = False
                    print(f"\n❌ ÉCHEC: Erreur attendue '{expected_error}' non trouvée")
                    print(f"   Erreurs obtenues: {result.errors}")
        
        # Check 3: Pas d'erreurs si attendu valide
        if test.expected_valid and result.errors:
            test_passed = False
            print(f"\n❌ ÉCHEC: Attendu aucune erreur, obtenu: {result.errors}")
        
        # Afficher résultat
        if test_passed:
            passed += 1
            print(f"\n✅ SUCCÈS")
            if result.errors:
                print(f"   Erreurs détectées (attendu): {result.errors}")
            if result.warnings:
                print(f"   Warnings: {result.warnings}")
        else:
            failed += 1
            print(f"\n❌ ÉCHEC")
            print(f"   Erreurs: {result.errors}")
            print(f"   Warnings: {result.warnings}")
    
    # ═══ RÉSUMÉ FINAL ═══
    print("\n" + "="*100)
    print("📊 RÉSUMÉ DES TESTS")
    print("="*100)
    print(f"\n✅ Réussis: {passed}/{len(TEST_CASES)} ({passed*100//len(TEST_CASES)}%)")
    print(f"❌ Échoués: {failed}/{len(TEST_CASES)} ({failed*100//len(TEST_CASES)}%)")
    
    # Métriques validateur
    print(f"\n📈 MÉTRIQUES VALIDATEUR:")
    print(f"   - Total validations: {validator.validation_count}")
    print(f"   - Hallucinations détectées: {validator.hallucination_count}")
    print(f"   - Erreurs de sources: {validator.source_errors_count}")
    print(f"   - Régénérations requises: {validator.regeneration_count}")
    
    print("\n" + "="*100)
    
    if failed == 0:
        print("🎉 TOUS LES TESTS SONT PASSÉS !")
        print("="*100)
        return 0
    else:
        print(f"⚠️ {failed} TEST(S) ÉCHOUÉ(S)")
        print("="*100)
        return 1

# ═══════════════════════════════════════════════════════════════════════════════
# 🚀 MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
