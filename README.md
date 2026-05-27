# ImmigraAssist 🏛️

> AI-powered immigration legal research assistant for law firms — from policies to precedents, instantly.

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB)](https://react.dev)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)](https://docker.com)
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

## Demo

![ImmigraAssist Demo](docs/demo.png)

**Live features:**
- Ask any US immigration law question
- Get answers grounded in real USCIS policy chapters
- See clickable BIA/AAO case precedents with CourtListener links
- References panel shows exact policy manual chapters and case citations

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
    │   ├── Milvus Vector Search (laws + cases)
    │   ├── BM25 Keyword Search
    │   └── CourtListener Live Search
    │
    ├── RRF Reranking (Reciprocal Rank Fusion)
    │
    ├── Context Builder (formats citations)
    │
    ├── GPT-4o (generates answer)
    │
    └── Output Sanitizer (PII redaction, citations)
```

### Tech Stack

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
| Frontend | React 18, TypeScript, Tailwind CSS, Vite |
| Serving | Nginx (reverse proxy) |
| Container | Docker Compose |

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

### Core
- **Hybrid RAG** — dense vector search + BM25 keyword search merged with Reciprocal Rank Fusion
- **Visa type detection** — automatically detects H1B, H4, L1, O1, asylum, green card, F1 queries
- **Proper citations** — `USCIS Policy Manual — Vol. 10 (Employment Authorization) — Part B — Ch. 2`
- **BIA case links** — `Matter of Simeio Solutions (BIA) → https://courtlistener.com/opinion/...`
- **CourtListener integration** — live federal court case search with court filtering

### UI
- **Split panel layout** — chat on left, references panel on right
- **Legal Clauses section** — exact USCIS policy chapter citations
- **Related Cases section** — clickable BIA/AAO and federal court decisions
- **Response time display** — ms timing for each query
- **Helpful/unhelpful feedback** — thumbs up/down per response

### Security & Access
- **Role-based access control** — `super_admin`, `admin`, `attorney`, `junior_associate`
- **JWT authentication** — secure token-based auth
- **Invite system** — admins generate invite links with specific roles
- **PII detection** — GLiNER model redacts names, SSNs, addresses from outputs
- **Audit logging** — every query logged with user, response time, token count

### Operations
- **Auto-scraping** — Celery scheduled tasks run daily/weekly
- **Change detection** — MD5 hash comparison, only re-ingests updated content
- **Admin dashboard** — trigger scrapes, view system stats
- **Audit logs** — full query history with metadata

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

Edit `backend/.env` and add your OpenAI API key:

```env
OPENAI_API_KEY=sk-your-key-here
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

Trigger the initial data scrape from the admin dashboard or via API:

```bash
# Get auth token
curl -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@yourfirm.com", "password": "yourpassword"}'

# Trigger full scrape (replace TOKEN)
curl -X POST "http://localhost/api/v1/admin/scrape/trigger?scrape_policy=true&scrape_news=true&scrape_bia=true" \
  -H "Authorization: Bearer TOKEN"
```

This will ingest ~330 documents and 6,500+ vectors. Takes 15-20 minutes on first run.

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
│   │   └── tasks/              # Celery tasks
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

### Authentication
```
POST /api/v1/auth/login          # Login
POST /api/v1/auth/register       # Register (junior_associate role)
```

### Chat
```
POST /api/v1/chat/query          # Ask a question
POST /api/v1/chat/feedback       # Submit feedback
GET  /api/v1/cases/search        # Search CourtListener cases
```

### Admin
```
POST /api/v1/admin/scrape/trigger    # Trigger data scrape
GET  /api/v1/admin/stats             # System statistics
GET  /api/v1/users/                  # List all users
POST /api/v1/invites/                # Create invite link
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

## Sample Questions

```
What are the requirements for H4 EAD eligibility?
Explain AC21 portability for H1B holders
What documents are needed for asylum application?
What happens if an H1B petition is denied?
What defenses are available against deportation for long-term residents?
What is the latest update on H1B registration for FY 2027?
```

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API key | required |
| `OPENAI_MODEL` | GPT model to use | `gpt-4o` |
| `POSTGRES_HOST` | PostgreSQL host | `localhost` |
| `MILVUS_HOST` | Milvus host | `localhost` |
| `REDIS_HOST` | Redis host | `localhost` |
| `ADMIN_EMAIL` | Super admin email | required |
| `ADMIN_PASSWORD` | Super admin password | required |
| `SECRET_KEY` | JWT secret key | required |

See `backend/.env.example` for the full list.

---

## Development

### Run locally (without Docker)

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev

# Celery worker
cd backend
celery -A celery_worker worker --loglevel=info
```

### Run with Docker

```bash
docker compose up -d           # Start all services
docker compose logs -f backend # View backend logs
docker compose ps              # Check service health
docker compose down            # Stop all services
```

---

## Built With

- [FastAPI](https://fastapi.tiangolo.com) — modern Python web framework
- [Milvus](https://milvus.io) — open-source vector database
- [LangChain](https://langchain.com) — LLM application framework
- [GLiNER](https://github.com/urchade/GLiNER) — generalist NER model for PII detection
- [CourtListener](https://courtlistener.com) — free law API with 4M+ opinions
- [Playwright](https://playwright.dev) — browser automation for JS-rendered scraping
- [Celery](https://celeryq.dev) — distributed task queue

---

## Author

**Nithish Karanam**
- MS Artificial Intelligence, University of North Texas
- NVIDIA Certified
- [GitHub](https://github.com/Nithishkaranam2002)
- [LinkedIn](https://linkedin.com/in/nithishkaranam)

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Disclaimer

ImmigraAssist is an AI research tool intended to assist legal professionals with research. It does not constitute legal advice. Always consult a qualified immigration attorney before making legal decisions.
