import re
from typing import Any, Dict, List, Optional, Tuple

from core.company_catalog_v2_loader import get_company_product_catalog_v2


def match_key_case_insensitive(keys: List[str], target: str) -> Optional[str]:
    t = str(target or "").strip().lower()
    if not t:
        return None
    for k in keys:
        if str(k or "").strip().lower() == t:
            return str(k)
    return None


def soft_match(keys: List[str], target: str) -> Optional[str]:
    t = str(target or "").strip().lower()
    if not t:
        return None
    for k in keys:
        kl = str(k or "").strip().lower()
        if t and (t in kl or kl in t):
            return str(k)
    return None


def select_product_catalog(
    *,
    company_id: str,
    container: Optional[Dict[str, Any]],
    product_id: str,
) -> Optional[Dict[str, Any]]:
    if not isinstance(container, dict):
        return None

    plist = container.get("products")
    if not isinstance(plist, list):
        return container

    pid = str(product_id or "").strip()
    if not pid:
        only_one = [p for p in plist if isinstance(p, dict) and isinstance(p.get("catalog_v2"), dict)]
        if len(only_one) == 1:
            return only_one[0].get("catalog_v2")
        return None

    try:
        selected = get_company_product_catalog_v2(company_id, pid)
        if isinstance(selected, dict):
            return selected
    except Exception:
        selected = None

    for p in plist:
        if not isinstance(p, dict):
            continue
        cat = p.get("catalog_v2") if isinstance(p.get("catalog_v2"), dict) else None
        if not isinstance(cat, dict):
            continue
        pid2 = str(p.get("product_id") or cat.get("product_id") or "").strip()
        if pid2 and pid2.lower() == pid.lower():
            return cat

    return None


def extract_t_number(specs_raw: str) -> Optional[int]:
    s = str(specs_raw or "").strip().upper()
    m = re.search(r"\bT\s*([1-9]\d*)\b", s)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    m2 = re.search(r"\bTAILLE\s*([1-9]\d*)\b", s)
    if m2:
        try:
            return int(m2.group(1))
        except Exception:
            return None
    return None


def spec_key_matches(sub_key: str, requested_specs: str) -> bool:
    if not sub_key:
        return False
    exact = match_key_case_insensitive([str(sub_key)], requested_specs)
    if exact:
        return True

    req_n = extract_t_number(requested_specs)
    if req_n is None:
        return False

    nums = [int(x) for x in re.findall(r"T\s*([1-9]\d*)", str(sub_key).upper()) if x.isdigit()]
    if not nums:
        return False
    lo, hi = min(nums), max(nums)
    return lo <= req_n <= hi


def find_subvariant_key(node_s: Dict[str, Any], specs_raw: str) -> Optional[str]:
    if not isinstance(node_s, dict):
        return None
    specs_s = str(specs_raw or "").strip()
    if not specs_s:
        return None
    sub_keys = [str(k) for k in node_s.keys()]
    exact = match_key_case_insensitive(sub_keys, specs_s)
    if exact:
        return exact
    for k in sub_keys:
        if spec_key_matches(k, specs_s):
            return str(k)
    return soft_match(sub_keys, specs_s)


def resolve_variant_and_specs(
    *,
    catalog_v2: Dict[str, Any],
    product_hint: str,
    specs_hint: str,
) -> Tuple[str, str]:
    vtree = catalog_v2.get("v")
    if not isinstance(vtree, dict) or not vtree:
        return "", ""

    v_keys = [str(k) for k in vtree.keys() if str(k).strip()]
    if not v_keys:
        return "", ""

    variant_key = None
    for cand in [product_hint, specs_hint]:
        if not cand:
            continue
        variant_key = match_key_case_insensitive(v_keys, cand) or soft_match(v_keys, cand)
        if variant_key:
            break
    if (not variant_key) and len(v_keys) == 1:
        variant_key = str(v_keys[0])
    if not variant_key:
        return "", ""

    node = vtree.get(variant_key)
    if not isinstance(node, dict):
        return str(variant_key), ""

    node_s = node.get("s")
    if not isinstance(node_s, dict) or not node_s:
        return str(variant_key), ""

    sub_key = find_subvariant_key(node_s, specs_hint)
    return str(variant_key), str(sub_key or "")


def allowed_units_for_variant_and_specs(
    *,
    catalog_v2: Dict[str, Any],
    variant_key: str,
    specs_key: str,
) -> List[str]:
    vtree = catalog_v2.get("v")
    if not isinstance(vtree, dict) or not vtree:
        return []

    node = vtree.get(variant_key)
    if not isinstance(node, dict):
        return []

    if specs_key:
        node_s = node.get("s")
        if isinstance(node_s, dict) and isinstance(node_s.get(specs_key), dict):
            sub_u = node_s.get(specs_key, {}).get("u")
            if isinstance(sub_u, dict) and sub_u:
                return sorted({str(k).strip() for k in sub_u.keys() if str(k).strip()})

    node_u = node.get("u")
    if isinstance(node_u, dict) and node_u:
        return sorted({str(k).strip() for k in node_u.keys() if str(k).strip()})

    node_s = node.get("s")
    if isinstance(node_s, dict) and node_s:
        out: set[str] = set()
        for sub in node_s.values():
            if not isinstance(sub, dict):
                continue
            sub_u = sub.get("u")
            if not isinstance(sub_u, dict):
                continue
            for key in sub_u.keys():
                if str(key).strip():
                    out.add(str(key).strip())
        return sorted(out)
    return []


def resolve_catalog_item_context(
    *,
    company_id: str,
    container: Optional[Dict[str, Any]],
    product_id: str,
    product_hint: str,
    specs_hint: str,
) -> Dict[str, Any]:
    selected_catalog = select_product_catalog(company_id=company_id, container=container, product_id=product_id)
    if not isinstance(selected_catalog, dict):
        selected_catalog = container if isinstance(container, dict) else None
    if not isinstance(selected_catalog, dict):
        return {"catalog": None, "variant_key": "", "specs_key": "", "allowed_units": []}

    variant_key, specs_key = resolve_variant_and_specs(
        catalog_v2=selected_catalog,
        product_hint=product_hint,
        specs_hint=specs_hint,
    )
    if not variant_key and specs_hint:
        variant_key, specs_key = resolve_variant_and_specs(
            catalog_v2=selected_catalog,
            product_hint=specs_hint,
            specs_hint="",
        )
    allowed_units = allowed_units_for_variant_and_specs(
        catalog_v2=selected_catalog,
        variant_key=variant_key,
        specs_key=specs_key,
    )
    return {
        "catalog": selected_catalog,
        "variant_key": variant_key,
        "specs_key": specs_key,
        "allowed_units": allowed_units,
    }
