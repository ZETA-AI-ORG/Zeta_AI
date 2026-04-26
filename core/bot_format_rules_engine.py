from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple


def _xml_escape(value: Any) -> str:
    s = str(value or "")
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def load_bot_format(catalog: Dict[str, Any]) -> Dict[str, Any]:
    bot_format = catalog.get("bot_format")
    if isinstance(bot_format, dict):
        return bot_format
    ui_state = catalog.get("ui_state")
    if isinstance(ui_state, dict) and isinstance(ui_state.get("bot_format"), dict):
        return ui_state.get("bot_format") or {}
    return {}


def extract_allowed_units(bot_format: Dict[str, Any], fallback_allowed_units: Optional[List[str]] = None) -> List[str]:
    allowed_units: List[str] = []
    raw_allowed = bot_format.get("allowed_units") if isinstance(bot_format.get("allowed_units"), list) else []
    for row in raw_allowed:
        if isinstance(row, dict):
            key = str(row.get("key") or "").strip()
            if key:
                allowed_units.append(key)
        else:
            key = str(row or "").strip()
            if key:
                allowed_units.append(key)

    if not allowed_units:
        selling_formats = bot_format.get("selling_formats") if isinstance(bot_format.get("selling_formats"), list) else []
        for row in selling_formats:
            if not isinstance(row, dict):
                continue
            key = str(row.get("canonical_id") or "").strip()
            if key:
                allowed_units.append(key)

    if not allowed_units and isinstance(fallback_allowed_units, list):
        allowed_units.extend(str(u).strip() for u in fallback_allowed_units if str(u).strip())

    return sorted(set([u for u in allowed_units if u]))


def extract_unit_aliases(bot_format: Dict[str, Any]) -> Dict[str, List[str]]:
    aliases: Dict[str, List[str]] = {}
    raw_allowed = bot_format.get("allowed_units") if isinstance(bot_format.get("allowed_units"), list) else []
    for row in raw_allowed:
        if not isinstance(row, dict):
            continue
        key = str(row.get("key") or "").strip()
        vals = row.get("aliases") if isinstance(row.get("aliases"), list) else []
        clean = [str(v).strip().lower() for v in vals if str(v).strip()]
        if key and clean:
            aliases[key] = sorted(set(clean))

    legacy = bot_format.get("unit_aliases") if isinstance(bot_format.get("unit_aliases"), dict) else {}
    for key, vals in legacy.items():
        canon = str(key or "").strip()
        items = vals if isinstance(vals, list) else []
        clean = [str(v).strip().lower() for v in items if str(v).strip()]
        if canon and clean:
            merged = set(aliases.get(canon, []))
            merged.update(clean)
            aliases[canon] = sorted(merged)
    return aliases


def apply_explicit_unit_alias(unit_raw: str, *, bot_format: Dict[str, Any], allowed_units: Optional[List[str]] = None) -> str:
    unit_val = str(unit_raw or "").strip()
    if not unit_val:
        return ""

    normalized = unit_val.lower()
    aliases = extract_unit_aliases(bot_format)
    allowed = set(extract_allowed_units(bot_format, allowed_units))
    for canon, values in aliases.items():
        if allowed and canon not in allowed:
            continue
        if normalized in {str(v).strip().lower() for v in values if str(v).strip()}:
            return canon
    return unit_val


def _extract_required_options(bot_format: Dict[str, Any], catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
    required_options = bot_format.get("required_options") if isinstance(bot_format.get("required_options"), list) else []
    clean: List[Dict[str, Any]] = []
    for row in required_options:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or row.get("label") or row.get("key") or "").strip()
        values = row.get("values") if isinstance(row.get("values"), list) else []
        clean_values = [str(v).strip() for v in values if str(v).strip()]
        if name:
            clean.append(
                {
                    "name": name,
                    "key": str(row.get("key") or "").strip(),
                    "is_mandatory": bool(row.get("is_mandatory")),
                    "values": clean_values,
                }
            )
    if clean:
        return clean

    ui_state = catalog.get("ui_state") if isinstance(catalog.get("ui_state"), dict) else {}
    ui_product_options = ui_state.get("productOptions") if isinstance(ui_state.get("productOptions"), list) else []
    ui_fallback: List[Dict[str, Any]] = []
    for row in ui_product_options:
        if not isinstance(row, dict):
            continue
        values = row.get("values") if isinstance(row.get("values"), list) else []
        clean_values = [str(v).strip() for v in values if str(v).strip()]
        name = str(row.get("label") or row.get("name") or row.get("key") or "").strip()
        if name and clean_values:
            ui_fallback.append(
                {
                    "name": name,
                    "key": str(row.get("key") or "").strip(),
                    "is_mandatory": bool(row.get("required")),
                    "values": clean_values,
                }
            )
    if ui_fallback:
        return ui_fallback

    specs = bot_format.get("specs") if isinstance(bot_format.get("specs"), list) else []
    fallback: List[Dict[str, Any]] = []
    for row in specs:
        if not isinstance(row, dict):
            continue
        values = row.get("values") if isinstance(row.get("values"), list) else []
        if not values:
            values = row.get("allowed_values") if isinstance(row.get("allowed_values"), list) else []
        clean_values = [str(v).strip() for v in values if str(v).strip()]
        if clean_values:
            fallback.append(
                {
                    "name": str(row.get("label") or row.get("key") or "").strip(),
                    "key": str(row.get("key") or "").strip(),
                    "is_mandatory": bool(row.get("required", True)),
                    "values": clean_values,
                }
            )
    return fallback


def _surface_normalize(value: Any) -> str:
    raw = unicodedata.normalize("NFKD", str(value or ""))
    ascii_only = "".join(ch for ch in raw if not unicodedata.combining(ch))
    lowered = ascii_only.lower().strip()
    return re.sub(r"[^a-z0-9]+", "", lowered)


def _extract_option_values(catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
    bot_format = load_bot_format(catalog)
    options = _extract_required_options(bot_format, catalog)
    out: List[Dict[str, Any]] = []
    for opt in options:
        values = [str(v).strip() for v in (opt.get("values") or []) if str(v).strip()]
        if not values:
            continue
        out.append(
            {
                "key": str(opt.get("key") or "").strip(),
                "name": str(opt.get("name") or "").strip(),
                "is_mandatory": bool(opt.get("is_mandatory")),
                "values": values,
            }
        )
    return out


def _value_label(candidate: str) -> str:
    text = str(candidate or "").strip()
    if "(" in text:
        text = text.split("(", 1)[0].strip()
    return text


def _extract_numeric_probe(raw_value: str) -> Optional[float]:
    match = re.search(r"(\d+(?:[\.,]\d+)?)", str(raw_value or ""))
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", "."))
    except Exception:
        return None


def _extract_candidate_range(candidate: str) -> Optional[Tuple[float, float]]:
    numbers = re.findall(r"(\d+(?:[\.,]\d+)?)", str(candidate or ""))
    if len(numbers) < 2:
        return None
    try:
        low = float(numbers[0].replace(",", "."))
        high = float(numbers[1].replace(",", "."))
    except Exception:
        return None
    if low > high:
        low, high = high, low
    return low, high


def canonicalize_option_value(raw_value: Any, allowed_values: List[str]) -> Dict[str, Any]:
    raw = str(raw_value or "").strip()
    values = [str(v).strip() for v in (allowed_values or []) if str(v).strip()]
    result = {
        "value": "",
        "status": "missing" if not raw else "not_found",
        "attempt_count": 1 if raw else 0,
        "success_count": 0,
        "ambiguous_count": 0,
    }
    if not raw or not values:
        return result

    for candidate in values:
        if raw == candidate:
            result.update({"value": candidate, "status": "exact", "success_count": 1})
            return result

    raw_norm = _surface_normalize(raw)
    normalized_hits = [candidate for candidate in values if _surface_normalize(candidate) == raw_norm]
    if len(normalized_hits) == 1:
        result.update({"value": normalized_hits[0], "status": "surface", "success_count": 1})
        return result
    if len(normalized_hits) > 1:
        result.update({"status": "ambiguous_surface", "ambiguous_count": 1})
        return result

    contains_hits = [candidate for candidate in values if _surface_normalize(candidate) in raw_norm or raw_norm in _surface_normalize(candidate)]
    if len(contains_hits) == 1:
        result.update({"value": contains_hits[0], "status": "contains", "success_count": 1})
        return result
    if len(contains_hits) > 1:
        result.update({"status": "ambiguous_contains", "ambiguous_count": 1})
        return result

    label_hits = []
    for candidate in values:
        label = _surface_normalize(_value_label(candidate))
        if label and (raw_norm == label or raw_norm.startswith(label) or label.startswith(raw_norm)):
            label_hits.append(candidate)
    if len(label_hits) == 1:
        result.update({"value": label_hits[0], "status": "label", "success_count": 1})
        return result
    if len(label_hits) > 1:
        result.update({"status": "ambiguous_label", "ambiguous_count": 1})
        return result

    probe = _extract_numeric_probe(raw)
    if probe is not None:
        range_hits = []
        for candidate in values:
            parsed_range = _extract_candidate_range(candidate)
            if not parsed_range:
                continue
            low, high = parsed_range
            if low <= probe <= high:
                range_hits.append(candidate)
        if len(range_hits) == 1:
            result.update({"value": range_hits[0], "status": "range", "success_count": 1})
            return result
        if len(range_hits) > 1:
            result.update({"status": "ambiguous_range", "ambiguous_count": 1})
            return result

    return result


def resolve_selected_options(
    catalog: Dict[str, Any],
    *,
    raw_specs: Optional[str],
    selected_options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    options = _extract_option_values(catalog)
    provided = selected_options if isinstance(selected_options, dict) else {}
    specs_text = str(raw_specs or "").strip()
    resolved: Dict[str, str] = {}
    metrics = {
        "canonicalization_attempt_count": 0,
        "canonicalization_success_count": 0,
        "canonicalization_ambiguous_count": 0,
    }

    for opt in options:
        key = str(opt.get("key") or opt.get("name") or "").strip()
        raw_value = provided.get(key)
        if raw_value is None and str(opt.get("name") or "").strip():
            raw_value = provided.get(str(opt.get("name") or "").strip())
        raw_probe = raw_value if raw_value is not None else specs_text
        result = canonicalize_option_value(raw_probe, opt.get("values") or [])
        metrics["canonicalization_attempt_count"] += int(result.get("attempt_count") or 0)
        metrics["canonicalization_success_count"] += int(result.get("success_count") or 0)
        metrics["canonicalization_ambiguous_count"] += int(result.get("ambiguous_count") or 0)
        value = str(result.get("value") or "").strip()
        if key and value:
            resolved[key] = value

    return {"selected_options": resolved, "metrics": metrics, "options": options}


def build_selected_options_display(catalog: Dict[str, Any], selected_options: Optional[Dict[str, Any]]) -> str:
    selected = selected_options if isinstance(selected_options, dict) else {}
    if not selected:
        return ""
    ordered_values: List[str] = []
    for opt in _extract_option_values(catalog):
        key = str(opt.get("key") or opt.get("name") or "").strip()
        value = str(selected.get(key) or "").strip()
        if value:
            ordered_values.append(value)
    for _, value in selected.items():
        value_s = str(value or "").strip()
        if value_s and value_s not in ordered_values:
            ordered_values.append(value_s)
    return " / ".join(ordered_values)


def canonicalize_item_options(catalog: Dict[str, Any], item: Dict[str, Any]) -> Dict[str, Any]:
    item_dict = dict(item or {})
    resolution = resolve_selected_options(
        catalog,
        raw_specs=item_dict.get("specs") or item_dict.get("spec"),
        selected_options=item_dict.get("selected_options") if isinstance(item_dict.get("selected_options"), dict) else None,
    )
    selected = resolution.get("selected_options") if isinstance(resolution.get("selected_options"), dict) else {}
    display = build_selected_options_display(catalog, selected)
    if selected:
        item_dict["selected_options"] = selected
    if display:
        item_dict["spec"] = display
        item_dict["specs"] = display
    item_dict["_canonicalization_meta"] = resolution.get("metrics") if isinstance(resolution.get("metrics"), dict) else {}
    return item_dict


def _extract_min_order_by_unit(bot_format: Dict[str, Any]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    rules = bot_format.get("validation_rules") if isinstance(bot_format.get("validation_rules"), dict) else {}
    raw = rules.get("min_order_by_unit") if isinstance(rules.get("min_order_by_unit"), dict) else {}
    for key, value in raw.items():
        canon = str(key or "").strip()
        try:
            parsed = int(value)
        except Exception:
            parsed = 0
        if canon and parsed > 0:
            out[canon] = parsed

    if not out:
        min_order = bot_format.get("min_order") if isinstance(bot_format.get("min_order"), dict) else {}
        unit = str(min_order.get("unit") or "").strip()
        try:
            value = int(min_order.get("value")) if min_order.get("value") is not None else 0
        except Exception:
            value = 0
        if unit and value > 0:
            out[unit] = value
    return out


def is_price_lookup_ready(
    catalog: Dict[str, Any],
    *,
    unit: Optional[str],
    specs: Optional[str],
    selected_options: Optional[Dict[str, Any]] = None,
    allowed_units: Optional[List[str]] = None,
) -> Dict[str, Any]:
    bot_format = load_bot_format(catalog)
    if not bot_format:
        return {"ready": bool(str(unit or "").strip()), "missing_required_options": [], "allowed_units": []}

    unit_val = apply_explicit_unit_alias(
        str(unit or "").strip(),
        bot_format=bot_format,
        allowed_units=allowed_units,
    )
    specs_val = str(specs or "").strip()
    effective_allowed_units = extract_allowed_units(bot_format, allowed_units)
    missing_required: List[Dict[str, Any]] = []

    if not unit_val:
        return {"ready": False, "missing_required_options": missing_required, "allowed_units": effective_allowed_units}

    if effective_allowed_units and unit_val not in effective_allowed_units:
        return {"ready": False, "missing_required_options": missing_required, "allowed_units": effective_allowed_units}

    required_options = _extract_required_options(bot_format, catalog)
    resolution = resolve_selected_options(catalog, raw_specs=specs_val, selected_options=selected_options)
    resolved_selected = resolution.get("selected_options") if isinstance(resolution.get("selected_options"), dict) else {}
    for opt in required_options:
        if not bool(opt.get("is_mandatory")):
            continue
        values = [str(v).strip() for v in (opt.get("values") or []) if str(v).strip()]
        opt_key = str(opt.get("key") or opt.get("name") or "").strip()
        if not str(resolved_selected.get(opt_key) or "").strip():
            missing_required.append({"name": str(opt.get("name") or "").strip(), "values": values})

    return {
        "ready": not missing_required,
        "missing_required_options": missing_required,
        "allowed_units": effective_allowed_units,
        "selected_options": resolved_selected,
        "canonicalization_metrics": resolution.get("metrics") if isinstance(resolution.get("metrics"), dict) else {},
    }


def validate_cart_item(
    catalog: Dict[str, Any],
    item: Dict[str, Any],
    *,
    allowed_units: Optional[List[str]] = None,
    strict_bot_format: bool = True,
) -> Optional[Dict[str, Any]]:
    bot_format = load_bot_format(catalog)
    if not bot_format:
        return None

    item_dict = canonicalize_item_options(catalog, item)
    item_dict["unit"] = apply_explicit_unit_alias(
        str(item_dict.get("unit") or "").strip(),
        bot_format=bot_format,
        allowed_units=allowed_units,
    )

    qty_val = item_dict.get("qty")
    unit_val = str(item_dict.get("unit") or "").strip()
    specs_val = str(item_dict.get("specs") or item_dict.get("spec") or "").strip()
    resolved_selected = item_dict.get("selected_options") if isinstance(item_dict.get("selected_options"), dict) else {}
    effective_allowed_units = extract_allowed_units(bot_format, allowed_units)
    rules = bot_format.get("validation_rules") if isinstance(bot_format.get("validation_rules"), dict) else {}

    if qty_val is None:
        if not unit_val and not specs_val:
            return None
        return {
            "code": "qty_missing",
            "expected": {"qty": "integer>0"},
            "message": "Quantité manquante. Tu dois demander une quantité valide au client.",
            "item": item_dict,
        }
    if not isinstance(qty_val, int) or qty_val <= 0:
        return {
            "code": "qty_invalid",
            "expected": {"qty": "integer>0"},
            "message": f"Quantité {qty_val} refusée. Demande une quantité entière valide au client.",
            "item": item_dict,
        }

    block_if_unit_not_allowed = bool(rules.get("block_if_unit_not_allowed"))
    if strict_bot_format and block_if_unit_not_allowed and effective_allowed_units and unit_val:
        if unit_val not in effective_allowed_units:
            return {
                "code": "unit_not_allowed",
                "expected": {"allowed_units": effective_allowed_units},
                "message": f'Unité "{unit_val}" interdite. Les seules unités autorisées sont {", ".join(effective_allowed_units)}. Demande au client de choisir parmi les formats autorisés.',
                "item": item_dict,
            }

    required_options = _extract_required_options(bot_format, catalog)
    for opt in required_options:
        if not bool(opt.get("is_mandatory")):
            continue
        values = [str(v).strip() for v in (opt.get("values") or []) if str(v).strip()]
        opt_key = str(opt.get("key") or opt.get("name") or "").strip()
        resolved_value = str(resolved_selected.get(opt_key) or "").strip()
        if not resolved_value:
            return {
                "code": "missing_required_option",
                "expected": {"name": opt.get("name"), "values": values},
                "message": f'Option manquante. Tu dois IMPERATIVEMENT demander l\'option {opt.get("name")} au client parmi cette liste : {", ".join(values)}.',
                "item": item_dict,
            }
        if values and resolved_value not in values:
            return {
                "code": "option_value_not_allowed",
                "expected": {"name": opt.get("name"), "values": values},
                "message": f'Valeur refusée pour {opt.get("name")}. Les valeurs autorisées sont : {", ".join(values)}.',
                "item": item_dict,
            }

    block_if_below_min_order = bool(rules.get("block_if_below_min_order"))
    min_by_unit = _extract_min_order_by_unit(bot_format)
    if strict_bot_format and block_if_below_min_order and unit_val and unit_val in min_by_unit:
        min_qty = int(min_by_unit[unit_val])
        if qty_val < min_qty:
            return {
                "code": "below_min_order",
                "expected": {"unit": unit_val, "min_qty": min_qty},
                "message": f"Quantité {qty_val} refusée. La commande minimum pour {unit_val} est de {min_qty}. Recadre le client.",
                "item": item_dict,
            }

    return None


def validate_cart_intent(
    catalog: Dict[str, Any],
    items: List[Dict[str, Any]],
    *,
    allowed_units: Optional[List[str]] = None,
    strict_bot_format: bool = True,
) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "ok": False,
        "confirmed": [],
        "invalid": [],
        "unconfirmed": [],
        "validation_errors_xml": "",
        "canonicalization_metrics": {
            "canonicalization_attempt_count": 0,
            "canonicalization_success_count": 0,
            "canonicalization_ambiguous_count": 0,
        },
    }

    for item in items or []:
        if not isinstance(item, dict):
            out["invalid"].append(
                {
                    "item": item,
                    "code": "invalid_item",
                    "expected": {"item": "dict"},
                    "message": "Item invalide reçu par le validateur.",
                }
            )
            continue

        canonical_item = canonicalize_item_options(catalog, item)
        rejection = validate_cart_item(
            catalog,
            canonical_item,
            allowed_units=allowed_units,
            strict_bot_format=strict_bot_format,
        )
        canonical_metrics = canonical_item.get("_canonicalization_meta") if isinstance(canonical_item.get("_canonicalization_meta"), dict) else {}
        for metric_name in ("canonicalization_attempt_count", "canonicalization_success_count", "canonicalization_ambiguous_count"):
            out["canonicalization_metrics"][metric_name] = int(out["canonicalization_metrics"].get(metric_name) or 0) + int(canonical_metrics.get(metric_name) or 0)
        if rejection:
            out["invalid"].append(rejection)
            continue
        out["confirmed"].append(canonical_item)

    if out["invalid"]:
        first = out["invalid"][0]
        item = first.get("item") if isinstance(first, dict) else {}
        expected = first.get("expected") if isinstance(first, dict) else {}
        allowed = expected.get("allowed_units") if isinstance(expected, dict) else []
        if isinstance(allowed, list):
            allowed_txt = ", ".join(str(x).strip() for x in allowed if str(x).strip())
        else:
            allowed_txt = ""
        out["validation_errors_xml"] = (
            "<validation_errors>\n"
            "  <PANIER>\n"
            f"    <code>{_xml_escape(first.get('code') or '')}</code>\n"
            f"    <unit_received>{_xml_escape((item or {}).get('unit') or '')}</unit_received>\n"
            f"    <qty_received>{_xml_escape((item or {}).get('qty') or '')}</qty_received>\n"
            f"    <option_name>{_xml_escape(expected.get('name') if isinstance(expected, dict) else '')}</option_name>\n"
            f"    <allowed_units>{_xml_escape(allowed_txt)}</allowed_units>\n"
            f"    <allowed_values>{_xml_escape(', '.join(expected.get('values') or []) if isinstance(expected, dict) and isinstance(expected.get('values'), list) else '')}</allowed_values>\n"
            f"    <message>{_xml_escape(first.get('message') or '')}</message>\n"
            "  </PANIER>\n"
            "</validation_errors>"
        )
        return out

    out["ok"] = True
    return out
