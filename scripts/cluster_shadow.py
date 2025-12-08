import os
import json
import asyncio
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import Counter, defaultdict

import numpy as np

import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.global_embedding_cache import get_cached_embedding
from core.botlive_stopwords import extract_botlive_keywords

SHADOW_PAIRS_PATH = Path("data/shadow/shadow_pairs.jsonl")
CANONICAL_QA_PATH = Path("data/shadow/canonical_qa.jsonl")

MIN_CLUSTER_SIM = float(os.getenv("CANONICAL_MIN_CLUSTER_SIM", "0.82"))
MIN_OPERATOR_DIVERSITY = int(os.getenv("CANONICAL_MIN_OPERATOR_DIVERSITY", "3"))
MAX_QUESTIONS_PER_CLUSTER = int(os.getenv("CANONICAL_MAX_Q_PER_CLUSTER", "40"))
MAX_OUTPUT = int(os.getenv("CANONICAL_MAX_OUTPUT", "200"))
EMBED_MODEL = os.getenv("CANONICAL_EMBED_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")

# Intent clustering (A2 + CLU-1)
CLUSTER_MODE = os.getenv("CLUSTER_MODE", "intent").lower()
CLUSTER_WINDOW_DAYS = int(os.getenv("CLUSTER_WINDOW_DAYS", "0"))
CLUSTER_MIN_CONFIDENCE = float(os.getenv("CLUSTER_MIN_CONFIDENCE", "0.0"))
CLUSTER_FILTER_COMPANY_ID = os.getenv("CLUSTER_FILTER_COMPANY_ID", "").strip()
CLUSTER_INTENTS = os.getenv("CLUSTER_INTENTS", "all").strip()
CLUSTER_MIN_SIZE = int(os.getenv("CLUSTER_MIN_SIZE", "3"))
CLUSTER_MAX_EXAMPLES_PER_CLUSTER = int(os.getenv("CLUSTER_MAX_EXAMPLES_PER_CLUSTER", "5"))
CLUSTER_OUT_DIR = Path(os.getenv("CLUSTER_OUT_DIR", "data/clusters"))
CLUSTER_MAX_CLUSTERS_PER_INTENT = int(os.getenv("CLUSTER_MAX_CLUSTERS_PER_INTENT", "100"))


def _cos(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))


def _load_pairs() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if not SHADOW_PAIRS_PATH.exists():
        return items
    with SHADOW_PAIRS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if obj.get("type") == "pair" and obj.get("message_client") and obj.get("response_operateur"):
                items.append(obj)
    return items


async def _embed_batch_texts(texts: List[str], model_name: str) -> List[np.ndarray]:
    embs: List[np.ndarray] = []
    for t in texts:
        try:
            e = await get_cached_embedding(t, model_name)
            embs.append(np.asarray(e, dtype=np.float32))
        except Exception:
            embs.append(None)
    return embs


def _medoid_index(embs: List[np.ndarray]) -> int:
    if not embs:
        return -1
    mat = np.vstack(embs)
    # Cosine sim via dot (assume normalized)
    sims = mat @ mat.T
    sums = sims.sum(axis=1)
    return int(np.argmax(sums))


async def build_canonicals() -> int:
    pairs = _load_pairs()
    if not pairs:
        print("No pairs found. Nothing to cluster.")
        return 0

    qs = [p["message_client"].strip() for p in pairs]
    ans = [p["response_operateur"].strip() for p in pairs]
    ops = [p.get("operateur_display_name") or p.get("user_id") or "unknown" for p in pairs]

    print(f"Embedding {len(qs)} questions with model={EMBED_MODEL}...")
    q_embs = await _embed_batch_texts(qs, EMBED_MODEL)

    # Online greedy clustering by centroid similarity
    clusters: List[Dict[str, Any]] = []
    for i, qe in enumerate(q_embs):
        if qe is None:
            continue
        placed = False
        for c in clusters:
            centroid = c["centroid"]
            if _cos(qe, centroid) >= MIN_CLUSTER_SIM:
                # add
                c["idxs"].append(i)
                c["sum_vec"] += qe
                # renormalize centroid
                norm = np.linalg.norm(c["sum_vec"]) or 1.0
                c["centroid"] = c["sum_vec"] / norm
                placed = True
                break
        if not placed:
            clusters.append({
                "idxs": [i],
                "sum_vec": qe.copy(),
                "centroid": qe.copy(),
            })

    # Build canonicals per cluster
    out: List[Dict[str, Any]] = []
    for c in clusters:
        idxs: List[int] = c["idxs"]
        if len(idxs) < 3:
            continue
        # Cap the cluster size for speed
        if len(idxs) > MAX_QUESTIONS_PER_CLUSTER:
            idxs = idxs[:MAX_QUESTIONS_PER_CLUSTER]
        sub_embs = [q_embs[i] for i in idxs]
        medoid = _medoid_index([e for e in sub_embs if e is not None])
        if medoid < 0:
            continue
        medoid_global_idx = idxs[medoid]
        # consensus score: avg cos to medoid
        mvec = q_embs[medoid_global_idx]
        sims = [(i, _cos(mvec, q_embs[i])) for i in idxs if q_embs[i] is not None]
        avg_consensus = float(np.mean([s for _, s in sims])) if sims else 0.0
        # operator diversity on the cluster
        op_set = set(ops[i] for i in idxs)
        if len(op_set) < MIN_OPERATOR_DIVERSITY:
            continue
        # choose canonical answer: pick the answer paired with medoid question
        canonical_answer = ans[medoid_global_idx]
        questions_examples = [qs[i] for i, s in sorted(sims, key=lambda x: -x[1])[:5]]
        out.append({
            "questions_examples": questions_examples,
            "canonical_answer": canonical_answer,
            "consensus_score": round(avg_consensus, 3),
            "operator_diversity": len(op_set),
            "cluster_size": len(idxs),
        })
        if len(out) >= MAX_OUTPUT:
            break

    if not out:
        print("No canonical items produced (try lowering thresholds).")
        return 0

    CANONICAL_QA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CANONICAL_QA_PATH.open("w", encoding="utf-8") as f:
        for item in out:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"Wrote {len(out)} canonical items to {CANONICAL_QA_PATH}")
    return len(out)


# ------------------------------
# Per-intent clustering (A2 + CLU-1)
# ------------------------------
def _iter_shadow_user_messages() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if not SHADOW_PAIRS_PATH.exists():
        return items
    now_ts = int(time.time())
    with SHADOW_PAIRS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("type") != "user_message":
                continue
            ts = rec.get("ts")
            if CLUSTER_WINDOW_DAYS > 0 and isinstance(ts, (int, float)):
                if now_ts - int(ts) > CLUSTER_WINDOW_DAYS * 86400:
                    continue
            intent = rec.get("intent_pred") or {}
            if CLUSTER_MIN_CONFIDENCE > 0.0:
                conf_val = intent.get("confidence")
                try:
                    if conf_val is None or float(conf_val) < CLUSTER_MIN_CONFIDENCE:
                        continue
                except (TypeError, ValueError):
                    continue
            best_id = intent.get("best_id")
            if best_id is None:
                continue
            company_id = rec.get("company_id") or "unknown"
            if CLUSTER_FILTER_COMPANY_ID and str(company_id) != CLUSTER_FILTER_COMPANY_ID:
                continue
            txt = (rec.get("text") or rec.get("message") or "").strip()
            if not txt:
                continue
            items.append({
                "intent_id": str(best_id),
                "company_id": str(company_id),
                "text": txt,
            })
    return items


async def _embed_texts(texts: List[str]) -> List[np.ndarray | None]:
    out: List[np.ndarray | None] = []
    for t in texts:
        try:
            vec = await get_cached_embedding(t, EMBED_MODEL)
            v = np.asarray(vec, dtype=np.float32)
            n = np.linalg.norm(v) or 1.0
            out.append(v / n)
        except Exception:
            out.append(None)
    return out


def _greedy_cluster(embs: List[np.ndarray], min_sim: float) -> List[Dict[str, Any]]:
    clusters: List[Dict[str, Any]] = []
    for i, e in enumerate(embs):
        placed = False
        for c in clusters:
            centroid = c["centroid"]
            if float(np.dot(e, centroid)) >= min_sim:
                c["idxs"].append(i)
                c["sum_vec"] += e
                norm = np.linalg.norm(c["sum_vec"]) or 1.0
                c["centroid"] = c["sum_vec"] / norm
                placed = True
                break
        if not placed:
            clusters.append({
                "idxs": [i],
                "sum_vec": e.copy(),
                "centroid": e.copy(),
            })
    return clusters


async def build_intent_clusters() -> int:
    msgs = _iter_shadow_user_messages()
    if not msgs:
        print("No user messages. Nothing to cluster.")
        return 0
    # Group by intent
    by_intent: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in msgs:
        by_intent[r["intent_id"]].append(r)

    # Filter intents if provided
    intents_target: List[str]
    if CLUSTER_INTENTS.lower() == "all" or not CLUSTER_INTENTS:
        intents_target = sorted(by_intent.keys(), key=lambda x: int(x))
    else:
        intents_target = [s.strip() for s in CLUSTER_INTENTS.split(",") if s.strip()]

    CLUSTER_OUT_DIR.mkdir(parents=True, exist_ok=True)
    total_clusters = 0

    for iid in intents_target:
        records = by_intent.get(iid) or []
        if not records:
            continue
        texts = [r["text"] for r in records]
        companies = [r["company_id"] for r in records]

        embs_raw = await _embed_texts(texts)
        embs: List[np.ndarray] = [e for e in embs_raw if e is not None]
        idx_map = [i for i, e in enumerate(embs_raw) if e is not None]
        if not embs:
            continue

        clusters = _greedy_cluster(embs, MIN_CLUSTER_SIM)
        # Build output clusters
        out_clusters: List[Dict[str, Any]] = []
        for c in clusters:
            idxs_local: List[int] = c["idxs"]
            if len(idxs_local) < CLUSTER_MIN_SIZE:
                continue
            # Map to original indices
            idxs = [idx_map[j] for j in idxs_local]
            # Medoid and consensus
            sub_embs = [embs[j] for j in idxs_local]
            med_local = _medoid_index(sub_embs)
            if med_local < 0:
                continue
            med_idx = idxs[med_local]
            mvec = embs[idxs_local[med_local]]
            sims = [(ii, float(np.dot(mvec, embs[idxs_local[k]]))) for k, ii in enumerate(idxs)]
            avg_consensus = float(np.mean([s for _, s in sims])) if sims else 0.0
            # Company support
            comp_counts: Dict[str, int] = {}
            for ii in idxs:
                comp = companies[ii]
                comp_counts[comp] = comp_counts.get(comp, 0) + 1
            company_support = len(comp_counts)
            # Keywords aggregation
            kw_counter: Counter = Counter()
            for ii in idxs:
                kws = extract_botlive_keywords(texts[ii]) or []
                for w in kws:
                    kw_counter[w] += 1
            top_kw = [
                {"word": w, "freq": int(f)}
                for w, f in kw_counter.most_common(20)
            ]
            # Top examples by similarity
            top_examples = [
                texts[ii] for ii, _ in sorted(sims, key=lambda x: -x[1])[:CLUSTER_MAX_EXAMPLES_PER_CLUSTER]
            ]
            out_clusters.append({
                "size": len(idxs),
                "consensus": round(avg_consensus, 3),
                "company_support": company_support,
                "per_company": comp_counts,
                "top_examples": top_examples,
                "keywords": top_kw,
            })
            if len(out_clusters) >= CLUSTER_MAX_CLUSTERS_PER_INTENT:
                break

        if out_clusters:
            out_path = CLUSTER_OUT_DIR / f"intent_{iid}.json"
            with out_path.open("w", encoding="utf-8") as f:
                json.dump({
                    "intent_id": iid,
                    "clusters": out_clusters,
                }, f, ensure_ascii=False, indent=2)
            print(f"[CLU] intent {iid}: wrote {len(out_clusters)} clusters -> {out_path}")
            total_clusters += len(out_clusters)

    if total_clusters == 0:
        print("No intent clusters produced (try lowering thresholds or widening window).")
    else:
        print(f"Total clusters: {total_clusters}")
    return total_clusters


if __name__ == "__main__":
    if CLUSTER_MODE == "intent":
        asyncio.run(build_intent_clusters())
    else:
        asyncio.run(build_canonicals())
