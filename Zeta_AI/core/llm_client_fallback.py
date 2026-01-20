#!/usr/bin/env python3
"""
Client LLM avec fallback automatique Groq → DeepSeek
Gère les surcharges 503 et limites 429 de manière transparente
"""

import os
import time
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict

class LLMFallbackManager:
    def __init__(self):
        self.groq_blocked_until = None  # Timestamp de déblocage Groq
        self.groq_retry_delay = 600  # 10 minutes entre retry Groq
        self.consecutive_groq_failures = 0
        self.max_groq_failures = 3  # Après 3 échecs, attendre plus longtemps
        
    def is_groq_available(self) -> bool:
        """Vérifie si Groq est disponible pour retry"""
        if self.groq_blocked_until is None:
            return True
        return datetime.now() > self.groq_blocked_until
    
    def block_groq_temporarily(self):
        """Bloque Groq temporairement après échec"""
        self.consecutive_groq_failures += 1
        
        # Backoff exponentiel
        if self.consecutive_groq_failures <= 3:
            delay = self.groq_retry_delay  # 10 min
        else:
            delay = self.groq_retry_delay * 2  # 20 min après 3 échecs
            
        self.groq_blocked_until = datetime.now() + timedelta(seconds=delay)
        print(f"🚫 [FALLBACK] Groq bloqué jusqu'à {self.groq_blocked_until.strftime('%H:%M:%S')}")
    
    def reset_groq_failures(self):
        """Reset compteur après succès Groq"""
        self.consecutive_groq_failures = 0
        self.groq_blocked_until = None

# Instance globale
fallback_manager = LLMFallbackManager()

async def complete_with_fallback(prompt: str,
                                model_name: Optional[str] = None,
                                max_tokens: int = 600,
                                temperature: float = 0.7,
                                prefer_groq: bool = False) -> Tuple[str, Dict]:
    """
    Appel LLM avec stratégie adaptative :
    - Par défaut : DeepSeek (stable)
    - Si prefer_groq=True : Groq puis fallback DeepSeek
    Retourne: (response_text, token_info)
    """
    
    # STRATÉGIE : DeepSeek PRIMARY sauf si Groq explicitement demandé
    if not prefer_groq:
        # 1. DEEPSEEK DIRECT (STRATÉGIE STABLE)
        try:
            print(f"🟢 [STABLE] Utilisation DeepSeek (primary)...")
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
                "fallback_used": False,
                "estimated": True,
                "strategy": "primary"
            }
            
            print(f"✅ [STABLE] DeepSeek réussi - ~{token_info['total_tokens']} tokens (estimé)")
            return response, token_info
            
        except Exception as e:
            print(f"❌ [STABLE] DeepSeek échec: {e} - Tentative Groq...")
            # Fallback vers Groq si DeepSeek échoue
    
    # 2. ESSAYER GROQ (si disponible ou si DeepSeek a échoué)
    if fallback_manager.is_groq_available():
        try:
            print(f"🚀 [FALLBACK] Tentative Groq...")
            from core.llm_client_groq import complete as groq_complete
            
            response, token_info = await groq_complete(
                prompt, model_name, max_tokens, temperature
            )
            
            # Succès Groq
            fallback_manager.reset_groq_failures()
            token_info["provider"] = "groq"
            token_info["fallback_used"] = False
            print(f"✅ [FALLBACK] Groq réussi - {token_info.get('total_tokens', 0)} tokens")
            return response, token_info
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Analyser le type d'erreur
            if "503" in error_msg or "over capacity" in error_msg:
                print(f"🚫 [FALLBACK] Groq 503 (surcharge) - Fallback DeepSeek")
                fallback_manager.block_groq_temporarily()
            elif "429" in error_msg:
                print(f"🚫 [FALLBACK] Groq 429 (rate limit) - Fallback DeepSeek")
                fallback_manager.block_groq_temporarily()
            else:
                print(f"🚫 [FALLBACK] Groq erreur: {e} - Fallback DeepSeek")
                # Pas de blocage pour autres erreurs
    else:
        print(f"⏰ [FALLBACK] Groq bloqué jusqu'à {fallback_manager.groq_blocked_until.strftime('%H:%M:%S')} - DeepSeek direct")
    
    # 2. FALLBACK DEEPSEEK
    try:
        print(f"🔄 [FALLBACK] Utilisation DeepSeek...")
        from core.llm_client_deepseek import complete as deepseek_complete
        
        # DeepSeek retourne juste le texte, pas les tokens
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
            "fallback_used": True,
            "estimated": True
        }
        
        print(f"✅ [FALLBACK] DeepSeek réussi - ~{token_info['total_tokens']} tokens (estimé)")
        return response, token_info
        
    except Exception as e:
        print(f"❌ [FALLBACK] DeepSeek ÉCHEC: {e}")
        
        # Dernière tentative: réponse d'urgence
        emergency_response = "Bonjour ! 👋 Envoyez-moi la photo du produit que vous voulez commander."
        token_info = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "model": "emergency",
            "provider": "emergency",
            "fallback_used": True,
            "error": str(e)
        }
        
        print(f"🆘 [FALLBACK] Réponse d'urgence utilisée")
        return emergency_response, token_info

# Alias pour compatibilité avec le code existant
complete = complete_with_fallback
