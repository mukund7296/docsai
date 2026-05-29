from fastapi import APIRouter
from app.core.vectorstore import get_vectorstore
from app.core.config import settings

router = APIRouter()


@router.get("/health")
def health():
    collection, _ = get_vectorstore()
    return {
        "status": "ok",
        "model": settings.LLM_MODEL,
        "embed_model": settings.EMBED_MODEL,
        "documents_indexed": collection.count(),
    }
