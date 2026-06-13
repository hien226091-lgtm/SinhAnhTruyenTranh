"""File upload and download endpoints."""

from __future__ import annotations

from pathlib import Path
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile, Depends, status
from fastapi.responses import FileResponse

from api_base.app.config import CONFIG
from api_base.app.models.schemas import UploadResponse
from api_base.app.utils.helpers import ensure_dir, resolve_under, sanitize_filename
from api_base.app.security.deps import get_current_user
from api_base.app.models.schema_db import User


router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
) -> UploadResponse:
    """Upload a file to the temporary upload directory."""
    ensure_dir(CONFIG.upload_temp_dir)

    safe_name = sanitize_filename(file.filename or "upload.bin")
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    target_path = resolve_under(CONFIG.upload_temp_dir, unique_name)

    try:
        content = await file.read()
        target_path.write_bytes(content)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {exc}",
        ) from exc

    return UploadResponse(filename=unique_name, url=f"/api/files/{unique_name}")


@router.get("/{filename}")
def download_file(filename: str) -> FileResponse:
    """Download a file from the temporary upload directory."""
    try:
        file_path = resolve_under(CONFIG.upload_temp_dir, filename)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    return FileResponse(path=file_path, filename=Path(filename).name)
