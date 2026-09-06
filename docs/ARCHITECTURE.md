<![CDATA[# 🏗️ ARCHITECTURE.md — Kiến trúc Hệ thống RAQ Chatbot

---

## 📑 Mục lục

- [1. Tổng quan kiến trúc](#1-tổng-quan-kiến-trúc)
- [2. Sơ đồ kiến trúc tổng thể](#2-sơ-đồ-kiến-trúc-tổng-thể)
- [3. Frontend Architecture](#3-frontend-architecture)
- [4. Backend Architecture](#4-backend-architecture)
- [5. AI Engine — Multi-Agent Graph](#5-ai-engine--multi-agent-graph)
- [6. Database Schema (9 bảng)](#6-database-schema-9-bảng)
- [7. Luồng xử lý dữ liệu chính](#7-luồng-xử-lý-dữ-liệu-chính)
- [8. Cơ chế bảo mật](#8-cơ-chế-bảo-mật)
- [9. Thiết kế BYOK (Bring Your Own Key)](#9-thiết-kế-byok-bring-your-own-key)

---

## 1. Tổng quan kiến trúc

RAQ Chatbot được thiết kế theo kiến trúc **Client-Server 3 tầng** (Three-tier):

| Tầng | Công nghệ | Vai trò |
|------|-----------|---------|
| **Presentation** | Next.js 16 (App Router) + React 19 | SPA, SSE streaming, BYOK UI |
| **Application** | FastAPI (Python async) + LangGraph | REST API, Agent orchestration |
| **Data** | PostgreSQL 16 + pgvector + MinIO | Relational data + vector store + file storage |

**Nguyên tắc thiết kế:**
- **Multi-tenant isolation**: Mỗi user sở hữu library riêng, dữ liệu hoàn toàn cách ly qua `user_id` filter trên mọi query.
- **Async-first**: Backend sử dụng `asyncpg`, `AsyncSession`, `asyncio.create_task` cho non-blocking I/O.
- **Mock-first development**: Chế độ `USE_MOCK_LLM=true` cho phép phát triển/test mà không cần API key thật.
- **Stateless API**: Backend không giữ state trong memory (trừ event queue tạm thời cho SSE stream).

---

## 2. Sơ đồ kiến trúc tổng thể

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

### 3.1 Kiến trúc tổng quan

Frontend sử dụng **Next.js 16 App Router** với React 19, TailwindCSS v4, và Vercel AI SDK.

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

### 3.2 Luồng xử lý Chat (SSE Streaming)

```
User nhập câu hỏi
    │
    ▼
ChatWindow.tsx
    │  POST /api/chat (body: messages, libraryId, sessionId)
    │  Headers: Authorization, X-Gemini-Key, X-Openai-Key, ...
    │
    ▼
SSE Stream nhận về:
    ├── <!--EVENT:{...}-->     → Real-time status (searching, quiz_batch, quiz_ready)
    ├── text chunks            → Hiển thị từng từ (word-by-word streaming)
    └── <!--METADATA_START--> → Citations, quiz_id (cuối stream)
```

### 3.3 State Management

- **Auth state**: `AuthContext` (React Context) → lưu JWT token vào `localStorage`
- **Chat state**: `useChat` custom hook → quản lý messages, streaming state, event queue
- **Library/Document state**: Local state trong page components, fetch trực tiếp từ API
- **Quiz state**: Nhận quiz_id từ SSE event → fetch quiz detail từ `/api/quizzes/:id`

---

## 4. Backend Architecture

### 4.1 Cấu trúc module

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
# Mọi route đều inject 2 dependencies chính:
async def endpoint(
    db: AsyncSession = Depends(get_db),           # Database session
    current_user: User = Depends(get_current_user) # JWT auth
):
```

- `get_db()`: Yield một `AsyncSession` từ `AsyncSessionLocal`, auto-close sau request.
- `get_current_user()`: Decode JWT từ header `Authorization: Bearer <token>`, trả về `User` ORM object.

### 4.3 Background Processing

Upload PDF sử dụng `asyncio.create_task()` để chạy ingestion pipeline nền:
```
Upload request → save to DB + MinIO → response 201
                                    ↓ (background)
                              _run_ingestion()
                                    │
                              ingest_document()
                              ├── Extract pages (PyMuPDF)
                              ├── Chunk text (1000 chars, 150 overlap)
                              ├── Generate embeddings (batch 50)
                              └── Store in document_chunks
```

---

## 5. AI Engine — Multi-Agent Graph

### 5.1 Main Agent Graph (Supervisor ReAct)

Hệ thống AI sử dụng **LangGraph StateGraph** với mô hình **ReAct** (Reasoning + Acting):

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
| Field | Type | Mô tả |
|-------|------|--------|
| `messages` | `list[BaseMessage]` | Lịch sử hội thoại LangChain |
| `library_id` | `str` | ID thư viện hiện tại |
| `session_id` | `str` | ID phiên chat |
| `user_id` | `str` | ID người dùng |
| `api_keys` | `dict` | BYOK keys (gemini, openai, anthropic, default) |
| `model_config` | `dict` | Model names cho từng role |
| `citations` | `list[dict]` | Trích dẫn từ search_documents |
| `quiz_draft` | `list[dict]` | Bộ câu hỏi đã sinh |
| `event_queue` | `asyncio.Queue` | Queue gửi SSE events real-time |

### 5.2 Tool: search_documents (RAG + HyDE)

```
User query: "Giải thích nguyên lý hoạt động của transistor"
    │
    ▼
┌── HyDE (Hypothetical Document Embeddings) ───────────────┐
│  LLM sinh 2 câu trả lời giả định:                       │
│  • "Transistor hoạt động dựa trên nguyên lý bán dẫn..."  │
│  • "Cấu trúc BJT gồm 3 lớp bán dẫn P-N-P hoặc N-P-N.." │
└──────────────────────────────────────────────────────────┘
    │
    ▼ Embed query gốc + 2 hypothetical answers (tổng 3 vectors)
    │
    ▼ pgvector cosine similarity (1 - embedding <=> query)
    │
    ▼ Deduplicate by chunk_id, lấy max score
    │
    ▼ Return top-20 chunks + citations
```

### 5.3 Tool: generate_quiz (Multi-Agent Subgraph)

Quiz Subgraph là một **StateGraph lồng** (nested graph) với 4 nodes và vòng lặp phản biện (reflection loop):

```
┌──────────────────────────────────────────────────────────────────────┐
│                       Quiz Subgraph                                  │
│                                                                      │
│  ┌───────┐    ┌───────────┐    ┌───────────┐    ┌─────────────┐     │
│  │ init  │───▶│ generator │───▶│ evaluator │───▶│ synthesizer │     │
│  │(plan) │    │  (sinh)   │    │ (đánh giá)│    │ (tổng hợp)  │     │
│  └───────┘    └─────┬─────┘    └─────┬─────┘    └──────┬──────┘     │
│                     ▲                │                  │            │
│                     │          rejected (≤2 lần)        │            │
│                     └────────────────┘                  │            │
│                                                         │            │
│               ┌─────────────────────────────────────────┘            │
│               │                                                      │
│         has_more_batches?                                            │
│         ├── yes → generator (batch tiếp theo)                        │
│         └── no  → END                                                │
└──────────────────────────────────────────────────────────────────────┘
```

**Chi tiết các node:**

| Node | Vai trò | Input | Output |
|------|---------|-------|--------|
| **init** | Lập kế hoạch batch, phân chia khía cạnh kiến thức (Structured LLM) | `num_questions`, `focus_topic` | `total_batches`, `aspect_hints[]` |
| **generator** | Sinh câu hỏi trắc nghiệm theo aspect_hint của batch hiện tại | context_chunks (HyDE search), aspect_hint | `draft_questions[]` |
| **evaluator** | Đánh giá chất lượng câu hỏi (approved/rejected + feedback) | `draft_questions[]` | `eval_feedback`, `eval_details` |
| **synthesizer** | Lọc câu hỏi đạt yêu cầu, gửi SSE `quiz_batch` event | `draft_questions[]`, `eval_feedback` | `accepted_questions[]` (append) |

**Quy tắc flow:**
- Evaluator rejected → generator regenerate (tối đa 2 lần retry/batch)
- Evaluator approved hoặc max retries → synthesizer
- Synthesizer xong batch → kiểm tra `has_more_batches`:
  - `current_batch >= total_batches` → END
  - `len(accepted_questions) >= num_questions` → END
  - Còn → tiếp tục generator cho batch tiếp

---

## 6. Database Schema (9 bảng)

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

### 6.2 Mô tả chi tiết các bảng

| # | Bảng | Mô tả | Quan hệ |
|---|------|--------|---------|
| 1 | `users` | Người dùng (email unique, bcrypt hash) | 1:N → libraries |
| 2 | `libraries` | Thư viện tài liệu (multi-tenant) | N:1 → users, 1:N → documents, sessions, quizzes |
| 3 | `documents` | File PDF đã upload | N:1 → libraries, 1:1 → ingestion_jobs, 1:N → chunks |
| 4 | `ingestion_jobs` | Tiến trình xử lý PDF (progress tracking) | 1:1 → documents |
| 5 | `document_chunks` | Chunk text + vector embedding (2048 dims) | N:1 → documents, libraries |
| 6 | `chat_sessions` | Phiên hội thoại trong thư viện | N:1 → libraries, 1:N → messages |
| 7 | `chat_messages` | Tin nhắn (user/assistant, citations JSONB) | N:1 → sessions, N:1 → quizzes |
| 8 | `quizzes` | Bộ đề trắc nghiệm | N:1 → libraries, 1:N → questions |
| 9 | `quiz_questions` | Câu hỏi trắc nghiệm (4 lựa chọn A/B/C/D) | N:1 → quizzes |

### 6.3 Indexes quan trọng

```sql
CREATE INDEX idx_libraries_user ON libraries(user_id);
CREATE INDEX idx_documents_library ON documents(library_id);
CREATE INDEX idx_chunks_library_user ON document_chunks(library_id, user_id);
CREATE INDEX idx_questions_quiz ON quiz_questions(quiz_id, order_index);
CREATE INDEX idx_messages_session ON chat_messages(session_id, created_at);
-- pgvector tự động tạo index cho cột VECTOR(2048)
```

---

## 7. Luồng xử lý dữ liệu chính

### 7.1 Luồng Upload & Ingestion

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

### 7.2 Luồng Chat (RAG)

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

### 7.3 Luồng Sinh Quiz

```
User: "Tạo 20 câu trắc nghiệm về chương 3"
    │
    ▼
Supervisor Agent → gọi tool generate_quiz(num_questions=20, focus_topic="chương 3")
    │
    ▼
Quiz Subgraph:
    │
    ├── init: Phân chia → 1 batch (20 câu ÷ 20/batch = 1 batch)
    │         Sinh aspect_hints bằng Structured LLM
    │
    ├── Batch 1:
    │   ├── generator: HyDE search → lấy context → LLM sinh 20 câu hỏi
    │   ├── evaluator: Đánh giá chất lượng → approved/rejected
    │   │   └── (nếu rejected) → generator lại (max 2 lần)
    │   └── synthesizer: Lọc câu đạt → gửi SSE quiz_batch event
    │
    ▼
Tool return: {quiz_draft: [...20 câu...], message: "Đã sinh xong 20 câu"}
    │
    ▼
Chat endpoint:
    ├── Auto-save quiz to DB (quizzes + quiz_questions tables)
    ├── Gửi SSE event: quiz_ready (quiz_id)
    ├── Persist assistant message to DB (chat_messages.quiz_id = ...)
    └── Stream text response + metadata
```

---

## 8. Cơ chế bảo mật

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

Mỗi query đều filter theo `user_id`:
```python
# Ví dụ: list libraries
select(Library).where(Library.user_id == current_user.id)

# Ví dụ: get document
doc = await db.get(Document, document_id)
if not doc or doc.user_id != current_user.id:
    raise HTTPException(404)
```

### 8.3 CORS

```python
allow_origins=[settings.FRONTEND_URL, "http://localhost:3000", "http://localhost:3001"]
allow_methods=["*"]
allow_headers=["*"]
allow_credentials=True
```

---

## 9. Thiết kế BYOK (Bring Your Own Key)

### 9.1 Mô hình 2 tầng (Two-tier Key Resolution)

```
                    ┌─────────────────┐
                    │  User BYOK Key  │  ← Ưu tiên 1 (từ HTTP header)
                    │  (per-request)   │
                    └────────┬────────┘
                             │
                     key tồn tại?
                    ┌────yes──┴──no────┐
                    │                  │
             ┌──────▼──────┐  ┌───────▼───────┐
             │ Dùng key    │  │ System key    │  ← Ưu tiên 2 (từ .env)
             │ của user    │  │ (.env)        │
             └─────────────┘  └───────────────┘
```

### 9.2 Provider Support

| Provider | Header | Models hỗ trợ |
|----------|--------|---------------|
| NVIDIA NIM (default) | System-only (.env) | deepseek-v4-pro-0813, deepseek-v4-flash-0731 |
| Google Gemini | `X-Gemini-Key` | gemini-2.5-flash, gemini-3.1-pro |
| OpenAI | `X-Openai-Key` | gpt-4o, gpt-4o-mini |
| Anthropic | `X-Anthropic-Key` | claude-3-5-sonnet, claude-3-5-haiku |

### 9.3 Quy tắc phân quyền key

| Loại key | User có thể cấu hình? | Mục đích |
|----------|----------------------|----------|
| Chat LLM key (gemini/openai/anthropic) | ✅ Có (BYOK) | Cho chat & quiz generation |
| System default key (NVIDIA NIM) | ❌ Không (admin-only) | Fallback khi user không có key |
| Embedding key | ❌ Không (admin-only) | Tạo embedding vectors (NVIDIA) |
]]>
