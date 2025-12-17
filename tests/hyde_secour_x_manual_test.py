import asyncio
import os
import sys
import json
import csv
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

# S'assurer que le projet est dans le PYTHONPATH
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

from core.botlive_intent_router import route_botlive_intent
from core.hyde_secour_x import run_hyde_secour_x
from database.supabase_client import get_botlive_prompt

TEST_COMPANY_ID = "W27PwOPiblP8TlOrhPcjOtxd0cza"
TEST_USER_ID = "test_hyde_secour_x"

HYDE_X_MIN = 0.55
HYDE_X_MAX = 0.69

AMBIGUOUS_CASES: List[Dict[str, Any]] = [
    {"score": 0.55, "question": "Où êtes-vous situés exactement ?", "expected_intent": "INFO_GENERALE"},
    {"score": 0.53, "question": "En fait c'est pour ma femme, elle est enceinte", "expected_intent": "INFO_GENERALE"},
    {"score": 0.57, "question": "Lui il a commandé l'autre fois, il était content", "expected_intent": "INFO_GENERALE"},
    {"score": 0.59, "question": "Ah mais je me souviens ! Il me faut du lait 1er âge", "expected_intent": "INFO_GENERALE"},
    {"score": 0.59, "question": "Je veux des couches... ou peut-être du lait... je sais pas", "expected_intent": "CATALOGUE"},
    {"score": 0.60, "question": "Vous êtes où exactement ? C'est une entreprise ou juste une app ?", "expected_intent": "INFO_GENERALE"},
    {"score": 0.60, "question": "Mon numéro c'est 0707070707 mais parfois je réponds pas", "expected_intent": "INFO_GENERALE"},
    {"score": 0.65, "question": "Bonjour ! Il fait beau aujourd'hui non ?", "expected_intent": "INFO_GENERALE"},
    {"score": 0.66, "question": "On peut vous visiter ? J'aime voir les gens avant de commander", "expected_intent": "INFO_GENERALE"},
    {"score": 0.76, "question": "Ah oui c'est ça ! Mais je sais pas combien c'est...", "expected_intent": "PRIX_PROMO"},
    {"score": 0.65, "question": "Salut, je suis pas sûr... je pense commander quelque chose", "expected_intent": "ACHAT_COMMANDE"},
    {"score": 0.69, "question": "Oui c'est bon, confirmez ma commande", "expected_intent": "ACHAT_COMMANDE"},
    {"score": 0.67, "question": "Je serais livré aujourd'hui ?", "expected_intent": "LIVRAISON"},
    {"score": 0.61, "question": "Je suis à Abobo", "expected_intent": "ACHAT_COMMANDE"},
    {"score": 0.65, "question": "Attendez je cherche... voilà", "expected_intent": "ACHAT_COMMANDE"},
    {"score": 0.65, "question": "C'est ça que je veux... en fait non, c'est juste pour vous montrer", "expected_intent": "INFO_GENERALE"},
    {"score": 0.65, "question": "Finalement si ! Je veux les couches sur la photo", "expected_intent": "SALUT"},
    {"score": 0.80, "question": "Je veux commander... non en fait c'est pour une question d'abord", "expected_intent": "ACHAT_COMMANDE"},
]


def _extract_json_payload(text: str) -> Optional[Dict[str, Any]]:
    raw = text or ""
    if not raw.strip():
        return None

    decoder = json.JSONDecoder()
    candidates: List[Dict[str, Any]] = []

    for m in re.finditer(r"\{", raw):
        start = m.start()
        try:
            obj, end = decoder.raw_decode(raw[start:])
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue

        # On ne garde que les payloads qui ressemblent à HYDE_X
        has_hyde_shape = any(
            k in obj
            for k in [
                "hyde_question",
                "hyde_intent",
                "hyde_group",
                "hyde_missing_fields",
            ]
        )
        if has_hyde_shape:
            candidates.append(obj)

    if not candidates:
        return None

    # Priorité à celui qui contient hyde_question
    for c in candidates:
        if isinstance(c.get("hyde_question"), str) and c.get("hyde_question").strip():
            return c
    return candidates[0]


def _extract_reformulated_text(hyde_raw: str) -> str:
    payload = _extract_json_payload(hyde_raw)
    if isinstance(payload, dict):
        # HYDE_X: on veut UNIQUEMENT hyde_question (et pas d'autres champs)
        val = payload.get("hyde_question")
        if isinstance(val, str) and val.strip():
            return val.strip()

    raw = (hyde_raw or "").strip()
    if not raw:
        return ""

    # 1) Fallback: extraction directe si le JSON a été imprimé en texte
    m = re.search(r'"hyde_question"\s*:\s*"([^"]{2,200})"', raw)
    if m:
        return m.group(1).strip()

    # 2) Fallback: "Vocabulaire simple : \"...\"" (ancien prompt)
    m = re.search(r"Vocabulaire\s+simple\s*:\s*\"([^\"]{2,200})\"", raw, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    # 3) Fallback: section REFORMULATION HYDE → prendre la 1ère phrase courte entre guillemets
    if "REFORMULATION" in raw.upper():
        # On prend les guillemets après le mot REFORMULATION
        up = raw.upper()
        pos = up.find("REFORMULATION")
        tail = raw[pos:]
        quoted = re.findall(r'"([^"]{2,200})"', tail)
        if quoted:
            # souvent: original message apparaît avant; on prend le dernier qui ressemble à une reformulation
            return quoted[-1].strip()

    # 4) Fallback: format "* Message : \"...\"" → au moins on reroute sur le message initial, pas l'analyse
    m = re.search(r"\*\s*Message\s*:\s*\"([^\"]{2,200})\"", raw)
    if m:
        return m.group(1).strip()

    # 5) Dernier recours: éviter de rerouter sur un bloc, on renvoie vide (le caller retombe sur q)
    return ""


def _gating_path(score: float) -> str:
    if score >= 0.90:
        return "light"
    if score < HYDE_X_MIN:
        return "prompt_x"
    if score <= HYDE_X_MAX:
        return "hyde"
    if score < 0.90:
        return "standard"
    return "standard"


def _histogram(values: List[float], bins: List[float]) -> List[int]:
    counts = [0 for _ in range(len(bins) - 1)]
    for v in values:
        for i in range(len(bins) - 1):
            lo, hi = bins[i], bins[i + 1]
            if (v >= lo) and (v < hi or (i == len(bins) - 2 and v <= hi)):
                counts[i] += 1
                break
    return counts


async def main():
    question = input("Question à tester (HYDE SECOUR X) ou 'all' pour batch : ") or "je veux ça"

    conversation_history = ""
    base_state = {
        "photo_collected": False,
        "paiement_collected": False,
        "zone_collected": False,
        "tel_collected": False,
        "tel_valide": False,
        "collected_count": 0,
        "is_complete": False,
    }

    print("\n=== ETAPE 0: RECUPERATION TEMPLATE SUPABASE (1 seule fois) ===")
    base_prompt_template = await get_botlive_prompt(TEST_COMPANY_ID)
    print("Longueur template:", len(base_prompt_template))

    if question.strip().lower() != "all":
        print("\n=== ETAPE 1: ROUTER EMBEDDINGS (pour fournir intent/mode/confiance à HYDE) ===")
        routing = await route_botlive_intent(
            company_id=TEST_COMPANY_ID,
            user_id=TEST_USER_ID,
            message=question,
            conversation_history=conversation_history,
            state_compact=base_state,
        )

        print(
            f"intent={routing.intent} | mode={routing.mode} | missing={routing.missing_fields} | score={routing.confidence:.2f}"
        )

        score = float(routing.confidence or 0.0)
        gating = _gating_path(score)
        print(f"GATING={gating} | HYDE_X_RANGE=[{HYDE_X_MIN:.2f},{HYDE_X_MAX:.2f}]")

        if gating != "hyde":
            print("\n[SKIP] HYDE_X non déclenché (score hors 0.55-0.69)")
            return

        print("\n=== ETAPE 2: APPEL HYDE SECOUR X (llama-3.1-8b-instant) ===")

        hyde_raw = await run_hyde_secour_x(
            base_prompt_template=base_prompt_template,
            question=question,
            conversation_history=conversation_history,
            checklist=routing.state,
            state=routing.state,
            intent=routing.intent,
            confidence=routing.confidence,
            mode=routing.mode,
            missing_fields=routing.missing_fields,
            detected_objects="",
            filtered_transactions="",
            expected_deposit="2000",
        )

        print("\n=== REPONSE BRUTE HYDE SECOUR X ===")
        print(hyde_raw)

        print("\n=== PARSE JSON (si possible) ===")
        payload = _extract_json_payload(hyde_raw)
        if payload is None:
            print("[WARN] Aucun JSON détecté dans la sortie.")
        else:
            print(json.dumps(payload, indent=2, ensure_ascii=False))

        reformulated = _extract_reformulated_text(hyde_raw)
        print("\n=== TEXTE REFORMULE UTILISE POUR RE-ROUTAGE ===")
        print(reformulated)

        reroute = await route_botlive_intent(
            company_id=TEST_COMPANY_ID,
            user_id=TEST_USER_ID,
            message=reformulated or question,
            conversation_history=conversation_history,
            state_compact=base_state,
        )
        print("\n=== RE-ROUTAGE APRES HYDE_X ===")
        print(
            f"intent={reroute.intent} | mode={reroute.mode} | missing={reroute.missing_fields} | score={reroute.confidence:.2f}"
        )
        return

    print("\n=== MODE BATCH HYDE_X (post-router) ===")
    print(f"Règle: HYDE_X s'applique seulement si score embeddings ∈ [{HYDE_X_MIN:.2f}, {HYDE_X_MAX:.2f}]")

    os.makedirs(os.path.join(_ROOT_DIR, "results"), exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_json = os.path.join(_ROOT_DIR, "results", f"hyde_x_eval_{timestamp}.json")
    out_csv = os.path.join(_ROOT_DIR, "results", f"hyde_x_eval_{timestamp}.csv")

    results: List[Dict[str, Any]] = []
    scores_post: List[float] = []
    total_in_range = 0
    total_correct = 0

    for idx, case in enumerate(AMBIGUOUS_CASES, 1):
        q = str(case.get("question") or "")
        expected_intent = str(case.get("expected_intent") or "")
        expected_score = float(case.get("score") or 0.0)

        routing0 = await route_botlive_intent(
            company_id=TEST_COMPANY_ID,
            user_id=TEST_USER_ID,
            message=q,
            conversation_history=conversation_history,
            state_compact=base_state,
        )

        score0 = float(routing0.confidence or 0.0)
        gating = _gating_path(score0)

        entry: Dict[str, Any] = {
            "index": idx,
            "question": q,
            "expected": {"intent": expected_intent, "score_initial": expected_score},
            "initial": {
                "intent": routing0.intent,
                "confidence": score0,
                "mode": routing0.mode,
                "missing_fields": routing0.missing_fields,
            },
            "gating": gating,
            "hyde": None,
            "post": None,
            "correct": None,
        }

        effective_intent = routing0.intent
        effective_score = score0

        if gating == "hyde":
            total_in_range += 1
            try:
                hyde_raw = await run_hyde_secour_x(
                    base_prompt_template=base_prompt_template,
                    question=q,
                    conversation_history=conversation_history,
                    checklist=routing0.state,
                    state=routing0.state,
                    intent=routing0.intent,
                    confidence=routing0.confidence,
                    mode=routing0.mode,
                    missing_fields=routing0.missing_fields,
                    detected_objects="",
                    filtered_transactions="",
                    expected_deposit="2000",
                )
                reformulated = _extract_reformulated_text(hyde_raw)

                routing1 = await route_botlive_intent(
                    company_id=TEST_COMPANY_ID,
                    user_id=TEST_USER_ID,
                    message=reformulated or q,
                    conversation_history=conversation_history,
                    state_compact=base_state,
                )
                score1 = float(routing1.confidence or 0.0)
                scores_post.append(score1)

                entry["hyde"] = {
                    "raw": hyde_raw,
                    "reformulated": reformulated,
                    "payload": _extract_json_payload(hyde_raw),
                }
                entry["post"] = {
                    "intent": routing1.intent,
                    "confidence": score1,
                    "mode": routing1.mode,
                    "missing_fields": routing1.missing_fields,
                }

                effective_intent = routing1.intent
                effective_score = score1
            except Exception as e:
                entry["hyde"] = {"error": str(e)}

        is_correct = bool(expected_intent and effective_intent == expected_intent)
        entry["correct"] = is_correct
        if gating == "hyde" and is_correct:
            total_correct += 1

        results.append(entry)

        print(
            f"[{idx:02d}] score0={score0:.2f} gating={gating:<8} expected={expected_intent:<15} "
            f"initial={routing0.intent:<15} -> final={effective_intent:<15} (score={effective_score:.2f})"
        )

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "index",
                "question",
                "expected_intent",
                "initial_intent",
                "initial_confidence",
                "gating",
                "hyde_reformulated",
                "post_intent",
                "post_confidence",
                "correct",
                "hyde_error",
            ],
        )
        writer.writeheader()
        for r in results:
            writer.writerow(
                {
                    "index": r.get("index"),
                    "question": r.get("question"),
                    "expected_intent": (r.get("expected") or {}).get("intent"),
                    "initial_intent": (r.get("initial") or {}).get("intent"),
                    "initial_confidence": (r.get("initial") or {}).get("confidence"),
                    "gating": r.get("gating"),
                    "hyde_reformulated": ((r.get("hyde") or {}) if isinstance(r.get("hyde"), dict) else {}).get(
                        "reformulated"
                    ),
                    "post_intent": (r.get("post") or {}).get("intent"),
                    "post_confidence": (r.get("post") or {}).get("confidence"),
                    "correct": r.get("correct"),
                    "hyde_error": ((r.get("hyde") or {}) if isinstance(r.get("hyde"), dict) else {}).get("error"),
                }
            )

    print("\n=== RÉSUMÉ HYDE_X ===")
    print(f"Questions total: {len(AMBIGUOUS_CASES)}")
    print(f"Questions dans range HYDE_X: {total_in_range}")
    if total_in_range:
        rate = 100.0 * (total_correct / total_in_range)
        print(f"Routage correct (HYDE_X uniquement): {total_correct}/{total_in_range} = {rate:.1f}%")
    else:
        print("Routage correct (HYDE_X uniquement): N/A")

    if scores_post:
        bins = [0.0, 0.55, 0.60, 0.65, 0.70, 0.80, 1.01]
        counts = _histogram(scores_post, bins)
        print("\nDistribution scores post-HYDE_X:")
        for i in range(len(counts)):
            lo, hi = bins[i], bins[i + 1]
            bar = "#" * counts[i]
            print(f"  [{lo:.2f}-{hi:.2f}] {counts[i]:>3} {bar}")

    print("\n=== EXPORT ===")
    print(f"JSON: {out_json}")
    print(f"CSV : {out_csv}")


if __name__ == "__main__":
    asyncio.run(main())
