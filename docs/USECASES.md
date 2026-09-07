# 📋 USECASES.md — Đặc tả Use Case theo Cockburn

> Tài liệu đặc tả các Use Case chính của RAQ Chatbot, trình bày theo khuôn mẫu **Cockburn (Fully-dressed)**.

---

## 📑 Mục lục

- [UC-01: Đăng ký tài khoản](#uc-01-đăng-ký-tài-khoản)
- [UC-02: Đăng nhập hệ thống](#uc-02-đăng-nhập-hệ-thống)
- [UC-03: Quản lý Thư viện tài liệu](#uc-03-quản-lý-thư-viện-tài-liệu)
- [UC-04: Upload và xử lý tài liệu PDF](#uc-04-upload-và-xử-lý-tài-liệu-pdf)
- [UC-05: Chat hỏi đáp bám sát tài liệu (RAG)](#uc-05-chat-hỏi-đáp-bám-sát-tài-liệu-rag)
- [UC-06: Tạo đề trắc nghiệm tự động](#uc-06-tạo-đề-trắc-nghiệm-tự-động)
- [UC-07: Chỉnh sửa và lưu đề trắc nghiệm](#uc-07-chỉnh-sửa-và-lưu-đề-trắc-nghiệm)
- [UC-08: Xuất đề trắc nghiệm PDF](#uc-08-xuất-đề-trắc-nghiệm-pdf)
- [Sơ đồ Use Case tổng quan](#sơ-đồ-use-case-tổng-quan)

---

## UC-01: Đăng ký tài khoản

| Thuộc tính | Chi tiết |
|-----------|----------|
| **Mã UC** | UC-01 |
| **Tên** | Đăng ký tài khoản mới |
| **Mức độ** | User Goal |
| **Tác nhân chính** | Người dùng (Student/Teacher) |
| **Tác nhân phụ** | Hệ thống backend |
| **Mô tả** | Người dùng tạo tài khoản mới bằng email và mật khẩu để truy cập hệ thống |
| **Tiền điều kiện** | Người dùng chưa có tài khoản |
| **Hậu điều kiện** | Tài khoản được tạo trong DB, người dùng có thể đăng nhập |

### Luồng chính (Main Success Scenario)

| Bước | Tác nhân | Hành động |
|------|---------|-----------|
| 1 | Người dùng | Truy cập trang `/auth/register` |
| 2 | Người dùng | Nhập email, mật khẩu, họ tên |
| 3 | Người dùng | Nhấn nút "Đăng ký" |
| 4 | Hệ thống | Kiểm tra email chưa tồn tại trong DB |
| 5 | Hệ thống | Hash mật khẩu bằng bcrypt |
| 6 | Hệ thống | Tạo bản ghi User mới trong bảng `users` |
| 7 | Hệ thống | Trả về thông tin user (201 Created) |
| 8 | Frontend | Chuyển hướng người dùng đến trang đăng nhập |

### Luồng thay thế (Alternate Flows)

| Bước | Điều kiện | Hành động |
|------|-----------|-----------|
| 4a | Email đã tồn tại | Hệ thống trả về lỗi 409 "Email đã được đăng ký" |
| 3a | Email không hợp lệ | Frontend/Backend validation lỗi 422 |
| 3b | Mật khẩu quá ngắn | Frontend hiển thị thông báo lỗi |

### Mapping kỹ thuật

| Component | File | Endpoint/Function |
|-----------|------|-------------------|
| Backend route | `backend/app/api/routes/auth.py` | `POST /api/auth/register` |
| Schema | `backend/app/schemas/auth.py` | `RegisterRequest`, `UserOut` |
| Frontend page | `frontend/src/app/auth/register/page.tsx` | Register form component |

---

## UC-02: Đăng nhập hệ thống

| Thuộc tính | Chi tiết |
|-----------|----------|
| **Mã UC** | UC-02 |
| **Tên** | Đăng nhập hệ thống |
| **Mức độ** | User Goal |
| **Tác nhân chính** | Người dùng đã đăng ký |
| **Mô tả** | Người dùng đăng nhập bằng email/password để nhận JWT token |
| **Tiền điều kiện** | Đã có tài khoản (UC-01 hoàn thành) |
| **Hậu điều kiện** | JWT token được lưu vào localStorage, người dùng truy cập Dashboard |

### Luồng chính

| Bước | Tác nhân | Hành động |
|------|---------|-----------|
| 1 | Người dùng | Truy cập trang `/auth/login` |
| 2 | Người dùng | Nhập email và mật khẩu |
| 3 | Người dùng | Nhấn "Đăng nhập" |
| 4 | Hệ thống | Tìm User theo email trong DB |
| 5 | Hệ thống | Verify password bằng bcrypt |
| 6 | Hệ thống | Tạo JWT token (HS256, exp=24h) |
| 7 | Hệ thống | Trả về `{access_token, token_type}` |
| 8 | Frontend | Lưu token vào `localStorage` |
| 9 | Frontend | Chuyển hướng đến Dashboard (`/`) |

### Luồng thay thế

| Bước | Điều kiện | Hành động |
|------|-----------|-----------|
| 4a | Email không tồn tại | Trả lỗi 401 "Email hoặc mật khẩu không đúng" |
| 5a | Password sai | Trả lỗi 401 (cùng message để không leak info) |
| 8a | Token hết hạn (sau 24h) | Frontend redirect về `/auth/login` |

### Mapping kỹ thuật

| Component | File | Endpoint/Function |
|-----------|------|-------------------|
| Backend route | `backend/app/api/routes/auth.py` | `POST /api/auth/login` |
| Security | `backend/app/core/security.py` | `verify_password()`, `create_access_token()` |
| Frontend page | `frontend/src/app/auth/login/page.tsx` | Login form component |
| Auth context | `frontend/src/lib/auth-context.tsx` | `AuthProvider`, `useAuth()` |

---

## UC-03: Quản lý Thư viện tài liệu

| Thuộc tính | Chi tiết |
|-----------|----------|
| **Mã UC** | UC-03 |
| **Tên** | Tạo, xem, xóa Thư viện tài liệu |
| **Mức độ** | User Goal |
| **Tác nhân chính** | Người dùng đã đăng nhập |
| **Mô tả** | Người dùng tổ chức tài liệu theo Thư viện (Library) riêng biệt |
| **Tiền điều kiện** | Đã đăng nhập (UC-02) |
| **Hậu điều kiện** | Library được tạo/xóa thành công |

### Luồng chính — Tạo thư viện

| Bước | Tác nhân | Hành động |
|------|---------|-----------|
| 1 | Người dùng | Tại Dashboard, nhấn nút "Tạo thư viện mới" |
| 2 | Người dùng | Nhập tên thư viện, mô tả (tùy chọn), chọn màu icon |
| 3 | Người dùng | Nhấn "Tạo" |
| 4 | Hệ thống | Tạo bản ghi Library (user_id = current_user) |
| 5 | Frontend | Cập nhật danh sách thư viện, hiển thị thư viện mới |

### Luồng chính — Xóa thư viện

| Bước | Tác nhân | Hành động |
|------|---------|-----------|
| 1 | Người dùng | Nhấn nút xóa trên thư viện |
| 2 | Frontend | Hiển thị dialog xác nhận |
| 3 | Người dùng | Xác nhận xóa |
| 4 | Hệ thống | CASCADE DELETE: xóa library + documents + chunks + sessions + messages + quizzes |
| 5 | Frontend | Cập nhật danh sách thư viện |

### Mapping kỹ thuật

| Component | File | Endpoint |
|-----------|------|----------|
| Backend route | `backend/app/api/routes/libraries.py` | `GET/POST /api/libraries`, `DELETE /api/libraries/{id}` |
| Frontend page | `frontend/src/app/page.tsx` | Dashboard (Library grid) |

---

## UC-04: Upload và xử lý tài liệu PDF

| Thuộc tính | Chi tiết |
|-----------|----------|
| **Mã UC** | UC-04 |
| **Tên** | Upload tài liệu PDF vào thư viện |
| **Mức độ** | User Goal |
| **Tác nhân chính** | Người dùng đã đăng nhập |
| **Tác nhân phụ** | MinIO (S3), NVIDIA Embedding API |
| **Mô tả** | Upload file PDF → lưu MinIO → trích xuất text → chia chunk → tạo embedding vector |
| **Tiền điều kiện** | Đã tạo ít nhất 1 thư viện (UC-03) |
| **Hậu điều kiện** | File PDF được lưu trữ, chunks + embeddings sẵn sàng cho RAG search |

### Luồng chính

| Bước | Tác nhân | Hành động |
|------|---------|-----------|
| 1 | Người dùng | Mở trang thư viện `/libraries/{id}` |
| 2 | Người dùng | Nhấn nút "Upload tài liệu" trên sidebar |
| 3 | Người dùng | Chọn file PDF từ máy tính |
| 4 | Frontend | Gửi `POST /api/documents/upload` (multipart/form-data) |
| 5 | Hệ thống | Validate: file phải là `.pdf`, thư viện thuộc user |
| 6 | Hệ thống | Upload file lên MinIO bucket `pdf-storage` |
| 7 | Hệ thống | Tạo bản ghi Document (status: `processing`) và IngestionJob |
| 8 | Hệ thống | Trả về 201 Created ngay lập tức |
| 9 | Hệ thống | **Background task** bắt đầu ingestion pipeline: |
| 9a | | PyMuPDF trích xuất text theo từng trang |
| 9b | | RecursiveCharacterTextSplitter chia chunk (1000 chars, overlap 150) |
| 9c | | NVIDIA Embedding API tạo vector 2048 dims (batch 32) |
| 9d | | Lưu chunks + embeddings vào bảng `document_chunks` |
| 10 | Frontend | Polling `GET /api/documents/{id}/progress` mỗi 2 giây |
| 11 | Frontend | Hiển thị progress bar (processed_chunks / total_chunks) |
| 12 | Hệ thống | Khi hoàn tất: status → `ready`, progress → 100% |

### Luồng thay thế

| Bước | Điều kiện | Hành động |
|------|-----------|-----------|
| 5a | File không phải PDF | Trả lỗi 400 "Chỉ chấp nhận file PDF" |
| 9d-a | Embedding API lỗi | Document status → `failed`, error_message ghi nhận |
| 9d-b | Mock mode (`USE_MOCK_LLM=true`) | Tạo pseudo-embedding bằng SHA-256 hash |

### Mapping kỹ thuật

| Component | File | Function |
|-----------|------|----------|
| Backend route | `backend/app/api/routes/documents.py` | `upload_document()`, `get_progress()` |
| Ingestion | `backend/app/services/ingestion_service.py` | `ingest_document()` |
| Storage | `backend/app/services/storage_service.py` | `upload_file()` |
| Frontend | `frontend/src/components/library/LibrarySidebar.tsx` | Upload UI + progress polling |

---

## UC-05: Chat hỏi đáp bám sát tài liệu (RAG)

| Thuộc tính | Chi tiết |
|-----------|----------|
| **Mã UC** | UC-05 |
| **Tên** | Hỏi đáp tài liệu qua chatbot AI |
| **Mức độ** | User Goal |
| **Tác nhân chính** | Người dùng đã đăng nhập |
| **Tác nhân phụ** | LLM (DeepSeek/Gemini/GPT/Claude), pgvector |
| **Mô tả** | Người dùng đặt câu hỏi → AI tìm kiếm tài liệu (RAG + HyDE) → trả lời có trích dẫn |
| **Tiền điều kiện** | Thư viện có ít nhất 1 document ở trạng thái `ready` |
| **Hậu điều kiện** | Câu trả lời hiển thị real-time với citations (trang, tên file) |

### Luồng chính

| Bước | Tác nhân | Hành động |
|------|---------|-----------|
| 1 | Người dùng | Mở thư viện, chọn/tạo phiên chat |
| 2 | Người dùng | Nhập câu hỏi (ví dụ: "Giải thích nguyên lý transistor") |
| 3 | Frontend | `POST /api/chat` (SSE stream, kèm messages history, libraryId, sessionId) |
| 4 | Hệ thống | Lưu tin nhắn user vào DB (`chat_messages`) |
| 5 | Hệ thống | Cập nhật tiêu đề session tự động (nếu chưa đặt tên) |
| 6 | Agent | Supervisor Agent phân tích intent → quyết định gọi `search_documents` |
| 7 | Agent | **HyDE**: LLM sinh 2 câu trả lời giả định |
| 8 | Agent | Embed query gốc + 2 hypothetical answers → 3 vectors |
| 9 | Agent | pgvector cosine similarity → top-20 chunks (deduplicated) |
| 10 | Frontend | SSE event: `tool_status` (searching → completed, N trích dẫn) |
| 11 | Agent | Supervisor tổng hợp câu trả lời từ context chunks |
| 12 | Frontend | Stream text word-by-word (15ms/word) |
| 13 | Frontend | Nhận metadata footer: citations (page, file, document_id) |
| 14 | Hệ thống | Background: lưu tin nhắn assistant vào DB |

### Luồng thay thế

| Bước | Điều kiện | Hành động |
|------|-----------|-----------|
| 6a | Câu hỏi chào hỏi / ngoài lề | Agent trả lời trực tiếp, không gọi tool |
| 9a | Không tìm thấy chunk liên quan | Trả "Không tìm thấy tài liệu liên quan" |
| 11a | LLM rate limit (429) | Format friendly error, hướng dẫn đợi N giây |
| 11b | API key lỗi (401/403) | Thông báo kiểm tra API key trong Settings |

### Mapping kỹ thuật

| Component | File | Function |
|-----------|------|----------|
| Chat endpoint | `backend/app/api/routes/chat.py` | `chat_endpoint()`, `generate_stream()` |
| Agent graph | `backend/app/agents/assistant/graph.py` | `build_assistant_graph()` |
| RAG tool | `backend/app/agents/assistant/tools/search_documents.py` | `search_documents()` |
| Vector search | `backend/app/services/vector_store.py` | `similarity_search()` + HyDE |
| Frontend | `frontend/src/components/chat/ChatWindow.tsx` | Chat UI + SSE parsing |

---

## UC-06: Tạo đề trắc nghiệm tự động

| Thuộc tính | Chi tiết |
|-----------|----------|
| **Mã UC** | UC-06 |
| **Tên** | AI tự động sinh đề trắc nghiệm |
| **Mức độ** | User Goal |
| **Tác nhân chính** | Người dùng đã đăng nhập |
| **Tác nhân phụ** | Multi-Agent System (Generator, Evaluator, Synthesizer) |
| **Mô tả** | Người dùng yêu cầu tạo N câu trắc nghiệm → hệ thống Multi-Agent sinh đề bám sát tài liệu |
| **Tiền điều kiện** | Thư viện có tài liệu ready |
| **Hậu điều kiện** | Bộ đề trắc nghiệm được lưu vào DB, hiển thị inline trong chat |

### Luồng chính

| Bước | Tác nhân | Hành động |
|------|---------|-----------|
| 1 | Người dùng | Chat: "Tạo 20 câu trắc nghiệm về chương 3" |
| 2 | Supervisor | Phân tích intent → gọi `generate_quiz(num_questions=20, focus_topic="chương 3")` |
| 3 | Frontend | SSE: `tool_status` "Đang lập kế hoạch biên soạn 20 câu hỏi..." |
| 4 | Init node | Tính số batch (ceil(20/20) = 1), sinh aspect_hints bằng Structured LLM |
| 5 | Frontend | SSE: `tool_status` "Đã lập kế hoạch 1 đợt. Bắt đầu đợt 1..." |
| 6 | Generator | HyDE search lấy context → LLM sinh 20 câu hỏi trắc nghiệm (Structured Output) |
| 7 | Frontend | SSE: `tool_status` "Đang sinh câu hỏi đợt 1/1..." |
| 8 | Evaluator | Đánh giá chất lượng 20 câu → approved/rejected |
| 9a | (approved) | Chuyển sang synthesizer |
| 9b | (rejected) | Generator regenerate với feedback (max 2 lần) |
| 10 | Synthesizer | Lọc câu đạt, gửi SSE `quiz_batch` event |
| 11 | Frontend | SSE: `quiz_batch` → hiển thị preview câu hỏi real-time |
| 12 | Hệ thống | Auto-save quiz vào DB (bảng `quizzes` + `quiz_questions`) |
| 13 | Frontend | SSE: `quiz_ready` (quiz_id) → fetch quiz detail |
| 14 | Frontend | Hiển thị QuizPreviewCard inline trong chat |
| 15 | Hệ thống | Lưu assistant message với `quiz_id` vào `chat_messages` |

### Luồng thay thế

| Bước | Điều kiện | Hành động |
|------|-----------|-----------|
| 6a | Mock mode | Generator trả câu hỏi mock mẫu |
| 8a | Evaluator rejected (lần 1) | Generator tạo lại + feedback |
| 8b | Evaluator rejected (lần 2) | Chấp nhận best effort → synthesizer |
| 6b | Rate limit 429 | Lưu câu hỏi đã có, thông báo friendly error + số câu đã sinh |
| 1a | Không nói rõ số câu | Mặc định 10 câu (theo system prompt) |

### Mapping kỹ thuật

| Component | File | Function |
|-----------|------|----------|
| Quiz tool | `backend/app/agents/assistant/tools/generate_quiz/tool.py` | `generate_quiz()` |
| Subgraph | `backend/app/agents/assistant/tools/generate_quiz/subgraph.py` | init → generator → evaluator → synthesizer |
| Generator | `backend/app/agents/assistant/tools/generate_quiz/nodes/generator_node.py` | `generator_node()` |
| Evaluator | `backend/app/agents/assistant/tools/generate_quiz/nodes/evaluator_node.py` | `evaluator_node()` |
| Synthesizer | `backend/app/agents/assistant/tools/generate_quiz/nodes/synthesizer_node.py` | `synthesizer_node()` |
| Auto-save | `backend/app/api/routes/chat.py` | `save_quiz_to_db()` |

---

## UC-07: Chỉnh sửa và lưu đề trắc nghiệm

| Thuộc tính | Chi tiết |
|-----------|----------|
| **Mã UC** | UC-07 |
| **Tên** | Chỉnh sửa đề trắc nghiệm inline |
| **Mức độ** | User Goal |
| **Tác nhân chính** | Người dùng đã đăng nhập |
| **Mô tả** | Người dùng chỉnh sửa nội dung câu hỏi, đáp án, giải thích ngay trong giao diện chat |
| **Tiền điều kiện** | Đã có quiz được sinh từ UC-06 |
| **Hậu điều kiện** | Quiz đã cập nhật trong DB (`is_edited_by_user = true`) |

### Luồng chính

| Bước | Tác nhân | Hành động |
|------|---------|-----------|
| 1 | Người dùng | Tại QuizPreviewCard, nhấn nút "Chỉnh sửa" |
| 2 | Frontend | Chuyển QuizPreviewCard → QuizEditorCard |
| 3 | Người dùng | Sửa nội dung câu hỏi, đáp án A/B/C/D, đáp án đúng, giải thích |
| 4 | Người dùng | Có thể xóa câu hỏi hoặc thay đổi thứ tự |
| 5 | Người dùng | Nhấn "Lưu thay đổi" |
| 6 | Frontend | `PUT /api/quizzes/{quiz_id}` (gửi toàn bộ questions mới) |
| 7 | Hệ thống | Xóa toàn bộ questions cũ, insert questions mới |
| 8 | Hệ thống | Set `is_edited_by_user = true` |
| 9 | Frontend | Chuyển về QuizPreviewCard với nội dung đã cập nhật |

### Mapping kỹ thuật

| Component | File |
|-----------|------|
| Backend route | `backend/app/api/routes/quizzes.py` → `PUT /api/quizzes/{quiz_id}` |
| Frontend editor | `frontend/src/components/quiz/QuizEditorCard.tsx` |
| Frontend preview | `frontend/src/components/quiz/QuizPreviewCard.tsx` |

---

## UC-08: Xuất đề trắc nghiệm PDF

| Thuộc tính | Chi tiết |
|-----------|----------|
| **Mã UC** | UC-08 |
| **Tên** | Xuất đề trắc nghiệm thành file PDF |
| **Mức độ** | User Goal |
| **Tác nhân chính** | Người dùng đã đăng nhập |
| **Mô tả** | Người dùng xuất bộ đề trắc nghiệm đã có thành file PDF để in ấn hoặc chia sẻ |
| **Tiền điều kiện** | Đã có quiz (UC-06 hoặc UC-07) |
| **Hậu điều kiện** | File PDF được download về máy |

### Luồng chính

| Bước | Tác nhân | Hành động |
|------|---------|-----------|
| 1 | Người dùng | Tại QuizPreviewCard, nhấn nút "Xuất PDF" |
| 2 | Frontend | QuizPdfExport component tạo PDF bằng jsPDF |
| 3 | Frontend | Format: tiêu đề, câu hỏi (1→N), lựa chọn A/B/C/D |
| 4 | Frontend | Trang đáp án cuối cùng (correct_answer + explanation) |
| 5 | Frontend | Trigger browser download `quiz_<title>.pdf` |

### Mapping kỹ thuật

| Component | File |
|-----------|------|
| Frontend export | `frontend/src/components/quiz/QuizPdfExport.tsx` |
| PDF library | `jspdf` (client-side PDF generation) |

---

## Sơ đồ Use Case tổng quan

```
                         ┌──────────────────────────────────────┐
                         │           RAQ Chatbot System         │
                         │                                      │
     ┌──────────┐        │  ┌─────────────────────────────────┐ │
     │          │        │  │ UC-01: Đăng ký tài khoản        │ │
     │  Người   │───────▶│  │ UC-02: Đăng nhập hệ thống      │ │
     │  dùng    │        │  │ UC-03: Quản lý Thư viện         │ │
     │ (Student/│        │  │ UC-04: Upload & xử lý PDF       │ │
     │ Teacher) │        │  │ UC-05: Chat RAG hỏi đáp         │ │
     │          │        │  │ UC-06: Tạo đề trắc nghiệm       │ │
     └──────────┘        │  │ UC-07: Chỉnh sửa đề trắc nghiệm│ │
                         │  │ UC-08: Xuất PDF đề thi           │ │
                         │  └─────────────────────────────────┘ │
                         │                                      │
                         │         «uses»           «uses»      │
                         │                                      │
                         │  ┌─────────┐  ┌──────────────────┐   │
                         │  │ LLM API │  │ pgvector + MinIO │   │
                         │  │(NVIDIA/ │  │ (Data Layer)     │   │
                         │  │Gemini/  │  │                  │   │
                         │  │GPT/     │  │                  │   │
                         │  │Claude)  │  │                  │   │
                         │  └─────────┘  └──────────────────┘   │
                         └──────────────────────────────────────┘
```

### Ma trận Actor → Use Case

| Actor | UC-01 | UC-02 | UC-03 | UC-04 | UC-05 | UC-06 | UC-07 | UC-08 |
|-------|-------|-------|-------|-------|-------|-------|-------|-------|
| Người dùng (chưa đăng nhập) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Người dùng (đã đăng nhập) | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| LLM API | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ |
| MinIO | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| NVIDIA Embedding API | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ |

### Quan hệ giữa các Use Case

| Quan hệ | Mô tả |
|---------|--------|
| UC-03 `<<extends>>` UC-01 | Phải đăng ký trước mới tạo thư viện |
| UC-04 `<<extends>>` UC-03 | Phải có thư viện trước mới upload |
| UC-05 `<<extends>>` UC-04 | Phải có tài liệu ready mới chat RAG |
| UC-06 `<<extends>>` UC-05 | Sinh quiz là một loại chat action |
| UC-07 `<<extends>>` UC-06 | Chỉnh sửa quiz đã được sinh |
| UC-08 `<<extends>>` UC-06/07 | Xuất PDF từ quiz đã có |
