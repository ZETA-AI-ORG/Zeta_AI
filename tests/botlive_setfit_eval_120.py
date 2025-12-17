import asyncio
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime
import math
import statistics
from typing import Any, Dict, List, Tuple

# Assurer l'import des modules du projet
_THIS_DIR = os.path.dirname(__file__)
_ROOT_DIR = os.path.abspath(os.path.join(_THIS_DIR, ".."))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

# Charger .env si présent (les scripts de test ne chargent pas automatiquement l'env)
try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(_ROOT_DIR, ".env"), override=False)
except Exception:
    pass

# On force l'évaluation SetFit via ProductionPipeline
os.environ["BOTLIVE_ROUTER_EMBEDDINGS_ENABLED"] = "false"

_EVAL_ENABLE_HYDE_PRE = os.environ.get("BOTLIVE_EVAL_ENABLE_HYDE_PRE", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "y",
    "on",
}

if not _EVAL_ENABLE_HYDE_PRE:
    os.environ["BOTLIVE_HYDE_PRE_ENABLED"] = "false"

from core.production_pipeline import ProductionPipeline
from core.hyde_reformulator import HydeReformulator
from tests.production_test_cases import PRODUCTION_TEST_CASES


TEST_COMPANY_ID = "W27PwOPiblP8TlOrhPcjOtxd0cza"
TEST_USER_ID = "setfit_eval_120"


def _expected_label_to_internal_intent(expected_label: str, expected_intent_id: int) -> str:
    label = (expected_label or "").strip().upper()

    # Note: production_test_cases.py utilise des labels "métier" indépendants des intents internes Botlive.
    # On map vers les intents internes attendus (ceux produits par SetFit pipeline).
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
    }

    if label in mapping:
        return mapping[label]

    # Fallback basé sur l'intent_id si jamais le label est inconnu
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
        12: "PROBLEME",
        13: "CONTACT_COORDONNEES",
    }
    return id_map.get(int(expected_intent_id), "INFO_GENERALE")


def _percentile_nearest_rank(sorted_vals: List[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    q = max(0.0, min(1.0, float(q)))
    k = max(1, math.ceil(q * len(sorted_vals))) - 1
    return float(sorted_vals[k])


def _intent_to_group(intent: str) -> str:
    upper = (intent or "").upper()

    if upper in {"PRODUIT_GLOBAL", "PRIX_PROMO"}:
        return "PRODUIT"
    if upper in {"ACHAT_COMMANDE", "COMMANDE_EXISTANTE"}:
        return "COMMANDE"
    if upper in {"SALUT", "INFO_GENERALE", "CONTACT_COORDONNEES"}:
        return "INFO"
    if upper == "PAIEMENT":
        return "PAIEMENT"
    if upper == "LIVRAISON":
        return "LIVRAISON"

    return "AUTRE"


def _percentile(sorted_vals: List[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    k = max(1, math.ceil(q * len(sorted_vals))) - 1
    return float(sorted_vals[k])


def _summarize_confidence(vals: List[float]) -> Dict[str, float]:
    if not vals:
        return {"n": 0}
    s = sorted(float(v) for v in vals)
    return {
        "n": float(len(s)),
        "min": float(s[0]),
        "p10": _percentile(s, 0.10),
        "p25": _percentile(s, 0.25),
        "median": float(statistics.median(s)),
        "p75": _percentile(s, 0.75),
        "p90": _percentile(s, 0.90),
        "max": float(s[-1]),
        "mean": float(statistics.fmean(s)),
    }


def _safe_float(x: Any) -> float | None:
    if x is None:
        return None
    try:
        return float(x)
    except Exception:
        return None


async def run_eval(limit: int | None = None) -> Dict[str, Any]:
    cases = PRODUCTION_TEST_CASES if limit is None else PRODUCTION_TEST_CASES[:limit]

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

    per_case: List[Dict[str, Any]] = []
    correct = 0
    confusion: Dict[str, Counter] = defaultdict(Counter)
    by_expected: Counter = Counter()

    # Métriques par groupe d'intents (PRODUIT / COMMANDE / INFO / ...)
    group_correct = 0
    group_confusion: Dict[str, Counter] = defaultdict(Counter)
    by_expected_group: Counter = Counter()

    # Analyse de la confiance (pour décider quand déclencher HYDE)
    conf_ok_group: List[float] = []
    conf_ko_group: List[float] = []

    print(f"\n================= SETFIT EVAL ({len(cases)}) =================\n")

    for idx, (question, expected_label, expected_id) in enumerate(cases, 1):
        expected_intent = _expected_label_to_internal_intent(expected_label, expected_id)

        res = await pipeline.route_message(
            company_id=TEST_COMPANY_ID,
            user_id=TEST_USER_ID,
            message=question,
            conversation_history="",
            state_compact=base_state,
            hyde_pre_enabled=True if _EVAL_ENABLE_HYDE_PRE else False,
        )

        routing = res["result"]
        got_intent = (routing.intent or "").upper()
        got_mode = routing.mode
        score = float(routing.confidence or 0.0)

        ok = got_intent == expected_intent
        if ok:
            correct += 1

        by_expected[expected_intent] += 1
        confusion[expected_intent][got_intent] += 1

        expected_group = _intent_to_group(expected_intent)
        got_group = _intent_to_group(got_intent)
        ok_group = expected_group == got_group
        if ok_group:
            group_correct += 1
            conf_ok_group.append(score)
        else:
            conf_ko_group.append(score)

        by_expected_group[expected_group] += 1
        group_confusion[expected_group][got_group] += 1

        print(
            f"[{idx:03d}] {'OK' if ok else 'KO'} | score={score:.3f} | expected={expected_intent:<18} | got={got_intent:<18} | mode={got_mode:<14} | q={question}"
        )

        per_case.append(
            {
                "index": idx,
                "question": question,
                "expected_label": expected_label,
                "expected_intent_id": expected_id,
                "expected_internal_intent": expected_intent,
                "expected_group": expected_group,
                "got": {
                    "intent": got_intent,
                    "group": got_group,
                    "mode": got_mode,
                    "confidence": score,
                    "missing_fields": routing.missing_fields,
                    "debug": routing.debug,
                },
                "pipeline": {
                    "cache_hit": bool(res.get("cache_hit")),
                    "llm_model": res.get("llm_model"),
                    "llm_routing_reason": res.get("llm_routing_reason"),
                },
                "ok": ok,
                "ok_group": ok_group,
            }
        )

    total = len(cases)
    accuracy = (correct / total * 100.0) if total else 0.0

    group_accuracy = (group_correct / total * 100.0) if total else 0.0

    # Top erreurs (expected -> got)
    error_pairs: Counter = Counter()
    for exp, got_counts in confusion.items():
        for got, n in got_counts.items():
            if got != exp:
                error_pairs[(exp, got)] += n

    summary = {
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "top_errors": [
            {"expected": exp, "got": got, "count": n}
            for (exp, got), n in error_pairs.most_common(20)
        ],
        "confusion": {exp: dict(got_counts) for exp, got_counts in confusion.items()},
        "by_expected": dict(by_expected),
        "group": {
            "correct": group_correct,
            "accuracy": group_accuracy,
            "confusion": {g: dict(cnt) for g, cnt in group_confusion.items()},
            "by_expected": dict(by_expected_group),
        },
    }

    print("\n================= RÉSUMÉ SETFIT =================")
    print(f"Accuracy: {correct}/{total} = {accuracy:.1f}%")
    print("\nTop erreurs:")
    for e in summary["top_errors"][:10]:
        print(f"- expected={e['expected']:<18} got={e['got']:<18} count={e['count']}")

    print("\n================= RÉSUMÉ PAR GROUPE =================")
    print(f"Group accuracy: {group_correct}/{total} = {group_accuracy:.1f}%")

    print("\n================= CONFIANCE (OK vs KO par groupe) =================")
    ok_stats = _summarize_confidence(conf_ok_group)
    ko_stats = _summarize_confidence(conf_ko_group)
    print(
        "OK_GROUP  "
        f"n={int(ok_stats['n'])} "
        f"min={ok_stats['min']:.3f} p10={ok_stats['p10']:.3f} p25={ok_stats['p25']:.3f} "
        f"med={ok_stats['median']:.3f} p75={ok_stats['p75']:.3f} p90={ok_stats['p90']:.3f} "
        f"max={ok_stats['max']:.3f} mean={ok_stats['mean']:.3f}"
    )
    if int(ko_stats.get("n", 0)) > 0:
        print(
            "KO_GROUP  "
            f"n={int(ko_stats['n'])} "
            f"min={ko_stats['min']:.3f} p10={ko_stats['p10']:.3f} p25={ko_stats['p25']:.3f} "
            f"med={ko_stats['median']:.3f} p75={ko_stats['p75']:.3f} p90={ko_stats['p90']:.3f} "
            f"max={ko_stats['max']:.3f} mean={ko_stats['mean']:.3f}"
        )
    else:
        print("KO_GROUP  n=0")

    thresholds = [0.98, 0.95, 0.92, 0.90, 0.88, 0.85, 0.80, 0.75]
    print("\n================= TABLE SEUILS (pour HYDE) =================")
    print("threshold | coverage | group_accuracy_above")
    for t in thresholds:
        above = [c for c in per_case if float(((c.get("got") or {}).get("confidence")) or 0.0) >= t]
        if not above:
            print(f"{t:>8.2f} | 0/{total:<3}  | n/a")
            continue
        ok_above = sum(1 for c in above if c.get("ok_group"))
        acc_above = ok_above / len(above) * 100.0
        print(f"{t:>8.2f} | {len(above)}/{total:<3} | {acc_above:>6.1f}%")

    summary["confidence"] = {
        "ok_group": ok_stats,
        "ko_group": ko_stats,
    }

    # =====================================================================
    # HYDE gating via margin (top1 - top2) : estimation offline
    # =====================================================================
    margins: List[float] = []
    for c in per_case:
        dbg = ((c.get("got") or {}).get("debug") or {})
        m = dbg.get("setfit_margin")
        if m is None:
            continue
        try:
            margins.append(float(m))
        except Exception:
            continue

    if margins:
        margins_sorted = sorted(margins)
        bottom_pct = 0.15
        thr = _percentile_nearest_rank(margins_sorted, bottom_pct)
        triggered = [c for c in per_case if float((((c.get("got") or {}).get("debug") or {}).get("setfit_margin")) or 0.0) <= thr]
        not_triggered = [c for c in per_case if c not in triggered]

        trig_ok = sum(1 for c in triggered if c.get("ok_group"))
        not_ok = sum(1 for c in not_triggered if c.get("ok_group"))

        trig_acc = (trig_ok / len(triggered) * 100.0) if triggered else 0.0
        not_acc = (not_ok / len(not_triggered) * 100.0) if not_triggered else 0.0

        print("\n================= HYDE GATING (MARGIN bottom 15%) =================")
        print(f"margin_threshold(p15)={thr:.4f} | trigger={len(triggered)}/{total} = {len(triggered)/total*100.0:.1f}%")
        print(f"Group accuracy on TRIGGERED:     {trig_ok}/{len(triggered)} = {trig_acc:.1f}%")
        print(f"Group accuracy on NOT_TRIGGERED: {not_ok}/{len(not_triggered)} = {not_acc:.1f}%")

        summary["hyde_margin_eval"] = {
            "bottom_pct": bottom_pct,
            "threshold": thr,
            "trigger_count": len(triggered),
            "trigger_rate": (len(triggered) / total) if total else 0.0,
            "triggered_group_accuracy": trig_acc,
            "not_triggered_group_accuracy": not_acc,
        }

        # =====================================================================
        # Option A: métriques HYDE_PRE réelles (si BOTLIVE_EVAL_ENABLE_HYDE_PRE=true)
        # - compare intent/group/conf/margin AVANT vs APRÈS HYDE sur les cas où le routeur a tenté HYDE.
        # =====================================================================
        if _EVAL_ENABLE_HYDE_PRE:
            hyde_candidates = 0
            hyde_used = 0
            improved_intent = 0
            worsened_intent = 0
            unchanged_intent = 0

            improved_group = 0
            worsened_group = 0
            unchanged_group = 0

            conf_delta: List[float] = []
            margin_delta: List[float] = []

            improved_examples: List[Dict[str, Any]] = []
            worsened_examples: List[Dict[str, Any]] = []

            for c in per_case:
                dbg = ((c.get("got") or {}).get("debug") or {})
                reason = str(dbg.get("hyde_pre_reason") or "")
                if not reason.startswith("LOW_MARGIN<=THR"):
                    continue
                hyde_candidates += 1

                if dbg.get("hyde_pre_used") is True:
                    hyde_used += 1

                expected_intent = str(c.get("expected_internal_intent") or "").upper()
                expected_group = str(c.get("expected_group") or "")

                before_intent = str(dbg.get("hyde_setfit_intent_before") or "").upper()
                after_intent = str(((c.get("got") or {}).get("intent")) or "").upper()

                before_group = _intent_to_group(before_intent)
                after_group = str(((c.get("got") or {}).get("group")) or "")

                ok_before = before_intent == expected_intent
                ok_after = after_intent == expected_intent

                ok_group_before = before_group == expected_group
                ok_group_after = after_group == expected_group

                if ok_before and ok_after:
                    unchanged_intent += 1
                elif (not ok_before) and ok_after:
                    improved_intent += 1
                    improved_examples.append(
                        {
                            "index": c.get("index"),
                            "q": c.get("question"),
                            "expected": expected_intent,
                            "before": before_intent,
                            "after": after_intent,
                        }
                    )
                elif ok_before and (not ok_after):
                    worsened_intent += 1
                    worsened_examples.append(
                        {
                            "index": c.get("index"),
                            "q": c.get("question"),
                            "expected": expected_intent,
                            "before": before_intent,
                            "after": after_intent,
                        }
                    )
                else:
                    unchanged_intent += 1

                if ok_group_before and ok_group_after:
                    unchanged_group += 1
                elif (not ok_group_before) and ok_group_after:
                    improved_group += 1
                elif ok_group_before and (not ok_group_after):
                    worsened_group += 1
                else:
                    unchanged_group += 1

                before_conf = _safe_float(dbg.get("hyde_setfit_conf_before"))
                after_conf = _safe_float(((c.get("got") or {}).get("confidence")))
                if before_conf is not None and after_conf is not None:
                    conf_delta.append(after_conf - before_conf)

                before_margin = _safe_float(dbg.get("hyde_margin"))
                after_margin = _safe_float(dbg.get("hyde_after_setfit_margin"))
                if before_margin is not None and after_margin is not None:
                    margin_delta.append(after_margin - before_margin)

            print("\n================= HYDE_PRE REAL METRICS (OPTION A) =================")
            print(
                f"HYDE candidates (LOW_MARGIN): {hyde_candidates}/{total} = "
                f"{(hyde_candidates/total*100.0 if total else 0.0):.1f}%"
            )
            print(
                f"HYDE reformulated (hyde_pre_used=true): {hyde_used}/{hyde_candidates if hyde_candidates else 1} = "
                f"{(hyde_used/hyde_candidates*100.0 if hyde_candidates else 0.0):.1f}%"
            )
            print(
                "Intent impact on candidates | "
                f"improved={improved_intent} worsened={worsened_intent} unchanged={unchanged_intent}"
            )
            print(
                "Group  impact on candidates | "
                f"improved={improved_group} worsened={worsened_group} unchanged={unchanged_group}"
            )

            if conf_delta:
                conf_delta_stats = _summarize_confidence(conf_delta)
                print(
                    "Δconfidence(after-before) "
                    f"n={int(conf_delta_stats['n'])} "
                    f"min={conf_delta_stats['min']:.3f} p10={conf_delta_stats['p10']:.3f} p25={conf_delta_stats['p25']:.3f} "
                    f"med={conf_delta_stats['median']:.3f} p75={conf_delta_stats['p75']:.3f} p90={conf_delta_stats['p90']:.3f} "
                    f"max={conf_delta_stats['max']:.3f} mean={conf_delta_stats['mean']:.3f}"
                )
            else:
                print("Δconfidence(after-before) n=0")

            if margin_delta:
                margin_delta_stats = _summarize_confidence(margin_delta)
                print(
                    "Δmargin(after-before) "
                    f"n={int(margin_delta_stats['n'])} "
                    f"min={margin_delta_stats['min']:.3f} p10={margin_delta_stats['p10']:.3f} p25={margin_delta_stats['p25']:.3f} "
                    f"med={margin_delta_stats['median']:.3f} p75={margin_delta_stats['p75']:.3f} p90={margin_delta_stats['p90']:.3f} "
                    f"max={margin_delta_stats['max']:.3f} mean={margin_delta_stats['mean']:.3f}"
                )
            else:
                print("Δmargin(after-before) n=0")

            if improved_examples:
                print("\nTop improved examples (intent):")
                for ex in improved_examples[:5]:
                    print(
                        f"- [{ex['index']}] expected={ex['expected']} before={ex['before']} after={ex['after']} | q={ex['q']}"
                    )

            if worsened_examples:
                print("\nTop worsened examples (intent):")
                for ex in worsened_examples[:5]:
                    print(
                        f"- [{ex['index']}] expected={ex['expected']} before={ex['before']} after={ex['after']} | q={ex['q']}"
                    )

        # =====================================================================
        # Optionnel: lancer HYDE uniquement sur les cas déclenchés (≈15%)
        # =====================================================================
        hyde_on_triggered = os.environ.get("BOTLIVE_EVAL_HYDE_ON_TRIGGERED", "false").strip().lower() in {
            "1",
            "true",
            "yes",
            "y",
            "on",
        }

        if hyde_on_triggered:
            print("\n================= HYDE ON TRIGGERED ONLY (EXPENSIVE) =================")
            print(
                f"HYDE will run only for triggered cases: {len(triggered)}/{total} ({len(triggered)/total*100.0:.1f}%)"
            )

            reformulator = HydeReformulator()
            triggered_by_idx = {int(c.get("index")): c for c in triggered}

            hyde_provider = "openrouter" if os.getenv("OPENROUTER_API_KEY") else "groq"
            hyde_model = (
                os.getenv("OPENROUTER_HYDE_PRE_MODEL", "")
                if hyde_provider == "openrouter"
                else os.getenv("BOTLIVE_HYDE_PRE_MODEL", "")
            )
            hyde_temperature = float(os.getenv("BOTLIVE_HYDE_PRE_TEMPERATURE", "0.0" if hyde_provider == "openrouter" else "0.3"))
            hyde_max_tokens = int(os.getenv("BOTLIVE_HYDE_PRE_MAX_TOKENS", "30"))
            hyde_top_p = float(os.getenv("BOTLIVE_HYDE_PRE_TOP_P", "1.0"))
            hyde_seed = os.getenv("BOTLIVE_HYDE_PRE_SEED")
            hyde_resp_json = os.getenv("BOTLIVE_HYDE_PRE_RESPONSE_JSON", "false")

            post_hyde_min_margin = float(os.getenv("BOTLIVE_POST_HYDE_MIN_MARGIN", "0.75"))
            post_hyde_min_confidence = float(os.getenv("BOTLIVE_POST_HYDE_MIN_CONFIDENCE", "0.85"))

            def _clarification_question(top1: str, top2: str) -> str:
                t1 = (top1 or "").upper()
                t2 = (top2 or "").upper()
                pair = (t1, t2)
                pair_rev = (t2, t1)

                mapping = {
                    ("PRIX_PROMO", "PRODUIT_GLOBAL"): "Tu veux le prix ou des infos produit ?",
                    ("ACHAT_COMMANDE", "COMMANDE_EXISTANTE"): "Tu veux passer une commande ou gérer une commande existante ?",
                    ("COMMANDE_EXISTANTE", "LIVRAISON"): "Tu parles d'une commande existante ou des infos livraison ?",
                    ("PAIEMENT", "PROBLEME"): "C'est un paiement ou un problème technique ?",
                }

                q = mapping.get(pair) or mapping.get(pair_rev)
                if q:
                    return q
                return f"Tu parles plutôt de {t1} ou de {t2} ?"

            hyde_used_count = 0
            group_correct_after = 0
            correct_after = 0

            for c in per_case:
                idx = int(c.get("index"))
                question = str(c.get("question") or "")
                expected_intent = str(c.get("expected_internal_intent") or "")
                expected_group = str(c.get("expected_group") or "")

                if idx not in triggered_by_idx:
                    # Pas de HYDE sur ce cas : on garde le résultat initial
                    got_intent_after = str(((c.get("got") or {}).get("intent")) or "").upper()
                    got_group_after = str(((c.get("got") or {}).get("group")) or "")
                    got_score_after = float(((c.get("got") or {}).get("confidence")) or 0.0)
                    got_mode_after = str(((c.get("got") or {}).get("mode")) or "")

                    hyde_used = False
                    reformulated = question
                    reroute_debug = None
                else:
                    ctx = {"conversation_history": "", "state_compact": base_state}
                    reformulated = await reformulator.reformulate(TEST_COMPANY_ID, question, ctx)
                    hyde_used = bool(reformulated and reformulated.strip() and reformulated.strip() != question.strip())
                    if hyde_used:
                        hyde_used_count += 1

                    hyde_meta = getattr(reformulator, "last_meta", None)

                    rerouted = await pipeline.route_message(
                        company_id=TEST_COMPANY_ID,
                        user_id=TEST_USER_ID,
                        message=reformulated,
                        conversation_history="",
                        state_compact=base_state,
                        hyde_pre_enabled=False,
                    )

                    routing2 = rerouted["result"]
                    got_intent_after = (routing2.intent or "").upper()
                    got_mode_after = routing2.mode
                    got_score_after = float(routing2.confidence or 0.0)
                    got_group_after = _intent_to_group(got_intent_after)
                    reroute_debug = routing2.debug

                    post_margin = None
                    post_top2_intent = None
                    if isinstance(reroute_debug, dict):
                        try:
                            post_margin = float(reroute_debug.get("setfit_margin"))
                        except Exception:
                            post_margin = None
                        post_top2_intent = str(reroute_debug.get("legacy_top2_intent") or "")

                    post_decision_mode = "ROUTE"
                    post_decision_reason = "post_hyde_ok"
                    clarification_question = None

                    if not hyde_used:
                        post_decision_mode = "CLARIFY"
                        post_decision_reason = "hyde_no_change"
                    else:
                        if post_margin is None or post_margin < post_hyde_min_margin or got_score_after < post_hyde_min_confidence:
                            post_decision_mode = "CLARIFY"
                            post_decision_reason = "low_post_hyde_scores"

                    if post_decision_mode == "CLARIFY":
                        clarification_question = _clarification_question(got_intent_after, post_top2_intent)

                ok_after = got_intent_after == expected_intent
                ok_group_after = got_group_after == expected_group

                if ok_after:
                    correct_after += 1
                if ok_group_after:
                    group_correct_after += 1

                c["hyde_triggered"] = idx in triggered_by_idx
                c["hyde_reformulated"] = reformulated
                c["hyde_used"] = hyde_used
                c["hyde_meta"] = hyde_meta if idx in triggered_by_idx else None
                if idx in triggered_by_idx:
                    c["post_hyde_decision"] = {
                        "mode": post_decision_mode,
                        "reason": post_decision_reason,
                        "post_margin": post_margin,
                        "post_confidence": got_score_after,
                        "thresholds": {
                            "min_margin": post_hyde_min_margin,
                            "min_confidence": post_hyde_min_confidence,
                        },
                        "candidates": [
                            got_intent_after,
                            post_top2_intent,
                        ],
                        "clarification_question": clarification_question,
                    }
                else:
                    c["post_hyde_decision"] = None
                c["after_hyde"] = {
                    "intent": got_intent_after,
                    "group": got_group_after,
                    "mode": got_mode_after,
                    "confidence": got_score_after,
                    "debug": reroute_debug,
                }
                c["ok_after_hyde"] = ok_after
                c["ok_group_after_hyde"] = ok_group_after

            acc_after = (correct_after / total * 100.0) if total else 0.0
            group_acc_after = (group_correct_after / total * 100.0) if total else 0.0

            print("\n--- BEFORE (no HYDE) ---")
            print(f"Intent accuracy: {correct}/{total} = {accuracy:.1f}%")
            print(f"Group  accuracy: {group_correct}/{total} = {group_accuracy:.1f}%")

            print("\n--- AFTER (HYDE only on triggered) ---")
            print(f"Intent accuracy: {correct_after}/{total} = {acc_after:.1f}%")
            print(f"Group  accuracy: {group_correct_after}/{total} = {group_acc_after:.1f}%")
            print(f"HYDE reformulated (changed text): {hyde_used_count}/{len(triggered)}")

            summary["hyde_triggered_eval"] = {
                "enabled": True,
                "margin_threshold": thr,
                "trigger_count": len(triggered),
                "trigger_rate": (len(triggered) / total) if total else 0.0,
                "hyde_used_count": hyde_used_count,
                "intent_accuracy_before": accuracy,
                "group_accuracy_before": group_accuracy,
                "intent_accuracy_after": acc_after,
                "group_accuracy_after": group_acc_after,
                "hyde_config": {
                    "provider": hyde_provider,
                    "model": hyde_model,
                    "temperature": hyde_temperature,
                    "max_tokens": hyde_max_tokens,
                    "top_p": hyde_top_p,
                    "seed": hyde_seed,
                    "response_json": hyde_resp_json,
                },
            }

            # ===================== Post-HYDE decision summary =====================
            hyde_then_routed = 0
            hyde_then_clarify = 0
            hyde_no_change = 0
            for c in per_case:
                dec = c.get("post_hyde_decision")
                if not isinstance(dec, dict):
                    continue
                mode = str(dec.get("mode") or "")
                reason = str(dec.get("reason") or "")
                if reason == "hyde_no_change":
                    hyde_no_change += 1
                if mode == "ROUTE":
                    hyde_then_routed += 1
                elif mode == "CLARIFY":
                    hyde_then_clarify += 1

            summary["hyde_post_decision_eval"] = {
                "post_hyde_min_margin": post_hyde_min_margin,
                "post_hyde_min_confidence": post_hyde_min_confidence,
                "trigger_count": len(triggered),
                "hyde_no_change": hyde_no_change,
                "hyde_then_routed": hyde_then_routed,
                "hyde_then_clarify": hyde_then_clarify,
            }
    else:
        summary["hyde_margin_eval"] = {"error": "setfit_margin missing in debug"}

    return {"summary": summary, "cases": per_case}


async def main() -> None:
    os.makedirs(os.path.join(_ROOT_DIR, "results"), exist_ok=True)

    results = await run_eval(limit=None)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(_ROOT_DIR, "results", f"botlive_setfit_eval_{results['summary']['total']}_{timestamp}.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n=== SETFIT EVAL TERMINÉ ===")
    print(f"Fichier JSON généré: {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
