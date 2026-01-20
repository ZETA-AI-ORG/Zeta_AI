# core/llm_core.py
"""
Module de génération LLM pour HyDE, branché sur l'API Groq (Llama3, etc).
"""
import aiohttp
import os
from ..config import GROQ_API_KEY, GROQ_API_URL

async def complete(prompt: str, model_name: str = "llama3-8b-8192", temperature: float = 0.0, max_tokens: int = 256, **kwargs):
    """
    Appelle l'API Groq pour générer des hypothèses HyDE.
    Retourne une liste de chaînes (hypothèses).
    """
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_name,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        **kwargs
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(GROQ_API_URL, headers=headers, json=payload, timeout=30) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"Groq API error {resp.status}: {text}")
            data = await resp.json()
    # Extraction du texte généré (supporte n réponses)
    completions = data.get("choices", [])
    if not completions:
        raise RuntimeError("Groq API: aucune completion retournée")
    # On retourne le(s) message(s) généré(s) (HyDE attend un seul string ou une liste de strings)
    return [c["message"]["content"] for c in completions]
