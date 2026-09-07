# 🏗️ ARCHITECTURE.md — RAQ Chatbot System Architecture

---

## 📑 Table of Contents

- [1. Architecture Overview](#1-architecture-overview)
- [2. High-Level Architecture Diagram](#2-high-level-architecture-diagram)
- [3. Frontend Architecture](#3-frontend-architecture)
- [4. Backend Architecture](#4-backend-architecture)
- [5. AI Engine — Multi-Agent Graph](#5-ai-engine--multi-agent-graph)
- [6. Database Schema (9 Tables)](#6-database-schema-9-tables)
- [7. Core Data Flows](#7-core-data-flows)
- [8. Security Architecture](#8-security-architecture)
- [9. BYOK (Bring Your Own Key) Design](#9-byok-bring-your-own-key-design)

---

## 1. Architecture Overview

RAQ Chatbot is architected as a **Three-tier Client-Server** application:

| Tier | Technology | Responsibility |
|------|------------|----------------|
| **Presentation** | Next.js 16 (App Router) + React 19 | Single Page Application (SPA), SSE streaming, BYOK configuration UI |
| **Application** | FastAPI (Python async) + LangGraph | REST API, Multi-Agent workflow orchestration, background processing |
| **Data** | PostgreSQL 16 + pgvector + MinIO | Relational records + vector store + object/file storage |

**Core Design Principles:**
- **Multi-tenant isolation**: Every user owns independent libraries; data isolation is strictly enforced via `user_id` filtering on all queries.
- **Async-first**: The backend utilizes `asyncpg`, `AsyncSession`, and `asyncio.create_task` for non-blocking I/O.
- **Mock-first development**: The `USE_MOCK_LLM=true` flag enables complete end-to-end development, testing, and grading without external API keys.
- **Stateless API**: The backend stores no in-memory state across requests (except transient asyncio queues during active SSE streaming).

---

## 2. High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js 16)                        │
│  ┌───────────┐  ┌──────────────┐  ┌──────────┐  ┌───────────────┐  │
│  │ Dashboard  │  │ Library Page │  │ Auth Pages│  │ Settings Modal│  │
│  │ (page.tsx) │  │ ([id]/page)  │  │ login/reg │  │ (BYOK Config) │  │
│  └─────┬─────┘  └──────┬───────┘  └─────┬────┘  └───────┬───────┘  │
│        │               │                │                │          │
│  ┌─────┴───────────────┴────────────────┴────────────────┴─────┐    │
│  │                    API Client (lib/api.ts)                  │    │
│  │           + Auth Context (lib/auth-context.tsx)              │    │
│  └──────────────────────────┬──────────────────────────────────┘    │
└─────────────────────────────┼──────────────────────────────────────┘
                              │ HTTP/SSE (Port 3000 → 8000)
┌─────────────────────────────┼──────────────────────────────────────┐
│                      BACKEND (FastAPI)                              │
│  ┌──────────────────────────┴──────────────────────────────────┐    │
│  │                    CORS Middleware                           │    │
│  ├─────────────────────────────────────────────────────────────┤    │
│  │  API Routes                                                  │    │
│  │  ├── /api/auth/*        (register, login, me)               │    │
│  │  ├── /api/libraries/*   (CRUD + sessions + messages)        │    │
│  │  ├── /api/documents/*   (upload, progress, list, delete)    │    │
│  │  ├── /api/quizzes/*     (CRUD quiz + questions)             │    │
│  │  ├── /api/chat          (SSE streaming endpoint)            │    │
│  │  └── /api/health        (health check)                      │    │
│  ├─────────────────────────────────────────────────────────────┤    │
│  │  Core Services                                               │    │
│  │  ├── LLM Factory     (BYOK + Mock + Multi-provider)         │    │
│  │  ├── Ingestion Service (PDF → chunks → embeddings)          │    │
│  │  ├── Vector Store     (HyDE + pgvector cosine search)       │    │
│  │  └── Storage Service  (MinIO S3 upload/download)            │    │
│  ├─────────────────────────────────────────────────────────────┤    │
│  │  AI Agent Engine (LangGraph)                                 │    │
│  │  ├── Supervisor Agent (ReAct loop)                          │    │
│  │  │   ├── Tool: search_documents (RAG)                       │    │
│  │  │   └── Tool: generate_quiz (Multi-Agent Subgraph)         │    │
│  │  │       ├── Generator Node                                  │    │
│  │  │       ├── Evaluator Node (Reflection)                    │    │
│  │  │       └── Synthesizer Node (Batch merge)                 │    │
│  └─────────────────────────────────────────────────────────────┘    │
└────────────┬───────────────────────────────┬───────────────────────┘
             │                               │
    ┌────────┴────────┐             ┌────────┴────────┐
    │   PostgreSQL 16  │             │     MinIO S3     │
    │   + pgvector     │             │  (PDF Storage)   │
    │   (Port 5432)    │             │  (Port 9000/9001)│
    │                  │             │                  │
    │  9 tables:       │             │  Bucket:         │
    │  users           │             │  pdf-storage/    │
    │  libraries       │             │                  │
    │  documents       │             └──────────────────┘
    │  ingestion_jobs  │
    │  document_chunks │
    │  chat_sessions   │
    │  chat_messages   │
    │  quizzes         │
    │  quiz_questions  │
    └──────────────────┘
```

---

## 3. Frontend Architecture

### 3.1 Overview

The frontend is built on **Next.js 16 App Router** with React 19, TailwindCSS v4, and Vercel AI SDK principles.

```
src/
├── app/                        # App Router (file-based routing)
│   ├── layout.tsx              # Root layout (AuthProvider wrapper)
│   ├── page.tsx                # "/" — Dashboard (Library grid)
│   ├── auth/
│   │   ├── login/page.tsx      # "/auth/login"
│   │   └── register/page.tsx   # "/auth/register"
│   └── libraries/
│       └── [id]/page.tsx       # "/libraries/:id" — Main workspace
│
├── components/
│   ├── chat/ChatWindow.tsx     # Real-time chat (SSE + quiz inline)
│   ├── library/LibrarySidebar.tsx  # Session list + document upload
│   ├── quiz/
│   │   ├── QuizPreviewCard.tsx    # Quiz display (read-only)
│   │   ├── QuizEditorCard.tsx     # Inline quiz editor
│   │   └── QuizPdfExport.tsx      # PDF export (jsPDF)
│   └── settings/
│       └── ModelSettingsPanel.tsx  # BYOK model configuration
│
├── hooks/useChat.ts            # Custom SSE chat hook
└── lib/
    ├── api.ts                  # Centralized fetch wrapper
    └── auth-context.tsx        # JWT token management context
```

### 3.2 Chat SSE Streaming Flow

```
User submits question
    │
    ▼
ChatWindow.tsx
    │  POST /api/chat (body: messages, libraryId, sessionId)
    │  Headers: Authorization, X-Gemini-Key, X-Openai-Key, ...
    │
    ▼
SSE Stream parsed in real-time:
    ├── <!--EVENT:{...}-->     → Real-time status (searching, quiz_batch, quiz_ready)
    ├── text chunks            → Word-by-word streaming rendering
    └── <!--METADATA_START--> → Citations, quiz_id (at stream end)
```

### 3.3 State Management

- **Auth state**: `AuthContext` (React Context) → persists JWT token in `localStorage`.
- **Chat state**: `useChat` custom hook → manages messages, streaming flags, and event queues.
- **Library / Document state**: Local page component state, synchronized via API queries.
- **Quiz state**: Receives `quiz_id` via SSE event → fetches full quiz details from `/api/quizzes/:id`.

---

## 4. Backend Architecture

### 4.1 Module Structure

```
app/
├── main.py                 # FastAPI entry point, router registration, CORS
├── core/
│   ├── config.py           # Pydantic Settings (env vars)
│   ├── db.py               # AsyncEngine, AsyncSession, LangGraph Checkpointer
│   └── security.py         # hash_password, verify_password, create/decode JWT
├── api/
│   ├── deps.py             # get_db(), get_current_user() dependency injection
│   └── routes/             # API endpoint handlers
├── db/
│   └── models.py           # 9 SQLAlchemy ORM models
├── schemas/                # Pydantic request/response models
├── llm/
│   └── llm_factory.py      # Dynamic LLM instantiation
├── services/               # Business logic services
└── agents/                 # LangGraph agent system
```

### 4.2 Dependency Injection

```python
# Every protected route injects two primary dependencies:
async def endpoint(
    db: AsyncSession = Depends(get_db),           # Database session
    current_user: User = Depends(get_current_user) # JWT authentication
):
```

- `get_db()`: Yields an `AsyncSession` from `AsyncSessionLocal`, ensuring automatic session cleanup.
- `get_current_user()`: Decodes the JWT from the `Authorization: Bearer <token>` header, returning the authenticated `User` ORM entity.

### 4.3 Background Ingestion Processing

Document ingestion runs asynchronously via `asyncio.create_task()`:

```
Upload request → save metadata to DB + file to MinIO → return 201 Created
                                                        ↓ (background task)
                                                  _run_ingestion()
                                                        │
                                                  ingest_document()
                                                  ├── Extract pages (PyMuPDF)
                                                  ├── Split chunks (1000 chars, 150 overlap)
                                                  ├── Compute embeddings (batch 50)
                                                  └── Store in document_chunks table
```

---

## 5. AI Engine — Multi-Agent Graph

### 5.1 Main Agent Graph (Supervisor ReAct Loop)

The core AI engine uses a **LangGraph StateGraph** implementing the **ReAct** (Reasoning + Acting) pattern:

```
                    ┌─────────────────┐
                    │   Entry Point   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
              ┌─────│   Agent Node    │─────┐
              │     │  (Supervisor)   │     │
              │     └────────┬────────┘     │
              │              │              │
         tools_condition     │         direct response
              │              │              │
    ┌─────────▼──────────┐   │    ┌─────────▼──────────┐
    │   Custom Tool Node │   │    │        END          │
    │ ┌────────────────┐ │   │    └────────────────────┘
    │ │search_documents│ │   │
    │ │ (RAG + HyDE)   │ │   │
    │ ├────────────────┤ │   │
    │ │ generate_quiz  │ │   │
    │ │ (Subgraph)     │ │   │
    │ └────────────────┘ │   │
    └─────────┬──────────┘   │
              │              │
              └──────────────┘  (loop back to agent)
```

**AgentState** (TypedDict):

| Field | Type | Description |
|-------|------|-------------|
| `messages` | `list[BaseMessage]` | LangChain conversation history |
| `library_id` | `str` | Active library ID |
| `session_id` | `str` | Active chat session ID |
| `user_id` | `str` | Authenticated user ID |
| `api_keys` | `dict` | BYOK keys (gemini, openai, anthropic, default) |
| `model_config` | `dict` | Selected model identifiers per agent role |
| `citations` | `list[dict]` | Citations retrieved by search_documents |
| `quiz_draft` | `list[dict]` | Quiz questions generated |
| `event_queue` | `asyncio.Queue` | Real-time SSE event queue |

### 5.2 Tool: search_documents (RAG + HyDE)

```
User query: "Explain the operating principle of a transistor"
    │
    ▼
┌── HyDE (Hypothetical Document Embeddings) ───────────────┐
│  LLM generates 2 hypothetical answers:                   │
│  • "A transistor operates based on semiconductor physics"│
│  • "The BJT structure features 3 alternating P/N layers" │
└──────────────────────────────────────────────────────────┘
    │
    ▼ Compute embeddings for original query + 2 answers (3 vectors total)
    │
    ▼ pgvector cosine similarity search (1 - embedding <=> query)
    │
    ▼ Deduplicate results by chunk_id, retaining maximum score
    │
    ▼ Return top-20 chunks + citations
```

### 5.3 Tool: generate_quiz (Multi-Agent Subgraph)

The quiz generator operates as a **nested StateGraph** comprising 4 nodes and a reflection/critique loop:

```
┌──────────────────────────────────────────────────────────────────────┐
│                       Quiz Subgraph                                  │
│                                                                      │
│  ┌───────┐    ┌───────────┐    ┌───────────┐    ┌─────────────┐     │
│  │ init  │───▶│ generator │───▶│ evaluator │───▶│ synthesizer │     │
│  │(plan) │    │  (draft)  │    │(critique) │    │  (merge)    │     │
│  └───────┘    └─────┬─────┘    └─────┬─────┘    └──────┬──────┘     │
│                     ▲                │                  │            │
│                     │          rejected (≤2 retries)    │            │
│                     └────────────────┘                  │            │
│                                                         │            │
│               ┌─────────────────────────────────────────┘            │
│               │                                                      │
│         has_more_batches?                                            │
│         ├── yes → generator (next batch)                             │
│         └── no  → END                                                │
└──────────────────────────────────────────────────────────────────────┘
```

**Node Responsibilities:**

| Node | Role | Input | Output |
|------|------|-------|--------|
| **init** | Batch planning, dividing topics into aspects (Structured LLM) | `num_questions`, `focus_topic` | `total_batches`, `aspect_hints[]` |
| **generator** | Generates draft quiz questions based on aspect hints | context_chunks (HyDE search), aspect_hint | `draft_questions[]` |
| **evaluator** | Evaluates question clarity, accuracy, and options | `draft_questions[]` | `eval_feedback`, `eval_details` |
| **synthesizer** | Filters passing questions, dispatches SSE `quiz_batch` event | `draft_questions[]`, `eval_feedback` | `accepted_questions[]` (appended) |

**Flow Execution Rules:**
- Evaluator rejects → generator re-runs with critique feedback (maximum 2 retries per batch).
- Evaluator approves OR max retries reached → synthesizer absorbs questions.
- Synthesizer completes batch → checks `has_more_batches`:
  - `current_batch >= total_batches` → END
  - `len(accepted_questions) >= num_questions` → END
  - Remaining batches → routes back to generator for the next batch.

---

## 6. Database Schema (9 Tables)

### 6.1 Entity Relationship Diagram (ERD)

```
┌──────────┐       ┌────────────┐       ┌────────────────┐
│  users   │1─────*│ libraries  │1─────*│   documents    │
│          │       │            │       │                │
│ id (PK)  │       │ id (PK)   │       │ id (PK)        │
│ email    │       │ user_id(FK)│       │ library_id(FK) │
│ password │       │ name       │       │ user_id (FK)   │
│ first_   │       │ description│       │ file_name      │
│  name    │       │ icon_color │       │ file_path_minio│
│ last_    │       │ total_docs │       │ total_pages    │
│  name    │       │ created_at │       │ status         │
│ created  │       └─────┬──────┘       └───────┬────────┘
│  _at     │             │                      │
└──────────┘             │                      │ 1:1
                         │              ┌───────┴────────┐
                         │              │ ingestion_jobs │
                         │              │ id (PK)        │
                         │              │ document_id(FK)│
                         │              │ total_chunks   │
                         │              │ processed_     │
                         │              │  chunks        │
                         │              │ progress_%     │
                         │              │ error_message  │
                         │              └────────────────┘
                         │
                         │ 1:*          ┌────────────────┐
                         ├─────────────*│document_chunks │
                         │              │ id (PK)        │
                         │              │ library_id(FK) │
                         │              │ document_id(FK)│
                         │              │ user_id (FK)   │
                         │              │ page_number    │
                         │              │ chunk_index    │
                         │              │ content (TEXT)  │
                         │              │ embedding      │
                         │              │  VECTOR(2048)  │
                         │              │ metadata (JSONB│
                         │              └────────────────┘
                         │
                         │ 1:*          ┌────────────────┐
                         ├─────────────*│ chat_sessions  │
                         │              │ id (PK)        │
                         │              │ library_id(FK) │
                         │              │ user_id (FK)   │
                         │              │ title          │
                         │              │ created_at     │
                         │              │ updated_at     │
                         │              └───────┬────────┘
                         │                      │ 1:*
                         │              ┌───────┴────────┐
                         │              │ chat_messages  │
                         │              │ id (PK)        │
                         │              │ session_id(FK) │
                         │              │ role           │
                         │              │ content        │
                         │              │ citations(JSONB│
                         │              │ quiz_id (FK)   │
                         │              │ created_at     │
                         │              └────────────────┘
                         │
                         │ 1:*          ┌────────────────┐
                         └─────────────*│   quizzes      │
                                        │ id (PK)        │
                                        │ library_id(FK) │
                                        │ user_id (FK)   │
                                        │ title          │
                                        │ description    │
                                        │ total_questions│
                                        │ is_edited_by_  │
                                        │  user          │
                                        │ created_at     │
                                        └───────┬────────┘
                                                │ 1:*
                                        ┌───────┴────────┐
                                        │quiz_questions  │
                                        │ id (PK)        │
                                        │ quiz_id (FK)   │
                                        │ order_index    │
                                        │ question_text  │
                                        │ option_a/b/c/d │
                                        │ correct_answer │
                                        │  CHECK(A/B/C/D)│
                                        │ explanation    │
                                        │ source_page    │
                                        └────────────────┘
```

### 6.2 Interactive Schema Diagram

> 📎 Open [db.html](./db.html) directly in any web browser to explore the interactive ERD featuring dynamic Bezier connector lines, hover highlighting, and complete attribute specifications across all 9 tables.

### 6.3 Detailed Table Descriptions

| # | Table | Description | Relationships |
|---|-------|-------------|---------------|
| 1 | `users` | User accounts (unique email, bcrypt hashed password) | 1:N → libraries |
| 2 | `libraries` | Document libraries for multi-tenant isolation | N:1 → users, 1:N → documents, sessions, quizzes |
| 3 | `documents` | Uploaded PDF files and status | N:1 → libraries, 1:1 → ingestion_jobs, 1:N → chunks |
| 4 | `ingestion_jobs` | Ingestion pipeline progress tracking | 1:1 → documents |
| 5 | `document_chunks` | Extracted text chunks + 2048-dim vector embeddings | N:1 → documents, libraries |
| 6 | `chat_sessions` | Chat conversation threads within a library | N:1 → libraries, 1:N → messages |
| 7 | `chat_messages` | Individual messages (user/assistant, JSONB citations) | N:1 → sessions, N:1 → quizzes |
| 8 | `quizzes` | Multiple-choice quiz metadata | N:1 → libraries, 1:N → questions |
| 9 | `quiz_questions` | Multiple-choice questions with 4 options (A/B/C/D) | N:1 → quizzes |

### 6.4 Key Indexes

```sql
CREATE INDEX idx_libraries_user ON libraries(user_id);
CREATE INDEX idx_documents_library ON documents(library_id);
CREATE INDEX idx_chunks_library_user ON document_chunks(library_id, user_id);
CREATE INDEX idx_questions_quiz ON quiz_questions(quiz_id, order_index);
CREATE INDEX idx_messages_session ON chat_messages(session_id, created_at);
-- pgvector indexes manage similarity queries on VECTOR(2048)
```

---

## 7. Core Data Flows

### 7.1 Upload & Ingestion Flow

```
┌──────┐  POST /api/documents/upload  ┌─────────┐  upload_file()  ┌───────┐
│ User │ ──────────────────────────▶  │ Backend │ ─────────────▶  │ MinIO │
└──────┘    (multipart/form-data)     └────┬────┘                 └───────┘
                                           │
                                 asyncio.create_task()
                                           │
                                    ┌──────▼──────┐
                                    │  Ingestion  │
                                    │  Pipeline   │
                                    │             │
                                    │ 1. PyMuPDF  │── extract pages
                                    │ 2. Splitter │── chunk (1000/150)
                                    │ 3. Embed    │── NVIDIA API (batch 32)
                                    │ 4. Store    │── document_chunks
                                    └──────┬──────┘
                                           │
                               progress tracking via
                               GET /api/documents/:id/progress
```

### 7.2 Chat Flow (RAG)

```
┌──────┐  POST /api/chat  ┌─────────┐         ┌─────────────────┐
│ User │ ───────────────▶  │ Chat    │ ──────▶ │ LangGraph Agent │
└──────┘  (SSE stream)    │ Endpoint│         │ (Supervisor)    │
                          └────┬────┘         └────────┬────────┘
                               │                       │
                          SSE events              tools_condition
                          ◀────┤                       │
                               │              ┌────────▼────────┐
                               │              │ search_documents│
                               │              │   (HyDE RAG)   │
                               │              └────────┬────────┘
                               │                       │
                               │              pgvector similarity
                               │                       │
                               │              ┌────────▼────────┐
                               │              │ Return top-20   │
                               │              │ chunks + cites  │
                               │              └────────┬────────┘
                               │                       │
                               │              ┌────────▼────────┐
                               │              │ Agent synthesize│
                               │              │ final response  │
                               │              └─────────────────┘
                               │
                          StreamingResponse
                          (word-by-word + metadata)
```

### 7.3 Quiz Generation Flow

```
User: "Generate 20 multiple choice questions on Chapter 3"
    │
    ▼
Supervisor Agent → invokes tool generate_quiz(num_questions=20, focus_topic="Chapter 3")
    │
    ▼
Quiz Subgraph:
    │
    ├── init: Planning → 1 batch (20 questions ÷ 20/batch = 1 batch)
    │         Generates aspect_hints using Structured LLM
    │
    ├── Batch 1:
    │   ├── generator: HyDE search → retrieve context → LLM generates 20 questions
    │   ├── evaluator: Quality evaluation → approved / rejected
    │   │   └── (if rejected) → re-prompt generator with feedback (max 2 retries)
    │   └── synthesizer: Collects approved questions → dispatches SSE quiz_batch event
    │
    ▼
Tool returns: {quiz_draft: [...20 items...], message: "Successfully generated 20 questions"}
    │
    ▼
Chat endpoint:
    ├── Auto-saves quiz to DB (quizzes + quiz_questions tables)
    ├── Sends SSE event: quiz_ready (quiz_id)
    ├── Persists assistant message to DB (chat_messages.quiz_id = ...)
    └── Streams final text response + metadata
```

---

## 8. Security Architecture

### 8.1 Authentication (JWT)

```
Register → hash_password(bcrypt) → save to DB
Login → verify_password → create_access_token(user_id, exp=24h)
                                        │
                                   HS256 signed JWT
                                        │
                                        ▼
               Authorization: Bearer <token>
                                        │
                               decode_access_token()
                                        │
                               get_current_user() dependency
```

### 8.2 Authorization (Resource Isolation)

Every database query is strictly scoped by `user_id`:

```python
# Example: listing libraries
select(Library).where(Library.user_id == current_user.id)

# Example: accessing a document
doc = await db.get(Document, document_id)
if not doc or doc.user_id != current_user.id:
    raise HTTPException(status_code=404, detail="Document not found")
```

### 8.3 CORS Configuration

```python
allow_origins=[settings.FRONTEND_URL, "http://localhost:3000", "http://localhost:3001"]
allow_methods=["*"]
allow_headers=["*"]
allow_credentials=True
```

---

## 9. BYOK (Bring Your Own Key) Design

### 9.1 Two-Tier Key Resolution Model

```
                    ┌─────────────────┐
                    │  User BYOK Key  │  ← Priority 1 (from HTTP header)
                    │  (per-request)   │
                    └────────┬────────┘
                             │
                      Key present?
                    ┌────yes──┴──no────┐
                    │                  │
             ┌──────▼──────┐  ┌───────▼───────┐
             │ Use user's  │  │ System key    │  ← Priority 2 (from .env)
             │ key         │  │ (.env)        │
             └─────────────┘  └───────────────┘
```

### 9.2 Supported Providers

| Provider | Request Header | Supported Models |
|----------|----------------|------------------|
| NVIDIA NIM (Default) | System-only (.env) | deepseek-v4-pro-0813, deepseek-v4-flash-0731 |
| Google Gemini | `X-Gemini-Key` | gemini-2.5-flash, gemini-3.1-pro |
| OpenAI | `X-Openai-Key` | gpt-4o, gpt-4o-mini |
| Anthropic | `X-Anthropic-Key` | claude-3-5-sonnet, claude-3-5-haiku |

### 9.3 Key Permission and Scope Rules

| Key Type | User Configurable? | Purpose |
|----------|-------------------|---------|
| Chat LLM Key (Gemini/OpenAI/Anthropic) | ✅ Yes (BYOK) | Dedicated chat and quiz generation |
| System Default Key (NVIDIA NIM) | ❌ No (Server-side) | Fallback when user does not supply a key |
| Embedding Key | ❌ No (Server-side) | Computes 2048-dim vectors for document chunks |
