import json
import re
from typing import Any, Dict, List, Optional


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


def _compress_labels(labels: List[str]) -> str:
    items = [str(x).strip() for x in (labels or []) if str(x).strip()]
    if not items:
        return ""
    items = sorted(set(items), key=lambda x: x)
    if len(items) <= 8:
        return ", ".join(items)
    return f"{items[0]}, …, {items[-1]} ({len(items)})"


def _extract_bot_format(catalog: Dict[str, Any]) -> Dict[str, Any]:
    bot_format = catalog.get("bot_format")
    if isinstance(bot_format, dict):
        return bot_format
    ui_state = catalog.get("ui_state")
    if isinstance(ui_state, dict) and isinstance(ui_state.get("bot_format"), dict):
        return ui_state.get("bot_format") or {}
    return {}


def _extract_unit_aliases(bot_format: Dict[str, Any]) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    raw_allowed = bot_format.get("allowed_units") if isinstance(bot_format.get("allowed_units"), list) else []
    for row in raw_allowed:
        if not isinstance(row, dict):
            continue
        key = str(row.get("key") or "").strip()
        aliases = row.get("aliases") if isinstance(row.get("aliases"), list) else []
        clean_aliases = [str(a).strip().lower() for a in aliases if str(a).strip()]
        if key:
            out[key] = sorted(set(clean_aliases))
    legacy = bot_format.get("unit_aliases") if isinstance(bot_format.get("unit_aliases"), dict) else {}
    for key, aliases in legacy.items():
        canon = str(key or "").strip()
        vals = aliases if isinstance(aliases, list) else []
        clean = [str(a).strip().lower() for a in vals if str(a).strip()]
        if canon:
            merged = set(out.get(canon, []))
            merged.update(clean)
            out[canon] = sorted(merged)
    return out


def _extract_allowed_units(bot_format: Dict[str, Any], catalog: Dict[str, Any]) -> List[str]:
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

    if not allowed_units:
        canonical_units = catalog.get("canonical_units")
        if isinstance(canonical_units, list):
            allowed_units.extend(str(u).strip() for u in canonical_units if str(u).strip())

    return sorted(set([u for u in allowed_units if u]))


def _extract_required_options(bot_format: Dict[str, Any]) -> List[Dict[str, Any]]:
    required_options = bot_format.get("required_options")
    if isinstance(required_options, list):
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
        name = str(row.get("label") or row.get("key") or "").strip()
        if name and clean_values:
            fallback.append(
                {
                    "name": name,
                    "key": str(row.get("key") or "").strip(),
                    "is_mandatory": bool(row.get("required", True)),
                    "values": clean_values,
                }
            )
    return fallback


def _extract_selling_formats(bot_format: Dict[str, Any], catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
    selling_formats = bot_format.get("selling_formats")
    if isinstance(selling_formats, list):
        clean: List[Dict[str, Any]] = []
        for row in selling_formats:
            if not isinstance(row, dict):
                continue
            format_name = str(row.get("format_name") or "").strip()
            canonical_id = str(row.get("canonical_id") or "").strip()
            if not canonical_id and not format_name:
                continue
            price = row.get("price")
            try:
                price = int(float(price)) if price is not None and str(price).strip() != "" else None
            except Exception:
                price = None
            try:
                min_order = int(row.get("min_order")) if row.get("min_order") is not None else None
            except Exception:
                min_order = None
            clean.append(
                {
                    "format_name": format_name or canonical_id,
                    "canonical_id": canonical_id,
                    "min_order": min_order,
                    "price": price,
                }
            )
        if clean:
            return clean

    fallback: List[Dict[str, Any]] = []
    allowed_units = _extract_allowed_units(bot_format, catalog)
    min_rules = bot_format.get("validation_rules") if isinstance(bot_format.get("validation_rules"), dict) else {}
    min_by_unit = min_rules.get("min_order_by_unit") if isinstance(min_rules.get("min_order_by_unit"), dict) else {}
    price_matrix = catalog.get("priceMatrix") if isinstance(catalog.get("priceMatrix"), dict) else {}
    for unit in allowed_units:
        size = _parse_unit_size(unit)
        label = "Pièce" if unit == "piece" else unit
        if size is not None and "_" in unit:
            head = unit.split("_", 1)[0]
            label_map = {
                "lot": "Lot de",
                "paquet": "Paquet de",
                "balle": "Balle de",
                "carton": "Carton de",
                "pack": "Pack de",
                "caisse": "Caisse de",
            }
            label = f"{label_map.get(head, head.capitalize())} {size}".strip()
        price = None
        for key, value in price_matrix.items():
            if str(key).lower().endswith(f"_{unit.lower()}") or f"_{unit.lower()}" in str(key).lower():
                price = _parse_price_value(value)
                if price is not None:
                    break
        fallback.append(
            {
                "format_name": label,
                "canonical_id": unit,
                "min_order": int(min_by_unit.get(unit) or 0) or None,
                "price": price,
            }
        )
    return fallback


def build_catalogue_block_from_catalog_v2(catalog: Dict[str, Any]) -> str:
    try:
        if not isinstance(catalog, dict) or not catalog:
            return ""

        bot_format = _extract_bot_format(catalog)
        pricing_mode = str(bot_format.get("pricing_mode") or "").strip().lower()
        sales_target = str(bot_format.get("sales_target") or bot_format.get("sales_mode") or "").strip().lower()
        allowed_units = _extract_allowed_units(bot_format, catalog)
        unit_aliases = _extract_unit_aliases(bot_format)
        required_options = _extract_required_options(bot_format)
        selling_formats = _extract_selling_formats(bot_format, catalog)
        free_texts = bot_format.get("free_texts") if isinstance(bot_format.get("free_texts"), dict) else {}
        technical_specs = str(free_texts.get("technical_specs") or catalog.get("technical_specs") or "").strip()
        sales_constraints = str(free_texts.get("sales_constraints") or catalog.get("sales_constraints") or "").strip()
        important_note = str(free_texts.get("important_note") or catalog.get("important_note") or "").strip()
        description = str(catalog.get("description") or "").strip()

        lines: List[str] = ["# CATALOGUE_REFERENCE (AUTO)", ""]

        if description:
            lines.append("## DESCRIPTION (RAW)")
            lines.append(description)
            lines.append("")

        if selling_formats:
            lines.append("## FORMATS_DE_VENTE")
            for row in selling_formats:
                tail: List[str] = []
                canonical_id = str(row.get("canonical_id") or "").strip()
                format_name = str(row.get("format_name") or canonical_id or "").strip()
                price = row.get("price")
                min_order = row.get("min_order")
                if canonical_id:
                    tail.append(f"canonical={canonical_id}")
                if price is not None:
                    tail.append(f"price={price}")
                if min_order is not None:
                    tail.append(f"min_order={min_order}")
                suffix = f" | {' | '.join(tail)}" if tail else ""
                lines.append(f"- (format) -> {format_name}{suffix}")
            lines.append("")

        if required_options:
            lines.append("## REQUIRED_CHOICES (BLOCKERS)")
            for row in required_options:
                values = [str(v).strip() for v in (row.get("values") or []) if str(v).strip()]
                values_txt = ", ".join(values)
                label = "Obligatoire" if bool(row.get("is_mandatory")) else "Optionnel"
                if values_txt:
                    lines.append(f"- {row.get('name')} ({label}) : {values_txt}")
                else:
                    lines.append(f"- {row.get('name')} ({label})")
            lines.append("")

        auto_rules: List[str] = []
        if pricing_mode:
            auto_rules.append(f"- pricing_mode: {pricing_mode}" if pricing_mode == "unique" else f"- pricing_mode: {pricing_mode} (per_format)")
        if sales_target:
            auto_rules.append(f"- sales_target: {sales_target}")
        if allowed_units:
            auto_rules.append(f"- allowed_units: {', '.join(allowed_units)}")
            auto_rules.append(f"- sold_only_by: {', '.join(allowed_units)}")
        if unit_aliases:
            alias_chunks = []
            for unit, aliases in unit_aliases.items():
                if aliases:
                    alias_chunks.append(f"{unit} => {', '.join(aliases)}")
            if alias_chunks:
                auto_rules.append(f"- unit_aliases: {' ; '.join(alias_chunks)}")
        if selling_formats:
            parsed_prices = [int(row.get("price")) for row in selling_formats if isinstance(row.get("price"), int)]
            parsed_sizes = [_parse_unit_size(str(row.get('canonical_id') or '')) for row in selling_formats]
            parsed_pairs = [(parsed_sizes[i], parsed_prices[i]) for i in range(min(len(parsed_sizes), len(parsed_prices))) if parsed_sizes[i] is not None]
            if len(parsed_prices) <= 1:
                auto_rules.append("- pricing_by_specs: FIXE (observed)")
                auto_rules.append("- volume_discount: false")
            else:
                auto_rules.append("- pricing_by_specs: UNKNOWN")
                if len(parsed_pairs) >= 2:
                    unit_prices = sorted([(size, price / float(size)) for size, price in parsed_pairs], key=lambda x: x[0])
                    has_discount = any(unit_prices[i][1] < unit_prices[i - 1][1] for i in range(1, len(unit_prices)))
                    auto_rules.append(f"- volume_discount: {'true' if has_discount else 'false'}")
        if auto_rules:
            lines.append("## AUTO_RULES (DEDUCTIONS_SURES)")
            lines.extend(auto_rules)
            lines.append("")

        if technical_specs:
            lines.append("## TECHNICAL_SPECS (RAW)")
            lines.append(technical_specs)
            lines.append("")

        if sales_constraints:
            lines.append("## SALES_CONSTRAINTS (RAW)")
            lines.append(sales_constraints)
            lines.append("")

        if important_note:
            lines.append("## IMPORTANT_NOTE (RAW)")
            lines.append(important_note)
            lines.append("")

        if lines and not lines[-1]:
            lines.pop()
        return "\n".join(lines).strip() + "\n"
    except Exception:
        return ""
