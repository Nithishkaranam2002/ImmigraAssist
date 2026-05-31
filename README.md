# ImmigraAssist 🏛️

> AI-powered immigration legal research assistant for law firms — from policies to precedents, instantly.

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB)](https://react.dev)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)](https://docker.com)
[![RAGAS](https://img.shields.io/badge/RAGAS-0.840-brightgreen)](https://docs.ragas.io)
[![LangSmith](https://img.shields.io/badge/LangSmith-Traced-orange)](https://smith.langchain.com)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## What is ImmigraAssist?

ImmigraAssist is a production-grade RAG (Retrieval-Augmented Generation) system built for immigration law firms. It reduces legal research time from hours to seconds by combining:

- **Real USCIS policy data** — scraped live from the USCIS Policy Manual using Playwright
- **BIA/AAO case precedents** — 244 Board of Immigration Appeals decisions indexed in Milvus
- **USCIS news & alerts** — latest policy updates, fee changes, and regulatory announcements
- **CourtListener live search** — real-time federal court case retrieval
- **GPT-4o answers** — structured legal research summaries with proper citations

---

## Evaluation Results

| Metric | Score | Method |
|---|---|---|
| Answer Relevancy | **0.840 / 1.000** | RAGAS + GPT-4o evaluator |
| Grade | **EXCELLENT** | 20 immigration law test cases |
| Observability | **LangSmith** | Full LLM pipeline tracing |

> Evaluated across 20 immigration law questions covering H1B, H4 EAD, asylum, green card, naturalization, deportation, OPT, TPS, and EB visa categories.

---

## Architecture

```
User Query
    │
    ▼
FastAPI Backend
    │
    ├── Metadata Filter (visa type detection)
    │
    ├── Parallel Retrieval
    │   ├── Milvus Dense Vector Search (laws + cases)
    │   ├── BM25 Keyword Search
    │   └── CourtListener Live Search
    │
    ├── RRF Reranking (Reciprocal Rank Fusion)
    │
    ├── Context Builder (formats citations)
    │
    ├── GPT-4o (generates answer)
    │
    ├── Output Sanitizer (PII redaction, citations)
    │
    └── LangSmith (traces every LLM call)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Python 3.12 |
| LLM | OpenAI GPT-4o |
| Vector DB | Milvus 2.4 |
| Embeddings | text-embedding-3-small |
| Relational DB | PostgreSQL 16 |
| Cache/Queue | Redis 7 + Celery |
| Scraping | Playwright (USCIS), httpx (CourtListener) |
| Retrieval | Hybrid (dense + BM25 + RRF) |
| Guardrails | GLiNER (PII detection) |
| Observability | LangSmith (LLM tracing) |
| Evaluation | RAGAS (answer relevancy 0.840) |
| Frontend | React 18, TypeScript, Tailwind CSS, Vite |
| Serving | Nginx (reverse proxy) |
| Container | Docker Compose (9 services) |

---

## Knowledge Base

| Source | Documents | Vectors |
|---|---|---|
| USCIS Policy Manual | 66 | 657 |
| BIA/AAO Case Decisions | 244 | 5,860 |
| USCIS News & Alerts | 20 | ~80 |
| **Total** | **330** | **6,597** |

---

## Features

### Core RAG Pipeline
- **Hybrid retrieval** — dense vector search + BM25 keyword search merged with Reciprocal Rank Fusion
- **Visa type detection** — automatically detects H1B, H4, L1, O1, asylum, green card, F1 queries
- **Proper citations** — `USCIS Policy Manual — Vol. 10 (Employment Authorization) — Part B — Ch. 2`
- **BIA case links** — `Matter of Simeio Solutions (BIA) → https://courtlistener.com/opinion/...`
- **CourtListener integration** — live federal court case search with immigration court filtering

### Observability & Evaluation
- **LangSmith tracing** — every LLM call traced with inputs, outputs, token counts, and latency
- **RAGAS evaluation** — answer relevancy score of 0.840 across 20 immigration law test cases
- **Audit logging** — every query logged with user, response time, and token count

### UI
- **Split panel layout** — chat on left, references panel on right
- **Legal Clauses section** — exact USCIS policy chapter citations
- **Related Cases section** — clickable BIA/AAO and federal court decisions
- **Response time display** — ms timing for each query

### Security & Access
- **Role-based access control** — `super_admin`, `admin`, `attorney`, `junior_associate`
- **JWT authentication** — secure token-based auth
- **Invite system** — admins generate invite links with specific roles
- **PII detection** — GLiNER model redacts names, SSNs, addresses from outputs

### Operations
- **Auto-scraping** — Celery scheduled tasks run daily/weekly
- **Change detection** — MD5 hash comparison, only re-ingests updated content
- **Admin dashboard** — trigger scrapes, view system stats

---

## Quick Start

### Prerequisites
- Docker Desktop
- OpenAI API key

### 1. Clone the repo

```bash
git clone https://github.com/Nithishkaranam2002/ImmigraAssist.git
cd ImmigraAssist
```

### 2. Configure environment

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and add your keys:

```env
OPENAI_API_KEY=sk-your-key-here
LANGSMITH_API_KEY=your-langsmith-key-here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=immigraassist
ADMIN_EMAIL=admin@yourfirm.com
ADMIN_PASSWORD=yourpassword
```

### 3. Start with Docker

```bash
docker compose up -d
```

Wait ~60 seconds for all services to initialize.

### 4. Open the app

```
http://localhost
```

Login with your admin credentials from `.env`.

### 5. Ingest data

```bash
# Get auth token
curl -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@yourfirm.com", "password": "yourpassword"}'

# Trigger full scrape (replace TOKEN)
curl -X POST "http://localhost/api/v1/admin/scrape/trigger?scrape_policy=true&scrape_news=true&scrape_bia=true" \
  -H "Authorization: Bearer TOKEN"
```

Takes 15-20 minutes on first run to ingest ~330 documents.

---

## Running RAGAS Evaluation

```bash
cd backend
python tests/test_ragas.py
```

Output:
```
IMMIGRAASSIST RAGAS EVALUATION RESULTS
========================================
Questions evaluated: 20
SCORES:
  Answer Relevancy:  0.840 / 1.000
  Overall Average:   0.840 / 1.000
  Grade: EXCELLENT
```

---

## Project Structure

```
ImmigraAssist/
├── backend/
│   ├── app/
│   │   ├── api/v1/routes/      # FastAPI route handlers
│   │   ├── db/                 # PostgreSQL + Milvus + Redis clients
│   │   ├── guardrails/         # PII detection, content moderation
│   │   ├── ingestion/          # Document chunking, embedding pipeline
│   │   ├── llm/                # GPT-4o client, prompt builder
│   │   ├── retrieval/          # Hybrid retriever, reranker, context builder
│   │   ├── scrapers/           # USCIS, BIA/AAO, CourtListener scrapers
│   │   └── tasks/              # Celery background tasks
│   ├── tests/
│   │   ├── test_ragas.py       # RAGAS evaluation script
│   │   ├── eval_dataset.json   # 20 immigration law test cases
│   │   └── ragas_results.json  # Latest evaluation results
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/              # ChatPage, AdminPage, UsersPage, etc.
│   │   ├── services/           # API clients
│   │   └── store/              # Zustand state management
│   ├── Dockerfile
│   └── nginx.conf
└── docker-compose.yml
```

---

## API Reference

```
POST /api/v1/auth/login           # Login
POST /api/v1/auth/register        # Register
POST /api/v1/chat/query           # Ask a question
GET  /api/v1/cases/search         # Search CourtListener cases
POST /api/v1/admin/scrape/trigger # Trigger data scrape
GET  /api/v1/users/               # List all users
POST /api/v1/invites/             # Create invite link
GET  /health                      # Health check
```

---

## User Roles

| Role | Chat | Documents | Users | Dashboard | Audit Logs |
|---|---|---|---|---|---|
| `junior_associate` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `attorney` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `admin` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `super_admin` | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## Environment Variables

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key (required) |
| `OPENAI_MODEL` | GPT model — default `gpt-4o` |
| `LANGSMITH_API_KEY` | LangSmith API key for tracing |
| `LANGCHAIN_TRACING_V2` | Enable LangSmith tracing |
| `POSTGRES_HOST` | PostgreSQL host |
| `MILVUS_HOST` | Milvus vector DB host |
| `REDIS_HOST` | Redis host |
| `ADMIN_EMAIL` | Super admin email (required) |
| `ADMIN_PASSWORD` | Super admin password (required) |
| `SECRET_KEY` | JWT secret key (required) |

See `backend/.env.example` for full list.

---

## Built With

- [FastAPI](https://fastapi.tiangolo.com) — modern Python web framework
- [Milvus](https://milvus.io) — open-source vector database
- [LangChain](https://langchain.com) — LLM application framework
- [LangSmith](https://smith.langchain.com) — LLM observability and tracing
- [RAGAS](https://docs.ragas.io) — RAG evaluation framework
- [GLiNER](https://github.com/urchade/GLiNER) — generalist NER model for PII detection
- [CourtListener](https://courtlistener.com) — free law API with 4M+ opinions
- [Playwright](https://playwright.dev) — browser automation for JS-rendered scraping
- [Celery](https://celeryq.dev) — distributed task queue

---

## Author

**Nithish Karanam**
- MS Artificial Intelligence, University of North Texas (GPA: 3.5)
- NVIDIA Certified — NCP-AAI and Generative AI LLMs Associate
- [GitHub](https://github.com/Nithishkaranam2002)
- [LinkedIn](https://linkedin.com/in/nithishkaranam)
- [Portfolio](https://nithishkaranam.lovable.app)

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Disclaimer

ImmigraAssist is an AI research tool intended to assist legal professionals with research. It does not constitute legal advice. Always consult a qualified immigration attorney before making legal decisions.
