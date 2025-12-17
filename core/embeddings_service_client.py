from __future__ import annotations

import os
from typing import List, Optional

import httpx
import numpy as np


_EMBEDDINGS_SERVICE_URL = os.getenv("EMBEDDINGS_SERVICE_URL", "http://127.0.0.1:8010").strip().rstrip("/")
_EMBEDDINGS_SERVICE_API_KEY = (os.getenv("EMBEDDINGS_SERVICE_API_KEY", "") or "").strip()
_EMBEDDINGS_REMOTE_ENABLED = os.getenv("BOTLIVE_EMBEDDINGS_REMOTE_ENABLED", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "y",
    "on",
}

_TIMEOUT = float(os.getenv("EMBEDDINGS_HTTP_TIMEOUT_SECONDS", "1.2"))


def _url(path: str) -> str:
    p = (path or "").strip()
    if not p.startswith("/"):
        p = "/" + p
    return f"{_EMBEDDINGS_SERVICE_URL}{p}"


def _headers() -> dict:
    if not _EMBEDDINGS_SERVICE_API_KEY:
        return {}
    return {"x-api-key": _EMBEDDINGS_SERVICE_API_KEY}


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def embed_sync(text: str, *, client: Optional[httpx.Client] = None) -> Optional[np.ndarray]:
    if not _EMBEDDINGS_REMOTE_ENABLED:
        return None
    t = (text or "").strip()
    if not t:
        return None

    owns_client = client is None
    if client is None:
        client = httpx.Client(timeout=_TIMEOUT)

    try:
        r = client.post(_url("/embed"), json={"text": t}, headers=_headers())
        r.raise_for_status()
        data = r.json()
        emb = data.get("embedding")
        if not isinstance(emb, list) or not emb:
            return None
        return np.asarray(emb, dtype=np.float32)
    except Exception:
        return None
    finally:
        if owns_client:
            client.close()


def embed_batch_sync(texts: List[str], *, client: Optional[httpx.Client] = None) -> Optional[List[np.ndarray]]:
    if not _EMBEDDINGS_REMOTE_ENABLED:
        return None
    cleaned = [t.strip() for t in (texts or []) if isinstance(t, str) and t.strip()]
    if not cleaned:
        return None

    owns_client = client is None
    if client is None:
        client = httpx.Client(timeout=_TIMEOUT)

    try:
        r = client.post(_url("/embed_batch"), json={"texts": cleaned}, headers=_headers())
        r.raise_for_status()
        data = r.json()
        embs = data.get("embeddings")
        if not isinstance(embs, list) or not embs:
            return None
        out: List[np.ndarray] = []
        for e in embs:
            if not isinstance(e, list) or not e:
                return None
            out.append(np.asarray(e, dtype=np.float32))
        return out
    except Exception:
        return None
    finally:
        if owns_client:
            client.close()


async def embed(text: str, *, client: Optional[httpx.AsyncClient] = None) -> Optional[np.ndarray]:
    if not _EMBEDDINGS_REMOTE_ENABLED:
        return None
    t = (text or "").strip()
    if not t:
        return None

    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=_TIMEOUT)

    try:
        r = await client.post(_url("/embed"), json={"text": t}, headers=_headers())
        r.raise_for_status()
        data = r.json()
        emb = data.get("embedding")
        if not isinstance(emb, list) or not emb:
            return None
        return np.asarray(emb, dtype=np.float32)
    except Exception:
        return None
    finally:
        if owns_client:
            await client.aclose()


async def embed_batch(texts: List[str], *, client: Optional[httpx.AsyncClient] = None) -> Optional[List[np.ndarray]]:
    if not _EMBEDDINGS_REMOTE_ENABLED:
        return None
    cleaned = [t.strip() for t in (texts or []) if isinstance(t, str) and t.strip()]
    if not cleaned:
        return None

    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=_TIMEOUT)

    try:
        r = await client.post(_url("/embed_batch"), json={"texts": cleaned}, headers=_headers())
        r.raise_for_status()
        data = r.json()
        embs = data.get("embeddings")
        if not isinstance(embs, list) or not embs:
            return None
        out: List[np.ndarray] = []
        for e in embs:
            if not isinstance(e, list) or not e:
                return None
            out.append(np.asarray(e, dtype=np.float32))
        return out
    except Exception:
        return None
    finally:
        if owns_client:
            await client.aclose()
