"""
Client LLM pour Gemini 1.5 Pro (Google)
Production-ready avec retry logic et rate limiting
"""
import os
import asyncio
import google.generativeai as genai
from typing import Optional
import time
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DEFAULT_MODEL = "gemini-1.5-pro"
DEFAULT_MAX_TOKENS = 1000
DEFAULT_TEMPERATURE = 0.7

# Client configuré
_configured = False

def configure_client():
    """Configure le client Gemini une seule fois"""
    global _configured
    if not _configured:
        if not GEMINI_API_KEY:
            raise ValueError("❌ GEMINI_API_KEY non définie dans .env")
        genai.configure(api_key=GEMINI_API_KEY)
        _configured = True
        print("✅ [GEMINI] Client configuré")


async def complete(
    prompt: str,
    model_name: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
    max_retries: int = 3
) -> str:
    """
    Génère une réponse avec Gemini 1.5 Pro
    
    Args:
        prompt: Le prompt utilisateur
        model_name: Modèle à utiliser (défaut: gemini-1.5-pro)
        max_tokens: Nombre max de tokens de sortie
        temperature: Créativité (0=déterministe, 1=créatif)
        max_retries: Nombre de tentatives en cas d'erreur
        
    Returns:
        str: Réponse générée par le LLM
    """
    configure_client()
    
    # Configuration du modèle
    generation_config = {
        "temperature": temperature,
        "max_output_tokens": max_tokens,
        "top_p": 0.95,
    }
    
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    
    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config=generation_config,
        safety_settings=safety_settings
    )
    
    # Retry logic
    for attempt in range(max_retries):
        try:
            start_time = time.time()
            
            # Génération asynchrone
            response = await asyncio.to_thread(
                model.generate_content,
                prompt
            )
            
            elapsed = time.time() - start_time
            
            # Extraire le texte
            if response and response.text:
                text = response.text.strip()
                
                # Logs
                print(f"✅ [GEMINI] Réponse générée en {elapsed:.2f}s")
                print(f"📊 [GEMINI] Tokens: ~{len(text.split())} mots")
                
                return text
            else:
                print(f"⚠️ [GEMINI] Réponse vide (tentative {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Backoff exponentiel
                continue
                
        except Exception as e:
            error_msg = str(e)
            print(f"❌ [GEMINI] Erreur (tentative {attempt + 1}/{max_retries}): {error_msg}")
            
            # Gestion des erreurs spécifiques
            if "quota" in error_msg.lower() or "rate" in error_msg.lower():
                print("⏳ [GEMINI] Rate limit atteint, attente 5s...")
                await asyncio.sleep(5)
            elif "api key" in error_msg.lower():
                raise ValueError("❌ Clé API Gemini invalide")
            else:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    
    # Si tous les essais échouent
    raise Exception(f"❌ [GEMINI] Échec après {max_retries} tentatives")


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
    configure_client()
    
    generation_config = {
        "temperature": temperature,
        "max_output_tokens": max_tokens,
        "top_p": 0.95,
    }
    
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    
    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config=generation_config,
        safety_settings=safety_settings
    )
    
    # Convertir les messages au format Gemini
    chat = model.start_chat(history=[])
    
    for msg in messages[:-1]:  # Tous sauf le dernier
        role = "user" if msg["role"] == "user" else "model"
        chat.history.append({
            "role": role,
            "parts": [msg["content"]]
        })
    
    # Dernier message = requête actuelle
    last_message = messages[-1]["content"]
    
    # Retry logic
    for attempt in range(max_retries):
        try:
            start_time = time.time()
            
            response = await asyncio.to_thread(
                chat.send_message,
                last_message
            )
            
            elapsed = time.time() - start_time
            
            if response and response.text:
                text = response.text.strip()
                print(f"✅ [GEMINI] Réponse avec historique en {elapsed:.2f}s")
                return text
            else:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                continue
                
        except Exception as e:
            print(f"❌ [GEMINI] Erreur historique (tentative {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
    
    raise Exception(f"❌ [GEMINI] Échec après {max_retries} tentatives")


# Test rapide
if __name__ == "__main__":
    async def test():
        print("🧪 Test Gemini 1.5 Pro...")
        
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
