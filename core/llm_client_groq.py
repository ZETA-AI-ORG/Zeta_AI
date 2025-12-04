import os
import requests
from typing import Optional

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
DEFAULT_MODEL = os.getenv("DEFAULT_LLM_MODEL", "llama-3.3-70b-versatile")

class GroqLLMError(Exception):
    pass

async def complete(prompt: str,
                   model_name: Optional[str] = None,
                   max_tokens: int = 600,
                   temperature: float = 0.7,
                   top_p: float = 1.0,
                   frequency_penalty: float = 0.0) -> tuple[str, dict]:
    """
    Wrapper OpenAI-compatible pour Groq chat completions.
    """
    if not GROQ_API_KEY:
        raise GroqLLMError("GROQ_API_KEY manquant dans l'environnement")

    model = (model_name or DEFAULT_MODEL).strip()

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    body = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": top_p,
        "frequency_penalty": frequency_penalty,
        "stream": False
    }

    try:
        resp = requests.post(GROQ_API_URL, json=body, headers=headers, timeout=60)
        if resp.status_code != 200:
            raise GroqLLMError(f"Groq API HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            raise GroqLLMError("Réponse Groq sans choices")
        
        # Extraire le contenu
        content = choices[0].get("message", {}).get("content", "").strip()
        
        # Extraire les tokens usage depuis l'API Groq
        usage = data.get("usage", {})
        token_info = {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "model": model
        }
        
        return content, token_info
    except requests.RequestException as e:
        raise GroqLLMError(f"Erreur requête Groq: {e}")
