import asyncio
import os
import tempfile
import time

import requests

from dotenv import load_dotenv

from Zeta_AI.vision_gemini import analyze_product_with_gemini


load_dotenv()


TEST_IMAGES = {
    "produit": "https://scontent-atl3-1.xx.fbcdn.net/v/t1.15752-9/606980593_2273401639829812_4894506129511960265_n.jpg?_nc_cat=106&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=FmmSzPcx2REQ7kNvwErnOmq&_nc_oc=Adni5GjdIrxHlewIqYObOSD9Xo0pUG5DJTd4szXpnB_5w-wExNxPmELcbQSO0t2TKoorn25yYRG5IgjgAH4GTSZJ&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent-atl3-1.xx&oh=03_Q7cD4QEsdnTDlFjMGQmxCrqQOeLqGkiyq7M8qkJKiHOed2l7jA&oe=697E1F80",
    "paiement": "https://scontent-atl3-3.xx.fbcdn.net/v/t1.15752-9/597360982_1522361755643073_1046808360937074239_n.jpg?_nc_cat=109&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=hb7QgNIX-GUQ7kNvwGvvtuj&_nc_oc=AdkTUqx9yhjXuGQoB6MjjgODELCqDVx5xJcbFBDiIBwzhWq-datbBB2fNyvGMLyTD8muFGJIojldBlFi-dcNYN18&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent-atl3-3.xx&oh=03_Q7cD4AGscacRxk_JHwC6eQflUC5FNq4YADPaVuKzZ33-sLCmng&oe=6961323F",
    "paiement_insuffisant": "https://scontent.xx.fbcdn.net/v/t1.15752-9/582949854_1524325675515592_1712402945374325664_n.jpg?_nc_cat=107&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=brNHcmG2PkUQ7kNvwG9c3oX&_nc_oc=AdnFlJc_jyF9Svs8lkVKjOtaM2w99-edoFB14QuA7OTcTqezTahqQfHaB0yxRYMSF0DJXVFghjZUGqjmoO8FUWgr&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent.xx&oh=03_Q7cD4QFS1LYSpryUlFPSRH4fSJA9CKhwQiMoJTnt49ER_ba4Yg&oe=697E1A12",
    "ambigue": "https://scontent-atl3-3.xx.fbcdn.net/v/t1.15752-9/609493933_1424861619241972_889957579385000309_n.jpg?_nc_cat=107&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=pqrBR4BJWKAQ7kNvwEELfeO&_nc_oc=Adlb6vFFxv-eb5_yZldLX32_ZIptpATP3fWJ4Bp-8b1HHwyamwm8CJO4_G_qjQu68kOKqqPE4RUtWBnM30kjmVR5&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent-atl3-3.xx&oh=03_Q7cD4QEFUhVkXMLvn9DD3m9hHWEraSVSbRrVY3YIBIvU7HvVuw&oe=697E1F86",
}


async def bench() -> None:
    company_phone = os.getenv("BOTLIVE_COMPANY_PHONE") or os.getenv("COMPANY_PHONE")
    enable_ocr = (os.getenv("BENCH_ENABLE_OCR", "false") or "").strip().lower() == "true"
    force_divergence = (os.getenv("BENCH_FORCE_DIVERGENCE", "false") or "").strip().lower() == "true"
    for test_name, url in TEST_IMAGES.items():
        print("\n" + "=" * 60)
        print(f"TEST: {test_name}")
        print(f"URL: {url}")
        print("=" * 60)

        start = time.time()
        try:
            result, meta = await analyze_product_with_gemini(
                image_url=url,
                user_message="Test bench - 100 produits catalogue",
                company_phone=company_phone,
                required_amount=2000,
            )
            elapsed = time.time() - start

            print(f"✅ Succès en {elapsed:.2f}s")
            print(f"  - Name: {result.get('name')}")
            print(f"  - Confidence: {result.get('confidence')}")
            print(f"  - Is Product: {result.get('is_product_image')}")
            print(f"  - Notes: {(result.get('notes') or '')[:160]}")

            if result.get('payment') is not None:
                print(f"  - Payment: {result.get('payment')}")

            if enable_ocr and (test_name.startswith("paiement") or result.get('payment') is not None):
                ocr_start = time.time()
                tmp_path = None
                try:
                    from core.botlive_engine import get_botlive_engine
                    from Zeta_AI.payment_forensic import validate_payment_authenticity

                    r = requests.get(url, timeout=15)
                    r.raise_for_status()
                    fd, tmp_path = tempfile.mkstemp(suffix=".jpg", prefix="bench_ocr_")
                    with os.fdopen(fd, "wb") as f:
                        f.write(r.content)

                    engine = get_botlive_engine()
                    ocr_out = await asyncio.to_thread(
                        engine.verify_payment,
                        tmp_path,
                        company_phone=company_phone,
                        required_amount=2000,
                    )

                    try:
                        ocr_amount = int(str((ocr_out or {}).get("amount") or "0").strip())
                    except Exception:
                        ocr_amount = 0

                    pay = (result or {}).get("payment") if isinstance(result, dict) else None
                    try:
                        gem_amount = float((pay or {}).get("detected_amount") or (pay or {}).get("amount") or 0)
                    except Exception:
                        gem_amount = 0.0

                    if force_divergence and gem_amount > 0:
                        gem_amount = gem_amount + 500

                    payment_data_forensic = {
                        "provider": (pay or {}).get("provider") if isinstance(pay, dict) else None,
                        "amount": (ocr_amount if ocr_amount > 0 else gem_amount),
                        "currency": (pay or {}).get("currency") if isinstance(pay, dict) else "FCFA",
                        "recipient_phone": (pay or {}).get("recipient_phone") if isinstance(pay, dict) else None,
                        "recipient_phone_normalized": (pay or {}).get("recipient_phone_normalized") if isinstance(pay, dict) else None,
                        "reference": (pay or {}).get("reference") if isinstance(pay, dict) else None,
                        "date_time": (pay or {}).get("date_time") if isinstance(pay, dict) else None,
                        "required_amount": 2000,
                        "detected_amount": (ocr_amount if ocr_amount > 0 else gem_amount),
                        "signals": {
                            "ocr_ok": bool(ocr_amount >= 2000),
                            "ocr_amount": ocr_amount,
                            "gem_ok": bool(gem_amount >= 2000),
                            "gem_amount": gem_amount,
                        },
                    }

                    forensic = await validate_payment_authenticity(
                        image_url=url,
                        payment_data=payment_data_forensic,
                        company_phone=company_phone,
                        required_amount=2000,
                    )

                    print(f"  - OCR amount: {ocr_amount}")
                    print(f"  - Forensic: verdict={(forensic or {}).get('verdict')} score={(forensic or {}).get('fraud_score')} flags={(forensic or {}).get('red_flags')}")
                    print(f"  - OCR+Forensic en {time.time() - ocr_start:.2f}s")
                except Exception as e:
                    print(f"  - OCR/Forensic error: {type(e).__name__}: {e}")
                finally:
                    try:
                        if tmp_path and os.path.isfile(tmp_path):
                            os.remove(tmp_path)
                    except Exception:
                        pass

            if isinstance(meta, dict) and meta:
                print(f"  - Meta model: {meta.get('model')}")
                if meta.get("total_cost") is not None:
                    print(f"  - Meta total_cost: {meta.get('total_cost')}")
                if meta.get("total_tokens") is not None:
                    print(f"  - Meta total_tokens: {meta.get('total_tokens')}")

            if result.get("error"):
                print(f"  - Error: {result.get('error')}")
                print(f"  - Raw: {(result.get('raw') or '')[:300]}")

        except Exception as e:
            elapsed = time.time() - start
            print(f"❌ Erreur en {elapsed:.2f}s: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(bench())
