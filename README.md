# 📚 RAQ Chatbot — Retrieval-Augmented Quiz Generation Platform

> **Intelligent Study Chatbot Platform** integrating RAG (Retrieval-Augmented Generation) and a Multi-Agent AI system to automatically generate multiple-choice quizzes strictly grounded in user-uploaded PDF documents.

---

## 📑 Table of Contents

- [1. Problem Statement](#1-problem-statement)
- [2. Technology Stack](#2-technology-stack)
- [3. Environment Requirements](#3-environment-requirements)
- [4. Environment Variables](#4-environment-variables)
- [5. Getting Started](#5-getting-started)
  - [5.1 Local Run (Dev Mode)](#51-local-run-dev-mode)
  - [5.2 Full Docker Compose Run](#52-full-docker-compose-run)
- [6. Additional Documentation](#6-additional-documentation)
- [7. Directory Structure](#7-directory-structure)

---

## 1. Problem Statement

**RAQ Chatbot** solves key challenges in personalized learning and exam preparation:

| Challenge | RAQ Solution |
|-----------|--------------|
| Long, dense PDF documents where students don't know where to start | Upload PDF → automated text extraction, chunking, and vector indexing |
| Difficulty self-testing knowledge retention | Multi-Agent AI automatically generates multiple-choice quizzes grounded in document content |
| Need for fast document retrieval and fact verification | HyDE RAG search with precise source citations (page number, file name) |
| Inconsistent quiz quality and hallucinations | Generator → Evaluator → Synthesizer workflow with reflection and critique loop |

**Key Features:**
- 🔐 Multi-tenant user isolation with JWT authentication
- 📂 Independent document organization via Libraries
- 📤 PDF Upload → automated text extraction, chunking, and 2048-dim vector embeddings
- 💬 Grounded AI chat using HyDE (Hypothetical Document Embeddings)
- 📝 Automated batch quiz generation (Generator → Evaluator → Synthesizer)
- ✏️ Inline quiz editing and PDF export
- ⚙️ BYOK (Bring Your Own Key) — support for Gemini, OpenAI, and Anthropic

---

## 2. Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| **Frontend** | Next.js (App Router), React, TailwindCSS v4, Vercel AI SDK | Next 16.x, React 19.x |
| **Backend** | FastAPI (Python, Async) | 0.141+ |
| **AI Engine** | LangChain + LangGraph (Multi-Agent StateGraph) | LangChain 1.3+, LangGraph 1.2+ |
| **Database** | PostgreSQL + pgvector (Vector 2048 dims) | PG 16 + pgvector |
| **Object Storage** | MinIO (S3-compatible) | Latest |
| **PDF Processing** | PyMuPDF (fitz) | 1.28+ |
| **Embedding** | NVIDIA NeMo Retriever / Nemotron-3-Embed-1B | 2048 dims |
| **Default LLM** | DeepSeek V4 Pro (via NVIDIA NIM) | deepseek-v4-pro-0813 |
| **Auth** | JWT (python-jose), bcrypt | HS256, 24h TTL |

---

## 3. Environment Requirements

### Minimum Hardware
| Resource | Requirement |
|----------|-------------|
| RAM | ≥ 8 GB (16 GB recommended for Docker) |
| Disk Space | ≥ 10 GB free space |
| CPU | 4 cores or higher |

### Required Software
| Software | Minimum Version | Notes |
|----------|-----------------|-------|
| **Node.js** | ≥ 20.x | For Next.js frontend |
| **Python** | ≥ 3.11 | For FastAPI backend |
| **Docker** | ≥ 24.x | For Docker Compose mode |
| **Docker Compose** | ≥ 2.20 | Plugin V2 (Docker integrated) |
| **Git** | ≥ 2.40 | Repository cloning |

---

## 4. Environment Variables

Copy the template configuration file and adjust variables as needed:

```bash
cp backend/.env.example backend/.env
```

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `DATABASE_URL` | PostgreSQL connection string (async) | `postgresql+asyncpg://postgres:postgres@localhost:5432/raq_chatbot` |
| `MINIO_ENDPOINT` | MinIO server address | `localhost:9000` |
| `MINIO_ACCESS_KEY` | MinIO access key | `minioadmin` |
| `MINIO_SECRET_KEY` | MinIO secret key | `minioadmin` |
| `MINIO_BUCKET_NAME` | S3 bucket name for PDF storage | `pdf-storage` |
| `MINIO_USE_SSL` | Enable SSL for MinIO | `false` |
| `JWT_SECRET_KEY` | Secret key for JWT signing | ⚠️ **Change in production** |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `JWT_EXPIRE_MINUTES` | Token expiration time (minutes) | `1440` (24 hours) |
| `SYSTEM_DEFAULT_API_KEY` | System fallback API key for LLM (NVIDIA NIM) | *(required when `USE_MOCK_LLM=false`)* |
| `SYSTEM_DEFAULT_EMBEDDING_KEY` | Dedicated API key for embedding model | *(falls back to `SYSTEM_DEFAULT_API_KEY` if unset)* |
| `SYSTEM_DEFAULT_API_BASE` | Base URL for LLM API | `https://integrate.api.nvidia.com/v1` |
| `DEFAULT_CHAT_MODEL` | Default LLM model for chat/quiz | `deepseek-ai/deepseek-v4-pro-0813` |
| `DEFAULT_EMBEDDING_MODEL` | Default embedding model | `nvidia/nemotron-3-embed-1b` |
| `USE_MOCK_LLM` | Mock mode (no real API key required) | `true` |
| `FRONTEND_URL` | Frontend origin for CORS | `http://localhost:3000` |

> **📌 Note**: Under `USE_MOCK_LLM=true` mode, the entire platform runs without needing **any real API keys** — embeddings are computed deterministically via hash algorithms, and LLM queries return simulated responses. This is ideal for demonstrations, offline testing, and grading.

Frontend configuration file:

```env
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 5. Getting Started

### 5.1 Local Run (Dev Mode)

**Step 1: Clone the repository**
```bash
git clone <repository-url>
cd RAQ_CHAT_BOT
```

**Step 2: Start PostgreSQL + MinIO (Docker)**
```bash
docker compose up -d postgres minio
```
> Wait approximately 10-15 seconds for services to become healthy. Database schema will automatically initialize from `sql/init.sql`.

**Step 3: Setup Backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # Edit .env if needed
```

**Step 4: Launch Backend**
```bash
uvicorn app.main:app --reload --port 8000
```
> Backend API: `http://localhost:8000`
> Swagger Docs: `http://localhost:8000/docs`

**Step 5: Setup Frontend**
```bash
cd ../frontend
npm install
```

**Step 6: Launch Frontend**
```bash
npm run dev
```
> Frontend Application: `http://localhost:3000`

---

### 5.2 Full Docker Compose Run

**Start all 4 services:**
```bash
# Create backend .env file (if not already created)
cp backend/.env.example backend/.env

# Build and start containers
docker compose up --build -d
```

**Check service status:**
```bash
docker compose ps
docker compose logs -f backend
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| MinIO Console | http://localhost:9001 |
| PostgreSQL | localhost:5432 |

**Stop services:**
```bash
docker compose down          # Preserve database volumes
docker compose down -v       # Remove volumes (erases all data)
```

---

## 6. Additional Documentation

| Document | Content Description |
|----------|---------------------|
| [ARCHITECTURE.md](./docs/ARCHITECTURE.md) | System architecture, data flow diagrams, Multi-Agent Graph design |
| [API.md](./docs/API.md) | Complete RESTful API specifications (endpoints, requests/responses, status codes) |
| [USECASES.md](./docs/USECASES.md) | Fully-dressed Cockburn Use Case specifications (UC-01 → UC-08) |
| [DEPLOYMENT.md](./docs/DEPLOYMENT.md) | Production deployment guide, Docker strategies, monitoring, backup |

---

## 7. Directory Structure

```
RAQ_CHAT_BOT/
├── backend/                    # FastAPI Backend (Python 3.11+)
│   ├── app/
│   │   ├── agents/             # LangGraph Multi-Agent system
│   │   │   └── assistant/
│   │   │       ├── graph.py        # Main agent ReAct loop (Supervisor)
│   │   │       ├── prompts.py      # System prompt definitions
│   │   │       ├── state.py        # AgentState TypedDict
│   │   │       └── tools/
│   │   │           ├── search_documents.py   # RAG search tool
│   │   │           └── generate_quiz/        # Quiz generation subgraph
│   │   │               ├── tool.py               # Tool entry point
│   │   │               ├── subgraph.py            # StateGraph (batch + reflection)
│   │   │               ├── state.py / schemas.py  # Quiz state & Pydantic schemas
│   │   │               └── nodes/
│   │   │                   ├── generator_node.py   # Question generation
│   │   │                   ├── evaluator_node.py   # Quality evaluation
│   │   │                   └── synthesizer_node.py # Batch synthesis
│   │   ├── api/
│   │   │   ├── deps.py             # Dependency injection (DB session, auth)
│   │   │   └── routes/
│   │   │       ├── auth.py         # Register, Login, Get Me
│   │   │       ├── libraries.py    # Library & ChatSession CRUD
│   │   │       ├── documents.py    # Upload PDF, Ingestion progress
│   │   │       ├── quizzes.py      # Quiz CRUD
│   │   │       └── chat.py         # Streaming chat endpoint (Vercel AI SDK)
│   │   ├── core/
│   │   │   ├── config.py           # Pydantic Settings (.env)
│   │   │   ├── db.py               # AsyncSession, engine, checkpointer
│   │   │   └── security.py         # JWT, bcrypt helpers
│   │   ├── db/
│   │   │   └── models.py           # 9 SQLAlchemy ORM models + pgvector
│   │   ├── llm/
│   │   │   └── llm_factory.py      # Dynamic LLM Factory (BYOK, Mock)
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   │   ├── auth.py
│   │   │   ├── library.py
│   │   │   ├── document.py
│   │   │   ├── quiz.py
│   │   │   └── chat.py
│   │   └── services/
│   │       ├── ingestion_service.py  # PDF → chunks → embeddings
│   │       ├── storage_service.py    # MinIO upload/download/delete
│   │       └── vector_store.py       # HyDE + pgvector similarity search
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/                   # Next.js Frontend (React 19)
│   ├── src/
│   │   ├── app/                    # App Router pages
│   │   │   ├── page.tsx                # Dashboard (Library list)
│   │   │   ├── auth/login/page.tsx     # Login page
│   │   │   ├── auth/register/page.tsx  # Register page
│   │   │   └── libraries/[id]/page.tsx # Library detail (chat + docs)
│   │   ├── components/
│   │   │   ├── chat/
│   │   │   │   └── ChatWindow.tsx      # Real-time chat + quiz display
│   │   │   ├── library/
│   │   │   │   └── LibrarySidebar.tsx   # Session list sidebar
│   │   │   ├── quiz/
│   │   │   │   ├── QuizPreviewCard.tsx  # Quiz preview (read-only)
│   │   │   │   ├── QuizEditorCard.tsx   # Inline quiz editor
│   │   │   │   └── QuizPdfExport.tsx    # Export quiz to PDF
│   │   │   └── settings/
│   │   │       └── ModelSettingsPanel.tsx # BYOK settings modal
│   │   ├── hooks/
│   │   │   └── useChat.ts              # Custom chat hook (SSE streaming)
│   │   └── lib/
│   │       ├── api.ts                  # API client (fetch wrapper)
│   │       └── auth-context.tsx        # Auth context provider
│   ├── Dockerfile
│   └── package.json
├── sql/
│   └── init.sql                # Database schema (9 tables, pgvector)
├── docker-compose.yml          # All-in-one orchestration
└── README.md                   # ← You are here
```
