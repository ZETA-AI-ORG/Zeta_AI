#!/usr/bin/env python3
"""
🧪 TESTS DU NOUVEAU SYSTÈME D'INTENTION RÉVOLUTIONNAIRE
=======================================================
Tests de validation pour la nouvelle logique binaire d'intention

TESTS COUVERTS:
- Détection binaire par index (≥1 doc = intention existe)
- Détection d'actions par stop words significatifs
- Génération de suggestions contextuelles intelligentes
- Intégration avec le cache sémantique
"""

import asyncio
from typing import Dict, List, Any

from core.intention_detector import (
    detect_user_intention, 
    format_intention_for_llm,
    IntentionDetector
)
from core.semantic_intent_cache import (
    create_intent_signature_from_detection,
    create_intent_signature_from_binary_detection
)

class NewIntentionSystemTests:
    """🧪 Suite de tests pour le nouveau système d'intention"""
    
    def __init__(self):
        self.detector = IntentionDetector()
        self.test_results = []
    
    async def run_all_tests(self):
        """🚀 Exécute tous les tests du nouveau système"""
        print("🧪 TESTS DU SYSTÈME D'INTENTION RÉVOLUTIONNAIRE")
        print("=" * 70)
        
        test_methods = [
            self.test_binary_index_detection,
            self.test_action_keywords_detection,
            self.test_multiple_intentions,
            self.test_contextual_suggestions,
            self.test_cache_integration,
            self.test_real_world_scenarios
        ]
        
        for test_method in test_methods:
            print(f"\n🔬 {test_method.__name__.replace('_', ' ').title()}")
            print("-" * 50)
            
            try:
                result = await test_method()
                status = "✅ PASSED" if result.get("success", False) else "❌ FAILED"
                print(f"{status}: {result.get('message', 'Completed')}")
                self.test_results.append({
                    "test": test_method.__name__,
                    "status": "PASSED" if result.get("success", False) else "FAILED",
                    "result": result
                })
            except Exception as e:
                print(f"❌ ERROR: {e}")
                self.test_results.append({
                    "test": test_method.__name__,
                    "status": "ERROR",
                    "error": str(e)
                })
        
        self._print_final_report()
    
    async def test_binary_index_detection(self) -> Dict[str, Any]:
        """Test de la détection binaire par index"""
        # Simuler des résultats par index
        results_by_index = {
            "delivery_company_id": [{"doc": "livraison info"}],  # ≥1 doc → LIVRAISON
            "products_company_id": [{"doc": "produit 1"}, {"doc": "produit 2"}],  # ≥1 doc → PRODUIT
            "support_paiement_company_id": [],  # 0 doc → pas d'intention
            "localisation_company_id": [{"doc": "zone info"}],  # ≥1 doc → LOCALISATION
            "company_docs_company_id": []  # 0 doc → pas d'intention
        }
        
        query = "Test de détection binaire"
        result = detect_user_intention(query, results_by_index)
        
        expected_intentions = ['LIVRAISON', 'PRODUIT', 'LOCALISATION']
        detected_intentions = result['detected_intentions']
        
        success = set(expected_intentions) == set(detected_intentions)
        
        return {
            "success": success,
            "message": f"Intentions détectées: {detected_intentions}",
            "expected": expected_intentions,
            "detected": detected_intentions
        }
    
    async def test_action_keywords_detection(self) -> Dict[str, Any]:
        """Test de la détection d'actions par mots-clés"""
        test_cases = [
            ("Combien ça coûte ?", ["PRIX"]),
            ("Je veux acheter", ["COMMANDE"]),
            ("Comment faire ?", ["SUPPORT"]),
            ("Combien pour commander ?", ["PRIX", "COMMANDE"]),
            ("Info sur les produits", ["INFORMATION"])
        ]
        
        results = []
        for query, expected_actions in test_cases:
            # Index vides pour tester seulement les actions
            empty_results = {f"index_{i}": [] for i in range(5)}
            
            result = detect_user_intention(query, empty_results)
            detected_actions = [intent for intent in result['detected_intentions'] 
                              if intent in ['PRIX', 'COMMANDE', 'SUPPORT', 'INFORMATION']]
            
            match = set(expected_actions) == set(detected_actions)
            results.append(match)
            
            print(f"  Query: '{query}' → Expected: {expected_actions}, Got: {detected_actions}")
        
        success_rate = sum(results) / len(results)
        
        return {
            "success": success_rate >= 0.8,  # 80% de réussite minimum
            "message": f"Taux de réussite: {success_rate:.1%} ({sum(results)}/{len(results)})",
            "success_rate": success_rate
        }
    
    async def test_multiple_intentions(self) -> Dict[str, Any]:
        """Test de la détection d'intentions multiples"""
        # Cas complexe: index + actions multiples
        results_by_index = {
            "delivery_company_id": [{"doc": "livraison"}],  # LIVRAISON
            "products_company_id": [{"doc": "produit"}],    # PRODUIT
            "support_paiement_company_id": [],
            "localisation_company_id": [],
            "company_docs_company_id": []
        }
        
        query = "Combien coûte la livraison du produit que je veux commander ?"
        # Attendu: LIVRAISON (index) + PRODUIT (index) + PRIX (action) + COMMANDE (action)
        
        result = detect_user_intention(query, results_by_index)
        detected = result['detected_intentions']
        
        expected_min = {'LIVRAISON', 'PRODUIT', 'PRIX', 'COMMANDE'}
        detected_set = set(detected)
        
        success = expected_min.issubset(detected_set)
        
        return {
            "success": success,
            "message": f"Intentions multiples détectées: {detected}",
            "expected_minimum": list(expected_min),
            "detected": detected,
            "has_multiple": len(detected) > 1
        }
    
    async def test_contextual_suggestions(self) -> Dict[str, Any]:
        """Test des suggestions contextuelles intelligentes"""
        test_scenarios = [
            {
                "query": "Combien coûte la livraison ?",
                "results": {"delivery_company_id": [{"doc": "info"}]},
                "expected_pattern": "coût de la livraison"
            },
            {
                "query": "Je veux acheter ce produit",
                "results": {"products_company_id": [{"doc": "produit"}]},
                "expected_pattern": "acheter un produit"
            },
            {
                "query": "Combien pour livrer ce produit ?",
                "results": {
                    "delivery_company_id": [{"doc": "livraison"}],
                    "products_company_id": [{"doc": "produit"}]
                },
                "expected_pattern": "coût total"
            }
        ]
        
        results = []
        for scenario in test_scenarios:
            # Ajouter des index vides pour compléter
            full_results = {
                "support_paiement_company_id": [],
                "localisation_company_id": [],
                "company_docs_company_id": [],
                **scenario["results"]
            }
            
            result = detect_user_intention(scenario["query"], full_results)
            suggestion = result['llm_guidance']
            
            # Vérifier si le pattern attendu est dans la suggestion
            pattern_found = scenario["expected_pattern"].lower() in suggestion.lower()
            results.append(pattern_found)
            
            print(f"  Query: '{scenario['query']}'")
            print(f"  Suggestion: {suggestion}")
            print(f"  Pattern '{scenario['expected_pattern']}' found: {pattern_found}")
            print()
        
        success_rate = sum(results) / len(results)
        
        return {
            "success": success_rate >= 0.7,  # 70% de patterns trouvés
            "message": f"Suggestions contextuelles: {success_rate:.1%} de patterns corrects",
            "success_rate": success_rate
        }
    
    async def test_cache_integration(self) -> Dict[str, Any]:
        """Test de l'intégration avec le cache sémantique"""
        # Simuler un résultat d'intention
        results_by_index = {
            "delivery_company_id": [{"doc": "livraison"}],
            "products_company_id": [],
            "support_paiement_company_id": [],
            "localisation_company_id": [],
            "company_docs_company_id": []
        }
        
        query = "Combien coûte la livraison ?"
        intention_result = detect_user_intention(query, results_by_index)
        
        # Test création de signature pour le cache
        try:
            signature1 = create_intent_signature_from_detection(intention_result)
            signature2 = create_intent_signature_from_binary_detection(
                intention_result['detected_intentions'], 
                query, 
                results_by_index
            )
            
            # Vérifier que les signatures sont cohérentes
            same_primary = signature1.primary_intent == signature2.primary_intent
            
            return {
                "success": same_primary,
                "message": f"Signatures créées: {signature1.primary_intent} == {signature2.primary_intent}",
                "signature1": signature1.primary_intent,
                "signature2": signature2.primary_intent
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Erreur création signature: {e}",
                "error": str(e)
            }
    
    async def test_real_world_scenarios(self) -> Dict[str, Any]:
        """Test avec des scénarios réels de RUE_DU_GROS"""
        # Utiliser le vrai company_id de Rue_du_gros
        company_id = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
        
        real_scenarios = [
            {
                "query": "Et la livraison a COCODY CHU fera combien ?",
                "results": {
                    f"delivery_{company_id}": [
                        {"content": "=== LIVRAISON ABIDJAN - ZONES CENTRALES === Zones couvertes: Yopougon, Cocody, Plateau, Adjamé, Abobo, Marcory, Koumassi, Treichville, Angré, Riviera Tarif: 1500 FCFA"},
                        {"content": "=== LIVRAISON ABIDJAN - ZONES PÉRIPHÉRIQUES === Zones: Port-Bouët, Attécoubé, Bingerville, Songon, Anyama, Brofodoumé, Grand-Bassam, Dabou Tarif: 2000 - 2500 FCFA"}
                    ],
                    f"products_{company_id}": [
                        {"content": "Couches à pression ( pour enfant de 0 à 30 kg ) VARIANTES ET PRIX : Taille 1 - 0 à 4 kg - 300 couches | 17.900 F CFA"}
                    ],
                    f"support_paiement_{company_id}": [
                        {"content": "=== PAIEMENT & COMMANDE === Modes de paiement: Wave (+2250787360757) Condition de commande: Un acompte de 2000 FCFA"}
                    ],
                    f"localisation_{company_id}": [],
                    f"company_docs_{company_id}": []
                },
                "expected_intentions": ["LIVRAISON", "PRODUIT", "PAIEMENT", "PRIX"]
            },
            {
                "query": "Je veux des couches culottes 3 paquets",
                "results": {
                    f"products_{company_id}": [
                        {"content": "Couches culottes ( pour enfant de 5 à 30 kg ) VARIANTES ET PRIX : 1 paquet - 5.500 F CFA | 5.500 F/paquet 2 paquets - 9.800 F CFA | 4.900 F/paquet 3 paquets - 13.500 F CFA | 4.500 F/paquet"},
                        {"content": "6 paquets - 25.000 F CFA | 4.150 F/paquet 12 paquets - 48.000 F CFA | 4.000 F/paquet"}
                    ],
                    f"delivery_{company_id}": [],
                    f"support_paiement_{company_id}": [],
                    f"localisation_{company_id}": [],
                    f"company_docs_{company_id}": []
                },
                "expected_intentions": ["PRODUIT", "COMMANDE"]
            },
            {
                "query": "Numéro WhatsApp pour commander ?",
                "results": {
                    f"support_paiement_{company_id}": [
                        {"content": "=== SUPPORT CLIENT === Téléphone/WhatsApp: APPEL DIRECT : +2250787360757 // WHATSAPP : +2250160924560 Horaires: Toujours ouvert"}
                    ],
                    f"products_{company_id}": [],
                    f"delivery_{company_id}": [],
                    f"localisation_{company_id}": [],
                    f"company_docs_{company_id}": []
                },
                "expected_intentions": ["PAIEMENT", "SUPPORT", "COMMANDE"]
            }
        ]
        
        results = []
        for scenario in real_scenarios:
            result = detect_user_intention(scenario["query"], scenario["results"])
            detected = set(result['detected_intentions'])
            expected = set(scenario["expected_intentions"])
            
            # Vérifier que toutes les intentions attendues sont détectées
            match = expected.issubset(detected)
            results.append(match)
            
            print(f"  Scenario: '{scenario['query']}'")
            print(f"  Expected: {scenario['expected_intentions']}")
            print(f"  Detected: {result['detected_intentions']}")
            print(f"  Guidance: {result['llm_guidance']}")
            print(f"  Match: {match}")
            print()
        
        success_rate = sum(results) / len(results)
        
        return {
            "success": success_rate == 1.0,  # 100% pour les scénarios réels
            "message": f"Scénarios réels: {success_rate:.1%} de réussite",
            "success_rate": success_rate
        }
    
    def _print_final_report(self):
        """Affiche le rapport final des tests"""
        print("\n" + "=" * 70)
        print("📊 RAPPORT FINAL - SYSTÈME D'INTENTION RÉVOLUTIONNAIRE")
        print("=" * 70)
        
        passed = sum(1 for result in self.test_results if result["status"] == "PASSED")
        total = len(self.test_results)
        success_rate = (passed / total) * 100 if total > 0 else 0
        
        print(f"✅ Tests réussis: {passed}/{total}")
        print(f"📈 Taux de réussite: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("🎉 SYSTÈME D'INTENTION RÉVOLUTIONNAIRE VALIDÉ !")
            print("✅ Prêt pour l'intégration avec le RAG")
        elif success_rate >= 60:
            print("⚠️ Système partiellement fonctionnel - Optimisations recommandées")
        else:
            print("❌ Problèmes détectés - Corrections nécessaires")
        
        print("\n📋 Détail des résultats:")
        for result in self.test_results:
            status_emoji = "✅" if result["status"] == "PASSED" else "❌" if result["status"] == "FAILED" else "⚠️"
            print(f"  {status_emoji} {result['test']}: {result['status']}")

async def main():
    """🚀 Fonction principale de test"""
    test_suite = NewIntentionSystemTests()
    await test_suite.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
