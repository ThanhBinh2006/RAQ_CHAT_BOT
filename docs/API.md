# 📡 API.md — RESTful API Specification

> Comprehensive API specification for the RAQ Chatbot Backend.
> Base URL: `http://localhost:8000`

---

## 📑 Table of Contents

- [1. General Conventions](#1-general-conventions)
- [2. Authentication](#2-authentication)
- [3. Libraries](#3-libraries)
- [4. Chat Sessions](#4-chat-sessions)
- [5. Documents](#5-documents)
- [6. Chat (Streaming)](#6-chat-streaming)
- [7. Quizzes](#7-quizzes)
- [8. Health Check](#8-health-check)
- [9. HTTP Status Codes](#9-http-status-codes)

---

## 1. General Conventions

### 1.1 Authentication

All endpoints (except `/api/auth/register`, `/api/auth/login`, and `/api/health`) require a valid Bearer JWT token:

```
Authorization: Bearer <access_token>
```

### 1.2 Content-Type

| Request / Response Type | Content-Type |
|-------------------------|--------------|
| JSON request/response body | `application/json` |
| File upload | `multipart/form-data` |
| Streaming chat response | `text/plain` (SSE stream) |

### 1.3 UUID Format

All resource identifiers adhere to UUID v4 format. Example: `550e8400-e29b-41d4-a716-446655440000`

### 1.4 Timestamp Format

Timestamps are formatted according to ISO 8601 with UTC timezone offset: `2024-01-15T10:30:00+00:00`

---

## 2. Authentication

### 2.1 User Registration

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

**Error `409 Conflict`:** Email already registered.

---

### 2.2 User Login

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

**Error `401 Unauthorized`:** Incorrect email or password.

---

### 2.3 Get Current User Profile

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

### 3.1 List Libraries

```
GET /api/libraries
```

**Response `200 OK`:**
```json
[
  {
    "id": "lib-uuid-001",
    "name": "General Physics",
    "description": "First-year physics lecture notes",
    "icon_or_color": "#3B82F6",
    "total_documents": 5,
    "created_at": "2024-01-15T10:30:00+00:00"
  }
]
```

---

### 3.2 Create New Library

```
POST /api/libraries
```

**Request Body:**
```json
{
  "name": "General Physics",
  "description": "First-year physics lecture notes",
  "icon_or_color": "#3B82F6"
}
```

**Response `201 Created`:** Returns the created `LibraryOut` object.

---

### 3.3 Get Library Details

```
GET /api/libraries/{library_id}
```

**Response `200 OK`:** Returns `LibraryOut` object.

**Error `404 Not Found`:** Library not found or does not belong to the current user.

---

### 3.4 Delete Library

```
DELETE /api/libraries/{library_id}
```

**Response `204 No Content`**

> ⚠️ **Cascade delete**: Deleting a library cascades and permanently deletes all related documents, chunks, sessions, messages, and quizzes.

---

## 4. Chat Sessions

### 4.1 List Chat Sessions

```
GET /api/libraries/{library_id}/sessions
```

**Response `200 OK`:**
```json
[
  {
    "id": "sess-uuid-001",
    "library_id": "lib-uuid-001",
    "title": "Questions about Chapter 3",
    "created_at": "2024-01-15T10:30:00+00:00",
    "updated_at": "2024-01-15T11:00:00+00:00"
  }
]
```

---

### 4.2 Create Chat Session

```
POST /api/libraries/{library_id}/sessions
```

**Request Body:**
```json
{
  "title": "New Chat Session"
}
```

**Response `201 Created`:** Returns `SessionOut` object.

---

### 4.3 Delete Chat Session

```
DELETE /api/libraries/{library_id}/sessions/{session_id}
```

**Response `204 No Content`**

---

### 4.4 Get Message History

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
    "content": "Explain the operating principle of a bipolar junction transistor",
    "citations": null,
    "quiz_id": null,
    "quiz": null,
    "created_at": "2024-01-15T10:35:00+00:00"
  },
  {
    "id": "msg-uuid-002",
    "session_id": "sess-uuid-001",
    "role": "assistant",
    "content": "A bipolar junction transistor (BJT) operates based on semiconductor physics...",
    "citations": [
      {"page_number": 45, "document_id": "doc-uuid-001", "file_name": "Physics.pdf"}
    ],
    "quiz_id": null,
    "quiz": null,
    "created_at": "2024-01-15T10:35:05+00:00"
  }
]
```

> **Note**: When `quiz_id` is present (non-null), the `quiz` field is populated with the complete `QuizOut` object (including `questions[]`).

---

## 5. Documents

### 5.1 Upload PDF Document

```
POST /api/documents/upload
Content-Type: multipart/form-data
```

**Form Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `library_id` | string (UUID) | ✅ | Target library ID |
| `file` | File (PDF) | ✅ | PDF file to upload |

**Response `201 Created`:**
```json
{
  "id": "doc-uuid-001",
  "library_id": "lib-uuid-001",
  "file_name": "Physics_Textbook.pdf",
  "total_pages": null,
  "status": "processing",
  "created_at": "2024-01-15T10:30:00+00:00"
}
```

**Error `400 Bad Request`:** File is not a valid PDF.
**Error `404 Not Found`:** Library does not exist or is not owned by the current user.

> **Note**: Immediately following upload, the background ingestion pipeline begins. Use the progress endpoint below to monitor extraction and vectorization.

---

### 5.2 Monitor Ingestion Progress

```
GET /api/documents/{document_id}/progress
```

**Response `200 OK`:**
```json
{
  "document_id": "doc-uuid-001",
  "file_name": "Physics_Textbook.pdf",
  "status": "processing",
  "total_chunks": 150,
  "processed_chunks": 75,
  "progress_percent": 50.0,
  "error_message": null
}
```

**Status Values:**

| Status | Description |
|--------|-------------|
| `pending` | Queued, waiting to begin processing |
| `processing` | Extracting text and computing vector embeddings |
| `ready` | Completed successfully; available for similarity search |
| `failed` | Processing failed (see `error_message` for details) |

---

### 5.3 List Documents in Library

```
GET /api/documents/library/{library_id}
```

**Response `200 OK`:** Array of `DocumentOut[]`.

---

### 5.4 Delete Document

```
DELETE /api/documents/{document_id}
```

**Response `204 No Content`**

> Concurrently removes the stored PDF in MinIO, vector chunks in PostgreSQL, and any associated ingestion job records.

---

## 6. Chat (Streaming)

### 6.1 Send Chat Message

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
      "content": "Summarize the key takeaways of Chapter 5"
    }
  ],
  "libraryId": "lib-uuid-001",
  "sessionId": "sess-uuid-001"
}
```

**Custom Headers (Optional — BYOK):**

| Header | Description |
|--------|-------------|
| `X-Gemini-Key` | Google Gemini API key |
| `X-Openai-Key` | OpenAI API key |
| `X-Anthropic-Key` | Anthropic Claude API key |
| `X-Supervisor-Model` | Override model for the Supervisor agent |
| `X-Generator-Model` | Override model for the Generator node |
| `X-Evaluator-Model` | Override model for the Evaluator node |
| `X-Synthesizer-Model` | Override model for the Synthesizer node |

**Response `200 OK` (`text/plain` streaming):**

The stream delivers three types of interleaved content:

#### 1. SSE Events (Inline HTML Comments)
```
<!--EVENT:{"type":"tool_status","tool":"search_documents","phase":"searching","label":"Searching documents..."}-->
<!--EVENT:{"type":"tool_status","tool":"search_documents","phase":"completed","label":"Found 12 citations"}-->
<!--EVENT:{"type":"quiz_batch","batch_index":0,"questions":[...]}-->
<!--EVENT:{"type":"quiz_ready","quiz_id":"quiz-uuid-001"}-->
```

#### 2. Text Response (Word-by-Word Streaming)
```
A bipolar junction transistor (BJT) operates based on semiconductor physics...
```

#### 3. Metadata Footer
```
<!--METADATA_START-->{"quiz_id":"quiz-uuid-001","citations":[{"page_number":45,"document_id":"doc-001","file_name":"Physics.pdf"}]}<!--METADATA_END-->
```

**Event Types:**

| Event Type | Description | Payload |
|------------|-------------|---------|
| `tool_status` | Status updates during tool invocation | `tool`, `phase`, `label`, `citations?` |
| `quiz_batch` | Completed batch of quiz questions | `batch_index`, `questions[]` |
| `quiz_ready` | Quiz persisted to database | `quiz_id` |

---

## 7. Quizzes

### 7.1 Create Quiz (from Editor)

```
POST /api/quizzes
```

**Request Body:**
```json
{
  "library_id": "lib-uuid-001",
  "title": "Physics Chapter 3 Revision Quiz",
  "description": "20 multiple choice questions",
  "is_edited_by_user": true,
  "questions": [
    {
      "question_text": "How many semiconductor layers does a BJT possess?",
      "option_a": "1 layer",
      "option_b": "2 layers",
      "option_c": "3 layers",
      "option_d": "4 layers",
      "correct_answer": "C",
      "explanation": "A BJT consists of 3 alternating semiconductor layers: P-N-P or N-P-N (Page 45).",
      "source_page": 45
    }
  ]
}
```

**Response `201 Created`:** Returns `QuizOut` object (including `questions[]` with generated `id` and `order_index`).

---

### 7.2 Get Quiz Details

```
GET /api/quizzes/{quiz_id}
```

**Response `200 OK`:**
```json
{
  "id": "quiz-uuid-001",
  "title": "Revision Quiz 2024-01-15 10:30",
  "description": null,
  "total_questions": 20,
  "is_edited_by_user": false,
  "questions": [
    {
      "id": "q-uuid-001",
      "order_index": 0,
      "question_text": "How many semiconductor layers does a BJT possess?",
      "option_a": "1 layer",
      "option_b": "2 layers",
      "option_c": "3 layers",
      "option_d": "4 layers",
      "correct_answer": "C",
      "explanation": "A BJT consists of 3 alternating semiconductor layers: P-N-P or N-P-N.",
      "source_page": 45
    }
  ]
}
```

---

### 7.3 Update Quiz (Full Question Set Replacement)

```
PUT /api/quizzes/{quiz_id}
```

**Request Body:** Same schema as `POST /api/quizzes` (including `library_id`, `title`, `questions[]`).

**Response `200 OK`:** Returns updated `QuizOut` object.

> **Note**: A `PUT` request removes all existing questions for this quiz and replaces them with the new set. The `is_edited_by_user` flag is automatically updated to `true`.

---

### 7.4 List Quizzes by Library

```
GET /api/quizzes/library/{library_id}
```

**Response `200 OK`:** Array of `QuizOut[]`.

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

> Does not require authentication.

---

## 9. HTTP Status Codes

| Code | Status Text | Use Case |
|------|-------------|----------|
| `200` | OK | Successful retrieval or mutation (GET, PUT, POST) |
| `201` | Created | Resource successfully created (register, create library, upload) |
| `204` | No Content | Successful deletion with no body returned (DELETE) |
| `400` | Bad Request | Non-PDF upload, quiz without questions, invalid inputs |
| `401` | Unauthorized | Missing or expired token, incorrect credentials |
| `404` | Not Found | Resource does not exist or is not owned by the current user |
| `409` | Conflict | Email already registered |
| `422` | Unprocessable Entity | Pydantic validation error |
| `500` | Internal Server Error | Unexpected server runtime exception |

### Error Response Format

```json
{
  "detail": "Error description in English"
}
```

### Pydantic Validation Error Example (`422`):

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
