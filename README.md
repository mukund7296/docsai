# docsai
# DocsAI — Chat With Your Documents

> Upload PDFs or text files. Ask questions. Get answers grounded in your documents.

---

## What It Does

```
You upload a PDF  →  DocsAI reads & indexes it  →  You ask questions  →  Get cited answers
```

---

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| LLM | Groq (llama3-8b) | Free, fast, OpenAI-compatible |
| Embeddings | all-MiniLM-L6-v2 | Local, no API cost |
| Vector DB | ChromaDB | No account needed, runs in Docker |
| Backend | FastAPI | Fast, typed, auto-docs |
| Frontend | React + Tailwind | Simple SPA |
| Infra | Docker Compose | One command to run everything |

---

## Architecture

```
Browser (port 3000)
        │
        │ HTTP
        ▼
   nginx proxy
        │
        ├──── /documents ──────────────────────────────────┐
        │                                                   │
        └──── /chat ────────────────────────────────────┐   │
                                                        │   │
                                    FastAPI (port 8000) │   │
                                                        │   │
                              ┌─── RAG Pipeline ────────┘   │
                              │   1. Embed question         │
                              │   2. Search ChromaDB        │
                              │   3. Build prompt           │
                              │   4. Call Groq API          │
                              │   5. Return answer+sources  │
                              │                             │
                              └─── Ingestion Pipeline ──────┘
                                  1. Extract text (PDF/TXT)
                                  2. Chunk (512 chars, 64 overlap)
                                  3. Embed (all-MiniLM-L6-v2)
                                  4. Store in ChromaDB
```

### RAG Flow

```
User question
      │
      ▼
Embed question
      │
      ▼
ChromaDB similarity search → top 5 chunks
      │
      ▼
Build prompt: [System] + [History] + [Context] + [Question]
      │
      ▼
Groq API (llama3-8b)
      │
      ▼
Answer + Source citations → UI
```

---

## Quick Start — Docker (Recommended)

**You need:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) + a free [Groq API key](https://console.groq.com)

```bash
# 1. Clone
git clone https://github.com/mukund7296/docsai.git
cd docsai

# 2. Add your API key
cp backend/.env.example backend/.env
# Open backend/.env and set: OPENAI_API_KEY=gsk_your_key_here

# 3. Run
docker compose up --build

# 4. Open http://localhost:3000
```

**Get a free Groq key (60 seconds):**
1. Go to [console.groq.com](https://console.groq.com) → sign up free
2. Click **API Keys → Create API Key**
3. Copy the `gsk_...` key into `backend/.env`

---

## Local Dev (No Docker)

### Terminal 1 — Backend

```bash
cd backend
python3 -m venv venv && source venv/bin/activate   # Macos  OR Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                               # add your Groq key
uvicorn app.main:app --reload --port 8000
```

Check it works: [http://localhost:8000/health](http://localhost:8000/health) → `{"status":"ok"}`
# output 
<img width="607" height="283" alt="image" src="https://github.com/user-attachments/assets/a1ec3105-8df5-425e-91a1-27a434ccb702" />


### Terminal 2 — Frontend

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```
# output 
<img width="1279" height="798" alt="image" src="https://github.com/user-attachments/assets/4b17e0ef-6a18-47f0-9411-9ae35e8dcb9b" />


---

## Running Tests

```bash
cd backend
pytest tests/ -v
```
# output 

<img width="690" height="345" alt="image" src="https://github.com/user-attachments/assets/54b64419-cc6e-4256-8c78-fb15697846eb" />

Tests cover chunking logic and prompt assembly — no live LLM or DB needed.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/documents/upload` | Upload & index a file |
| GET | `/documents/` | List all documents |
| DELETE | `/documents/{filename}` | Remove a document |
| POST | `/chat/` | Ask a question |

Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Before chunking and upload document 

<img width="1276" height="775" alt="image" src="https://github.com/user-attachments/assets/08ac1b8b-c9b2-4265-9c63-bbd853f918b3" />

# PDF 1 — Attention Is All You Need (AI Research Paper)

**Link:** https://arxiv.org/pdf/1706.03762

## Key Questions for Understanding

1. What problem does the Transformer architecture solve?
2. How does multi-head attention work internally?
3. What BLEU scores were achieved on WMT translation benchmarks?
4. Why did the authors remove recurrence (RNNs) from the model?

## After chunking and upload document and chunks count.
<img width="1266" height="760" alt="image" src="https://github.com/user-attachments/assets/d1fa7314-d2ec-49cf-82da-8d0ac198430f" />

---

## Key Decisions

**Groq over OpenAI** — free tier, same API format, one-line swap if needed

**ChromaDB over Pinecone** — no cloud account, persists to Docker volume, zero cost

**Local embeddings** — model downloaded at Docker build time, no per-call cost, works offline

**Sentence-aware chunking** — splits on sentence boundaries (not raw characters) for cleaner embeddings

**Strict system prompt** — the main guardrail; forces the LLM to cite sources and refuse to answer from outside the documents

---

## Productionising This (AWS / GCP / Azure)

```
Current (Docker)          →    Production
──────────────────────────────────────────────────
docker compose            →    ECS Fargate / Cloud Run
ChromaDB on disk          →    Pinecone or pgvector (RDS)
Local file upload         →    S3 + presigned URLs
nginx                     →    ALB + CloudFront CDN
.env file                 →    AWS Secrets Manager
docker volume             →    EFS (persistent storage)
pytest CI                 →    GitHub Actions → ECR → ECS deploy
```

Additional changes needed:
- **Auth** — JWT/OAuth2, per-user namespaced collections
- **Async ingestion** — background tasks + WebSocket progress (large PDFs block)
- **Observability** — OpenTelemetry tracing, structured logging, latency metrics
- **Rate limiting** — per-user upload + chat limits

---

## 2nd use case explained 

# 📊 ACME Corporation — Annual Report 2024 Project

This project contains a sample dataset (`sample.txt`) and a set of questions to test understanding of the data.

---

## 📥 1. Sample Data File (sample.txt)

Copy the following content into a file named **`sample.txt`**:

```text
ACME Corporation — Annual Report 2024

CEO: John Smith  
Revenue: $5.2 billion (up 18% from last year)  
Employees: 15,000 worldwide  
Headquarters: New York, USA  

Products:
- Cloud software: $2.8 billion revenue
- Hardware devices: $1.6 billion revenue  
- Consulting services: $0.8 billion revenue  

Key Achievements:
- Launched AI product line in March 2024
- Expanded to 12 new countries
- Won "Best Tech Company" award in June 2024  

Risks:
- Rising competition from Asian markets
- Cybersecurity threats increasing
- Supply chain delays in hardware division
```

```
| No. | Question                               | Answer                                   |
|-----|----------------------------------------|------------------------------------------|
| 1   | Who is the CEO?                        | John Smith                               |
| 2   | What was the total revenue?            | $5.2 billion, up 18%                     |
| 3   | What are the three products?           | Cloud, Hardware, Consulting              |
| 4   | What risks does the company face?      | Competition, cybersecurity, supply chain |
| 5   | When was the AI product launched?      | March 2024                               |
| 6   | What is the consulting revenue?        | $0.8 billion                             |
| 7   | How many countries did they expand to? | 12 new countries                         |
| 8   | What award did they win?               | Best Tech Company, June 2024             |

```
# Output 
<img width="1279" height="773" alt="image" src="https://github.com/user-attachments/assets/18bcbf48-30cc-47f1-8bdf-131948b88eb7" />

# terminal flow
<img width="1051" height="421" alt="image" src="https://github.com/user-attachments/assets/f9363003-4446-45b9-98b6-a150789c919a" />

