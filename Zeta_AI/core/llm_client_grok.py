import os
import requests
from typing import Optional

XAI_API_KEY = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
XAI_API_URL = os.getenv("XAI_API_URL", "https://api.x.ai/v1/chat/completions")
DEFAULT_MODEL = os.getenv("GROK_MODEL", "grok-2-70b")  # versatile 70B

class GrokLLMError(Exception):
    pass

async def complete(prompt: str,
                   model_name: Optional[str] = None,
                   max_tokens: int = 600,
                   temperature: float = 0.7) -> str:
    """
    Minimal async-compatible wrapper around xAI Grok chat completions.
    Uses requests synchronously; FastAPI will await this function's result.
    """
    if not XAI_API_KEY:
        raise GrokLLMError("XAI_API_KEY/GROK_API_KEY manquant dans l'environnement")

    model = (model_name or DEFAULT_MODEL).strip()

    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json",
    }

    body = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        # Ensure we get text out
        "stream": False
    }

    try:
        resp = requests.post(XAI_API_URL, json=body, headers=headers, timeout=60)
        if resp.status_code != 200:
            raise GrokLLMError(f"xAI API HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        # Expected OpenAI-like shape
        choices = data.get("choices") or []
        if not choices:
            raise GrokLLMError("Réponse xAI sans choices")
        return choices[0].get("message", {}).get("content", "").strip()
    except requests.RequestException as e:
        raise GrokLLMError(f"Erreur requête xAI: {e}")
