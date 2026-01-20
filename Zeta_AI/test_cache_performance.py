#!/usr/bin/env python3
"""
🚀 TEST DE PERFORMANCE DES CACHES OPTIMISÉS
Objectif: Valider les gains de performance attendus (19.6s → 7.3s)
Architecture: Tests automatisés avec métriques détaillées
"""

import asyncio
import time
import json
import statistics
from typing import Dict, List, Any
import httpx
from datetime import datetime

class CachePerformanceTester:
    """
    🎯 Testeur de performance pour les caches optimisés
    - Mesure les temps de réponse avant/après cache
    - Valide les hit rates
    - Génère des rapports détaillés
    """
    
    def __init__(self, base_url: str = "http://127.0.0.1:8001"):
        self.base_url = base_url
        self.results = {
            "test_start": datetime.now().isoformat(),
            "cache_tests": [],
            "performance_tests": [],
            "summary": {}
        }
    
    async def test_cache_endpoints(self) -> Dict[str, Any]:
        """🔍 Test des endpoints de monitoring des caches"""
        print("🔍 Test des endpoints de monitoring des caches...")
        
        endpoints = [
            ("/api/cache/stats", "Statistiques globales"),
            ("/api/cache/health", "Santé des caches"),
            ("/api/cache/performance", "Analyse de performance")
        ]
        
        cache_results = {}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for endpoint, description in endpoints:
                try:
                    start_time = time.time()
                    response = await client.get(f"{self.base_url}{endpoint}")
                    response_time = (time.time() - start_time) * 1000
                    
                    if response.status_code == 200:
                        data = response.json()
                        cache_results[endpoint] = {
                            "status": "success",
                            "response_time_ms": response_time,
                            "data": data
                        }
                        print(f"✅ {description}: {response_time:.1f}ms")
                    else:
                        cache_results[endpoint] = {
                            "status": "error",
                            "status_code": response.status_code,
                            "response_time_ms": response_time
                        }
                        print(f"❌ {description}: HTTP {response.status_code}")
                        
                except Exception as e:
                    cache_results[endpoint] = {
                        "status": "exception",
                        "error": str(e)
                    }
                    print(f"❌ {description}: Exception {e}")
        
        self.results["cache_tests"] = cache_results
        return cache_results
    
    async def test_chat_performance(self, company_id: str, test_queries: List[str]) -> Dict[str, Any]:
        """⚡ Test de performance du chat avec caches"""
        print(f"⚡ Test de performance chat (company: {company_id})...")
        
        performance_results = {
            "company_id": company_id,
            "queries_tested": len(test_queries),
            "individual_results": [],
            "cold_start_times": [],
            "warm_cache_times": [],
            "improvement_ratios": []
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            for i, query in enumerate(test_queries):
                print(f"  📝 Test {i+1}/{len(test_queries)}: {query[:50]}...")
                
                query_results = {
                    "query": query,
                    "attempts": []
                }
                
                # Faire 3 tentatives pour mesurer l'amélioration du cache
                for attempt in range(3):
                    try:
                        payload = {
                            "company_id": company_id,
                            "user_id": company_id,
                            "message": query,
                            "message_id": f"test_{i}_{attempt}_{int(time.time())}"
                        }
                        
                        start_time = time.time()
                        response = await client.post(
                            f"{self.base_url}/chat",
                            json=payload,
                            headers={"Content-Type": "application/json"}
                        )
                        response_time = (time.time() - start_time) * 1000
                        
                        attempt_result = {
                            "attempt": attempt + 1,
                            "response_time_ms": response_time,
                            "status_code": response.status_code,
                            "success": response.status_code == 200
                        }
                        
                        if response.status_code == 200:
                            data = response.json()
                            attempt_result["response_length"] = len(data.get("response", ""))
                            print(f"    ✅ Tentative {attempt+1}: {response_time:.0f}ms")
                        else:
                            print(f"    ❌ Tentative {attempt+1}: HTTP {response.status_code}")
                        
                        query_results["attempts"].append(attempt_result)
                        
                        # Attendre un peu entre les tentatives
                        if attempt < 2:
                            await asyncio.sleep(1)
                            
                    except Exception as e:
                        print(f"    ❌ Tentative {attempt+1}: Exception {e}")
                        query_results["attempts"].append({
                            "attempt": attempt + 1,
                            "error": str(e),
                            "success": False
                        })
                
                # Analyser les résultats de cette query
                successful_attempts = [a for a in query_results["attempts"] if a.get("success", False)]
                if len(successful_attempts) >= 2:
                    times = [a["response_time_ms"] for a in successful_attempts]
                    query_results["cold_start_ms"] = times[0]
                    query_results["warm_cache_ms"] = min(times[1:])
                    query_results["improvement_ratio"] = times[0] / min(times[1:])
                    
                    performance_results["cold_start_times"].append(times[0])
                    performance_results["warm_cache_times"].append(min(times[1:]))
                    performance_results["improvement_ratios"].append(query_results["improvement_ratio"])
                
                performance_results["individual_results"].append(query_results)
        
        # Calculer les statistiques globales
        if performance_results["cold_start_times"] and performance_results["warm_cache_times"]:
            performance_results["statistics"] = {
                "avg_cold_start_ms": statistics.mean(performance_results["cold_start_times"]),
                "avg_warm_cache_ms": statistics.mean(performance_results["warm_cache_times"]),
                "avg_improvement_ratio": statistics.mean(performance_results["improvement_ratios"]),
                "max_improvement_ratio": max(performance_results["improvement_ratios"]),
                "time_saved_per_request_ms": statistics.mean(performance_results["cold_start_times"]) - statistics.mean(performance_results["warm_cache_times"])
            }
        
        self.results["performance_tests"].append(performance_results)
        return performance_results
    
    async def test_cache_preload(self, company_id: str) -> Dict[str, Any]:
        """🚀 Test du préchargement des caches"""
        print(f"🚀 Test du préchargement pour {company_id}...")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                start_time = time.time()
                response = await client.post(
                    f"{self.base_url}/api/cache/preload/{company_id}",
                    params={"common_queries": ["prix produit", "livraison", "contact"]}
                )
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Préchargement réussi: {response_time:.1f}ms")
                    return {
                        "status": "success",
                        "response_time_ms": response_time,
                        "results": data
                    }
                else:
                    print(f"❌ Préchargement échoué: HTTP {response.status_code}")
                    return {
                        "status": "error",
                        "status_code": response.status_code,
                        "response_time_ms": response_time
                    }
                    
        except Exception as e:
            print(f"❌ Préchargement exception: {e}")
            return {
                "status": "exception",
                "error": str(e)
            }
    
    def generate_summary(self) -> Dict[str, Any]:
        """📊 Génère un résumé des résultats"""
        summary = {
            "test_completion": datetime.now().isoformat(),
            "cache_endpoints_working": 0,
            "performance_improvement": {},
            "recommendations": []
        }
        
        # Analyser les endpoints de cache
        if "cache_tests" in self.results:
            working_endpoints = sum(1 for result in self.results["cache_tests"].values() 
                                  if result.get("status") == "success")
            summary["cache_endpoints_working"] = working_endpoints
            summary["total_cache_endpoints"] = len(self.results["cache_tests"])
        
        # Analyser les performances
        if self.results["performance_tests"]:
            all_improvements = []
            all_time_saved = []
            
            for test in self.results["performance_tests"]:
                if "statistics" in test:
                    stats = test["statistics"]
                    all_improvements.append(stats["avg_improvement_ratio"])
                    all_time_saved.append(stats["time_saved_per_request_ms"])
            
            if all_improvements:
                summary["performance_improvement"] = {
                    "average_improvement_ratio": statistics.mean(all_improvements),
                    "average_time_saved_ms": statistics.mean(all_time_saved),
                    "total_queries_tested": sum(len(test["individual_results"]) for test in self.results["performance_tests"])
                }
        
        # Générer des recommandations
        if summary.get("cache_endpoints_working", 0) < summary.get("total_cache_endpoints", 1):
            summary["recommendations"].append("Vérifier la configuration des endpoints de cache")
        
        if summary.get("performance_improvement", {}).get("average_improvement_ratio", 1) < 1.5:
            summary["recommendations"].append("Performance d'amélioration faible - vérifier les caches")
        elif summary.get("performance_improvement", {}).get("average_improvement_ratio", 1) > 3:
            summary["recommendations"].append("Excellente performance des caches - système optimisé")
        
        if not summary["recommendations"]:
            summary["recommendations"].append("Système fonctionnel - surveillance continue recommandée")
        
        self.results["summary"] = summary
        return summary
    
    def save_results(self, filename: str = None) -> str:
        """💾 Sauvegarde les résultats"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"cache_performance_test_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"💾 Résultats sauvegardés: {filename}")
        return filename

async def main():
    """🎯 Fonction principale de test"""
    print("🚀 TEST DE PERFORMANCE DES CACHES OPTIMISÉS")
    print("=" * 60)
    
    # Configuration du test
    company_id = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"  # Rue du Gros
    test_queries = [
        "juste savoir combien coute vos couches pour bebe de 6kg",
        "juste savoir combien coute vos couches pour bebe de 9kg",
        "livraison à Yopougon combien ça coûte",
        "contact WhatsApp pour support",
        "informations sur l'entreprise"
    ]
    
    tester = CachePerformanceTester()
    
    try:
        # 1. Tester les endpoints de monitoring
        print("\n1️⃣ TEST DES ENDPOINTS DE MONITORING")
        await tester.test_cache_endpoints()
        
        # 2. Tester le préchargement
        print("\n2️⃣ TEST DU PRÉCHARGEMENT")
        await tester.test_cache_preload(company_id)
        
        # 3. Tester les performances du chat
        print("\n3️⃣ TEST DE PERFORMANCE DU CHAT")
        await tester.test_chat_performance(company_id, test_queries)
        
        # 4. Générer le résumé
        print("\n4️⃣ GÉNÉRATION DU RÉSUMÉ")
        summary = tester.generate_summary()
        
        # 5. Afficher les résultats
        print("\n" + "=" * 60)
        print("📊 RÉSULTATS FINAUX")
        print("=" * 60)
        
        print(f"✅ Endpoints de cache fonctionnels: {summary['cache_endpoints_working']}/{summary.get('total_cache_endpoints', 0)}")
        
        if "performance_improvement" in summary:
            perf = summary["performance_improvement"]
            print(f"⚡ Ratio d'amélioration moyen: {perf['average_improvement_ratio']:.2f}x")
            print(f"⏱️ Temps économisé par requête: {perf['average_time_saved_ms']:.0f}ms")
            print(f"📝 Queries testées: {perf['total_queries_tested']}")
        
        print("\n🎯 RECOMMANDATIONS:")
        for rec in summary["recommendations"]:
            print(f"  - {rec}")
        
        # 6. Sauvegarder les résultats
        print("\n5️⃣ SAUVEGARDE DES RÉSULTATS")
        filename = tester.save_results()
        
        print(f"\n🎉 TEST TERMINÉ - Résultats dans {filename}")
        
    except Exception as e:
        print(f"\n❌ ERREUR DURANT LE TEST: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
