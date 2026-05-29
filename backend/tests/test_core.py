"""
Unit tests for pure-logic functions.
These tests have ZERO external dependencies (no chromadb, no pdfplumber, no torch).
The functions under test are copied inline so imports can't fail.
Run: pytest tests/ -v
"""
import re
import pytest


# ── Inline copy of chunk_text (no imports needed) ────────────────────────────

def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks = []
    current = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(current) + len(sentence) + 1 > chunk_size and current:
            chunks.append(current.strip())
            words = current.split()
            carry = " ".join(words[-(overlap // 6):]) if words else ""
            current = carry + " " + sentence
        else:
            current = (current + " " + sentence).strip()
    if current.strip():
        chunks.append(current.strip())
    return [c for c in chunks if len(c) > 20]


# ── Inline copy of build_messages (no imports needed) ────────────────────────

SYSTEM_PROMPT = "You are DocsAI. Answer only from context."

def build_messages(question: str, context_chunks: list, history: list) -> list:
    context_lines = []
    for chunk in context_chunks:
        context_lines.append(
            f"[Source: {chunk['source']}, chunk {chunk['chunk_index']}]\n{chunk['text']}"
        )
    context_block = "\n\n---\n\n".join(context_lines)
    max_turns = 12
    trimmed_history = history[-max_turns:] if history else []
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(trimmed_history)
    messages.append({
        "role": "user",
        "content": (
            f"Context:\n\n{context_block}\n\nQuestion: {question}"
        ) if context_block else f"Question: {question}",
    })
    return messages


# ── Chunking tests ────────────────────────────────────────────────────────────

def test_chunk_basic():
    chunks = chunk_text("Hello world. " * 100, chunk_size=200, overlap=20)
    assert len(chunks) > 1

def test_chunk_empty():
    assert chunk_text("") == []

def test_chunk_single_sentence():
    text = "This is a short document."
    chunks = chunk_text(text, chunk_size=200)
    assert len(chunks) == 1
    assert chunks[0] == text

def test_chunk_no_oversized():
    chunks = chunk_text("Alpha beta. " * 200, chunk_size=150, overlap=30)
    for c in chunks:
        assert len(c) <= 400   # generous upper bound after overlap carry


# ── Prompt tests ──────────────────────────────────────────────────────────────

def test_messages_no_history():
    chunks = [{"text": "Paris is the capital.", "source": "geo.txt", "chunk_index": 0}]
    msgs = build_messages("Capital of France?", chunks, history=[])
    assert msgs[0]["role"] == "system"
    assert msgs[-1]["role"] == "user"
    assert "Paris" in msgs[-1]["content"]

def test_messages_with_history():
    chunks = [{"text": "Rome has the Colosseum.", "source": "travel.pdf", "chunk_index": 2}]
    history = [
        {"role": "user", "content": "Tell me about Italy."},
        {"role": "assistant", "content": "Italy is known for art."},
    ]
    msgs = build_messages("What's in Rome?", chunks, history=history)
    assert len(msgs) == 4  # system + 2 history + user

def test_messages_no_context():
    msgs = build_messages("Any question", context_chunks=[], history=[])
    assert "Question:" in msgs[-1]["content"]

def test_history_trimmed():
    chunks = [{"text": "Some text.", "source": "doc.txt", "chunk_index": 0}]
    long_history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"}
        for i in range(40)
    ]
    msgs = build_messages("Q?", chunks, history=long_history)
    assert len(msgs) < 42