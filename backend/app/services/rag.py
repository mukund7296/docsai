"""
RAG pipeline:
  1. Embed query
  2. Retrieve top-K chunks from ChromaDB
  3. Build prompt (system + history + context + question)
  4. Call LLM (Groq or any OpenAI-compatible endpoint)
  5. Return answer + source citations
"""
import logging
from openai import OpenAI

from app.core.config import settings
from app.core.vectorstore import get_vectorstore, embed_query

logger = logging.getLogger(__name__)


# ── LLM client ───────────────────────────────────────────────────────────────

def _get_llm_client() -> OpenAI:
    return OpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
    )


# ── Retrieval ─────────────────────────────────────────────────────────────────

def retrieve(query: str, top_k: int = None, source_filter: str = None) -> list[dict]:
    """
    Semantic search over ChromaDB.
    Returns list of {text, source, chunk_index, score}.
    """
    top_k = top_k or settings.TOP_K
    collection, _ = get_vectorstore()

    if collection.count() == 0:
        return []

    q_emb = embed_query(query)

    where = {"source": source_filter} if source_filter else None

    results = collection.query(
        query_embeddings=[q_emb],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
        where=where,
    )

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append({
            "text": doc,
            "source": meta.get("source", "unknown"),
            "chunk_index": meta.get("chunk_index", 0),
            "score": round(1 - dist, 4),   # cosine distance → similarity
        })

    # Filter low-relevance chunks
    chunks = [c for c in chunks if c["score"] > 0.25]
    return chunks


# ── Prompt assembly ───────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are DocsAI, a precise document analysis assistant.

Rules:
- Answer ONLY from the provided context passages.
- If the context doesn't contain the answer, say: "I couldn't find that in the uploaded documents."
- Be concise. Use bullet points for lists.
- Always cite which document (and page/chunk) your answer comes from using [Source: filename, chunk N].
- Never hallucinate facts not present in the context.
- Keep answers under 300 words unless the user asks for detail.
"""


def build_messages(
    question: str,
    context_chunks: list[dict],
    history: list[dict],
) -> list[dict]:
    """
    Assemble the messages array for the LLM.
    history format: [{"role": "user"|"assistant", "content": "..."}]
    """
    # Build context block
    context_lines = []
    for i, chunk in enumerate(context_chunks):
        context_lines.append(
            f"[Source: {chunk['source']}, chunk {chunk['chunk_index']}]\n{chunk['text']}"
        )
    context_block = "\n\n---\n\n".join(context_lines)

    # Trim history to last N turns
    max_turns = settings.MAX_HISTORY_TURNS * 2  # each turn = user+assistant
    trimmed_history = history[-max_turns:] if history else []

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(trimmed_history)
    messages.append({
        "role": "user",
        "content": (
            f"Context from documents:\n\n{context_block}\n\n"
            f"---\n\nQuestion: {question}"
        ) if context_block else f"Question: {question}",
    })
    return messages


# ── Answer generation ─────────────────────────────────────────────────────────

def answer_question(
    question: str,
    history: list[dict] | None = None,
    source_filter: str | None = None,
) -> dict:
    """
    Full RAG: retrieve → prompt → generate.
    Returns {answer, sources, model, chunks_used}.
    """
    history = history or []

    chunks = retrieve(question, source_filter=source_filter)
    logger.info("Retrieved %d chunks for query: %s", len(chunks), question[:60])

    if not chunks:
        return {
            "answer": "No documents have been uploaded yet, or no relevant content was found. Please upload some documents first.",
            "sources": [],
            "model": settings.LLM_MODEL,
            "chunks_used": 0,
        }

    messages = build_messages(question, chunks, history)

    client = _get_llm_client()
    response = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=messages,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
    )

    answer = response.choices[0].message.content.strip()

    # Deduplicate sources
    seen = set()
    sources = []
    for c in chunks:
        key = f"{c['source']}:{c['chunk_index']}"
        if key not in seen:
            seen.add(key)
            sources.append({"file": c["source"], "chunk": c["chunk_index"], "score": c["score"]})

    return {
        "answer": answer,
        "sources": sources,
        "model": settings.LLM_MODEL,
        "chunks_used": len(chunks),
    }
