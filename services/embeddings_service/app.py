from __future__ import annotations

import os
import time
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field

try:
    from sentence_transformers import SentenceTransformer
except Exception as e:  # pragma: no cover
    SentenceTransformer = None  # type: ignore
    _SENTENCE_TRANSFORMERS_IMPORT_ERROR = str(e)
else:
    _SENTENCE_TRANSFORMERS_IMPORT_ERROR = ""


APP_NAME = "zeta-embeddings-service"

MODEL_NAME = os.getenv("EMBEDDINGS_MODEL_NAME", "dangvantuan/sentence-camembert-large").strip() or "dangvantuan/sentence-camembert-large"
NORMALIZE = os.getenv("EMBEDDINGS_NORMALIZE", "true").strip().lower() in {"1", "true", "yes", "y", "on"}
API_KEY = (os.getenv("EMBEDDINGS_API_KEY", "") or "").strip()

_model: SentenceTransformer | None = None
_model_load_error: str | None = None


def _get_model() -> SentenceTransformer:
    global _model, _model_load_error

    if _model is not None:
        return _model

    if SentenceTransformer is None:
        raise RuntimeError(
            f"sentence-transformers not available: {_SENTENCE_TRANSFORMERS_IMPORT_ERROR}"
        )

    try:
        t0 = time.time()
        _model = SentenceTransformer(MODEL_NAME)
        _model.max_seq_length = int(os.getenv("EMBEDDINGS_MAX_SEQ_LENGTH", "384"))
        _model_load_error = None
        _ = time.time() - t0
        return _model
    except Exception as e:
        _model_load_error = str(e)
        raise


class EmbedRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)


class EmbedResponse(BaseModel):
    model: str
    dim: int
    normalized: bool
    embedding: List[float]


class EmbedBatchRequest(BaseModel):
    texts: List[str] = Field(..., min_length=1, max_length=256)


class EmbedBatchResponse(BaseModel):
    model: str
    dim: int
    normalized: bool
    embeddings: List[List[float]]


class HealthResponse(BaseModel):
    status: str
    model: str
    model_loaded: bool
    model_error: Optional[str] = None


app = FastAPI(title=APP_NAME)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    model_loaded = _model is not None
    return HealthResponse(
        status="ok" if model_loaded or not _model_load_error else "degraded",
        model=MODEL_NAME,
        model_loaded=model_loaded,
        model_error=_model_load_error,
    )


@app.post("/embed", response_model=EmbedResponse)
def embed(req: EmbedRequest, x_api_key: Optional[str] = Header(default=None)) -> EmbedResponse:
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is empty")

    if API_KEY and (x_api_key or "") != API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")

    try:
        model = _get_model()
        vec = model.encode(text, convert_to_tensor=False, normalize_embeddings=NORMALIZE)
        embedding = [float(x) for x in vec]
        return EmbedResponse(
            model=MODEL_NAME,
            dim=len(embedding),
            normalized=NORMALIZE,
            embedding=embedding,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"embed_failed: {e}")


@app.post("/embed_batch", response_model=EmbedBatchResponse)
def embed_batch(req: EmbedBatchRequest, x_api_key: Optional[str] = Header(default=None)) -> EmbedBatchResponse:
    texts = [t.strip() for t in (req.texts or []) if isinstance(t, str) and t.strip()]
    if not texts:
        raise HTTPException(status_code=400, detail="texts is empty")

    if API_KEY and (x_api_key or "") != API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")

    try:
        model = _get_model()
        vecs = model.encode(texts, batch_size=int(os.getenv("EMBEDDINGS_BATCH_SIZE", "32")), convert_to_tensor=False, normalize_embeddings=NORMALIZE, show_progress_bar=False)
        embeddings = [[float(x) for x in v] for v in vecs]
        dim = len(embeddings[0]) if embeddings else 0
        return EmbedBatchResponse(
            model=MODEL_NAME,
            dim=dim,
            normalized=NORMALIZE,
            embeddings=embeddings,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"embed_batch_failed: {e}")
