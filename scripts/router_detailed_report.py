from __future__ import annotations

import asyncio
import csv
import html
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

# Load .env if present (scripts do not necessarily auto-load env)
try:
    from dotenv import load_dotenv

    load_dotenv(str(ROOT / ".env"), override=False)
except Exception:
    pass

# Keep consistent with other eval scripts
os.environ.setdefault("BOTLIVE_ROUTER_EMBEDDINGS_ENABLED", "false")
os.environ.setdefault("BOTLIVE_HYDE_PRE_ENABLED", "false")

from tests.production_test_cases import PRODUCTION_TEST_CASES
from core.setfit_intent_router import route_botlive_intent as route_terrain
from core.setfit_intent_router_academic import route_botlive_intent as route_academic
from core.production_pipeline import ProductionPipeline


@dataclass
class RouterMetrics:
    intent: str
    confidence: float
    margin: Optional[float]
    guard_reason: Optional[str]
    guard_applied: Optional[bool]
    human_handoff: Optional[bool]
    human_handoff_reason: Optional[str]
    debug: Dict[str, Any]


def _report_company_id() -> str:
    # IMPORTANT: must match an existing row in Supabase table company_rag_configs
    # so that prompts (including [[HYDE_PRE_ROUTING_START]] blocks) can be fetched dynamically.
    return (
        os.environ.get("BOTLIVE_REPORT_COMPANY_ID")
        or os.environ.get("BOTLIVE_TEST_COMPANY_ID")
        or os.environ.get("SUPABASE_COMPANY_ID")
        or "test-company"
    ).strip()


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


def _safe_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(x)
    except Exception:
        return None


def _metrics_from_result(res: Any) -> RouterMetrics:
    intent = str(getattr(res, "intent", "") or "CLARIFICATION").upper()
    confidence = float(getattr(res, "confidence", 0.0) or 0.0)
    dbg = getattr(res, "debug", None)
    if not isinstance(dbg, dict):
        dbg = {}

    margin = _safe_float(dbg.get("setfit_margin"))

    guard_reason = None
    guard_applied = None
    # Two possible naming styles exist across router versions
    if "payment_guard_reason" in dbg or "payment_guard_applied" in dbg:
        guard_reason = dbg.get("payment_guard_reason")
        guard_applied = dbg.get("payment_guard_applied")
    elif "guard_reason" in dbg or "guard_applied" in dbg:
        guard_reason = dbg.get("guard_reason")
        guard_applied = dbg.get("guard_applied")

    human_handoff = dbg.get("human_handoff")
    human_handoff_reason = dbg.get("human_handoff_reason")

    return RouterMetrics(
        intent=intent,
        confidence=confidence,
        margin=margin,
        guard_reason=str(guard_reason) if guard_reason is not None else None,
        guard_applied=bool(guard_applied) if guard_applied is not None else None,
        human_handoff=bool(human_handoff) if human_handoff is not None else None,
        human_handoff_reason=str(human_handoff_reason) if human_handoff_reason is not None else None,
        debug=dbg,
    )


def _class_for_cell(*, ok: bool, kind: str) -> str:
    # kind: 'terrain'|'academic'
    return f"ok" if ok else "ko"


def _html_escape(x: Any) -> str:
    return html.escape(str(x if x is not None else ""))


def _truthy_env(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "y", "on"}


async def _run_one(
    *,
    idx: int,
    question: str,
) -> Tuple[RouterMetrics, RouterMetrics, bool, Optional[str]]:
    # Keep state empty like compare script
    state: Dict[str, Any] = {}

    company_id = _report_company_id()

    res_t = await route_terrain(
        company_id=company_id,
        user_id=f"eval-terrain-{idx}",
        message=question,
        conversation_history="",
        state_compact=state,
        hyde_pre_enabled=False,
    )

    res_a = await route_academic(
        company_id=company_id,
        user_id=f"eval-academic-{idx}",
        message=question,
        conversation_history="",
        state_compact=state,
        hyde_pre_enabled=False,
    )

    terrain_m = _metrics_from_result(res_t)
    academic_m = _metrics_from_result(res_a)

    # HYDE candidates (cheap): only if both routers end up in CLARIFICATION
    hyde_candidate = terrain_m.intent == "CLARIFICATION" and academic_m.intent == "CLARIFICATION"

    # HYDE Tier-3 info (ProductionPipeline three_tier) - expensive
    hyde_used = False
    hyde_stage: Optional[str] = None
    if _truthy_env("BOTLIVE_REPORT_RUN_HYDE", "false") and hyde_candidate:
        try:
            # Force three-tier inside this call
            old_mode = os.environ.get("BOTLIVE_DUAL_ROUTER_MODE")
            os.environ["BOTLIVE_DUAL_ROUTER_MODE"] = "three_tier"

            pipeline = ProductionPipeline()
            out = await pipeline.route_message(
                company_id=company_id,
                user_id=f"eval-three-tier-{idx}",
                message=question,
                conversation_history="",
                state_compact=state,
                hyde_pre_enabled=False,
            )
            rr = out.get("result")
            dbg = getattr(rr, "debug", {}) if rr is not None else {}
            if isinstance(dbg, dict):
                hyde_used = bool(dbg.get("tier3_hyde_used"))
                hyde_stage = str(dbg.get("dual_router_stage") or "") or None
        except Exception:
            hyde_used = False
            hyde_stage = None
        finally:
            if old_mode is None:
                os.environ.pop("BOTLIVE_DUAL_ROUTER_MODE", None)
            else:
                os.environ["BOTLIVE_DUAL_ROUTER_MODE"] = old_mode

    # NOTE: We return hyde_candidate as stage marker if HYDE was not run.
    # Caller will store both fields explicitly.
    return terrain_m, academic_m, (hyde_used or hyde_candidate), (hyde_stage or ("CANDIDATE" if hyde_candidate else None))


async def main() -> None:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "results"
    out_dir.mkdir(parents=True, exist_ok=True)

    company_id = _report_company_id()

    max_concurrency = int(os.environ.get("BOTLIVE_REPORT_MAX_CONCURRENCY", "10") or 10)
    sem = asyncio.Semaphore(max(1, max_concurrency))

    async def _run_one_limited(*, idx: int, question: str):
        async with sem:
            return await _run_one(idx=idx, question=question)

    rows: List[Dict[str, Any]] = []

    tasks = [
        _run_one_limited(idx=i, question=q)
        for i, (q, _lab, _eid) in enumerate(PRODUCTION_TEST_CASES, start=1)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for i, (question, expected_label, expected_id) in enumerate(PRODUCTION_TEST_CASES, start=1):
        expected_internal = _expected_label_to_internal_intent(expected_label, expected_id)

        # Keep state empty like compare script
        state: Dict[str, Any] = {}

        terrain_m: Optional[RouterMetrics] = None
        academic_m: Optional[RouterMetrics] = None
        hyde_flag: bool = False
        hyde_stage: Optional[str] = None
        error: Optional[str] = None

        final_intent: str = ""
        final_conf: float | str = ""
        smart_hyde_used: bool | str = ""
        smart_hyde_trigger_reason: str = ""

        smart_hyde_checked: bool | str = ""
        smart_hyde_should_trigger: bool | str = ""
        smart_hyde_internal_reason: str = ""
        smart_hyde_error: str = ""
        smart_hyde_original_message: str = ""
        smart_hyde_message: str = ""

        final_result_type: str = ""
        final_debug_is_dict: bool | str = ""
        final_debug_keys_sample: str = ""

        r = results[i - 1]
        if isinstance(r, Exception):
            error = str(r)
        else:
            terrain_m, academic_m, hyde_flag, hyde_stage = r

        try:
            pipeline = ProductionPipeline()
            out = await pipeline.route_message(
                company_id=company_id,
                user_id=f"eval-final-{i}",
                message=question,
                conversation_history="",
                state_compact=state,
                hyde_pre_enabled=False,
            )
            rr = out.get("result")
            if rr is not None:
                final_result_type = type(rr).__name__
                # rr can be BotliveRoutingResult OR a plain dict (depending on integration)
                if isinstance(rr, dict):
                    final_intent = str(rr.get("intent") or "CLARIFICATION").upper()
                    try:
                        final_conf = float(rr.get("confidence") or 0.0)
                    except Exception:
                        final_conf = 0.0
                    dbg = rr.get("debug") or {}
                else:
                    final_intent = str(getattr(rr, "intent", "") or "CLARIFICATION").upper()
                    final_conf = float(getattr(rr, "confidence", 0.0) or 0.0)
                    dbg = getattr(rr, "debug", {})

                if isinstance(dbg, dict):
                    final_debug_is_dict = True
                    try:
                        keys = sorted(list(dbg.keys()))
                        final_debug_keys_sample = ",".join(keys[:25])
                    except Exception:
                        final_debug_keys_sample = ""

                    smart_hyde_used = bool(dbg.get("hyde_used"))
                    smart_hyde_trigger_reason = str(dbg.get("hyde_trigger_reason") or "")

                    smart_hyde_checked = bool(dbg.get("smart_hyde_checked"))
                    smart_hyde_should_trigger = bool(dbg.get("smart_hyde_should_trigger"))
                    smart_hyde_internal_reason = str(dbg.get("smart_hyde_trigger_reason") or "")
                    smart_hyde_error = str(dbg.get("hyde_error") or "")
                    smart_hyde_original_message = str(dbg.get("hyde_original_message") or "")
                    smart_hyde_message = str(dbg.get("hyde_message") or "")
                else:
                    final_debug_is_dict = False
        except Exception as e:
            if not error:
                error = f"FINAL_PIPELINE_ERROR:{e}"

        # Explicit fields
        hyde_candidate = bool(hyde_stage == "CANDIDATE")
        hyde_real_used = bool(hyde_flag and hyde_stage and hyde_stage != "CANDIDATE")

        terrain_ok = bool(terrain_m is not None and terrain_m.intent == expected_internal)
        academic_ok = bool(academic_m is not None and academic_m.intent == expected_internal)
        final_ok = bool(final_intent and final_intent == expected_internal)

        rows.append(
            {
                "idx": i,
                "question": question,
                "expected_label": expected_label,
                "expected_id": expected_id,
                "expected_internal": expected_internal,
                "terrain_intent": terrain_m.intent if terrain_m else "",
                "terrain_conf": terrain_m.confidence if terrain_m else "",
                "terrain_margin": terrain_m.margin if terrain_m else "",
                "terrain_guard_reason": terrain_m.guard_reason if terrain_m else "",
                "terrain_guard_applied": terrain_m.guard_applied if terrain_m else "",
                "terrain_handoff": terrain_m.human_handoff if terrain_m else "",
                "terrain_handoff_reason": terrain_m.human_handoff_reason if terrain_m else "",
                "terrain_ok": terrain_ok,
                "academic_intent": academic_m.intent if academic_m else "",
                "academic_conf": academic_m.confidence if academic_m else "",
                "academic_margin": academic_m.margin if academic_m else "",
                "academic_guard_reason": academic_m.guard_reason if academic_m else "",
                "academic_guard_applied": academic_m.guard_applied if academic_m else "",
                "academic_handoff": academic_m.human_handoff if academic_m else "",
                "academic_handoff_reason": academic_m.human_handoff_reason if academic_m else "",
                "academic_ok": academic_ok,
                "final_intent": final_intent,
                "final_conf": final_conf,
                "final_ok": final_ok,
                "smart_hyde_used": smart_hyde_used,
                "smart_hyde_trigger_reason": smart_hyde_trigger_reason,
                "smart_hyde_checked": smart_hyde_checked,
                "smart_hyde_should_trigger": smart_hyde_should_trigger,
                "smart_hyde_internal_reason": smart_hyde_internal_reason,
                "smart_hyde_error": smart_hyde_error,
                "smart_hyde_original_message": smart_hyde_original_message,
                "smart_hyde_message": smart_hyde_message,
                "final_result_type": final_result_type,
                "final_debug_is_dict": final_debug_is_dict,
                "final_debug_keys_sample": final_debug_keys_sample,
                "hyde_candidate": hyde_candidate,
                "hyde_tier3_used": hyde_real_used,
                "hyde_stage": hyde_stage or "",
                "error": error or "",
            }
        )

    # ===================== CSV =====================
    csv_path = out_dir / f"router_detailed_report_{ts}.csv"
    csv_fields = list(rows[0].keys()) if rows else []
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=csv_fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # ===================== HTML =====================
    html_path = out_dir / f"router_detailed_report_{ts}.html"

    n = len(rows)
    terrain_ok_n = sum(1 for r in rows if r.get("terrain_ok") is True)
    academic_ok_n = sum(1 for r in rows if r.get("academic_ok") is True)
    final_ok_n = sum(1 for r in rows if r.get("final_ok") is True)
    hyde_n = sum(1 for r in rows if r.get("hyde_tier3_used") is True)
    hyde_candidate_n = sum(1 for r in rows if r.get("hyde_candidate") is True)
    err_n = sum(1 for r in rows if bool(r.get("error")))

    css = """
    <style>
      body { font-family: Arial, sans-serif; margin: 16px; }
      table { border-collapse: collapse; width: 100%; }
      th, td { border: 1px solid #ddd; padding: 6px; vertical-align: top; font-size: 12px; }
      th { background: #f5f5f5; position: sticky; top: 0; z-index: 1; }
      .ok { background: #d4edda; }
      .ko { background: #f8d7da; }
      .hyde { background: #fff3cd; }
      .other { background: #d1ecf1; }
      .mono { font-family: Consolas, monospace; white-space: pre-wrap; }
      .small { color: #555; font-size: 11px; }
    </style>
    """

    header = f"""
    <h2>Router Detailed Report (130 questions)</h2>
    <div class='small'>Generated: {ts}</div>
    <div class='small'>company_id: {_html_escape(company_id)}</div>
    <div class='small'>Legend: Green=correct, Red=incorrect, Yellow=HYDE tier-3 used, Blue=exception/other</div>
    <ul class='small'>
      <li>Terrain correct: {terrain_ok_n}/{n} = {(terrain_ok_n/n*100.0 if n else 0.0):.1f}%</li>
      <li>Academic correct: {academic_ok_n}/{n} = {(academic_ok_n/n*100.0 if n else 0.0):.1f}%</li>
      <li>Final correct (ProductionPipeline): {final_ok_n}/{n} = {(final_ok_n/n*100.0 if n else 0.0):.1f}%</li>
      <li>HYDE candidates (double CLARIFICATION): {hyde_candidate_n}/{n} = {(hyde_candidate_n/n*100.0 if n else 0.0):.1f}%</li>
      <li>HYDE Tier-3 used (three-tier): {hyde_n}/{n} = {(hyde_n/n*100.0 if n else 0.0):.1f}%</li>
      <li>Errors/exceptions: {err_n}</li>
    </ul>
    """

    cols = [
        "#",
        "Question",
        "Expected(label/id → internal)",
        "Terrain (intent/conf/margin/guard/handoff)",
        "Academic (intent/conf/margin/guard/handoff)",
        "HYDE tier-3",
        "Other/Error",
    ]

    lines = ["<html><head><meta charset='utf-8'>", css, "</head><body>", header, "<table>"]
    lines.append("<tr>" + "".join(f"<th>{_html_escape(c)}</th>" for c in cols) + "</tr>")

    for r in rows:
        expected = f"{r['expected_label']}/{r['expected_id']} → {r['expected_internal']}"

        terrain_cell = (
            f"<div class='mono'>{_html_escape(r['terrain_intent'])} ({_html_escape(r['terrain_conf'])})</div>"
            f"<div class='small'>margin={_html_escape(r['terrain_margin'])} guard={_html_escape(r['terrain_guard_reason'])} applied={_html_escape(r['terrain_guard_applied'])}</div>"
            f"<div class='small'>handoff={_html_escape(r['terrain_handoff'])} reason={_html_escape(r['terrain_handoff_reason'])}</div>"
        )

        academic_cell = (
            f"<div class='mono'>{_html_escape(r['academic_intent'])} ({_html_escape(r['academic_conf'])})</div>"
            f"<div class='small'>margin={_html_escape(r['academic_margin'])} guard={_html_escape(r['academic_guard_reason'])} applied={_html_escape(r['academic_guard_applied'])}</div>"
            f"<div class='small'>handoff={_html_escape(r['academic_handoff'])} reason={_html_escape(r['academic_handoff_reason'])}</div>"
        )

        hyde_cell = ""
        if r.get("hyde_tier3_used"):
            hyde_cell = f"<div class='mono'>YES</div><div class='small'>stage={_html_escape(r.get('hyde_stage'))}</div>"
        elif r.get("hyde_candidate"):
            hyde_cell = "<div class='mono'>CANDIDATE</div><div class='small'>double CLARIFICATION</div>"

        err_cell = _html_escape(r.get("error") or "")

        # Cell-level coloring
        terrain_cls = "other" if err_cell else _class_for_cell(ok=bool(r.get("terrain_ok")), kind="terrain")
        academic_cls = "other" if err_cell else _class_for_cell(ok=bool(r.get("academic_ok")), kind="academic")
        hyde_cls = "hyde" if (r.get("hyde_tier3_used") or r.get("hyde_candidate")) else ""
        err_cls = "other" if err_cell else ""

        lines.append(
            "<tr>"
            + f"<td class='mono'>{r['idx']}</td>"
            + f"<td>{_html_escape(r['question'])}</td>"
            + f"<td class='mono'>{_html_escape(expected)}</td>"
            + f"<td class='{terrain_cls}'>{terrain_cell}</td>"
            + f"<td class='{academic_cls}'>{academic_cell}</td>"
            + f"<td class='{hyde_cls}'>{hyde_cell}</td>"
            + f"<td class='{err_cls} mono'>{err_cell}</td>"
            + "</tr>"
        )

    lines.append("</table></body></html>")

    html_path.write_text("\n".join(lines), encoding="utf-8")

    print("\n=== REPORT GENERATED ===")
    print(f"CSV : {csv_path}")
    print(f"HTML: {html_path}")


if __name__ == "__main__":
    asyncio.run(main())
