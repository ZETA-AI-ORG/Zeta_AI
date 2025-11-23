from config import GROK_API_KEY, GROK_API_URL, GROQ_API_KEY, GROQ_API_URL
import httpx
import json
import logging
import asyncio
from typing import Optional, Dict, Any
from .rate_limiter import rate_limited_llm_call
from .circuit_breaker import protected_groq_call

class GroqLLMClient:
    """
    Wrapper pour appels LLM Groq (multi-modèle, compatible agent hybride).
    """
    def __init__(self, api_key=None, api_url=None):
        from config import GROK_API_KEY, GROK_API_URL, GROQ_API_KEY, GROQ_API_URL
        # Support both alias and canonical names
        self.api_key = api_key or GROQ_API_KEY or GROK_API_KEY
        self.api_url = api_url or GROQ_API_URL or GROK_API_URL

    async def complete(self, prompt: str, model_name: str = "llama-3.3-70b-versatile", temperature: float = 0.2, max_tokens: int = 100) -> str:
        import httpx
        from utils import log3
        
        # Wrapper avec rate limiting
        async def _make_request():
            # Normalize/alias model names to Groq-supported identifiers
            model_aliases = {
                # legacy/common aliases -> groq canonical
                "llama3-8b-8192": "llama-3.1-8b-instant",
                "llama3-70b-8192": "llama-3.3-70b-versatile",
                "llama-3-8b": "llama-3.1-8b-instant",
                "llama-3-70b": "llama-3.3-70b-versatile",
                "gemma-7b-it": "llama-3.1-8b-instant",
            }
            canonical_model = model_aliases.get(model_name, model_name)
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            # Validation du prompt
            if not prompt or not prompt.strip() or len(prompt.strip()) < 3:
                log3("[LLM][BYPASS][ERROR] Prompt vide/trop court, injection prompt minimaliste", str(prompt))
                validated_prompt = "Merci pour votre confirmation."
            elif len(prompt) > 16000:
                log3("[LLM][ERROR] Prompt trop long, tronqué", prompt[:200] + " ...")
                validated_prompt = prompt[:16000]
            else:
                validated_prompt = prompt
                
            payload = {
                "model": canonical_model,
                "messages": [
                    {"role": "user", "content": validated_prompt}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            # Log réduit - seulement le modèle et la taille
            log3("[LLM]", f"Groq {payload['model']} | {len(str(payload))} chars")
            
            async with httpx.AsyncClient() as client:
                resp = await client.post(self.api_url, json=payload, headers=headers, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                response_text = data["choices"][0]["message"]["content"].strip()
                
                # Extraire les tokens usage si disponible
                usage = data.get("usage", {})
                if usage:
                    log3("[LLM][TOKENS]", f"{usage.get('prompt_tokens', 0)} + {usage.get('completion_tokens', 0)} = {usage.get('total_tokens', 0)} tokens")
                
                # Retourner réponse + usage
                return {"response": response_text, "usage": usage, "model": canonical_model}
        
        # Fallback intelligent AVANT rate limiting pour éviter circuit breaker
        async def _make_request_with_fallback():
            try:
                return await _make_request()
            except httpx.HTTPStatusError as e:
                status = getattr(e.response, "status_code", None)
                body = getattr(e.response, "text", "")
                log3("[LLM][HTTP ERROR]", f"Status: {status}, Body: {body}")
                
                if status in [400, 429] and model_name != "llama-3.1-8b-instant":
                    # Étape 1: Si on était sur 70B, essayer GPT-OSS-120B DIRECTEMENT avec délai augmenté
                    if model_name == "llama-3.3-70b-versatile":
                        log3("[LLM][FALLBACK]", "70B épuisé, attente 5s puis GPT-OSS-120B")
                        await asyncio.sleep(5)  # Délai augmenté pour éviter rate limiting
                        return await self._direct_llm_call(prompt, "openai/gpt-oss-120b", temperature, max_tokens)
                    
                    # Étape 2: Si on était sur GPT-OSS-120B, passer au 8B avec délai augmenté
                    elif model_name == "openai/gpt-oss-120b":
                        log3("[LLM][FALLBACK]", "GPT-OSS épuisé, attente 3s puis 8B")
                        await asyncio.sleep(3)
                        return await self._direct_llm_call(prompt, "llama-3.1-8b-instant", temperature, max_tokens)
                    
                    # Étape 3: Pour autres modèles, passer au 8B avec délai augmenté
                    else:
                        log3("[LLM][FALLBACK]", "Modèle épuisé, attente 3s puis 8B")
                        await asyncio.sleep(3)
                        return await self._direct_llm_call(prompt, "llama-3.1-8b-instant", temperature, max_tokens)
                
                # Re-raise si pas de fallback applicable
                raise e

        # Exécution avec rate limiting ET fallback intégré
        try:
            return await rate_limited_llm_call(_make_request_with_fallback, user_id="groq_client")
        except Exception as e:
            log3("[GroqLLMClient][EXCEPTION]", str(e))
            return f"[Erreur LLM] Exception: {str(e)}"
    
    async def _direct_llm_call(self, prompt: str, model_name: str, temperature: float = 0.2, max_tokens: int = 100) -> str:
        """Appel LLM direct sans rate limiting pour fallback"""
        import httpx
        
        # Normalize/alias model names
        model_aliases = {
            "llama3-8b-8192": "llama-3.1-8b-instant",
            "llama3-70b-8192": "llama-3.3-70b-versatile",
            "llama-3-8b": "llama-3.1-8b-instant",
            "llama-3-70b": "llama-3.3-70b-versatile",
            "gemma-7b-it": "llama-3.1-8b-instant",
        }
        canonical_model = model_aliases.get(model_name, model_name)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": canonical_model,
            "messages": [
                {"role": "system", "content": "Tu es un assistant expert."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.api_url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()


_global_llm_client: Optional[GroqLLMClient] = None


def get_llm_client() -> GroqLLMClient:
    """Retourne un singleton GroqLLMClient pour les modules utilitaires (ex: InterventionGuardian)."""
    global _global_llm_client
    if _global_llm_client is None:
        _global_llm_client = GroqLLMClient()
    return _global_llm_client

async def complete(prompt: str, model_name: str = "llama-3.1-8b-instant", temperature: float = 0.2, max_tokens: int = 512) -> str:
    """
    Appel asynchrone à Groq avec rate limiting intégré
    """
    from utils import log3
    
    # Fonction complete avec rate limiting
    async def _rate_limited_complete():
        prompt_lines = prompt.splitlines()
        to_show = '\n'.join(prompt_lines[:3]) + ('\n ...' if len(prompt_lines) > 3 else '')
        log3("Prompt", prompt)
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY or GROK_API_KEY}",
            "Content-Type": "application/json"
        }
        # Normalize/alias model names
        model_aliases = {
            "llama3-8b-8192": "llama-3.1-8b-instant",
            "llama3-70b-8192": "llama-3.3-70b-versatile",
            "llama-3-8b": "llama-3.1-8b-instant",
            "llama-3-70b": "llama-3.3-70b-versatile",
            "gemma-7b-it": "llama-3.1-8b-instant",
        }
        canonical_model = model_aliases.get(model_name, model_name)
        payload = {
            "model": canonical_model,
            "messages": [
                {"role": "system", "content": "Tu es un assistant expert."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        print(f" [LLM] Envoi requête vers {GROQ_API_URL or GROK_API_URL}")
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(GROQ_API_URL or GROK_API_URL, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            response_text = data["choices"][0]["message"]["content"].strip()
            print(f" [LLM] Réponse reçue")
            log3("Réponse LLM", response_text)
            return response_text
    
    # Fonction helper pour fallback avec modèle spécifique
    async def _rate_limited_complete_with_model(fallback_model: str):
        prompt_lines = prompt.splitlines()
        to_show = '\n'.join(prompt_lines[:3]) + ('\n ...' if len(prompt_lines) > 3 else '')
        log3("Prompt", prompt)
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY or GROK_API_KEY}",
            "Content-Type": "application/json"
        }
        # Normalize/alias model names
        model_aliases = {
            "llama3-8b-8192": "llama-3.1-8b-instant",
            "llama3-70b-8192": "llama-3.3-70b-versatile",
            "llama-3-8b": "llama-3.1-8b-instant",
            "llama-3-70b": "llama-3.3-70b-versatile",
            "gemma-7b-it": "llama-3.1-8b-instant",
        }
        canonical_model = model_aliases.get(fallback_model, fallback_model)
        payload = {
            "model": canonical_model,
            "messages": [
                {"role": "system", "content": "Tu es un assistant expert."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        print(f" [LLM] Envoi requête vers {GROQ_API_URL or GROK_API_URL}")
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(GROQ_API_URL or GROK_API_URL, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            response_text = data["choices"][0]["message"]["content"].strip()
            print(f" [LLM] Réponse reçue")
            log3("Réponse LLM", response_text)
            return response_text

    # Appel avec rate limiting et circuit breaker + fallback intelligent
    try:
        return await protected_groq_call(
            lambda: rate_limited_llm_call(_rate_limited_complete, user_id="global_complete")
        )
    except Exception as e:
        error_str = str(e)
        
        # Détection erreur 429 (quotas épuisés) - FALLBACK IMMÉDIAT
        if "429" in error_str or "rate_limit" in error_str.lower() or "quota" in error_str.lower():
            log3("[LLM][FALLBACK]", "70B épuisé, fallback direct GPT-OSS-120B")
            try:
                # FALLBACK DIRECT sans rate limiter pour éviter blocage
                llm_client = LLMClient()
                return await llm_client._direct_llm_call(prompt, "openai/gpt-oss-120b", temperature, max_tokens)
            except Exception as e2:
                log3("[LLM][FALLBACK]", f"GPT-OSS-120B échoué: {e2}")
                try:
                    # Dernier recours: 8B DIRECT
                    return await llm_client._direct_llm_call(prompt, "llama-3.1-8b-instant", temperature, max_tokens)
                except Exception as e3:
                    log3("[LLM][FALLBACK]", f"Tous les modèles échoués: {e3}")
                    # Retour message d'erreur au lieu d'exception - OPTIMISÉ
                    return "Système temporairement surchargé. Réponse partielle disponible."
        else:
            # Autres erreurs, pas de fallback
            print(f"[LLM] Erreur: {type(e).__name__}")
            log3("[LLM][ERROR]", str(e))
            return f"[Erreur LLM] {str(e)}"

from utils import timing_metric

@timing_metric("embedding_generation")
async def embed_text_hf(text: str, model_name: str = "mpnet-base-v2") -> list:
    """
    Encode un texte en embedding via Hugging Face (sentence-transformers).
    """
    # Début embedding silencieux
    # Génération embedding silencieuse
    
    try:
        model = get_embedding_model(model_name)
        print(f" [EMBEDDING] Modèle chargé, encoding en cours...")
        embedding = model.encode([text])[0].tolist()
        # Embedding généré
        return embedding
    except Exception as e:
        print(f"[EMBEDDING] Erreur: {type(e).__name__}")
        raise