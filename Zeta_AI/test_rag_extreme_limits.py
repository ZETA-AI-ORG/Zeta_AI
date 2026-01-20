#!/usr/bin/env python3
"""
🔥 TEST ULTIME RAG - POUSSER DANS SES LIMITES ABSOLUES
Test de stress, edge cases, et scénarios extrêmes pour le système hybride
"""

import asyncio
import requests
import json
import time
import random
import string
from datetime import datetime
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor
import threading

# Configuration
API_URL = "http://127.0.0.1:8001/chat"
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
USER_ID = "testuser135"

class RAGExtremeLimitsTest:
    """Test ultime pour pousser le RAG dans ses limites absolues"""
    
    def __init__(self):
        self.extreme_test_cases = [
            # 🔥 CATÉGORIE 1: QUERIES EXTRÊMEMENT LONGUES
            {
                "category": "ultra_long_query",
                "level": "extreme",
                "question": "bonjour monsieur gamma je suis une maman de trois enfants et j'aimerais vraiment beaucoup savoir si vous avez des couches pour mes bébés qui pèsent respectivement 8 kilos 12 kilos et 18 kilos et aussi combien ça va me coûter exactement pour la livraison si j'habite à port-bouët dans le quartier résidentiel près de la pharmacie du coin et est-ce que je peux payer avec wave comme d'habitude ou bien il y a d'autres moyens de paiement disponibles et aussi j'aimerais savoir si vous faites des promotions ou des réductions pour les familles nombreuses comme la mienne et quelle est votre politique de retour au cas où les couches ne conviendraient pas à mes enfants merci beaucoup pour votre attention",
                "expected_elements": ["8", "12", "18", "kilos", "port-bouët", "wave", "retour"],
                "description": "Query ultra-longue avec multiples informations"
            },
            
            # 🔥 CATÉGORIE 2: QUERIES AVEC CARACTÈRES SPÉCIAUX
            {
                "category": "special_characters",
                "level": "extreme",
                "question": "Prix??? couches!!! @#$%^&*() taille 3??? URGENT!!! 💰💰💰",
                "expected_elements": ["prix", "couches", "taille", "3"],
                "description": "Query avec caractères spéciaux et emojis"
            },
            
            # 🔥 CATÉGORIE 3: QUERIES RÉPÉTITIVES
            {
                "category": "repetitive",
                "level": "extreme", 
                "question": "prix prix prix prix prix couches couches couches taille taille taille 3 3 3 combien combien combien",
                "expected_elements": ["prix", "couches", "taille", "3"],
                "description": "Query avec répétitions massives"
            },
            
            # 🔥 CATÉGORIE 4: QUERIES MULTILINGUES
            {
                "category": "multilingual",
                "level": "extreme",
                "question": "hello bonjour price prix couches diapers taille size 3 three combien how much cost coût",
                "expected_elements": ["prix", "couches", "taille", "3"],
                "description": "Query mélange français-anglais"
            },
            
            # 🔥 CATÉGORIE 5: QUERIES AVEC FAUTES MASSIVES
            {
                "category": "typos_extreme",
                "level": "extreme",
                "question": "combyen coute lé couchz pour bebé tayl 3 livrezon yopougon wav paymen",
                "expected_elements": ["prix", "couches", "taille", "3", "livraison", "yopougon", "wave"],
                "description": "Query avec fautes d'orthographe extrêmes"
            },
            
            # 🔥 CATÉGORIE 6: QUERIES CONTRADICTOIRES
            {
                "category": "contradictory",
                "level": "extreme",
                "question": "je veux pas acheter mais combien coûte les couches gratuits payants taille 3 et 4 et 5 mais pas 3 livraison rapide lente",
                "expected_elements": ["prix", "couches", "taille"],
                "description": "Query avec contradictions internes"
            },
            
            # 🔥 CATÉGORIE 7: QUERIES AVEC NOMBRES EXTRÊMES
            {
                "category": "extreme_numbers",
                "level": "extreme",
                "question": "je veux 999999999 paquets de couches taille 0.5 pour bébé de 1000kg livraison sur mars",
                "expected_elements": ["paquets", "couches", "taille"],
                "description": "Query avec nombres impossibles"
            },
            
            # 🔥 CATÉGORIE 8: QUERIES VIDES OU MINIMALES
            {
                "category": "minimal",
                "level": "extreme",
                "question": "a",
                "expected_elements": [],
                "description": "Query ultra-minimale"
            },
            
            # 🔥 CATÉGORIE 9: QUERIES AVEC CONTEXTE ÉMOTIONNEL EXTRÊME
            {
                "category": "emotional_extreme",
                "level": "extreme",
                "question": "URGENT URGENT URGENT mon bébé pleure il a besoin de couches MAINTENANT taille 3 je suis désespérée aidez-moi s'il vous plaît c'est une urgence absolue",
                "expected_elements": ["urgent", "couches", "taille", "3"],
                "description": "Query avec charge émotionnelle extrême"
            },
            
            # 🔥 CATÉGORIE 10: QUERIES TECHNIQUES COMPLEXES
            {
                "category": "technical_complex",
                "level": "extreme",
                "question": "analyse comparative des propriétés d'absorption hydrophile des couches polymères superabsorbantes taille 3 versus alternatives biodégradables avec coefficient de perméabilité optimisé",
                "expected_elements": ["couches", "taille", "3"],
                "description": "Query avec vocabulaire technique complexe"
            },
            
            # 🔥 CATÉGORIE 11: QUERIES DE STRESS CONCURRENTIEL
            {
                "category": "concurrent_stress",
                "level": "extreme",
                "question": "prix couches taille 3 livraison cocody wave paiement",
                "expected_elements": ["prix", "couches", "taille", "3", "livraison", "cocody", "wave"],
                "description": "Query pour test de concurrence (sera répétée simultanément)"
            },
            
            # 🔥 CATÉGORIE 12: QUERIES AVEC INJECTION POTENTIELLE
            {
                "category": "injection_test",
                "level": "extreme",
                "question": "'; DROP TABLE documents; -- prix couches taille 3",
                "expected_elements": ["prix", "couches", "taille", "3"],
                "description": "Query avec tentative d'injection SQL"
            }
        ]
    
    def generate_random_query(self, length: int = 1000) -> str:
        """Génère une query aléatoire de longueur spécifiée"""
        words = ["couches", "prix", "taille", "livraison", "wave", "paiement", "bébé", "cocody", "yopougon"]
        random_words = [random.choice(words) for _ in range(length // 10)]
        random_chars = ''.join(random.choices(string.ascii_letters + string.digits + " ", k=length))
        return ' '.join(random_words) + " " + random_chars
    
    async def test_single_extreme_case(self, test_case: Dict) -> Dict[str, Any]:
        """Teste un cas extrême unique"""
        print(f"\n🔥 TEST EXTRÊME - {test_case['category'].upper()}")
        print(f"📝 Query: '{test_case['question'][:100]}{'...' if len(test_case['question']) > 100 else ''}'")
        print(f"🎯 Description: {test_case['description']}")
        print(f"📏 Longueur: {len(test_case['question'])} caractères")
        print("-" * 80)
        
        start_time = time.time()
        
        try:
            response = requests.post(API_URL, 
                json={
                    "message": test_case["question"],
                    "company_id": COMPANY_ID,
                    "user_id": USER_ID
                },
                timeout=60  # Timeout plus long pour les cas extrêmes
            )
            
            end_time = time.time()
            duration = (end_time - start_time) * 1000
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Analyse de la réponse
                analysis = {
                    "success": True,
                    "category": test_case["category"],
                    "level": test_case["level"],
                    "query_length": len(test_case["question"]),
                    "response_time": duration,
                    "http_status": 200,
                    "response_length": len(str(response_data)),
                    "elements_found": [],
                    "elements_missing": [],
                    "robustness_score": 0
                }
                
                # Vérifier les éléments attendus
                response_text = str(response_data).lower()
                for element in test_case["expected_elements"]:
                    if element.lower() in response_text:
                        analysis["elements_found"].append(element)
                    else:
                        analysis["elements_missing"].append(element)
                
                # Calculer le score de robustesse
                if test_case["expected_elements"]:
                    analysis["robustness_score"] = len(analysis["elements_found"]) / len(test_case["expected_elements"])
                else:
                    analysis["robustness_score"] = 1.0 if analysis["success"] else 0.0
                
                # Affichage des résultats
                status = "✅ ROBUSTE" if analysis["robustness_score"] >= 0.5 else "⚠️ FRAGILE"
                print(f"{status}")
                print(f"   ⏱️ Temps: {duration:.1f}ms")
                print(f"   📊 Score robustesse: {analysis['robustness_score']:.2f}")
                print(f"   📏 Réponse: {analysis['response_length']} chars")
                print(f"   ✅ Éléments trouvés: {analysis['elements_found']}")
                if analysis['elements_missing']:
                    print(f"   ❌ Éléments manquants: {analysis['elements_missing']}")
                
                return analysis
                
            else:
                print(f"❌ ÉCHEC HTTP {response.status_code}")
                return {
                    "success": False,
                    "category": test_case["category"],
                    "http_status": response.status_code,
                    "response_time": duration,
                    "robustness_score": 0
                }
                
        except Exception as e:
            end_time = time.time()
            duration = (end_time - start_time) * 1000
            print(f"❌ EXCEPTION: {str(e)}")
            return {
                "success": False,
                "category": test_case["category"],
                "exception": str(e),
                "response_time": duration,
                "robustness_score": 0
            }
    
    async def test_concurrent_stress(self, num_concurrent: int = 10):
        """Test de stress avec requêtes concurrentes"""
        print(f"\n🔥 TEST DE STRESS CONCURRENT - {num_concurrent} requêtes simultanées")
        print("=" * 80)
        
        stress_query = "prix couches taille 3 livraison cocody wave paiement"
        
        async def single_request():
            start_time = time.time()
            try:
                response = requests.post(API_URL, 
                    json={
                        "message": stress_query,
                        "company_id": COMPANY_ID,
                        "user_id": f"{USER_ID}_{threading.current_thread().ident}"
                    },
                    timeout=30
                )
                end_time = time.time()
                return {
                    "success": response.status_code == 200,
                    "time": (end_time - start_time) * 1000,
                    "status": response.status_code
                }
            except Exception as e:
                end_time = time.time()
                return {
                    "success": False,
                    "time": (end_time - start_time) * 1000,
                    "error": str(e)
                }
        
        # Lancer les requêtes concurrentes
        start_time = time.time()
        tasks = [single_request() for _ in range(num_concurrent)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Analyser les résultats
        successful = sum(1 for r in results if r["success"])
        avg_time = sum(r["time"] for r in results) / len(results)
        total_time = (end_time - start_time) * 1000
        
        print(f"📊 RÉSULTATS STRESS TEST:")
        print(f"   ✅ Succès: {successful}/{num_concurrent} ({successful/num_concurrent*100:.1f}%)")
        print(f"   ⏱️ Temps moyen: {avg_time:.1f}ms")
        print(f"   🕐 Temps total: {total_time:.1f}ms")
        print(f"   🚀 Débit: {num_concurrent/total_time*1000:.1f} req/s")
        
        return {
            "concurrent_requests": num_concurrent,
            "successful_requests": successful,
            "success_rate": successful/num_concurrent,
            "average_time": avg_time,
            "total_time": total_time,
            "throughput": num_concurrent/total_time*1000
        }
    
    async def test_memory_stress(self):
        """Test de stress mémoire avec queries très longues"""
        print(f"\n🔥 TEST DE STRESS MÉMOIRE")
        print("=" * 80)
        
        memory_tests = [
            {"size": 1000, "description": "Query 1KB"},
            {"size": 10000, "description": "Query 10KB"},
            {"size": 50000, "description": "Query 50KB"},
            {"size": 100000, "description": "Query 100KB"}
        ]
        
        results = []
        
        for test in memory_tests:
            print(f"\n📝 {test['description']} ({test['size']} caractères)")
            
            # Générer une query de la taille spécifiée
            large_query = self.generate_random_query(test['size'])
            
            start_time = time.time()
            try:
                response = requests.post(API_URL, 
                    json={
                        "message": large_query,
                        "company_id": COMPANY_ID,
                        "user_id": USER_ID
                    },
                    timeout=120
                )
                end_time = time.time()
                
                result = {
                    "size": test['size'],
                    "success": response.status_code == 200,
                    "time": (end_time - start_time) * 1000,
                    "status": response.status_code
                }
                
                status = "✅ GÉRÉ" if result["success"] else "❌ ÉCHEC"
                print(f"   {status} - {result['time']:.1f}ms")
                
            except Exception as e:
                end_time = time.time()
                result = {
                    "size": test['size'],
                    "success": False,
                    "time": (end_time - start_time) * 1000,
                    "error": str(e)
                }
                print(f"   ❌ EXCEPTION - {result['time']:.1f}ms - {str(e)[:50]}")
            
            results.append(result)
        
        return results
    
    async def run_extreme_limits_test(self):
        """Exécute tous les tests de limites extrêmes"""
        print("🔥 TEST ULTIME RAG - LIMITES ABSOLUES")
        print("=" * 80)
        print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🧪 Tests extrêmes: {len(self.extreme_test_cases)}")
        print("=" * 80)
        
        all_results = []
        
        # 1. Tests de cas extrêmes
        print("\n🎯 PHASE 1: TESTS DE CAS EXTRÊMES")
        for i, test_case in enumerate(self.extreme_test_cases, 1):
            print(f"\n{'='*20} TEST EXTRÊME {i}/{len(self.extreme_test_cases)} {'='*20}")
            result = await self.test_single_extreme_case(test_case)
            all_results.append(result)
            await asyncio.sleep(0.5)  # Pause entre tests
        
        # 2. Test de stress concurrent
        print(f"\n{'='*20} PHASE 2: STRESS CONCURRENT {'='*20}")
        concurrent_result = await self.test_concurrent_stress(15)
        
        # 3. Test de stress mémoire
        print(f"\n{'='*20} PHASE 3: STRESS MÉMOIRE {'='*20}")
        memory_results = await self.test_memory_stress()
        
        # 4. Rapport final
        self.generate_extreme_report(all_results, concurrent_result, memory_results)
        
        return {
            "extreme_cases": all_results,
            "concurrent_stress": concurrent_result,
            "memory_stress": memory_results
        }
    
    def generate_extreme_report(self, extreme_results: List[Dict], concurrent_result: Dict, memory_results: List[Dict]):
        """Génère le rapport final des tests extrêmes"""
        print("\n" + "="*80)
        print("🔥 RAPPORT FINAL - LIMITES ABSOLUES RAG")
        print("="*80)
        
        # Analyse des cas extrêmes
        total_extreme = len(extreme_results)
        successful_extreme = sum(1 for r in extreme_results if r.get("success", False))
        avg_robustness = sum(r.get("robustness_score", 0) for r in extreme_results) / total_extreme
        avg_time_extreme = sum(r.get("response_time", 0) for r in extreme_results) / total_extreme
        
        print(f"📊 RÉSISTANCE AUX CAS EXTRÊMES:")
        print(f"   ✅ Tests réussis: {successful_extreme}/{total_extreme} ({successful_extreme/total_extreme*100:.1f}%)")
        print(f"   🛡️ Score robustesse moyen: {avg_robustness:.2f}/1.0")
        print(f"   ⏱️ Temps moyen: {avg_time_extreme:.1f}ms")
        
        # Analyse par catégorie
        print(f"\n📈 PERFORMANCE PAR CATÉGORIE:")
        categories = {}
        for result in extreme_results:
            cat = result.get("category", "unknown")
            if cat not in categories:
                categories[cat] = {"total": 0, "success": 0, "robustness": []}
            categories[cat]["total"] += 1
            if result.get("success", False):
                categories[cat]["success"] += 1
            categories[cat]["robustness"].append(result.get("robustness_score", 0))
        
        for cat, stats in categories.items():
            success_rate = stats["success"] / stats["total"] * 100
            avg_robustness_cat = sum(stats["robustness"]) / len(stats["robustness"])
            print(f"   {cat}: {stats['success']}/{stats['total']} ({success_rate:.1f}%) - Robustesse: {avg_robustness_cat:.2f}")
        
        # Analyse stress concurrent
        print(f"\n🚀 PERFORMANCE CONCURRENT:")
        print(f"   📊 Taux de succès: {concurrent_result['success_rate']*100:.1f}%")
        print(f"   ⚡ Débit: {concurrent_result['throughput']:.1f} req/s")
        print(f"   ⏱️ Temps moyen: {concurrent_result['average_time']:.1f}ms")
        
        # Analyse stress mémoire
        print(f"\n💾 RÉSISTANCE MÉMOIRE:")
        memory_success = sum(1 for r in memory_results if r.get("success", False))
        print(f"   ✅ Tests réussis: {memory_success}/{len(memory_results)}")
        for result in memory_results:
            size_kb = result["size"] / 1000
            status = "✅" if result.get("success", False) else "❌"
            print(f"   {status} {size_kb}KB: {result.get('time', 0):.1f}ms")
        
        # Évaluation globale
        print(f"\n🎯 ÉVALUATION GLOBALE:")
        overall_score = (
            (successful_extreme / total_extreme) * 0.4 +
            concurrent_result['success_rate'] * 0.3 +
            (memory_success / len(memory_results)) * 0.3
        )
        
        if overall_score >= 0.8:
            grade = "🏆 EXCELLENT - RAG très robuste"
        elif overall_score >= 0.6:
            grade = "✅ BON - RAG robuste avec quelques faiblesses"
        elif overall_score >= 0.4:
            grade = "⚠️ MOYEN - RAG fragile sur certains cas"
        else:
            grade = "❌ FAIBLE - RAG nécessite des améliorations"
        
        print(f"   📊 Score global: {overall_score:.2f}/1.0")
        print(f"   🏅 Évaluation: {grade}")
        
        print("="*80)

async def main():
    """Point d'entrée principal"""
    test = RAGExtremeLimitsTest()
    await test.run_extreme_limits_test()

if __name__ == "__main__":
    asyncio.run(main())
