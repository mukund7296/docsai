"""
Ingestion pipeline:
  1. Extract text (PDF via pdfplumber, TXT/MD plain)
  2. Chunk with overlap
  3. Embed via sentence-transformers
  4. Upsert into ChromaDB
"""
import hashlib
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Iterator

from app.core.config import settings
from app.core.vectorstore import get_vectorstore, embed_texts

logger = logging.getLogger(__name__)


# ── Text extraction ──────────────────────────────────────────────────────────

def extract_text_from_pdf(path: str) -> str:
    import pdfplumber  # lazy import — only needed at runtime, not for tests
    pages = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            pages.append(f"[Page {i + 1}]\n{text}")
    return "\n\n".join(pages)


def extract_text_from_file(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(path)
    # txt, md, csv, etc.
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


# ── Chunking ─────────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> list[str]:
    """
    Simple sentence-aware chunker.
    Splits on sentence boundaries, accumulates up to chunk_size chars,
    then starts a new chunk with `overlap` chars carried over.
    """
    chunk_size = chunk_size or settings.CHUNK_SIZE
    overlap = overlap or settings.CHUNK_OVERLAP

    # Split into sentences (rough but effective)
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())

    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(current) + len(sentence) + 1 > chunk_size and current:
            chunks.append(current.strip())
            # carry-over overlap
            words = current.split()
            carry = " ".join(words[-(overlap // 6):]) if words else ""
            current = carry + " " + sentence
        else:
            current = (current + " " + sentence).strip()

    if current.strip():
        chunks.append(current.strip())

    return [c for c in chunks if len(c) > 20]  # drop micro-chunks


# ── Ingestion ─────────────────────────────────────────────────────────────────

def file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()[:16]


def ingest_file(file_path: str, filename: str) -> dict:
    """
    Full pipeline: extract → chunk → embed → upsert.
    Returns stats dict.
    """
    logger.info("Ingesting: %s", filename)

    text = extract_text_from_file(file_path)
    if not text.strip():
        raise ValueError(f"Could not extract any text from {filename}")

    chunks = chunk_text(text)
    logger.info("  %d chunks from %s", len(chunks), filename)

    # Embed in one batch
    embeddings = embed_texts(chunks)

    # Build IDs + metadata
    fhash = file_hash(file_path)
    ids = [f"{fhash}_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "source": filename,
            "chunk_index": i,
            "file_hash": fhash,
        }
        for i in range(len(chunks))
    ]

    collection, _ = get_vectorstore()

    # Delete existing chunks for this file (re-upload idempotency)
    existing = collection.get(where={"file_hash": fhash})
    if existing["ids"]:
        collection.delete(ids=existing["ids"])
        logger.info("  Replaced %d old chunks for %s", len(existing["ids"]), filename)

    # Upsert new chunks
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )

    return {
        "filename": filename,
        "chunks": len(chunks),
        "file_hash": fhash,
        "chars": len(text),
    }


def delete_document(filename: str) -> int:
    """Remove all chunks belonging to a document. Returns count deleted."""
    collection, _ = get_vectorstore()
    existing = collection.get(where={"source": filename})
    if not existing["ids"]:
        return 0
    collection.delete(ids=existing["ids"])
    return len(existing["ids"])


def list_documents() -> list[dict]:
    """Return one summary row per unique source file."""
    collection, _ = get_vectorstore()
    all_meta = collection.get(include=["metadatas"])["metadatas"] or []

    seen: dict[str, dict] = {}
    for m in all_meta:
        src = m.get("source", "unknown")
        if src not in seen:
            seen[src] = {"filename": src, "chunks": 0, "file_hash": m.get("file_hash", "")}
        seen[src]["chunks"] += 1

    return list(seen.values())