#!/usr/bin/env python3
"""
🔥 TEST DE CHARGE OPTIMISÉ - CHATBOT RUE_DU_GROS
===============================================
Tests de charge avec paramètres optimisés pour éviter erreurs 405
"""

import asyncio
import aiohttp
import time
import statistics
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from datetime import datetime

# Configuration OPTIMISÉE
ENDPOINT_URL = "http://127.0.0.1:8001/chat"
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"

# Requêtes de test variées
TEST_QUERIES = [
    "combien coûtent les couches taille 1",
    "livraison à Cocody quel tarif",
    "je peux payer avec wave money",
    "numéro whatsapp pour commander",
    "prix couches taille 4 pour enfant 10 kg"
]

# Configuration par défaut OPTIMISÉE
NUM_USERS = 10  # Réduit drastiquement
DURATION = 60   # Test plus court
RAMP_UP_TIME = 15  # Montée en charge plus douce

class OptimizedLoadTester:
    def __init__(self, num_users=10, duration=60, ramp_up=15):
        self.num_users = num_users
        self.duration = duration
        self.ramp_up = ramp_up
        self.results = []
        self.errors = []
        self.start_time = None
        
    async def single_request(self, session, user_id, query):
        """Effectue une requête unique avec timeout optimisé"""
        payload = {
            "message": query,
            "company_id": COMPANY_ID,
            "user_id": f"testuser{user_id}"
        }
        
        start_time = time.time()
        try:
            # Timeout réduit pour éviter accumulation
            async with session.post(ENDPOINT_URL, json=payload, timeout=aiohttp.ClientTimeout(total=45)) as response:
                response_text = await response.text()
                end_time = time.time()
                
                result = {
                    'user_id': user_id,
                    'query': query,
                    'status_code': response.status,
                    'response_time': (end_time - start_time) * 1000,
                    'response_length': len(response_text),
                    'timestamp': end_time - self.start_time,
                    'success': response.status == 200
                }
                
                if response.status != 200:
                    result['error'] = f"HTTP {response.status}"
                    self.errors.append(result)
                else:
                    self.results.append(result)
                    
                return result
                
        except Exception as e:
            end_time = time.time()
            error_result = {
                'user_id': user_id,
                'query': query,
                'error': str(e),
                'response_time': (end_time - start_time) * 1000,
                'timestamp': end_time - self.start_time,
                'success': False
            }
            self.errors.append(error_result)
            return error_result

    async def user_simulation(self, session, user_id):
        """Simule un utilisateur avec délais entre requêtes"""
        queries_sent = 0
        user_start_time = time.time()
        
        while (time.time() - self.start_time) < self.duration:
            query = TEST_QUERIES[queries_sent % len(TEST_QUERIES)]
            await self.single_request(session, user_id, query)
            queries_sent += 1
            
            # Délai entre requêtes pour éviter spam
            await asyncio.sleep(8)  # 8 secondes entre requêtes
            
        print(f"👤 Utilisateur {user_id}: {queries_sent} requêtes terminées")
        return queries_sent

    async def run_load_test(self):
        """Lance le test de charge optimisé"""
        print("🔥 DÉMARRAGE TEST DE CHARGE OPTIMISÉ")
        print(f"👥 Utilisateurs simultanés: {self.num_users}")
        print(f"⏱️ Durée: {self.duration}s")
        print(f"📈 Montée en charge: {self.ramp_up}s")
        print(f"🎯 URL: {ENDPOINT_URL}")
        print("=" * 70)
        
        self.start_time = time.time()
        
        # Configuration session HTTP optimisée
        connector = aiohttp.TCPConnector(
            limit=20,  # Limite connexions simultanées
            limit_per_host=10,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        
        timeout = aiohttp.ClientTimeout(total=60, connect=10)
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={"Content-Type": "application/json"}
        ) as session:
            
            tasks = []
            for i in range(self.num_users):
                # Délai de démarrage échelonné
                delay = (i * self.ramp_up) / self.num_users
                await asyncio.sleep(delay)
                print(f"🚀 Utilisateur {i} démarré (après {delay:.1f}s)")
                
                task = asyncio.create_task(self.user_simulation(session, i))
                tasks.append(task)
            
            # Attendre que tous les utilisateurs terminent
            await asyncio.gather(*tasks, return_exceptions=True)
        
        await self.analyze_results()

    async def analyze_results(self):
        """Analyse les résultats du test"""
        print("\n" + "=" * 70)
        print("📊 ANALYSE DES RÉSULTATS OPTIMISÉS")
        print("=" * 70)
        
        total_requests = len(self.results) + len(self.errors)
        success_count = len(self.results)
        error_count = len(self.errors)
        
        success_rate = (success_count / total_requests * 100) if total_requests > 0 else 0
        
        print(f"✅ Requêtes réussies: {success_count}")
        print(f"❌ Erreurs: {error_count}")
        print(f"📈 Taux de succès: {success_rate:.1f}%")
        
        if self.results:
            response_times = [r['response_time'] for r in self.results]
            avg_time = statistics.mean(response_times)
            median_time = statistics.median(response_times)
            p95_time = sorted(response_times)[int(len(response_times) * 0.95)] if len(response_times) > 1 else response_times[0]
            
            print(f"\n⏱️ TEMPS DE RÉPONSE:")
            print(f"  • Moyenne: {avg_time:.1f}ms")
            print(f"  • Médiane: {median_time:.1f}ms")
            print(f"  • P95: {p95_time:.1f}ms")
            print(f"  • Min: {min(response_times):.1f}ms")
            print(f"  • Max: {max(response_times):.1f}ms")
            
            # Throughput
            test_duration = max([r['timestamp'] for r in self.results]) if self.results else self.duration
            throughput = success_count / test_duration if test_duration > 0 else 0
            print(f"🚀 Throughput: {throughput:.2f} req/s")
        
        # Analyse des erreurs
        if self.errors:
            error_types = {}
            for error in self.errors:
                error_type = error.get('error', 'Unknown')
                if 'HTTP' in error_type:
                    error_type = f"HTTP_{error.get('status_code', 'Unknown')}"
                error_types[error_type] = error_types.get(error_type, 0) + 1
            
            print(f"\n❌ ANALYSE DES ERREURS ({error_count}):")
            for error_type, count in error_types.items():
                print(f"  • {error_type}: {count} occurrences")
        
        # Verdict
        if success_rate >= 95:
            print(f"\n🏆 VERDICT FINAL:")
            print("🟢 EXCELLENT - Système stable et performant")
        elif success_rate >= 80:
            print(f"\n🏆 VERDICT FINAL:")
            print("🟡 BON - Quelques améliorations possibles")
        else:
            print(f"\n🏆 VERDICT FINAL:")
            print("🔴 CRITIQUE - Corrections majeures requises")
        
        # Sauvegarde
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"optimized_load_test_results_{timestamp}.json"
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                'config': {
                    'num_users': self.num_users,
                    'duration': self.duration,
                    'ramp_up': self.ramp_up,
                    'success_rate': success_rate,
                    'total_requests': total_requests
                },
                'results': self.results,
                'errors': self.errors
            }, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Résultats sauvegardés: {results_file}")

async def main():
    parser = argparse.ArgumentParser(description='Test de charge optimisé pour chatbot RAG')
    parser.add_argument('--users', type=int, default=10, help='Nombre d\'utilisateurs simultanés')
    parser.add_argument('--duration', type=int, default=60, help='Durée du test en secondes')
    parser.add_argument('--ramp-up', type=int, default=15, help='Durée de montée en charge en secondes')
    
    args = parser.parse_args()
    
    tester = OptimizedLoadTester(
        num_users=args.users,
        duration=args.duration,
        ramp_up=args.ramp_up
    )
    
    await tester.run_load_test()

if __name__ == "__main__":
    asyncio.run(main())
