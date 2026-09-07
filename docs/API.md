# 📡 API.md — Đặc tả API RESTful

> Tài liệu đặc tả chi tiết tất cả endpoint API của RAQ Chatbot Backend.
> Base URL: `http://localhost:8000`

---

## 📑 Mục lục

- [1. Quy ước chung](#1-quy-ước-chung)
- [2. Authentication](#2-authentication)
- [3. Libraries](#3-libraries)
- [4. Chat Sessions](#4-chat-sessions)
- [5. Documents](#5-documents)
- [6. Chat (Streaming)](#6-chat-streaming)
- [7. Quizzes](#7-quizzes)
- [8. Health Check](#8-health-check)
- [9. Mã lỗi HTTP](#9-mã-lỗi-http)

---

## 1. Quy ước chung

### 1.1 Authentication

Tất cả endpoint (trừ `/api/auth/register`, `/api/auth/login`, `/api/health`) yêu cầu JWT token:

```
Authorization: Bearer <access_token>
```

### 1.2 Content-Type

| Loại request | Content-Type |
|-------------|-------------|
| JSON body | `application/json` |
| File upload | `multipart/form-data` |
| Chat response | `text/plain` (SSE stream) |

### 1.3 UUID Format

Tất cả ID sử dụng UUID v4. Ví dụ: `550e8400-e29b-41d4-a716-446655440000`

### 1.4 Timestamp Format

ISO 8601 với timezone: `2024-01-15T10:30:00+00:00`

---

## 2. Authentication

### 2.1 Đăng ký tài khoản

```
POST /api/auth/register
```

**Request Body:**
```json
{
  "email": "student@example.com",
  "password": "SecurePass123",
  "first_name": "Nguyen",
  "last_name": "Van A"
}
```

**Response `201 Created`:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "student@example.com",
  "first_name": "Nguyen",
  "last_name": "Van A"
}
```

**Lỗi `409 Conflict`:** Email đã được đăng ký.

---

### 2.2 Đăng nhập

```
POST /api/auth/login
```

**Request Body:**
```json
{
  "email": "student@example.com",
  "password": "SecurePass123"
}
```

**Response `200 OK`:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Lỗi `401 Unauthorized`:** Email hoặc mật khẩu không đúng.

---

### 2.3 Xem thông tin cá nhân

```
GET /api/auth/me
```

**Response `200 OK`:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "student@example.com",
  "first_name": "Nguyen",
  "last_name": "Van A"
}
```

---

## 3. Libraries

### 3.1 Danh sách thư viện

```
GET /api/libraries
```

**Response `200 OK`:**
```json
[
  {
    "id": "lib-uuid-001",
    "name": "Vật lý đại cương",
    "description": "Tài liệu vật lý năm nhất",
    "icon_or_color": "#3B82F6",
    "total_documents": 5,
    "created_at": "2024-01-15T10:30:00+00:00"
  }
]
```

---

### 3.2 Tạo thư viện mới

```
POST /api/libraries
```

**Request Body:**
```json
{
  "name": "Vật lý đại cương",
  "description": "Tài liệu vật lý năm nhất",
  "icon_or_color": "#3B82F6"
}
```

**Response `201 Created`:** Trả về `LibraryOut` object.

---

### 3.3 Xem chi tiết thư viện

```
GET /api/libraries/{library_id}
```

**Response `200 OK`:** Trả về `LibraryOut` object.

**Lỗi `404`:** Không tìm thấy thư viện hoặc không thuộc quyền sở hữu.

---

### 3.4 Xóa thư viện

```
DELETE /api/libraries/{library_id}
```

**Response `204 No Content`**

> ⚠️ **Cascade delete**: Xóa thư viện sẽ xóa toàn bộ documents, chunks, sessions, messages, quizzes liên quan.

---

## 4. Chat Sessions

### 4.1 Danh sách phiên chat

```
GET /api/libraries/{library_id}/sessions
```

**Response `200 OK`:**
```json
[
  {
    "id": "sess-uuid-001",
    "library_id": "lib-uuid-001",
    "title": "Hỏi về chương 3",
    "created_at": "2024-01-15T10:30:00+00:00",
    "updated_at": "2024-01-15T11:00:00+00:00"
  }
]
```

---

### 4.2 Tạo phiên chat mới

```
POST /api/libraries/{library_id}/sessions
```

**Request Body:**
```json
{
  "title": "Đoạn chat mới"
}
```

**Response `201 Created`:** Trả về `SessionOut` object.

---

### 4.3 Xóa phiên chat

```
DELETE /api/libraries/{library_id}/sessions/{session_id}
```

**Response `204 No Content`**

---

### 4.4 Lịch sử tin nhắn

```
GET /api/libraries/{library_id}/sessions/{session_id}/messages
```

**Response `200 OK`:**
```json
[
  {
    "id": "msg-uuid-001",
    "session_id": "sess-uuid-001",
    "role": "user",
    "content": "Giải thích nguyên lý hoạt động transistor",
    "citations": null,
    "quiz_id": null,
    "quiz": null,
    "created_at": "2024-01-15T10:35:00+00:00"
  },
  {
    "id": "msg-uuid-002",
    "session_id": "sess-uuid-001",
    "role": "assistant",
    "content": "Transistor hoạt động dựa trên nguyên lý bán dẫn...",
    "citations": [
      {"page_number": 45, "document_id": "doc-uuid-001", "file_name": "VatLy.pdf"}
    ],
    "quiz_id": null,
    "quiz": null,
    "created_at": "2024-01-15T10:35:05+00:00"
  }
]
```

> **Lưu ý**: Khi `quiz_id` không null, field `quiz` sẽ chứa đầy đủ `QuizOut` object (bao gồm `questions[]`).

---

## 5. Documents

### 5.1 Upload tài liệu PDF

```
POST /api/documents/upload
Content-Type: multipart/form-data
```

**Form Fields:**

| Field | Type | Bắt buộc | Mô tả |
|-------|------|----------|-------|
| `library_id` | string (UUID) | ✅ | ID thư viện đích |
| `file` | File (PDF) | ✅ | File PDF cần upload |

**Response `201 Created`:**
```json
{
  "id": "doc-uuid-001",
  "library_id": "lib-uuid-001",
  "file_name": "GiaoTrinh_VatLy.pdf",
  "total_pages": null,
  "status": "processing",
  "created_at": "2024-01-15T10:30:00+00:00"
}
```

**Lỗi `400`:** File không phải PDF.
**Lỗi `404`:** Thư viện không tồn tại hoặc không thuộc quyền sở hữu.

> **Lưu ý**: Sau khi upload, hệ thống tự động chạy ingestion pipeline nền. Dùng endpoint progress để theo dõi.

---

### 5.2 Theo dõi tiến trình xử lý

```
GET /api/documents/{document_id}/progress
```

**Response `200 OK`:**
```json
{
  "document_id": "doc-uuid-001",
  "file_name": "GiaoTrinh_VatLy.pdf",
  "status": "processing",
  "total_chunks": 150,
  "processed_chunks": 75,
  "progress_percent": 50.0,
  "error_message": null
}
```

**Status values:**

| Status | Mô tả |
|--------|--------|
| `pending` | Đang chờ xử lý |
| `processing` | Đang trích xuất text & tạo embeddings |
| `ready` | Hoàn thành, sẵn sàng tìm kiếm |
| `failed` | Xử lý thất bại (xem `error_message`) |

---

### 5.3 Danh sách tài liệu trong thư viện

```
GET /api/documents/library/{library_id}
```

**Response `200 OK`:** Mảng `DocumentOut[]`.

---

### 5.4 Xóa tài liệu

```
DELETE /api/documents/{document_id}
```

**Response `204 No Content`**

> Xóa đồng thời: file trên MinIO, chunks trong DB, ingestion job.

---

## 6. Chat (Streaming)

### 6.1 Gửi tin nhắn chat

```
POST /api/chat
Content-Type: application/json
```

**Request Body:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "Tóm tắt nội dung chương 5"
    }
  ],
  "libraryId": "lib-uuid-001",
  "sessionId": "sess-uuid-001"
}
```

**Custom Headers (tùy chọn — BYOK):**

| Header | Mô tả |
|--------|--------|
| `X-Gemini-Key` | API key Google Gemini |
| `X-Openai-Key` | API key OpenAI |
| `X-Anthropic-Key` | API key Anthropic |
| `X-Supervisor-Model` | Override model cho Supervisor agent |
| `X-Generator-Model` | Override model cho Generator node |
| `X-Evaluator-Model` | Override model cho Evaluator node |
| `X-Synthesizer-Model` | Override model cho Synthesizer node |

**Response `200 OK` (`text/plain` streaming):**

Stream bao gồm 3 loại nội dung xen kẽ:

#### 1. SSE Events (inline HTML comments)
```
<!--EVENT:{"type":"tool_status","tool":"search_documents","phase":"searching","label":"Đang tra cứu..."}-->
<!--EVENT:{"type":"tool_status","tool":"search_documents","phase":"completed","label":"Đã tìm 12 trích dẫn"}-->
<!--EVENT:{"type":"quiz_batch","batch_index":0,"questions":[...]}-->
<!--EVENT:{"type":"quiz_ready","quiz_id":"quiz-uuid-001"}-->
```

#### 2. Text Response (word-by-word streaming)
```
Transistor hoạt động dựa trên nguyên lý bán dẫn...
```

#### 3. Metadata Footer
```
<!--METADATA_START-->{"quiz_id":"quiz-uuid-001","citations":[{"page_number":45,"document_id":"doc-001","file_name":"VatLy.pdf"}]}<!--METADATA_END-->
```

**Event Types:**

| Event Type | Mô tả | Payload |
|------------|--------|---------|
| `tool_status` | Trạng thái thực thi tool | `tool`, `phase`, `label`, `citations?` |
| `quiz_batch` | Một batch câu hỏi hoàn thành | `batch_index`, `questions[]` |
| `quiz_ready` | Quiz đã được lưu vào DB | `quiz_id` |

---

## 7. Quizzes

### 7.1 Tạo quiz mới (từ editor)

```
POST /api/quizzes
```

**Request Body:**
```json
{
  "library_id": "lib-uuid-001",
  "title": "Đề ôn tập Vật lý chương 3",
  "description": "20 câu trắc nghiệm",
  "is_edited_by_user": true,
  "questions": [
    {
      "question_text": "Transistor BJT có bao nhiêu lớp bán dẫn?",
      "option_a": "1 lớp",
      "option_b": "2 lớp",
      "option_c": "3 lớp",
      "option_d": "4 lớp",
      "correct_answer": "C",
      "explanation": "Transistor BJT có 3 lớp bán dẫn: P-N-P hoặc N-P-N (Trang 45).",
      "source_page": 45
    }
  ]
}
```

**Response `201 Created`:** Trả về `QuizOut` object (bao gồm `questions[]` với `id`, `order_index`).

---

### 7.2 Xem chi tiết quiz

```
GET /api/quizzes/{quiz_id}
```

**Response `200 OK`:**
```json
{
  "id": "quiz-uuid-001",
  "title": "Đề ôn tập 15/01/2024 10:30",
  "description": null,
  "total_questions": 20,
  "is_edited_by_user": false,
  "questions": [
    {
      "id": "q-uuid-001",
      "order_index": 0,
      "question_text": "Transistor BJT có bao nhiêu lớp bán dẫn?",
      "option_a": "1 lớp",
      "option_b": "2 lớp",
      "option_c": "3 lớp",
      "option_d": "4 lớp",
      "correct_answer": "C",
      "explanation": "Transistor BJT có 3 lớp bán dẫn P-N-P hoặc N-P-N.",
      "source_page": 45
    }
  ]
}
```

---

### 7.3 Cập nhật quiz (thay thế toàn bộ câu hỏi)

```
PUT /api/quizzes/{quiz_id}
```

**Request Body:** Giống `POST /api/quizzes` (bao gồm `library_id`, `title`, `questions[]`).

**Response `200 OK`:** Trả về `QuizOut` object đã cập nhật.

> **Lưu ý**: PUT sẽ xóa toàn bộ câu hỏi cũ và thay thế bằng danh sách mới. `is_edited_by_user` tự động set `true`.

---

### 7.4 Danh sách quiz theo thư viện

```
GET /api/quizzes/library/{library_id}
```

**Response `200 OK`:** Mảng `QuizOut[]`.

---

## 8. Health Check

```
GET /api/health
```

**Response `200 OK`:**
```json
{
  "status": "ok",
  "mock_mode": true
}
```

> Không yêu cầu authentication.

---

## 9. Mã lỗi HTTP

| Mã | Ý nghĩa | Trường hợp sử dụng |
|----|---------|---------------------|
| `200` | OK | Thành công (GET, PUT, POST) |
| `201` | Created | Tạo mới thành công (register, create library, upload) |
| `204` | No Content | Xóa thành công (delete) |
| `400` | Bad Request | File không phải PDF, quiz không có câu hỏi |
| `401` | Unauthorized | Token hết hạn, sai email/password |
| `404` | Not Found | Resource không tồn tại hoặc không thuộc user hiện tại |
| `409` | Conflict | Email đã được đăng ký |
| `422` | Unprocessable Entity | Validation error (Pydantic) |
| `500` | Internal Server Error | Lỗi server không mong đợi |

### Error Response Format

```json
{
  "detail": "Mô tả lỗi bằng tiếng Việt"
}
```

### Ví dụ Pydantic Validation Error (`422`):

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```
