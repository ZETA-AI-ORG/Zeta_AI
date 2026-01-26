import os
import time
from typing import Any, Dict, Optional, Tuple


_CACHE: Dict[str, Tuple[float, Optional[Dict[str, Any]]]] = {}


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
