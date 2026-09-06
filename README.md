<![CDATA[# 📚 RAQ Chatbot — Retrieval-Augmented Quiz Generation Platform

> **Nền tảng Chatbot học tập thông minh** tích hợp kỹ thuật RAG (Retrieval-Augmented Generation) và hệ thống Multi-Agent AI để tự động tạo đề thi trắc nghiệm bám sát tài liệu PDF do người dùng tải lên.

---

## 📑 Mục lục

- [1. Giới thiệu bài toán](#1-giới-thiệu-bài-toán)
- [2. Stack công nghệ](#2-stack-công-nghệ)
- [3. Yêu cầu môi trường](#3-yêu-cầu-môi-trường)
- [4. Biến môi trường](#4-biến-môi-trường)
- [5. Khởi chạy dự án](#5-khởi-chạy-dự-án)
  - [5.1 Chạy Local (Dev Mode)](#51-chạy-local-dev-mode)
  - [5.2 Chạy bằng Docker Compose (toàn bộ)](#52-chạy-bằng-docker-compose-toàn-bộ)
- [6. Tài liệu bổ sung](#6-tài-liệu-bổ-sung)
- [7. Cấu trúc thư mục](#7-cấu-trúc-thư-mục)

---

## 1. Giới thiệu bài toán

**RAQ Chatbot** giải quyết bài toán hỗ trợ học tập cá nhân hóa:

| Vấn đề | Giải pháp RAQ |
|--------|---------------|
| Đọc tài liệu PDF dài, không biết bắt đầu từ đâu | Upload PDF → chatbot tự trích xuất, lập chỉ mục vector |
| Tự kiểm tra kiến thức khó khăn | Multi-Agent AI tự động sinh đề trắc nghiệm bám sát tài liệu |
| Cần tra cứu nhanh nội dung tài liệu | HyDE RAG search với trích dẫn nguồn (số trang, tên file) |
| Đề thi chất lượng không đồng đều | Quy trình Generator → Evaluator → Synthesizer với vòng lặp phản biện |

**Tính năng chính:**
- 🔐 Hệ thống đa người dùng (Multi-tenant) với JWT authentication
- 📂 Tổ chức tài liệu theo Thư viện (Library) độc lập
- 📤 Upload PDF → tự động trích xuất text, chia chunk, tạo embedding vector (2048 dims)
- 💬 Chat AI bám sát tài liệu với kỹ thuật HyDE (Hypothetical Document Embeddings)
- 📝 Sinh đề trắc nghiệm tự động theo batch (Generator → Evaluator → Synthesizer)
- ✏️ Chỉnh sửa đề thi inline, xuất PDF
- ⚙️ BYOK (Bring Your Own Key) — hỗ trợ Gemini, OpenAI, Anthropic

---

## 2. Stack công nghệ

| Layer | Công nghệ | Phiên bản |
|-------|-----------|-----------|
| **Frontend** | Next.js (App Router), React, TailwindCSS v4, Vercel AI SDK | Next 16.x, React 19.x |
| **Backend** | FastAPI (Python, Async) | 0.115+ |
| **AI Engine** | LangChain + LangGraph (Multi-Agent StateGraph) | LangChain 0.3.x, LangGraph 0.2.x |
| **Database** | PostgreSQL + pgvector (Vector 2048 dims) | PG 16 + pgvector |
| **Object Storage** | MinIO (S3-compatible) | Latest |
| **PDF Processing** | PyMuPDF (fitz) | 1.24+ |
| **Embedding** | NVIDIA NeMo Retriever / Nemotron-3-Embed-1B | 2048 dims |
| **LLM mặc định** | DeepSeek V4 Pro (qua NVIDIA NIM) | deepseek-v4-pro-0813 |
| **Auth** | JWT (python-jose), bcrypt | HS256, 24h TTL |

---

## 3. Yêu cầu môi trường

### Phần cứng tối thiểu
| Tài nguyên | Yêu cầu |
|-----------|---------|
| RAM | ≥ 8 GB (khuyến nghị 16 GB cho Docker) |
| Dung lượng đĩa | ≥ 10 GB trống |
| CPU | 4 cores trở lên |

### Phần mềm bắt buộc
| Phần mềm | Phiên bản tối thiểu | Ghi chú |
|----------|---------------------|---------|
| **Node.js** | ≥ 20.x | Cho frontend Next.js |
| **Python** | ≥ 3.11 | Cho backend FastAPI |
| **Docker** | ≥ 24.x | Cho Docker Compose mode |
| **Docker Compose** | ≥ 2.20 | Plugin V2 (tích hợp Docker) |
| **Git** | ≥ 2.40 | Clone repository |

---

## 4. Biến môi trường

Sao chép file mẫu và cấu hình các biến:

```bash
cp backend/.env.example backend/.env
```

| Biến | Mô tả | Giá trị mặc định |
|------|--------|-------------------|
| `DATABASE_URL` | Connection string PostgreSQL (async) | `postgresql+asyncpg://postgres:postgres@localhost:5432/raq_chatbot` |
| `MINIO_ENDPOINT` | Địa chỉ MinIO server | `localhost:9000` |
| `MINIO_ACCESS_KEY` | MinIO access key | `minioadmin` |
| `MINIO_SECRET_KEY` | MinIO secret key | `minioadmin` |
| `MINIO_BUCKET_NAME` | Tên bucket lưu PDF | `pdf-storage` |
| `MINIO_USE_SSL` | Dùng SSL cho MinIO | `false` |
| `JWT_SECRET_KEY` | Khóa bí mật ký JWT | ⚠️ **Đổi trong production** |
| `JWT_ALGORITHM` | Thuật toán ký JWT | `HS256` |
| `JWT_EXPIRE_MINUTES` | Thời gian hết hạn token (phút) | `1440` (24 giờ) |
| `SYSTEM_DEFAULT_API_KEY` | API key hệ thống cho LLM (NVIDIA NIM) | *(bắt buộc khi `USE_MOCK_LLM=false`)* |
| `SYSTEM_DEFAULT_EMBEDDING_KEY` | API key riêng cho embedding model | *(nếu không set → dùng `SYSTEM_DEFAULT_API_KEY`)* |
| `SYSTEM_DEFAULT_API_BASE` | Base URL cho LLM API | `https://integrate.api.nvidia.com/v1` |
| `DEFAULT_CHAT_MODEL` | Model LLM mặc định cho chat/quiz | `deepseek-ai/deepseek-v4-pro-0813` |
| `DEFAULT_EMBEDDING_MODEL` | Model embedding mặc định | `nvidia/nemotron-3-embed-1b` |
| `USE_MOCK_LLM` | Chế độ mock (không cần API key thật) | `true` |
| `FRONTEND_URL` | URL frontend cho CORS | `http://localhost:3000` |

> **📌 Lưu ý**: Ở chế độ `USE_MOCK_LLM=true`, hệ thống sẽ hoạt động bình thường mà **không cần API key thật** — embedding tạo bằng hash, LLM trả phản hồi mock. Phù hợp để demo, phát triển và chấm điểm.

Frontend sử dụng biến môi trường:

```env
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 5. Khởi chạy dự án

### 5.1 Chạy Local (Dev Mode)

**Bước 1: Clone repository**
```bash
git clone <repository-url>
cd RAQ_CHAT_BOT
```

**Bước 2: Khởi động PostgreSQL + MinIO (Docker)**
```bash
docker compose up -d postgres minio
```
> Chờ khoảng 10-15s để services healthy. Database schema sẽ tự động được khởi tạo từ `sql/init.sql`.

**Bước 3: Cài đặt Backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # Chỉnh sửa .env nếu cần
```

**Bước 4: Khởi chạy Backend**
```bash
uvicorn app.main:app --reload --port 8000
```
> Backend sẵn sàng tại `http://localhost:8000`
> API docs: `http://localhost:8000/docs`

**Bước 5: Cài đặt Frontend**
```bash
cd ../frontend
npm install
```

**Bước 6: Khởi chạy Frontend**
```bash
npm run dev
```
> Frontend sẵn sàng tại `http://localhost:3000`

---

### 5.2 Chạy bằng Docker Compose (toàn bộ)

**Khởi chạy toàn bộ 4 services:**
```bash
# Tạo file .env cho backend (nếu chưa có)
cp backend/.env.example backend/.env

# Build và chạy
docker compose up --build -d
```

**Kiểm tra trạng thái:**
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

**Dừng toàn bộ:**
```bash
docker compose down          # Giữ data
docker compose down -v       # Xóa cả volumes (mất dữ liệu)
```

---

## 6. Tài liệu bổ sung

| File | Nội dung |
|------|----------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Kiến trúc hệ thống, sơ đồ luồng dữ liệu, thiết kế Agent Graph |
| [API.md](./API.md) | Đặc tả API RESTful chi tiết (endpoint, request/response, mã lỗi) |
| [USECASES.md](./USECASES.md) | Đặc tả Use Case theo Cockburn (UC-01 → UC-08) |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Hướng dẫn triển khai production, Docker, giám sát |

---

## 7. Cấu trúc thư mục

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
│   │   │                   ├── generator_node.py   # Sinh câu hỏi
│   │   │                   ├── evaluator_node.py   # Đánh giá chất lượng
│   │   │                   └── synthesizer_node.py # Tổng hợp batch
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
└── README.md                   # ← Bạn đang ở đây
```
]]>
