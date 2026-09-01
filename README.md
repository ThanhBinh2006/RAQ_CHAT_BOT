# 📚 Multi-Tenant Agentic RAG & Multi-Agent Quiz Platform (Library Workspace Edition)

> **Nền tảng Quản lý Kho Tri thức Độc lập (Knowledge Base / Library Workspace), tích hợp 01 Chatbot Supervisor duy nhất tự động phân loại ý định để gọi Tool RAG hoặc Tool Multi-Agent Sinh Đề Trắc Nghiệm (Tối đa 100 câu/lần) với Kiến trúc Multi-Agent Reflection & Dynamic Model Routing.**

---

## 🌟 1. Kiến trúc Tổng thể Hệ thống (System Architecture)

```
                                 [ Internet / Trình duyệt Người dùng ]
                                                   │
                                                   ▼
                                       [ Nginx Reverse Proxy (SSL) ]
                                                   │
                ┌──────────────────────────────────┼──────────────────────────────────┐
                │ (Đường dẫn /)                    │ (Đường dẫn /api)                 │ (Đường dẫn /s3)
                ▼                                  ▼                                  ▼
      ┌──────────────────┐               ┌──────────────────┐               ┌──────────────────┐
      │ Docker: Frontend │               │ Docker: Backend  │               │ Docker: MinIO    │
      │ React/CopilotKit │               │ FastAPI/LangGraph│               │ S3 Storage (PDF) │
      │ (Port 3000)      │               │ (Port 8000)      │               │ (Port 9000)      │
      └────────┬─────────┘               └────────┬─────────┘               └──────────────────┘
               │ (Gửi request kèm Header:         │ (Query Vector & Chat History)
               │  API Keys & Model Selection)     ▼
               │                        ┌──────────────────┐
               │                        │ Docker: Postgres │
               │                        │ + pgvector       │
               │                        │ (Port 5432 - Ẩn) │
               │                        └──────────────────┘
               │                                  │ (Gọi API tương ứng qua Internet)
               │                                  ▼
               │                        [ Multi-Provider LLM Gateway ]
               │                        ├── Google Gemini (2.5 Flash, 1.5 Pro, Flash 8B)
               │                        ├── Groq Cloud (Llama 3.3 70B, Mixtral, Gemma 2)
               │                        ├── OpenAI (GPT-4o, GPT-4o-mini)
               │                        └── Anthropic (Claude 3.5 Sonnet, 3.5 Haiku)
               │
               ▼
[ Frontend-side PDF Exporter ] ──► Xuất 2 bản: Bản Đề thi (Học sinh) & Bản Đáp án (Giáo viên)
```

---

## 🏛️ 2. Mô hình Thư viện Độc lập & Quản lý Tài liệu Động (Dynamic Knowledge Ingestion)

Kho tri thức trong mỗi Thư viện được quản lý theo cơ chế **Nạp Cộng Dồn (Incremental Ingestion)** và **Dùng Chung Đa Phiên Chat (Multi-Session Shared Vector Space)**:

- **Nạp một lần - Tái sử dụng vĩnh viễn:** Tài liệu PDF khi upload chỉ cần bóc tách và tính toán Vector Embeddings **đúng 1 lần duy nhất**.
- **Thêm tài liệu linh hoạt bất kỳ lúc nào (Không chỉ lúc tạo Thư viện):** Người dùng có thể upload bổ sung tài liệu mới vào Thư viện ở bất kỳ thời điểm nào. Hệ thống chỉ xử lý nhúng riêng file mới thêm (Incremental), **hoàn toàn không cần nhúng lại các file cũ**, tiết kiệm tối đa chi phí API Embeddings và thời gian.
- **Tức thời đồng bộ cho mọi đoạn chat:** Ngay khi file mới hoàn tất ingestion, **toàn bộ các đoạn chat (cũ lẫn mới)** trong Thư viện đó đều ngay lập tức truy vấn được vùng kiến thức mới mà không cần tạo lại phiên chat.
- **Quản lý & Xóa tài liệu chuẩn hóa:** Khi xóa một file PDF khỏi Thư viện, hệ thống tự động dọn sạch metadata trong MinIO và xóa toàn bộ chunks trong `document_chunks` (Cascade Delete), đảm bảo kho vector luôn chuẩn xác.

```
[ Người dùng (User Account) ]
   │
   ├── 📚 Thư viện A: "Giáo trình Mạng Máy Tính"
   │     ├── 📄 Tài liệu 1: "Giao thức TCP/IP.pdf" (Đã embed sẵn)
   │     ├── 📄 Tài liệu 2: "Bảo mật Mạng Nâng cao.pdf" (➕ Upload bổ sung thêm sau -> Chỉ embed file này)
   │     │
   │     ├── 💬 Đoạn chat 1: "Ôn tập kiến thức mô hình OSI 7 tầng"
   │     ├── 💬 Đoạn chat 2: "Nhờ giải chi tiết bài tập chia IP Subnet"
   │     └── 💬 Đoạn chat 3: "Tạo 50 câu trắc nghiệm ôn tập cuối kỳ"
   │     (👉 Mọi đoạn chat đều tự động truy vấn full kiến thức từ cả Tài liệu 1 & 2)
   │
   └── 📚 Thư viện B: "Lịch sử Đảng & Tư tưởng Hồ Chí Minh"
         └── 💬 Các đoạn chat độc lập truy vấn riêng kho Vector của Thư viện B
```

---

## 🗄️ 3. Thiết kế Cơ sở Dữ liệu Đầy đủ (PostgreSQL + pgvector)

Hệ thống sử dụng **9 bảng chuẩn hóa** gắn chặt với mô hình không gian Thư viện độc lập (`library_id`):

| Bảng | Chức năng chính | Các trường quan trọng |
| :--- | :--- | :--- |
| **`users`** | Quản lý tài khoản & xác thực JWT | `id` (UUID), `email`, `password_hash`, `first_name`, `last_name`, `created_at` |
| **`libraries`** | Quản lý Thư viện tri thức độc lập (Kho tài liệu riêng) | `id` (UUID), `user_id`, `name`, `description`, `icon_or_color`, `total_documents`, `created_at` |
| **`documents`** | Lưu metadata file PDF gốc đã upload vào Thư viện | `id` (UUID), `library_id`, `user_id`, `file_name`, `file_path_minio`, `total_pages`, `status`, `created_at` |
| **`ingestion_jobs`** | Theo dõi tiến độ bóc tách PDF nền (Progress Bar) | `id` (UUID), `document_id`, `total_chunks`, `processed_chunks`, `progress_percent`, `error_message`, `started_at`, `finished_at` |
| **`document_chunks`** | Lưu đoạn text & Vector Embeddings theo Thư viện | `id` (UUID), `library_id`, `document_id`, `user_id`, `page_number`, `chunk_index`, `content`, `embedding` (VECTOR 768), `metadata` (JSONB) |
| **`chat_sessions`** | Quản lý các phiên trò chuyện độc lập trong Thư viện | `id` (UUID), `library_id`, `user_id`, `title`, `created_at`, `updated_at` |
| **`chat_messages`** | Lưu chi tiết tin nhắn hội thoại kèm trích dẫn số trang | `id` (UUID), `session_id`, `role` (`user`/`assistant`), `content`, `citations` (JSONB), `quiz_id` (UUID), `created_at` |
| **`quizzes`** | Lưu thông tin chung của bộ đề thi trắc nghiệm | `id` (UUID), `library_id`, `user_id`, `title`, `description`, `total_questions`, `is_edited_by_user`, `created_at`, `updated_at` |
| **`quiz_questions`** | Lưu chi tiết từng câu hỏi (chuẩn hóa thay vì dồn JSON) | `id` (UUID), `quiz_id`, `order_index`, `question_text`, `option_a`, `option_b`, `option_c`, `option_d`, `correct_answer`, `explanation`, `source_page` |

---

## 🤖 4. Kiến trúc 01 Chatbot Supervisor Điều phối 2 Tools (Agentic Router Workflow)

Người dùng tương tác qua **1 khung chat duy nhất**. Chatbot đóng vai trò là **Agent Supervisor** (sử dụng LangGraph Function Calling / Tool Calling) để tự động phân tích câu lệnh và quyết định luồng xử lý:

```
                          [ Tin nhắn từ Người dùng ]
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │   🤖 CHATBOT SUPERVISOR   │
                        │ (LangGraph Router / LLM)  │
                        └─────────────┬─────────────┘
                                      │
               ┌──────────────────────┼──────────────────────┐
               │                      │                      │
               ▼                      ▼                      ▼
        [1. Chat thông thường]  [2. Hỏi đáp RAG]       [3. Yêu cầu tạo đề]
               │                      │                      │
               ▼                      ▼                      ▼
        (Trả lời ngay)        ┌──────────────┐       ┌──────────────────────┐
                              │    TOOL 1    │       │        TOOL 2        │
                              │ (rag_search) │       │ (quiz_generator)     │
                              │ + Citations  │       │ Multi-Agent Batching │
                              └──────────────┘       └──────────┬───────────┘
                                                                │
                                                                ▼
                                                     [ Trả về Interactive   ]
                                                     [ Quiz UI Component    ]
```

### Chi tiết 2 Tools do Chatbot điều phối:

#### Tool 1: `rag_search_tool` (Hỏi đáp & Tra cứu Ngữ cảnh)
- **Kích hoạt khi:** Người dùng hỏi đáp kiến thức, nhờ giải thích, phân tích, tóm tắt nội dung tài liệu.
- **Xử lý:** Truy vấn Vector trong `document_chunks` theo `library_id` và `user_id` $\rightarrow$ Đưa chunks liên quan vào LLM $\rightarrow$ Trả lời kèm trích dẫn số trang (`citations`).

#### Tool 2: `quiz_generator_tool` (Sinh Đề Trắc Nghiệm Multi-Agent - Tối đa 100 câu)
- **Kích hoạt khi:** Người dùng yêu cầu *"tạo đề thi"*, *"tạo 30 câu trắc nghiệm"*, *"sinh câu hỏi ôn tập"*. Chatbot tự động trích xuất tham số `num_questions` ($N \le 100$) và `focus_topic`.
- **Cơ chế Batching tuần tự:** Chia $N$ câu thành các batch nhỏ ($15 - 20\text{ câu/batch}$) qua chu trình 3 Agent:
  1. **Generator Node:** Sinh bản nháp trắc nghiệm 4 lựa chọn A/B/C/D.
  2. **Evaluator Node:** Kiểm duyệt kiến thức bám sát tài liệu gốc, bắt lỗi đáp án mập mờ, loại bỏ hallucination.
  3. **Synthesizer Node:** Chuẩn hóa dữ liệu và xuất đúng **Strict Pydantic JSON Schema**.
- **Generative UI:** Kết quả trả về dưới dạng Widget **Interactive Quiz Editor** ngay trong khung chat để người dùng sửa trực tiếp trước khi bấm *Lưu vào Database* hoặc *Xuất PDF*.

---

## ⚙️ 5. Quản lý API Key & Định tuyến Model Động (Dynamic BYOK & 2-Tier Fallback)

Hệ thống kết hợp linh hoạt giữa **Khóa hệ thống (System Key)** và **Khóa người dùng (User BYOK)** theo cơ chế **Fallback 2 tầng**:

```
                       [ Yêu cầu từ Client gửi lên ]
                                     │
                                     ▼
                     Kiểm tra Header (User BYOK Key)?
                                     │
                    ┌────────────────┴────────────────┐
                    │ [CÓ KEY]                        │ [KHÔNG CÓ KEY]
                    ▼                                 ▼
      (Dùng Key của User)               (Fallback dùng System Key trong .env)
      - Chatbot Supervisor              - Ingestion Embedding (text-embedding-004)
      - Generator, Evaluator, Synth     - Auto-Title Session & Chat RAG dùng thử
```

### A. Xử lý các tác vụ nền & API Ẩn (System Cloud API)
- **Bản chất:** Các tác vụ ngầm (như nhúng Vector `text-embedding-004`, tự động tóm tắt/đặt tên session) vẫn gọi **Cloud API qua Internet** từ phía Backend, **hoàn toàn không ngốn RAM/CPU của Server** (rất nhẹ, chạy hoàn hảo trên VPS 2 Core - 4GB RAM).
- **Chuẩn hóa Vector 768 chiều:** Database sử dụng kiểu dữ liệu `VECTOR(768)`. Hệ thống cố định model `text-embedding-004` của Gemini để đảm bảo đồng nhất số chiều vector, tự động sử dụng `SYSTEM_GEMINI_API_KEY` từ `.env` nếu người dùng không truyền key Gemini.
- **Bảo mật:** `SYSTEM_*_API_KEY` được lưu an toàn trong file `.env` trên Server, tuyệt đối không lộ ra Frontend.

### B. Cơ chế Kích hoạt Model theo Key Người dùng (User BYOK)
- Người dùng vào mục **Cài đặt (Settings)** nhập API Key của bất kỳ bên nào: **Google Gemini**, **Groq**, **OpenAI**, hoặc **Anthropic**.
- Key lưu tại `localStorage` trên trình duyệt (nhập 1 lần, không mất khi Logout, không lưu vào CSDL).
- Khi có Key của bên nào $\rightarrow$ Hệ thống tự động **Enable** danh sách Model tương ứng:
  - *Có Gemini Key:* `gemini-2.5-flash`, `gemini-1.5-pro`, `gemini-1.5-flash-8b`.
  - *Có Groq Key:* `llama-3.3-70b-versatile`, `mixtral-8x7b-32768`, `gemma2-9b-it`.
  - *Có OpenAI Key:* `gpt-4o-mini`, `gpt-4o`.
  - *Có Anthropic Key:* `claude-3-5-haiku`, `claude-3-5-sonnet`.

### C. Phân bổ Model Độc lập Cho Từng Vai Trò (Per-Agent Model Assignment)
- Cho phép người dùng tùy biến chọn model riêng cho Chatbot Supervisor, Generator, Evaluator và Synthesizer.
- Hỗ trợ chạy hoàn hảo cả khi người dùng **chỉ có duy nhất 1 API Key** (tự động dùng chung cho toàn bộ các node).
- Frontend gửi cấu hình qua Headers (`X-Generator-Model`, `X-Evaluator-Model`, `X-Synthesizer-Model` kèm API Keys). Backend dùng `llm_factory.py` để inject instance phù hợp vào từng Node trong LangGraph.

### D. Mẫu Cấu hình Môi trường Backend (`.env`)
```env
# Database & MinIO Storage
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/raq_chatbot
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
JWT_SECRET_KEY=your_super_secret_jwt_key

# System Cloud API Keys (Dành cho Ingestion Embeddings & Tác vụ ngầm)
SYSTEM_GEMINI_API_KEY=AIzaSy...
SYSTEM_GROQ_API_KEY=gsk_...
```

---

## 📄 6. Quy trình Ingestion & Xuất Đề Thi PDF

### A. Pipeline Nạp File PDF vào Thư viện
1. Upload file PDF vào Thư viện $\rightarrow$ Lưu file gốc trên **MinIO** (`pdf-storage`).
2. Tạo job trong `ingestion_jobs` để theo dõi tiến độ nền (Progress Bar).
3. `PyMuPDF` (`fitz`) đọc text theo trang $\rightarrow$ `RecursiveCharacterTextSplitter` cắt chunk ($1000\text{ ký tự}$, overlap $150$).
4. Tạo Vector Embedding $\rightarrow$ Lưu vào `document_chunks` (gắn nhãn `library_id`).

### B. Xuất Đề Thi Ra File PDF (Client-side Export)
- Render trực tiếp trên trình duyệt bằng `@react-pdf/renderer` hoặc `html2pdf.js` / `jspdf` (không tốn tài nguyên server).
- Hỗ trợ 2 phiên bản xuất:
  1. **Bản Đề thi (Học sinh):** Tiêu đề, Hướng dẫn, Câu hỏi và 4 lựa chọn A/B/C/D.
  2. **Bản Đáp án (Giáo viên / Giải chi tiết):** Đề thi + Đánh dấu đáp án đúng + Khung giải thích chi tiết trích từ tài liệu.

---

## 📅 7. Lộ trình Triển khai Code Từng Bước (Action Checklist)

```
[Tuần 1: Môi trường & DB] ──► [Tuần 2: Backend LangGraph] ──► [Tuần 3: Frontend & PDF] ──► [Tuần 4: Deploy & CV]
```

- [ ] **Bước 1 (Setup Local):** Viết file `docker-compose.yml` chạy PostgreSQL (`pgvector`) và MinIO. Chạy script tạo 9 bảng SQL DDL chuẩn Thư viện độc lập.
- [ ] **Bước 2 (Ingestion & Library Multi-Session API):** Viết endpoint FastAPI upload PDF vào Thư viện $\rightarrow$ lưu MinIO $\rightarrow$ PyMuPDF chunking $\rightarrow$ lưu vector vào `document_chunks` kèm `library_id`; viết CRUD API cho `libraries`, `chat_sessions` và `chat_messages`.
- [ ] **Bước 3 (LangGraph Single Supervisor & 2 Tools Engine):**
  - Xây dựng Dynamic LLM Factory nhận API Keys và Model Name tương ứng của từng Agent từ Header (`X-Generator-Model`, `X-Evaluator-Model`, `X-Synthesizer-Model`).
  - Xây dựng Agent Supervisor tự động router gọi `rag_search_tool` hoặc `quiz_generator_tool`.
  - Xây dựng Sequential Batch loop trong Tool 2 chạy cụm 3-Agent đa model xuất JSON Schema.
- [ ] **Bước 4 (Frontend UI 3 Cột NotebookLM):**
  - Cột 1: Quản lý Thư viện, danh sách file PDF và thanh tiến độ Ingestion.
  - Cột 2: Quản lý các đoạn chat (Sessions) trong Thư viện hiện tại.
  - Cột 3: Khung Chat Supervisor CopilotKit tích hợp Component **Interactive Quiz Editor** sửa câu hỏi/đáp án.
  - Modal Cài đặt API Key: Tự động kích hoạt model theo key và cho phép gán model riêng cho từng vai trò.
  - Viết module xuất file PDF 2 chế độ (Học sinh & Giáo viên).
- [ ] **Bước 5 (Deploy lên VPS CloudFly):**
  - Thuê VPS 2 Core - 4GB RAM (~100k - 150k/tháng tại CloudFly).
  - Cài Docker, tạo 4GB Swap RAM, cấu hình Nginx + SSL Certbot miễn phí.
  - Chạy `docker-compose up -d --build` toàn bộ hệ thống.
- [ ] **Bước 6 (Ghi vào CV):**
  - Đính kèm link Live Demo, GitHub repo.
  - Ghi nổi bật: *Agentic Supervisor Router Architecture, Multi-Tenant Knowledge Base RAG, Dynamic Multi-Provider Heterogeneous Multi-Agent Quiz Engine, Pydantic Structured Output, Zero Re-embedding Multi-Session Persistence, PostgreSQL pgvector, Client-side Dual-mode PDF Generator*.
