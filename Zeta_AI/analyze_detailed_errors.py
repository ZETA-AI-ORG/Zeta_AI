#!/usr/bin/env python3
"""
Analyse détaillée des erreurs du système de chatbot
Identifie les causes exactes des erreurs 429 et exceptions
"""

import asyncio
import httpx
import time
import json
from datetime import datetime
import traceback

# Configuration pour analyse détaillée
NUM_USERS = 3  # Très réduit pour analyse précise
DURATION = 60  # 1 minute
RAMP_UP = 10   # 10s
BASE_URL = "http://127.0.0.1:8001"

class DetailedErrorAnalyzer:
    def __init__(self):
        self.detailed_results = []
        self.error_patterns = {}
        self.start_time = None
        
    async def send_detailed_request(self, user_id: int, request_num: int, session: httpx.AsyncClient):
        """Envoie une requête avec capture détaillée des erreurs"""
        request_start = time.time()
        error_details = {
            "user_id": user_id,
            "request_num": request_num,
            "timestamp": time.time() - self.start_time,
            "status": "unknown",
            "error_type": None,
            "error_message": None,
            "response_headers": {},
            "request_duration": 0,
            "stack_trace": None
        }
        
        try:
            payload = {
                "message": f"Test détaillé {user_id}-{request_num}: Quels sont les avantages du commerce équitable?",
                "company_id": "MpfnlSbqwaZ6F4HvxQLRL9du0yG3",
                "user_id": "testuser123"
            }
            
            print(f"🔍 User {user_id} Req {request_num}: Envoi...")
            
            response = await session.post(
                f"{BASE_URL}/chat",
                json=payload,
                timeout=60.0  # Timeout plus long pour analyse
            )
            
            error_details["request_duration"] = time.time() - request_start
            error_details["response_headers"] = dict(response.headers)
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get("response", "")
                error_details["status"] = "success"
                error_details["response_length"] = len(response_text)
                
                # Analyse du contenu pour détecter les fallbacks
                if "difficultés techniques" in response_text:
                    error_details["fallback_used"] = "error_message"
                elif len(response_text) > 200:
                    error_details["fallback_used"] = "full_response"
                else:
                    error_details["fallback_used"] = "partial_response"
                    
                print(f"✅ User {user_id} Req {request_num}: SUCCESS ({error_details['request_duration']:.1f}s)")
                
            else:
                error_details["status"] = "http_error"
                error_details["error_type"] = f"HTTP_{response.status_code}"
                
                try:
                    error_body = response.text
                    error_details["error_message"] = error_body[:500]  # Limiter la taille
                except:
                    error_details["error_message"] = "Could not read response body"
                
                print(f"❌ User {user_id} Req {request_num}: HTTP {response.status_code} ({error_details['request_duration']:.1f}s)")
                
                # Analyse spécifique des erreurs 429
                if response.status_code == 429:
                    retry_after = response.headers.get('retry-after', 'unknown')
                    rate_limit_remaining = response.headers.get('x-ratelimit-remaining', 'unknown')
                    error_details["retry_after"] = retry_after
                    error_details["rate_limit_remaining"] = rate_limit_remaining
                    print(f"  📊 Retry-After: {retry_after}, Remaining: {rate_limit_remaining}")
                
        except asyncio.TimeoutError:
            error_details["request_duration"] = time.time() - request_start
            error_details["status"] = "timeout"
            error_details["error_type"] = "TimeoutError"
            error_details["error_message"] = f"Request timeout after {error_details['request_duration']:.1f}s"
            print(f"⏰ User {user_id} Req {request_num}: TIMEOUT ({error_details['request_duration']:.1f}s)")
            
        except httpx.ConnectError as e:
            error_details["request_duration"] = time.time() - request_start
            error_details["status"] = "connection_error"
            error_details["error_type"] = "ConnectError"
            error_details["error_message"] = str(e)
            error_details["stack_trace"] = traceback.format_exc()
            print(f"🔌 User {user_id} Req {request_num}: CONNECTION ERROR - {str(e)}")
            
        except httpx.ReadTimeout as e:
            error_details["request_duration"] = time.time() - request_start
            error_details["status"] = "read_timeout"
            error_details["error_type"] = "ReadTimeout"
            error_details["error_message"] = str(e)
            print(f"📖 User {user_id} Req {request_num}: READ TIMEOUT - {str(e)}")
            
        except Exception as e:
            error_details["request_duration"] = time.time() - request_start
            error_details["status"] = "exception"
            error_details["error_type"] = type(e).__name__
            error_details["error_message"] = str(e)
            error_details["stack_trace"] = traceback.format_exc()
            print(f"💥 User {user_id} Req {request_num}: EXCEPTION - {type(e).__name__}: {str(e)}")
        
        self.detailed_results.append(error_details)
        return error_details

    async def user_detailed_simulation(self, user_id: int):
        """Simule un utilisateur avec analyse détaillée"""
        async with httpx.AsyncClient() as session:
            for request_num in range(5):  # 5 requêtes par utilisateur
                await self.send_detailed_request(user_id, request_num, session)
                if request_num < 4:  # Pause entre requêtes
                    await asyncio.sleep(3)

    async def run_detailed_analysis(self):
        """Lance l'analyse détaillée des erreurs"""
        print("🔍 ANALYSE DÉTAILLÉE DES ERREURS")
        print(f"👥 Utilisateurs: {NUM_USERS}")
        print(f"⏱️ Durée: {DURATION}s")
        print(f"📈 Montée en charge: {RAMP_UP}s")
        print(f"🎯 URL: {BASE_URL}/chat")
        print("=" * 70)
        
        self.start_time = time.time()
        tasks = []
        
        # Démarrage échelonné des utilisateurs
        for user_id in range(NUM_USERS):
            delay = (user_id * RAMP_UP) / NUM_USERS
            task = asyncio.create_task(self.delayed_user_analysis(user_id, delay))
            tasks.append(task)
            
        # Attendre que tous les utilisateurs terminent
        await asyncio.gather(*tasks)
        
        # Analyse détaillée des résultats
        await self.analyze_detailed_results()

    async def delayed_user_analysis(self, user_id: int, delay: float):
        """Démarre un utilisateur après un délai"""
        await asyncio.sleep(delay)
        print(f"🚀 Utilisateur {user_id} démarré (après {delay:.1f}s)")
        await self.user_detailed_simulation(user_id)
        print(f"🏁 Utilisateur {user_id} terminé")

    async def analyze_detailed_results(self):
        """Analyse détaillée des résultats avec patterns d'erreurs"""
        print("\n" + "=" * 70)
        print("📊 ANALYSE DÉTAILLÉE DES ERREURS")
        print("=" * 70)
        
        # Statistiques générales
        total_requests = len(self.detailed_results)
        successes = [r for r in self.detailed_results if r["status"] == "success"]
        http_errors = [r for r in self.detailed_results if r["status"] == "http_error"]
        timeouts = [r for r in self.detailed_results if r["status"] == "timeout"]
        connection_errors = [r for r in self.detailed_results if r["status"] == "connection_error"]
        exceptions = [r for r in self.detailed_results if r["status"] == "exception"]
        
        print(f"📈 STATISTIQUES GÉNÉRALES:")
        print(f"  • Total requêtes: {total_requests}")
        print(f"  • Succès: {len(successes)} ({len(successes)/total_requests*100:.1f}%)")
        print(f"  • Erreurs HTTP: {len(http_errors)} ({len(http_errors)/total_requests*100:.1f}%)")
        print(f"  • Timeouts: {len(timeouts)} ({len(timeouts)/total_requests*100:.1f}%)")
        print(f"  • Erreurs connexion: {len(connection_errors)} ({len(connection_errors)/total_requests*100:.1f}%)")
        print(f"  • Exceptions: {len(exceptions)} ({len(exceptions)/total_requests*100:.1f}%)")
        
        # Analyse des erreurs HTTP détaillée
        if http_errors:
            print(f"\n🔍 ANALYSE ERREURS HTTP ({len(http_errors)}):")
            error_codes = {}
            for error in http_errors:
                code = error["error_type"]
                if code not in error_codes:
                    error_codes[code] = []
                error_codes[code].append(error)
            
            for code, errors in error_codes.items():
                print(f"  • {code}: {len(errors)} occurrences")
                if code == "HTTP_429":
                    print(f"    📊 Détails 429:")
                    for err in errors[:3]:  # Montrer 3 premiers
                        retry_after = err.get("retry_after", "unknown")
                        remaining = err.get("rate_limit_remaining", "unknown")
                        print(f"      - User {err['user_id']} Req {err['request_num']}: Retry-After={retry_after}, Remaining={remaining}")
                        print(f"        Message: {err['error_message'][:100]}...")
        
        # Analyse des timeouts
        if timeouts:
            print(f"\n⏰ ANALYSE TIMEOUTS ({len(timeouts)}):")
            timeout_durations = [t["request_duration"] for t in timeouts]
            avg_timeout = sum(timeout_durations) / len(timeout_durations)
            print(f"  • Durée moyenne avant timeout: {avg_timeout:.1f}s")
            print(f"  • Timeouts par utilisateur:")
            user_timeouts = {}
            for t in timeouts:
                user_id = t["user_id"]
                if user_id not in user_timeouts:
                    user_timeouts[user_id] = 0
                user_timeouts[user_id] += 1
            for user_id, count in user_timeouts.items():
                print(f"    - User {user_id}: {count} timeouts")
        
        # Analyse des exceptions
        if exceptions:
            print(f"\n💥 ANALYSE EXCEPTIONS ({len(exceptions)}):")
            exception_types = {}
            for exc in exceptions:
                exc_type = exc["error_type"]
                if exc_type not in exception_types:
                    exception_types[exc_type] = []
                exception_types[exc_type].append(exc)
            
            for exc_type, excs in exception_types.items():
                print(f"  • {exc_type}: {len(excs)} occurrences")
                for exc in excs[:2]:  # Montrer 2 premiers
                    print(f"    - User {exc['user_id']} Req {exc['request_num']}: {exc['error_message'][:100]}...")
                    if exc.get("stack_trace"):
                        print(f"      Stack trace: {exc['stack_trace'][:200]}...")
        
        # Analyse des temps de réponse
        if successes:
            durations = [s["request_duration"] for s in successes]
            avg_duration = sum(durations) / len(durations)
            min_duration = min(durations)
            max_duration = max(durations)
            print(f"\n⏱️ TEMPS DE RÉPONSE SUCCÈS:")
            print(f"  • Moyenne: {avg_duration:.1f}s")
            print(f"  • Min: {min_duration:.1f}s")
            print(f"  • Max: {max_duration:.1f}s")
            
            # Analyse des fallbacks utilisés
            fallback_types = {}
            for s in successes:
                fallback = s.get("fallback_used", "unknown")
                if fallback not in fallback_types:
                    fallback_types[fallback] = 0
                fallback_types[fallback] += 1
            
            print(f"  • Fallbacks utilisés:")
            for fallback, count in fallback_types.items():
                print(f"    - {fallback}: {count} fois")
        
        # Sauvegarde des résultats détaillés
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"detailed_error_analysis_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                "config": {
                    "num_users": NUM_USERS,
                    "duration": DURATION,
                    "ramp_up": RAMP_UP
                },
                "summary": {
                    "total_requests": total_requests,
                    "successes": len(successes),
                    "http_errors": len(http_errors),
                    "timeouts": len(timeouts),
                    "connection_errors": len(connection_errors),
                    "exceptions": len(exceptions)
                },
                "detailed_results": self.detailed_results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Analyse détaillée sauvegardée: {filename}")
        
        # Recommandations
        print(f"\n🎯 RECOMMANDATIONS:")
        if len(http_errors) > len(successes):
            print("  🔴 CRITIQUE: Plus d'erreurs HTTP que de succès")
            print("    → Vérifier les quotas API et rate limiting")
        if len(timeouts) > 0:
            print("  🟡 ATTENTION: Timeouts détectés")
            print("    → Optimiser les temps de réponse du serveur")
        if len(connection_errors) > 0:
            print("  🔴 CRITIQUE: Erreurs de connexion")
            print("    → Vérifier que le serveur est démarré et accessible")
        if len(exceptions) > 0:
            print("  🟠 PROBLÈME: Exceptions non gérées")
            print("    → Analyser les stack traces pour corriger le code")

if __name__ == "__main__":
    analyzer = DetailedErrorAnalyzer()
    asyncio.run(analyzer.run_detailed_analysis())
