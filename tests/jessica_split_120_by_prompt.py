import asyncio
import csv
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Tuple

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
from database.supabase_client import get_botlive_prompt
from tests.prod_benchmark_120 import PROD_BENCHMARK_120


def _truthy_env(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "y", "on"}


def _prompt_source_from_env() -> str:
    return (os.environ.get("BOTLIVE_EVAL_PROMPT_SOURCE") or "supabase").strip().lower()


def _prompt_path_from_env() -> str:
    return (os.environ.get("BOTLIVE_EVAL_PROMPT_PATH") or "").strip()


def _load_prompt_template(company_id: str) -> str:
    source = _prompt_source_from_env()
    if source == "file":
        path = _prompt_path_from_env()
        if not path:
            raise ValueError("BOTLIVE_EVAL_PROMPT_SOURCE=file mais BOTLIVE_EVAL_PROMPT_PATH est vide")
        if not os.path.isabs(path):
            path = os.path.join(_ROOT_DIR, path)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    # Default: Supabase (prompt_botlive_groq_70b)
    return asyncio.run(get_botlive_prompt(company_id))  # used only in sync wrapper


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


async def run_split() -> Tuple[str, str]:
    test_company_id = os.environ.get("BOTLIVE_EVAL_COMPANY_ID") or "W27PwOPiblP8TlOrhPcjOtxd0cza"
    test_user_id = os.environ.get("BOTLIVE_EVAL_USER_ID") or "jessica_split_120"

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

    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    rows: List[Dict[str, Any]] = []

    for idx, (question, expected_label, expected_id) in enumerate(PROD_BENCHMARK_120, 1):
        expected_internal = _expected_label_to_internal_intent(expected_label, expected_id)

        res = await pipeline.route_message(
            company_id=test_company_id,
            user_id=test_user_id,
            message=question,
            conversation_history="",
            state_compact=base_state,
            hyde_pre_enabled=True if hyde_pre_enabled else False,
        )

        routing = res["result"]
        debug = None
        if isinstance(routing, dict):
            debug = routing.get("debug")
        else:
            debug = getattr(routing, "debug", None)
        if not isinstance(debug, dict):
            debug = {}

        hyde_used = bool(debug.get("hyde_used"))
        hyde_stage = debug.get("hyde_stage")
        hyde_trigger_reason = debug.get("hyde_trigger_reason")

        got_intent = (getattr(routing, "intent", None) or (routing.get("intent") if isinstance(routing, dict) else "") or "").upper()
        got_conf = float(getattr(routing, "confidence", 0.0) or (routing.get("confidence") if isinstance(routing, dict) else 0.0) or 0.0)
        got_mode = str(getattr(routing, "mode", "") or (routing.get("mode") if isinstance(routing, dict) else ""))

        ok = got_intent == expected_internal

        hyde_like_result = {
            "success": True,
            "intent": got_intent,
            "confidence": got_conf,
            "mode": got_mode,
            "missing_fields": getattr(routing, "missing_fields", None)
            or (routing.get("missing_fields") if isinstance(routing, dict) else []),
            "state": getattr(routing, "state", None) or (routing.get("state") if isinstance(routing, dict) else {}),
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
            routing=routing,
        )

        letter = segment.get("segment_letter") or "A"
        gating = segment.get("gating_path") or "standard"

        prompt_bucket = f"{letter}:{gating}"
        record = {
            "idx": idx,
            "question": question,
            "expected_label": expected_label,
            "expected_internal": expected_internal,
            "final_intent": got_intent,
            "final_conf": got_conf,
            "final_ok": ok,
            "mode": got_mode,
            "result_type": type(routing).__name__,
            "hyde_used": hyde_used,
            "hyde_stage": hyde_stage,
            "hyde_trigger_reason": hyde_trigger_reason,
            "segment_letter": letter,
            "gating_path": gating,
            "prompt_bucket": prompt_bucket,
        }

        rows.append(record)
        groups[prompt_bucket].append(record)

        print(
            f"[{idx:03d}] bucket={prompt_bucket:<10} conf={got_conf:.3f} hyde_used={hyde_used} ok={'OK' if ok else 'KO'} intent={got_intent:<18} q={question}"
        )

    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_json = os.path.join(_ROOT_DIR, "results", f"jessica_split_120_{run_ts}.json")
    out_csv = os.path.join(_ROOT_DIR, "results", f"jessica_split_120_{run_ts}.csv")

    os.makedirs(os.path.dirname(out_json), exist_ok=True)

    payload = {
        "meta": {
            "company_id": test_company_id,
            "user_id": test_user_id,
            "prompt_source": _prompt_source_from_env(),
            "prompt_path": _prompt_path_from_env(),
            "hyde_pre_enabled": hyde_pre_enabled,
            "total": len(rows),
        },
        "groups": {k: v for k, v in groups.items()},
        "rows": rows,
    }

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "idx",
                "question",
                "expected_label",
                "expected_internal",
                "final_intent",
                "final_conf",
                "final_ok",
                "mode",
                "result_type",
                "hyde_used",
                "hyde_stage",
                "hyde_trigger_reason",
                "segment_letter",
                "gating_path",
                "prompt_bucket",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print("\n=== SPLIT DONE ===")
    print(f"JSON: {out_json}")
    print(f"CSV:  {out_csv}")

    return out_json, out_csv


def main() -> None:
    asyncio.run(run_split())


if __name__ == "__main__":
    main()
