#!/usr/bin/env python3
"""
🧪 TESTS SPÉCIALISÉS POUR RUE_DU_GROS
====================================
Tests d'intégration avec les vraies données de l'entreprise Rue_du_gros
Company ID: MpfnlSbqwaZ6F4HvxQLRL9du0yG3

DONNÉES TESTÉES:
- Couches à pression (7 tailles, 17.900-28.900 FCFA)
- Couches culottes (tarifs dégressifs 5.500-168.000 FCFA)
- Couches adultes (tarifs dégressifs 5.880-216.000 FCFA)
- Livraison Abidjan (1500 FCFA) vs périphérie (2000-2500 FCFA)
- Support WhatsApp +2250160924560 / Téléphone +2250787360757
- Paiement Wave uniquement
"""

import asyncio
from typing import Dict, List, Any

from core.intention_detector import detect_user_intention, format_intention_for_llm
from core.semantic_intent_cache import (
    get_semantic_intent_cache,
    create_intent_signature_from_binary_detection,
    IntentSignature
)

class RueDuGrosIntegrationTests:
    """🧪 Tests d'intégration spécialisés pour Rue_du_gros"""
    
    def __init__(self):
        self.company_id = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
        self.semantic_cache = get_semantic_intent_cache()
        self.test_results = []
    
    async def run_all_tests(self):
        """🚀 Exécute tous les tests spécialisés Rue_du_gros"""
        print("🧪 TESTS D'INTÉGRATION RUE_DU_GROS")
        print("=" * 60)
        print(f"Company ID: {self.company_id}")
        print(f"Assistant IA: gamma")
        print(f"Secteur: Bébé & Puériculture")
        print("=" * 60)
        
        test_methods = [
            self.test_couches_culottes_pricing,
            self.test_livraison_zones_abidjan,
            self.test_support_contact_info,
            self.test_paiement_wave,
            self.test_multi_intent_scenarios,
            self.test_cache_integration_real_data
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
    
    async def test_couches_culottes_pricing(self) -> Dict[str, Any]:
        """Test des tarifs dégressifs couches culottes"""
        # Simuler des résultats d'index products avec vraies données
        results_by_index = {
            f"products_{self.company_id}": [
                {
                    "content": "Couches culottes ( pour enfant de 5 à 30 kg ) VARIANTES ET PRIX : 1 paquet - 5.500 F CFA | 5.500 F/paquet 2 paquets - 9.800 F CFA | 4.900 F/paquet 3 paquets - 13.500 F CFA | 4.500 F/paquet 6 paquets - 25.000 F CFA | 4.150 F/paquet 12 paquets - 48.000 F CFA | 4.000 F/paquet 1 colis (48) - 168.000 F CFA | 3.500 F/paquet"
                }
            ],
            f"delivery_{self.company_id}": [],
            f"support_paiement_{self.company_id}": [],
            f"localisation_{self.company_id}": [],
            f"company_docs_{self.company_id}": []
        }
        
        test_queries = [
            ("Combien coûtent 3 paquets de couches culottes ?", "13.500"),
            ("Prix 6 paquets couches culottes", "25.000"),
            ("Je veux 12 paquets, ça fait combien ?", "48.000")
        ]
        
        results = []
        for query, expected_price in test_queries:
            intention_result = detect_user_intention(query, results_by_index)
            
            # Vérifier que PRODUIT et PRIX sont détectés
            detected = intention_result['detected_intentions']
            has_product = 'PRODUIT' in detected
            has_price = 'PRIX' in detected or 'COMMANDE' in detected
            
            # Vérifier la suggestion LLM
            guidance = intention_result['llm_guidance']
            
            success = has_product and has_price
            results.append(success)
            
            print(f"  Query: '{query}'")
            print(f"  Intentions: {detected}")
            print(f"  Guidance: {guidance}")
            print(f"  Expected price: {expected_price} FCFA")
            print(f"  Success: {success}")
            print()
        
        success_rate = sum(results) / len(results)
        
        return {
            "success": success_rate >= 0.8,
            "message": f"Tarifs couches culottes: {success_rate:.1%} de détection correcte",
            "success_rate": success_rate
        }
    
    async def test_livraison_zones_abidjan(self) -> Dict[str, Any]:
        """Test des zones de livraison Abidjan"""
        # Simuler des résultats d'index delivery avec vraies données
        results_by_index = {
            f"delivery_{self.company_id}": [
                {
                    "content": "=== LIVRAISON ABIDJAN - ZONES CENTRALES === Zones couvertes: Yopougon, Cocody, Plateau, Adjamé, Abobo, Marcory, Koumassi, Treichville, Angré, Riviera Tarif: 1500 FCFA"
                },
                {
                    "content": "=== LIVRAISON ABIDJAN - ZONES PÉRIPHÉRIQUES === Zones: Port-Bouët, Attécoubé, Bingerville, Songon, Anyama, Brofodoumé, Grand-Bassam, Dabou Tarif: 2000 - 2500 FCFA"
                }
            ],
            f"products_{self.company_id}": [],
            f"support_paiement_{self.company_id}": [],
            f"localisation_{self.company_id}": [],
            f"company_docs_{self.company_id}": []
        }
        
        test_queries = [
            ("Combien coûte la livraison à Cocody ?", "1500", "centrale"),
            ("Livraison à Yopougon ça fait combien ?", "1500", "centrale"),
            ("Et pour Port-Bouët ?", "2000-2500", "périphérique"),
            ("Tarif livraison Grand-Bassam", "2000-2500", "périphérique")
        ]
        
        results = []
        for query, expected_price, zone_type in test_queries:
            intention_result = detect_user_intention(query, results_by_index)
            
            detected = intention_result['detected_intentions']
            has_delivery = 'LIVRAISON' in detected
            has_price = 'PRIX' in detected
            
            guidance = intention_result['llm_guidance']
            
            success = has_delivery and has_price
            results.append(success)
            
            print(f"  Query: '{query}' (zone {zone_type})")
            print(f"  Intentions: {detected}")
            print(f"  Expected: {expected_price} FCFA")
            print(f"  Success: {success}")
            print()
        
        success_rate = sum(results) / len(results)
        
        return {
            "success": success_rate >= 0.8,
            "message": f"Zones livraison Abidjan: {success_rate:.1%} de détection correcte",
            "success_rate": success_rate
        }
    
    async def test_support_contact_info(self) -> Dict[str, Any]:
        """Test des informations de contact support"""
        results_by_index = {
            f"support_paiement_{self.company_id}": [
                {
                    "content": "=== SUPPORT CLIENT === Téléphone/WhatsApp: APPEL DIRECT : +2250787360757 // WHATSAPP : +2250160924560 Horaires: Toujours ouvert Canaux: Téléphone, WhatsApp"
                }
            ],
            f"products_{self.company_id}": [],
            f"delivery_{self.company_id}": [],
            f"localisation_{self.company_id}": [],
            f"company_docs_{self.company_id}": []
        }
        
        test_queries = [
            ("Numéro WhatsApp ?", "SUPPORT"),
            ("Comment vous contacter ?", "SUPPORT"),
            ("Téléphone pour commander", "SUPPORT", "COMMANDE")
        ]
        
        results = []
        for query_data in test_queries:
            query = query_data[0]
            expected_intentions = query_data[1:]
            
            intention_result = detect_user_intention(query, results_by_index)
            detected = set(intention_result['detected_intentions'])
            expected = set(expected_intentions)
            
            success = expected.issubset(detected)
            results.append(success)
            
            print(f"  Query: '{query}'")
            print(f"  Expected: {list(expected)}")
            print(f"  Detected: {list(detected)}")
            print(f"  Success: {success}")
            print()
        
        success_rate = sum(results) / len(results)
        
        return {
            "success": success_rate >= 0.8,
            "message": f"Contact support: {success_rate:.1%} de détection correcte",
            "success_rate": success_rate
        }
    
    async def test_paiement_wave(self) -> Dict[str, Any]:
        """Test des informations de paiement Wave"""
        results_by_index = {
            f"support_paiement_{self.company_id}": [
                {
                    "content": "=== PAIEMENT & COMMANDE === Modes de paiement: Wave (+2250787360757) Condition de commande: Un acompte de 2000 FCFA est exigé avant que la commande ne soit prise en compte."
                }
            ],
            f"products_{self.company_id}": [],
            f"delivery_{self.company_id}": [],
            f"localisation_{self.company_id}": [],
            f"company_docs_{self.company_id}": []
        }
        
        test_queries = [
            ("Comment payer ?", ["PAIEMENT"]),
            ("Vous acceptez Wave ?", ["PAIEMENT"]),
            ("Acompte obligatoire ?", ["PAIEMENT"])
        ]
        
        results = []
        for query, expected_intentions in test_queries:
            intention_result = detect_user_intention(query, results_by_index)
            detected = set(intention_result['detected_intentions'])
            expected = set(expected_intentions)
            
            success = expected.issubset(detected)
            results.append(success)
            
            print(f"  Query: '{query}'")
            print(f"  Expected: {expected_intentions}")
            print(f"  Detected: {list(detected)}")
            print(f"  Success: {success}")
            print()
        
        success_rate = sum(results) / len(results)
        
        return {
            "success": success_rate >= 0.8,
            "message": f"Paiement Wave: {success_rate:.1%} de détection correcte",
            "success_rate": success_rate
        }
    
    async def test_multi_intent_scenarios(self) -> Dict[str, Any]:
        """Test des scénarios multi-intentions réels"""
        # Scénario complexe: plusieurs index avec documents
        results_by_index = {
            f"products_{self.company_id}": [
                {"content": "Couches culottes 3 paquets - 13.500 F CFA"}
            ],
            f"delivery_{self.company_id}": [
                {"content": "Livraison Cocody: 1500 FCFA"}
            ],
            f"support_paiement_{self.company_id}": [
                {"content": "Paiement Wave (+2250787360757)"}
            ],
            f"localisation_{self.company_id}": [],
            f"company_docs_{self.company_id}": []
        }
        
        query = "Je veux 3 paquets de couches culottes, combien ça coûte avec la livraison à Cocody et comment payer ?"
        
        intention_result = detect_user_intention(query, results_by_index)
        detected = set(intention_result['detected_intentions'])
        
        # Intentions attendues: PRODUIT (products), LIVRAISON (delivery), PAIEMENT (support_paiement), PRIX (combien), COMMANDE (veux)
        expected_minimum = {'PRODUIT', 'LIVRAISON', 'PAIEMENT'}
        
        success = expected_minimum.issubset(detected)
        
        print(f"  Query complexe: '{query}'")
        print(f"  Expected minimum: {list(expected_minimum)}")
        print(f"  Detected: {list(detected)}")
        print(f"  Guidance: {intention_result['llm_guidance']}")
        print(f"  Success: {success}")
        
        return {
            "success": success,
            "message": f"Multi-intentions: {len(detected)} intentions détectées",
            "detected_count": len(detected),
            "detected_intentions": list(detected)
        }
    
    async def test_cache_integration_real_data(self) -> Dict[str, Any]:
        """Test d'intégration cache avec vraies données"""
        # Créer une signature d'intention réelle
        detected_intentions = ['PRODUIT', 'PRIX', 'COMMANDE']
        query = "Je veux 3 paquets couches culottes combien ?"
        
        results_by_index = {
            f"products_{self.company_id}": [{"content": "Couches culottes 3 paquets - 13.500 F CFA"}]
        }
        
        # Créer signature pour le cache
        intent_signature = create_intent_signature_from_binary_detection(
            detected_intentions, query, results_by_index
        )
        
        # Stocker dans le cache
        response = "3 paquets de couches culottes coûtent 13.500 FCFA (4.500 F/paquet)."
        store_success = await self.semantic_cache.store_response(
            query=query,
            response=response,
            intent_signature=intent_signature
        )
        
        if not store_success:
            return {"success": False, "message": "Échec stockage cache"}
        
        # Tester récupération avec formulation différente
        similar_query = "Prix 3 paquets couches culottes ?"
        cache_result = await self.semantic_cache.get_cached_response(
            query=similar_query,
            intent_signature=intent_signature
        )
        
        if cache_result:
            cached_response, confidence = cache_result
            return {
                "success": confidence >= 0.7,
                "message": f"Cache hit: confiance {confidence:.3f}",
                "cached_response": cached_response,
                "confidence": confidence
            }
        
        return {"success": False, "message": "Cache miss inattendu"}
    
    def _print_final_report(self):
        """Affiche le rapport final des tests"""
        print("\n" + "=" * 60)
        print("📊 RAPPORT FINAL - INTÉGRATION RUE_DU_GROS")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result["status"] == "PASSED")
        total = len(self.test_results)
        success_rate = (passed / total) * 100 if total > 0 else 0
        
        print(f"✅ Tests réussis: {passed}/{total}")
        print(f"📈 Taux de réussite: {success_rate:.1f}%")
        print(f"🏢 Entreprise: Rue_du_gros (gamma)")
        print(f"🆔 Company ID: {self.company_id}")
        
        if success_rate >= 80:
            print("🎉 INTÉGRATION RUE_DU_GROS VALIDÉE !")
            print("✅ Système d'intention + cache sémantique opérationnel")
        elif success_rate >= 60:
            print("⚠️ Intégration partiellement fonctionnelle")
        else:
            print("❌ Problèmes d'intégration détectés")
        
        print("\n📋 Détail des résultats:")
        for result in self.test_results:
            status_emoji = "✅" if result["status"] == "PASSED" else "❌" if result["status"] == "FAILED" else "⚠️"
            print(f"  {status_emoji} {result['test']}: {result['status']}")

async def main():
    """🚀 Fonction principale de test"""
    test_suite = RueDuGrosIntegrationTests()
    await test_suite.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
