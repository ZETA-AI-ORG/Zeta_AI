import os
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import numpy as np

from embedding_models import EMBEDDING_MODELS, DEFAULT_EMBEDDING_MODEL
from core.global_embedding_cache import get_cached_embedding

# Fichiers de données
CANONICAL_QA_PATH = Path("data/shadow/canonical_qa.jsonl")
SHADOW_PAIRS_PATH = Path("data/shadow/shadow_pairs.jsonl")

# Cache en mémoire (process)
_INDEX: Dict[str, Any] = {
    "model_name": None,
    "questions": [],  # type: List[str]
    "answers": [],    # type: List[str]
    "embeddings": None,  # type: Optional[np.ndarray]
    "mtime": 0.0,
    "source": None,   # "canonical" ou "pairs"
}

MAX_ITEMS = int(os.getenv("CANONICAL_MAX_ITEMS", "400"))
MIN_SIM = float(os.getenv("CANONICAL_MIN_SIM", "0.82"))
EMBED_KEY = os.getenv("CANONICAL_EMBED_MODEL", DEFAULT_EMBEDDING_MODEL)


def _get_model_name() -> str:
    try:
        return EMBEDDING_MODELS.get(EMBED_KEY, EMBEDDING_MODELS[DEFAULT_EMBEDDING_MODEL])["name"]
    except Exception:
        # Fallback robuste
        return EMBEDDING_MODELS[DEFAULT_EMBEDDING_MODEL]["name"]


def _cosine_sim(vec: np.ndarray, mat: np.ndarray) -> np.ndarray:
    if mat is None or mat.size == 0:
        return np.zeros((0,), dtype=np.float32)
    # Les embeddings sortent déjà normalisés
    return mat @ vec  # produit scalaire = cos sim


def _read_jsonl_tail(path: Path, limit: int) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    items: List[Dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            # Lire tout puis prendre la fin (simple et fiable; fichiers modestes)
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(json.loads(line))
                except Exception:
                    continue
        if limit > 0 and len(items) > limit:
            items = items[-limit:]
        return items
    except Exception:
        return []


async def _ensure_index(model_name: str) -> None:
    global _INDEX

    # Choisir la meilleure source disponible
    canonical_items = _read_jsonl_tail(CANONICAL_QA_PATH, MAX_ITEMS)
    if canonical_items:
        src = "canonical"
        # Utiliser mtime du fichier canonical
        mtime = CANONICAL_QA_PATH.stat().st_mtime
        raw_questions: List[str] = []
        raw_answers: List[str] = []
        for it in canonical_items:
            # Attendu: {canonical_answer, questions_examples: [..], consensus_score, ...}
            ans = it.get("canonical_answer") or it.get("answer") or ""
            q_examples = it.get("questions_examples") or []
            q = q_examples[0] if q_examples else it.get("question") or ""
            q = (q or "").strip()
            ans = (ans or "").strip()
            if q and ans:
                raw_questions.append(q)
                raw_answers.append(ans)
    else:
        src = "pairs"
        mtime = SHADOW_PAIRS_PATH.stat().st_mtime if SHADOW_PAIRS_PATH.exists() else 0.0
        pair_items = _read_jsonl_tail(SHADOW_PAIRS_PATH, MAX_ITEMS)
        raw_questions = []
        raw_answers = []
        for it in pair_items:
            if it.get("type") == "pair":
                q = (it.get("message_client") or "").strip()
                a = (it.get("response_operateur") or "").strip()
                if q and a:
                    raw_questions.append(q)
                    raw_answers.append(a)

    # Vérifier si index déjà à jour
    if (
        _INDEX["model_name"] == model_name
        and _INDEX["mtime"] == mtime
        and _INDEX["source"] == src
        and len(_INDEX.get("questions", [])) == len(raw_questions)
    ):
        return

    # (Re)construire l'index
    _INDEX["model_name"] = model_name
    _INDEX["questions"] = raw_questions
    _INDEX["answers"] = raw_answers
    _INDEX["mtime"] = mtime
    _INDEX["source"] = src

    # Générer embeddings un par un (API cache async unitaire)
    embs: List[np.ndarray] = []
    for q in raw_questions:
        try:
            e = await get_cached_embedding(q, model_name)
            embs.append(np.asarray(e, dtype=np.float32))
        except Exception:
            embs.append(None)
    # Filtrer les None, réaligner
    filt_questions: List[str] = []
    filt_answers: List[str] = []
    filt_embs: List[np.ndarray] = []
    for q, a, e in zip(raw_questions, raw_answers, embs):
        if e is not None:
            filt_questions.append(q)
            filt_answers.append(a)
            filt_embs.append(e)
    if filt_embs:
        _INDEX["questions"] = filt_questions
        _INDEX["answers"] = filt_answers
        _INDEX["embeddings"] = np.vstack(filt_embs)
    else:
        _INDEX["embeddings"] = np.zeros((0, 1), dtype=np.float32)


def format_suggestions_for_prompt(suggestions: List[Dict[str, Any]]) -> str:
    if not suggestions:
        return ""
    lines = [
        "[SUGGESTIONS CANONIQUES - à utiliser si pertinentes]",
    ]
    for i, s in enumerate(suggestions, 1):
        ans = (s.get("answer") or "").strip().replace("\n", " ")
        if len(ans) > 280:
            ans = ans[:277] + "..."
        score = s.get("score")
        src = s.get("source")
        lines.append(f"{i}. {ans}  (score={score:.2f}, src={src})")
    return "\n".join(lines)


async def get_canonical_suggestions(
    question: str,
    company_id: Optional[str] = None,
    top_k: int = 2,
    min_similarity: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Retourne jusqu'à top_k suggestions canoniques pour la question.
    S'appuie sur canonical_qa.jsonl si présent, sinon fallback sur shadow_pairs.jsonl (paires récentes).
    """
    enabled = os.getenv("CANONICAL_SUGGESTIONS_ENABLED", "true").lower() == "true"
    if not enabled:
        return []

    q = (question or "").strip()
    if not q:
        return []

    model_name = _get_model_name()
    await _ensure_index(model_name)

    mat = _INDEX.get("embeddings")
    questions = _INDEX.get("questions", [])
    answers = _INDEX.get("answers", [])
    src = _INDEX.get("source") or "unknown"

    if mat is None or len(questions) == 0:
        return []

    # Embedding de la question
    try:
        q_emb_list = await get_cached_embedding(q, model_name)
        q_emb = np.asarray(q_emb_list, dtype=np.float32)
    except Exception:
        return []

    sims = _cosine_sim(q_emb, mat)
    if sims.size == 0:
        return []

    # Seuil par défaut
    th = MIN_SIM if min_similarity is None else float(min_similarity)

    # Top-k indices
    order = np.argsort(-sims)[: top_k * 3]  # sur-échantillonner puis filtrer

    seen_answers = set()
    suggestions: List[Dict[str, Any]] = []
    for idx in order:
        score = float(sims[idx])
        if score < th:
            continue
        ans = answers[idx]
        if ans in seen_answers:
            continue
        seen_answers.add(ans)
        suggestions.append({
            "answer": ans,
            "score": score,
            "source": src,
            "question_example": questions[idx],
        })
        if len(suggestions) >= top_k:
            break

    return suggestions
