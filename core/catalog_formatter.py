"""
core/catalog_formatter.py

Scalable WhatsApp price list formatter.
Reads vtree structure + detected fields → generates optimal compact display.

Elimination logic (based on detected_items_json):
  Case 1: unit known + spec null   → show specs for that unit only
  Case 2: spec known + unit null   → show units for that spec only
  Case 3: both null                → smart grouped format
  Case 4: both known               → returns empty (caller confirms price)

Pattern detection (Case 3):
  SAME_PRICE_PER_UNIT  – all specs same price per unit → numbered formats + taille note
  UNIQUE_UNIT          – single unit → numbered spec list + unit in header
  VARIED               – flat numbered list (spec + unit + price)
"""

from typing import Any, Dict, List, Optional, Tuple
import re


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

_EMOJI_MAP = {
    1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣",
    6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟",
}


def _num_emoji(n: int) -> str:
    return _EMOJI_MAP.get(n, f"{n}.")


def _fmt_price(price: int) -> str:
    """Format price with thousands separator: 13500 → '13 500 F'."""
    return f"{price:,} F".replace(",", " ")


def _parse_price(raw) -> Optional[int]:
    """Extract price integer from vtree value [price, stock] or raw."""
    try:
        if isinstance(raw, (list, tuple)) and raw:
            v = int(raw[0])
            return v if v > 0 else None
        if isinstance(raw, (int, float)):
            v = int(raw)
            return v if v > 0 else None
        if isinstance(raw, str):
            m = re.search(r"(\d+)", raw.replace(" ", ""))
            if m:
                v = int(m.group(1))
                return v if v > 0 else None
    except Exception:
        pass
    return None


def _format_unit_label(unit_key: str, custom_formats: List[Dict]) -> str:
    """Convert unit key like 'paquet_50' to readable label 'paquet de 50'."""
    u = str(unit_key or "").strip()
    if not u:
        return ""
    for f in (custom_formats or []):
        if not isinstance(f, dict):
            continue
        f_type = str(f.get("type") or "").strip()
        qty = f.get("quantity")
        try:
            qty_i = int(qty) if qty is not None else None
        except Exception:
            qty_i = None
        if f_type and qty_i and qty_i > 0:
            canonical = f"{f_type}_{qty_i}"
            if canonical.strip().lower() == u.lower():
                primary = str(
                    f.get("label") or f.get("customLabel") or f.get("custom_label") or ""
                ).strip()
                if primary:
                    return primary
                return f"{f_type} de {qty_i}"
    # Fallback: parse from key
    m = re.match(r"^(paquet|lot|carton|pack|boite|sac)_(\d+)$", u, flags=re.IGNORECASE)
    if m:
        return f"{m.group(1)} de {m.group(2)}"
    return u.replace("_", " ")


def _match_key_ci(keys, target: str) -> Optional[str]:
    """Case-insensitive key match."""
    t = str(target or "").strip().lower()
    if not t:
        return None
    for k in keys:
        if str(k or "").strip().lower() == t:
            return k
    return None


def _item(pid, variant, spec, unit, label, price, idx):
    """Build a standard item dict for reverse_lookup compatibility."""
    return {
        "product_id": pid,
        "variant": variant,
        "spec": spec,
        "unit": unit,
        "label": label,
        "price_fcfa": price,
        "index": idx,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def _analyze_variant(s_map: Dict) -> Dict[str, Any]:
    """Analyze pricing structure of a variant's specs."""
    all_units: set = set()
    prices_by_unit: Dict[str, List[int]] = {}
    specs = sorted(str(k) for k in s_map.keys() if str(k).strip())

    for sk in specs:
        snode = s_map.get(sk)
        if not isinstance(snode, dict):
            continue
        u_map = snode.get("u")
        if not isinstance(u_map, dict):
            continue
        for uk, raw in u_map.items():
            uk_s = str(uk).strip()
            if not uk_s:
                continue
            all_units.add(uk_s)
            p = _parse_price(raw)
            if p is not None:
                prices_by_unit.setdefault(uk_s, []).append(p)

    units = sorted(all_units)
    unique_unit = len(units) == 1
    same_price_per_unit = bool(prices_by_unit) and all(
        len(set(pp)) == 1 for pp in prices_by_unit.values()
    )

    if same_price_per_unit and len(units) > 1:
        pattern = "SAME_PRICE_PER_UNIT"
    elif unique_unit:
        pattern = "UNIQUE_UNIT"
    else:
        pattern = "VARIED"

    return {
        "pattern": pattern,
        "units": units,
        "specs": specs,
        "prices_by_unit": {u: sorted(set(pp)) for u, pp in prices_by_unit.items()},
    }


# ═══════════════════════════════════════════════════════════════════════════════
# FORMAT STRATEGIES
# ═══════════════════════════════════════════════════════════════════════════════

def _format_specs_for_unit(
    *, pid, variant, s_map, unit_key, cf
) -> Tuple[str, List[Dict]]:
    """Case 1: Unit known, spec missing → show specs for that unit."""
    unit_label = _format_unit_label(unit_key, cf)
    items: List[Dict] = []
    lines = [f"{unit_label} noté ! Quelle taille ?", ""]

    idx = 1
    for sk in sorted(s_map.keys(), key=str):
        snode = s_map.get(sk)
        if not isinstance(snode, dict):
            continue
        u = snode.get("u", {})
        if not isinstance(u, dict):
            continue
        matched = _match_key_ci(list(u.keys()), unit_key)
        if not matched:
            continue
        price = _parse_price(u[matched])
        if price is None:
            continue
        lines.append(f"{_num_emoji(idx)} {sk} : {_fmt_price(price)}")
        items.append(_item(pid, variant, sk, unit_key, unit_label, price, idx))
        idx += 1

    if not items:
        return "", []
    lines.append("")
    lines.append("👉 Dites-moi le numéro de votre choix.")
    return "\n".join(lines), items


def _format_units_for_spec(
    *, pid, variant, s_map, spec_key, cf
) -> Tuple[str, List[Dict]]:
    """Case 2: Spec known, unit missing → show units for that spec."""
    snode = s_map.get(spec_key)
    if not isinstance(snode, dict):
        return "", []
    u_map = snode.get("u", {})
    if not isinstance(u_map, dict) or not u_map:
        return "", []

    items: List[Dict] = []
    lines = [f"Taille {spec_key} notée ! Quel format ?", ""]

    # Sort units by price ascending
    _unit_prices = []
    for uk in u_map.keys():
        price = _parse_price(u_map[uk])
        if price is not None:
            _unit_prices.append((uk, price))
    _unit_prices.sort(key=lambda x: x[1])

    idx = 1
    for uk, price in _unit_prices:
        label = _format_unit_label(uk, cf)
        lines.append(f"{_num_emoji(idx)} {label} : {_fmt_price(price)}")
        items.append(_item(pid, variant, spec_key, uk, label, price, idx))
        idx += 1

    if not items:
        return "", []
    lines.append("")
    lines.append("👉 Dites-moi le numéro de votre choix.")
    return "\n".join(lines), items


def _format_same_price_compact(
    *, pid, variant, s_map, analysis, cf
) -> Tuple[str, List[Dict]]:
    """Case 3a: SAME_PRICE_PER_UNIT → numbered formats + taille note."""
    specs = analysis["specs"]
    specs_range = f"{specs[0]} à {specs[-1]}" if len(specs) > 2 else ", ".join(specs)

    lines = [f"🔹 {variant} (tailles {specs_range}, prix identique)", ""]

    # Sort formats by price ascending
    _fmt_prices = []
    for uk, pp in analysis["prices_by_unit"].items():
        _fmt_prices.append((uk, pp[0]))
    _fmt_prices.sort(key=lambda x: x[1])

    items: List[Dict] = []
    idx = 1
    for uk, price in _fmt_prices:
        label = _format_unit_label(uk, cf)
        lines.append(f"{_num_emoji(idx)} {label} : {_fmt_price(price)}")
        items.append(_item(pid, variant, None, uk, label, price, idx))
        idx += 1

    lines.append("")
    first_label = _format_unit_label(_fmt_prices[0][0], cf) if _fmt_prices else "format"
    lines.append("👉 Choisissez le numéro ou dites format + taille")
    lines.append(f'Ex : "{first_label} {specs[-1]}"')
    lines.append(f"(Tailles : {', '.join(specs)})")

    return "\n".join(lines), items


def _format_unique_unit(
    *, pid, variant, s_map, analysis, cf
) -> Tuple[str, List[Dict]]:
    """Case 3b: UNIQUE_UNIT → numbered spec list, unit in header."""
    unit_key = analysis["units"][0]
    unit_label = _format_unit_label(unit_key, cf)

    lines = [f"🔹 {variant} ({unit_label} uniquement)", ""]

    items: List[Dict] = []
    idx = 1
    for sk in analysis["specs"]:
        snode = s_map.get(sk)
        if not isinstance(snode, dict):
            continue
        u = snode.get("u", {})
        if not isinstance(u, dict):
            continue
        matched = _match_key_ci(list(u.keys()), unit_key)
        if not matched:
            continue
        price = _parse_price(u[matched])
        if price is None:
            continue
        lines.append(f"{_num_emoji(idx)} {sk} : {_fmt_price(price)}")
        items.append(_item(pid, variant, sk, unit_key, unit_label, price, idx))
        idx += 1

    if not items:
        return "", []
    lines.append("")
    lines.append("👉 Dites-moi le numéro de votre choix.")
    return "\n".join(lines), items


def _format_varied(
    *, pid, variant, s_map, cf
) -> Tuple[str, List[Dict]]:
    """Case 3c: VARIED prices → flat numbered list (spec + unit + price)."""
    raw_items = []
    for sk in sorted(s_map.keys(), key=str):
        snode = s_map.get(sk)
        if not isinstance(snode, dict):
            continue
        u = snode.get("u", {})
        if not isinstance(u, dict):
            continue
        for uk in sorted(u.keys(), key=str):
            price = _parse_price(u[uk])
            if price is None:
                continue
            label = _format_unit_label(uk, cf)
            raw_items.append((sk, uk, label, price))

    # Sort by price ascending
    raw_items.sort(key=lambda x: x[3])
    if len(raw_items) > 12:
        raw_items = raw_items[:12]

    items: List[Dict] = []
    lines = [f"🔹 {variant}", ""]
    idx = 1
    for sk, uk, label, price in raw_items:
        lines.append(f"{_num_emoji(idx)} {sk} - {label} : {_fmt_price(price)}")
        items.append(_item(pid, variant, sk, uk, label, price, idx))
        idx += 1

    if not items:
        return "", []
    lines.append("")
    lines.append("👉 Dites-moi le numéro de votre choix.")
    return "\n".join(lines), items


def _format_direct_units(
    *, pid, variant, u_map, cf
) -> Tuple[str, List[Dict]]:
    """Variant with no specs, just units directly."""
    items: List[Dict] = []
    lines = [f"🔹 {variant}", ""]

    idx = 1
    for uk in sorted(u_map.keys(), key=str):
        price = _parse_price(u_map[uk])
        if price is None:
            continue
        label = _format_unit_label(uk, cf)
        lines.append(f"{_num_emoji(idx)} {label} : {_fmt_price(price)}")
        items.append(_item(pid, variant, None, uk, label, price, idx))
        idx += 1

    if not items:
        return "", []
    lines.append("")
    lines.append("👉 Dites-moi le numéro de votre choix.")
    return "\n".join(lines), items


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def auto_fill_single_options(
    *,
    variant_node: Dict,
    detected_spec: Optional[str] = None,
    detected_unit: Optional[str] = None,
) -> Dict[str, Optional[str]]:
    """
    Auto-fill fields when only 1 possible option exists in catalogue.

    Returns dict with:
        filled_spec:  spec value if auto-filled, else None
        filled_unit:  unit value if auto-filled, else None
        reason:       human-readable explanation for LLM context
    """
    result: Dict[str, Optional[str]] = {"filled_spec": None, "filled_unit": None, "reason": None}
    if not isinstance(variant_node, dict):
        return result

    s_map = variant_node.get("s") if isinstance(variant_node.get("s"), dict) else None
    if not isinstance(s_map, dict) or not s_map:
        return result

    # Collect all units across all specs
    all_units: set = set()
    for sn in s_map.values():
        if isinstance(sn, dict) and isinstance(sn.get("u"), dict):
            all_units.update(sn["u"].keys())

    reasons = []

    # Auto-fill unit if only 1 exists across all specs
    if not detected_unit and len(all_units) == 1:
        result["filled_unit"] = list(all_units)[0]
        reasons.append(f"seul format disponible: {list(all_units)[0]}")

    # Auto-fill spec if only 1 exists
    specs = [str(k) for k in s_map.keys() if str(k).strip()]
    if not detected_spec and len(specs) == 1:
        result["filled_spec"] = specs[0]
        reasons.append(f"seule taille disponible: {specs[0]}")

    if reasons:
        result["reason"] = " | ".join(reasons)

    return result


def format_price_list(
    *,
    product_id: str,
    variant_key: str,
    variant_node: Dict,
    detected_spec: Optional[str] = None,
    detected_unit: Optional[str] = None,
    custom_formats: Optional[List[Dict]] = None,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Generate smart price list for a variant.

    Args:
        product_id:    Product ID
        variant_key:   Variant name (e.g. "Culotte")
        variant_node:  vtree node for this variant (e.g. vtree["Culotte"])
        detected_spec: Spec already detected from user message (e.g. "T5")
        detected_unit: Unit already detected from user message (e.g. "paquet_50")
        custom_formats: customFormats from ui_state for label resolution

    Returns:
        (formatted_text, items_list)
        Empty ("", []) when both spec+unit are known (caller confirms price).
    """
    cf = custom_formats or []
    if not isinstance(variant_node, dict):
        return "", []

    s_map = variant_node.get("s") if isinstance(variant_node.get("s"), dict) else None
    u_map_direct = variant_node.get("u") if isinstance(variant_node.get("u"), dict) else None

    # Variant with NO specs → just show units
    if isinstance(u_map_direct, dict) and u_map_direct and not s_map:
        return _format_direct_units(
            pid=product_id, variant=variant_key, u_map=u_map_direct, cf=cf,
        )

    if not isinstance(s_map, dict) or not s_map:
        return "", []

    # Normalize detected values
    d_spec = str(detected_spec or "").strip() or None
    d_unit = str(detected_unit or "").strip() or None

    # Case-insensitive match detected values against actual keys
    if d_spec:
        d_spec = _match_key_ci(list(s_map.keys()), d_spec) or d_spec
    if d_unit:
        all_unit_keys: set = set()
        for sn in s_map.values():
            if isinstance(sn, dict) and isinstance(sn.get("u"), dict):
                all_unit_keys.update(sn["u"].keys())
        d_unit = _match_key_ci(list(all_unit_keys), d_unit) or d_unit

    analysis = _analyze_variant(s_map)

    # Case 4: Both known → empty (caller confirms price directly)
    if d_spec and d_unit:
        return "", []

    # Case 1: Unit known, spec missing → show specs only
    if d_unit and not d_spec:
        return _format_specs_for_unit(
            pid=product_id, variant=variant_key, s_map=s_map,
            unit_key=d_unit, cf=cf,
        )

    # Case 2: Spec known, unit missing → show units only
    if d_spec and not d_unit:
        return _format_units_for_spec(
            pid=product_id, variant=variant_key, s_map=s_map,
            spec_key=d_spec, cf=cf,
        )

    # Case 3: Both missing → pattern-based smart display
    if analysis["pattern"] == "SAME_PRICE_PER_UNIT":
        return _format_same_price_compact(
            pid=product_id, variant=variant_key, s_map=s_map,
            analysis=analysis, cf=cf,
        )
    elif analysis["pattern"] == "UNIQUE_UNIT":
        return _format_unique_unit(
            pid=product_id, variant=variant_key, s_map=s_map,
            analysis=analysis, cf=cf,
        )
    else:
        return _format_varied(
            pid=product_id, variant=variant_key, s_map=s_map, cf=cf,
        )
