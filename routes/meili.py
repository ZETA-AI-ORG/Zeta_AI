from fastapi import APIRouter, HTTPException
import os
import meilisearch

router = APIRouter()

@router.get("/meili/indexes")
async def list_meili_indexes():
    """Expose tous les indexes Meilisearch pour l'UI"""
    try:
        meili_url = os.environ.get("MEILI_URL", "http://127.0.0.1:7700")
        meili_key = os.environ.get("MEILI_API_KEY") or os.environ.get("MEILI_MASTER_KEY", "")
        client = meilisearch.Client(meili_url, meili_key)
        indexes = client.get_indexes().get("results", [])
        return {"indexes": indexes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/meili/index/{index_uid}/documents")
async def get_meili_documents(index_uid: str, q: str = "", offset: int = 0, limit: int = 100):
    """Liste ou recherche les documents d'un index Meilisearch"""
    try:
        meili_url = os.environ.get("MEILI_URL", "http://127.0.0.1:7700")
        meili_key = os.environ.get("MEILI_API_KEY") or os.environ.get("MEILI_MASTER_KEY", "")
        client = meilisearch.Client(meili_url, meili_key)
        index = client.index(index_uid)
        if q:
            results = index.search(q, {"offset": offset, "limit": limit})
            docs = results.get("hits", [])
        else:
            docs = index.get_documents({"offset": offset, "limit": limit})
        return {"documents": docs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/meili/index/{index_uid}/documents")
async def delete_meili_documents(index_uid: str, body: dict):
    """Supprime une liste de documents (par id) d'un index Meilisearch"""
    try:
        ids = body.get("ids", [])
        if not ids:
            raise HTTPException(status_code=400, detail="Pas d'ids fournis")
        meili_url = os.environ.get("MEILI_URL", "http://127.0.0.1:7700")
        meili_key = os.environ.get("MEILI_API_KEY") or os.environ.get("MEILI_MASTER_KEY", "")
        client = meilisearch.Client(meili_url, meili_key)
        index = client.index(index_uid)
        index.delete_documents(ids)
        return {"success": True, "deleted": len(ids)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/meili/index/{index_uid}")
async def delete_meili_index(index_uid: str):
    """Supprime un index Meilisearch complet"""
    try:
        meili_url = os.environ.get("MEILI_URL", "http://127.0.0.1:7700")
        meili_key = os.environ.get("MEILI_API_KEY") or os.environ.get("MEILI_MASTER_KEY", "")
        client = meilisearch.Client(meili_url, meili_key)
        client.delete_index(index_uid)
        return {"success": True, "deleted_index": index_uid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
