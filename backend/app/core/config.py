"""
Central configuration — all env vars in one place.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── LLM ──────────────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = "gsk_your_groq_key_here"
    OPENAI_BASE_URL: str = "https://api.groq.com/openai/v1"
    LLM_MODEL: str = "llama3-8b-8192"
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 1024

    # ── Embedding ─────────────────────────────────────────────────────────────
    EMBED_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ── ChromaDB ──────────────────────────────────────────────────────────────
    CHROMA_PATH: str = "./chroma_db"
    CHROMA_COLLECTION: str = "docsai"

    # ── RAG ───────────────────────────────────────────────────────────────────
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    TOP_K: int = 5
    MAX_HISTORY_TURNS: int = 6

    # ── Upload ────────────────────────────────────────────────────────────────
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_MB: int = 20

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:80", "http://localhost"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
