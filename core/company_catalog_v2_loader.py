import os
import json
import re
import time
from typing import Any, Dict, Optional, Tuple


import logging


logger = logging.getLogger(__name__)


def _norm_product_id(v: str) -> str:
    try:
        import unicodedata

        t = str(v or "").strip()
        t = unicodedata.normalize("NFKD", t)
        t = "".join(ch for ch in t if not unicodedata.combining(ch))
        t = re.sub(r"\s+", " ", t).strip()
        return t.upper()
    except Exception:
        return str(v or "").strip().upper()


_CACHE: Dict[str, Tuple[float, Optional[Dict[str, Any]]]] = {}


def invalidate_company_catalog_v2_cache(company_id: Optional[str] = None) -> None:
    if company_id is None:
        _CACHE.clear()
        return
    cid = str(company_id).strip()

    try:
        debug_logs = (os.getenv("CATALOG_V2_DEBUG_LOGS", "false") or "").strip().lower() in {"1", "true", "yes", "y", "on"}
    except Exception:
        debug_logs = False
    if cid:
        _CACHE.pop(cid, None)


def _get_local_catalog_path(company_id: str) -> Optional[str]:
    if not company_id or not str(company_id).strip():
        return None

    base_dir = os.getenv("CATALOG_V2_LOCAL_DIR") or "/data/catalogs"
    try:
        base_dir = str(base_dir).strip() or "/data/catalogs"
    except Exception:
        base_dir = "/data/catalogs"

    safe_id = re.sub(r"[^a-zA-Z0-9\-_]", "_", str(company_id).strip())
    if not safe_id:
        return None
    return os.path.join(base_dir, f"{safe_id}.json")


def _load_catalog_from_local_file(company_id: str) -> Optional[Dict[str, Any]]:
    path = _get_local_catalog_path(company_id)
    if not path or not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)

        if isinstance(obj, dict) and isinstance(obj.get("catalog"), dict):
            return obj.get("catalog")
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def get_company_catalog_v2_container(company_id: str) -> Optional[Dict[str, Any]]:
    """Returns the stored catalog dict (container or mono-product).

    Local file format:
    - wrapper: { company_id, ..., catalog: <dict> }
    - or direct dict
    """

    if not company_id or not str(company_id).strip():
        return None
    try:
        return get_company_catalog_v2(str(company_id).strip())
    except Exception:
        return None


def get_company_product_catalog_v2(company_id: str, product_id: str) -> Optional[Dict[str, Any]]:
    """Select a mono-product catalog_v2 from a multi-product container.

    - If storage is already mono-product, returns it as-is.
    - If storage is container with products[], selects by product_id (normalized).
    """

    cid = str(company_id or "").strip()
    if not cid:
        return None

    container = get_company_catalog_v2_container(cid)
    if not isinstance(container, dict):
        return None

    plist = container.get("products")
    if not isinstance(plist, list):
        return container

    pid = _norm_product_id(str(product_id or ""))
    if not pid:
        return None

    for p in plist:
        if not isinstance(p, dict):
            continue
        ppid = _norm_product_id(str(p.get("product_id") or p.get("product_name") or ""))
        if ppid and ppid == pid:
            cat = p.get("catalog_v2")
            return cat if isinstance(cat, dict) else None
    return None


def get_company_catalog_v2(company_id: str) -> Optional[Dict[str, Any]]:
    """Synchronous helper used by the price calculator.

    Fetches the latest active catalog for a company from Supabase.
    Returns the catalog JSON dict or None.
    """

    if not company_id or not str(company_id).strip():
        return None

    cid = str(company_id).strip()

    try:
        debug_logs = (os.getenv("CATALOG_V2_DEBUG_LOGS", "false") or "").strip().lower() in {"1", "true", "yes", "y", "on"}
    except Exception:
        debug_logs = False

    ttl_s = 60.0
    ttl_env = os.getenv("CATALOG_V2_CACHE_TTL_SECONDS")
    if ttl_env is not None:
        try:
            ttl_s = float(str(ttl_env).strip())
        except Exception:
            ttl_s = 60.0

    now = time.time()
    cached = _CACHE.get(cid)
    if cached:
        expires_at, val = cached
        if now < expires_at:
            return val

    local = _load_catalog_from_local_file(cid)
    if isinstance(local, dict):
        if debug_logs:
            try:
                logger.info(f"[CATALOG_LOAD] company={cid} source=local")
                plist0 = local.get("products") if isinstance(local, dict) else None
                if isinstance(plist0, list):
                    logger.info(f"[CATALOG_LOAD] products_count={len([p for p in plist0 if isinstance(p, dict)])}")
                    for p in plist0:
                        if not isinstance(p, dict):
                            continue
                        cat = p.get("catalog_v2") if isinstance(p.get("catalog_v2"), dict) else p
                        pid0 = str(p.get("product_id") or cat.get("product_id") or "").strip()
                        pname0 = str(p.get("product_name") or cat.get("product_name") or cat.get("name") or "").strip()
                        logger.info(f"  - product_id={pid0} name={pname0}")
                        logger.info(f"    technical_specs length: {len(str(cat.get('technical_specs') or ''))}")
                        logger.info(f"    sales_constraints length: {len(str(cat.get('sales_constraints') or ''))}")
                else:
                    logger.info("[CATALOG_LOAD] products_count=1 (mono)")
                    logger.info(f"  - product_id={str(local.get('product_id') or '').strip()} name={str(local.get('product_name') or local.get('name') or '').strip()}")
                    logger.info(f"    technical_specs length: {len(str(local.get('technical_specs') or ''))}")
                    logger.info(f"    sales_constraints length: {len(str(local.get('sales_constraints') or ''))}")
            except Exception:
                pass
        _CACHE[cid] = (now + ttl_s, local)
        return local

    try:
        from database.supabase_client import get_supabase_client

        client = get_supabase_client()
        resp = (
            client.table("company_catalogs_v2")
            .select("catalog")
            .eq("company_id", cid)
            .eq("is_active", True)
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        data = getattr(resp, "data", None) or []
        if not data:
            return None
        catalog = data[0].get("catalog")
        out = catalog if isinstance(catalog, dict) else None

        if debug_logs and isinstance(out, dict):
            try:
                logger.info(f"[CATALOG_LOAD] company={cid} source=supabase")
                plist1 = out.get("products") if isinstance(out, dict) else None
                if isinstance(plist1, list):
                    logger.info(f"[CATALOG_LOAD] products_count={len([p for p in plist1 if isinstance(p, dict)])}")
                    for p in plist1:
                        if not isinstance(p, dict):
                            continue
                        cat = p.get("catalog_v2") if isinstance(p.get("catalog_v2"), dict) else p
                        pid1 = str(p.get("product_id") or cat.get("product_id") or "").strip()
                        pname1 = str(p.get("product_name") or cat.get("product_name") or cat.get("name") or "").strip()
                        logger.info(f"  - product_id={pid1} name={pname1}")
                        logger.info(f"    technical_specs length: {len(str(cat.get('technical_specs') or ''))}")
                        logger.info(f"    sales_constraints length: {len(str(cat.get('sales_constraints') or ''))}")
                else:
                    logger.info("[CATALOG_LOAD] products_count=1 (mono)")
                    logger.info(f"  - product_id={str(out.get('product_id') or '').strip()} name={str(out.get('product_name') or out.get('name') or '').strip()}")
                    logger.info(f"    technical_specs length: {len(str(out.get('technical_specs') or ''))}")
                    logger.info(f"    sales_constraints length: {len(str(out.get('sales_constraints') or ''))}")
            except Exception:
                pass
        _CACHE[cid] = (now + ttl_s, out)
        return out
    except Exception:
        if debug_logs:
            try:
                logger.exception(f"[CATALOG_LOAD] company={cid} source=supabase error")
            except Exception:
                pass
        _CACHE[cid] = (now + ttl_s, None)
        return None
