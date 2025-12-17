import os
import json
import logging
import requests
from typing import Optional

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
DEFAULT_MODEL = os.getenv("DEFAULT_LLM_MODEL", "llama-3.3-70b-versatile")

logger = logging.getLogger(__name__)

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

    if model.startswith("openai/") or "gpt-oss" in model:
        body["tool_choice"] = "none"
        body["tools"] = []

    try:
        resp = requests.post(GROQ_API_URL, json=body, headers=headers, timeout=60)
        if resp.status_code != 200:
            raise GroqLLMError(f"Groq API HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            raise GroqLLMError("Réponse Groq sans choices")
        
        # Extraire le contenu
        message = choices[0].get("message") or {}
        content = str((message.get("content") or "")).strip()

        if not content:
            tool_calls = message.get("tool_calls") or []
            if isinstance(tool_calls, list) and tool_calls:
                fn = tool_calls[0].get("function") or {}
                args = fn.get("arguments")
                if isinstance(args, str):
                    content = args.strip()
                elif isinstance(args, dict):
                    try:
                        content = json.dumps(args, ensure_ascii=False)
                    except Exception:
                        content = ""

        if not content:
            reasoning = message.get("reasoning")
            if isinstance(reasoning, str) and reasoning.strip():
                content = reasoning.strip()

        if not content:
            debug_raw = os.getenv("BOTLIVE_LLM_DEBUG_RAW", "false").strip().lower() in {
                "1",
                "true",
                "yes",
                "y",
                "on",
            }
            if debug_raw:
                try:
                    raw_choice = choices[0]
                    raw_snip = ""
                    try:
                        raw_snip = resp.text[:1500]
                    except Exception:
                        raw_snip = ""
                    logger.warning(
                        "[Groq][EMPTY_CONTENT] model=%s | message_keys=%s | choice_keys=%s | resp_snip=%s",
                        model,
                        list(message.keys()),
                        list(raw_choice.keys()) if isinstance(raw_choice, dict) else type(raw_choice),
                        raw_snip,
                    )
                except Exception:
                    pass
        
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
