from config import GROK_API_KEY, GROK_API_URL, GROQ_API_KEY, GROQ_API_URL
import httpx
import json
import logging
import asyncio
from typing import Optional, Dict, Any
from .rate_limiter import rate_limited_llm_call
from .circuit_breaker import protected_groq_call
import os
from embedding_models import get_embedding_model

_global_llm_client: Optional[Any] = None

class OpenRouterLLMClient:
    """Adapter minimal pour utiliser OpenRouter via llm_client_openrouter avec une API .complete()."""

    async def complete(
        self,
        prompt: str,
        model_name: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 600,
        top_p: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
    ) -> Dict[str, Any]:
        from core.llm_client_openrouter import complete as openrouter_complete

        content, token_info = await openrouter_complete(
            prompt,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=float(top_p) if top_p is not None else 1.0,
            frequency_penalty=frequency_penalty,
        )
        return {"response": content, "usage": token_info, "model": token_info.get("model")}

class GroqLLMClient:
    """
    Wrapper pour appels LLM Groq (multi-modèle, compatible agent hybride).
    """
    def __init__(self, api_key=None, api_url=None):
        from config import GROK_API_KEY, GROK_API_URL, GROQ_API_KEY, GROQ_API_URL
        # Support both alias and canonical names
        self.api_key = api_key or GROQ_API_KEY or GROK_API_KEY
        self.api_url = api_url or GROQ_API_URL or GROK_API_URL

    async def complete(
        self,
        prompt: str,
        model_name: str = "llama-3.3-70b-versatile",
        temperature: float = 0.2,
        max_tokens: int = 100,
        top_p: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
    ) -> str:
        import httpx
        from utils import log3
        import traceback
        
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
            if top_p is not None:
                payload["top_p"] = float(top_p)
            if frequency_penalty is not None:
                try:
                    payload["frequency_penalty"] = float(frequency_penalty)
                except Exception:
                    pass
            # Log réduit - seulement le modèle et la taille
            log3("[LLM]", f"Groq {payload['model']} | {len(str(payload))} chars")

            debug_callers = os.getenv("BOTLIVE_DEBUG_LLM_CALLERS", "false").strip().lower() in {
                "1",
                "true",
                "yes",
                "y",
                "on",
            }
            if debug_callers:
                try:
                    stack = "".join(traceback.format_stack(limit=20))
                    log3("[LLM][CALLER_STACK]", stack, max_lines=40, max_length=4000)
                except Exception:
                    pass
            
            async with httpx.AsyncClient() as client:
                resp = await client.post(self.api_url, json=payload, headers=headers, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                response_text = data["choices"][0]["message"]["content"].strip()
                
                # Extraire les tokens usage si disponible
                usage = data.get("usage", {})
                if usage:
                    cached_tokens = 0
                    try:
                        cached_tokens = int(
                            usage.get("cached_tokens")
                            or (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
                            or 0
                        )
                    except Exception:
                        cached_tokens = 0
                    token_msg = f"{usage.get('prompt_tokens', 0)} + {usage.get('completion_tokens', 0)} = {usage.get('total_tokens', 0)} tokens"
                    if cached_tokens:
                        token_msg = f"{token_msg} | cached_prompt_tokens={cached_tokens}"
                    log3("[LLM][TOKENS]", token_msg)
                
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
    
    async def _direct_llm_call(
        self,
        prompt: str,
        model_name: str,
        temperature: float = 0.2,
        max_tokens: int = 100,
        top_p: Optional[float] = None,
    ) -> str:
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
        if top_p is not None:
            payload["top_p"] = float(top_p)
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.api_url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()


def get_llm_client() -> Any:
    """Retourne un singleton LLM client pour les modules utilitaires (ex: InterventionGuardian).

    Si Groq n'est pas configuré (pas de GROQ_API_KEY), on bascule sur OpenRouter.
    """
    global _global_llm_client
    if _global_llm_client is None:
        forced_provider = (os.getenv("LLM_PROVIDER") or "").strip().lower()
        groq_key_present = bool((os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY") or "").strip())
        openrouter_key_present = bool((os.getenv("OPENROUTER_API_KEY") or "").strip())

        if forced_provider in {"openrouter", "router"} and openrouter_key_present:
            _global_llm_client = OpenRouterLLMClient()
        elif (not groq_key_present) and openrouter_key_present:
            _global_llm_client = OpenRouterLLMClient()
        else:
            _global_llm_client = GroqLLMClient()
    return _global_llm_client


async def complete(
    prompt: str,
    model_name: str = "llama-3.1-8b-instant",
    temperature: float = 0.2,
    max_tokens: int = 512,
    top_p: Optional[float] = None,
) -> str:
    """
    Appel asynchrone à Groq avec rate limiting intégré
    """
    from utils import log3

    forced_provider = (os.getenv("LLM_PROVIDER") or "").strip().lower()
    openrouter_key_present = bool((os.getenv("OPENROUTER_API_KEY") or "").strip())
    groq_key_present = bool((os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY") or "").strip())
    prefer_openrouter = (forced_provider in {"openrouter", "router"} and openrouter_key_present) or (
        (not groq_key_present) and openrouter_key_present
    )

    if prefer_openrouter:
        try:
            client = get_llm_client()
            out = await client.complete(
                prompt=prompt,
                model_name=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
            )
            if isinstance(out, dict):
                return str(out.get("response") or "").strip()
            return str(out or "").strip()
        except Exception as e:
            log3("[LLM][ERROR]", str(e))
            return f"[Erreur LLM] {str(e)}"

    # Fonction complete avec rate limiting
    async def _rate_limited_complete():
        log3("Prompt", prompt)
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY or GROK_API_KEY}",
            "Content-Type": "application/json",
        }
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
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if top_p is not None:
            payload["top_p"] = float(top_p)
        print(f" [LLM] Envoi requête vers {GROQ_API_URL or GROK_API_URL}")

        async with httpx.AsyncClient() as client:
            resp = await client.post(GROQ_API_URL or GROK_API_URL, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            response_text = data["choices"][0]["message"]["content"].strip()
            print(" [LLM] Réponse reçue")
            log3("Réponse LLM", response_text)
            return response_text

    try:
        return await protected_groq_call(lambda: rate_limited_llm_call(_rate_limited_complete, user_id="global_complete"))
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "rate_limit" in error_str.lower() or "quota" in error_str.lower():
            log3("[LLM][FALLBACK]", "70B épuisé, fallback direct GPT-OSS-120B")
            return "Système temporairement surchargé. Réessaie dans un instant."
        print(f"[LLM] Erreur: {type(e).__name__}")
        log3("[LLM][ERROR]", str(e))
        return f"[Erreur LLM] {str(e)}"


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