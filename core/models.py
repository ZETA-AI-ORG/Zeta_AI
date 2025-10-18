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

    @validator('company_id')
    def validate_company_id(cls, v):
        # UUID ou identifiant alphanumérique strict
        if not re.match(r'^[a-zA-Z0-9\-]{8,64}$', v):
            raise ValueError('company_id must be a valid UUID or alphanumeric')
        return v

    @validator('user_id')
    def validate_user_id(cls, v):
        if not re.match(r'^[a-zA-Z0-9\-_]{4,64}$', v):
            raise ValueError('user_id must be a valid alphanumeric string (letters, numbers, hyphens, underscores)')
        return v

    @validator('images', pre=True, always=True)
    def ensure_images_array(cls, v):
        # Garantit un tableau
        if v is None:
            return []
        return v

    @validator('message', always=True)
    def ensure_message_rules(cls, v, values):
        # Assouplissement: on n'interdit plus message vide ici.
        # La logique de fallback/erreur est gérée dans l'endpoint /chat.
        if v is None:
            return ""
        return v[:2000]

class ChatResponse(BaseModel):
    response: str
    company_id: str
    user_id: str
    status: str = "success"
