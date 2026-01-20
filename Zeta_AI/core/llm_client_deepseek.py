"""
Client LLM pour DeepSeek-V3.2 (DeepSeek)
Production-ready avec retry logic, rate limiting et context caching
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
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"  # V3.2-Exp sans réflexion
DEFAULT_REASONER_MODEL = "deepseek-reasoner"  # V3.2-Exp avec réflexion
DEFAULT_MAX_TOKENS = 1000
DEFAULT_TEMPERATURE = 0.7

# Client global
_client: Optional[AsyncOpenAI] = None

def get_client() -> AsyncOpenAI:
    """Récupère ou crée le client DeepSeek"""
    global _client
    if _client is None:
        if not DEEPSEEK_API_KEY:
            raise ValueError("❌ DEEPSEEK_API_KEY non définie dans .env")
        _client = AsyncOpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL
        )
        print("✅ [DEEPSEEK] Client configuré")
    return _client


async def complete(
    prompt: str,
    model_name: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
    use_reasoning: bool = False,
    max_retries: int = 3
) -> str:
    """
    Génère une réponse avec DeepSeek-V3.2
    
    Args:
        prompt: Le prompt utilisateur
        model_name: Modèle à utiliser (défaut: deepseek-chat)
        max_tokens: Nombre max de tokens de sortie
        temperature: Créativité (0=déterministe, 1=créatif)
        use_reasoning: Utiliser le mode raisonnement (deepseek-reasoner)
        max_retries: Nombre de tentatives en cas d'erreur
        
    Returns:
        str: Réponse générée par le LLM
    """
    client = get_client()
    
    # Sélection du modèle
    if use_reasoning:
        model_name = DEFAULT_REASONER_MODEL
        print("🧠 [DEEPSEEK] Mode raisonnement activé")
    
    for attempt in range(max_retries):
        try:
            start_time = time.time()
            
            # Log complet de l'input envoyé au LLM
            if attempt == 0:  # Afficher seulement à la première tentative
                print("\n" + "="*100)
                print("\033[95m💜 [DEEPSEEK INPUT] PROMPT COMPLET ENVOYÉ AU LLM:\033[0m")
                print("\033[95m" + "="*100 + "\033[0m")
                print(f"\033[95m{prompt}\033[0m")
                print("\033[95m" + "="*100 + "\033[0m")
                print(f"\033[95m📊 Longueur: {len(prompt)} caractères\033[0m")
                print("="*100 + "\n")
            
            response = await client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=60.0
            )
            
            elapsed = time.time() - start_time
            
            if response.choices and response.choices[0].message.content:
                text = response.choices[0].message.content.strip()
                
                # Logs détaillés
                usage = response.usage
                
                # Calcul du coût (approximatif)
                input_cost = (usage.prompt_tokens / 1_000_000) * 0.28
                output_cost = (usage.completion_tokens / 1_000_000) * 0.42
                total_cost = input_cost + output_cost
                
                print(f"✅ [DEEPSEEK] Réponse en {elapsed:.2f}s")
                print(f"📊 [DEEPSEEK] Tokens: {usage.prompt_tokens} input + {usage.completion_tokens} output = {usage.total_tokens} total")
                print(f"💰 [DEEPSEEK] Coût: ${total_cost:.6f} (${input_cost:.6f} input + ${output_cost:.6f} output)")
                
                # Extraire le raisonnement si mode reasoner
                if use_reasoning and hasattr(response.choices[0].message, 'reasoning_content'):
                    reasoning = response.choices[0].message.reasoning_content
                    if reasoning:
                        print(f"🧠 [DEEPSEEK] Raisonnement: {reasoning[:100]}...")
                
                return text
            else:
                print(f"⚠️ [DEEPSEEK] Réponse vide (tentative {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                continue
                
        except Exception as e:
            error_msg = str(e)
            print(f"❌ [DEEPSEEK] Erreur (tentative {attempt + 1}/{max_retries}): {error_msg}")
            
            # Gestion des erreurs spécifiques
            if "rate_limit" in error_msg.lower() or "429" in error_msg:
                print("⏳ [DEEPSEEK] Rate limit, attente 10s...")
                await asyncio.sleep(10)
            elif "api_key" in error_msg.lower() or "authentication" in error_msg.lower() or "401" in error_msg:
                raise ValueError("❌ Clé API DeepSeek invalide")
            elif "timeout" in error_msg.lower():
                print("⏳ [DEEPSEEK] Timeout, nouvelle tentative...")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
            else:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
    
    raise Exception(f"❌ [DEEPSEEK] Échec après {max_retries} tentatives")


async def complete_with_history(
    messages: list[dict],
    model_name: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
    use_reasoning: bool = False,
    enable_cache: bool = True,
    max_retries: int = 3
) -> str:
    """
    Génère une réponse avec historique de conversation
    
    Args:
        messages: Liste de messages [{"role": "user/assistant/system", "content": "..."}]
        model_name: Modèle à utiliser
        max_tokens: Nombre max de tokens de sortie
        temperature: Créativité
        use_reasoning: Utiliser le mode raisonnement
        enable_cache: Activer le context caching (économise 10x sur tokens répétés)
        max_retries: Nombre de tentatives
        
    Returns:
        str: Réponse générée
    """
    client = get_client()
    
    # Sélection du modèle
    if use_reasoning:
        model_name = DEFAULT_REASONER_MODEL
    
    # Activer le cache pour les messages système/historique longs
    if enable_cache and len(messages) > 1:
        # Marquer les premiers messages pour le cache
        for i, msg in enumerate(messages[:-1]):  # Tous sauf le dernier
            if "cache_control" not in msg:
                msg["cache_control"] = {"type": "ephemeral"}
    
    for attempt in range(max_retries):
        try:
            start_time = time.time()
            
            # Log complet de l'input envoyé au LLM
            if attempt == 0:  # Afficher seulement à la première tentative
                print("\n" + "="*100)
                print("\033[95m💜 [DEEPSEEK INPUT] MESSAGES COMPLETS ENVOYÉS AU LLM:\033[0m")
                print("\033[95m" + "="*100 + "\033[0m")
                for i, msg in enumerate(messages):
                    print(f"\033[95m[Message {i+1}] Role: {msg.get('role', 'unknown')}\033[0m")
                    content = msg.get('content', '')
                    print(f"\033[95m{content}\033[0m")
                    print("\033[95m" + "-"*100 + "\033[0m")
                print(f"\033[95m📊 Total messages: {len(messages)}\033[0m")
                total_chars = sum(len(msg.get('content', '')) for msg in messages)
                print(f"\033[95m📊 Longueur totale: {total_chars} caractères\033[0m")
                print("="*100 + "\n")
            
            response = await client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=60.0
            )
            
            elapsed = time.time() - start_time
            
            if response.choices and response.choices[0].message.content:
                text = response.choices[0].message.content.strip()
                usage = response.usage
                
                # Calcul du coût avec cache
                cache_hit_tokens = getattr(usage, 'prompt_cache_hit_tokens', 0)
                cache_miss_tokens = usage.prompt_tokens - cache_hit_tokens
                
                cache_hit_cost = (cache_hit_tokens / 1_000_000) * 0.028
                cache_miss_cost = (cache_miss_tokens / 1_000_000) * 0.28
                output_cost = (usage.completion_tokens / 1_000_000) * 0.42
                total_cost = cache_hit_cost + cache_miss_cost + output_cost
                
                print(f"✅ [DEEPSEEK] Réponse avec historique en {elapsed:.2f}s")
                print(f"📊 [DEEPSEEK] Tokens: {usage.total_tokens} total")
                if cache_hit_tokens > 0:
                    print(f"🎯 [DEEPSEEK] Cache: {cache_hit_tokens} hits (économie: ${(cache_miss_tokens * 0.252 / 1_000_000):.6f})")
                print(f"💰 [DEEPSEEK] Coût: ${total_cost:.6f}")
                
                return text
            else:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                continue
                
        except Exception as e:
            print(f"❌ [DEEPSEEK] Erreur historique (tentative {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
    
    raise Exception(f"❌ [DEEPSEEK] Échec après {max_retries} tentatives")


# Test rapide
if __name__ == "__main__":
    async def test():
        print("🧪 Test DeepSeek-V3.2...")
        
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
        print(f"✅ Réponse structurée:\n{response2}\n")
        
        # Test mode raisonnement
        response3 = await complete(
            "Résous ce problème étape par étape : Si un produit coûte 15000 FCFA et j'ai une remise de 20%, combien je paie ?",
            max_tokens=500,
            use_reasoning=True
        )
        print(f"✅ Réponse avec raisonnement:\n{response3}")
    
    asyncio.run(test())
