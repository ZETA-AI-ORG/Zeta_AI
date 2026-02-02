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
debug_router = APIRouter(prefix="/api/catalog", tags=["Catalog Debug"])


def _norm_name_for_id(name: str) -> str:
    try:
        t = str(name or "").strip().lower()
    except Exception:
        t = ""
    if not t:
        return ""
    try:
        import unicodedata as _ud

        t = _ud.normalize("NFKD", t)
        t = "".join([c for c in t if not _ud.combining(c)])
    except Exception:
        pass
    t = re.sub(r"[^a-z0-9\s-]+", " ", t)
    t = t.replace("-", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _stable_product_id_from_name(name: str) -> str:
    base = _norm_name_for_id(name)
    if not base:
        return ""
    try:
        import hashlib as _hashlib

        h = _hashlib.sha1(base.encode("utf-8", errors="replace")).hexdigest()
        return f"prod_{h[:8]}"
    except Exception:
        return ""


def _anchor_product_id_in_catalog(catalog: Any, product_id: str, product_name: str) -> None:
    try:
        if not isinstance(catalog, dict):
            return
        pid = str(product_id or "").strip()
        pn = str(product_name or "").strip()
        if pid and not str(catalog.get("product_id") or "").strip():
            catalog["product_id"] = pid
        if pn and not str(catalog.get("product_name") or catalog.get("name") or "").strip():
            catalog["product_name"] = pn
    except Exception:
        return


def _anchor_product_ids_in_payload(catalog: Any) -> Any:
    if not isinstance(catalog, dict):
        return catalog

    plist = catalog.get("products")
    if isinstance(plist, list):
        for p in plist:
            if not isinstance(p, dict):
                continue
            pn = str(p.get("product_name") or p.get("name") or "").strip()
            pid = str(p.get("product_id") or "").strip()
            if not pid and pn:
                pid = _stable_product_id_from_name(pn)
                if pid:
                    p["product_id"] = pid
            cat_sub = p.get("catalog_v2")
            if isinstance(cat_sub, dict):
                _anchor_product_id_in_catalog(cat_sub, pid, pn)
        return catalog

    pn2 = str(catalog.get("product_name") or catalog.get("name") or "").strip()
    pid2 = str(catalog.get("product_id") or "").strip()
    if not pid2 and pn2:
        pid2 = _stable_product_id_from_name(pn2)
    _anchor_product_id_in_catalog(catalog, pid2, pn2)
    return catalog


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
    product_name: Optional[str] = None


class CatalogV2SyncLocalAndUpsertPromptResponse(BaseModel):
    success: bool
    company_id: str
    path: Optional[str] = None
    prompt_chars: Optional[int] = None
    catalogue_chars: Optional[int] = None
    debug: Optional[Dict[str, Any]] = None
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

        def _compress_labels(labels: list[str]) -> str:
            items = [str(x).strip() for x in (labels or []) if str(x).strip()]
            if not items:
                return ""
            items = sorted(set(items), key=lambda x: x)

            def _compress_numeric(items2: list[str]) -> Optional[str]:
                nums = []
                for x in items2:
                    if not re.fullmatch(r"\d+", x):
                        return None
                    nums.append(int(x))
                nums = sorted(set(nums))
                if len(nums) <= 2:
                    return ", ".join(str(n) for n in nums)
                if nums == list(range(min(nums), max(nums) + 1)):
                    return f"{min(nums)}-{max(nums)}"
                return None

            def _compress_prefix_numeric(items2: list[str]) -> Optional[str]:
                parsed = []
                prefix = None
                for x in items2:
                    m = re.fullmatch(r"([A-Za-z]+)(\d+)", x)
                    if not m:
                        return None
                    if prefix is None:
                        prefix = m.group(1)
                    if m.group(1) != prefix:
                        return None
                    parsed.append(int(m.group(2)))
                parsed = sorted(set(parsed))
                if len(parsed) <= 2:
                    return ", ".join(f"{prefix}{n}" for n in parsed)
                if parsed == list(range(min(parsed), max(parsed) + 1)):
                    return f"{prefix}{min(parsed)}-{prefix}{max(parsed)}"
                return None

            compact = _compress_prefix_numeric(items) or _compress_numeric(items)
            if compact:
                return compact
            if len(items) <= 8:
                return ", ".join(items)
            return f"{items[0]}, …, {items[-1]} ({len(items)})"

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
            lines.append(f"- {', '.join(sorted(set(canonical_units)))}")
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
                label = str(f.get("label") or f.get("customLabel") or f.get("custom_label") or "").strip()
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
                    units = sorted(set(units))
                    if units:
                        lines.append(f"- formats: {', '.join(units)}")
                    else:
                        lines.append("- formats: (none)")
                    lines.append("")
                    continue

                if isinstance(s_map, dict) and s_map:
                    # format-first projection:
                    # 1) gather units per spec
                    spec_to_units: Dict[str, list[str]] = {}
                    all_units: set[str] = set()
                    for sub_name, sub_node in s_map.items():
                        if not isinstance(sub_node, dict):
                            continue
                        sub_u = sub_node.get("u")
                        if not isinstance(sub_u, dict) or not sub_u:
                            continue
                        units = [str(k) for k in sub_u.keys()]
                        units = [u for u in units if u]
                        units = sorted(set(units))
                        if not units:
                            continue
                        spec_to_units[str(sub_name)] = units
                        for u in units:
                            all_units.add(u)

                    if all_units:
                        lines.append(f"- formats: {', '.join(sorted(all_units))}")
                    else:
                        lines.append("- formats: (none)")
                        lines.append("")
                        continue

                    # 2) If each spec maps to exactly one unit, group specs by unit.
                    if spec_to_units and all(len(v) == 1 for v in spec_to_units.values()):
                        unit_to_specs: Dict[str, list[str]] = {}
                        for spec, units in spec_to_units.items():
                            unit_to_specs.setdefault(units[0], []).append(spec)
                        for unit in sorted(unit_to_specs.keys()):
                            specs_s = _compress_labels(unit_to_specs.get(unit) or [])
                            if specs_s:
                                lines.append(f"- {unit}: {specs_s}")
                    else:
                        # 3) General case: group by unit-set.
                        groups: Dict[str, Dict[str, Any]] = {}
                        for spec, units in spec_to_units.items():
                            key = "|".join(units)
                            if key not in groups:
                                groups[key] = {"units": units, "specs": []}
                            groups[key]["specs"].append(spec)
                        for g in sorted(groups.values(), key=lambda x: ",".join(x.get("units") or [])):
                            specs = _compress_labels(g.get("specs") or [])
                            units_s = "+".join(g.get("units") or [])
                            if specs:
                                lines.append(f"- {units_s}: {specs}")

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
                    lines.append(f"- sold_only_by: {', '.join(allowed_units)}")
                else:
                    lines.append("- allowed_units: (none)")
                    lines.append("- sold_only_by: (none)")

                # Pricing varies by specs only if we can observe multiple spec rows with different prices.
                pricing_varies_by_specs: Optional[bool] = None
                if isinstance(node_s, dict) and node_s:
                    if len(matrix.keys()) >= 2:
                        seen_diff = False
                        for u in allowed_units:
                            prices = {row.get(u) for row in matrix.values() if row.get(u) is not None}
                            prices = {p for p in prices if isinstance(p, int)}
                            if len(prices) >= 2:
                                seen_diff = True
                                break
                        pricing_varies_by_specs = True if seen_diff else False
                elif isinstance(u_map_variant, dict) and u_map_variant:
                    pricing_varies_by_specs = False

                if pricing_varies_by_specs is True:
                    lines.append("- pricing_by_specs: VARIABLE")
                elif pricing_varies_by_specs is False:
                    lines.append("- pricing_by_specs: FIXE (observed)")
                else:
                    lines.append("- pricing_by_specs: UNKNOWN")

                # Volume discount (safe): compute per spec/base row and aggregate conservatively.
                # true only if all rows show a discount; false only if all rows show no discount; else unknown.
                # If there is only one unit overall, it's safely false.
                if len(allowed_units) <= 1:
                    lines.append("- volume_discount: false")
                    lines.append("")
                    continue

                def _row_has_discount(row: Dict[str, int]) -> bool:
                    pairs = []
                    for u, price in (row or {}).items():
                        size = _parse_unit_size(u)
                        if size is None or size <= 0:
                            continue
                        if not isinstance(price, int) or price <= 0:
                            continue
                        pairs.append((size, price / float(size)))
                    pairs = sorted(pairs, key=lambda x: x[0])
                    if len(pairs) < 2:
                        return False

                    min_unit_price_so_far = pairs[0][1]
                    for _, unit_p in pairs[1:]:
                        if unit_p < min_unit_price_so_far - 1e-9:
                            return True
                        min_unit_price_so_far = min(min_unit_price_so_far, unit_p)
                    return False

                row_flags = [_row_has_discount(row) for row in matrix.values()]
                vol_discount: Optional[bool]
                if row_flags and all(row_flags):
                    vol_discount = True
                elif row_flags and (not any(row_flags)):
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

    def _norm_product_key(v: str) -> str:
        try:
            import unicodedata

            t = str(v or "").strip()
            t = unicodedata.normalize("NFKD", t)
            t = "".join(ch for ch in t if not unicodedata.combining(ch))
            t = re.sub(r"\s+", " ", t).strip()
            return t.upper()
        except Exception:
            return str(v or "").strip().upper()

    incoming_catalog = payload.catalog
    incoming_name = str(incoming_catalog.get("product_name") or incoming_catalog.get("name") or "").strip()
    if not incoming_name:
        raise HTTPException(status_code=400, detail="product_name requis dans catalog")
    incoming_pid = _stable_product_id_from_name(incoming_name) or ""
    if incoming_pid:
        _anchor_product_id_in_catalog(incoming_catalog, incoming_pid, incoming_name)

    existing_container: Dict[str, Any] = {}
    try:
        if os.path.exists(final_path):
            with open(final_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            existing_container = raw.get("catalog") if isinstance(raw, dict) and isinstance(raw.get("catalog"), dict) else (raw if isinstance(raw, dict) else {})
    except Exception:
        existing_container = {}

    # Ensure container shape: { products: [ {product_id, product_name, catalog_v2, updated_at, version} ] }
    products_list: list[Dict[str, Any]] = []
    if isinstance(existing_container.get("products"), list):
        products_list = [x for x in existing_container.get("products") if isinstance(x, dict)]
    else:
        # Legacy mono-product file: convert to container if it looks like a catalog_v2
        legacy = existing_container if isinstance(existing_container, dict) else {}
        legacy_name = str(legacy.get("product_name") or legacy.get("name") or "").strip()
        if legacy_name:
            products_list = [
                {
                    "product_id": str(legacy.get("product_id") or "").strip() or _stable_product_id_from_name(legacy_name) or _norm_product_key(legacy_name),
                    "product_name": legacy_name,
                    "catalog_v2": legacy,
                }
            ]

    # Upsert product entry
    out_products: list[Dict[str, Any]] = []
    found = False
    for p in products_list:
        pid = _norm_product_key(str(p.get("product_id") or ""))
        p_name = str(p.get("product_name") or "").strip()
        name_key = _norm_product_key(p_name)
        incoming_name_key = _norm_product_key(incoming_name)
        same_by_name = bool(incoming_name_key and name_key and name_key == incoming_name_key)
        same_by_pid = bool(incoming_pid and pid and pid == _norm_product_key(incoming_pid))
        if same_by_name or same_by_pid:
            if incoming_pid and str(p.get("product_id") or "").strip() != incoming_pid:
                p["product_id"] = incoming_pid
            cat_existing = p.get("catalog_v2")
            if isinstance(cat_existing, dict) and incoming_pid:
                _anchor_product_id_in_catalog(cat_existing, incoming_pid, incoming_name)
            out_products.append(
                {
                    "product_id": incoming_pid or str(p.get("product_id") or "").strip() or _norm_product_key(incoming_name),
                    "product_name": incoming_name,
                    "catalog_v2": incoming_catalog,
                    "updated_at": payload.updated_at,
                    "version": payload.version,
                }
            )
            found = True
        else:
            out_products.append(p)

    if not found:
        out_products.append(
            {
                "product_id": incoming_pid or _norm_product_key(incoming_name),
                "product_name": incoming_name,
                "catalog_v2": incoming_catalog,
                "updated_at": payload.updated_at,
                "version": payload.version,
            }
        )

    wrapper = {
        "company_id": cid,
        "version": payload.version,
        "updated_at": payload.updated_at,
        "catalog": {
            "products": out_products,
        },
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

        try:
            payload.catalog = _anchor_product_ids_in_payload(payload.catalog)
        except Exception:
            pass

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
    request: Request,
    payload: CatalogV2SyncLocalAndUpsertPromptRequest,
    debug: bool = False,
    upsert_prompt: bool = False,
) -> CatalogV2SyncLocalAndUpsertPromptResponse:
    _check_internal_key(request)

    company_id = str(payload.company_id).strip()

    # Backward/forward compatibility:
    # allow sending product_name at the payload top-level, but store it inside catalog.
    try:
        if isinstance(payload.catalog, dict):
            pn_top = str(getattr(payload, "product_name", "") or "").strip()
            pn_in = str(payload.catalog.get("product_name") or "").strip()
            if pn_top and not pn_in:
                payload.catalog["product_name"] = pn_top
    except Exception:
        pass

    final_path = _write_local_catalog(company_id, payload)  # type: ignore[arg-type]

    catalogue_block = _build_catalogue_block_from_catalog_v2(payload.catalog)
    if not catalogue_block or not catalogue_block.strip():
        raise HTTPException(status_code=400, detail="catalogue_block vide")

    def _upsert_product_index_block(existing_prompt: str, product_name: str) -> str:
        p = str(existing_prompt or "")
        pn = str(product_name or "").strip()
        if not pn:
            return p

        def _norm_name_for_id(name: str) -> str:
            try:
                t = str(name or "").strip().lower()
            except Exception:
                t = ""
            if not t:
                return ""
            try:
                import unicodedata as _ud

                t = _ud.normalize("NFKD", t)
                t = "".join([c for c in t if not _ud.combining(c)])
            except Exception:
                pass
            t = re.sub(r"[^a-z0-9\s-]+", " ", t)
            t = t.replace("-", " ")
            t = re.sub(r"\s+", " ", t).strip()
            return t

        def _product_id_hash(name: str) -> str:
            base = _norm_name_for_id(name)
            if not base:
                return ""
            try:
                import hashlib as _hashlib

                h = _hashlib.sha1(base.encode("utf-8", errors="replace")).hexdigest()
                return f"prod_{h[:8]}"
            except Exception:
                return ""

        pid = _product_id_hash(pn)
        entry = f"{pn} [ID: {pid}]" if pid else pn
        start_tag = "[[PRODUCT_INDEX_START]]"
        end_tag = "[[PRODUCT_INDEX_END]]"
        si = p.find(start_tag)
        ei = p.find(end_tag)
        if si != -1 and ei != -1 and ei > si:
            block_start = si + len(start_tag)
            existing_block = p[block_start:ei]
            raw_lines = [ln.strip() for ln in str(existing_block or "").splitlines()]
            items: list[tuple[str, str, str]] = []
            # Keep existing entries but dedupe by prod_ id if present.
            seen_pids: set[str] = set()
            for ln in raw_lines:
                if not ln:
                    continue
                if ln.startswith("-"):
                    n = ln[1:].strip()
                else:
                    n = ln
                if not n:
                    continue
                m_pid = re.search(r"\bprod_[0-9a-f]{8}\b", n, flags=re.IGNORECASE)
                existing_pid = str(m_pid.group(0)).lower() if m_pid else ""
                name_only = re.sub(r"\s*\[ID:\s*prod_[0-9a-f]{8}\s*\]\s*", "", n, flags=re.IGNORECASE).strip()
                if existing_pid:
                    if existing_pid in seen_pids:
                        continue
                    seen_pids.add(existing_pid)
                items.append((name_only, existing_pid, n))

            if pid:
                if pid not in seen_pids:
                    items.append((pn, pid, entry))
                    seen_pids.add(pid)
                else:
                    # Upgrade legacy name-only entry to include [ID: ...] if matching product name.
                    upgraded: list[tuple[str, str, str]] = []
                    for name_only, existing_pid, raw in items:
                        if (not existing_pid) and name_only.strip().lower() == pn.strip().lower():
                            upgraded.append((pn, pid, entry))
                        else:
                            upgraded.append((name_only, existing_pid, raw))
                    items = upgraded
            else:
                # If no pid, keep legacy behavior by name.
                if pn.strip().lower() not in {it[0].strip().lower() for it in items if it[0]}:
                    items.append((pn, "", pn))

            items_sorted = sorted(items, key=lambda it: (it[0] or "").lower())
            new_block = "\n" + "\n".join([f"- {it[2]}" for it in items_sorted if (it[2] or "").strip()]) + "\n"
            return p[:block_start] + new_block + p[ei:]

        insertion = "\n".join(
            [
                start_tag,
                f"- {entry}",
                end_tag,
                "",
            ]
        )
        return insertion + p

    def _clear_catalogue_markers(existing_prompt: str) -> str:
        p = str(existing_prompt or "")
        if not p.strip():
            return p
        try:
            import re as _re

            pat = r"\[CATALOGUE_START\](.*?)\[CATALOGUE_END\]"
            matches = list(_re.finditer(pat, p, flags=_re.IGNORECASE | _re.DOTALL))
            if matches:
                m = matches[-1]
                replacement = "[CATALOGUE_START]\n\n[CATALOGUE_END]"
                out = p[: m.start()] + replacement + p[m.end() :]
                return str(out)
        except Exception:
            pass
        return p

    try:
        from database.supabase_client import get_supabase_client
        import hashlib

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

        # IMPORTANT: we do NOT persist catalogue content inside the Supabase prompt.
        # We keep the markers but force them empty.
        updated_prompt = _clear_catalogue_markers(existing_prompt)
        try:
            updated_prompt = _upsert_product_index_block(updated_prompt, str(payload.catalog.get("product_name") or ""))
        except Exception:
            pass
        if not updated_prompt or len(updated_prompt.strip()) < 50:
            raise HTTPException(status_code=400, detail="prompt_deepseek introuvable ou trop court: initialise d'abord le prompt")

        debug_payload: Optional[Dict[str, Any]] = None
        if debug:
            injected_block = ""
            markers_found = 0
            try:
                import re as _re

                pat = r"\[CATALOGUE_START\](.*?)\[CATALOGUE_END\]"
                matches = list(_re.finditer(pat, str(updated_prompt or ""), flags=_re.IGNORECASE | _re.DOTALL))
                markers_found = len(matches)
                if matches:
                    injected_block = str(matches[-1].group(1) or "").strip()
            except Exception:
                injected_block = ""

            gen_block = str(catalogue_block or "").strip()
            gen_hash = hashlib.sha256(gen_block.encode("utf-8", errors="replace")).hexdigest() if gen_block else ""
            inj_hash = hashlib.sha256(injected_block.encode("utf-8", errors="replace")).hexdigest() if injected_block else ""

            debug_payload = {
                "supabase_table": "company_rag_configs",
                "supabase_column": "prompt_botlive_deepseek_v3",
                "markers_found": markers_found,
                "generated_catalogue_block": gen_block,
                "generated_catalogue_block_chars": len(gen_block),
                "generated_catalogue_block_sha256": gen_hash,
                "injected_catalogue_block": injected_block,
                "injected_catalogue_block_chars": len(injected_block),
                "injected_catalogue_block_sha256": inj_hash,
                "injected_equals_generated": bool(gen_block and injected_block and gen_hash == inj_hash),
                "note": "Catalogue block is NOT persisted in Supabase prompt; markers are kept empty.",
            }

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
            debug=debug_payload,
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


@debug_router.get("/debug/{company_id}")
async def debug_company_catalog_v2(request: Request, company_id: str) -> Dict[str, Any]:
    _check_internal_key(request)
    cid = str(company_id or "").strip()
    if not cid:
        raise HTTPException(status_code=400, detail="company_id requis")
    try:
        from core.company_catalog_v2_loader import get_company_catalog_v2_container

        catalog = get_company_catalog_v2_container(cid)
        if not isinstance(catalog, dict):
            raise HTTPException(status_code=404, detail="catalog_v2 introuvable")

        anchored = _anchor_product_ids_in_payload(catalog)

        products = []
        try:
            plist = anchored.get("products") if isinstance(anchored, dict) else None
            if isinstance(plist, list):
                products = [p for p in plist if isinstance(p, dict)]
            else:
                products = [anchored] if isinstance(anchored, dict) else []
        except Exception:
            products = []

        products_meta = []
        for p in products:
            try:
                # In container form, product fields can be on p or inside p['catalog_v2'].
                cat = p.get("catalog_v2") if isinstance(p.get("catalog_v2"), dict) else p
                pid = str(p.get("product_id") or cat.get("product_id") or "").strip()
                pname = str(p.get("product_name") or cat.get("product_name") or cat.get("name") or "").strip()
                tech = str(cat.get("technical_specs") or "")
                sales = str(cat.get("sales_constraints") or "")
                vtree = cat.get("v")
                products_meta.append(
                    {
                        "product_id": pid or None,
                        "product_name": pname or None,
                        "technical_specs_length": len(tech),
                        "sales_constraints_length": len(sales),
                        "fields_present": {
                            "technical_specs": bool(str(tech or "").strip()),
                            "sales_constraints": bool(str(sales or "").strip()),
                            "v": isinstance(vtree, dict) and bool(vtree),
                        },
                    }
                )
            except Exception:
                continue
        return {
            "company_id": cid,
            "exists": True,
            "products_count": len(products_meta),
            "products": products_meta,
            "catalog": anchored,
            "timestamp": time.time(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CATALOG_V2][DEBUG] error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Erreur debug catalogue")


@debug_router.get("/debug/{company_id}/{product_id}")
async def debug_company_product_catalog_v2(request: Request, company_id: str, product_id: str) -> Dict[str, Any]:
    _check_internal_key(request)
    cid = str(company_id or "").strip()
    pid = str(product_id or "").strip()
    if not cid:
        raise HTTPException(status_code=400, detail="company_id requis")
    if not pid:
        raise HTTPException(status_code=400, detail="product_id requis")
    try:
        from core.company_catalog_v2_loader import get_company_product_catalog_v2

        mono = get_company_product_catalog_v2(cid, pid)
        if not isinstance(mono, dict):
            raise HTTPException(status_code=404, detail="catalog_v2 produit introuvable")
        anchored = _anchor_product_ids_in_payload(mono)
        try:
            tech = str(anchored.get("technical_specs") or "")
        except Exception:
            tech = ""
        try:
            sales = str(anchored.get("sales_constraints") or "")
        except Exception:
            sales = ""
        try:
            vtree = anchored.get("v")
        except Exception:
            vtree = None
        return {
            "company_id": cid,
            "product_id": pid,
            "exists": True,
            "technical_specs_length": len(tech),
            "sales_constraints_length": len(sales),
            "fields_present": {
                "technical_specs": bool(str(tech or "").strip()),
                "sales_constraints": bool(str(sales or "").strip()),
                "v": isinstance(vtree, dict) and bool(vtree),
            },
            "catalog": anchored,
            "timestamp": time.time(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CATALOG_V2][DEBUG_PRODUCT] error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Erreur debug catalogue produit")
