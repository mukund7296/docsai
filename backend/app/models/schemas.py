from pydantic import BaseModel, Field
from typing import Optional


class ChatMessage(BaseModel):
    role: str          # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list)
    source_filter: Optional[str] = None


class SourceCitation(BaseModel):
    file: str
    chunk: int
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceCitation]
    model: str
    chunks_used: int


class DocumentInfo(BaseModel):
    filename: str
    chunks: int
    file_hash: str


class UploadResponse(BaseModel):
    filename: str
    chunks: int
    file_hash: str
    chars: int
    message: str = "Document ingested successfully"


class DeleteResponse(BaseModel):
    filename: str
    chunks_deleted: int
    message: str
