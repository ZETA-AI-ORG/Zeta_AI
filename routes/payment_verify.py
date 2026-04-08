"""
Payment Verification Route
Receives payment proof screenshots (Wave receipts) and verifies them
using Gemini multimodal + OCR.

Returns: { verified: bool, amount: int|null, reference: str|null, error: str|null }
"""

import os
import logging
import base64
import json
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("payment_verify")

router = APIRouter(prefix="/api/payment", tags=["Payment Verification"])

# ── Gemini config ──
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_VISION_MODEL", "gemini-1.5-flash")

# ── Response model ──
class VerifyResponse(BaseModel):
    verified: bool
    amount: Optional[int] = None
    reference: Optional[str] = None
    sender: Optional[str] = None
    receiver: Optional[str] = None
    error: Optional[str] = None


VERIFICATION_PROMPT = """Tu es un système de vérification de paiement mobile Wave (Côte d'Ivoire).
Analyse cette capture d'écran de reçu de paiement et extrais les informations suivantes :

1. Est-ce un vrai reçu de paiement Wave valide ? (pas une image truquée, pas un simple screenshot d'un autre écran)
2. Le montant du paiement en FCFA (nombre entier)
3. La référence de transaction (si visible)
4. Le nom ou numéro de l'expéditeur
5. Le nom ou numéro du destinataire

Réponds UNIQUEMENT en JSON strict avec ce format exact, sans markdown ni texte autour :
{
  "is_valid_receipt": true/false,
  "amount": 5000,
  "reference": "TX-ABC123" ou null,
  "sender": "nom ou numéro" ou null,
  "receiver": "nom ou numéro" ou null,
  "confidence": 0.95,
  "reason": "Reçu Wave valide avec montant lisible"
}

Si ce n'est pas un reçu de paiement valide, mets is_valid_receipt à false et explique pourquoi dans reason.
"""


async def verify_with_gemini(image_bytes: bytes, mime_type: str) -> dict:
    """Send image to Gemini for multimodal verification."""
    try:
        import google.generativeai as genai

        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not configured")

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)

        # Encode image for Gemini
        image_part = {
            "mime_type": mime_type,
            "data": image_bytes,
        }

        response = model.generate_content(
            [VERIFICATION_PROMPT, image_part],
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=500,
            ),
        )

        text = response.text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        result = json.loads(text)
        return result

    except json.JSONDecodeError as e:
        logger.error(f"[PAYMENT_VERIFY] Gemini returned non-JSON: {e}")
        return {"is_valid_receipt": False, "reason": "Réponse Gemini invalide", "confidence": 0}
    except Exception as e:
        logger.error(f"[PAYMENT_VERIFY] Gemini error: {e}")
        return {"is_valid_receipt": False, "reason": f"Erreur vérification: {str(e)}", "confidence": 0}


@router.post("/verify", response_model=VerifyResponse)
async def verify_payment(
    file: UploadFile = File(...),
    expected_amount: Optional[int] = Form(None),
    company_id: Optional[str] = Form(None),
):
    """
    Verify a payment proof screenshot using Gemini multimodal.
    
    - **file**: The payment receipt image (PNG, JPG, WEBP)
    - **expected_amount**: Optional expected amount to cross-check
    - **company_id**: The merchant's company ID
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Le fichier doit être une image")

    # Read image
    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="Image trop volumineuse (max 10 Mo)")

    logger.info(f"[PAYMENT_VERIFY] Received proof: {file.filename} ({len(image_bytes)} bytes) company={company_id} expected={expected_amount}")

    # Verify with Gemini
    result = await verify_with_gemini(image_bytes, file.content_type)

    is_valid = result.get("is_valid_receipt", False)
    detected_amount = result.get("amount")
    confidence = result.get("confidence", 0)

    # Cross-check amount if expected_amount provided
    amount_match = True
    if expected_amount and detected_amount:
        # Allow 5% tolerance for rounding
        tolerance = max(100, expected_amount * 0.05)
        amount_match = abs(detected_amount - expected_amount) <= tolerance

    verified = is_valid and confidence >= 0.7 and amount_match

    if not amount_match and is_valid:
        logger.warning(
            f"[PAYMENT_VERIFY] Amount mismatch: expected={expected_amount}, detected={detected_amount}"
        )

    logger.info(
        f"[PAYMENT_VERIFY] Result: verified={verified} amount={detected_amount} "
        f"confidence={confidence} reason={result.get('reason')}"
    )

    return VerifyResponse(
        verified=verified,
        amount=detected_amount if verified else None,
        reference=result.get("reference"),
        sender=result.get("sender"),
        receiver=result.get("receiver"),
        error=None if verified else result.get("reason", "Vérification échouée"),
    )


@router.get("/health")
async def payment_health():
    """Health check for payment verification service."""
    return {
        "status": "ok",
        "gemini_configured": bool(GEMINI_API_KEY),
        "model": GEMINI_MODEL,
    }
