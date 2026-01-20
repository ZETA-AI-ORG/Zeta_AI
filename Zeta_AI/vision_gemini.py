import json
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

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


def _coerce_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        if isinstance(x, (int, float)):
            return float(x)
        s = str(x).strip()
        if not s:
            return None
        return float(s)
    except Exception:
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


def _parse_payment_datetime(raw: Optional[str]) -> Optional[datetime]:
    try:
        s = str(raw or "").strip()
        if not s:
            return None

        now = datetime.now()
        sl = s.lower()
        sl = sl.replace("à", " ").replace("h", "h")

        if "aujourd" in sl:
            m = re.search(r"(\d{1,2})\s*[h:]\s*(\d{2})", sl)
            if m:
                hh = int(m.group(1))
                mm = int(m.group(2))
                return datetime(now.year, now.month, now.day, hh, mm)
            return datetime(now.year, now.month, now.day)

        if "hier" in sl:
            m = re.search(r"(\d{1,2})\s*[h:]\s*(\d{2})", sl)
            base = datetime(now.year, now.month, now.day) - timedelta(days=1)
            if m:
                hh = int(m.group(1))
                mm = int(m.group(2))
                return datetime(base.year, base.month, base.day, hh, mm)
            return base

        month_map = {
            "jan": 1,
            "janv": 1,
            "fev": 2,
            "fév": 2,
            "fevr": 2,
            "févr": 2,
            "mar": 3,
            "mars": 3,
            "avr": 4,
            "avril": 4,
            "mai": 5,
            "jun": 6,
            "juin": 6,
            "jul": 7,
            "juil": 7,
            "aoû": 8,
            "aou": 8,
            "août": 8,
            "sep": 9,
            "sept": 9,
            "oct": 10,
            "nov": 11,
            "dec": 12,
            "déc": 12,
        }

        m = re.search(
            r"(?P<day>\d{1,2})\s*(?P<mon>[a-zéûôàù\.]{3,5})[\s,\.]*?(?P<hh>\d{1,2})\s*[h:]\s*(?P<mm>\d{2})",
            sl,
        )
        if m:
            day = int(m.group("day"))
            mon_s = m.group("mon").replace(".", "")
            mon_s = mon_s[:4] if len(mon_s) > 4 else mon_s
            mon = month_map.get(mon_s) or month_map.get(mon_s[:3])
            if mon:
                hh = int(m.group("hh"))
                mm = int(m.group("mm"))
                return datetime(now.year, mon, day, hh, mm)

        m = re.search(r"(?P<day>\d{1,2})\s*(?P<mon>[a-zéûôàù\.]{3,5})", sl)
        if m:
            day = int(m.group("day"))
            mon_s = m.group("mon").replace(".", "")
            mon_s = mon_s[:4] if len(mon_s) > 4 else mon_s
            mon = month_map.get(mon_s) or month_map.get(mon_s[:3])
            if mon:
                return datetime(now.year, mon, day)

        return None
    except Exception:
        return None


async def analyze_product_with_gemini(
    *,
    image_url: str,
    user_message: Optional[str] = None,
    company_phone: Optional[str] = None,
    required_amount: Optional[int] = None,
    model_name: Optional[str] = None,
    max_tokens: int = 450,
    temperature: float = 0.2,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    company_phone_raw = str(company_phone or "").strip()
    company_phone_norm10 = _normalize_phone_last10(company_phone_raw)

    normalized_company_phone_hint = company_phone_raw
    required_amount_hint = "" if required_amount is None else str(int(required_amount))

    prompt = (
        "Analyse cette image. Tu as 2 objectifs: "
        "(1) si c'est une photo de PRODUIT à commander, identifier le produit; "
        "(2) si c'est une CAPTURE DE PAIEMENT (Wave/Orange Money/MTN Money/etc.), appliquer la MÊME logique que notre OCR strict. "
        "\n\n"
        "IMPORTANT (paiement - logique OCR strict):\n"
        "- On te donne un NUMÉRO ENTREPRISE à retrouver dans l'image (après normalisation).\n"
        "- Normalisation téléphone: retire tous caractères non numériques, garde les 10 derniers chiffres.\n"
        "- Extrais TOUTES les transactions visibles (montant + destinataire + date/heure + référence si visible).\n"
        "- Filtre UNIQUEMENT les transactions dont le destinataire correspond au numéro entreprise normalisé.\n"
        "- Sélectionne la transaction la PLUS RÉCENTE (date/heure la plus récente si visible, sinon la dernière transaction clairement lisible).\n"
        "- Si un acompte minimum est fourni, la transaction sélectionnée doit avoir montant >= acompte minimum.\n"
        "\n"
        "CODES ERREUR (identiques OCR) à retourner dans payment.error_code si capture paiement détectée:\n"
        "- NUMERO_ABSENT: le numéro entreprise n'apparaît pas dans l'image.\n"
        "- TRANSACTION_ABSENTE: numéro entreprise visible mais aucune transaction vers ce numéro.\n"
        "- CAPTURE_INVALIDE: image de paiement mais trop floue/incomplète pour lire.\n"
        "- MONTANT_INSUFFISANT: montant détecté < acompte minimum.\n"
        "\n"
        "Entrées:")

    if normalized_company_phone_hint:
        prompt += f"\n- company_phone_raw: {normalized_company_phone_hint}"
    else:
        prompt += "\n- company_phone_raw: (non fourni)"

    if company_phone_norm10:
        prompt += f"\n- company_phone_normalized_last10: {company_phone_norm10}"
    else:
        prompt += "\n- company_phone_normalized_last10: (non fourni)"

    if required_amount_hint:
        prompt += f"\n- required_amount: {required_amount_hint}"
    else:
        prompt += "\n- required_amount: (non fourni)"

    prompt += (
        "\n\n"
        "FORMAT DE SORTIE (obligatoire): retourne UNIQUEMENT un JSON valide avec exactement ces clés racines:\n"
        "- IMPORTANT: ne mets PAS le JSON dans un bloc ``` (aucun code fence).\n"
        "- name (string)\n"
        "- confidence (number entre 0 et 1)\n"
        "- is_product_image (bool)\n"
        "- notes (string court)\n"
        "- payment (object|null)\n"
        "\n"
        "Règles:\n"
        "- Si produit: is_product_image=true, name non vide, confidence élevée, payment=null.\n"
        "- Si capture paiement: is_product_image=false, name=\"\", confidence=0, payment non-null (avec verdict).\n"
        "- Si image floue/indécidable: is_product_image=false, name=\"\", confidence=0, payment=null.\n"
        "\n"
        "Le champ payment (quand présent) DOIT être un objet JSON avec les clés:\n"
        "- error_code (string|null)\n"
        "- provider (string|null)\n"
        "- amount (number|null)\n"
        "- currency (string|null)\n"
        "- recipient_phone (string|null)\n"
        "- recipient_phone_normalized (string|null)\n"
        "- reference (string|null)\n"
        "- date_time (string|null)\n"
        "- required_amount (number|null)\n"
        "- detected_amount (number|null)\n"
        "- transactions (array|null)\n"
        "\n"
        "CRITIQUE (anti-bug récence):\n"
        "- payment.transactions doit contenir TOUTES les transactions vers le numéro entreprise (après normalisation), dans l'ORDRE affiché à l'écran (de haut en bas).\n"
        "- Chaque item de transactions doit contenir: amount, currency, recipient_phone, recipient_phone_normalized, reference, date_time.\n"
        "- Ne choisis PAS toi-même une transaction 'au hasard': liste-les toutes.\n"
    )
    if user_message:
        prompt = prompt + "\n\nContexte utilisateur: " + str(user_message).strip()

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        }
    ]

    text, meta = await complete(
        prompt="",
        model_name=model_name,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=1.0,
        messages=messages,
    )

    parsed = _extract_first_json_object(text)
    if not isinstance(parsed, dict) and int(max_tokens or 0) < 1200:
        text2, meta2 = await complete(
            prompt="",
            model_name=model_name,
            max_tokens=1200,
            temperature=temperature,
            top_p=1.0,
            messages=messages,
        )
        parsed = _extract_first_json_object(text2)
        if isinstance(parsed, dict):
            text = text2
            meta = meta2
    if not isinstance(parsed, dict):
        fallback_name = (text or "").strip()
        return (
            {
                "name": fallback_name,
                "confidence": None,
                "is_product_image": None,
                "notes": None,
                "raw": text,
                "error": "NON_JSON_RESPONSE",
            },
            meta or {},
        )

    name = str(parsed.get("name") or "").strip()
    is_product_image = parsed.get("is_product_image")
    if isinstance(is_product_image, str):
        v = is_product_image.strip().lower()
        is_product_image = v in {"1", "true", "yes", "y", "ok"}
    elif not isinstance(is_product_image, bool):
        is_product_image = None

    confidence = _coerce_float(parsed.get("confidence"))
    notes = parsed.get("notes")
    notes = str(notes).strip() if notes is not None else None

    payment = parsed.get("payment")
    payment_obj: Optional[Dict[str, Any]] = None
    if isinstance(payment, dict):
        transactions_raw = payment.get("transactions")
        transactions: Optional[List[Dict[str, Any]]] = None
        if isinstance(transactions_raw, list):
            tmp: List[Dict[str, Any]] = []
            for it in transactions_raw:
                if not isinstance(it, dict):
                    continue
                amt = _coerce_float(it.get("amount"))
                if amt is not None:
                    try:
                        amt = abs(float(amt))
                    except Exception:
                        pass
                tmp.append(
                    {
                        "amount": amt,
                        "currency": (str(it.get("currency")).strip() if it.get("currency") is not None else None),
                        "recipient_phone": (
                            str(it.get("recipient_phone")).strip()
                            if it.get("recipient_phone") is not None
                            else None
                        ),
                        "recipient_phone_normalized": (
                            str(it.get("recipient_phone_normalized")).strip()
                            if it.get("recipient_phone_normalized") is not None
                            else None
                        ),
                        "reference": (str(it.get("reference")).strip() if it.get("reference") is not None else None),
                        "date_time": (str(it.get("date_time")).strip() if it.get("date_time") is not None else None),
                    }
                )
            transactions = tmp or None

        payment_obj = {
            "error_code": (str(payment.get("error_code")).strip() if payment.get("error_code") is not None else None),
            "provider": (str(payment.get("provider")).strip() if payment.get("provider") is not None else None),
            "amount": _coerce_float(payment.get("amount")),
            "currency": (str(payment.get("currency")).strip() if payment.get("currency") is not None else None),
            "recipient_phone": (
                str(payment.get("recipient_phone")).strip() if payment.get("recipient_phone") is not None else None
            ),
            "recipient_phone_normalized": (
                str(payment.get("recipient_phone_normalized")).strip()
                if payment.get("recipient_phone_normalized") is not None
                else None
            ),
            "reference": (str(payment.get("reference")).strip() if payment.get("reference") is not None else None),
            "date_time": (str(payment.get("date_time")).strip() if payment.get("date_time") is not None else None),
            "required_amount": _coerce_float(payment.get("required_amount")),
            "detected_amount": _coerce_float(payment.get("detected_amount")),
            "transactions": transactions,
        }

        try:
            if transactions:
                best_idx = 0
                best_dt: Optional[datetime] = None
                for idx, tx in enumerate(transactions):
                    dt = _parse_payment_datetime(tx.get("date_time"))
                    if dt is None:
                        continue
                    if best_dt is None or dt > best_dt:
                        best_dt = dt
                        best_idx = idx

                chosen = transactions[best_idx]
                payment_obj["amount"] = chosen.get("amount")
                payment_obj["currency"] = chosen.get("currency") or payment_obj.get("currency")
                payment_obj["recipient_phone"] = chosen.get("recipient_phone")
                payment_obj["recipient_phone_normalized"] = chosen.get("recipient_phone_normalized")
                payment_obj["reference"] = chosen.get("reference")
                payment_obj["date_time"] = chosen.get("date_time")
                payment_obj["detected_amount"] = chosen.get("amount")
        except Exception:
            pass

        try:
            required_amt = _coerce_float(payment_obj.get("required_amount") if isinstance(payment_obj, dict) else None)
            detected_amt = _coerce_float(payment_obj.get("detected_amount") if isinstance(payment_obj, dict) else None)
            if required_amt is None:
                required_amt = _coerce_float(payment.get("required_amount"))
            if detected_amt is None:
                detected_amt = _coerce_float(payment.get("detected_amount"))
                if detected_amt is None:
                    detected_amt = _coerce_float(payment_obj.get("amount") if isinstance(payment_obj, dict) else None)

            if isinstance(payment_obj, dict) and required_amt is not None:
                payment_obj["required_amount"] = required_amt
                if detected_amt is not None:
                    payment_obj["detected_amount"] = detected_amt
                if detected_amt is not None and detected_amt < required_amt:
                    payment_obj["error_code"] = "MONTANT_INSUFFISANT"
        except Exception:
            pass

        try:
            if str(os.getenv("GEMINI_RETURN_TRANSACTIONS", "false") or "").strip().lower() != "true":
                if isinstance(payment_obj, dict):
                    payment_obj.pop("transactions", None)
        except Exception:
            pass

    return (
        {
            "name": name,
            "confidence": confidence,
            "is_product_image": is_product_image,
            "notes": notes,
            "payment": payment_obj,
            "raw": text,
            "error": None,
        },
        meta or {},
    )
