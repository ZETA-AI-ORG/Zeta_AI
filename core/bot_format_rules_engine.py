from __future__ import annotations

from typing import Any, Dict, List, Optional


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


def _extract_required_options(bot_format: Dict[str, Any]) -> List[Dict[str, Any]]:
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

    item_dict = dict(item or {})
    item_dict["unit"] = apply_explicit_unit_alias(
        str(item_dict.get("unit") or "").strip(),
        bot_format=bot_format,
        allowed_units=allowed_units,
    )

    qty_val = item_dict.get("qty")
    unit_val = str(item_dict.get("unit") or "").strip()
    specs_val = str(item_dict.get("specs") or item_dict.get("spec") or "").strip()
    effective_allowed_units = extract_allowed_units(bot_format, allowed_units)
    rules = bot_format.get("validation_rules") if isinstance(bot_format.get("validation_rules"), dict) else {}

    if qty_val is None:
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
    if strict_bot_format and block_if_unit_not_allowed and effective_allowed_units:
        if not unit_val or unit_val not in effective_allowed_units:
            return {
                "code": "unit_not_allowed",
                "expected": {"allowed_units": effective_allowed_units},
                "message": f'Unité "{unit_val or "∅"}" interdite. Les seules unités autorisées sont {", ".join(effective_allowed_units)}. Demande au client de choisir parmi les formats autorisés.',
                "item": item_dict,
            }

    required_options = _extract_required_options(bot_format)
    specs_lower = specs_val.lower()
    for opt in required_options:
        if not bool(opt.get("is_mandatory")):
            continue
        values = [str(v).strip() for v in (opt.get("values") or []) if str(v).strip()]
        if not specs_val:
            return {
                "code": "missing_required_option",
                "expected": {"name": opt.get("name"), "values": values},
                "message": f'Option manquante. Tu dois IMPERATIVEMENT demander l\'option {opt.get("name")} au client parmi cette liste : {", ".join(values)}.',
                "item": item_dict,
            }
        if values and not any(str(v).lower() in specs_lower for v in values):
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

        rejection = validate_cart_item(
            catalog,
            item,
            allowed_units=allowed_units,
            strict_bot_format=strict_bot_format,
        )
        if rejection:
            out["invalid"].append(rejection)
            continue
        out["confirmed"].append(item)

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
