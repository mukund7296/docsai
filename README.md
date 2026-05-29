# DocsAI — Chat With Your Documents

> Upload PDFs and text files. Ask questions. Get answers grounded in your documents — not hallucinated facts.

![DocsAI Screenshot](docs/screenshot.png)

---

## Quick Start (Docker — 3 commands)

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) · A free [Groq API key](https://console.groq.com)

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/docsai.git && cd docsai

# 2. Set your API key
cp backend/.env.example backend/.env
# Open backend/.env and replace: OPENAI_API_KEY=gsk_your_groq_key_here

# 3. Run
docker compose up --build
```

Open **http://localhost:3000** — that's it. No local Python or Node setup needed.

> **Get a free Groq key in 60 seconds:**
> 1. Go to [console.groq.com](https://console.groq.com)
> 2. Sign up with GitHub or Google (free)
> 3. Click **API Keys → Create API Key**
> 4. Copy the `gsk_...` key into `backend/.env`

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Browser (port 3000)                      │
│              React + Tailwind + Vite                         │
│              served by nginx                                 │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP  (nginx proxy → backend)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Backend  (port 8000)                    │
│                                                             │
│   POST /documents/upload    POST /chat/    GET /health      │
│          │                       │                          │
│          ▼                       ▼                          │
│   ┌─────────────┐      ┌──────────────────────┐            │
│   │  Ingestion  │      │    RAG Pipeline       │            │
│   │  Service    │      │                       │            │
│   │             │      │  1. Embed query       │            │
│   │ 1. Extract  │      │  2. Similarity search │            │
│   │ 2. Chunk    │      │  3. Build context     │            │
│   │ 3. Embed    │      │  4. Call LLM          │            │
│   │ 4. Upsert   │      │  5. Return + sources  │            │
│   └──────┬──────┘      └──────────┬────────────┘           │
│          │                        │                         │
│          ▼                        ▼                         │
│   ┌─────────────┐         ┌──────────────┐                 │
│   │  ChromaDB   │         │  Groq API    │                 │
│   │ (persistent │         │ llama3-8b    │                 │
│   │  local vec) │         │ (free tier)  │                 │
│   └─────────────┘         └──────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

### RAG Flow

```
User question
     │
     ▼
Embed with all-MiniLM-L6-v2
     │
     ▼
ChromaDB cosine similarity search → top-5 chunks
     │
     ▼
Filter low-relevance chunks (score < 0.25)
     │
     ▼
Build prompt: [System] + [Chat History (last 6 turns)] + [Context] + [Question]
     │
     ▼
Groq API — llama3-8b-8192
     │
     ▼
Answer + Source Citations → Frontend
```

---

## Local Dev (without Docker)

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                               # add your Groq key
uvicorn app.main:app --reload --port 8000
# → http://localhost:8000/health
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

---

## Running Tests

```bash
cd backend
pytest tests/ -v
```

Tests cover chunking logic and prompt assembly — the pure-logic parts that don't need a live LLM or DB.

---

## Project Structure

```
docsai/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI routers (chat, documents, health)
│   │   ├── core/           # Config, vector store singleton
│   │   ├── models/         # Pydantic schemas
│   │   └── services/       # Ingestion pipeline, RAG pipeline
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.tsx         # Main UI
│   │   └── lib/api.ts      # Typed API client
│   ├── nginx.conf
│   └── Dockerfile
├── docker-compose.yml
└── .github/workflows/ci.yml
```

---

## RAG / LLM Decisions

### LLM: Groq + llama3-8b-8192
**Why Groq?** It's free, fast (~300 tokens/sec), and uses the same OpenAI-compatible API format — so switching to GPT-4o, Claude, or any other provider is a one-line config change. No credit card required.

**Why llama3-8b over larger models?** For RAG tasks where context is explicitly provided, 8B models perform very well. The bottleneck is retrieval quality, not model size.

### Embedding Model: all-MiniLM-L6-v2
**Why?** Runs locally (no API cost), ~80MB, fast (CPU-friendly), and genuinely good for semantic similarity on documents. I considered `text-embedding-3-small` (OpenAI) but the local model avoids per-embedding API costs and latency.

### Vector DB: ChromaDB (local persistent)
**Why not Pinecone/Weaviate?** They're great for production, but require accounts, API keys, and network calls. ChromaDB runs embedded in the same process, persists to disk via Docker volume, and has a clean Python API. The trade-off: it doesn't scale horizontally, but that's fine for this scope.

**What I'd use in production:** Pinecone (managed, serverless) or pgvector (if already on Postgres).

### Chunking Strategy
Sentence-aware chunking at 512 chars with 64-char overlap. I avoided pure character splits because they break sentences mid-way, confusing both embeddings and the LLM. A more sophisticated approach would be semantic chunking (splitting on topic shifts), but that requires an additional embedding pass.

### Prompt Design
Three-layer prompt:
1. **System:** Strict grounding instructions — answer only from context, always cite sources
2. **History:** Last 6 conversation turns for follow-up question handling
3. **User:** Context passages (labelled by source + chunk index) + question

The strict system prompt is the key guardrail — without it, LLMs confidently hallucinate answers not in the documents.

### Context Management
- History trimmed to last 12 messages (6 turns) to fit in context window
- Low-relevance chunks filtered out (cosine similarity < 0.25)
- Context block labelled with `[Source: filename, chunk N]` so the LLM can cite correctly

---

## What Would Be Required to Productionise

### Infrastructure (AWS example)
```
Current (Docker)          →    Production (AWS)
─────────────────────────────────────────────────
docker compose             →    ECS Fargate (auto-scaling)
ChromaDB on disk           →    Pinecone or pgvector (RDS)
Local file upload          →    S3 + presigned URLs
nginx proxy                →    ALB + CloudFront CDN
docker volume              →    EFS for persistent storage
.env file                  →    AWS Secrets Manager
pytest CI                  →    GitHub Actions → ECR push → ECS deploy
```

Same architecture applies to GCP (Cloud Run + AlloyDB) or Azure (Container Apps + Azure AI Search).

### What Else Would Change
- **Auth:** Add JWT/OAuth2 (FastAPI has built-in OAuth2 support). Multi-tenant: namespace ChromaDB collections by user ID
- **Async ingestion:** Large PDFs can take 10–30s to embed. Move to background task (FastAPI BackgroundTasks or Celery) with WebSocket progress updates
- **Observability:** Add OpenTelemetry tracing, structured logging (structlog), and a metrics endpoint. Track retrieval latency, LLM latency, and answer quality scores
- **Eval harness:** A test set of (document, question, expected_answer) pairs to catch regressions when changing embedding models or chunking strategies
- **Re-ranking:** After vector search, add a cross-encoder re-ranker (e.g., `cross-encoder/ms-marco-MiniLM-L-6-v2`) for better precision
- **Hybrid search:** BM25 (keyword) + vector search combined for better recall on exact terms
- **Rate limiting:** Per-user limits on upload size and chat requests
- **Persistent doc registry:** SQLite/Postgres to track metadata (upload time, user, processing status) separately from the vector store

---

## Key Technical Decisions & Why

| Decision | Alternative Considered | Reason for Choice |
|---|---|---|
| Groq free tier (llama3-8b) | OpenAI GPT-4o | No credit card, same API format, fast enough for RAG |
| ChromaDB embedded | Pinecone, Weaviate | No account setup, runs in Docker, zero cost |
| all-MiniLM-L6-v2 local | OpenAI text-embedding-3-small | No per-call cost, works offline, good quality |
| FastAPI | Flask, Django | Async-native, Pydantic validation, auto-docs at /docs |
| Vite + React | Next.js, CRA | Fastest dev loop, simple SPA sufficient here |
| Sentence-aware chunking | Fixed-size char split | Less sentence fragmentation, better embedding quality |
| Docker Compose | Kubernetes, bare metal | Right tool for the scope — one command, reproducible |

---

## Engineering Standards Applied

**Applied:**
- Pydantic models for all API inputs/outputs (type safety + auto-validation)
- Dependency injection via `lru_cache` singletons (no global state mutation)
- Structured logging with log levels throughout
- `.env.example` so secrets are never committed
- Docker health checks so the frontend waits for a healthy backend
- Idempotent ingestion — re-uploading the same file replaces old chunks cleanly
- Unit tests for pure-logic functions (no mocking LLMs)
- CI pipeline (GitHub Actions)

**Consciously skipped (would add with more time):**
- Integration tests hitting a live test ChromaDB instance
- Pre-commit hooks (black, ruff, mypy)
- API versioning (`/v1/...`)
- Rate limiting middleware
- Comprehensive error boundary in the React frontend

---

## How I Used AI Tools

I used Claude as a coding assistant throughout. My approach:

**Where AI accelerated me:**
- Boilerplate (FastAPI router structure, Pydantic schemas, Dockerfile syntax) — I described what I wanted and reviewed/edited the output
- React component structure — the UI logic is mine, AI helped with Tailwind class combinations
- Writing out repetitive test cases once I'd established the pattern

**Where I wrote everything myself:**
- Architecture decisions — I decided on Groq over OpenAI, ChromaDB over Pinecone, local embeddings over API embeddings. The README reflects my reasoning, not AI reasoning
- The RAG prompt — system prompt wording matters enormously for grounding behaviour; I iterated on this manually
- Chunking strategy — I evaluated the trade-offs myself and chose sentence-aware splitting
- This README — I wrote this to explain my actual thinking. The only AI involvement was spell-check

**My do's and don'ts with AI coding tools:**
- ✅ Use AI for boilerplate and syntax you know but don't want to type
- ✅ Use AI to generate a starting structure, then rework it to match your standards
- ✅ Use AI to explain unfamiliar library APIs (e.g., ChromaDB's `query()` parameters)
- ❌ Don't let AI pick your stack — it'll pick whatever sounds popular, not what fits your constraints
- ❌ Don't commit AI-generated code without reading it line by line — it hallucinates APIs
- ❌ Don't use AI-generated READMEs for anything that requires your actual thought process

---

## What I'd Do Differently with More Time

1. **Async ingestion with progress** — Large files block the request. Background task + WebSocket progress bar
2. **Semantic chunking** — Split on topic shifts, not just character count
3. **Hybrid search** — BM25 + vector for better exact-term recall
4. **Cross-encoder re-ranking** — A second pass after retrieval for precision
5. **Eval harness** — Automated quality regression tests against ground-truth Q&A pairs
6. **Persistent doc registry** — SQLite so documents survive container rebuilds with metadata intact
7. **Multi-file upload** — Batch upload via drag-and-drop (the UI supports it, the API processes sequentially)

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check + stats |
| POST | `/documents/upload` | Upload and ingest a file |
| GET | `/documents/` | List all indexed documents |
| DELETE | `/documents/{filename}` | Remove a document |
| POST | `/chat/` | Ask a question (RAG) |

Interactive docs: **http://localhost:8000/docs**
