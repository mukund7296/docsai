"""
/documents endpoints:
  POST /documents/upload   — ingest a file
  GET  /documents/         — list all documents
  DELETE /documents/{name} — remove a document
"""
import os
import shutil
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import settings
from app.models.schemas import DeleteResponse, DocumentInfo, UploadResponse
from app.services.ingestion import delete_document, ingest_file, list_documents

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".csv"}
MAX_BYTES = settings.MAX_UPLOAD_MB * 1024 * 1024


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Save temp file
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    tmp_path = os.path.join(settings.UPLOAD_DIR, file.filename)

    contents = await file.read()
    if len(contents) > MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max {settings.MAX_UPLOAD_MB} MB.",
        )

    with open(tmp_path, "wb") as f:
        f.write(contents)

    try:
        stats = ingest_file(tmp_path, file.filename)
    except Exception as e:
        os.remove(tmp_path)
        raise HTTPException(status_code=422, detail=str(e))

    return UploadResponse(**stats)


@router.get("/", response_model=list[DocumentInfo])
def get_documents():
    return list_documents()


@router.delete("/{filename}", response_model=DeleteResponse)
def remove_document(filename: str):
    deleted = delete_document(filename)
    if deleted == 0:
        raise HTTPException(status_code=404, detail=f"Document '{filename}' not found.")
    return DeleteResponse(
        filename=filename,
        chunks_deleted=deleted,
        message=f"Deleted {deleted} chunks",
    )
