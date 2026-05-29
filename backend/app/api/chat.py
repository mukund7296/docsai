"""
POST /chat/  — RAG question answering
"""
from fastapi import APIRouter, HTTPException

from app.models.schemas import ChatRequest, ChatResponse
from app.services.rag import answer_question

router = APIRouter()


@router.post("/", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    history = [{"role": m.role, "content": m.content} for m in req.history]

    result = answer_question(
        question=req.question,
        history=history,
        source_filter=req.source_filter,
    )
    return ChatResponse(**result)
