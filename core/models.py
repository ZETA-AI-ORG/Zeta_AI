# models.py - Modèles Pydantic pour CHATBOT2.0
from pydantic import BaseModel
from typing import Optional, List

import re
from pydantic import BaseModel, validator, constr, ValidationError

class ChatRequest(BaseModel):
    company_id: constr(strip_whitespace=True, min_length=8, max_length=64)
    user_id: constr(strip_whitespace=True, min_length=4, max_length=64)
    # message peut être vide si images présentes ou si botlive est actif
    message: Optional[str] = ""
    message_id: Optional[str] = None
    images: List[str] = []  # URLs d'images depuis Messenger (toujours tableau)
    botlive_enabled: bool = False
    rag_enabled: Optional[bool] = None
    # présent dans le payload n8n, mais on utilise "message" comme champ canonique
    user_question: Optional[str] = None
    # conversation_history n'est plus attendu côté API; chargé depuis Supabase
    conversation_history: Optional[str] = ""
    # Permet de forcer un modèle spécifique (ex: tests)
    model_name: Optional[str] = None

    @validator('company_id')
    def validate_company_id(cls, v):
        # UUID ou identifiant alphanumérique strict
        if not re.match(r'^[a-zA-Z0-9\-]{8,64}$', v):
            raise ValueError('company_id must be a valid UUID or alphanumeric')
        return v

    @validator('user_id')
    def validate_user_id(cls, v):
        # Accept:
        # - existing IDs: alphanumeric + hyphens/underscores
        # - WhatsApp E.164 numbers: + followed by digits (e.g. +2250719568895)
        # - WhatsApp LID format: digits@lid (e.g. 120538492100718@lid)
        if re.match(r'^\+\d{6,15}$', v):
            return v
        if re.match(r'^\d+@lid$', v):
            return v
        if not re.match(r'^[a-zA-Z0-9\-_]{4,64}$', v):
            raise ValueError('user_id must be a valid alphanumeric string, E.164 phone number, or WhatsApp LID (digits@lid)')
        return v

    @validator('images', pre=True, always=True)
    def ensure_images_array(cls, v):
        # Garantit un tableau d'URLs valides
        if v is None:
            return []
        # Si c'est une string (n8n envoie parfois "Voici la capture URL" au lieu de ["URL"])
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            # Extraire toutes les URLs HTTP(S) de la string
            urls = re.findall(r'https?://[^\s"\]\)]+', v)
            return urls if urls else []
        # Si c'est déjà une liste, filtrer les entrées valides
        if isinstance(v, list):
            cleaned = []
            for item in v:
                if isinstance(item, str):
                    item = item.strip()
                    # Si l'item est une URL directe, garder
                    if item.startswith('http'):
                        cleaned.append(item)
                    else:
                        # Extraire les URLs de l'item (cas "Voici la capture URL")
                        urls = re.findall(r'https?://[^\s"\]\)]+', item)
                        cleaned.extend(urls)
            return cleaned
        return []

    @validator('message', always=True)
    def ensure_message_rules(cls, v, values):
        # Assouplissement: on n'interdit plus message vide ici.
        # La logique de fallback/erreur est gérée dans l'endpoint /chat.
        if v is None:
            v = ""
        v = v.strip()
        # Si message est vide mais images contient des URLs, créer un message par défaut
        if not v and values.get('images'):
            v = "Voici la capture"
        return v[:2000]

class ChatResponse(BaseModel):
    response: str
    company_id: str
    user_id: str
    status: str = "success"
    status: str = "success"
