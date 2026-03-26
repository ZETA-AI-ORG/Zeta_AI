import asyncio
import logging
import os

import requests
from fastapi import APIRouter, File, Response, UploadFile
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Upload Product Image"])


def _error_response(message: str, status_code: int) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})


@router.post("/upload-product-image")
async def upload_product_image(file: UploadFile = File(...)):
    worker_url = os.getenv("CF_IMAGE_UPLOAD_URL")
    upload_secret = os.getenv("CF_IMAGE_UPLOAD_SECRET")

    if not worker_url or not upload_secret:
        return _error_response("Upload proxy not configured", 500)

    if not file:
        return _error_response("No file provided", 400)

    content = await file.read()
    if not content:
        return _error_response("Empty file", 400)

    filename = file.filename or "upload.bin"
    content_type = file.content_type or "application/octet-stream"

    files = {
        "file": (filename, content, content_type),
    }
    headers = {
        "X-Upload-Token": upload_secret,
    }

    try:
        response = await asyncio.to_thread(
            requests.post,
            worker_url,
            files=files,
            headers=headers,
            timeout=90,
        )
    except requests.RequestException as exc:
        logger.exception("[upload-product-image] worker request failed")
        return _error_response(f"Upload worker request failed: {exc}", 502)

    return Response(
        content=response.text,
        status_code=response.status_code,
        media_type=response.headers.get("Content-Type") or "application/json",
    )
