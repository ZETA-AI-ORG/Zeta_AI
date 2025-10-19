#!/usr/bin/env python3
"""
🎯 TEST ULTIME DE COHÉRENCE RAG
Teste MeiliSearch vs Supabase vs Hybride et détecte les hallucinations
Basé sur la base de données exacte de Rue du Gros
"""

import asyncio
import json
import time
import requests
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

@dataclass
class TestResult:
    """Résultat d'un test de cohérence"""
    question: str
    response: str
    method_used: str
    processing_time: float
    confidence: float
    accuracy_score: float
    hallucination_detected: bool
    errors_found: List[str]
    correct_facts: List[str]

class UltimateCoherenceValidator:
    """Validateur de cohérence ultime basé sur les données exactes"""
    
    def __init__(self):
        self.api_url = "http://127.0.0.1:8001/chat"
        self.company_id = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
        self.user_id = "testuser135"
        
        # BASE DE DONNÉES EXACTE RUE DU GROS
        self.exact_data = {
            "company_info": {
                "name": "Rue_du_gros",
                "ai_name": "gamma",
                "sector": "Bébé & Puériculture",
                "zone": "Côte d'Ivoire"
            },
            "products": {
                "couches_pression": {
                    "age_range": "0 à 30 kg",
                    "sizes": {
                        "taille_1": {"range": "0 à 4 kg", "price": 17900, "quantity": 300},
                        "taille_2": {"range": "3 à 8 kg", "price": 18900, "quantity": 300},
                        "taille_3": {"range": "6 à 11 kg", "price": 22900, "quantity": 300},
                        "taille_4": {"range": "9 à 14 kg", "price": 25900, "quantity": 300},
                        "taille_5": {"range": "12 à 17 kg", "price": 25900, "quantity": 300},
                        "taille_6": {"range": "15 à 25 kg", "price": 27900, "quantity": 300},
                        "taille_7": {"range": "20 à 30 kg", "price": 28900, "quantity": 300}
                    }
                },
                "couches_culottes": {
                    "age_range": "5 à 30 kg",
                    "packages": {
                        "1_paquet": {"price": 5500, "unit_price": 5500},
                        "2_paquets": {"price": 9800, "unit_price": 4900},
                        "3_paquets": {"price": 13500, "unit_price": 4500},
                        "6_paquets": {"price": 25000, "unit_price": 4150},
                        "12_paquets": {"price": 48000, "unit_price": 4000},
                        "1_colis_48": {"price": 168000, "unit_price": 3500}
                    }
                },
                "couches_adultes": {
                    "packages": {
                        "1_paquet_10u": {"price": 5880, "unit_price": 588},
                        "2_paquets_20u": {"price": 11760, "unit_price": 588},
                        "3_paquets_30u": {"price": 16200, "unit_price": 540},
                        "6_paquets_60u": {"price": 36000, "unit_price": 600},
                        "12_paquets_120u": {"price": 114000, "unit_price": 950},
                        "1_colis_240u": {"price": 216000, "unit_price": 900}
                    }
                }
            },
            "delivery": {
                "abidjan_centre": {
                    "zones": ["Yopougon", "Cocody", "Plateau", "Adjamé", "Abobo", "Marcory", "Koumassi", "Treichville", "Angré", "Riviera"],
                    "price": 1500
                },
                "abidjan_peripherie": {
                    "zones": ["Port-Bouët", "Attécoubé", "Bingerville", "Songon", "Anyama", "Brofodoumé", "Grand-Bassam", "Dabou"],
                    "price_range": [2000, 2500]
                },
                "hors_abidjan": {
                    "price_range": [3500, 5000]
                },
                "timing": {
                    "before_11h": "jour même",
                    "after_11h": "lendemain"
                }
            },
            "contact": {
                "phone": "+2250787360757",
                "whatsapp": "+2250160924560",
                "hours": "Toujours ouvert"
            },
            "payment": {
                "method": "Wave",
                "phone": "+2250787360757",
                "acompte": 2000
            },
            "return_policy": {
                "delay": "24H",
                "condition": "Ventes définitives après livraison"
            }
        }
    
    def create_test_scenarios(self) -> List[Dict[str, Any]]:
        """Crée les scénarios de test pour détecter les hallucinations"""
        return [
            # TESTS MEILISEARCH (mots-clés précis)
            {
                "category": "meilisearch_keywords",
                "question": "Quel est le prix exact de la taille 3 couches à pression?",
                "expected_facts": ["22.900 FCFA", "6 à 11 kg", "300 couches"],
                "forbidden_facts": ["23.000", "22.800", "5 à 10 kg", "250 couches"],
                "test_type": "prix_exact"
            },
            {
                "category": "meilisearch_keywords", 
                "question": "Combien coûte la livraison à Yopougon?",
                "expected_facts": ["1500 FCFA", "Yopougon"],
                "forbidden_facts": ["2000", "1000", "2500"],
                "test_type": "livraison_zone"
            },
            {
                "category": "meilisearch_keywords",
                "question": "Quel est le numéro WhatsApp exact?",
                "expected_facts": ["+2250160924560"],
                "forbidden_facts": ["+2250787360757", "autre numéro"],
                "test_type": "contact_exact"
            },
            
            # TESTS SUPABASE (sémantique)
            {
                "category": "supabase_semantic",
                "question": "Je cherche des couches pour un bébé de 10kg, que me conseillez-vous?",
                "expected_facts": ["taille 3", "taille 4", "6 à 11 kg", "9 à 14 kg", "22.900", "25.900"],
                "forbidden_facts": ["taille 1", "taille 2", "taille 5", "prix incorrect"],
                "test_type": "conseil_taille"
            },
            {
                "category": "supabase_semantic",
                "question": "Quelle est votre mission en tant qu'entreprise?",
                "expected_facts": ["faciliter l'accès aux couches", "Côte d'Ivoire", "livraison rapide"],
                "forbidden_facts": ["vendre des vêtements", "autre mission"],
                "test_type": "mission_entreprise"
            },
            {
                "category": "supabase_semantic",
                "question": "Comment puis-je économiser sur l'achat de couches culottes?",
                "expected_facts": ["12 paquets", "48.000 FCFA", "4.000 F/paquet", "1 colis", "168.000 FCFA", "3.500 F/paquet"],
                "forbidden_facts": ["prix incorrect", "quantité incorrecte"],
                "test_type": "optimisation_prix"
            },
            
            # TESTS HYBRIDES (mots-clés + sémantique)
            {
                "category": "hybrid",
                "question": "Je veux 6 paquets de couches culottes livrés à Cocody, quel est le prix total?",
                "expected_facts": ["25.000 FCFA", "6 paquets", "1500 FCFA", "26.500 FCFA total"],
                "forbidden_facts": ["prix incorrect", "livraison incorrecte"],
                "test_type": "calcul_total"
            },
            {
                "category": "hybrid",
                "question": "Quelle taille de couches à pression pour jumeaux de 7kg et 12kg avec livraison Port-Bouët?",
                "expected_facts": ["taille 3", "taille 4", "22.900", "25.900", "2000", "2500"],
                "forbidden_facts": ["taille incorrecte", "prix incorrect"],
                "test_type": "conseil_multiple"
            },
            
            # TESTS PIÈGES (pour détecter hallucinations)
            {
                "category": "hallucination_trap",
                "question": "Avez-vous des couches de couleur rouge en stock?",
                "expected_facts": ["pas de couleur spécifique", "couches standards"],
                "forbidden_facts": ["rouge", "bleu", "vert", "couleurs disponibles"],
                "test_type": "produit_inexistant"
            },
            {
                "category": "hallucination_trap",
                "question": "Quel est votre magasin physique à Abidjan?",
                "expected_facts": ["boutique 100% en ligne", "pas de magasin physique"],
                "forbidden_facts": ["adresse physique", "magasin", "boutique physique"],
                "test_type": "info_incorrecte"
            },
            {
                "category": "hallucination_trap",
                "question": "Acceptez-vous les paiements par carte bancaire?",
                "expected_facts": ["Wave uniquement", "pas de carte bancaire"],
                "forbidden_facts": ["carte bancaire", "Visa", "MasterCard", "autres paiements"],
                "test_type": "paiement_inexistant"
            }
        ]
    
    async def send_question(self, question: str) -> Dict[str, Any]:
        """Envoie une question à l'API et récupère la réponse"""
        try:
            payload = {
                "message": question,
                "company_id": self.company_id,
                "user_id": self.user_id
            }
            
            start_time = time.time()
            response = requests.post(self.api_url, json=payload, timeout=60)
            processing_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "response": data.get("response", ""),
                    "method_used": data.get("search_method", "unknown"),
                    "confidence": data.get("confidence", 0.0),
                    "processing_time": processing_time
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "processing_time": processing_time
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "processing_time": 0
            }
    
    def validate_response(self, response: str, expected_facts: List[str], forbidden_facts: List[str]) -> Tuple[float, bool, List[str], List[str]]:
        """Valide la réponse et détecte les hallucinations"""
        # S'assurer que response est une string
        if isinstance(response, dict):
            response = response.get("response", str(response))
        response_lower = str(response).lower()
        
        # Vérifier les faits attendus
        correct_facts = []
        for fact in expected_facts:
            if fact.lower() in response_lower:
                correct_facts.append(fact)
        
        # Vérifier les hallucinations (faits interdits)
        errors_found = []
        hallucination_detected = False
        
        for forbidden in forbidden_facts:
            if forbidden.lower() in response_lower:
                errors_found.append(f"Hallucination détectée: {forbidden}")
                hallucination_detected = True
        
        # Calcul du score de précision
        if len(expected_facts) > 0:
            accuracy_score = len(correct_facts) / len(expected_facts)
        else:
            accuracy_score = 1.0 if not hallucination_detected else 0.0
        
        # Pénalité pour hallucinations
        if hallucination_detected:
            accuracy_score = max(0.0, accuracy_score - 0.5)
        
        return accuracy_score, hallucination_detected, errors_found, correct_facts
    
    async def run_ultimate_test(self) -> Dict[str, Any]:
        """Lance le test ultime de cohérence"""
        print("🎯 TEST ULTIME DE COHÉRENCE RAG")
        print("=" * 80)
        print("Basé sur la base de données exacte de Rue du Gros")
        print("Détection des hallucinations et validation de la précision")
        print("=" * 80)
        
        scenarios = self.create_test_scenarios()
        results = []
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n🧪 TEST {i}/{len(scenarios)}: {scenario['category'].upper()}")
            print(f"📝 Question: {scenario['question']}")
            print(f"🎯 Type: {scenario['test_type']}")
            print("-" * 60)
            
            # Envoyer la question
            api_result = await self.send_question(scenario['question'])
            
            # Debug API result
            print(f"🔍 Debug API: success={api_result.get('success')}, keys={list(api_result.keys())}")
            
            if api_result['success']:
                response = api_result['response']
                
                # Valider la réponse
                accuracy, hallucination, errors, correct = self.validate_response(
                    response, 
                    scenario['expected_facts'], 
                    scenario['forbidden_facts']
                )
                
                # Créer le résultat
                test_result = TestResult(
                    question=scenario['question'],
                    response=response,
                    method_used=api_result.get('method_used', 'unknown'),
                    processing_time=api_result['processing_time'],
                    confidence=api_result.get('confidence', 0.0),
                    accuracy_score=accuracy,
                    hallucination_detected=hallucination,
                    errors_found=errors,
                    correct_facts=correct
                )
                
                results.append(test_result)
                
                # Affichage du résultat
                status = "❌ ÉCHEC" if hallucination or accuracy < 0.7 else "✅ SUCCÈS"
                print(f"{status} | Précision: {accuracy:.2f} | Méthode: {test_result.method_used}")
                
                # Afficher la réponse (gérer dict/string)
                response_text = response if isinstance(response, str) else str(response)
                print(f"🤖 Réponse: {response_text[:100]}...")
                
                if correct:
                    print(f"✅ Faits corrects: {', '.join(correct[:3])}")
                if errors:
                    print(f"❌ Erreurs: {', '.join(errors[:2])}")
                    
            else:
                print(f"❌ ERREUR API: {api_result.get('error', 'Unknown')}")
        
        # Analyse globale
        return self.analyze_results(results)
    
    def analyze_results(self, results: List[TestResult]) -> Dict[str, Any]:
        """Analyse les résultats et génère le rapport final"""
        print(f"\n" + "=" * 80)
        print("📊 ANALYSE GLOBALE DES RÉSULTATS")
        print("=" * 80)
        
        if not results:
            print("❌ Aucun résultat à analyser")
            return {}
        
        # Statistiques globales
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r.accuracy_score >= 0.7 and not r.hallucination_detected)
        hallucination_count = sum(1 for r in results if r.hallucination_detected)
        avg_accuracy = sum(r.accuracy_score for r in results) / total_tests
        avg_confidence = sum(r.confidence for r in results) / total_tests
        avg_time = sum(r.processing_time for r in results) / total_tests
        
        # Analyse par méthode
        methods_used = {}
        for result in results:
            method = result.method_used
            if method not in methods_used:
                methods_used[method] = {"count": 0, "accuracy": 0, "hallucinations": 0}
            methods_used[method]["count"] += 1
            methods_used[method]["accuracy"] += result.accuracy_score
            methods_used[method]["hallucinations"] += 1 if result.hallucination_detected else 0
        
        # Calcul des moyennes par méthode
        for method in methods_used:
            if methods_used[method]["count"] > 0:
                methods_used[method]["avg_accuracy"] = methods_used[method]["accuracy"] / methods_used[method]["count"]
        
        # Affichage des résultats
        print(f"📊 RÉSULTATS GLOBAUX:")
        print(f"   ✅ Tests réussis: {successful_tests}/{total_tests} ({successful_tests/total_tests*100:.1f}%)")
        print(f"   🎯 Précision moyenne: {avg_accuracy:.3f}")
        print(f"   🤖 Confiance moyenne: {avg_confidence:.3f}")
        print(f"   ⏱️  Temps moyen: {avg_time:.2f}s")
        print(f"   ⚠️  Hallucinations détectées: {hallucination_count}")
        
        print(f"\n📈 PERFORMANCE PAR MÉTHODE:")
        for method, stats in methods_used.items():
            print(f"   🔍 {method.upper()}:")
            print(f"      - Tests: {stats['count']}")
            print(f"      - Précision: {stats['avg_accuracy']:.3f}")
            print(f"      - Hallucinations: {stats['hallucinations']}")
        
        # Tests les plus problématiques
        problematic_tests = [r for r in results if r.hallucination_detected or r.accuracy_score < 0.5]
        if problematic_tests:
            print(f"\n⚠️  TESTS PROBLÉMATIQUES ({len(problematic_tests)}):")
            for test in problematic_tests[:3]:
                print(f"   ❌ {test.question[:50]}...")
                print(f"      Précision: {test.accuracy_score:.2f} | Erreurs: {len(test.errors_found)}")
        
        # Recommandations
        print(f"\n💡 RECOMMANDATIONS:")
        if hallucination_count > 0:
            print(f"   🚨 {hallucination_count} hallucinations détectées - Améliorer la validation des réponses")
        if avg_accuracy < 0.8:
            print(f"   📈 Précision moyenne faible ({avg_accuracy:.2f}) - Optimiser la recherche")
        if avg_time > 5:
            print(f"   ⚡ Temps de réponse élevé ({avg_time:.1f}s) - Optimiser les performances")
        
        return {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "success_rate": successful_tests/total_tests,
            "avg_accuracy": avg_accuracy,
            "avg_confidence": avg_confidence,
            "avg_time": avg_time,
            "hallucination_count": hallucination_count,
            "methods_performance": methods_used,
            "problematic_tests": len(problematic_tests)
        }

async def main():
    """Fonction principale"""
    validator = UltimateCoherenceValidator()
    results = await validator.run_ultimate_test()
    
    print(f"\n🏁 TEST ULTIME TERMINÉ !")
    if results.get("success_rate", 0) > 0.8:
        print("🎉 Système RAG validé avec succès !")
    else:
        print("⚠️ Améliorations nécessaires détectées.")

if __name__ == "__main__":
    asyncio.run(main())
