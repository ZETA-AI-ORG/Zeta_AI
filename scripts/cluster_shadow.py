import os
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Tuple

import numpy as np

import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.global_embedding_cache import get_cached_embedding

SHADOW_PAIRS_PATH = Path("data/shadow/shadow_pairs.jsonl")
CANONICAL_QA_PATH = Path("data/shadow/canonical_qa.jsonl")

MIN_CLUSTER_SIM = float(os.getenv("CANONICAL_MIN_CLUSTER_SIM", "0.82"))
MIN_OPERATOR_DIVERSITY = int(os.getenv("CANONICAL_MIN_OPERATOR_DIVERSITY", "3"))
MAX_QUESTIONS_PER_CLUSTER = int(os.getenv("CANONICAL_MAX_Q_PER_CLUSTER", "40"))
MAX_OUTPUT = int(os.getenv("CANONICAL_MAX_OUTPUT", "200"))
EMBED_MODEL = os.getenv("CANONICAL_EMBED_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")


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


if __name__ == "__main__":
    asyncio.run(build_canonicals())
