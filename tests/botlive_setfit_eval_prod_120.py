import asyncio
import csv
import os
import sys
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

os.environ.setdefault("BOTLIVE_ROUTER_EMBEDDINGS_ENABLED", "false")
os.environ.setdefault("BOTLIVE_DUAL_ROUTER_MODE", "inverted_hyde")

from core.production_pipeline import ProductionPipeline
from tests.prod_benchmark_120 import PROD_BENCHMARK_120

TEST_COMPANY_ID = os.environ.get("BOTLIVE_EVAL_COMPANY_ID") or "W27PwOPiblP8TlOrhPcjOtxd0cza"
TEST_USER_ID = os.environ.get("BOTLIVE_EVAL_USER_ID") or "setfit_eval_prod_120"


def _truthy_env(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "y", "on"}


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


def _safe_bool(x: Any) -> bool:
    if isinstance(x, bool):
        return x
    if x is None:
        return False

    if isinstance(x, (int, float)):
        return bool(x)
    if isinstance(x, str):
        return x.strip().lower() in {"1", "true", "yes", "y", "on"}
    return False


def _extract_routing_fields(routing: Any) -> tuple[str, float, str, Dict[str, Any]]:
    if isinstance(routing, dict):
        intent = (routing.get("intent") or "").upper() or "CLARIFICATION"
        conf = float(routing.get("confidence") or 0.0)
        mode = str(routing.get("mode") or "")
        debug = routing.get("debug")
        if not isinstance(debug, dict):
            debug = {}
        return intent, conf, mode, debug

    intent = (getattr(routing, "intent", None) or "").upper() or "CLARIFICATION"
    conf = float(getattr(routing, "confidence", 0.0) or 0.0)
    mode = getattr(routing, "mode", "")
    debug = getattr(routing, "debug", None)
    if not isinstance(debug, dict):
        debug = {}
    return intent, conf, mode, debug


async def run_eval() -> str:
    pipeline = ProductionPipeline()

    base_state = {
        "photo_collected": False,
        "paiement_collected": False,
        "zone_collected": False,
        "tel_collected": False,
        "tel_valide": False,
        "collected_count": 0,
        "is_complete": False,
    }

    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_csv = os.path.join(_ROOT_DIR, "results", f"prod_eval_120_{run_ts}.csv")

    hyde_pre_enabled = _truthy_env("BOTLIVE_EVAL_ENABLE_HYDE_PRE", "false")
    if not hyde_pre_enabled:
        os.environ["BOTLIVE_HYDE_PRE_ENABLED"] = "false"

    rows: List[Dict[str, Any]] = []

    for idx, (question, expected_label, expected_id) in enumerate(PROD_BENCHMARK_120, 1):
        expected_internal = _expected_label_to_internal_intent(expected_label, expected_id)

        res = await pipeline.route_message(
            company_id=TEST_COMPANY_ID,
            user_id=TEST_USER_ID,
            message=question,
            conversation_history="",
            state_compact=base_state,
            hyde_pre_enabled=True if hyde_pre_enabled else False,
        )

        routing = res["result"]
        got_intent, got_conf, got_mode, debug = _extract_routing_fields(routing)

        hyde_used = _safe_bool(debug.get("hyde_used"))
        hyde_stage = debug.get("hyde_stage")
        hyde_candidate = (str(hyde_stage).upper() == "CANDIDATE") if hyde_stage is not None else False
        hyde_trigger_reason = debug.get("hyde_trigger_reason")

        human_handoff = _safe_bool(debug.get("human_handoff"))
        human_handoff_reason = debug.get("human_handoff_reason")

        ok = got_intent == expected_internal

        rows.append(
            {
                "idx": idx,
                "question": question,
                "expected_label": expected_label,
                "expected_id": int(expected_id),
                "expected_internal": expected_internal,
                "final_intent": got_intent,
                "final_conf": got_conf,
                "final_ok": ok,
                "mode": got_mode,
                "result_type": type(routing).__name__,
                "cache_hit": bool(res.get("cache_hit")),
                "hyde_candidate": hyde_candidate,
                "hyde_used": hyde_used,
                "hyde_stage": hyde_stage,
                "hyde_trigger_reason": hyde_trigger_reason,
                "human_handoff": human_handoff,
                "human_handoff_reason": human_handoff_reason,
            }
        )

        print(
            f"[{idx:03d}] {'OK' if ok else 'KO'} | conf={got_conf:.3f} | expected={expected_internal:<18} | got={got_intent:<18} | mode={got_mode:<14} | q={question}"
        )

    fieldnames = list(rows[0].keys()) if rows else []
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print("\n=== PROD EVAL GENERATED ===")
    print(f"CSV: {out_csv}")
    return out_csv


def main() -> None:
    asyncio.run(run_eval())


if __name__ == "__main__":
    main()
