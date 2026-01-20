import json
import os
import re
import asyncio
from hashlib import sha256
from typing import Any, Dict, List, Optional, Tuple

import httpx
from PIL import Image

from core.llm_client_openrouter import complete


def _extract_first_json_object(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None

    t = text.strip()

    try:
        if "```" in t:
            m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", t, flags=re.IGNORECASE)
            if m:
                t = m.group(1).strip()
    except Exception:
        pass

    try:
        obj = json.loads(t)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    try:
        m = re.search(r"\{[\s\S]*\}", t)
        if m:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict):
                return obj
    except Exception:
        pass

    return None


def _normalize_phone_last10(phone_str: Optional[str]) -> str:
    try:
        s = str(phone_str or "").strip()
        if not s:
            return ""
        digits = re.sub(r"[^\d]", "", s)
        if not digits:
            return ""
        return digits[-10:] if len(digits) >= 10 else digits
    except Exception:
        return ""


async def _fetch_image_bytes(image_url: str) -> Tuple[Optional[bytes], Dict[str, Any]]:
    meta: Dict[str, Any] = {}
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.facebook.com/",
        }
        timeout = float(os.getenv("PAYMENT_FORENSIC_HTTP_TIMEOUT", "10") or "10")
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(image_url, headers=headers)
            meta["http_status"] = resp.status_code
            meta["content_type"] = resp.headers.get("content-type")
            meta["content_length"] = resp.headers.get("content-length")
            resp.raise_for_status()
            b = bytes(resp.content)
            meta["bytes_len"] = len(b)
            meta["sha256"] = sha256(b).hexdigest()
            return b, meta
    except Exception as e:
        meta["error"] = f"{type(e).__name__}: {e}"
        return None, meta


def _image_basic_metadata(image_bytes: bytes) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    try:
        import io

        img = Image.open(io.BytesIO(image_bytes))
        out["format"] = str(getattr(img, "format", "") or "").upper() or None
        out["mode"] = str(getattr(img, "mode", "") or "") or None
        out["width"] = int(img.size[0])
        out["height"] = int(img.size[1])
    except Exception:
        return out

    return out


async def validate_payment_authenticity(
    *,
    image_url: str,
    payment_data: Dict[str, Any],
    company_phone: Optional[str] = None,
    required_amount: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Returns:
        {
            "is_authentic": bool,
            "fraud_score": float (0-1),
            "red_flags": list[str],
            "validation_details": dict
        }
    """

    red_flags: List[str] = []
    details: Dict[str, Any] = {
        "visual_analysis": {},
        "metadata_check": {},
        "cross_validation": {},
        "pattern_matching": {},
        "behavior": {},
    }

    try:
        if required_amount is None:
            required_amount = float(payment_data.get("required_amount")) if payment_data.get("required_amount") is not None else None
    except Exception:
        required_amount = None

    company_phone_norm10 = _normalize_phone_last10(company_phone)
    recipient_norm10 = _normalize_phone_last10(payment_data.get("recipient_phone") or payment_data.get("recipient_phone_normalized"))

    if company_phone_norm10 and recipient_norm10 and company_phone_norm10 != recipient_norm10:
        red_flags.append("NUMERO_INCOHERENT")
        details["cross_validation"]["recipient_phone_mismatch"] = True

    image_bytes, fetch_meta = await _fetch_image_bytes(image_url)
    details["metadata_check"]["fetch"] = fetch_meta

    if not image_bytes:
        return {
            "is_authentic": False,
            "fraud_score": 0.8,
            "verdict": "FRAUDE_PROBABLE",
            "red_flags": list(dict.fromkeys(red_flags + ["IMAGE_FETCH_FAILED"])),
            "validation_details": details,
        }

    img_meta = _image_basic_metadata(image_bytes)
    details["metadata_check"]["image"] = img_meta

    try:
        w = int(img_meta.get("width") or 0)
        h = int(img_meta.get("height") or 0)
        if w and h:
            if w < 720 or h < 720:
                red_flags.append("METADATA_FORTE")
                details["metadata_check"]["low_resolution"] = True
            ratio = (w / h) if h else 0
            if ratio and (ratio < 0.35 or ratio > 0.9):
                red_flags.append("METADATA_FORTE")
                details["metadata_check"]["unusual_aspect_ratio"] = True
    except Exception:
        pass

    fmt = str(img_meta.get("format") or "").upper()
    if fmt == "PNG":
        red_flags.append("METADATA_LEGERE")
        details["metadata_check"]["format_png"] = True

    try:
        bytes_len = int(fetch_meta.get("bytes_len") or 0)
        if bytes_len and bytes_len < 30_000:
            red_flags.append("METADATA_LEGERE")
            details["metadata_check"]["very_small_file"] = True
        if bytes_len and bytes_len > 8_000_000:
            red_flags.append("METADATA_FORTE")
            details["metadata_check"]["very_large_file"] = True
    except Exception:
        pass

    try:
        signals = payment_data.get("signals") if isinstance(payment_data, dict) else None
        signals = signals if isinstance(signals, dict) else {}
        ocr_ok = bool(signals.get("ocr_ok"))
        gem_ok = bool(signals.get("gem_ok"))
        ocr_amount = signals.get("ocr_amount")
        gem_amount = signals.get("gem_amount")
        details["cross_validation"].update(
            {
                "ocr_ok": ocr_ok,
                "gem_ok": gem_ok,
                "ocr_amount": ocr_amount,
                "gem_amount": gem_amount,
            }
        )

        if (ocr_ok and not gem_ok) or (gem_ok and not ocr_ok):
            red_flags.append("DETECTION_PARTIELLE")

        try:
            if ocr_ok and gem_ok and ocr_amount is not None and gem_amount is not None:
                diff = abs(int(ocr_amount) - int(gem_amount))
                details["cross_validation"]["amount_diff"] = diff
                if diff > 100:
                    red_flags.append("MONTANT_INCOHERENT")
        except Exception:
            pass
    except Exception:
        pass

    try:
        if required_amount is not None:
            detected_amt = payment_data.get("detected_amount")
            if detected_amt is None:
                detected_amt = payment_data.get("amount")
            detected_amt_f = float(detected_amt) if detected_amt is not None else None
            details["behavior"]["required_amount"] = required_amount
            details["behavior"]["detected_amount"] = detected_amt_f
            if detected_amt_f is not None and detected_amt_f > (required_amount * 10):
                red_flags.append("COMPORTEMENT_ANORMAL")
                details["behavior"]["unusually_high_amount"] = True
    except Exception:
        pass

    forensic_prompt = (
        "Tu es un expert forensic anti-fraude. Analyse UNIQUEMENT cette capture d'écran de paiement mobile money. "
        "Ton objectif: détecter si la capture semble authentique ou éditée (photoshop/paint).\n\n"
        "Indices à vérifier (liste non exhaustive):\n"
        "- Incohérences de police, alignement, espacements, anti-aliasing\n"
        "- Zones floues autour du montant/date/numéro, pixels bizarres, artefacts de collage\n"
        "- Couleurs/logo/layout incohérents avec l'app (Wave/Orange/MTN)\n"
        "- Incohérences internes: date/heure, montant, numéro destinataire\n\n"
        "Contrainte: retourne UNIQUEMENT un JSON valide (pas de ```), avec exactement ces clés:\n"
        "- edition_detectee (bool|null)\n"
        "- pattern_valid (bool|null)\n"
        "- provider_guess (string|null)\n"
        "- red_flags (array de strings)\n"
        "- notes (string court)\n\n"
        "Règles: si tu vois des signes d'édition, mets edition_detectee=true et ajoute 'EDITION_DETECTEE' dans red_flags.\n"
        "Si le design/layout ne correspond pas au provider, mets pattern_valid=false et ajoute 'PATTERN_INVALIDE'.\n\n"
        "Contexte (données extraites en amont):\n"
        f"- company_phone_normalized_last10: {company_phone_norm10 or '(non fourni)'}\n"
        f"- required_amount: {required_amount if required_amount is not None else '(non fourni)'}\n"
        f"- payment_data: {json.dumps(payment_data, ensure_ascii=False)}\n"
        f"- image_meta: {json.dumps(img_meta, ensure_ascii=False)}\n"
    )

    model_name = os.getenv("PAYMENT_FORENSIC_MODEL") or "google/gemini-2.5-flash-lite"
    max_tokens = int(os.getenv("PAYMENT_FORENSIC_MAX_TOKENS", "450") or "450")

    try:
        forensic_timeout_s = float(os.getenv("PAYMENT_FORENSIC_TIMEOUT_SECONDS", "8") or "8")
    except Exception:
        forensic_timeout_s = 8.0

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": forensic_prompt},
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        }
    ]

    try:
        text, llm_meta = await asyncio.wait_for(
            complete(
                prompt="",
                model_name=model_name,
                max_tokens=max_tokens,
                temperature=0.1,
                top_p=1.0,
                messages=messages,
            ),
            timeout=forensic_timeout_s,
        )
    except asyncio.TimeoutError:
        combined = list(dict.fromkeys(red_flags + ["FORENSIC_TIMEOUT"]))
        fraud_score = _compute_fraud_score(combined)
        # UX-first: ne pas bloquer si timeout -> score clamp à 0 (mais flag conservé)
        fraud_score = 0.0
        verdict = "AUTHENTIQUE"
        return {
            "is_authentic": True,
            "fraud_score": fraud_score,
            "verdict": verdict,
            "red_flags": combined,
            "validation_details": {**details, "llm": {"raw": None, "meta": {"error": "TIMEOUT"}}},
        }

    parsed = _extract_first_json_object(text)
    if not isinstance(parsed, dict):
        combined = list(dict.fromkeys(red_flags + ["FORENSIC_NON_JSON"]))
        fraud_score = _compute_fraud_score(combined)
        verdict = _verdict_from_score(fraud_score)
        return {
            "is_authentic": verdict == "AUTHENTIQUE",
            "fraud_score": fraud_score,
            "verdict": verdict,
            "red_flags": combined,
            "validation_details": {**details, "llm": {"raw": text, "meta": llm_meta}},
        }

    llm_flags_list: List[str] = []
    try:
        llm_flags = parsed.get("red_flags")
        if isinstance(llm_flags, list):
            for f in llm_flags:
                if isinstance(f, str) and f.strip():
                    llm_flags_list.append(f.strip())
    except Exception:
        pass

    try:
        edition_detectee = parsed.get("edition_detectee")
        if isinstance(edition_detectee, str):
            edition_detectee = edition_detectee.strip().lower() in {"1", "true", "yes", "y"}
        if edition_detectee is True:
            llm_flags_list.append("EDITION_DETECTEE")
        details["visual_analysis"]["edition_detectee"] = (True if edition_detectee is True else False if edition_detectee is False else None)
    except Exception:
        pass

    try:
        pattern_valid = parsed.get("pattern_valid")
        if isinstance(pattern_valid, str):
            pattern_valid = pattern_valid.strip().lower() in {"1", "true", "yes", "y"}
        if pattern_valid is False:
            llm_flags_list.append("PATTERN_INVALIDE")
        details["pattern_matching"]["pattern_valid"] = (True if pattern_valid is True else False if pattern_valid is False else None)
    except Exception:
        pass

    try:
        details["pattern_matching"]["provider_guess"] = parsed.get("provider_guess")
    except Exception:
        pass

    try:
        details["visual_analysis"]["notes"] = parsed.get("notes")
    except Exception:
        pass

    for f in llm_flags_list:
        red_flags.append(f)

    red_flags = list(dict.fromkeys(red_flags))
    details["llm"] = {"meta": llm_meta}

    fraud_score = _compute_fraud_score(red_flags)
    verdict = _verdict_from_score(fraud_score)

    return {
        "is_authentic": verdict == "AUTHENTIQUE",
        "fraud_score": fraud_score,
        "verdict": verdict,
        "red_flags": red_flags,
        "validation_details": details,
    }


def _compute_fraud_score(red_flags: List[str]) -> float:
    score = 0.0
    flags = {str(f or "").strip().upper() for f in (red_flags or [])}

    if "EDITION_DETECTEE" in flags:
        score += 0.4
    if "METADATA_LEGERE" in flags:
        score += 0.1
    if "METADATA_FORTE" in flags:
        score += 0.3
    if "MONTANT_INCOHERENT" in flags:
        score += 0.2
    if "PATTERN_INVALIDE" in flags:
        score += 0.15
    if "COMPORTEMENT_ANORMAL" in flags:
        score += 0.1

    if "DETECTION_PARTIELLE" in flags:
        score += 0.2
    if "NUMERO_INCOHERENT" in flags:
        score += 0.4

    if "IMAGE_FETCH_FAILED" in flags:
        score = max(score, 0.8)
    if "FORENSIC_NON_JSON" in flags:
        score = max(score, 0.7)

    return max(0.0, min(1.0, score))


def _verdict_from_score(score: float) -> str:
    try:
        s = float(score)
    except Exception:
        s = 1.0
    if s > 0.5:
        return "FRAUDE_PROBABLE"
    if s > 0.3:
        return "VERIFICATION_MANUELLE"
    return "AUTHENTIQUE"
