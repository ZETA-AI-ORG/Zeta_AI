#!/usr/bin/env python3
"""
Test de validation du fallback LLM corrigé
Test léger pour vérifier que le fallback fonctionne sous charge réduite
"""

import asyncio
import httpx
import time
import json
from datetime import datetime

# Configuration test réduit
NUM_USERS = 5  # Réduit de 50 à 5
DURATION = 30  # Réduit de 300s à 30s
RAMP_UP = 5   # Réduit de 30s à 5s
BASE_URL = "http://127.0.0.1:8001"

class FallbackTester:
    def __init__(self):
        self.results = []
        self.start_time = None
        
    async def send_request(self, user_id: int, session: httpx.AsyncClient):
        """Envoie une requête et capture les détails de la réponse"""
        try:
            start = time.time()
            
            payload = {
                "message": f"Utilisateur {user_id}: Explique-moi les avantages du commerce équitable",
                "company_id": "MpfnlSbqwaZ6F4HvxQLRL9du0yG3",
                "user_id": "testuser123"
            }
            
            response = await session.post(
                f"{BASE_URL}/chat",
                json=payload,
                timeout=45.0
            )
            
            duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get("response", "")
                
                # Détection du modèle utilisé
                model_used = "UNKNOWN"
                if "difficultés techniques" in response_text:
                    model_used = "FALLBACK_ERROR"
                elif len(response_text) > 200:  # Réponse complète
                    model_used = "SUCCESS"
                else:
                    model_used = "PARTIAL"
                    
                self.results.append({
                    "user_id": user_id,
                    "status": "success",
                    "duration": duration,
                    "model_used": model_used,
                    "response_length": len(response_text),
                    "timestamp": time.time() - self.start_time
                })
                
                print(f"✅ User {user_id}: {model_used} ({duration:.1f}s)")
                
            else:
                self.results.append({
                    "user_id": user_id,
                    "status": "error",
                    "status_code": response.status_code,
                    "duration": duration,
                    "timestamp": time.time() - self.start_time
                })
                print(f"❌ User {user_id}: HTTP {response.status_code} ({duration:.1f}s)")
                
        except Exception as e:
            duration = time.time() - start if 'start' in locals() else 0
            self.results.append({
                "user_id": user_id,
                "status": "exception",
                "error": str(e),
                "duration": duration,
                "timestamp": time.time() - self.start_time
            })
            print(f"💥 User {user_id}: {str(e)[:50]}... ({duration:.1f}s)")

    async def user_simulation(self, user_id: int):
        """Simule un utilisateur envoyant plusieurs requêtes"""
        async with httpx.AsyncClient() as session:
            # Chaque utilisateur envoie 3 requêtes avec pause
            for i in range(3):
                await self.send_request(user_id, session)
                if i < 2:  # Pause entre requêtes
                    await asyncio.sleep(2)

    async def run_test(self):
        """Lance le test de fallback"""
        print("🔥 TEST DE VALIDATION FALLBACK LLM")
        print(f"👥 Utilisateurs: {NUM_USERS}")
        print(f"⏱️ Durée: {DURATION}s")
        print(f"📈 Montée en charge: {RAMP_UP}s")
        print(f"🎯 URL: {BASE_URL}/chat")
        print("=" * 60)
        
        self.start_time = time.time()
        tasks = []
        
        # Démarrage échelonné des utilisateurs
        for user_id in range(NUM_USERS):
            delay = (user_id * RAMP_UP) / NUM_USERS
            task = asyncio.create_task(self.delayed_user(user_id, delay))
            tasks.append(task)
            
        # Attendre que tous les utilisateurs terminent
        await asyncio.gather(*tasks)
        
        # Analyse des résultats
        self.analyze_results()

    async def delayed_user(self, user_id: int, delay: float):
        """Démarre un utilisateur après un délai"""
        await asyncio.sleep(delay)
        print(f"🚀 Utilisateur {user_id} démarré (après {delay:.1f}s)")
        await self.user_simulation(user_id)
        print(f"🏁 Utilisateur {user_id} terminé")

    def analyze_results(self):
        """Analyse les résultats du test"""
        print("\n" + "=" * 60)
        print("📊 ANALYSE DES RÉSULTATS FALLBACK")
        print("=" * 60)
        
        total_requests = len(self.results)
        successes = [r for r in self.results if r["status"] == "success"]
        errors = [r for r in self.results if r["status"] == "error"]
        exceptions = [r for r in self.results if r["status"] == "exception"]
        
        success_rate = (len(successes) / total_requests * 100) if total_requests > 0 else 0
        
        print(f"✅ Requêtes réussies: {len(successes)}")
        print(f"❌ Erreurs HTTP: {len(errors)}")
        print(f"💥 Exceptions: {len(exceptions)}")
        print(f"📈 Taux de succès: {success_rate:.1f}%")
        
        if successes:
            durations = [r["duration"] for r in successes]
            avg_duration = sum(durations) / len(durations)
            print(f"⏱️ Temps réponse moyen: {avg_duration:.1f}s")
            
            # Analyse des modèles utilisés
            models = {}
            for r in successes:
                model = r.get("model_used", "UNKNOWN")
                models[model] = models.get(model, 0) + 1
                
            print(f"🤖 Modèles utilisés:")
            for model, count in models.items():
                print(f"  • {model}: {count} requêtes")
        
        # Analyse des erreurs
        if errors:
            status_codes = {}
            for r in errors:
                code = r.get("status_code", "unknown")
                status_codes[code] = status_codes.get(code, 0) + 1
            
            print(f"❌ Codes d'erreur:")
            for code, count in status_codes.items():
                print(f"  • {code}: {count} occurrences")
        
        # Verdict final
        if success_rate >= 80:
            print(f"\n🟢 FALLBACK VALIDÉ - Taux de succès: {success_rate:.1f}%")
        elif success_rate >= 50:
            print(f"\n🟡 FALLBACK PARTIEL - Taux de succès: {success_rate:.1f}%")
        else:
            print(f"\n🔴 FALLBACK DÉFAILLANT - Taux de succès: {success_rate:.1f}%")
        
        # Sauvegarde des résultats
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"fallback_test_results_{timestamp}.json"
        
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
                    "errors": len(errors),
                    "exceptions": len(exceptions),
                    "success_rate": success_rate
                },
                "results": self.results
            }, f, indent=2)
        
        print(f"💾 Résultats sauvegardés: {filename}")

if __name__ == "__main__":
    tester = FallbackTester()
    asyncio.run(tester.run_test())
