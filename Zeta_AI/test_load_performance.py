#!/usr/bin/env python3
"""
🔥 TEST DE CHARGE & PERFORMANCE - CHATBOT RUE_DU_GROS
======================================================
Tests de montée en charge avec utilisateurs simultanés
Mesure des performances sous stress
"""

import asyncio
import aiohttp
import time
import statistics
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from datetime import datetime

# Configuration
ENDPOINT_URL = "http://127.0.0.1:8001/chat"
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"

# Requêtes de test variées
TEST_QUERIES = [
    "combien coûtent les couches taille 1",
    "livraison à Cocody quel tarif",
    "je peux payer avec wave money",
    "numéro whatsapp pour commander",
    "prix couches taille 4 pour enfant 10 kg",
    "vous livrez à Yopougon combien ça coûte",
    "faut-il payer un acompte pour commander",
    "différence prix entre taille 3 et taille 6",
    "couches culottes prix pour 6 paquets",
    "commande avant 11h livraison jour même possible"
]

class LoadTester:
    def __init__(self, num_users=10, duration=60, ramp_up=10):
        self.num_users = num_users
        self.duration = duration  # secondes
        self.ramp_up = ramp_up   # secondes pour monter en charge
        self.results = []
        self.errors = []
        self.start_time = None
        
    async def single_request(self, session, user_id, query):
        """Effectue une requête unique"""
        payload = {
            "message": query,
            "company_id": COMPANY_ID,
            "user_id": f"loadtest{user_id}"
        }
        
        start_time = time.time()
        try:
            async with session.post(ENDPOINT_URL, json=payload, timeout=30) as response:
                end_time = time.time()
                duration = (end_time - start_time) * 1000
                
                if response.status == 200:
                    response_text = await response.text()
                    self.results.append({
                        'user_id': user_id,
                        'duration': duration,
                        'status': response.status,
                        'response_length': len(response_text),
                        'timestamp': time.time() - self.start_time
                    })
                    return True, duration
                else:
                    error_text = await response.text()
                    self.errors.append({
                        'user_id': user_id,
                        'status': response.status,
                        'error': error_text,
                        'timestamp': time.time() - self.start_time
                    })
                    return False, duration
                    
        except Exception as e:
            end_time = time.time()
            duration = (end_time - start_time) * 1000
            self.errors.append({
                'user_id': user_id,
                'error': str(e),
                'timestamp': time.time() - self.start_time
            })
            return False, duration

    async def user_simulation(self, session, user_id):
        """Simule un utilisateur pendant la durée du test"""
        end_time = self.start_time + self.duration
        request_count = 0
        
        while time.time() < end_time:
            # Sélectionne une requête aléatoire
            query = TEST_QUERIES[request_count % len(TEST_QUERIES)]
            
            success, duration = await self.single_request(session, user_id, query)
            request_count += 1
            
            # Pause entre requêtes (simule comportement utilisateur réel)
            await asyncio.sleep(5 + (request_count % 3))  # 5-7 secondes
            
        print(f"👤 Utilisateur {user_id}: {request_count} requêtes terminées")

    async def run_load_test(self):
        """Lance le test de charge principal"""
        print(f"🔥 DÉMARRAGE TEST DE CHARGE")
        print(f"👥 Utilisateurs simultanés: {self.num_users}")
        print(f"⏱️ Durée: {self.duration}s")
        print(f"📈 Montée en charge: {self.ramp_up}s")
        print(f"🎯 URL: {ENDPOINT_URL}")
        print("="*70)
        
        self.start_time = time.time()
        
        # Configuration session HTTP
        connector = aiohttp.TCPConnector(limit=self.num_users * 2)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            tasks = []
            
            # Montée en charge progressive
            for i in range(self.num_users):
                # Délai pour montée en charge progressive
                delay = (i / self.num_users) * self.ramp_up
                
                task = asyncio.create_task(self.delayed_user_start(session, i, delay))
                tasks.append(task)
            
            # Attendre que tous les utilisateurs terminent
            await asyncio.gather(*tasks, return_exceptions=True)
        
        await self.analyze_results()

    async def delayed_user_start(self, session, user_id, delay):
        """Démarre un utilisateur avec délai (montée en charge)"""
        await asyncio.sleep(delay)
        print(f"🚀 Utilisateur {user_id} démarré (après {delay:.1f}s)")
        await self.user_simulation(session, user_id)

    async def analyze_results(self):
        """Analyse et affiche les résultats"""
        print("\n" + "="*70)
        print("📊 ANALYSE DES RÉSULTATS")
        print("="*70)
        
        total_requests = len(self.results)
        total_errors = len(self.errors)
        success_rate = (total_requests / (total_requests + total_errors)) * 100 if (total_requests + total_errors) > 0 else 0
        
        if self.results:
            durations = [r['duration'] for r in self.results]
            avg_duration = statistics.mean(durations)
            median_duration = statistics.median(durations)
            p95_duration = sorted(durations)[int(len(durations) * 0.95)] if len(durations) > 20 else max(durations)
            min_duration = min(durations)
            max_duration = max(durations)
            
            # Calcul du throughput
            if self.results:
                test_duration = max([r['timestamp'] for r in self.results])
                throughput = total_requests / test_duration if test_duration > 0 else 0
            else:
                test_duration = self.duration
                throughput = 0
            
            # Fallback si throughput non défini
            if 'throughput' not in locals():
                throughput = 0
            
            print(f"✅ Requêtes réussies: {total_requests}")
            print(f"❌ Erreurs: {total_errors}")
            print(f"📈 Taux de succès: {success_rate:.1f}%")
            print(f"🚀 Throughput: {throughput:.2f} req/s")
            print()
            print("⏱️ TEMPS DE RÉPONSE:")
            print(f"  • Moyenne: {avg_duration:.1f}ms")
            print(f"  • Médiane: {median_duration:.1f}ms")
            print(f"  • P95: {p95_duration:.1f}ms")
            print(f"  • Min: {min_duration:.1f}ms")
            print(f"  • Max: {max_duration:.1f}ms")
            
            # Analyse de la performance dans le temps
            print("\n📈 PERFORMANCE DANS LE TEMPS:")
            time_buckets = {}
            for result in self.results:
                bucket = int(result['timestamp'] // 30) * 30  # Buckets de 30s
                if bucket not in time_buckets:
                    time_buckets[bucket] = []
                time_buckets[bucket].append(result['duration'])
            
            for bucket in sorted(time_buckets.keys()):
                avg_bucket = statistics.mean(time_buckets[bucket])
                count_bucket = len(time_buckets[bucket])
                print(f"  • {bucket:3d}-{bucket+30:3d}s: {avg_bucket:6.1f}ms avg ({count_bucket:3d} req)")
        
        # Analyse des erreurs
        if self.errors:
            print(f"\n❌ ANALYSE DES ERREURS ({len(self.errors)}):")
            error_types = {}
            for error in self.errors:
                error_key = error.get('status', 'Exception')
                if error_key not in error_types:
                    error_types[error_key] = 0
                error_types[error_key] += 1
            
            for error_type, count in error_types.items():
                print(f"  • {error_type}: {count} occurrences")
        
        # Verdict final
        print(f"\n🏆 VERDICT FINAL:")
        if success_rate >= 99 and avg_duration < 5000:
            print("✅ EXCELLENT - Système prêt pour production")
        elif success_rate >= 95 and avg_duration < 10000:
            print("🟡 BON - Quelques optimisations recommandées")
        elif success_rate >= 90:
            print("🟠 MOYEN - Optimisations nécessaires")
        else:
            print("🔴 CRITIQUE - Corrections majeures requises")
            
        # Sauvegarde des résultats
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"load_test_results_{timestamp}.json"
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                'config': {
                    'num_users': self.num_users,
                    'duration': self.duration,
                    'ramp_up': self.ramp_up
                },
                'summary': {
                    'total_requests': total_requests,
                    'total_errors': total_errors,
                    'success_rate': success_rate,
                    'avg_duration': avg_duration if self.results else 0,
                    'throughput': throughput
                },
                'results': self.results,
                'errors': self.errors
            }, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Résultats sauvegardés: {results_file}")

async def main():
    parser = argparse.ArgumentParser(description='Test de charge pour chatbot RAG')
    parser.add_argument('--users', type=int, default=15, help='Nombre d\'utilisateurs simultanés')
    parser.add_argument('--duration', type=int, default=120, help='Durée du test en secondes')
    parser.add_argument('--ramp-up', type=int, default=20, help='Durée de montée en charge en secondes')
    
    args = parser.parse_args()
    
    tester = LoadTester(
        num_users=args.users,
        duration=args.duration,
        ramp_up=args.ramp_up
    )
    
    await tester.run_load_test()

if __name__ == "__main__":
    asyncio.run(main())
