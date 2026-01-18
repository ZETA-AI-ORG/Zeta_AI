"""
Gestion et persistance de l'historique de conversation.
A compléter selon besoin (ex: stockage Supabase ou fichier local).
"""

import httpx
import uuid
import os
from datetime import datetime
from config import SUPABASE_URL, SUPABASE_KEY

# ✅ FIX 401: Utiliser SERVICE_KEY pour bypass RLS sur les INSERT
def _get_supabase_write_key():
    """Retourne la clé Supabase pour les opérations d'écriture (INSERT/UPDATE)"""
    # Priorité: SERVICE_KEY > KEY (service_role bypass RLS)
    service_key = os.getenv('SUPABASE_SERVICE_KEY')
    if service_key:
        return service_key
    return SUPABASE_KEY

def _normalize_conversation_role(role: str) -> str:
    """Normalise strictement le champ role pour éviter de polluer conversation_memory."""
    role_str = str(role or "").strip()
    role_lower = role_str.lower()

    # Backend doit rester compatible frontend: user / assistant / human
    if role_lower in {"assistant", "ai", "bot"}:
        return "assistant"
    if role_lower == "ia":
        return "assistant"
    if role_lower == "human":
        return "human"
    if role_lower == "user":
        return "user"

    # Si un callsite passe accidentellement le message dans le role, on force user.
    if len(role_str) > 16 or " " in role_str or "?" in role_str or "!" in role_str:
        return "user"

    return "user"

def _normalize_conversation_content(content):
    """Assure que content est une string (JSON) compatible avec la colonne Supabase."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    try:
        import json

        return json.dumps(content, ensure_ascii=False, default=str)
    except Exception:
        return str(content)

async def save_message(company_id: str, user_id: str, role: str, content: str):
    """
    Sauvegarde un message dans Supabase (table conversation_memory).
    Remplace automatiquement 'assistant' par 'IA' pour optimisation tokens.
    
    ✅ FIX 401: Utilise SUPABASE_SERVICE_KEY pour bypass RLS
    """
    write_key = _get_supabase_write_key()
    url = f"{SUPABASE_URL}/rest/v1/conversation_memory"
    headers = {
        "apikey": write_key,
        "Authorization": f"Bearer {write_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"  # Optimisation: pas besoin de retourner les données
    }
    
    # Génération d'un message_id unique
    message_id = str(uuid.uuid4())
    
    role = _normalize_conversation_role(role)
    content = _normalize_conversation_content(content)
    
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
    read_key = _get_supabase_write_key()
    headers = {
        "apikey": read_key,
        "Authorization": f"Bearer {read_key}"
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

            def normalize_prefix(db_role: str) -> str:
                r = str(db_role or "").strip().lower()
                if r == "assistant":
                    return "IA"
                if r == "human":
                    return "user"
                if r == "user":
                    return "user"
                return "user"

            history = "\n".join([
                f"{normalize_prefix(msg.get('role'))}: {extract_text(msg['content'])}"
                for msg in all_messages
            ])
            
            # Tronquer à 2000 chars max (garder les plus récents)
            if len(history) > 2000:
                history = "..." + history[-2000:]
            
            return history
        else:
            print(f"[SUPABASE] Erreur historique: {resp.status_code}")
            return ""