"""
Gestion et persistance de l'historique de conversation.
A compléter selon besoin (ex: stockage Supabase ou fichier local).
"""

import httpx
import uuid
from datetime import datetime
from config import SUPABASE_URL, SUPABASE_KEY

async def save_message(company_id: str, user_id: str, role: str, content: str):
    """
    Sauvegarde un message dans Supabase (table conversation_memory).
    Remplace automatiquement 'assistant' par 'IA' pour optimisation tokens.
    """
    url = f"{SUPABASE_URL}/rest/v1/conversation_memory"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    # Génération d'un message_id unique
    message_id = str(uuid.uuid4())
    
    # ✅ REMPLACER "assistant" par "IA" pour optimisation tokens
    if role.lower() == "assistant":
        role = "IA"
    
    payload = {
        "id": str(uuid.uuid4()),  # UUID pour la clé primaire
        "user_id": user_id,  # CORRIGÉ: Utilise le vrai user_id
        "company_id": company_id,  # Ajout du company_id séparé
        "role": role,  # "user" ou "IA" (optimisé)
        "content": content,
        "message_id": message_id
        # timestamp est auto-généré par Supabase (Default: now())
        # embedding est optionnel (NULL par défaut)
    }
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 201:
                print(f"[CONVERSATION] Message sauvegardé: {role}")
            else:
                print(f"[CONVERSATION] Erreur sauvegarde: {resp.status_code}")
    except Exception as e:
        print(f"[CONVERSATION] Erreur: {type(e).__name__}")

async def get_history(company_id: str, user_id: str) -> str:
    """
    Récupère les 15 derniers messages pour ce company_id depuis Supabase (table conversation_memory), triés par timestamp croissant.
    Retourne un historique formaté ("user: ...\nassistant: ...")
    """
    url = f"{SUPABASE_URL}/rest/v1/conversation_memory"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    params = {
        "user_id": f"eq.{user_id}",  # CORRIGÉ: Utilise le vrai user_id
        "company_id": f"eq.{company_id}",  # Filtre aussi par company_id
        "select": "role,content,timestamp",
        "order": "timestamp.desc",
        "limit": 15
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, params=params)
        if resp.status_code == 200:
            data = resp.json()
            # Réordonner du plus ancien au plus récent (après récupération en desc)
            data = list(reversed(data))
            # INCLURE TOUS LES MESSAGES (user + assistant) pour le cumul des paiements Botlive
            # Extraire le texte propre si le contenu est du JSON
            def extract_text(content):
                try:
                    import json
                    obj = json.loads(content)
                    return obj.get('text', content)
                except:
                    return content
            
            all_messages = [msg for msg in data if msg.get('content')]
            history = "\n".join([f"{msg['role']}: {extract_text(msg['content'])}" for msg in all_messages])
            
            # Tronquer à 2000 chars max (garder les plus récents)
            if len(history) > 2000:
                history = "..." + history[-2000:]
            
            return history
        else:
            print(f"[SUPABASE] Erreur historique: {resp.status_code}")
            return ""