"""
Gestion et persistance de l'historique de conversation.
A compléter selon besoin (ex: stockage Supabase ou fichier local).
"""

import httpx
import uuid
import os
from datetime import datetime
from config import SUPABASE_URL, SUPABASE_KEY

# ── Global async HTTP client pool for Supabase (reused across all conversation calls) ──
_supabase_conversation_client: httpx.AsyncClient | None = None


def _get_supabase_client() -> httpx.AsyncClient:
    """Lazy-init a long-lived async HTTP client for Supabase conversation ops."""
    global _supabase_conversation_client
    if _supabase_conversation_client is None or _supabase_conversation_client.is_closed:
        _supabase_conversation_client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            limits=httpx.Limits(max_connections=15, max_keepalive_connections=8),
        )
    return _supabase_conversation_client

def _get_supabase_rw_key() -> str:
    """Retourne la clé Supabase pour bypass RLS si disponible."""
    service_key = os.getenv("SUPABASE_SERVICE_KEY")
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
    """
    rw_key = _get_supabase_rw_key()
    url = f"{SUPABASE_URL}/rest/v1/conversation_memory"
    headers = {
        "apikey": rw_key,
        "Authorization": f"Bearer {rw_key}",
        "Content-Type": "application/json"
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
        client = _get_supabase_client()
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
    rw_key = _get_supabase_rw_key()
    headers = {
        "apikey": rw_key,
        "Authorization": f"Bearer {rw_key}"
    }
    params = {
        "user_id": f"eq.{user_id}",  # CORRIGÉ: Utilise le vrai user_id
        "company_id": f"eq.{company_id}",  # Filtre aussi par company_id
        "select": "role,content,timestamp",
        "order": "timestamp.desc",
        "limit": 15
    }
    client = _get_supabase_client()
    try:
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

            # Compat LLM: convertir roles DB (assistant/human/user) -> prefixes user/IA
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
    except Exception as e:
        print(f"[SUPABASE] Erreur get_history: {type(e).__name__}")
        return ""