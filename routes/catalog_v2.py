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
    product_id: Optional[str] = None
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
    product_id: Optional[str] = None
    technical_specs: Optional[str] = None
    sales_constraints: Optional[str] = None
    description: Optional[str] = None
    important_note: Optional[str] = None


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
    from core.catalogue_block_builder import build_catalogue_block_from_catalog_v2

    return build_catalogue_block_from_catalog_v2(catalog)

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

        unit_formats = ui_state.get("unitFormats")
        if not isinstance(unit_formats, dict):
            unit_formats = {}
        piece_enabled = bool(isinstance(unit_formats.get("piece"), dict) and unit_formats.get("piece", {}).get("enabled") is True)

        product_options = catalog.get("product_options")
        if not isinstance(product_options, list):
            product_options = []

        bot_format = catalog.get("bot_format")
        if not isinstance(bot_format, dict):
            bot_format = {}

        pricing_mode = str(bot_format.get("pricing_mode") or "").strip().lower()
        sales_target = str(bot_format.get("sales_target") or bot_format.get("sales_mode") or "").strip().lower()
        required_options = bot_format.get("required_options") if isinstance(bot_format.get("required_options"), list) else []
        selling_formats = bot_format.get("selling_formats") if isinstance(bot_format.get("selling_formats"), list) else []
        free_texts = bot_format.get("free_texts") if isinstance(bot_format.get("free_texts"), dict) else {}

        def _fmt_label_from_item(row: Dict[str, Any]) -> str:
            f_type = str(row.get("type") or "").strip().lower()
            qty = row.get("qty")
            label = str(row.get("label") or row.get("customLabel") or row.get("custom_label") or "").strip()
            if label:
                return label
            try:
                qty_i = int(qty) if qty is not None else None
            except Exception:
                qty_i = None
            type_label_map = {
                "piece": "Pièce",
                "lot": "Lot de",
                "paquet": "Paquet de",
                "balle": "Balle de",
                "carton": "Carton de",
                "pack": "Pack de",
                "caisse": "Caisse de",
            }
            if f_type and qty_i and qty_i > 0:
                prefix = type_label_map.get(f_type, f_type.capitalize())
                return f"{prefix} {qty_i}".strip()
            return f_type or "Format"

        format_catalog: list[Dict[str, Any]] = []
        for f in custom_formats:
            if not isinstance(f, dict):
                continue
            f_type = str(f.get("type") or "").strip().lower()
            qty = f.get("qty", f.get("quantity"))
            enabled = f.get("enabled")
            try:
                qty_i = int(qty) if qty is not None else None
            except Exception:
                qty_i = None
            if not f_type or not qty_i or qty_i <= 0:
                continue
            canonical = f"{f_type}_{qty_i}"
            format_catalog.append(
                {
                    "key": canonical,
                    "label": _fmt_label_from_item(f),
                    "enabled": enabled is not False,
                    "type": f_type,
                    "qty": qty_i,
                }
            )

        vtree = catalog.get("v")
        if not isinstance(vtree, dict):
            vtree = {}

        technical_specs = ""
        sales_constraints = ""
        important_note = ""
        if isinstance(free_texts, dict):
            technical_specs = str(free_texts.get("technical_specs") or "").strip()
            sales_constraints = str(free_texts.get("sales_constraints") or "").strip()
            important_note = str(free_texts.get("important_note") or "").strip()
        if not technical_specs and isinstance(ui_state, dict):
            technical_specs = str(ui_state.get("technicalSpecs") or "").strip()
        if not sales_constraints and isinstance(ui_state, dict):
            sales_constraints = str(ui_state.get("salesConstraints") or "").strip()
        if not important_note and isinstance(ui_state, dict):
            important_note = str(ui_state.get("importantNote") or "").strip()
        if not technical_specs:
            technical_specs = str(catalog.get("technical_specs") or "").strip()
        if not sales_constraints:
            sales_constraints = str(catalog.get("sales_constraints") or "").strip()
        if not important_note:
            important_note = str(catalog.get("important_note") or "").strip()
        description = str(catalog.get("description") or "").strip()

        lines = []
        lines.append("# CATALOGUE_REFERENCE (AUTO)\n")

        lines.append("## CANONICAL_UNITS")
        if canonical_units:
            lines.append(f"- {', '.join(sorted(set(canonical_units)))}")
        else:
            lines.append("- (none)")
        lines.append("")

        lines.append("## PRICING_MODE")
        if pricing_mode:
            lines.append(f"- pricing_mode: `{pricing_mode}`")
        else:
            lines.append("- pricing_mode: (unknown)")
        if sales_target:
            lines.append(f"- sales_target: `{sales_target}`")
        lines.append("")

        lines.append("## FORMATS_DE_VENTE")
        if selling_formats:
            for f in selling_formats:
                if not isinstance(f, dict):
                    continue
                fname = str(f.get("format_name") or "").strip()
                cid = str(f.get("canonical_id") or "").strip()
                try:
                    min_order_i = int(f.get("min_order") or 0)
                except Exception:
                    min_order_i = 0
                price_v = f.get("price")
                price_i = None
                try:
                    if price_v is not None and str(price_v).strip() != "":
                        price_i = int(float(price_v))
                except Exception:
                    price_i = None
                tail = []
                if cid:
                    tail.append(f"canonical={cid}")
                if price_i is not None:
                    tail.append(f"price={price_i}")
                if min_order_i > 0:
                    tail.append(f"min_order={min_order_i}")
                tail_s = (" | " + ", ".join(tail)) if tail else ""
                lines.append(f"- (format) -> {fname}{tail_s}" if fname else f"- (format){tail_s}")
        elif format_catalog:
            for f in format_catalog:
                enabled_s = "true" if f.get("enabled") is True else ("false" if f.get("enabled") is False else "")
                tail = []
                if f.get("key"):
                    tail.append(f"canonical={f['key']}")
                if enabled_s:
                    tail.append(f"enabled={enabled_s}")
                tail_s = (" | " + ", ".join(tail)) if tail else ""
                head = f"- {f.get('label') or '(format)'}"
                if f.get("type") and f.get("qty"):
                    head += f" -> {f['type']} x {f['qty']}"
                lines.append(head + tail_s)
        else:
            lines.append("- (none)")
        lines.append("")

        lines.append("## OPTIONS_CLIENT")
        if required_options:
            for opt in required_options:
                if not isinstance(opt, dict):
                    continue
                name = str(opt.get("name") or opt.get("label") or opt.get("key") or "").strip()
                mandatory = bool(opt.get("is_mandatory") if opt.get("is_mandatory") is not None else opt.get("required"))
                values = opt.get("values") if isinstance(opt.get("values"), list) else []
                values_txt = ", ".join(f"`{str(v).strip()}`" for v in values if str(v).strip())
                if name:
                    lines.append(f"- {name} ({'Obligatoire' if mandatory else 'Facultatif'}) : {values_txt}" if values_txt else f"- {name} ({'Obligatoire' if mandatory else 'Facultatif'})")
        elif product_options:
            for opt in product_options:
                if not isinstance(opt, dict):
                    continue
                key = str(opt.get("key") or opt.get("label") or "").strip()
                label = str(opt.get("label") or key or "").strip()
                required = bool(opt.get("required"))
                values = opt.get("values") if isinstance(opt.get("values"), list) else []
                values_txt = ", ".join(f"`{str(v).strip()}`" for v in values if str(v).strip())
                req_txt = "obligatoire" if required else "facultatif"
                if key:
                    if values_txt:
                        lines.append(f"- `{key}` ({label}) [{req_txt}] : {values_txt}")
                    else:
                        lines.append(f"- `{key}` ({label}) [{req_txt}]")
        else:
            lines.append("- (none)")
        lines.append("")

        lines.append("## BOT_FORMAT")
        if bot_format:
            sales_mode = str(bot_format.get("sales_mode") or "").strip()
            if sales_mode:
                lines.append(f"- sales_mode: `{sales_mode}`")
            bot_allowed_units_raw = bot_format.get("allowed_units") if isinstance(bot_format.get("allowed_units"), list) else []
            bot_allowed_units: list[str] = []
            bot_aliases: Dict[str, list[str]] = {}
            for row in bot_allowed_units_raw:
                if isinstance(row, dict):
                    key = str(row.get("key") or "").strip()
                    aliases = row.get("aliases") if isinstance(row.get("aliases"), list) else []
                    clean_aliases = [str(a).strip().lower() for a in aliases if str(a).strip()]
                    if key:
                        bot_allowed_units.append(key)
                        bot_aliases[key] = clean_aliases
                else:
                    key = str(row or "").strip()
                    if key:
                        bot_allowed_units.append(key)
            if bot_allowed_units:
                lines.append(f"- allowed_units: {', '.join(sorted(set(bot_allowed_units)))}")
            min_order = bot_format.get("min_order") if isinstance(bot_format.get("min_order"), dict) else {}
            min_value = min_order.get("value")
            min_unit = str(min_order.get("unit") or "").strip()
            if min_value is not None or min_unit:
                lines.append(f"- min_order: value={min_value or 0}, unit={min_unit or '(none)'}")
            if required_options:
                lines.append("- required_options: present")
            specs = bot_format.get("specs") if isinstance(bot_format.get("specs"), list) else []
            if specs:
                lines.append("- specs:")
                for s in specs:
                    if not isinstance(s, dict):
                        continue
                    skey = str(s.get("key") or "").strip()
                    slabel = str(s.get("label") or skey or "").strip()
                    stype = str(s.get("type") or "text").strip()
                    required = bool(s.get("required"))
                    values = s.get("values") if isinstance(s.get("values"), list) else []
                    clean_values = [str(v).strip() for v in values if str(v).strip()]
                    val_txt = f" values={', '.join(f'`{v}`' for v in clean_values)}" if clean_values else ""
                    if skey:
                        lines.append(f"  - `{skey}` ({slabel}) type={stype} required={str(required).lower()}{val_txt}")
            rules = bot_format.get("validation_rules") if isinstance(bot_format.get("validation_rules"), dict) else {}
            if rules:
                lines.append("- validation_rules:")
                for rk, rv in rules.items():
                    if isinstance(rv, dict):
                        lines.append(f"  - {rk}: {json.dumps(rv, ensure_ascii=False)}")
                    else:
                        lines.append(f"  - {rk}: {rv}")
            hints = bot_format.get("prompt_hints")
            if isinstance(hints, list) and hints:
                hint_txt = ", ".join(f"`{str(h).strip()}`" for h in hints if str(h).strip())
                if hint_txt:
                    lines.append(f"- prompt_hints: {hint_txt}")
            if selling_formats:
                lines.append("- selling_formats: present")
        else:
            lines.append("- (none)")
        lines.append("")

        lines.append("## UNITS_PAR_PRODUIT")
        if vtree:
            fallback_format_lines = []
            if selling_formats:
                fallback_format_lines.append(f"- formats: {', '.join(str(f.get('canonical_id') or '').strip() for f in selling_formats if isinstance(f, dict) and str(f.get('canonical_id') or '').strip())}")
                for fmt in selling_formats:
                    if not isinstance(fmt, dict):
                        continue
                    cid = str(fmt.get("canonical_id") or "").strip()
                    fname = str(fmt.get("format_name") or "").strip()
                    if cid and fname:
                        fallback_format_lines.append(f"- {cid}: {fname}")
            elif format_catalog:
                fallback_format_lines.append(f"- formats: {', '.join(f['key'] for f in format_catalog if f.get('key'))}")
                for fmt in format_catalog:
                    if fmt.get("key") and fmt.get("label"):
                        fallback_format_lines.append(f"- {fmt['key']}: {fmt['label']}")
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
                    if units == ["piece"] and not piece_enabled and fallback_format_lines:
                        lines.extend(fallback_format_lines)
                    elif units:
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

                if not piece_enabled and fallback_format_lines:
                    lines.extend(fallback_format_lines)
                else:
                    lines.append("- (no units)")
                lines.append("")
        else:
            if not piece_enabled and selling_formats:
                lines.append(f"- formats: {', '.join(str(f.get('canonical_id') or '').strip() for f in selling_formats if isinstance(f, dict) and str(f.get('canonical_id') or '').strip())}")
                for fmt in selling_formats:
                    if not isinstance(fmt, dict):
                        continue
                    cid = str(fmt.get("canonical_id") or "").strip()
                    fname = str(fmt.get("format_name") or "").strip()
                    if cid and fname:
                        lines.append(f"- {cid}: {fname}")
            elif not piece_enabled and format_catalog:
                lines.append(f"- formats: {', '.join(f['key'] for f in format_catalog if f.get('key'))}")
                for fmt in format_catalog:
                    if fmt.get("key") and fmt.get("label"):
                        lines.append(f"- {fmt['key']}: {fmt['label']}")
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

                if pricing_mode:
                    lines.append(f"- pricing_mode: {pricing_mode}")
                if sales_target:
                    lines.append(f"- sales_target: {sales_target}")

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

        if description:
            lines.append("## DESCRIPTION (RAW)")
            lines.append(description)
            lines.append("")

        if important_note:
            lines.append("## IMPORTANT_NOTE (RAW)")
            lines.append(important_note)
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

    incoming_pid = str(payload.product_id or incoming_catalog.get("product_id") or "").strip()
    if incoming_pid:
        incoming_pid = incoming_pid.lower()
    if not incoming_pid:
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
        def _norm_kw(v: Any) -> str:
            try:
                import unicodedata as _ud

                t = str(v or "").strip().lower()
                t = _ud.normalize("NFKD", t)
                t = "".join([c for c in t if not _ud.combining(c)])
            except Exception:
                t = str(v or "").strip().lower()
            t = re.sub(r"[^a-z0-9\s-]+", " ", t)
            t = t.replace("-", " ")
            t = re.sub(r"\s+", " ", t).strip()
            return t

        keyword_products: list[Dict[str, Any]] = []
        for prod in out_products:
            if not isinstance(prod, dict):
                continue
            cat = prod.get("catalog_v2") if isinstance(prod.get("catalog_v2"), dict) else {}
            pid = str(prod.get("product_id") or cat.get("product_id") or "").strip()
            if pid:
                pid = pid.lower()
            pname = str(prod.get("product_name") or cat.get("product_name") or cat.get("name") or "").strip()
            if not pid or not pname:
                continue

            kws: set[str] = set()
            kws.add(_norm_kw(pname))
            kws.update([w for w in _norm_kw(pname).split() if len(w) >= 3])

            for f in ["category", "subcategory"]:
                vv = _norm_kw(cat.get(f) or "")
                if vv:
                    kws.add(vv)
                    kws.update([w for w in vv.split() if len(w) >= 3])

            ui = cat.get("ui_state") if isinstance(cat.get("ui_state"), dict) else {}
            variants = ui.get("variants") if isinstance(ui.get("variants"), list) else []
            for v in variants:
                vv = _norm_kw(v)
                if vv:
                    kws.add(vv)
                    kws.update([w for w in vv.split() if len(w) >= 3])

            vtree = cat.get("v") if isinstance(cat.get("v"), dict) else {}
            for vname in vtree.keys():
                vv = _norm_kw(vname)
                if vv:
                    kws.add(vv)
                    kws.update([w for w in vv.split() if len(w) >= 3])

            kw_list = sorted({k for k in kws if k and len(k) >= 3}, key=lambda x: (len(x), x))
            keyword_products.append({"product_id": pid, "product_name": pname, "keywords": kw_list})

        kw_path = os.path.join(base_dir, f"{safe_id}.keywords.json")
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=base_dir, prefix=f"{safe_id}.kw.", suffix=".tmp") as fkw:
            tmp_kw = fkw.name
            json.dump(
                {
                    "company_id": cid,
                    "updated_at": payload.updated_at,
                    "version": payload.version,
                    "products": keyword_products,
                    "written_at": time.time(),
                },
                fkw,
                ensure_ascii=False,
            )
        os.replace(tmp_kw, kw_path)
    except Exception:
        try:
            if tmp_kw and os.path.exists(tmp_kw):
                os.unlink(tmp_kw)
        except Exception:
            pass

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


async def _dispatch_to_n8n(company_id: str, action: str, catalog: Any):
    """
    Envoie une notification à n8n pour synchronisation (Parallélisation).
    URL: https://n8n.zetaapp.xyz/webhook-test/onboarding-botlive
    """
    webhook_url = "https://n8n.zetaapp.xyz/webhook-test/onboarding-botlive"
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            # On respecte le format attendu par n8n (body.catalogs)
            payload = {
                "company_id": company_id,
                "action": action,
                "catalogs": [catalog] if isinstance(catalog, dict) else (catalog or []),
                "timestamp": time.time()
            }
            
            logger.info(f"📤 [N8N] Tentative d'envoi | company={company_id} | action={action}")
            
            # Debug ciblés sur les champs critiques
            if isinstance(catalog, dict):
                p_name = catalog.get('name') or catalog.get('product_name')
                img_count = len(catalog.get('imageUrls') or [])
                logger.info(f"🔍 [N8N] Payload Debug: name='{p_name}', images={img_count}")

            response = await client.post(webhook_url, json=payload, timeout=10.0)
            
            if response.status_code >= 400:
                logger.error(f"❌ [N8N] Erreur HTTP {response.status_code}")
            else:
                logger.info(f"🚀 [N8N] Dispatch réussi | status={response.status_code}")
                
    except Exception as e:
        logger.error(f"❌ [N8N] Erreur dispatch: {str(e)}")


@router.post("/delete", response_model=CatalogV2UpsertResponse)
async def delete_company_product_v2(request: Request, company_id: str, row_id: str) -> CatalogV2UpsertResponse:
    """Soft delete d'un produit : Supabase (is_active=False) + Local JSON removal + n8n."""
    _check_internal_key(request)
    
    cid = str(company_id).strip()
    rid = str(row_id).strip()
    
    try:
        from database.supabase_client import get_supabase_client
        client = get_supabase_client()
        
        # 1. Supabase Soft Delete
        res = await asyncio.to_thread(
            client.table("company_catalogs_v2")
            .update({"is_active": False, "updated_at": datetime.now().isoformat()})
            .eq("id", rid)
            .execute
        )
        
        # 2. Local JSON update (Removal)
        # On lit le fichier, on filtre, on réécrit
        base_dir = os.getenv("CATALOG_V2_LOCAL_DIR") or "/data/catalogs"
        safe_id = re.sub(r"[^a-zA-Z0-9\-_]", "_", cid)
        final_path = os.path.join(base_dir, f"{safe_id}.json")
        
        deleted_catalog = {}
        if os.path.exists(final_path):
            with open(final_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            products = data.get("catalog", {}).get("products", [])
            # On cherche le produit pour n8n avant de le supprimer
            for p in products:
                if str(p.get("row_id") or "").strip() == rid:
                    deleted_catalog = p.get("catalog_v2") or {}
                    break
            
            new_products = [p for p in products if str(p.get("row_id") or "").strip() != rid]
            data["catalog"]["products"] = new_products
            data["synced_at"] = time.time()
            
            with open(final_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        
        # 3. Dispatch n8n
        if deleted_catalog:
            await _dispatch_to_n8n(cid, "delete", deleted_catalog)
            
        return CatalogV2UpsertResponse(
            success=True,
            company_id=cid,
            id=rid,
            version=0,
            updated_at=datetime.now().isoformat(),
            timestamp=time.time()
        )
    except Exception as e:
        logger.error(f"[CATALOG_V2] Delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/destroy", response_model=CatalogV2UpsertResponse)
async def destroy_company_product_v2(request: Request, company_id: str, row_id: str) -> CatalogV2UpsertResponse:
    """Suppression définitive d'un produit (Hard Delete)."""
    _check_internal_key(request)
    cid = str(company_id).strip()
    rid = str(row_id).strip()
    try:
        from database.supabase_client import get_supabase_client
        client = get_supabase_client()
        # 1. Supabase Hard Delete
        client.table("company_catalogs_v2").delete().eq("id", rid).execute()
        # 2. Local JSON update and Dispatch (simplified)
        await _dispatch_to_n8n(cid, "destroy", {"id": rid})
        return CatalogV2UpsertResponse(success=True, company_id=cid, id=rid, version=0, updated_at=datetime.now().isoformat(), timestamp=time.time())
    except Exception as e:
        logger.error(f"[CATALOG_V2] Destroy error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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

        # 3. Sync Local JSON & Get Full Catalog for n8n
        full_catalog_data = payload.catalog
        try:
            sync_req = CatalogV2SyncLocalRequest(
                company_id=company_id,
                catalog=payload.catalog,
                product_id=str(payload.product_id or payload.catalog.get("product_id") or ""),
                updated_at=updated_at or datetime.now().isoformat(),
                version=version
            )
            final_path = _write_local_catalog(company_id, sync_req)

            if os.path.exists(final_path):
                with open(final_path, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                    full_catalog_data = cached_data.get("catalog") or cached_data
        except Exception as e:
            logger.error(f"[CATALOG_V2] Sync local error: {e}")

        try:
            from core.company_catalog_v2_loader import invalidate_company_catalog_v2_cache
            invalidate_company_catalog_v2_cache(company_id)
        except Exception:
            pass

        # 4. Dispatch n8n (Full Catalog)
        try:
            await _dispatch_to_n8n(company_id, "upsert", full_catalog_data)
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
            pid_top = str(getattr(payload, "product_id", "") or "").strip()
            pid_in = str(payload.catalog.get("product_id") or "").strip()
            if pid_top and not pid_in:
                payload.catalog["product_id"] = pid_top

            tech_top = str(getattr(payload, "technical_specs", "") or "").strip()
            sales_top = str(getattr(payload, "sales_constraints", "") or "").strip()
            desc_top = str(getattr(payload, "description", "") or "").strip()
            note_top = str(getattr(payload, "important_note", "") or "").strip()

            if tech_top:
                payload.catalog["technical_specs"] = tech_top
            if sales_top:
                payload.catalog["sales_constraints"] = sales_top
            if desc_top and not str(payload.catalog.get("description") or "").strip():
                payload.catalog["description"] = desc_top
            if note_top and not str(payload.catalog.get("important_note") or "").strip():
                payload.catalog["important_note"] = note_top
    except Exception:
        pass

    final_path = _write_local_catalog(company_id, payload)  # type: ignore[arg-type]

    catalogue_block = _build_catalogue_block_from_catalog_v2(payload.catalog)
    if not catalogue_block or not catalogue_block.strip():
        raise HTTPException(status_code=400, detail="catalogue_block vide")

    def _upsert_product_index_block(existing_prompt: str, product_name: str, product_id: str = "", variant_names: list[str] | None = None) -> str:
        """Upsert a product entry (with optional variants) into the [[PRODUCT_INDEX]] block."""
        p = str(existing_prompt or "")
        pn = str(product_name or "").strip()
        if not pn:
            return p

        pid = str(product_id or "").strip()
        if not pid:
            pid = _product_id_hash(pn)

        # Nouveau format Premium : - Nom Produit | ID: product_id | Variantes: [V1 | V2]
        variants_str = " | ".join(variant_names) if variant_names else "NULL"
        entry_line = f"- {pn} | ID: {pid} | Variantes: [{variants_str}]"

        start_tag = "[[PRODUCT_INDEX_START]]"
        end_tag = "[[PRODUCT_INDEX_END]]"
        si = p.find(start_tag)
        ei = p.find(end_tag)
        if si != -1 and ei != -1 and ei > si:
            block_start = si + len(start_tag)
            existing_block = p[block_start:ei]
            raw_lines = [ln.strip() for ln in str(existing_block or "").splitlines()]

            # Parse existing entries: each product is a "- NAME [ID: ...]" line
            # optionally followed by "  - VARIANTS: ..." sub-line
            items: list[dict] = []  # {name, pid, line, variants_line}
            seen_pids: set[str] = set()
            i = 0
            while i < len(raw_lines):
                ln = raw_lines[i]
                if not ln:
                    i += 1
                    continue
                # Skip variant sub-lines (they belong to previous product)
                if ln.startswith("- VARIANTS:") or ln.startswith("-   VARIANTS:"):
                    i += 1
                    continue
                # Nouveau parsing pipe-separated
                m_pid = re.search(r"ID:\s*(prod_[a-z0-9_]{6,64})", n, flags=re.IGNORECASE)
                existing_pid = str(m_pid.group(1)).lower() if m_pid else ""
                
                # Extraction du nom (tout ce qui est avant le premier '|')
                name_only = n.split("|")[0].replace("-", "", 1).strip()
                
                # Extraction des variantes
                m_vars = re.search(r"Variantes:\s*\[(.*?)\]", n, flags=re.IGNORECASE)
                existing_variants_str = m_vars.group(1) if m_vars else "NULL"
                
                if existing_pid:
                    if existing_pid in seen_pids:
                        i += 1
                        continue
                    seen_pids.add(existing_pid)
                items.append({
                    "name": name_only, 
                    "pid": existing_pid, 
                    "variants_str": existing_variants_str
                })
                i += 1

            if pid:
                if pid not in seen_pids:
                    items.append({"name": pn, "pid": pid, "variants_str": variants_str})
                    seen_pids.add(pid)
                else:
                    # Update existing entry (same pid) with new name/variants
                    for item in items:
                        if item["pid"] == pid:
                            item["name"] = pn
                            item["variants_str"] = variants_str
                            break
            else:
                if pn.strip().lower() not in {it["name"].strip().lower() for it in items if it["name"]}:
                    items.append({"name": pn, "pid": "", "variants_str": variants_str})

            items_sorted = sorted(items, key=lambda it: (it["name"] or "").lower())
            block_lines = []
            for idx, it in enumerate(items_sorted, 1):
                # Format final numéroté Premium
                line = f"{idx}. {it['name']} | ID: {it['pid']} | Variantes: [{it['variants_str']}]"
                block_lines.append(line)
            
            new_block = "\n" + "\n".join(block_lines) + "\n"
            return p[:block_start] + new_block + p[ei:]

        # No existing block → create one
        block_lines = [start_tag, entry_line]
        if variants_line:
            block_lines.append(variants_line)
        block_lines.extend([end_tag, ""])
        insertion = "\n".join(block_lines)
        return insertion + p

    def _inject_catalogue_block(prompt: str, block: str) -> str:
        p = str(prompt or "")
        if not p.strip():
            return p
        try:
            import re as _re
            start_tag = "[CATALOGUE_START]"
            end_tag = "[CATALOGUE_END]"
            pat = r"\[CATALOGUE_START\](.*?)\[CATALOGUE_END\]"
            new_content = f"{start_tag}\n{block.strip()}\n{end_tag}"
            
            if _re.search(pat, p, flags=_re.IGNORECASE | _re.DOTALL):
                return _re.sub(pat, new_content, p, flags=_re.IGNORECASE | _re.DOTALL)
            else:
                return p + "\n\n" + new_content
        except Exception:
            return p

    def _clear_catalogue_markers(existing_prompt: str) -> str:
        # Keep this for backward compatibility if needed, but we prefer _inject
        p = str(existing_prompt or "")
        try:
            import re as _re
            pat = r"\[CATALOGUE_START\](.*?)\[CATALOGUE_END\]"
            replacement = "[CATALOGUE_START]\n\n[CATALOGUE_END]"
            return _re.sub(pat, replacement, p, flags=_re.IGNORECASE | _re.DOTALL)
        except Exception:
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
            pass

        # 2. REDIS: Store Product Index dynamically (Scalable approach)
        try:
            import redis
            from config import REDIS_URL
            r = redis.from_url(REDIS_URL)
            
            # On prépare la ligne d'index
            _vtree = payload.catalog.get("v") if isinstance(payload.catalog.get("v"), dict) else {}
            _variant_names = [str(k).strip() for k in _vtree.keys() if str(k).strip()] if isinstance(_vtree, dict) else []
            v_str = " | ".join(_variant_names) if _variant_names else "NULL"
            p_id = str(payload.product_id or payload.catalog.get("product_id") or "")
            p_name = str(payload.catalog.get("product_name") or payload.catalog.get("name") or "")
            
            index_line = f"- {p_name} | ID: {p_id} | Variantes: [{v_str}]"
            
            # On stocke dans un Hash Redis pour accumulation automatique
            r.hset(f"zeta:product_index:{company_id}", p_id, index_line)
            # TTL de 30 jours pour la persistance
            r.expire(f"zeta:product_index:{company_id}", 30 * 24 * 3600)
            
            logger.info("[CATALOG_V2][REDIS] ✅ Product Index updated for %s | %s", company_id, p_id)
        except Exception as e:
            logger.error(f"[CATALOG_V2][REDIS] ❌ Error: {e}")

        # 3. SUPABASE: We keep it clean (No injection in prompt anymore)
        updated_prompt = _clear_catalogue_markers(existing_prompt)
        
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

        # Dispatch n8n
        try:
            await _dispatch_to_n8n(company_id, "sync_local_upsert", payload.catalog)
        except Exception:
            pass

        return CatalogV2SyncLocalAndUpsertPromptResponse(
            success=True,
            company_id=company_id,
            path=final_path,
            prompt_chars=len(str(updated_prompt)),
            catalogue_chars=len(str(catalogue_block)),
            debug=None,
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


@router.delete("/row/{row_id}")
async def soft_delete_product_v2(request: Request, row_id: str):
    _check_internal_key(request)
    try:
        from database.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # 1. Récupérer le produit pour n8n avant de le désactiver
        resp_get = supabase.table("company_catalogs_v2").select("*").eq("id", row_id).single().execute()
        product_data = getattr(resp_get, "data", {})
        cid = product_data.get("company_id")
        
        # 2. Update status
        now_iso = datetime.now().isoformat()
        supabase.table("company_catalogs_v2").update({
            "is_active": False,
            "status": "deleted",
            "deleted_at": now_iso,
            "updated_at": now_iso
        }).eq("id", row_id).execute()
        
        # 3. Dispatch n8n
        if cid:
            await _dispatch_to_n8n(cid, "delete", product_data.get("catalog") or {})
            
        return {"success": True, "message": "Produit déplacé dans la corbeille"}
    except Exception as e:
        logger.error(f"[CATALOG_V2] Soft delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/row/{row_id}/restore")
async def restore_product_v2(request: Request, row_id: str):
    _check_internal_key(request)
    try:
        from database.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # 1. Update status
        now_iso = datetime.now().isoformat()
        resp = supabase.table("company_catalogs_v2").update({
            "is_active": True,
            "status": "active",
            "deleted_at": None,
            "updated_at": now_iso
        }).eq("id", row_id).execute()
        
        product_data = (getattr(resp, "data", []) or [{}])[0]
        cid = product_data.get("company_id")
        
        # 2. Dispatch n8n
        if cid:
            await _dispatch_to_n8n(cid, "restore", product_data.get("catalog") or {})
            
        return {"success": True, "message": "Produit restauré"}
    except Exception as e:
        logger.error(f"[CATALOG_V2] Restore error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/row/{row_id}/hard")
async def hard_delete_product_v2(request: Request, row_id: str):
    _check_internal_key(request)
    try:
        from database.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # 1. Get cid for cache invalidation
        resp_get = supabase.table("company_catalogs_v2").select("company_id").eq("id", row_id).single().execute()
        cid = getattr(resp_get, "data", {}).get("company_id")
        
        # 2. Delete
        supabase.table("company_catalogs_v2").delete().eq("id", row_id).execute()
        
        return {"success": True, "message": "Produit supprimé définitivement"}
    except Exception as e:
        logger.error(f"[CATALOG_V2] Hard delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
