import os
import requests
from typing import Any, Dict, Optional


OPENROUTER_API_URL = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")


class OpenRouterLLMError(Exception):
    pass


async def complete(
    prompt: str,
    model_name: Optional[str] = None,
    max_tokens: int = 600,
    temperature: float = 0.7,
    top_p: float = 1.0,
    seed: Optional[int] = None,
    response_format: Optional[Dict[str, Any]] = None,
) -> tuple[str, dict]:
    """Wrapper OpenAI-compatible pour OpenRouter chat completions."""

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise OpenRouterLLMError("OPENROUTER_API_KEY manquant dans l'environnement")

    default_model = os.getenv("LLM_MODEL", "google/gemini-2.5-flash-lite")
    model = (model_name or default_model).strip()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    http_referer = os.getenv("OPENROUTER_HTTP_REFERER")
    if http_referer:
        headers["HTTP-Referer"] = http_referer

    x_title = os.getenv("OPENROUTER_X_TITLE")
    if x_title:
        headers["X-Title"] = x_title

    prefer_provider = os.getenv("OPENROUTER_PREFER_PROVIDER")
    if prefer_provider:
        headers["OpenRouter-Prefer-Provider"] = prefer_provider

    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": top_p,
        "stream": False,
    }

    if seed is not None:
        body["seed"] = int(seed)
    if response_format is not None:
        body["response_format"] = response_format

    try:
        resp = requests.post(OPENROUTER_API_URL, json=body, headers=headers, timeout=60)
        if resp.status_code != 200:
            raise OpenRouterLLMError(f"OpenRouter API HTTP {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            raise OpenRouterLLMError("Réponse OpenRouter sans choices")

        message = choices[0].get("message") or {}
        content = str((message.get("content") or "")).strip()

        usage = data.get("usage", {})
        token_info = {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "model": model,
        }

        return content, token_info
    except requests.RequestException as e:
        raise OpenRouterLLMError(f"Erreur requête OpenRouter: {e}")
