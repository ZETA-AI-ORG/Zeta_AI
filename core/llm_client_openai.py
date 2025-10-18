"""
Client LLM pour GPT-4o-mini (OpenAI)
Production-ready avec retry logic et rate limiting
"""
import os
import asyncio
from openai import AsyncOpenAI
from typing import Optional
import time
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEFAULT_MODEL = "gpt-4o-mini"  # Rapide et économique
DEFAULT_MAX_TOKENS = 1000
DEFAULT_TEMPERATURE = 0.7

# Client global
_client: Optional[AsyncOpenAI] = None

def get_client() -> AsyncOpenAI:
    """Récupère ou crée le client OpenAI"""
    global _client
    if _client is None:
        if not OPENAI_API_KEY:
            raise ValueError("❌ OPENAI_API_KEY non définie dans .env")
        _client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        print("✅ [OPENAI] Client configuré")
    return _client


async def complete(
    prompt: str,
    model_name: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
    max_retries: int = 3
) -> str:
    """
    Génère une réponse avec GPT-4o-mini
    
    Args:
        prompt: Le prompt utilisateur
        model_name: Modèle à utiliser (défaut: gpt-4o-mini)
        max_tokens: Nombre max de tokens de sortie
        temperature: Créativité (0=déterministe, 1=créatif)
        max_retries: Nombre de tentatives en cas d'erreur
        
    Returns:
        str: Réponse générée par le LLM
    """
    client = get_client()
    
    for attempt in range(max_retries):
        try:
            start_time = time.time()
            
            response = await client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=30.0
            )
            
            elapsed = time.time() - start_time
            
            if response.choices and response.choices[0].message.content:
                text = response.choices[0].message.content.strip()
                
                # Logs détaillés
                usage = response.usage
                print(f"✅ [OPENAI] Réponse en {elapsed:.2f}s")
                print(f"📊 [OPENAI] Tokens: {usage.prompt_tokens} input + {usage.completion_tokens} output = {usage.total_tokens} total")
                
                return text
            else:
                print(f"⚠️ [OPENAI] Réponse vide (tentative {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                continue
                
        except Exception as e:
            error_msg = str(e)
            print(f"❌ [OPENAI] Erreur (tentative {attempt + 1}/{max_retries}): {error_msg}")
            
            # Gestion des erreurs spécifiques
            if "rate_limit" in error_msg.lower():
                print("⏳ [OPENAI] Rate limit, attente 10s...")
                await asyncio.sleep(10)
            elif "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
                raise ValueError("❌ Clé API OpenAI invalide")
            elif "timeout" in error_msg.lower():
                print("⏳ [OPENAI] Timeout, nouvelle tentative...")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
            else:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
    
    raise Exception(f"❌ [OPENAI] Échec après {max_retries} tentatives")


async def complete_with_history(
    messages: list[dict],
    model_name: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
    max_retries: int = 3
) -> str:
    """
    Génère une réponse avec historique de conversation
    
    Args:
        messages: Liste de messages [{"role": "user/assistant", "content": "..."}]
        model_name: Modèle à utiliser
        max_tokens: Nombre max de tokens de sortie
        temperature: Créativité
        max_retries: Nombre de tentatives
        
    Returns:
        str: Réponse générée
    """
    client = get_client()
    
    for attempt in range(max_retries):
        try:
            start_time = time.time()
            
            response = await client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=30.0
            )
            
            elapsed = time.time() - start_time
            
            if response.choices and response.choices[0].message.content:
                text = response.choices[0].message.content.strip()
                usage = response.usage
                print(f"✅ [OPENAI] Réponse avec historique en {elapsed:.2f}s")
                print(f"📊 [OPENAI] Tokens: {usage.total_tokens} total")
                return text
            else:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                continue
                
        except Exception as e:
            print(f"❌ [OPENAI] Erreur historique (tentative {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
    
    raise Exception(f"❌ [OPENAI] Échec après {max_retries} tentatives")


# Test rapide
if __name__ == "__main__":
    async def test():
        print("🧪 Test GPT-4o-mini...")
        
        # Test simple
        response = await complete(
            "Réponds en une phrase : Quelle est la capitale de la Côte d'Ivoire ?",
            max_tokens=100
        )
        print(f"\n✅ Réponse: {response}\n")
        
        # Test avec balises XML
        response2 = await complete(
            """Réponds avec ce format exact:
<thinking>
Analyse rapide
</thinking>

<response>
Réponse courte
</response>

Question: Quel est 2+2 ?""",
            max_tokens=200
        )
        print(f"✅ Réponse structurée:\n{response2}")
    
    asyncio.run(test())
