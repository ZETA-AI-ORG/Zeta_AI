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

from datetime import datetime

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


class CatalogV2SyncLocalAndUpsertPromptRequest(BaseModel):
    company_id: str
    catalog: Dict[str, Any]
    version: Optional[int] = None
    updated_at: Optional[str] = None
    ai_name: Optional[str] = None
    company_name: Optional[str] = None


class CatalogV2SyncLocalAndUpsertPromptResponse(BaseModel):
    success: bool
    company_id: str
    path: Optional[str] = None
    prompt_chars: Optional[int] = None
    catalogue_chars: Optional[int] = None
    updated_at: Optional[str] = None
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


def _build_catalogue_block_from_catalog_v2(catalog: Dict[str, Any]) -> str:
    try:
        if not isinstance(catalog, dict) or not catalog:
            return ""

        def _parse_unit_size(unit_key: str) -> Optional[int]:
            s = str(unit_key or "").strip().lower()
            if not s or "_" not in s:
                return None
            try:
                tail = s.split("_", 1)[1]
                n = int(re.sub(r"\D+", "", tail) or "0")
                return n if n > 0 else None
            except Exception:
                return None

        def _parse_price_value(v: Any) -> Optional[int]:
            try:
                if v is None:
                    return None
                if isinstance(v, list) and len(v) >= 1:
                    return int(float(v[0]))
                return int(float(v))
            except Exception:
                return None

        canonical_units = catalog.get("canonical_units")
        if not isinstance(canonical_units, list):
            canonical_units = []
        canonical_units = [str(u).strip() for u in canonical_units if str(u).strip()]

        ui_state = catalog.get("ui_state")
        if not isinstance(ui_state, dict):
            ui_state = {}
        custom_formats = ui_state.get("customFormats")
        if not isinstance(custom_formats, list):
            custom_formats = []

        vtree = catalog.get("v")
        if not isinstance(vtree, dict):
            vtree = {}

        technical_specs = str(catalog.get("technical_specs") or "").strip()
        sales_constraints = str(catalog.get("sales_constraints") or "").strip()

        lines = []
        lines.append("# CATALOGUE_REFERENCE (AUTO)\n")

        lines.append("## CANONICAL_UNITS")
        if canonical_units:
            for u in canonical_units:
                lines.append(f"- {u}")
        else:
            lines.append("- (none)")
        lines.append("")

        lines.append("## FORMATS_DE_VENTE")
        if custom_formats:
            for f in custom_formats:
                if not isinstance(f, dict):
                    continue
                f_type = str(f.get("type") or "").strip()
                qty = f.get("quantity")
                label = str(f.get("label") or "").strip()
                enabled = f.get("enabled")

                try:
                    qty_i = int(qty) if qty is not None else None
                except Exception:
                    qty_i = None

                canonical = ""
                if f_type and qty_i and qty_i > 0:
                    canonical = f"{f_type}_{qty_i}"
                enabled_s = "true" if enabled is True else ("false" if enabled is False else "")

                tail = []
                if canonical:
                    tail.append(f"canonical={canonical}")
                if enabled_s:
                    tail.append(f"enabled={enabled_s}")
                tail_s = (" | " + ", ".join(tail)) if tail else ""

                head = f"- {label}" if label else "- (format)"
                if f_type and qty_i and qty_i > 0:
                    head += f" -> {f_type} x {qty_i}"
                lines.append(head + tail_s)
        else:
            lines.append("- (none)")
        lines.append("")

        lines.append("## UNITS_PAR_PRODUIT")
        if vtree:
            for variant_name, node in vtree.items():
                if not isinstance(node, dict):
                    continue
                vname = str(variant_name)
                lines.append(f"### product={vname}")

                u_map = node.get("u")
                s_map = node.get("s")

                if isinstance(u_map, dict) and u_map:
                    units = [str(k) for k in u_map.keys()]
                    units = [u for u in units if u]
                    units = sorted(units)
                    for u in units:
                        lines.append(f"- unit: {u}")
                    lines.append("")
                    continue

                if isinstance(s_map, dict) and s_map:
                    for sub_name, sub_node in s_map.items():
                        if not isinstance(sub_node, dict):
                            continue
                        sub_u = sub_node.get("u")
                        if not isinstance(sub_u, dict) or not sub_u:
                            continue
                        sname = str(sub_name)
                        lines.append(f"- specs: {sname}")
                        units = [str(k) for k in sub_u.keys()]
                        units = [u for u in units if u]
                        units = sorted(units)
                        for u in units:
                            lines.append(f"  - unit: {u}")
                    lines.append("")
                    continue

                lines.append("- (no units)")
                lines.append("")
        else:
            lines.append("- (none)")

        # Conservative, data-driven rules derived only from structured price data.
        lines.append("")
        lines.append("## AUTO_RULES (DEDUCTIONS_SURES)")
        if not vtree:
            lines.append("- (none)")
        else:
            for variant_name, node in vtree.items():
                if not isinstance(node, dict):
                    continue
                vname = str(variant_name)
                lines.append(f"### product={vname}")

                node_s = node.get("s")
                u_map_variant = node.get("u") if isinstance(node.get("u"), dict) else None

                # Build a matrix: spec_label -> {unit_key -> price_int}
                matrix: Dict[str, Dict[str, int]] = {}
                if isinstance(node_s, dict) and node_s:
                    for sub_name, sub_node in node_s.items():
                        if not isinstance(sub_node, dict):
                            continue
                        sub_u = sub_node.get("u")
                        if not isinstance(sub_u, dict):
                            continue
                        row: Dict[str, int] = {}
                        for unit_key, raw_price in sub_u.items():
                            p = _parse_price_value(raw_price)
                            if p is None or p <= 0:
                                continue
                            row[str(unit_key)] = p
                        if row:
                            matrix[str(sub_name)] = row
                elif isinstance(u_map_variant, dict) and u_map_variant:
                    row2: Dict[str, int] = {}
                    for unit_key, raw_price in u_map_variant.items():
                        p = _parse_price_value(raw_price)
                        if p is None or p <= 0:
                            continue
                        row2[str(unit_key)] = p
                    if row2:
                        matrix["__base__"] = row2

                allowed_units = sorted({u for row in matrix.values() for u in row.keys()})
                if allowed_units:
                    lines.append(f"- allowed_units: {', '.join(allowed_units)}")
                else:
                    lines.append("- allowed_units: (none)")

                # Pricing varies by specs only if we can observe multiple spec rows with different prices.
                pricing_varies_by_specs: Optional[bool] = None
                if len(matrix.keys()) >= 2:
                    seen_diff = False
                    for u in allowed_units:
                        prices = {row.get(u) for row in matrix.values() if row.get(u) is not None}
                        prices = {p for p in prices if isinstance(p, int)}
                        if len(prices) >= 2:
                            seen_diff = True
                            break
                    pricing_varies_by_specs = True if seen_diff else False

                if pricing_varies_by_specs is True:
                    lines.append("- pricing_by_specs: VARIABLE")
                elif pricing_varies_by_specs is False:
                    lines.append("- pricing_by_specs: FIXE (observed)")
                else:
                    lines.append("- pricing_by_specs: UNKNOWN")

                # Volume discount (safe): compute per spec/base row and aggregate conservatively.
                # true only if all rows show a discount; false only if all rows show no discount; else unknown.
                def _row_has_discount(row: Dict[str, int]) -> Optional[bool]:
                    if not isinstance(row, dict) or not row:
                        return None
                    pairs = []
                    for u, price in row.items():
                        size = _parse_unit_size(u)
                        if size is None or size <= 0:
                            continue
                        if not isinstance(price, int) or price <= 0:
                            continue
                        pairs.append((size, price / float(size)))
                    pairs = sorted(pairs, key=lambda x: x[0])
                    if len(pairs) < 2:
                        return None

                    min_unit_price_so_far = pairs[0][1]
                    for _, unit_p in pairs[1:]:
                        if unit_p < min_unit_price_so_far - 1e-9:
                            return True
                        min_unit_price_so_far = min(min_unit_price_so_far, unit_p)
                    return False

                row_flags = []
                for row in matrix.values():
                    flag = _row_has_discount(row)
                    if flag is None:
                        continue
                    row_flags.append(flag)

                vol_discount: Optional[bool] = None
                if row_flags:
                    if all(row_flags):
                        vol_discount = True
                    elif (not any(row_flags)):
                        vol_discount = False
                    else:
                        vol_discount = None

                if vol_discount is True:
                    lines.append("- volume_discount: true")
                elif vol_discount is False:
                    lines.append("- volume_discount: false")
                else:
                    lines.append("- volume_discount: unknown")

                lines.append("")

        if technical_specs:
            lines.append("## TECHNICAL_SPECS (RAW)")
            lines.append(technical_specs)
            lines.append("")

        if sales_constraints:
            lines.append("## SALES_CONSTRAINTS (RAW)")
            lines.append(sales_constraints)
            lines.append("")

        return "\n".join(lines).strip() + "\n"
    except Exception:
        return ""


def _write_local_catalog(company_id: str, payload: CatalogV2SyncLocalRequest) -> str:
    if not company_id or not str(company_id).strip():
        raise HTTPException(status_code=400, detail="company_id requis")
    if not isinstance(payload.catalog, dict):
        raise HTTPException(status_code=400, detail="catalog invalide")

    cid = str(company_id).strip()
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

    safe_id = re.sub(r"[^a-zA-Z0-9\-_]", "_", cid)
    if not safe_id:
        raise HTTPException(status_code=400, detail="company_id invalide")

    final_path = os.path.join(base_dir, f"{safe_id}.json")
    wrapper = {
        "company_id": cid,
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

        invalidate_company_catalog_v2_cache(cid)
    except Exception:
        pass

    return final_path


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

    company_id = str(payload.company_id).strip()
    final_path = _write_local_catalog(company_id, payload)
    return CatalogV2SyncLocalResponse(success=True, company_id=company_id, path=final_path, timestamp=time.time())


@router.post("/sync-local-and-upsert-botlive-catalogue-block-deepseek", response_model=CatalogV2SyncLocalAndUpsertPromptResponse)
async def sync_local_and_upsert_botlive_catalogue_block_deepseek(
    request: Request, payload: CatalogV2SyncLocalAndUpsertPromptRequest
) -> CatalogV2SyncLocalAndUpsertPromptResponse:
    _check_internal_key(request)

    company_id = str(payload.company_id).strip()
    final_path = _write_local_catalog(company_id, payload)  # type: ignore[arg-type]

    catalogue_block = _build_catalogue_block_from_catalog_v2(payload.catalog)
    if not catalogue_block or not catalogue_block.strip():
        raise HTTPException(status_code=400, detail="catalogue_block vide")

    try:
        from database.supabase_client import get_supabase_client
        from Zeta_AI.ingestion.ingestion_api import _inject_catalogue_block

        supabase = get_supabase_client()
        now_iso = datetime.now().isoformat()

        existing_prompt = ""
        try:
            resp = (
                supabase.table("company_rag_configs")
                .select("prompt_botlive_deepseek_v3")
                .eq("company_id", company_id)
                .single()
                .execute()
            )
            if resp and getattr(resp, "data", None):
                existing_prompt = str((resp.data or {}).get("prompt_botlive_deepseek_v3") or "")
        except Exception:
            existing_prompt = ""

        updated_prompt = _inject_catalogue_block(existing_prompt, catalogue_block)
        if not updated_prompt or len(updated_prompt.strip()) < 50:
            raise HTTPException(status_code=400, detail="prompt_deepseek introuvable ou trop court: initialise d'abord le prompt")

        row: Dict[str, Any] = {
            "company_id": company_id,
            "prompt_botlive_deepseek_v3": updated_prompt,
            "botlive_prompts_updated_at": now_iso,
        }
        if payload.ai_name is not None and str(payload.ai_name).strip():
            row["ai_name"] = str(payload.ai_name).strip()
        if payload.company_name is not None and str(payload.company_name).strip():
            row["company_name"] = str(payload.company_name).strip()

        supabase.table("company_rag_configs").upsert(row, on_conflict="company_id").execute()

        logger.info(
            "[CATALOG_V2][SYNC+PROMPT] ✅ company_id=%s | catalogue_chars=%s | prompt_chars=%s",
            company_id,
            len(str(catalogue_block)),
            len(str(updated_prompt)),
        )

        return CatalogV2SyncLocalAndUpsertPromptResponse(
            success=True,
            company_id=company_id,
            path=final_path,
            prompt_chars=len(str(updated_prompt)),
            catalogue_chars=len(str(catalogue_block)),
            updated_at=now_iso,
            timestamp=time.time(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[CATALOG_V2][SYNC+PROMPT] ❌")
        raise HTTPException(status_code=500, detail=str(e))


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
