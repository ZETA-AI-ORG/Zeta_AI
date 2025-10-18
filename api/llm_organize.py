from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import json
from core.llm_client import GroqLLMClient
import asyncio

router = APIRouter()

# Modèle d'entrée : texte brut ou données onboarding "sales"
class RawOnboardingData(BaseModel):
    raw_text: str
    # Optionnel : company_id, metadata, etc.

# Modèle de sortie : JSON structuré (clé/valeurs)
class StructuredData(BaseModel):
    structured_data: dict

# Utilitaire : prompt LLM pour structuration
LLM_ORGANIZER_PROMPT = """
Tu es un agent d'organisation de données e-commerce. 
À partir du texte brut ci-dessous, produis un objet JSON structuré selon ce schéma :
{
  "company": {
    "companyName": "...",
    "aiName": "...",
    "sector": "...",
    "mission": "...",
    "activityZone": "..."
  },
  "products": [
    {
      "nom_produit": "...",
      "catégorie": "...",
      "sous_catégorie": "...",
      "description": "...",
      "images": [],
      "conditions_vente": "...",
      "disponibilité": "...",
      "variantes": [
        {"nom": "...", "attributs": {...}, "prix": ...}
      ],
      "tarifs": [
        {"variant": "...", "prix": ...}
      ]
    }
  ],
  "payment_methods": "...",
  "delivery": {...},
  "faq": [
    {"question": "...", "answer": "..."}
  ]
}
- Respecte les types (prix = int, variantes = array…).
- Ne laisse aucun champ important vide si l’info est présente.
- Si un champ n’existe pas dans le texte, mets-le à null ou omets-le.
Texte à structurer :
{raw_text}
"""

@router.post("/api/llm-organize", response_model=StructuredData)
async def llm_organize(data: RawOnboardingData):
    prompt = LLM_ORGANIZER_PROMPT.format(raw_text=data.raw_text)
    llm_client = GroqLLMClient()  # Utilise la config centrale (GROK_API_KEY, GROK_API_URL)
    try:
        # Appel du LLM Groq (même modèle que le pipeline principal)
        response_text = await llm_client.complete(
            prompt=prompt,
            model_name="llama3-8b-8192",
            temperature=0.1,
            max_tokens=512
        )
        # Tente de parser le JSON renvoyé
        structured_data = json.loads(response_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur LLM ou parsing : {e}")
    return {"structured_data": structured_data}
