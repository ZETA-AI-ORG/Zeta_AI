#!/usr/bin/env python3
"""
Health Check intelligent pour Groq
Test rapide avant chaque requête pour éviter les 503
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict
import os

class GroqHealthChecker:
    def __init__(self):
        self.last_check_time = None
        self.last_check_result = None
        self.check_cache_duration = 30  # Cache le résultat 30 secondes
        self.consecutive_failures = 0
        
    async def is_groq_healthy(self) -> bool:
        """
        Vérifie si Groq est disponible avec un test rapide
        Cache le résultat pour éviter trop de tests
        """
        now = datetime.now()
        
        # Utiliser le cache si récent
        if (self.last_check_time and 
            (now - self.last_check_time).total_seconds() < self.check_cache_duration):
            return self.last_check_result
        
        # Si pas de clé Groq, considérer Groq indisponible et ne jamais appeler l'API
        if not (os.getenv("GROQ_API_KEY") or "").strip():
            self.last_check_time = now
            self.last_check_result = False
            return False

        # Effectuer le health check
        try:
            print(f"🔍 [HEALTH] Test Groq...")
            start_time = time.time()
            
            from core.llm_client_groq import complete as groq_complete
            
            # Test ultra-rapide : 1 token max
            response, token_info = await asyncio.wait_for(
                groq_complete(
                    "Hi", 
                    model_name="llama-3.3-70b-versatile",
                    max_tokens=1,
                    temperature=0.1
                ),
                timeout=5.0  # Timeout 5 secondes
            )
            
            duration = time.time() - start_time
            
            # Succès
            self.last_check_time = now
            self.last_check_result = True
            self.consecutive_failures = 0
            
            print(f"✅ [HEALTH] Groq OK ({duration:.1f}s)")
            return True
            
        except asyncio.TimeoutError:
            print(f"⏰ [HEALTH] Groq timeout (>5s)")
            self._mark_failure()
            return False
            
        except Exception as e:
            error_msg = str(e).lower()
            
            if "503" in error_msg or "over capacity" in error_msg:
                print(f"🚫 [HEALTH] Groq 503 (surcharge)")
            elif "429" in error_msg:
                print(f"🚫 [HEALTH] Groq 429 (rate limit)")
            else:
                print(f"❌ [HEALTH] Groq erreur: {e}")
            
            self._mark_failure()
            return False
    
    def _mark_failure(self):
        """Marque un échec et ajuste le cache"""
        self.last_check_time = datetime.now()
        self.last_check_result = False
        self.consecutive_failures += 1
        
        # Augmenter le cache après échecs répétés
        if self.consecutive_failures >= 3:
            self.check_cache_duration = 120  # 2 minutes après 3 échecs
        elif self.consecutive_failures >= 2:
            self.check_cache_duration = 60   # 1 minute après 2 échecs
        else:
            self.check_cache_duration = 30   # 30s par défaut

# Instance globale
health_checker = GroqHealthChecker()

async def complete_with_health_check(prompt: str,
                                   model_name: Optional[str] = None,
                                   max_tokens: int = 600,
                                   temperature: float = 0.7) -> Tuple[str, Dict]:
    """
    Appel LLM avec health check préalable
    Groq si healthy, sinon DeepSeek directement
    """
    
    # 0) Si Groq est désactivé (pas de clé), basculer OpenRouter directement si possible
    if not (os.getenv("GROQ_API_KEY") or "").strip():
        try:
            from core.llm_client_openrouter import complete as openrouter_complete

            content, token_info = await openrouter_complete(
                prompt,
                model_name=model_name,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            token_info["provider"] = "openrouter"
            token_info["health_check"] = False
            token_info["fallback_used"] = True
            return content, token_info
        except Exception:
            # Si OpenRouter indisponible, on continue vers le fallback existant
            groq_healthy = False
    else:
        # 1. HEALTH CHECK GROQ
        groq_healthy = await health_checker.is_groq_healthy()
    
    if groq_healthy:
        # 2. ESSAYER GROQ (après validation health check)
        try:
            print(f"🚀 [SMART] Groq validé - requête réelle...")
            from core.llm_client_groq import complete as groq_complete
            
            response, token_info = await groq_complete(
                prompt, model_name, max_tokens, temperature
            )
            
            # Succès Groq
            token_info["provider"] = "groq"
            token_info["health_check"] = True
            token_info["fallback_used"] = False
            
            print(f"✅ [SMART] Groq réussi - {token_info.get('total_tokens', 0)} tokens")
            return response, token_info
            
        except Exception as e:
            print(f"🚫 [SMART] Groq échec malgré health check: {e}")
            # Marquer comme unhealthy pour les prochaines fois
            health_checker._mark_failure()
            # Continuer vers DeepSeek
    else:
        print(f"🔄 [SMART] Groq unhealthy - DeepSeek direct")
    
    # 3. FALLBACK DEEPSEEK
    try:
        print(f"🟢 [SMART] Utilisation DeepSeek...")
        from core.llm_client_deepseek import complete as deepseek_complete
        
        response = await deepseek_complete(
            prompt, 
            model_name="deepseek-chat", 
            max_tokens=max_tokens, 
            temperature=temperature
        )
        
        # Estimation tokens pour compatibilité
        estimated_input = len(prompt) // 4
        estimated_output = len(response) // 4
        
        token_info = {
            "prompt_tokens": estimated_input,
            "completion_tokens": estimated_output,
            "total_tokens": estimated_input + estimated_output,
            "model": "deepseek-chat",
            "provider": "deepseek",
            "health_check": not groq_healthy,
            "fallback_used": True,
            "estimated": True
        }
        
        print(f"✅ [SMART] DeepSeek réussi - ~{token_info['total_tokens']} tokens")
        return response, token_info
        
    except Exception as e:
        print(f"❌ [SMART] DeepSeek ÉCHEC: {e}")
        
        # Réponse d'urgence
        emergency_response = "Bonjour ! 👋 Envoyez-moi la photo du produit que vous voulez commander."
        token_info = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "model": "emergency",
            "provider": "emergency",
            "health_check": False,
            "fallback_used": True,
            "error": str(e)
        }
        
        print(f"🆘 [SMART] Réponse d'urgence")
        return emergency_response, token_info

# Alias pour compatibilité
complete = complete_with_health_check
