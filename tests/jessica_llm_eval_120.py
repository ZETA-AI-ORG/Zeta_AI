import asyncio
import csv
import json
import os
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

_THIS_DIR = os.path.dirname(__file__)
_ROOT_DIR = os.path.abspath(os.path.join(_THIS_DIR, ".."))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(_ROOT_DIR, ".env"), override=False)
except Exception:
    pass

from core.jessica_prompt_segmenter import build_jessica_prompt_segment
from core.production_pipeline import ProductionPipeline
from core.botlive_intent_router import route_botlive_intent
from core.llm_client_openrouter import complete as openrouter_complete
from core.llm_health_check import complete as groq_complete
from database.supabase_client import get_botlive_prompt
from tests.prod_benchmark_120 import PROD_BENCHMARK_120


def _truthy_env(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "y", "on"}


def _prompt_source_from_env() -> str:
    return (os.environ.get("BOTLIVE_EVAL_PROMPT_SOURCE") or "supabase").strip().lower()


def _prompt_path_from_env() -> str:
    return (os.environ.get("BOTLIVE_EVAL_PROMPT_PATH") or "").strip()


def _llm_provider_from_env() -> str:
    return (os.environ.get("BOTLIVE_EVAL_LLM_PROVIDER") or "openrouter").strip().lower()


def _llm_model_from_env() -> str:
    raw = (os.environ.get("BOTLIVE_EVAL_LLM_MODEL") or "mistralai/mistral-7b-instruct").strip()
    # Be forgiving with .env values like "mistralai/..." (quotes included)
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        raw = raw[1:-1].strip()

    # OpenRouter requires a fully-qualified model id, e.g. "mistralai/mistral-small-3.2-24b-instruct"
    if "/" not in raw:
        lower = raw.lower()
        if lower.startswith("mistral-") or lower.startswith("mistral_small") or lower.startswith("mistral-small"):
            raw = f"mistralai/{raw}"
    return raw


def _llm_seed_from_env() -> Optional[int]:
    raw = (os.environ.get("BOTLIVE_EVAL_LLM_SEED") or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except Exception:
        return None


def _expected_label_to_internal_intent(expected_label: str, expected_intent_id: int) -> str:
    label = (expected_label or "").strip().upper()

    mapping = {
        "GREETING": "SALUT",
        "INFO_GENERAL": "INFO_GENERALE",
        "CONTACT_COORDONNEES": "CONTACT_COORDONNEES",
        "PRODUCT_INFO": "PRODUIT_GLOBAL",
        "PRICE": "PRIX_PROMO",
        "STOCK": "PRODUIT_GLOBAL",
        "ORDER_CREATE": "ACHAT_COMMANDE",
        "ORDER_MODIFY": "COMMANDE_EXISTANTE",
        "PAYMENT": "PAIEMENT",
        "DELIVERY_INFO": "LIVRAISON",
        "DELIVERY_MODIFY": "LIVRAISON",
        "TRACKING": "COMMANDE_EXISTANTE",
        "PROBLEME": "COMMANDE_EXISTANTE",
    }

    if label in mapping:
        return mapping[label]

    id_map = {
        1: "SALUT",
        2: "INFO_GENERALE",
        3: "INFO_GENERALE",
        4: "PRODUIT_GLOBAL",
        5: "PRODUIT_GLOBAL",
        6: "PRIX_PROMO",
        7: "PRODUIT_GLOBAL",
        8: "ACHAT_COMMANDE",
        9: "LIVRAISON",
        10: "PAIEMENT",
        11: "COMMANDE_EXISTANTE",
        12: "COMMANDE_EXISTANTE",
        13: "CONTACT_COORDONNEES",
    }
    return id_map.get(int(expected_intent_id), "INFO_GENERALE")


async def _get_prompt_template_async(company_id: str) -> str:
    source = _prompt_source_from_env()
    if source == "file":
        path = _prompt_path_from_env()
        if not path:
            raise ValueError("BOTLIVE_EVAL_PROMPT_SOURCE=file mais BOTLIVE_EVAL_PROMPT_PATH est vide")
        if not os.path.isabs(path):
            path = os.path.join(_ROOT_DIR, path)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    return await get_botlive_prompt(company_id)


def _extract_meta_response(text: str) -> Dict[str, Optional[str]]:
    if not text:
        return {"meta": None, "response": None}

    meta_match = re.search(r"<meta>\s*(.*?)\s*</meta>", text, re.DOTALL | re.IGNORECASE)
    resp_match = re.search(r"<response>\s*(.*?)\s*</response>", text, re.DOTALL | re.IGNORECASE)

    meta = meta_match.group(1).strip() if meta_match else None
    resp = resp_match.group(1).strip() if resp_match else None
    return {"meta": meta, "response": resp}


def _is_strict_meta_response(text: str) -> bool:
    if not text:
        return False

    # Strict: only whitespace allowed outside the two blocks
    pattern = r"^\s*<meta>.*?</meta>\s*<response>.*?</response>\s*$"
    return bool(re.match(pattern, text, re.DOTALL | re.IGNORECASE))


def _parse_meta_kv(meta_text: Optional[str]) -> Dict[str, str]:
    if not meta_text:
        return {}
    # format: key:value|key:value
    items = [p.strip() for p in meta_text.split("|") if p.strip()]
    out: Dict[str, str] = {}
    for it in items:
        if ":" not in it:
            continue
        k, v = it.split(":", 1)
        out[k.strip()] = v.strip()
    return out


async def _llm_complete(prompt: str) -> Tuple[str, Dict[str, Any]]:
    provider = _llm_provider_from_env()
    model = _llm_model_from_env()
    seed = _llm_seed_from_env()

    if provider == "groq":
        text, tokens = await groq_complete(prompt, model)
        tokens = tokens or {}
        tokens["provider"] = tokens.get("provider") or "groq"
        tokens["model"] = tokens.get("model") or model
        return text, tokens

    # default openrouter
    text, tokens = await openrouter_complete(
        prompt,
        model_name=model,
        temperature=float(os.environ.get("BOTLIVE_EVAL_LLM_TEMPERATURE", "0.2")),
        max_tokens=int(os.environ.get("BOTLIVE_EVAL_LLM_MAX_TOKENS", "220")),
        top_p=float(os.environ.get("BOTLIVE_EVAL_LLM_TOP_P", "0.9")),
        seed=seed,
    )
    tokens = tokens or {}
    tokens["provider"] = tokens.get("provider") or "openrouter"
    tokens["model"] = tokens.get("model") or model
    return text, tokens


async def run_eval(limit: int = 120) -> Tuple[str, str]:
    test_company_id = os.environ.get("BOTLIVE_EVAL_COMPANY_ID") or "W27PwOPiblP8TlOrhPcjOtxd0cza"
    test_user_id = os.environ.get("BOTLIVE_EVAL_USER_ID") or "jessica_llm_eval_120"

    hyde_pre_enabled = _truthy_env("BOTLIVE_EVAL_ENABLE_HYDE_PRE", "false")
    if not hyde_pre_enabled:
        os.environ["BOTLIVE_HYDE_PRE_ENABLED"] = "false"

    pipeline = ProductionPipeline()
    base_prompt_template = await _get_prompt_template_async(test_company_id)

    base_state = {
        "photo_collected": False,
        "paiement_collected": False,
        "zone_collected": False,
        "tel_collected": False,
        "tel_valide": False,
        "collected_count": 0,
        "is_complete": False,
    }

    rows: List[Dict[str, Any]] = []

    cases = PROD_BENCHMARK_120[:limit]

    for idx, (question, expected_label, expected_id) in enumerate(cases, 1):
        expected_internal = _expected_label_to_internal_intent(expected_label, expected_id)

        # 1) Production routing (SetFit + dual router selon env)
        res_prod = await pipeline.route_message(
            company_id=test_company_id,
            user_id=test_user_id,
            message=question,
            conversation_history="",
            state_compact=base_state,
            hyde_pre_enabled=True if hyde_pre_enabled else False,
        )
        routing_prod = res_prod["result"]

        prod_intent = (getattr(routing_prod, "intent", None) or (routing_prod.get("intent") if isinstance(routing_prod, dict) else "") or "").upper()
        prod_conf = float(getattr(routing_prod, "confidence", 0.0) or (routing_prod.get("confidence") if isinstance(routing_prod, dict) else 0.0) or 0.0)
        prod_mode = str(getattr(routing_prod, "mode", "") or (routing_prod.get("mode") if isinstance(routing_prod, dict) else ""))

        ok = prod_intent == expected_internal

        # 2) Embeddings router (for comparison)
        routing_embed = await route_botlive_intent(
            company_id=test_company_id,
            user_id=f"{test_user_id}_emb",
            message=question,
            conversation_history="",
            state_compact=base_state,
        )

        embed_intent = (routing_embed.intent or "").upper()
        embed_conf = float(routing_embed.confidence or 0.0)
        embed_mode = str(routing_embed.mode or "")

        # 3) Segmenter Jessica based on PROD routing (what you'd do in prod)
        hyde_like_result = {
            "success": True,
            "intent": prod_intent,
            "confidence": prod_conf,
            "mode": prod_mode,
            "missing_fields": getattr(routing_prod, "missing_fields", None)
            or (routing_prod.get("missing_fields") if isinstance(routing_prod, dict) else []),
            "state": getattr(routing_prod, "state", None) or (routing_prod.get("state") if isinstance(routing_prod, dict) else {}),
            "raw": "",
            "token_info": {"source": "production_pipeline"},
        }

        segment = build_jessica_prompt_segment(
            base_prompt_template=base_prompt_template,
            hyde_result=hyde_like_result,
            question_with_context=question,
            conversation_history="",
            detected_objects_str="",
            filtered_transactions_str="[AUCUNE TRANSACTION VALIDE]",
            expected_deposit_str="2000 FCFA",
            enriched_checklist="[CHECKLIST TEST]",
            routing=routing_prod,
        )

        letter = segment.get("segment_letter") or "A"
        gating = segment.get("gating_path") or "standard"
        used_light = bool(segment.get("used_light"))
        used_prompt_x = bool(segment.get("used_prompt_x"))

        # 4) Call LLM with the selected segment prompt
        prompt_to_use = segment.get("prompt") or ""
        llm_text, token_info = await _llm_complete(prompt_to_use)

        parts = _extract_meta_response(llm_text or "")
        strict_ok = _is_strict_meta_response(llm_text or "")
        meta_kv = _parse_meta_kv(parts.get("meta"))

        # Minimal automatic scoring
        score = 0
        if strict_ok:
            score += 1
        if parts.get("meta") and parts.get("response"):
            score += 1
        if meta_kv.get("intent") == prod_intent:
            score += 1

        row: Dict[str, Any] = {
            "idx": idx,
            "question": question,
            "expected_label": expected_label,
            "expected_internal": expected_internal,
            "final_ok": ok,
            "prod_intent": prod_intent,
            "prod_conf": f"{prod_conf:.3f}",
            "prod_mode": prod_mode,
            "embed_intent": embed_intent,
            "embed_conf": f"{embed_conf:.3f}",
            "embed_mode": embed_mode,
            "segment_letter": letter,
            "gating_path": gating,
            "used_light": used_light,
            "used_prompt_x": used_prompt_x,
            "llm_provider": token_info.get("provider"),
            "llm_model": token_info.get("model"),
            "llm_prompt_chars": len(prompt_to_use),
            "llm_raw": llm_text,
            "llm_meta": parts.get("meta"),
            "llm_response": parts.get("response"),
            "format_strict_ok": strict_ok,
            "meta_mode": meta_kv.get("mode", ""),
            "meta_intent": meta_kv.get("intent", ""),
            "meta_action": meta_kv.get("action", ""),
            "score": score,
            "prompt_tokens": token_info.get("prompt_tokens", 0),
            "completion_tokens": token_info.get("completion_tokens", 0),
            "total_tokens": token_info.get("total_tokens", 0),
        }

        rows.append(row)

        print(
            f"[{idx:03d}] letter={letter} gating={gating:<8} score={score} format={'OK' if strict_ok else 'KO'} "
            f"prod={prod_intent:<18}({prod_conf:.2f}) embed={embed_intent:<18}({embed_conf:.2f}) q={question}"
        )

    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_json = os.path.join(_ROOT_DIR, "results", f"jessica_llm_eval_120_{run_ts}.json")
    out_csv = os.path.join(_ROOT_DIR, "results", f"jessica_llm_eval_120_{run_ts}.csv")

    os.makedirs(os.path.dirname(out_json), exist_ok=True)

    payload = {
        "meta": {
            "company_id": test_company_id,
            "user_id": test_user_id,
            "prompt_source": _prompt_source_from_env(),
            "prompt_path": _prompt_path_from_env(),
            "hyde_pre_enabled": hyde_pre_enabled,
            "llm_provider": _llm_provider_from_env(),
            "llm_model": _llm_model_from_env(),
            "llm_seed": _llm_seed_from_env(),
            "total": len(rows),
        },
        "rows": rows,
    }

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    csv_fields = [
        "idx",
        "question",
        "expected_label",
        "expected_internal",
        "final_ok",
        "prod_intent",
        "prod_conf",
        "prod_mode",
        "embed_intent",
        "embed_conf",
        "embed_mode",
        "segment_letter",
        "gating_path",
        "used_light",
        "used_prompt_x",
        "llm_provider",
        "llm_model",
        "llm_prompt_chars",
        "format_strict_ok",
        "meta_mode",
        "meta_intent",
        "meta_action",
        "score",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "llm_meta",
        "llm_response",
    ]

    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=csv_fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in csv_fields})

    print("\n=== JESSICA LLM EVAL DONE ===")
    print(f"JSON: {out_json}")
    print(f"CSV:  {out_csv}")
    return out_json, out_csv


def main() -> None:
    limit = int(os.environ.get("BOTLIVE_EVAL_LIMIT", "120"))
    asyncio.run(run_eval(limit=limit))


if __name__ == "__main__":
    main()
