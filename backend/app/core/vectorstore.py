"""
ChromaDB wrapper — single collection, sentence-transformer embeddings.
"""
import logging
from functools import lru_cache

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_embed_model() -> SentenceTransformer:
    logger.info("Loading embedding model: %s", settings.EMBED_MODEL)
    return SentenceTransformer(settings.EMBED_MODEL)


@lru_cache(maxsize=1)
def get_vectorstore():
    """Return (chroma_collection, embed_model) tuple — cached singleton."""
    client = chromadb.PersistentClient(
        path=settings.CHROMA_PATH,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    collection = client.get_or_create_collection(
        name=settings.CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )
    embed_model = _get_embed_model()
    logger.info("ChromaDB ready. Collection=%s  docs=%d", settings.CHROMA_COLLECTION, collection.count())
    return collection, embed_model


def embed_texts(texts: list[str]) -> list[list[float]]:
    _, model = get_vectorstore()
    return model.encode(texts, batch_size=32, show_progress_bar=False).tolist()


def embed_query(query: str) -> list[float]:
    _, model = get_vectorstore()
    return model.encode([query], show_progress_bar=False)[0].tolist()
