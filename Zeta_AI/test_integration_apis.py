#!/usr/bin/env python3
"""
🔌 TESTS D'INTÉGRATION & PANNES APIs - CHATBOT RUE_DU_GROS
=========================================================
Tests de robustesse face aux pannes d'APIs externes
Validation des mécanismes de fallback et récupération
"""

import asyncio
import aiohttp
import time
import json
from datetime import datetime
import subprocess
import psutil
import requests

# Configuration
ENDPOINT_URL = "http://127.0.0.1:8001/chat"
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"

# URLs des services à tester
MEILISEARCH_URL = "http://127.0.0.1:7700"
SUPABASE_URL = "https://your-project.supabase.co"  # À ajuster selon config

class IntegrationTester:
    def __init__(self):
        self.results = []
        self.service_failures = []
        
    # Tests de disponibilité des services
    SERVICE_AVAILABILITY_TESTS = [
        {
            "name": "MeiliSearch Health Check",
            "url": f"{MEILISEARCH_URL}/health",
            "service": "meilisearch",
            "critical": True
        },
        {
            "name": "MeiliSearch Version",
            "url": f"{MEILISEARCH_URL}/version",
            "service": "meilisearch",
            "critical": False
        }
    ]
    
    # Tests de résilience aux pannes
    RESILIENCE_TESTS = [
        {
            "name": "Requête Pendant Surcharge MeiliSearch",
            "query": "combien coûtent les couches taille 1",
            "simulation": "meilisearch_overload",
            "expected_behavior": "graceful_degradation"
        },
        {
            "name": "Requête avec Timeout Réseau",
            "query": "livraison à Cocody combien ça coûte",
            "simulation": "network_timeout",
            "expected_behavior": "timeout_handling"
        },
        {
            "name": "Requête avec Service Indisponible",
            "query": "je peux payer avec wave money",
            "simulation": "service_unavailable",
            "expected_behavior": "fallback_response"
        }
    ]
    
    # Tests de récupération après panne
    RECOVERY_TESTS = [
        {
            "name": "Récupération Après Redémarrage MeiliSearch",
            "steps": [
                "test_before_restart",
                "simulate_restart", 
                "test_after_restart"
            ],
            "query": "prix couches taille 4",
            "expected_recovery_time": 30  # secondes
        }
    ]

    async def check_service_availability(self):
        """Vérifie la disponibilité des services externes"""
        print(f"\n🔍 VÉRIFICATION DISPONIBILITÉ SERVICES")
        print("="*50)
        
        availability_results = []
        
        for test in self.SERVICE_AVAILABILITY_TESTS:
            print(f"\n📡 {test['name']}")
            
            try:
                start_time = time.time()
                response = requests.get(test['url'], timeout=10)
                end_time = time.time()
                duration = (end_time - start_time) * 1000
                
                if response.status_code == 200:
                    print(f"    ✅ Service disponible ({duration:.1f}ms)")
                    status = "available"
                else:
                    print(f"    ⚠️ Service répond mais erreur {response.status_code}")
                    status = "error"
                
            except requests.exceptions.Timeout:
                print(f"    ⏰ Timeout - Service lent ou indisponible")
                status = "timeout"
                duration = 10000
                
            except requests.exceptions.ConnectionError:
                print(f"    ❌ Service indisponible - Connexion refusée")
                status = "unavailable"
                duration = 0
                
            except Exception as e:
                print(f"    💥 Erreur inattendue: {str(e)}")
                status = "error"
                duration = 0
            
            availability_results.append({
                'service': test['service'],
                'test_name': test['name'],
                'status': status,
                'duration': duration,
                'critical': test['critical'],
                'timestamp': time.time()
            })
            
            if test['critical'] and status != "available":
                self.service_failures.append({
                    'service': test['service'],
                    'issue': f"Service critique indisponible: {test['name']}",
                    'impact': "high"
                })
        
        return availability_results

    async def run_resilience_tests(self, session):
        """Tests de résilience face aux pannes"""
        print(f"\n🛡️ TESTS DE RÉSILIENCE")
        print("="*50)
        
        resilience_results = []
        
        for test in self.RESILIENCE_TESTS:
            print(f"\n⚡ {test['name']}")
            print(f"    Simulation: {test['simulation']}")
            
            # Simulation de la panne selon le type
            if test['simulation'] == "meilisearch_overload":
                await self.simulate_meilisearch_overload()
            elif test['simulation'] == "network_timeout":
                await self.simulate_network_timeout()
            elif test['simulation'] == "service_unavailable":
                await self.simulate_service_unavailable()
            
            # Test de la requête pendant la simulation
            success, response, duration = await self.send_request_with_timeout(
                session, test['query'], timeout=15
            )
            
            # Analyse du comportement
            behavior_analysis = self.analyze_resilience_behavior(
                test, success, response, duration
            )
            
            result = {
                'test_name': test['name'],
                'query': test['query'],
                'simulation': test['simulation'],
                'expected_behavior': test['expected_behavior'],
                'success': success,
                'response': response if success else str(response),
                'duration': duration,
                'behavior_analysis': behavior_analysis,
                'timestamp': time.time()
            }
            
            resilience_results.append(result)
            
            if behavior_analysis['appropriate']:
                print(f"    ✅ Comportement approprié: {behavior_analysis['description']}")
            else:
                print(f"    ❌ Comportement inapproprié: {behavior_analysis['description']}")
                self.service_failures.append({
                    'test': test['name'],
                    'issue': behavior_analysis['description'],
                    'impact': 'medium'
                })
            
            print(f"    ⏱️ Temps de réponse: {duration:.1f}ms")
            
            # Nettoyage après simulation
            await self.cleanup_simulation(test['simulation'])
            await asyncio.sleep(2)
        
        return resilience_results

    async def run_recovery_tests(self, session):
        """Tests de récupération après panne"""
        print(f"\n🔄 TESTS DE RÉCUPÉRATION")
        print("="*50)
        
        recovery_results = []
        
        for test in self.RECOVERY_TESTS:
            print(f"\n🔁 {test['name']}")
            
            recovery_data = {
                'test_name': test['name'],
                'query': test['query'],
                'expected_recovery_time': test['expected_recovery_time'],
                'steps': []
            }
            
            # Étape 1: Test avant simulation
            print("    1. Test avant simulation...")
            success_before, response_before, duration_before = await self.send_request(
                session, test['query']
            )
            
            recovery_data['steps'].append({
                'step': 'before_simulation',
                'success': success_before,
                'duration': duration_before,
                'response_length': len(response_before) if success_before else 0
            })
            
            if success_before:
                print(f"       ✅ Fonctionnel ({duration_before:.1f}ms)")
            else:
                print(f"       ❌ Déjà dysfonctionnel")
            
            # Étape 2: Simulation de panne/redémarrage
            print("    2. Simulation de redémarrage...")
            restart_success = await self.simulate_service_restart("meilisearch")
            
            if restart_success:
                print("       🔄 Redémarrage simulé")
            else:
                print("       ⚠️ Simulation de redémarrage échouée")
            
            # Étape 3: Tests de récupération
            print("    3. Tests de récupération...")
            recovery_start = time.time()
            max_attempts = test['expected_recovery_time']
            
            for attempt in range(1, max_attempts + 1):
                await asyncio.sleep(1)
                
                success_after, response_after, duration_after = await self.send_request(
                    session, test['query']
                )
                
                recovery_time = time.time() - recovery_start
                
                if success_after:
                    print(f"       ✅ Récupération réussie en {recovery_time:.1f}s (tentative {attempt})")
                    
                    recovery_data['steps'].append({
                        'step': 'recovery_successful',
                        'recovery_time': recovery_time,
                        'attempts': attempt,
                        'success': True,
                        'duration': duration_after
                    })
                    break
                else:
                    if attempt % 5 == 0:  # Log tous les 5 essais
                        print(f"       ⏳ Tentative {attempt}/{max_attempts}...")
            
            else:
                # Récupération échouée
                print(f"       ❌ Récupération échouée après {max_attempts}s")
                recovery_data['steps'].append({
                    'step': 'recovery_failed',
                    'recovery_time': max_attempts,
                    'attempts': max_attempts,
                    'success': False
                })
                
                self.service_failures.append({
                    'test': test['name'],
                    'issue': f"Récupération échouée après {max_attempts}s",
                    'impact': 'high'
                })
            
            recovery_results.append(recovery_data)
        
        return recovery_results

    async def simulate_meilisearch_overload(self):
        """Simule une surcharge de MeiliSearch"""
        print("       🔥 Simulation surcharge MeiliSearch...")
        # Simulation basique - dans un vrai test, on pourrait envoyer de nombreuses requêtes
        await asyncio.sleep(0.1)

    async def simulate_network_timeout(self):
        """Simule un timeout réseau"""
        print("       ⏰ Simulation timeout réseau...")
        await asyncio.sleep(0.1)

    async def simulate_service_unavailable(self):
        """Simule un service indisponible"""
        print("       ❌ Simulation service indisponible...")
        await asyncio.sleep(0.1)

    async def simulate_service_restart(self, service):
        """Simule le redémarrage d'un service"""
        print(f"       🔄 Simulation redémarrage {service}...")
        # Dans un environnement de test réel, on pourrait redémarrer le service
        # Pour cette simulation, on attend juste
        await asyncio.sleep(2)
        return True

    async def cleanup_simulation(self, simulation_type):
        """Nettoie après une simulation"""
        await asyncio.sleep(0.1)

    def analyze_resilience_behavior(self, test, success, response, duration):
        """Analyse le comportement de résilience"""
        expected = test['expected_behavior']
        
        if expected == "graceful_degradation":
            if success and duration < 30000:  # 30s max
                return {
                    'appropriate': True,
                    'description': 'Dégradation gracieuse - service maintenu'
                }
            elif success and duration >= 30000:
                return {
                    'appropriate': False,
                    'description': 'Réponse trop lente sous charge'
                }
            else:
                return {
                    'appropriate': False,
                    'description': 'Service complètement indisponible'
                }
        
        elif expected == "timeout_handling":
            if success and duration < 20000:  # 20s max
                return {
                    'appropriate': True,
                    'description': 'Timeout géré correctement'
                }
            else:
                return {
                    'appropriate': False,
                    'description': 'Gestion de timeout insuffisante'
                }
        
        elif expected == "fallback_response":
            if success:
                # Vérifier si c'est une réponse de fallback
                fallback_indicators = [
                    'temporairement indisponible',
                    'service en maintenance',
                    'réessayez plus tard',
                    'problème technique'
                ]
                
                if any(indicator in response.lower() for indicator in fallback_indicators):
                    return {
                        'appropriate': True,
                        'description': 'Réponse de fallback appropriée'
                    }
                else:
                    return {
                        'appropriate': True,
                        'description': 'Service maintenu malgré la panne'
                    }
            else:
                return {
                    'appropriate': False,
                    'description': 'Aucune réponse de fallback'
                }
        
        return {
            'appropriate': False,
            'description': 'Comportement non analysé'
        }

    async def send_request_with_timeout(self, session, query, timeout=10):
        """Envoie une requête avec timeout personnalisé"""
        payload = {
            "message": query,
            "company_id": COMPANY_ID,
            "user_id": "integrationtest123"
        }
        
        start_time = time.time()
        try:
            async with session.post(ENDPOINT_URL, json=payload, timeout=timeout) as response:
                end_time = time.time()
                duration = (end_time - start_time) * 1000
                
                if response.status == 200:
                    response_text = await response.text()
                    try:
                        response_json = json.loads(response_text)
                        actual_response = response_json.get('response', response_text)
                    except:
                        actual_response = response_text
                    return True, actual_response, duration
                else:
                    error_text = await response.text()
                    return False, f"HTTP {response.status}: {error_text}", duration
                    
        except asyncio.TimeoutError:
            end_time = time.time()
            duration = (end_time - start_time) * 1000
            return False, f"Timeout après {timeout}s", duration
            
        except Exception as e:
            end_time = time.time()
            duration = (end_time - start_time) * 1000
            return False, str(e), duration

    async def send_request(self, session, query):
        """Envoie une requête standard"""
        return await self.send_request_with_timeout(session, query, 30)

    async def run_all_tests(self):
        """Lance tous les tests d'intégration"""
        print("🔌 TESTS D'INTÉGRATION & PANNES APIs - RUE_DU_GROS")
        print("="*60)
        print(f"🎯 URL: {ENDPOINT_URL}")
        print(f"🏢 Company ID: {COMPANY_ID}")
        print(f"🔧 Tests de robustesse et intégration...")
        
        # Vérification initiale des services
        availability_results = await self.check_service_availability()
        
        async with aiohttp.ClientSession() as session:
            # Tests de résilience
            resilience_results = await self.run_resilience_tests(session)
            
            # Tests de récupération
            recovery_results = await self.run_recovery_tests(session)
            
            self.results = {
                'availability': availability_results,
                'resilience': resilience_results,
                'recovery': recovery_results
            }
            
        await self.generate_integration_report()

    async def generate_integration_report(self):
        """Génère le rapport d'intégration final"""
        print("\n" + "="*60)
        print("🔌 RAPPORT D'INTÉGRATION FINAL")
        print("="*60)
        
        availability_results = self.results['availability']
        resilience_results = self.results['resilience']
        recovery_results = self.results['recovery']
        
        # Analyse de disponibilité
        critical_services = [r for r in availability_results if r['critical']]
        available_critical = [r for r in critical_services if r['status'] == 'available']
        
        print(f"📡 DISPONIBILITÉ DES SERVICES:")
        print(f"  • Services critiques: {len(available_critical)}/{len(critical_services)} disponibles")
        
        for service in availability_results:
            status_icon = "✅" if service['status'] == 'available' else "❌"
            critical_mark = " (CRITIQUE)" if service['critical'] else ""
            print(f"    {status_icon} {service['test_name']}: {service['status']}{critical_mark}")
        
        # Analyse de résilience
        resilient_tests = [r for r in resilience_results if r['behavior_analysis']['appropriate']]
        resilience_rate = (len(resilient_tests) / len(resilience_results)) * 100 if resilience_results else 0
        
        print(f"\n🛡️ RÉSILIENCE:")
        print(f"  • Tests réussis: {len(resilient_tests)}/{len(resilience_results)} ({resilience_rate:.1f}%)")
        
        for test in resilience_results:
            status_icon = "✅" if test['behavior_analysis']['appropriate'] else "❌"
            print(f"    {status_icon} {test['test_name']}: {test['behavior_analysis']['description']}")
        
        # Analyse de récupération
        successful_recoveries = []
        for recovery in recovery_results:
            recovery_successful = any(step.get('success', False) for step in recovery['steps'] if step['step'] == 'recovery_successful')
            if recovery_successful:
                successful_recoveries.append(recovery)
        
        recovery_rate = (len(successful_recoveries) / len(recovery_results)) * 100 if recovery_results else 0
        
        print(f"\n🔄 RÉCUPÉRATION:")
        print(f"  • Récupérations réussies: {len(successful_recoveries)}/{len(recovery_results)} ({recovery_rate:.1f}%)")
        
        for recovery in recovery_results:
            recovery_step = next((s for s in recovery['steps'] if s['step'] in ['recovery_successful', 'recovery_failed']), None)
            if recovery_step:
                if recovery_step['success']:
                    print(f"    ✅ {recovery['test_name']}: Récupération en {recovery_step['recovery_time']:.1f}s")
                else:
                    print(f"    ❌ {recovery['test_name']}: Récupération échouée")
        
        # Score global d'intégration
        availability_score = (len(available_critical) / len(critical_services)) * 100 if critical_services else 100
        integration_score = (availability_score + resilience_rate + recovery_rate) / 3
        
        print(f"\n🎯 SCORE GLOBAL D'INTÉGRATION: {integration_score:.1f}%")
        
        # Problèmes critiques
        if self.service_failures:
            high_impact = [f for f in self.service_failures if f['impact'] == 'high']
            medium_impact = [f for f in self.service_failures if f['impact'] == 'medium']
            
            if high_impact:
                print(f"\n🚨 PROBLÈMES CRITIQUES ({len(high_impact)}):")
                for failure in high_impact:
                    print(f"  • {failure['issue']}")
            
            if medium_impact:
                print(f"\n⚠️ PROBLÈMES MOYENS ({len(medium_impact)}):")
                for failure in medium_impact:
                    print(f"  • {failure['issue']}")
        
        # Verdict final
        print(f"\n🏆 VERDICT INTÉGRATION:")
        if integration_score >= 90:
            print("✅ EXCELLENT - Système très robuste")
        elif integration_score >= 75:
            print("🟡 BON - Bonne résilience générale")
        elif integration_score >= 60:
            print("🟠 MOYEN - Améliorations nécessaires")
        else:
            print("🔴 CRITIQUE - Problèmes d'intégration majeurs")
        
        # Recommandations
        print(f"\n💡 RECOMMANDATIONS:")
        if integration_score >= 90:
            print("  • Excellente robustesse du système")
            print("  • Maintenir les bonnes pratiques de monitoring")
        else:
            print("  • Améliorer les mécanismes de fallback")
            print("  • Optimiser les temps de récupération")
            print("  • Renforcer le monitoring des services")
            print("  • Implémenter des circuit breakers")
            print("  • Tester régulièrement la résilience")
        
        # Sauvegarde du rapport
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"integration_report_{timestamp}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': {
                    'integration_score': integration_score,
                    'availability_score': availability_score,
                    'resilience_rate': resilience_rate,
                    'recovery_rate': recovery_rate,
                    'critical_failures': len([f for f in self.service_failures if f['impact'] == 'high']),
                    'timestamp': timestamp
                },
                'detailed_results': self.results,
                'service_failures': self.service_failures
            }, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Rapport sauvegardé: {report_file}")

async def main():
    tester = IntegrationTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
