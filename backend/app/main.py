"""
DocsAI — FastAPI backend entry point
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import documents, chat, health
from app.core.config import settings
from app.core.vectorstore import get_vectorstore

logging.basicConfig(level=logging.INFO, format="%(levelname)s │ %(name)s │ %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm up vector store on startup."""
    logger.info("Starting DocsAI backend …")
    get_vectorstore()          # initialise ChromaDB collection once
    logger.info("Vector store ready ✓")
    yield
    logger.info("Shutting down …")


app = FastAPI(
    title="DocsAI",
    description="RAG-based document Q&A API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
