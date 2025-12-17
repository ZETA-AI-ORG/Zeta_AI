from __future__ import annotations

import os
import threading
from typing import List, Sequence, Union

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None  # type: ignore


_LOCK = threading.RLock()
_MODEL: SentenceTransformer | None = None
_MODEL_NAME: str | None = None


def _bool_env(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "y", "on"}


def _ensure_cache_dir() -> None:
    cache_dir = (os.getenv("EMBEDDING_CACHE_DIR", "") or "").strip()
    if not cache_dir:
        return

    os.environ.setdefault("HF_HOME", cache_dir)
    os.environ.setdefault("TRANSFORMERS_CACHE", cache_dir)


def _get_model_name() -> str:
    return (os.getenv("EMBEDDING_MODEL", "") or "").strip() or "paraphrase-xlm-r-multilingual-v1"


def get_embedding_model() -> SentenceTransformer:
    global _MODEL, _MODEL_NAME

    with _LOCK:
        model_name = _get_model_name()

        if _MODEL is not None and _MODEL_NAME == model_name:
            return _MODEL

        if SentenceTransformer is None:
            raise RuntimeError(
                "sentence-transformers n'est pas disponible. Installe la dépendance (requirements.txt)"
            )

        _ensure_cache_dir()

        _MODEL = SentenceTransformer(model_name)
        _MODEL_NAME = model_name
        return _MODEL


class EmbeddingService:
    def __init__(self) -> None:
        self.model = get_embedding_model()
        self.model_name = _get_model_name()
        self.normalize = _bool_env("EMBEDDING_NORMALIZE", True)
        self.batch_size = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))

    def encode(self, texts: Union[str, Sequence[str]]) -> Union[np.ndarray, List[np.ndarray]]:
        if isinstance(texts, str):
            t = texts.strip()
            if not t:
                return np.zeros((0,), dtype=np.float32)
            v = self.model.encode(
                t,
                convert_to_tensor=False,
                normalize_embeddings=self.normalize,
            )
            return np.asarray(v, dtype=np.float32)

        cleaned = [t.strip() for t in texts if isinstance(t, str) and t.strip()]
        if not cleaned:
            return []

        vecs = self.model.encode(
            cleaned,
            batch_size=self.batch_size,
            convert_to_tensor=False,
            normalize_embeddings=self.normalize,
            show_progress_bar=False,
        )
        return [np.asarray(v, dtype=np.float32) for v in vecs]


_SERVICE: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    global _SERVICE
    with _LOCK:
        if _SERVICE is None:
            _SERVICE = EmbeddingService()
        return _SERVICE
