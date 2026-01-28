#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import tempfile
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/catalog-v2", tags=["Catalog V2"])


class CatalogV2UpsertRequest(BaseModel):
    company_id: str
    catalog: Dict[str, Any]


class CatalogV2UpsertResponse(BaseModel):
    success: bool
    company_id: str
    id: Optional[str] = None
    version: Optional[int] = None
    updated_at: Optional[str] = None
    timestamp: float


class CatalogV2SyncLocalRequest(BaseModel):
    company_id: str
    catalog: Dict[str, Any]
    version: Optional[int] = None
    updated_at: Optional[str] = None


class CatalogV2SyncLocalResponse(BaseModel):
    success: bool
    company_id: str
    path: Optional[str] = None
    timestamp: float


class CatalogV2GetResponse(BaseModel):
    company_id: str
    exists: bool
    catalog: Optional[Dict[str, Any]] = None
    id: Optional[str] = None
    version: Optional[int] = None
    updated_at: Optional[str] = None
    timestamp: float


def _check_internal_key(request: Request) -> None:
    """
    Protection minimale optionnelle.

    Si CATALOG_V2_INTERNAL_KEY est défini, alors le client doit envoyer:
    - header: x-internal-key: <valeur>

    Sinon, l'endpoint reste accessible (utile en dev).
    """
    expected = os.getenv("CATALOG_V2_INTERNAL_KEY")
    if not expected:
        return

    provided = request.headers.get("x-internal-key") or request.headers.get("X-Internal-Key")
    if not provided or provided != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/upsert", response_model=CatalogV2UpsertResponse)
async def upsert_company_catalog_v2(request: Request, payload: CatalogV2UpsertRequest) -> CatalogV2UpsertResponse:
    _check_internal_key(request)

    if not payload.company_id or not str(payload.company_id).strip():
        raise HTTPException(status_code=400, detail="company_id requis")

    try:
        from database.supabase_client import get_supabase_client

        client = get_supabase_client()
        company_id = str(payload.company_id).strip()

        def _sync():
            existing = (
                client.table("company_catalogs_v2")
                .select("id,version,updated_at")
                .eq("company_id", company_id)
                .eq("is_active", True)
                .limit(1)
                .execute()
            )
            data = getattr(existing, "data", None) or []

            if data:
                row = data[0]
                current_version = int(row.get("version") or 1)
                new_version = current_version + 1
                updated = (
                    client.table("company_catalogs_v2")
                    .update({"catalog": payload.catalog, "version": new_version})
                    .eq("id", row.get("id"))
                    .execute()
                )
                out = (getattr(updated, "data", None) or [])
                if out:
                    r = out[0]
                    return r.get("id"), int(r.get("version") or new_version), r.get("updated_at")
                return row.get("id"), new_version, row.get("updated_at")

            inserted = (
                client.table("company_catalogs_v2")
                .insert({
                    "company_id": company_id,
                    "catalog": payload.catalog,
                    "version": 1,
                    "is_active": True,
                })
                .execute()
            )
            out = (getattr(inserted, "data", None) or [])
            if not out:
                return None, 1, None
            r = out[0]
            return r.get("id"), int(r.get("version") or 1), r.get("updated_at")

        catalog_id, version, updated_at = await asyncio.to_thread(_sync)

        try:
            from core.company_catalog_v2_loader import invalidate_company_catalog_v2_cache

            invalidate_company_catalog_v2_cache(company_id)
        except Exception:
            pass

        return CatalogV2UpsertResponse(
            success=True,
            company_id=company_id,
            id=str(catalog_id) if catalog_id else None,
            version=version,
            updated_at=updated_at,
            timestamp=time.time(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CATALOG_V2] Upsert error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Erreur sauvegarde catalogue")


@router.post("/sync-local", response_model=CatalogV2SyncLocalResponse)
async def sync_company_catalog_v2_local(request: Request, payload: CatalogV2SyncLocalRequest) -> CatalogV2SyncLocalResponse:
    _check_internal_key(request)

    if not payload.company_id or not str(payload.company_id).strip():
        raise HTTPException(status_code=400, detail="company_id requis")

    if not isinstance(payload.catalog, dict):
        raise HTTPException(status_code=400, detail="catalog invalide")

    company_id = str(payload.company_id).strip()
    base_dir = os.getenv("CATALOG_V2_LOCAL_DIR") or "/data/catalogs"
    try:
        base_dir = str(base_dir).strip() or "/data/catalogs"
    except Exception:
        base_dir = "/data/catalogs"

    try:
        os.makedirs(base_dir, exist_ok=True)
    except Exception as e:
        logger.error(f"[CATALOG_V2] sync-local mkdir error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Erreur écriture cache catalogue")

    safe_id = re.sub(r"[^a-zA-Z0-9\-_]", "_", company_id)
    if not safe_id:
        raise HTTPException(status_code=400, detail="company_id invalide")

    final_path = os.path.join(base_dir, f"{safe_id}.json")
    wrapper = {
        "company_id": company_id,
        "version": payload.version,
        "updated_at": payload.updated_at,
        "catalog": payload.catalog,
        "synced_at": time.time(),
    }

    try:
        tmp_path = None
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=base_dir, prefix=f"{safe_id}.", suffix=".tmp") as f:
            tmp_path = f.name
            json.dump(wrapper, f, ensure_ascii=False)
        os.replace(tmp_path, final_path)
    except Exception as e:
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except Exception:
            pass
        logger.error(f"[CATALOG_V2] sync-local write error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Erreur écriture cache catalogue")

    try:
        from core.company_catalog_v2_loader import invalidate_company_catalog_v2_cache

        invalidate_company_catalog_v2_cache(company_id)
    except Exception:
        pass

    return CatalogV2SyncLocalResponse(success=True, company_id=company_id, path=final_path, timestamp=time.time())


@router.get("/{company_id}", response_model=CatalogV2GetResponse)
async def get_company_catalog_v2(request: Request, company_id: str) -> CatalogV2GetResponse:
    _check_internal_key(request)

    if not company_id or not str(company_id).strip():
        raise HTTPException(status_code=400, detail="company_id requis")

    try:
        from database.supabase_client import get_supabase_client

        client = get_supabase_client()
        cid = str(company_id).strip()

        def _sync():
            resp = (
                client.table("company_catalogs_v2")
                .select("id,company_id,catalog,version,updated_at")
                .eq("company_id", cid)
                .eq("is_active", True)
                .order("updated_at", desc=True)
                .limit(1)
                .execute()
            )
            data = getattr(resp, "data", None) or []
            return data[0] if data else None

        row = await asyncio.to_thread(_sync)
        if not row:
            return CatalogV2GetResponse(company_id=cid, exists=False, timestamp=time.time())

        return CatalogV2GetResponse(
            company_id=cid,
            exists=True,
            catalog=row.get("catalog"),
            id=row.get("id"),
            version=int(row.get("version") or 1),
            updated_at=row.get("updated_at"),
            timestamp=time.time(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CATALOG_V2] Get error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Erreur récupération catalogue")
