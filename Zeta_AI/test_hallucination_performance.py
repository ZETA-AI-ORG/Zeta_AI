#!/usr/bin/env python3
"""
⚡ TEST DE PERFORMANCE - GARDE-FOU ANTI-HALLUCINATION
Mesure de l'impact performance du nouveau système
"""

import asyncio
import time
import statistics
import psutil
import os
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceTester:
    """Testeur de performance pour le système anti-hallucination"""
    
    def __init__(self):
        self.results = []
        self.memory_usage = []
        self.cpu_usage = []
        
    def get_system_metrics(self) -> Dict:
        """Récupère les métriques système"""
        process = psutil.Process(os.getpid())
        return {
            'memory_mb': process.memory_info().rss / 1024 / 1024,
            'cpu_percent': process.cpu_percent(),
            'threads': process.num_threads()
        }
    
    async def test_old_system_performance(self, num_tests: int = 10) -> Dict:
        """Test de performance de l'ancien système"""
        print("📊 Test de performance de l'ANCIEN système...")
        
        try:
            from core.rag_engine_simplified_fixed import get_rag_response
            
            times = []
            memory_usage = []
            
            for i in range(num_tests):
                # Mesure des métriques avant
                metrics_before = self.get_system_metrics()
                
                start_time = time.time()
                
                # Test
                response = await get_rag_response(
                    message="Comment tu t'appelles ?",
                    company_id="test_company",
                    user_id="test_user"
                )
                
                end_time = time.time()
                
                # Mesure des métriques après
                metrics_after = self.get_system_metrics()
                
                processing_time = (end_time - start_time) * 1000
                memory_delta = metrics_after['memory_mb'] - metrics_before['memory_mb']
                
                times.append(processing_time)
                memory_usage.append(memory_delta)
                
                print(f"   Test {i+1}/{num_tests}: {processing_time:.2f}ms, {memory_delta:+.2f}MB")
            
            return {
                'system': 'old',
                'times': times,
                'memory_usage': memory_usage,
                'avg_time': statistics.mean(times),
                'median_time': statistics.median(times),
                'std_time': statistics.stdev(times) if len(times) > 1 else 0,
                'avg_memory': statistics.mean(memory_usage),
                'max_memory': max(memory_usage),
                'min_memory': min(memory_usage)
            }
            
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            return {'system': 'old', 'error': str(e)}
    
    async def test_new_system_performance(self, num_tests: int = 10) -> Dict:
        """Test de performance du nouveau système"""
        print("\n📊 Test de performance du NOUVEAU système...")
        
        try:
            from core.rag_engine_simplified_fixed import get_rag_response_advanced
            
            times = []
            memory_usage = []
            
            for i in range(num_tests):
                # Mesure des métriques avant
                metrics_before = self.get_system_metrics()
                
                start_time = time.time()
                
                # Test
                result = await get_rag_response_advanced(
                    message="Comment tu t'appelles ?",
                    user_id="test_user",
                    company_id="test_company"
                )
                
                end_time = time.time()
                
                # Mesure des métriques après
                metrics_after = self.get_system_metrics()
                
                processing_time = (end_time - start_time) * 1000
                memory_delta = metrics_after['memory_mb'] - metrics_before['memory_mb']
                
                times.append(processing_time)
                memory_usage.append(memory_delta)
                
                print(f"   Test {i+1}/{num_tests}: {processing_time:.2f}ms, {memory_delta:+.2f}MB")
            
            return {
                'system': 'new',
                'times': times,
                'memory_usage': memory_usage,
                'avg_time': statistics.mean(times),
                'median_time': statistics.median(times),
                'std_time': statistics.stdev(times) if len(times) > 1 else 0,
                'avg_memory': statistics.mean(memory_usage),
                'max_memory': max(memory_usage),
                'min_memory': min(memory_usage)
            }
            
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            return {'system': 'new', 'error': str(e)}
    
    async def test_concurrent_performance(self, num_concurrent: int = 5, num_tests: int = 20) -> Dict:
        """Test de performance en concurrence"""
        print(f"\n📊 Test de performance CONCURRENT ({num_concurrent} concurrent, {num_tests} tests)...")
        
        try:
            from core.rag_engine_simplified_fixed import get_rag_response_advanced
            
            async def single_concurrent_test(test_id: int):
                start_time = time.time()
                
                result = await get_rag_response_advanced(
                    message=f"Test concurrent {test_id}",
                    user_id=f"test_user_{test_id}",
                    company_id="test_company"
                )
                
                end_time = time.time()
                return (end_time - start_time) * 1000
            
            # Créer les tâches concurrentes
            tasks = []
            for i in range(num_tests):
                task = single_concurrent_test(i)
                tasks.append(task)
            
            # Exécuter avec limitation de concurrence
            semaphore = asyncio.Semaphore(num_concurrent)
            
            async def limited_task(task):
                async with semaphore:
                    return await task
            
            # Exécuter toutes les tâches
            start_time = time.time()
            times = await asyncio.gather(*[limited_task(task) for task in tasks])
            total_time = time.time() - start_time
            
            return {
                'system': 'new_concurrent',
                'times': times,
                'total_time': total_time,
                'avg_time': statistics.mean(times),
                'median_time': statistics.median(times),
                'std_time': statistics.stdev(times) if len(times) > 1 else 0,
                'requests_per_second': num_tests / total_time,
                'concurrent_limit': num_concurrent
            }
            
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            return {'system': 'new_concurrent', 'error': str(e)}
    
    def compare_performance(self, old_results: Dict, new_results: Dict) -> Dict:
        """Compare les performances des deux systèmes"""
        print("\n📊 COMPARAISON DES PERFORMANCES")
        print("=" * 50)
        
        if 'error' in old_results or 'error' in new_results:
            print("❌ Impossible de comparer - erreurs détectées")
            return {}
        
        # Comparaison du temps
        time_improvement = ((old_results['avg_time'] - new_results['avg_time']) / old_results['avg_time']) * 100
        
        print(f"⏱️  TEMPS DE TRAITEMENT:")
        print(f"   Ancien système: {old_results['avg_time']:.2f}ms (médiane: {old_results['median_time']:.2f}ms)")
        print(f"   Nouveau système: {new_results['avg_time']:.2f}ms (médiane: {new_results['median_time']:.2f}ms)")
        print(f"   Amélioration: {time_improvement:+.1f}%")
        
        # Comparaison de la mémoire
        memory_impact = new_results['avg_memory'] - old_results['avg_memory']
        
        print(f"\n💾 UTILISATION MÉMOIRE:")
        print(f"   Ancien système: {old_results['avg_memory']:+.2f}MB")
        print(f"   Nouveau système: {new_results['avg_memory']:+.2f}MB")
        print(f"   Impact: {memory_impact:+.2f}MB")
        
        # Analyse de la stabilité
        old_stability = old_results['std_time'] / old_results['avg_time'] * 100
        new_stability = new_results['std_time'] / new_results['avg_time'] * 100
        
        print(f"\n📈 STABILITÉ (coefficient de variation):")
        print(f"   Ancien système: {old_stability:.1f}%")
        print(f"   Nouveau système: {new_stability:.1f}%")
        
        # Recommandations
        print(f"\n💡 RECOMMANDATIONS:")
        
        if time_improvement > 20:
            print("   ✅ Le nouveau système est significativement plus rapide")
        elif time_improvement > 0:
            print("   ✅ Le nouveau système est légèrement plus rapide")
        elif time_improvement > -20:
            print("   ⚠️  Le nouveau système est légèrement plus lent")
        else:
            print("   ⚠️  Le nouveau système est significativement plus lent")
        
        if memory_impact < 10:
            print("   ✅ Impact mémoire acceptable")
        elif memory_impact < 50:
            print("   ⚠️  Impact mémoire modéré")
        else:
            print("   ⚠️  Impact mémoire élevé")
        
        if new_stability < old_stability:
            print("   ✅ Le nouveau système est plus stable")
        else:
            print("   ⚠️  Le nouveau système est moins stable")
        
        return {
            'time_improvement': time_improvement,
            'memory_impact': memory_impact,
            'stability_improvement': old_stability - new_stability,
            'recommendations': self._generate_recommendations(time_improvement, memory_impact, new_stability)
        }
    
    def _generate_recommendations(self, time_improvement: float, memory_impact: float, stability: float) -> List[str]:
        """Génère des recommandations basées sur les résultats"""
        recommendations = []
        
        if time_improvement < -50:
            recommendations.append("Considérer l'optimisation du nouveau système")
        
        if memory_impact > 100:
            recommendations.append("Surveiller l'utilisation mémoire en production")
        
        if stability > 50:
            recommendations.append("Investiguer la variabilité des performances")
        
        if time_improvement > 0 and memory_impact < 50:
            recommendations.append("Le nouveau système est prêt pour la production")
        
        return recommendations

async def main():
    """Fonction principale"""
    print("⚡ TEST DE PERFORMANCE - GARDE-FOU ANTI-HALLUCINATION")
    print("Mesure de l'impact performance du nouveau système")
    print("=" * 70)
    
    tester = PerformanceTester()
    
    # Test de performance de base
    print("🚀 DÉMARRAGE DES TESTS DE PERFORMANCE")
    print("=" * 50)
    
    # Test ancien système
    old_results = await tester.test_old_system_performance(num_tests=5)
    
    # Test nouveau système
    new_results = await tester.test_new_system_performance(num_tests=5)
    
    # Comparaison
    comparison = tester.compare_performance(old_results, new_results)
    
    # Test de concurrence
    concurrent_results = await tester.test_concurrent_performance(num_concurrent=3, num_tests=10)
    
    if 'error' not in concurrent_results:
        print(f"\n🔄 PERFORMANCE CONCURRENTE:")
        print(f"   Temps moyen: {concurrent_results['avg_time']:.2f}ms")
        print(f"   Requêtes/seconde: {concurrent_results['requests_per_second']:.2f}")
        print(f"   Limite concurrente: {concurrent_results['concurrent_limit']}")
    
    # Résumé final
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ FINAL")
    
    if 'error' not in old_results and 'error' not in new_results:
        print(f"   Impact temps: {comparison['time_improvement']:+.1f}%")
        print(f"   Impact mémoire: {comparison['memory_impact']:+.2f}MB")
        print(f"   Amélioration stabilité: {comparison['stability_improvement']:+.1f}%")
        
        if comparison['recommendations']:
            print(f"\n💡 RECOMMANDATIONS:")
            for rec in comparison['recommendations']:
                print(f"   - {rec}")
    
    print("\n🎉 TESTS DE PERFORMANCE TERMINÉS !")

if __name__ == "__main__":
    asyncio.run(main())
