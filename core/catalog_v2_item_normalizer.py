import re
from typing import Any, Dict, List, Optional, Tuple

from core.company_catalog_v2_loader import get_company_catalog_v2, get_company_product_catalog_v2


def _norm_name_for_id(name: str) -> str:
    try:
        import unicodedata as _ud

        t = str(name or "").strip().lower()
        t = _ud.normalize("NFKD", t)
        t = "".join([c for c in t if not _ud.combining(c)])
    except Exception:
        t = str(name or "").strip().lower()
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


def _match_key_case_insensitive(keys: List[str], target: str) -> Optional[str]:
    t = str(target or "").strip().lower()
    if not t:
        return None
    for k in keys:
        if str(k or "").strip().lower() == t:
            return str(k)
    return None


def _soft_match(keys: List[str], target: str) -> Optional[str]:
    t = str(target or "").strip().lower()
    if not t:
        return None
    for k in keys:
        kl = str(k or "").strip().lower()
        if t and (t in kl or kl in t):
            return str(k)
    return None


def _parse_unit_key(unit_key: str) -> Optional[Dict[str, Any]]:
    s = str(unit_key or "").strip().lower()
    if not s:
        return None
    if "_" not in s:
        return None
    head, tail = s.split("_", 1)
    if not head:
        return None
    digits = re.sub(r"\D+", "", tail)
    if not digits:
        return None
    try:
        n = int(digits)
    except Exception:
        return None
    if n <= 0:
        return None
    return {"type": head, "size": n, "key": str(unit_key)}


def _extract_int(text: str) -> Optional[int]:
    m = re.search(r"\b(\d+)\b", str(text or ""))
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def _select_product_catalog(
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
        # allow if only one product
        only_one = [p for p in plist if isinstance(p, dict) and isinstance(p.get("catalog_v2"), dict)]
        if len(only_one) == 1:
            return only_one[0].get("catalog_v2")
        return None

    # direct resolver (works when pid is normalized product_name)
    try:
        selected = get_company_product_catalog_v2(company_id, pid)
        if isinstance(selected, dict):
            return selected
    except Exception:
        selected = None

    # multi-product: direct product_id match inside container
    if isinstance(container, dict) and isinstance(container.get("products"), list):
        plist2 = [p for p in (container.get("products") or []) if isinstance(p, dict)]
        for p in plist2:
            cat2 = p.get("catalog_v2") if isinstance(p.get("catalog_v2"), dict) else None
            if not isinstance(cat2, dict):
                continue
            pid2 = str(p.get("product_id") or cat2.get("product_id") or "").strip()
            if pid2 and pid2.lower() == pid.lower():
                return cat2

    # fallback: pid can be legacy prod_<sha1:8>
    if re.fullmatch(r"prod_[0-9a-f]{8}", pid, flags=re.IGNORECASE):
        pid_l = pid.lower()
        for p in plist:
            if not isinstance(p, dict):
                continue
            pname = str(p.get("product_name") or (p.get("catalog_v2") or {}).get("product_name") or "").strip()
            if pname and _product_id_hash(pname).lower() == pid_l and isinstance(p.get("catalog_v2"), dict):
                return p.get("catalog_v2")

    return None


def _map_product_id_if_needed(
    *,
    company_id: str,
    catalog_container: Optional[Dict[str, Any]],
    raw_pid: str,
) -> str:
    pid = str(raw_pid or "").strip()
    if not pid:
        return ""

    # already a product_id (new format or legacy) -> keep
    if re.fullmatch(r"prod_[a-z0-9_\-]{6,80}", pid, flags=re.IGNORECASE):
        return pid

    # If container is multi-product, map a name-like product_id to real product_id (preferred) or legacy hash.
    if isinstance(catalog_container, dict) and isinstance(catalog_container.get("products"), list):
        cname = _norm_name_for_id(pid)
        for p in (catalog_container.get("products") or []):
            if not isinstance(p, dict):
                continue
            pname = str(p.get("product_name") or (p.get("catalog_v2") or {}).get("product_name") or "").strip()
            if pname and _norm_name_for_id(pname) == cname:
                real_id = str(p.get("product_id") or (p.get("catalog_v2") or {}).get("product_id") or "").strip()
                if real_id:
                    return real_id
                mapped = _product_id_hash(pname)
                return mapped or pid

    # If mono-product, keep as-is (can refer to business product_name)
    return pid


def _resolve_variant_and_specs(
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

    # Variant key
    candidates = [product_hint, specs_hint]
    variant_key: Optional[str] = None
    for cand in candidates:
        if not cand:
            continue
        variant_key = _match_key_case_insensitive(v_keys, cand) or _soft_match(v_keys, cand)
        if variant_key:
            break
    if (not variant_key) and len(v_keys) == 1:
        variant_key = str(v_keys[0])

    if not variant_key:
        return "", ""

    node = vtree.get(variant_key)
    if not isinstance(node, dict):
        return str(variant_key), ""

    s_map = node.get("s")
    if not isinstance(s_map, dict) or not s_map:
        return str(variant_key), ""

    sub_keys = [str(k) for k in s_map.keys() if str(k).strip()]
    if not sub_keys:
        return str(variant_key), ""

    specs_s = str(specs_hint or "").strip()
    if not specs_s:
        return str(variant_key), ""

    sub = _match_key_case_insensitive(sub_keys, specs_s) or _soft_match(sub_keys, specs_s)
    if sub:
        return str(variant_key), str(sub)

    # numeric range match (generic)
    req_n = _extract_int(specs_s)
    if req_n is not None:
        for k in sub_keys:
            nums = [int(x) for x in re.findall(r"(\d+)", str(k)) if x.isdigit()]
            if not nums:
                continue
            lo, hi = min(nums), max(nums)
            if lo <= req_n <= hi:
                return str(variant_key), str(k)

    return str(variant_key), ""


def _map_weight_to_spec_from_technical_specs(*, catalog_v2: Dict[str, Any], specs_hint: str) -> Tuple[str, str]:
    specs_s = str(specs_hint or "").strip()
    if not specs_s:
        return "", ""

    w = _extract_int(specs_s)
    if w is None:
        return "", ""

    if not re.search(r"\bkg\b", specs_s, flags=re.IGNORECASE):
        return "", ""

    tech = str(catalog_v2.get("technical_specs") or "")
    if not tech.strip():
        return "", ""

    matches: List[Tuple[str, int, int]] = []
    try:
        for m in re.finditer(r"\b(T\d+)\b[^\n\r]*?\(\s*(\d+)\s*[–\-]\s*(\d+)\s*kg\s*\)", tech, flags=re.IGNORECASE):
            key = str(m.group(1) or "").strip().upper()
            try:
                lo = int(m.group(2))
                hi = int(m.group(3))
            except Exception:
                continue
            if key and lo > 0 and hi > 0 and lo <= hi:
                matches.append((key, lo, hi))
    except Exception:
        matches = []

    if not matches:
        return "", ""

    hits = [k for (k, lo, hi) in matches if lo <= int(w) <= hi]
    hits = sorted(set([h for h in hits if h]))
    if len(hits) == 1:
        return hits[0], ""
    if len(hits) > 1:
        return "", "AMBIGU"
    return "", "INCOMPATIBLE"


def _allowed_units_for_variant_and_specs(
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
        s_map = node.get("s")
        if isinstance(s_map, dict) and isinstance(s_map.get(specs_key), dict):
            sub_u = s_map.get(specs_key, {}).get("u")
            if isinstance(sub_u, dict) and sub_u:
                return sorted({str(k) for k in sub_u.keys() if str(k).strip()})

    u_map = node.get("u")
    if isinstance(u_map, dict) and u_map:
        return sorted({str(k) for k in u_map.keys() if str(k).strip()})

    # fallback to union across specs
    s_map2 = node.get("s")
    if isinstance(s_map2, dict) and s_map2:
        out: set[str] = set()
        for sub in s_map2.values():
            if not isinstance(sub, dict):
                continue
            sub_u = sub.get("u")
            if not isinstance(sub_u, dict):
                continue
            for k in sub_u.keys():
                if str(k).strip():
                    out.add(str(k).strip())
        return sorted(out)

    return []


def _canonicalize_unit_and_qty(
    *,
    allowed_units: List[str],
    catalog_v2: Dict[str, Any],
    raw_unit: str,
    raw_qty: Any,
    message: str,
) -> Tuple[str, Optional[int]]:
    unit_s = str(raw_unit or "").strip()
    unit_l = unit_s.lower()

    qty_i: Optional[int] = None
    try:
        if isinstance(raw_qty, bool):
            qty_i = None
        elif raw_qty is None:
            qty_i = None
        elif isinstance(raw_qty, int):
            qty_i = raw_qty
        else:
            qty_i = int(float(str(raw_qty).strip()))
    except Exception:
        qty_i = None

    allowed = [str(u).strip() for u in (allowed_units or []) if str(u).strip()]

    # Direct
    if unit_s and unit_s in allowed:
        return unit_s, qty_i

    def _units_from_vtree(cv2: Dict[str, Any]) -> List[str]:
        try:
            vtree = cv2.get("v")
            if not isinstance(vtree, dict):
                return []
            out: set[str] = set()
            for _vk, _node in vtree.items():
                if not isinstance(_node, dict):
                    continue
                uu = _node.get("u")
                if isinstance(uu, dict):
                    for _uk in uu.keys():
                        if str(_uk).strip():
                            out.add(str(_uk).strip())
                ss = _node.get("s")
                if isinstance(ss, dict):
                    for _sub in ss.values():
                        if not isinstance(_sub, dict):
                            continue
                        uu2 = _sub.get("u")
                        if not isinstance(uu2, dict):
                            continue
                        for _uk in uu2.keys():
                            if str(_uk).strip():
                                out.add(str(_uk).strip())

            return sorted(out)
        except Exception:
            return []

    canon_units = catalog_v2.get("canonical_units")
    if not isinstance(canon_units, list):
        canon_units = []
    canon_units = [str(u).strip() for u in canon_units if str(u).strip()]

    if not canon_units:
        canon_units = _units_from_vtree(catalog_v2)

    if not canon_units and allowed:
        canon_units = list(allowed)

    if unit_s and unit_s in canon_units and (not allowed or unit_s in allowed):
        return unit_s, qty_i

    for t in ["lot", "paquet", "pack", "carton", "colis", "balle"]:
        if re.search(rf"\b{t}s?\b", msg_l):
            token = _canon_token(t)
            break

    parsed_units = [_parse_unit_key(u) for u in canon_units]
    parsed_units = [p for p in parsed_units if p]

    allowed_set = set(allowed) if allowed else set(canon_units)

    # If user used a non-canonical/vague unit (ex: "carton") but the catalog allows only ONE unit
    # for this variant/spec, we can safely map to that single unit.
    if unit_s and (unit_s not in allowed_set) and len(allowed_set) == 1:
        return list(allowed_set)[0], qty_i

    # If user provided a unit that is not allowed and there are multiple possible units,
    # do not keep an invalid unit; force clarification downstream.
    if unit_s and (unit_s not in allowed_set) and len(allowed_set) > 1:
        return "", None

    if (not unit_s) and len(allowed_set) == 1:
        return list(allowed_set)[0], qty_i

    if token and token != "piece":
        candidates = [p for p in parsed_units if p.get("type") == token and str(p.get("key") or "") in allowed_set]
        candidates = sorted(candidates, key=lambda x: int(x.get("size") or 0))
        base = candidates[0] if candidates else None
        if base and qty_i is not None and qty_i > 0:
            try:
                total = int(qty_i) * int(base.get("size") or 0)
            except Exception:
                total = 0
            if total > 0:
                exact = [p for p in candidates if int(p.get("size") or 0) == total]
                if exact:
                    return str(exact[0].get("key")), 1
        if base:
            return str(base.get("key")), qty_i

    # piece fallback: if exactly one allowed unit, pick it
    if token == "piece":
        if len(allowed_set) == 1:
            return list(allowed_set)[0], qty_i

    return unit_s, qty_i


def normalize_detected_items(
    *,
    company_id: str,
    items: List[Dict[str, Any]],
    message: str,
    catalog_container: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    cid = str(company_id or "").strip()
    if not cid:
        return [it for it in (items or []) if isinstance(it, dict)]

    container = catalog_container
    if not isinstance(container, dict):
        try:
            container = get_company_catalog_v2(cid)
        except Exception:
            container = None

    out: List[Dict[str, Any]] = []
    for raw in (items or []):
        if not isinstance(raw, dict):
            continue

        pid_raw = str(raw.get("product_id") or "").strip()
        pid = _map_product_id_if_needed(company_id=cid, catalog_container=container, raw_pid=pid_raw)

        # `product_id` is the technical ID. `variant` is the business variant key (vtree key).
        # Keep them separate; never use variant as product_id.
        product_hint = str(raw.get("variant") or raw.get("product") or "").strip()
        specs_hint = str(raw.get("specs") or "").strip() or str(raw.get("spec") or "").strip()

        selected_catalog = _select_product_catalog(company_id=cid, container=container, product_id=pid)
        if not isinstance(selected_catalog, dict):
            selected_catalog = container if isinstance(container, dict) else None
        if not isinstance(selected_catalog, dict):
            out.append({**raw, "product_id": pid})
            continue

        variant_key, specs_key = _resolve_variant_and_specs(
            catalog_v2=selected_catalog,
            product_hint=product_hint,
            specs_hint=specs_hint,
        )

        weight_mapped_spec, weight_status = "", ""
        try:
            if (not specs_key) and specs_hint:
                weight_mapped_spec, weight_status = _map_weight_to_spec_from_technical_specs(
                    catalog_v2=selected_catalog,
                    specs_hint=specs_hint,
                )
                if weight_mapped_spec:
                    specs_key = weight_mapped_spec
        except Exception:
            weight_mapped_spec, weight_status = "", ""

        allowed_units = _allowed_units_for_variant_and_specs(
            catalog_v2=selected_catalog,
            variant_key=variant_key,
            specs_key=specs_key,
        )

        unit_key, qty_i = _canonicalize_unit_and_qty(
            allowed_units=allowed_units,
            catalog_v2=selected_catalog,
            raw_unit=str(raw.get("unit") or "").strip(),
            raw_qty=raw.get("qty"),
            message=message,
        )

        nxt: Dict[str, Any] = dict(raw)
        nxt["product_id"] = pid
        if variant_key:
            nxt["variant"] = variant_key
        if specs_key:
            nxt["specs"] = specs_key
            nxt["spec"] = specs_key
        else:
            if specs_hint:
                if weight_status in {"AMBIGU", "INCOMPATIBLE"}:
                    nxt["specs"] = ""
                    nxt["spec"] = ""
                else:
                    nxt["specs"] = specs_hint
        if unit_key:
            nxt["unit"] = unit_key
        if qty_i is not None:
            nxt["qty"] = qty_i
        out.append(nxt)

    return out
