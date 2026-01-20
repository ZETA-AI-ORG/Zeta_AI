#!/usr/bin/env python3
"""
🎯 TEST ENDPOINT COMPLET - APRÈS INGESTION HYDE
Test complet de l'endpoint /chat après création du cache HyDE
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

# Configuration
ENDPOINT_URL = "http://127.0.0.1:8001/chat"
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"  # RueduGrossiste

def log_test(message, data=None):
    """Log formaté pour les tests"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[TEST_ENDPOINT][{timestamp}] {message}")
    if data:
        print(f"  📊 {json.dumps(data, indent=2, ensure_ascii=False)}")

class EndpointTester:
    """
    Testeur complet de l'endpoint /chat avec cache HyDE
    """
    
    def __init__(self):
        self.test_results = []
        
    async def test_single_query(self, session, query, test_name, expected_elements=None):
        """
        Teste une requête unique sur l'endpoint
        """
        print(f"\n{'='*60}")
        print(f"📝 TEST: {test_name}")
        print(f"🔍 Requête: '{query}'")
        
        if expected_elements:
            print(f"🎯 Éléments attendus: {expected_elements}")
        
        payload = {
            "message": query,
            "company_id": COMPANY_ID,
            "user_id": "testuser123"
        }
        
        try:
            start_time = time.time()
            
            async with session.post(ENDPOINT_URL, json=payload) as response:
                end_time = time.time()
                duration = (end_time - start_time) * 1000
                
                if response.status == 200:
                    result = await response.json()
                    
                    # Analyser la réponse
                    response_text = result.get('response', '')
                    debug_info = result.get('debug_info', {})
                    
                    # Vérifier les éléments attendus
                    elements_found = []
                    if expected_elements:
                        for element in expected_elements:
                            if element.lower() in response_text.lower():
                                elements_found.append(element)
                    
                    # Analyser les performances
                    performance_score = self._calculate_performance_score(
                        duration, len(response_text), elements_found, expected_elements
                    )
                    
                    test_result = {
                        "test_name": test_name,
                        "query": query,
                        "status": "SUCCESS",
                        "duration_ms": round(duration, 1),
                        "response_length": len(response_text),
                        "elements_found": elements_found,
                        "elements_expected": expected_elements or [],
                        "performance_score": performance_score,
                        "response_preview": response_text[:200] + "..." if len(response_text) > 200 else response_text
                    }
                    
                    print(f"✅ SUCCÈS ({duration:.1f}ms)")
                    print(f"📄 Réponse: {len(response_text)} caractères")
                    print(f"🎯 Éléments trouvés: {elements_found}")
                    print(f"⭐ Score performance: {performance_score}/100")
                    print(f"💬 Aperçu: {response_text[:150]}...")
                    
                    # Afficher les infos de debug si disponibles
                    if debug_info:
                        hyde_info = debug_info.get('hyde_scoring', {})
                        if hyde_info:
                            print(f"🧠 HyDE - Intention: {hyde_info.get('intention', 'N/A')}")
                            print(f"🧠 HyDE - Efficacité: {hyde_info.get('efficacite', 'N/A')}")
                    
                    self.test_results.append(test_result)
                    return test_result
                    
                else:
                    error_text = await response.text()
                    print(f"❌ ERREUR HTTP {response.status}")
                    print(f"💥 Détails: {error_text[:200]}")
                    
                    test_result = {
                        "test_name": test_name,
                        "query": query,
                        "status": "ERROR",
                        "error": f"HTTP {response.status}: {error_text[:100]}"
                    }
                    
                    self.test_results.append(test_result)
                    return test_result
                    
        except Exception as e:
            print(f"💥 EXCEPTION: {str(e)}")
            
            test_result = {
                "test_name": test_name,
                "query": query,
                "status": "EXCEPTION",
                "error": str(e)
            }
            
            self.test_results.append(test_result)
            return test_result

    def _calculate_performance_score(self, duration_ms, response_length, elements_found, expected_elements):
        """
        Calcule un score de performance sur 100
        """
        score = 100
        
        # Pénalité durée (optimal < 5s, acceptable < 10s, lent > 15s)
        if duration_ms > 15000:
            score -= 30
        elif duration_ms > 10000:
            score -= 15
        elif duration_ms > 5000:
            score -= 5
        
        # Pénalité longueur réponse (trop courte < 50, trop longue > 1000)
        if response_length < 50:
            score -= 20
        elif response_length > 1000:
            score -= 10
        
        # Bonus éléments trouvés
        if expected_elements:
            found_ratio = len(elements_found) / len(expected_elements)
            score += int(found_ratio * 20)  # Bonus jusqu'à 20 points
        
        return max(0, min(100, score))

    async def run_complete_test_suite(self):
        """
        Lance la suite complète de tests
        """
        print("🚀 DÉMARRAGE TESTS ENDPOINT COMPLET")
        print(f"🎯 URL: {ENDPOINT_URL}")
        print(f"🏢 Company ID: {COMPANY_ID}")
        
        # Définir les tests
        test_cases = [
            {
                "name": "Prix Samsung Galaxy",
                "query": "combien coûte le samsung galaxy s24 ultra",
                "expected": ["samsung", "galaxy", "s24", "prix", "450000", "650000", "fcfa"]
            },
            {
                "name": "Stock iPhone disponible",
                "query": "iphone 15 pro max disponible en stock",
                "expected": ["iphone", "15", "pro", "max", "stock", "disponible"]
            },
            {
                "name": "Livraison Cocody",
                "query": "livraison possible à cocody combien ça coûte",
                "expected": ["livraison", "cocody", "gratuite", "2000", "fcfa"]
            },
            {
                "name": "Paiement Wave Money",
                "query": "je peux payer avec wave money",
                "expected": ["wave", "money", "paiement", "mobile", "accepté"]
            },
            {
                "name": "Contact WhatsApp",
                "query": "contact whatsapp pour commander",
                "expected": ["whatsapp", "contact", "+225", "commander"]
            },
            {
                "name": "Casque JBL rouge",
                "query": "casque jbl rouge bluetooth prix",
                "expected": ["casque", "jbl", "rouge", "bluetooth", "35000", "45000"]
            },
            {
                "name": "Moto Yamaha financement",
                "query": "yamaha mt 125 financement possible",
                "expected": ["yamaha", "mt", "125", "financement", "1200000"]
            },
            {
                "name": "Support technique",
                "query": "problème avec mon téléphone support technique",
                "expected": ["support", "technique", "assistance", "réparation"]
            },
            {
                "name": "Requête complexe multi-intentions",
                "query": "samsung s24 prix livraison yopougon paiement wave contact whatsapp",
                "expected": ["samsung", "s24", "prix", "yopougon", "wave", "whatsapp"]
            },
            {
                "name": "Requête conversationnelle",
                "query": "salut je cherche un bon smartphone pas trop cher pour mon fils",
                "expected": ["smartphone", "prix", "recommandation"]
            }
        ]
        
        async with aiohttp.ClientSession() as session:
            success_count = 0
            total_duration = 0
            
            for i, test_case in enumerate(test_cases, 1):
                result = await self.test_single_query(
                    session,
                    test_case["query"],
                    f"{i}. {test_case['name']}",
                    test_case["expected"]
                )
                
                if result["status"] == "SUCCESS":
                    success_count += 1
                    total_duration += result["duration_ms"]
                
                # Pause entre les tests
                await asyncio.sleep(1)
            
            # Statistiques finales
            self._display_final_statistics(success_count, len(test_cases), total_duration)

    def _display_final_statistics(self, success_count, total_tests, total_duration):
        """
        Affiche les statistiques finales
        """
        print(f"\n{'='*60}")
        print("🎉 RÉSULTATS FINAUX")
        print(f"{'='*60}")
        
        success_rate = (success_count / total_tests) * 100
        avg_duration = total_duration / success_count if success_count > 0 else 0
        
        print(f"✅ Tests réussis: {success_count}/{total_tests} ({success_rate:.1f}%)")
        print(f"⏱️ Durée moyenne: {avg_duration:.1f}ms")
        print(f"📊 Durée totale: {total_duration:.1f}ms")
        
        # Analyse par performance
        successful_tests = [t for t in self.test_results if t["status"] == "SUCCESS"]
        if successful_tests:
            avg_score = sum(t["performance_score"] for t in successful_tests) / len(successful_tests)
            best_test = max(successful_tests, key=lambda x: x["performance_score"])
            worst_test = min(successful_tests, key=lambda x: x["performance_score"])
            
            print(f"⭐ Score moyen: {avg_score:.1f}/100")
            print(f"🏆 Meilleur test: {best_test['test_name']} ({best_test['performance_score']}/100)")
            print(f"⚠️ Test à améliorer: {worst_test['test_name']} ({worst_test['performance_score']}/100)")
        
        # Recommandations
        if success_rate >= 90:
            print("\n🎯 EXCELLENT! Système prêt pour la production")
        elif success_rate >= 70:
            print("\n👍 BON! Quelques optimisations recommandées")
        else:
            print("\n⚠️ ATTENTION! Corrections nécessaires avant production")
        
        # Détail des échecs
        failed_tests = [t for t in self.test_results if t["status"] != "SUCCESS"]
        if failed_tests:
            print(f"\n❌ TESTS ÉCHOUÉS:")
            for test in failed_tests:
                print(f"  - {test['test_name']}: {test.get('error', 'Erreur inconnue')}")

async def main():
    """
    Fonction principale
    """
    print("🎯 TEST ENDPOINT COMPLET - SYSTÈME HYDE")
    print("=" * 60)
    
    tester = EndpointTester()
    await tester.run_complete_test_suite()

if __name__ == "__main__":
    asyncio.run(main())
