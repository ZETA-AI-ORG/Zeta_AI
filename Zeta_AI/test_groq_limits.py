#!/usr/bin/env python3
"""
Test d'épuisement des quotas Groq Free Tier
Objectif: Découvrir les vraies limites en production
"""

import os
import time
import json
from datetime import datetime
from core.llm_client_groq import complete as groq_complete

class GroqLimitTester:
    def __init__(self):
        self.start_time = datetime.now()
        self.request_count = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_tokens = 0
        self.errors = []
        self.last_success_time = None
        
        # Logs
        self.log_file = f"groq_test_{self.start_time.strftime('%Y%m%d_%H%M%S')}.log"
        
    def log(self, message):
        """Log avec timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_line = f"[{timestamp}] {message}"
        print(log_line)
        
        # Sauvegarder dans fichier
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
    
    async def test_single_request(self):
        """Test une requête simple"""
        try:
            # Message court pour minimiser les tokens
            test_prompt = "Réponds juste 'OK' en 1 mot."
            
            # Appel Groq
            response, token_info = await groq_complete(
                test_prompt,
                model_name="llama-3.3-70b-versatile",
                max_tokens=10,
                temperature=0.1
            )
            
            # Extraire les tokens réels
            input_tokens = token_info.get("prompt_tokens", 0)
            output_tokens = token_info.get("completion_tokens", 0)
            total_req_tokens = token_info.get("total_tokens", 0)
            
            # Compteurs
            self.request_count += 1
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            self.total_tokens += total_req_tokens
            self.last_success_time = datetime.now()
            
            # Log succès
            self.log(f"Requête #{self.request_count} - {total_req_tokens} tokens - OK - Réponse: '{response[:20]}...'")
            
            return True
            
        except Exception as e:
            # Erreur détectée
            error_msg = str(e)
            self.errors.append({
                "request_number": self.request_count + 1,
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            })
            
            self.log(f"ERREUR Requête #{self.request_count + 1}: {error_msg}")
            return False
    
    async def run_test(self, delay_seconds=2.1):
        """Lance le test d'épuisement"""
        self.log("🧪 DÉBUT TEST D'ÉPUISEMENT GROQ - MODE CONTINU")
        self.log(f"Modèle: llama-3.3-70b-versatile")
        self.log(f"Délai entre requêtes: {delay_seconds}s (29 RPM max)")
        self.log("=" * 50)
        
        try:
            while True:
                # Test une requête
                success = await self.test_single_request()
                
                if not success:
                    # Première erreur = arrêt
                    break
                
                # Délai pour éviter le spam
                time.sleep(delay_seconds)
                
                # Log de progression toutes les 50 requêtes (plus fréquent)
                if self.request_count % 50 == 0:
                    elapsed = datetime.now() - self.start_time
                    tokens_per_hour = (self.total_tokens / elapsed.total_seconds()) * 3600 if elapsed.total_seconds() > 0 else 0
                    self.log(f"📊 Progression: {self.request_count} requêtes | {self.total_tokens} tokens | {tokens_per_hour:.0f} tokens/h")
        
        except KeyboardInterrupt:
            self.log("⚠️ Test interrompu par l'utilisateur")
        
        # Rapport final
        self.generate_report()
    
    def generate_report(self):
        """Génère le rapport final"""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        self.log("=" * 50)
        self.log("🏁 RAPPORT FINAL")
        self.log("=" * 50)
        
        # Statistiques principales
        self.log(f"📊 Requêtes réussies: {self.request_count}")
        self.log(f"⏱️ Durée totale: {duration}")
        self.log(f"🔢 Tokens input: {self.total_input_tokens}")
        self.log(f"🔢 Tokens output: {self.total_output_tokens}")
        self.log(f"🔢 Tokens TOTAL: {self.total_tokens}")
        
        # Moyennes
        if self.request_count > 0:
            avg_tokens = self.total_tokens / self.request_count
            req_per_minute = self.request_count / (duration.total_seconds() / 60)
            self.log(f"📈 Moyenne tokens/requête: {avg_tokens:.1f}")
            self.log(f"📈 Requêtes/minute: {req_per_minute:.1f}")
        
        # Erreurs
        if self.errors:
            self.log(f"❌ Première erreur: {self.errors[0]['error']}")
            
            # Détection type d'erreur
            error_msg = self.errors[0]['error'].lower()
            if "429" in error_msg or "rate limit" in error_msg:
                self.log("🚦 Type: RATE LIMIT (quota épuisé)")
            elif "503" in error_msg or "capacity" in error_msg:
                self.log("🚦 Type: OVER CAPACITY (serveur surchargé)")
            else:
                self.log("🚦 Type: AUTRE ERREUR")
        
        # Estimation reset
        if self.last_success_time:
            # Les quotas Groq se reset généralement toutes les 24h
            next_reset = self.last_success_time.replace(hour=0, minute=0, second=0, microsecond=0)
            next_reset = next_reset.replace(day=next_reset.day + 1)
            self.log(f"🔄 Prochain reset estimé: {next_reset}")
        
        # Sauvegarde JSON
        report_data = {
            "start_time": self.start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration.total_seconds(),
            "successful_requests": self.request_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "errors": self.errors,
            "model": "llama-3.3-70b-versatile"
        }
        
        json_file = f"groq_report_{self.start_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        self.log(f"💾 Rapport sauvegardé: {json_file}")

async def main():
    """Point d'entrée principal"""
    print("🧪 TEST D'ÉPUISEMENT GROQ FREE TIER")
    print("Appuyez sur Ctrl+C pour arrêter manuellement")
    print()
    
    # Vérifier la clé API
    if not os.getenv("GROQ_API_KEY"):
        print("❌ ERREUR: GROQ_API_KEY manquante dans l'environnement")
        return
    
    # Lancer le test
    tester = GroqLimitTester()
    await tester.run_test(delay_seconds=2.1)  # 29 requêtes/minute (60s ÷ 29 = 2.07s)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
