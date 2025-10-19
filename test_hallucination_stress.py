#!/usr/bin/env python3
"""
💥 TEST DE STRESS - GARDE-FOU ANTI-HALLUCINATION
Test de charge et de limites du système
"""

import asyncio
import time
import random
import string
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StressTester:
    """Testeur de stress pour le système anti-hallucination"""
    
    def __init__(self):
        self.results = []
        self.start_time = None
        
    def generate_random_query(self, length: int = 50) -> str:
        """Génère une requête aléatoire"""
        words = [
            "comment", "quand", "où", "pourquoi", "combien", "quel", "quelle",
            "produit", "prix", "livraison", "stock", "garantie", "contact",
            "bonjour", "merci", "aide", "information", "service", "client"
        ]
        
        query = " ".join(random.choices(words, k=random.randint(3, 8)))
        
        # Ajouter des caractères spéciaux
        if random.random() < 0.3:
            query += " " + "".join(random.choices(string.punctuation, k=random.randint(1, 5)))
        
        return query[:length]
    
    def generate_hallucination_response(self) -> str:
        """Génère une réponse d'hallucination"""
        templates = [
            "Le prix exact est {price}€ avec une garantie de {years} ans.",
            "Nous livrons gratuitement en {time} dans toute l'Europe.",
            "Notre stock actuel est de {stock} unités, disponible immédiatement.",
            "Ce produit est certifié {certification} et respecte la norme {norm}.",
            "La livraison est garantie en {time} avec un taux de satisfaction de {percent}%."
        ]
        
        template = random.choice(templates)
        return template.format(
            price=random.randint(10, 1000),
            years=random.randint(1, 5),
            time=random.choice(["24h", "48h", "1 semaine"]),
            stock=random.randint(100, 5000),
            certification=random.choice(["ISO 9001", "CE", "FDA"]),
            norm=random.choice(["EN 12345", "ISO 14001", "CE 67890"]),
            percent=random.randint(95, 100)
        )
    
    async def run_stress_test(self, num_requests: int = 100, concurrent: int = 10) -> Dict:
        """Exécute le test de stress"""
        print(f"💥 DÉMARRAGE DU TEST DE STRESS")
        print(f"   Requêtes: {num_requests}")
        print(f"   Concurrence: {concurrent}")
        print("=" * 50)
        
        self.start_time = time.time()
        
        # Créer les tâches
        tasks = []
        for i in range(num_requests):
            task = self._single_stress_test(i)
            tasks.append(task)
        
        # Exécuter avec limitation de concurrence
        semaphore = asyncio.Semaphore(concurrent)
        
        async def limited_task(task):
            async with semaphore:
                return await task
        
        # Exécuter toutes les tâches
        results = await asyncio.gather(*[limited_task(task) for task in tasks], return_exceptions=True)
        
        # Analyser les résultats
        return self._analyze_stress_results(results)
    
    async def _single_stress_test(self, test_id: int) -> Dict:
        """Exécute un test de stress individuel"""
        start_time = time.time()
        
        try:
            from core.advanced_intent_classifier import classify_intent_advanced
            from core.context_aware_hallucination_guard import validate_response_contextual
            from core.confidence_scoring_system import calculate_confidence_score
            
            # Générer des données de test
            query = self.generate_random_query()
            response = self.generate_hallucination_response() if random.random() < 0.5 else "Réponse normale"
            
            # Classification
            intent_result = await classify_intent_advanced(query)
            
            # Validation
            validation_result = await validate_response_contextual(
                user_query=query,
                ai_response=response,
                intent_result=intent_result,
                supabase_results=[],
                meili_results=[],
                supabase_context="",
                meili_context="",
                company_id="stress_test"
            )
            
            # Scoring
            confidence_score = await calculate_confidence_score(
                user_query=query,
                ai_response=response,
                intent_result=intent_result,
                supabase_results=[],
                meili_results=[],
                supabase_context="",
                meili_context="",
                validation_result=validation_result.__dict__ if validation_result else None
            )
            
            processing_time = (time.time() - start_time) * 1000
            
            return {
                'test_id': test_id,
                'status': 'success',
                'query': query,
                'response': response,
                'intent': intent_result.primary_intent.value,
                'intent_confidence': intent_result.confidence,
                'validation_safe': validation_result.is_safe,
                'validation_confidence': validation_result.confidence_score,
                'overall_confidence': confidence_score.overall_confidence,
                'confidence_level': confidence_score.confidence_level.value,
                'risk_level': confidence_score.risk_level,
                'processing_time_ms': processing_time
            }
            
        except Exception as e:
            return {
                'test_id': test_id,
                'status': 'error',
                'error': str(e),
                'processing_time_ms': (time.time() - start_time) * 1000
            }
    
    def _analyze_stress_results(self, results: List[Dict]) -> Dict:
        """Analyse les résultats du test de stress"""
        successful_tests = [r for r in results if isinstance(r, dict) and r.get('status') == 'success']
        failed_tests = [r for r in results if isinstance(r, dict) and r.get('status') == 'error']
        exception_tests = [r for r in results if not isinstance(r, dict)]
        
        total_time = time.time() - self.start_time
        
        # Statistiques de performance
        processing_times = [r['processing_time_ms'] for r in successful_tests]
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        max_processing_time = max(processing_times) if processing_times else 0
        min_processing_time = min(processing_times) if processing_times else 0
        
        # Statistiques de validation
        safe_responses = len([r for r in successful_tests if r['validation_safe']])
        unsafe_responses = len([r for r in successful_tests if not r['validation_safe']])
        
        # Statistiques de confiance
        confidence_scores = [r['overall_confidence'] for r in successful_tests]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        # Distribution des niveaux de confiance
        confidence_levels = {}
        for r in successful_tests:
            level = r['confidence_level']
            confidence_levels[level] = confidence_levels.get(level, 0) + 1
        
        # Distribution des niveaux de risque
        risk_levels = {}
        for r in successful_tests:
            level = r['risk_level']
            risk_levels[level] = risk_levels.get(level, 0) + 1
        
        analysis = {
            'total_tests': len(results),
            'successful_tests': len(successful_tests),
            'failed_tests': len(failed_tests),
            'exception_tests': len(exception_tests),
            'success_rate': (len(successful_tests) / len(results)) * 100 if results else 0,
            'total_time_seconds': total_time,
            'requests_per_second': len(results) / total_time if total_time > 0 else 0,
            'performance': {
                'avg_processing_time_ms': avg_processing_time,
                'max_processing_time_ms': max_processing_time,
                'min_processing_time_ms': min_processing_time
            },
            'validation': {
                'safe_responses': safe_responses,
                'unsafe_responses': unsafe_responses,
                'safety_rate': (safe_responses / len(successful_tests)) * 100 if successful_tests else 0
            },
            'confidence': {
                'avg_confidence': avg_confidence,
                'confidence_distribution': confidence_levels,
                'risk_distribution': risk_levels
            },
            'errors': [r['error'] for r in failed_tests if 'error' in r]
        }
        
        return analysis
    
    def print_stress_results(self, analysis: Dict):
        """Affiche les résultats du test de stress"""
        print("\n📊 RÉSULTATS DU TEST DE STRESS")
        print("=" * 50)
        
        print(f"📈 PERFORMANCE:")
        print(f"   Tests réussis: {analysis['successful_tests']}/{analysis['total_tests']} ({analysis['success_rate']:.1f}%)")
        print(f"   Temps total: {analysis['total_time_seconds']:.2f}s")
        print(f"   Requêtes/seconde: {analysis['requests_per_second']:.2f}")
        print(f"   Temps de traitement moyen: {analysis['performance']['avg_processing_time_ms']:.2f}ms")
        print(f"   Temps max: {analysis['performance']['max_processing_time_ms']:.2f}ms")
        print(f"   Temps min: {analysis['performance']['min_processing_time_ms']:.2f}ms")
        
        print(f"\n🛡️ VALIDATION:")
        print(f"   Réponses sûres: {analysis['validation']['safe_responses']}")
        print(f"   Réponses rejetées: {analysis['validation']['unsafe_responses']}")
        print(f"   Taux de sécurité: {analysis['validation']['safety_rate']:.1f}%")
        
        print(f"\n📊 CONFIANCE:")
        print(f"   Confiance moyenne: {analysis['confidence']['avg_confidence']:.3f}")
        print(f"   Distribution des niveaux:")
        for level, count in analysis['confidence']['confidence_distribution'].items():
            print(f"     {level}: {count}")
        print(f"   Distribution des risques:")
        for level, count in analysis['confidence']['risk_distribution'].items():
            print(f"     {level}: {count}")
        
        if analysis['errors']:
            print(f"\n❌ ERREURS ({len(analysis['errors'])}):")
            for error in set(analysis['errors']):
                print(f"   {error}")

async def main():
    """Fonction principale"""
    print("💥 TEST DE STRESS - GARDE-FOU ANTI-HALLUCINATION")
    print("Ce test va pousser le système à ses limites")
    print("=" * 60)
    
    tester = StressTester()
    
    # Test de stress progressif
    test_configs = [
        {'num_requests': 10, 'concurrent': 2, 'name': 'Test léger'},
        {'num_requests': 50, 'concurrent': 5, 'name': 'Test modéré'},
        {'num_requests': 100, 'concurrent': 10, 'name': 'Test intense'}
    ]
    
    for config in test_configs:
        print(f"\n🚀 {config['name']} ({config['num_requests']} requêtes, {config['concurrent']} concurrent)")
        print("-" * 50)
        
        try:
            results = await tester.run_stress_test(
                num_requests=config['num_requests'],
                concurrent=config['concurrent']
            )
            tester.print_stress_results(results)
            
            # Pause entre les tests
            if config != test_configs[-1]:
                print("\n⏸️  Pause de 2 secondes...")
                await asyncio.sleep(2)
                
        except Exception as e:
            print(f"❌ Erreur lors du {config['name']}: {e}")
    
    print("\n🎉 TESTS DE STRESS TERMINÉS !")

if __name__ == "__main__":
    asyncio.run(main())
