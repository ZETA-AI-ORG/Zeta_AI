"""
Payment Verification Route v2
Multi-level Wave receipt verification using Gemini multimodal.

Levels:
  1. Documentary validity (Wave receipt, status, amount, merchant, tx_id)
  2. Anti-replay (tx_id uniqueness, image hash, composite key)
  3. Temporal coherence (pay_clicked_at ↔ uploaded_at ↔ receipt datetime)
  4. Buyer identity (sender coherence)
  5. Visual integrity (tampering signals from Gemini)
  6. Quality & legibility (confidence threshold)

Returns: { decision: approved|manual_review|rejected, ... }
"""

import os
import re
import base64
import hashlib
import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, List
import httpx
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("payment_verify")

router = APIRouter(prefix="/api/payment", tags=["Payment Verification"])

# ── Config ──
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_BOTLIVE_MODEL", "google/gemini-2.5-flash")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY", "")
MAX_DELAY_SECONDS = 600  # 10 minutes
RATE_LIMIT_MAX = 3       # max attempts per window
RATE_LIMIT_WINDOW = 30   # minutes

# ── Response model ──
class VerifyResponse(BaseModel):
    decision: str  # approved | manual_review | rejected
    decision_reasons: List[str] = []
    risk_score: float = 0.0
    amount: Optional[int] = None
    reference: Optional[str] = None
    sender: Optional[str] = None
    receiver: Optional[str] = None
    confidence: float = 0.0
    receipt_datetime: Optional[str] = None
    # Legacy compat
    verified: bool = False
    error: Optional[str] = None


# ── Gemini prompt ──
VERIFICATION_PROMPT = """Tu es un système anti-fraude spécialisé dans la vérification de reçus de paiement mobile Wave (Côte d'Ivoire / Sénégal).

Analyse cette capture d'écran avec une EXTRÊME RIGUEUR et extrais TOUTES les informations suivantes.

Réponds UNIQUEMENT en JSON strict (sans markdown, sans texte autour) avec ce format exact :
{
  "is_wave_receipt": true/false,
  "transaction_type": "Paiement marchand" | "Transfert" | "Retrait" | "Dépôt" | "Autre" | null,
  "status": "Effectué" | "En attente" | "Échoué" | null,
  "amount": 1000,
  "currency": "FCFA",
  "merchant_name": "ZETA" ou null,
  "transaction_id": "TX-XXXXX" ou null,
  "datetime": "2026-04-12T14:30:00" ou null,
  "fees": 0,
  "sender_name": "nom" ou null,
  "sender_phone": "numéro" ou null,

  "image_quality": "high" | "medium" | "low",
  "is_legible": true/false,
  "tampering_signals": {
    "inconsistent_fonts": false,
    "overlay_detected": false,
    "suspicious_cropping": false,
    "abnormal_compression": false,
    "edited_pixels": false,
    "screenshot_of_screenshot": false
  },
  "fraud_risk": "none" | "low" | "medium" | "high",
  "confidence": 0.95,
  "reason": "Description courte du verdict"
}

RÈGLES CRITIQUES :
- Si ce n'est PAS un reçu Wave → is_wave_receipt: false
- Le montant doit être un ENTIER en FCFA, pas de décimales
- transaction_id : copie l'ID exact tel qu'affiché, même partiel
- datetime : format ISO si lisible, sinon null
- Sois TRÈS attentif aux signaux de falsification (polices incohérentes, artefacts de compression, superpositions)
- confidence entre 0.0 et 1.0
"""


# ── Supabase helpers ──
async def _supabase_query(table: str, params: dict, method: str = "GET", body: dict = None) -> dict:
    """Execute a Supabase REST query."""
    import httpx
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    async with httpx.AsyncClient(timeout=10) as client:
        if method == "GET":
            resp = await client.get(url, headers=headers, params=params)
        elif method == "POST":
            resp = await client.post(url, headers=headers, json=body, params=params)
        else:
            resp = await client.request(method, url, headers=headers, json=body, params=params)
        return {"status": resp.status_code, "data": resp.json() if resp.status_code < 300 else None, "error": resp.text if resp.status_code >= 300 else None}


async def check_anti_replay(tx_id: Optional[str], image_hash: str, tx_suffix: Optional[str], amount: Optional[int], merchant: Optional[str]) -> List[str]:
    """Check payment_verifications for duplicates. Returns list of reasons if replay detected."""
    reasons = []
    if not SUPABASE_URL:
        return reasons

    # Check image hash
    res = await _supabase_query("payment_verifications", {"image_hash": f"eq.{image_hash}", "select": "id", "limit": "1"})
    if res["data"] and len(res["data"]) > 0:
        reasons.append("IMAGE_DEJA_UTILISEE")

    # Check transaction ID
    if tx_id:
        res = await _supabase_query("payment_verifications", {"transaction_id": f"eq.{tx_id}", "select": "id", "limit": "1"})
        if res["data"] and len(res["data"]) > 0:
            reasons.append("TRANSACTION_ID_DEJA_UTILISE")

    # Check composite: suffix + amount + merchant
    if tx_suffix and amount and merchant:
        res = await _supabase_query("payment_verifications", {
            "transaction_id_suffix": f"eq.{tx_suffix}",
            "receipt_amount": f"eq.{amount}",
            "receipt_merchant": f"eq.{merchant}",
            "select": "id", "limit": "1",
        })
        if res["data"] and len(res["data"]) > 0 and "IMAGE_DEJA_UTILISEE" not in reasons and "TRANSACTION_ID_DEJA_UTILISE" not in reasons:
            reasons.append("COMBINAISON_DEJA_VUE")

    return reasons


_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)

async def store_verification(record: dict):
    """Store verification attempt in payment_verifications table."""
    if not SUPABASE_URL:
        logger.warning("[PAYMENT_VERIFY] SUPABASE_URL not set, skipping store")
        return
    company_id = record.get("company_id", "") or ""
    if not _UUID_RE.match(str(company_id)):
        logger.info(f"[PAYMENT_VERIFY] Store skipped: company_id not UUID ({company_id})")
        return
    try:
        res = await _supabase_query("payment_verifications", {}, method="POST", body=record)
        if res["error"]:
            logger.error(f"[PAYMENT_VERIFY] Store error: {res['error']}")
        else:
            logger.info("[PAYMENT_VERIFY] Verification stored successfully")
    except Exception as e:
        logger.error(f"[PAYMENT_VERIFY] Store exception: {e}")


# ── OpenRouter vision call ──
async def verify_with_gemini(image_bytes: bytes, mime_type: str) -> dict:
    """Send image to Gemini via OpenRouter for multimodal verification."""
    try:
        if not OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY not configured")

        image_b64 = base64.b64encode(image_bytes).decode()

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://api.zetaapp.xyz",
                    "X-Title": "Zeta AI Payment Verify",
                },
                json={
                    "model": OPENROUTER_MODEL,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": VERIFICATION_PROMPT},
                            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_b64}"}},
                        ],
                    }],
                    "temperature": 0.1,
                    "max_tokens": 800,
                },
            )

        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"].strip()

        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        return json.loads(text)

    except json.JSONDecodeError as e:
        logger.error(f"[PAYMENT_VERIFY] OpenRouter non-JSON: {e}")
        return {"is_wave_receipt": False, "reason": "Réponse IA invalide", "confidence": 0}
    except Exception as e:
        logger.error(f"[PAYMENT_VERIFY] OpenRouter error: {e}")
        return {"is_wave_receipt": False, "reason": f"Erreur vérification: {str(e)}", "confidence": 0}


# ── Main endpoint ──
@router.post("/verify", response_model=VerifyResponse)
async def verify_payment(
    file: UploadFile = File(...),
    expected_amount: Optional[int] = Form(None),
    expected_merchant: Optional[str] = Form("ZETA"),
    company_id: Optional[str] = Form(None),
    payment_session_id: Optional[str] = Form(None),
    pay_clicked_at: Optional[str] = Form(None),
    offer_type: Optional[str] = Form(None),
    plan_id: Optional[str] = Form(None),
):
    """
    Verify a Wave payment receipt screenshot using Gemini multimodal.
    Returns a 3-level decision: approved, manual_review, or rejected.
    """
    # ── Validate file ──
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Le fichier doit être une image")

    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image trop volumineuse (max 10 Mo)")

    uploaded_at = datetime.now(timezone.utc)
    image_hash = hashlib.sha256(image_bytes).hexdigest()

    logger.info(
        f"[PAYMENT_VERIFY] Received: {file.filename} ({len(image_bytes)}B) "
        f"company={company_id} expected={expected_amount} session={payment_session_id}"
    )

    # ── PRE-CHECK: Rate limiting (3 attempts / 30 min per company_id) ──
    if company_id and SUPABASE_URL:
        try:
            window_start = (uploaded_at - timedelta(minutes=RATE_LIMIT_WINDOW)).isoformat()
            rl_res = await _supabase_query("payment_attempts", {
                "company_id": f"eq.{company_id}",
                "created_at": f"gte.{window_start}",
                "select": "id",
            })
            recent_count = len(rl_res.get("data") or []) if rl_res.get("data") else 0
            if recent_count >= RATE_LIMIT_MAX:
                logger.warning(f"[PAYMENT_VERIFY] Rate limited: {company_id} ({recent_count} attempts in {RATE_LIMIT_WINDOW}min)")
                # Log the blocked attempt
                await _log_payment_attempt(company_id, image_hash, file.filename, len(image_bytes), file.content_type, "rate_limited")
                return VerifyResponse(
                    decision="rejected",
                    decision_reasons=["TOO_MANY_ATTEMPTS"],
                    risk_score=2.0,
                    verified=False,
                    error="Trop de tentatives. Réessayez dans 30 minutes.",
                )
        except Exception as e:
            logger.warning(f"[PAYMENT_VERIFY] Rate limit check failed (non-blocking): {e}")

    # ── PRE-CHECK: Duplicate file hash ──
    if SUPABASE_URL:
        try:
            dup_res = await _supabase_query("payment_attempts", {
                "file_hash": f"eq.{image_hash}",
                "status": f"neq.rate_limited",
                "select": "id",
                "limit": "1",
            })
            if dup_res.get("data") and len(dup_res["data"]) > 0:
                logger.warning(f"[PAYMENT_VERIFY] Duplicate hash detected: {image_hash[:16]}...")
                await _log_payment_attempt(company_id or "unknown", image_hash, file.filename, len(image_bytes), file.content_type, "duplicate")
                return VerifyResponse(
                    decision="rejected",
                    decision_reasons=["DUPLICATE_FILE"],
                    risk_score=2.0,
                    verified=False,
                    error="Ce reçu a déjà été soumis.",
                )
        except Exception as e:
            logger.warning(f"[PAYMENT_VERIFY] Duplicate check failed (non-blocking): {e}")

    # ── Log attempt as processing ──
    await _log_payment_attempt(company_id or "unknown", image_hash, file.filename, len(image_bytes), file.content_type, "processing")

    # ── Call Gemini ──
    gemini = await verify_with_gemini(image_bytes, file.content_type)

    reasons: List[str] = []
    risk = 0.0

    # ── LEVEL 1: Documentary validity ──
    if not gemini.get("is_wave_receipt", False):
        reasons.append("PAS_UN_RECU_WAVE")
        risk += 1.0

    status = gemini.get("status")
    if status and status != "Effectué":
        reasons.append(f"STATUT_INVALIDE:{status}")
        risk += 1.0

    detected_amount = gemini.get("amount")
    if expected_amount and detected_amount and detected_amount != expected_amount:
        reasons.append(f"MONTANT_INCORRECT:attendu={expected_amount},detecte={detected_amount}")
        risk += 1.0

    merchant = gemini.get("merchant_name") or ""
    if expected_merchant and merchant.upper().strip() != expected_merchant.upper().strip():
        reasons.append(f"MARCHAND_INCORRECT:attendu={expected_merchant},detecte={merchant}")
        risk += 0.8

    tx_id = gemini.get("transaction_id")
    if not tx_id:
        reasons.append("TRANSACTION_ID_ABSENT")
        risk += 0.5

    receipt_dt_str = gemini.get("datetime")
    if not receipt_dt_str:
        reasons.append("DATETIME_ABSENT")
        risk += 0.3

    # ── LEVEL 2: Anti-replay ──
    tx_suffix = tx_id[-6:] if tx_id and len(tx_id) >= 6 else tx_id
    replay_reasons = await check_anti_replay(tx_id, image_hash, tx_suffix, detected_amount, merchant)
    if replay_reasons:
        reasons.extend(replay_reasons)
        risk += 2.0

    # ── LEVEL 3: Temporal coherence ──
    delay_seconds = None
    if pay_clicked_at:
        try:
            clicked = datetime.fromisoformat(pay_clicked_at.replace("Z", "+00:00"))
            if clicked.tzinfo is None:
                clicked = clicked.replace(tzinfo=timezone.utc)
            delay_seconds = int((uploaded_at - clicked).total_seconds())

            if delay_seconds > MAX_DELAY_SECONDS:
                reasons.append(f"DELAI_TROP_LONG:{delay_seconds}s")
                risk += 0.8
            elif delay_seconds < 0:
                reasons.append("TIMESTAMP_INCOHERENT")
                risk += 1.0
        except Exception:
            logger.warning("[PAYMENT_VERIFY] Could not parse pay_clicked_at")

    if receipt_dt_str and pay_clicked_at:
        try:
            receipt_dt = datetime.fromisoformat(receipt_dt_str.replace("Z", "+00:00"))
            clicked = datetime.fromisoformat(pay_clicked_at.replace("Z", "+00:00"))
            if receipt_dt.tzinfo is None:
                receipt_dt = receipt_dt.replace(tzinfo=timezone.utc)
            if clicked.tzinfo is None:
                clicked = clicked.replace(tzinfo=timezone.utc)
            diff = abs((receipt_dt - clicked).total_seconds())
            if diff > MAX_DELAY_SECONDS:
                reasons.append(f"DATE_RECU_INCOHERENTE:diff={int(diff)}s")
                risk += 0.6
        except Exception:
            pass

    if receipt_dt_str:
        try:
            receipt_dt = datetime.fromisoformat(receipt_dt_str.replace("Z", "+00:00"))
            if receipt_dt.date() != uploaded_at.date():
                reasons.append("DATE_RECU_PAS_AUJOURDHUI")
                risk += 0.5
        except Exception:
            pass

    # ── LEVEL 4: Buyer identity (informational) ──
    sender = gemini.get("sender_name") or gemini.get("sender_phone")

    # ── LEVEL 5: Visual integrity ──
    tampering = gemini.get("tampering_signals", {})
    tampering_flags = [k for k, v in tampering.items() if v is True]
    if tampering_flags:
        reasons.append(f"FALSIFICATION_DETECTEE:{','.join(tampering_flags)}")
        risk += 0.5 * len(tampering_flags)

    fraud_risk = gemini.get("fraud_risk", "none")
    if fraud_risk in ("medium", "high"):
        reasons.append(f"RISQUE_FRAUDE_GEMINI:{fraud_risk}")
        risk += 1.0 if fraud_risk == "high" else 0.5

    # ── LEVEL 6: Quality & legibility ──
    confidence = gemini.get("confidence", 0)
    if not gemini.get("is_legible", True):
        reasons.append("IMAGE_ILLISIBLE")
        risk += 0.5

    quality = gemini.get("image_quality", "medium")
    if quality == "low":
        reasons.append("QUALITE_IMAGE_BASSE")
        risk += 0.3

    # ── Decision logic ──
    if risk >= 1.5 or any(r.startswith(("PAS_UN_RECU", "STATUT_INVALIDE", "MONTANT_INCORRECT", "IMAGE_DEJA", "TRANSACTION_ID_DEJA")) for r in reasons):
        decision = "rejected"
    elif risk >= 0.5 or confidence < 0.8:
        decision = "manual_review"
    else:
        decision = "approved"

    verified = decision == "approved"

    logger.info(
        f"[PAYMENT_VERIFY] Decision={decision} risk={risk:.1f} confidence={confidence} "
        f"amount={detected_amount} tx={tx_id} reasons={reasons}"
    )

    # ── Store in payment_verifications ──
    # ── Update payment_attempt status ──
    try:
        if SUPABASE_URL:
            await _supabase_query("payment_attempts", {
                "file_hash": f"eq.{image_hash}",
                "status": f"eq.processing",
            }, method="PATCH", body={
                "status": "ocr_success" if verified else "ocr_failed",
                "decision": decision,
                "raw_ocr_result": gemini,
            })
    except Exception as e:
        logger.warning(f"[PAYMENT_VERIFY] Failed to update payment_attempt: {e}")

    try:
        await store_verification({
            "company_id": company_id,
            "payment_session_id": payment_session_id,
            "offer_type": offer_type,
            "plan_id": plan_id,
            "expected_amount": expected_amount,
            "expected_merchant": expected_merchant,
            "pay_clicked_at": pay_clicked_at,
            "uploaded_at": uploaded_at.isoformat(),
            "delay_seconds": delay_seconds,
            "transaction_id": tx_id,
            "transaction_id_suffix": tx_suffix,
            "receipt_amount": detected_amount,
            "receipt_merchant": merchant or None,
            "receipt_datetime": receipt_dt_str,
            "receipt_status": status,
            "receipt_sender": sender,
            "receipt_fees": gemini.get("fees"),
            "image_hash": image_hash,
            "gemini_payload": gemini,
            "decision": decision,
            "decision_reasons": reasons,
            "risk_score": round(risk, 2),
            "confidence": confidence,
        })
    except Exception as e:
        logger.error(f"[PAYMENT_VERIFY] Failed to store verification: {e}")

    return VerifyResponse(
        decision=decision,
        decision_reasons=reasons,
        risk_score=round(risk, 2),
        amount=detected_amount,
        reference=tx_id,
        sender=sender,
        receiver=merchant,
        confidence=confidence,
        receipt_datetime=receipt_dt_str,
        verified=verified,
        error=None if verified else (gemini.get("reason") or "; ".join(reasons) or "Vérification échouée"),
    )


async def _log_payment_attempt(company_id: str, file_hash: str, file_name: str, file_size: int, mime_type: str, status: str):
    """Log a payment attempt in the payment_attempts table."""
    if not SUPABASE_URL:
        return
    try:
        await _supabase_query("payment_attempts", {}, method="POST", body={
            "company_id": company_id,
            "file_hash": file_hash,
            "file_name": file_name,
            "file_size": file_size,
            "mime_type": mime_type,
            "status": status,
        })
    except Exception as e:
        logger.warning(f"[PAYMENT_VERIFY] Failed to log attempt: {e}")


@router.get("/health")
async def payment_health():
    """Health check for payment verification service."""
    return {
        "status": "ok",
        "gemini_configured": bool(OPENROUTER_API_KEY),
        "model": OPENROUTER_MODEL,
    }
