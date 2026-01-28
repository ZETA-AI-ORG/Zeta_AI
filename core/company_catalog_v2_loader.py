import os
import json
import re
import time
from typing import Any, Dict, Optional, Tuple


_CACHE: Dict[str, Tuple[float, Optional[Dict[str, Any]]]] = {}


def invalidate_company_catalog_v2_cache(company_id: Optional[str] = None) -> None:
    if company_id is None:
        _CACHE.clear()
        return
    cid = str(company_id).strip()
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


def get_company_catalog_v2(company_id: str) -> Optional[Dict[str, Any]]:
    """Synchronous helper used by the price calculator.

    Fetches the latest active catalog for a company from Supabase.
    Returns the catalog JSON dict or None.
    """

    if not company_id or not str(company_id).strip():
        return None

    cid = str(company_id).strip()

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
        _CACHE[cid] = (now + ttl_s, out)
        return out
    except Exception:
        _CACHE[cid] = (now + ttl_s, None)
        return None
