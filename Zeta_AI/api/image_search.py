from fastapi import APIRouter, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse
from PIL import Image
import os
import shutil
import requests
from io import BytesIO

from embedding_models import get_clip_image_embedding
from database.vector_store import search_images, recommend_images_by_id

router = APIRouter()

UPLOAD_DIR = "images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_image_embedding(image_path):
    # Conservation pour compatibilité des endpoints existants
    with open(image_path, "rb") as f:
        file_bytes = f.read()
    return get_clip_image_embedding(file_bytes)

@router.post("/api/image/index")
async def index_image_api(file: UploadFile, product_id: int, product_name: str):
    # Sauvegarde du fichier
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    # Génération embedding et indexation
    vec = get_image_embedding(file_path)
    # Ancien code utilisait Qdrant direct; conservé ici comme placeholder si nécessaire
    # Cette route n'est pas multi-tenant et peut être dépréciée.
    return {"status": "ok", "message": f"Image indexée pour {product_name}"}

@router.post("/api/image/search")
async def search_similar_api(file: UploadFile, top_k: int = 5):
    # Sauvegarde temporaire
    file_path = os.path.join(UPLOAD_DIR, "_search_" + file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    vec = get_image_embedding(file_path)
    # Ancienne recherche non multi-tenant (collection products) retirée
    results = []
    # Nettoyage fichier temporaire
    os.remove(file_path)
    return JSONResponse(content={"results": results})


# --- Nouveaux endpoints multi-tenant ---

@router.get("/images/similar-by-id")
async def similar_by_id(company_id: str = Query(...), id: str = Query(...), limit: int = Query(10, ge=1, le=100)):
    try:
        items = recommend_images_by_id(company_id=company_id, seed_id=id, limit=limit)
        return {"company_id": company_id, "items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Qdrant recommend error: {e}")


@router.get("/images/similar-by-url")
async def similar_by_url(company_id: str = Query(...), url: str = Query(...), limit: int = Query(10, ge=1, le=100)):
    try:
        # Télécharger l'image
        resp = requests.get(url, timeout=20)
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Impossible de télécharger l'image: HTTP {resp.status_code}")
        image_bytes = resp.content
        # Embedding OpenCLIP
        embedding = get_clip_image_embedding(image_bytes)
        # Recherche Qdrant dans la collection du tenant
        items = search_images(company_id=company_id, query_vector=embedding, limit=limit)
        return {"company_id": company_id, "items": items}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Qdrant search error: {e}")
