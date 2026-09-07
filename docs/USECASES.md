# 📋 USECASES.md — Cockburn Use Case Specifications

> Detailed specification of core Use Cases for RAQ Chatbot, structured according to the **Cockburn (Fully-Dressed)** template.

---

## 📑 Table of Contents

- [UC-01: User Registration](#uc-01-user-registration)
- [UC-02: User Authentication](#uc-02-user-authentication)
- [UC-03: Document Library Management](#uc-03-document-library-management)
- [UC-04: PDF Upload & Ingestion Processing](#uc-04-pdf-upload--ingestion-processing)
- [UC-05: Document Question Answering (RAG Chat)](#uc-05-document-question-answering-rag-chat)
- [UC-06: Automated Quiz Generation](#uc-06-automated-quiz-generation)
- [UC-07: Inline Quiz Editing and Saving](#uc-07-inline-quiz-editing-and-saving)
- [UC-08: Export Quiz to PDF](#uc-08-export-quiz-to-pdf)
- [Overall Use Case Diagram](#overall-use-case-diagram)

---

## UC-01: User Registration

| Attribute | Details |
|-----------|---------|
| **UC ID** | UC-01 |
| **Name** | Register New Account |
| **Level** | User Goal |
| **Primary Actor** | User (Student / Instructor) |
| **Secondary Actor** | Backend System |
| **Description** | User creates a new account using email and password to access system features |
| **Preconditions** | User does not already possess an active account |
| **Postconditions** | User record created in database; user can proceed to login |

### Main Success Scenario

| Step | Actor | Action |
|------|-------|--------|
| 1 | User | Navigates to `/auth/register` |
| 2 | User | Enters email, password, first name, and last name |
| 3 | User | Clicks "Register" |
| 4 | System | Verifies that the email is not already registered |
| 5 | System | Hashes password using bcrypt |
| 6 | System | Inserts new User record into `users` table |
| 7 | System | Returns user details (`201 Created`) |
| 8 | Frontend | Redirects user to the login screen |

### Alternate Flows

| Step | Condition | Action |
|------|-----------|--------|
| 4a | Email already exists | System returns `409 Conflict` ("Email already registered") |
| 3a | Invalid email format | Frontend / backend returns `422 Unprocessable Entity` |
| 3b | Password does not meet criteria | Frontend displays validation warning message |

### Technical Mapping

| Component | File Path | Endpoint / Symbol |
|-----------|-----------|-------------------|
| Backend Route | `backend/app/api/routes/auth.py` | `POST /api/auth/register` |
| Schema | `backend/app/schemas/auth.py` | `RegisterRequest`, `UserOut` |
| Frontend Page | `frontend/src/app/auth/register/page.tsx` | Register form component |

---

## UC-02: User Authentication

| Attribute | Details |
|-----------|---------|
| **UC ID** | UC-02 |
| **Name** | System Login |
| **Level** | User Goal |
| **Primary Actor** | Registered User |
| **Description** | User logs in using email and password to obtain a JWT access token |
| **Preconditions** | User account exists (UC-01 completed) |
| **Postconditions** | JWT stored in localStorage; user redirected to Dashboard |

### Main Success Scenario

| Step | Actor | Action |
|------|-------|--------|
| 1 | User | Navigates to `/auth/login` |
| 2 | User | Enters registered email and password |
| 3 | User | Clicks "Log In" |
| 4 | System | Queries User by email from database |
| 5 | System | Verifies password hash using bcrypt |
| 6 | System | Generates signed JWT token (HS256, 24-hour expiration) |
| 7 | System | Returns `{access_token, token_type}` (`200 OK`) |
| 8 | Frontend | Stores access token in `localStorage` |
| 9 | Frontend | Redirects user to Dashboard (`/`) |

### Alternate Flows

| Step | Condition | Action |
|------|-----------|--------|
| 4a | Email not found | Returns `401 Unauthorized` ("Incorrect email or password") |
| 5a | Password incorrect | Returns identical `401 Unauthorized` error (avoids enumeration) |
| 8a | Token expired (after 24h) | Frontend automatically redirects to `/auth/login` |

### Technical Mapping

| Component | File Path | Endpoint / Symbol |
|-----------|-----------|-------------------|
| Backend Route | `backend/app/api/routes/auth.py` | `POST /api/auth/login` |
| Security Core | `backend/app/core/security.py` | `verify_password()`, `create_access_token()` |
| Frontend Page | `frontend/src/app/auth/login/page.tsx` | Login form component |
| Auth Context | `frontend/src/lib/auth-context.tsx` | `AuthProvider`, `useAuth()` |

---

## UC-03: Document Library Management

| Attribute | Details |
|-----------|---------|
| **UC ID** | UC-03 |
| **Name** | Create, View, and Delete Document Libraries |
| **Level** | User Goal |
| **Primary Actor** | Authenticated User |
| **Description** | User organizes documents into isolated subject libraries |
| **Preconditions** | User is authenticated (UC-02) |
| **Postconditions** | Library successfully created, listed, or deleted |

### Main Success Scenario — Create Library

| Step | Actor | Action |
|------|-------|--------|
| 1 | User | On Dashboard, clicks "New Library" |
| 2 | User | Enters library title, description (optional), and selects an accent color |
| 3 | User | Clicks "Create" |
| 4 | System | Inserts Library record with `user_id = current_user.id` |
| 5 | Frontend | Refreshes library grid to show newly created item |

### Main Success Scenario — Delete Library

| Step | Actor | Action |
|------|-------|--------|
| 1 | User | Clicks delete action on library card |
| 2 | Frontend | Prompts user with confirmation dialog |
| 3 | User | Confirms deletion |
| 4 | System | CASCADE DELETE: drops library, documents, chunks, sessions, messages, and quizzes |
| 5 | Frontend | Removes library from view |

### Technical Mapping

| Component | File Path | Endpoint / Symbol |
|-----------|-----------|-------------------|
| Backend Route | `backend/app/api/routes/libraries.py` | `GET/POST /api/libraries`, `DELETE /api/libraries/{id}` |
| Frontend Page | `frontend/src/app/page.tsx` | Dashboard (Library grid) |

---

## UC-04: PDF Upload & Ingestion Processing

| Attribute | Details |
|-----------|---------|
| **UC ID** | UC-04 |
| **Name** | Upload PDF Document to Library |
| **Level** | User Goal |
| **Primary Actor** | Authenticated User |
| **Secondary Actor** | MinIO (S3), NVIDIA Embedding API |
| **Description** | Upload PDF → save to MinIO → extract text → chunk → generate 2048-dim vector embeddings |
| **Preconditions** | At least one library exists (UC-03) |
| **Postconditions** | PDF stored in MinIO; chunks and embeddings ready for RAG similarity queries |

### Main Success Scenario

| Step | Actor | Action |
|------|-------|--------|
| 1 | User | Opens library view (`/libraries/{id}`) |
| 2 | User | Clicks "Upload Document" in the sidebar |
| 3 | User | Selects a PDF file from their computer |
| 4 | Frontend | Dispatches `POST /api/documents/upload` (`multipart/form-data`) |
| 5 | System | Validates file type (`.pdf`) and library ownership |
| 6 | System | Uploads file to MinIO bucket `pdf-storage` |
| 7 | System | Creates `Document` (status: `processing`) and `IngestionJob` records |
| 8 | System | Immediately responds with `201 Created` |
| 9 | System | **Background task** executes ingestion pipeline: |
| 9a | | PyMuPDF extracts text page by page |
| 9b | | RecursiveCharacterTextSplitter generates chunks (1000 chars, 150 overlap) |
| 9c | | NVIDIA Embedding API computes 2048-dim vector embeddings (batch size 32) |
| 9d | | Chunks and vectors are inserted into `document_chunks` table |
| 10 | Frontend | Polls `GET /api/documents/{id}/progress` every 2 seconds |
| 11 | Frontend | Updates progress bar (`processed_chunks / total_chunks`) |
| 12 | System | Upon completion: status becomes `ready`, progress hits 100% |

### Alternate Flows

| Step | Condition | Action |
|------|-----------|--------|
| 5a | File is not a PDF | System returns `400 Bad Request` ("Only PDF files accepted") |
| 9d-a | Embedding API error | Document status set to `failed`; error message recorded in job |
| 9d-b | Mock mode (`USE_MOCK_LLM=true`) | Generates deterministic pseudo-embeddings via SHA-256 hash |

### Technical Mapping

| Component | File Path | Endpoint / Symbol |
|-----------|-----------|-------------------|
| Backend Route | `backend/app/api/routes/documents.py` | `upload_document()`, `get_progress()` |
| Ingestion Service | `backend/app/services/ingestion_service.py` | `ingest_document()` |
| Storage Service | `backend/app/services/storage_service.py` | `upload_file()` |
| Frontend Component | `frontend/src/components/library/LibrarySidebar.tsx` | Upload UI + progress polling |

---

## UC-05: Document Question Answering (RAG Chat)

| Attribute | Details |
|-----------|---------|
| **UC ID** | UC-05 |
| **Name** | Document QA via AI Chatbot |
| **Level** | User Goal |
| **Primary Actor** | Authenticated User |
| **Secondary Actor** | LLM (DeepSeek / Gemini / GPT / Claude), pgvector |
| **Description** | User submits a question → AI performs RAG search with HyDE → streams response with citations |
| **Preconditions** | Library contains at least one document in `ready` state |
| **Postconditions** | Response rendered in real-time with document page and file citations |

### Main Success Scenario

| Step | Actor | Action |
|------|-------|--------|
| 1 | User | Opens library and selects or creates a chat session |
| 2 | User | Inputs a query (e.g., "Explain how a transistor works") |
| 3 | Frontend | Calls `POST /api/chat` with SSE streaming, message history, and IDs |
| 4 | System | Persists user message into `chat_messages` table |
| 5 | System | Automatically names session if currently untitled |
| 6 | Agent | Supervisor Agent evaluates intent and calls tool `search_documents` |
| 7 | Agent | **HyDE**: LLM synthesizes 2 hypothetical answers |
| 8 | Agent | Embeds original query + hypothetical answers into 3 vectors |
| 9 | Agent | Executes pgvector cosine similarity search to retrieve top-20 chunks |
| 10 | Frontend | Receives SSE event: `tool_status` (searching → completed, N citations) |
| 11 | Agent | Supervisor synthesizes comprehensive answer from context chunks |
| 12 | Frontend | Streams answer text word-by-word |
| 13 | Frontend | Receives metadata footer with citations (page number, file name) |
| 14 | System | Persists assistant message and citations to database |

### Alternate Flows

| Step | Condition | Action |
|------|-----------|--------|
| 6a | Casual greeting / out-of-scope query | Agent replies directly without invoking search tools |
| 9a | No relevant chunks found | Replies indicating that relevant source content was not found |
| 11a | LLM rate limit (429) | Emits friendly error and indicates retry waiting time |
| 11b | Invalid BYOK key (401/403) | Notifies user to verify their API key in Settings |

### Technical Mapping

| Component | File Path | Endpoint / Symbol |
|-----------|-----------|-------------------|
| Chat Endpoint | `backend/app/api/routes/chat.py` | `chat_endpoint()`, `generate_stream()` |
| Agent Graph | `backend/app/agents/assistant/graph.py` | `build_assistant_graph()` |
| RAG Tool | `backend/app/agents/assistant/tools/search_documents.py` | `search_documents()` |
| Vector Store | `backend/app/services/vector_store.py` | `similarity_search()` + HyDE |
| Frontend Component | `frontend/src/components/chat/ChatWindow.tsx` | Chat UI + SSE stream parsing |

---

## UC-06: Automated Quiz Generation

| Attribute | Details |
|-----------|---------|
| **UC ID** | UC-06 |
| **Name** | Automated Multi-Agent Quiz Generation |
| **Level** | User Goal |
| **Primary Actor** | Authenticated User |
| **Secondary Actor** | Multi-Agent System (Generator, Evaluator, Synthesizer) |
| **Description** | User requests N multiple-choice questions → Multi-Agent system generates grounded quiz |
| **Preconditions** | Library contains ready documents |
| **Postconditions** | Quiz saved to DB and rendered inline in the chat conversation |

### Main Success Scenario

| Step | Actor | Action |
|------|-------|--------|
| 1 | User | Chats: "Generate 20 multiple choice questions on Chapter 3" |
| 2 | Supervisor | Detects intent and calls `generate_quiz(num_questions=20, focus_topic="Chapter 3")` |
| 3 | Frontend | Receives SSE: `tool_status` ("Planning 20 quiz questions...") |
| 4 | Init Node | Calculates batch count (ceil(20/20) = 1) and generates aspect hints |
| 5 | Frontend | Receives SSE: `tool_status` ("Planned 1 batch. Starting batch 1...") |
| 6 | Generator | Executes HyDE search for context and generates 20 questions |
| 7 | Frontend | Receives SSE: `tool_status` ("Generating questions for batch 1/1...") |
| 8 | Evaluator | Evaluates question clarity and answer accuracy (approved / rejected) |
| 9a | (Approved) | Passes questions to synthesizer node |
| 9b | (Rejected) | Prompts generator to regenerate with critique feedback (max 2 retries) |
| 10 | Synthesizer | Gathers passing questions and dispatches SSE `quiz_batch` event |
| 11 | Frontend | Receives SSE: `quiz_batch` and renders real-time question cards |
| 12 | System | Automatically saves quiz to database (`quizzes` and `quiz_questions`) |
| 13 | Frontend | Receives SSE: `quiz_ready` (with `quiz_id`) and fetches details |
| 14 | Frontend | Renders `QuizPreviewCard` directly inline in the chat timeline |
| 15 | System | Saves assistant message referencing `quiz_id` into `chat_messages` |

### Alternate Flows

| Step | Condition | Action |
|------|-----------|--------|
| 6a | Mock mode active | Generator supplies pre-formatted mock questions |
| 8a | Evaluator rejects (retry 1) | Generator regenerates with targeted critique feedback |
| 8b | Evaluator rejects (retry 2) | Best-effort accepted questions passed to synthesizer |
| 6b | Rate limit 429 encountered | Saves accumulated questions; returns partial success warning |
| 1a | Question count omitted | Defaults to 10 questions according to system prompt |

### Technical Mapping

| Component | File Path | Endpoint / Symbol |
|-----------|-----------|-------------------|
| Quiz Tool | `backend/app/agents/assistant/tools/generate_quiz/tool.py` | `generate_quiz()` |
| Subgraph | `backend/app/agents/assistant/tools/generate_quiz/subgraph.py` | init → generator → evaluator → synthesizer |
| Generator Node | `backend/app/agents/assistant/tools/generate_quiz/nodes/generator_node.py` | `generator_node()` |
| Evaluator Node | `backend/app/agents/assistant/tools/generate_quiz/nodes/evaluator_node.py` | `evaluator_node()` |
| Synthesizer Node | `backend/app/agents/assistant/tools/generate_quiz/nodes/synthesizer_node.py` | `synthesizer_node()` |
| Auto-Save Logic | `backend/app/api/routes/chat.py` | `save_quiz_to_db()` |

---

## UC-07: Inline Quiz Editing and Saving

| Attribute | Details |
|-----------|---------|
| **UC ID** | UC-07 |
| **Name** | Inline Quiz Editing and Revision |
| **Level** | User Goal |
| **Primary Actor** | Authenticated User |
| **Description** | User modifies question text, choices, correct answers, or explanations inline |
| **Preconditions** | Quiz generated from UC-06 |
| **Postconditions** | Quiz updated in database with `is_edited_by_user = true` |

### Main Success Scenario

| Step | Actor | Action |
|------|-------|--------|
| 1 | User | On `QuizPreviewCard`, clicks "Edit Quiz" |
| 2 | Frontend | Transitions component to `QuizEditorCard` |
| 3 | User | Edits question text, options A/B/C/D, correct answer, or explanation |
| 4 | User | Optionally deletes questions or reorganizes question order |
| 5 | User | Clicks "Save Changes" |
| 6 | Frontend | Calls `PUT /api/quizzes/{quiz_id}` with full updated question payload |
| 7 | System | Deletes previous questions and inserts updated question records |
| 8 | System | Flags quiz with `is_edited_by_user = true` |
| 9 | Frontend | Transitions back to `QuizPreviewCard` with revised content |

### Technical Mapping

| Component | File Path |
|-----------|-----------|
| Backend Route | `backend/app/api/routes/quizzes.py` → `PUT /api/quizzes/{quiz_id}` |
| Frontend Editor | `frontend/src/components/quiz/QuizEditorCard.tsx` |
| Frontend Preview | `frontend/src/components/quiz/QuizPreviewCard.tsx` |

---

## UC-08: Export Quiz to PDF

| Attribute | Details |
|-----------|---------|
| **UC ID** | UC-08 |
| **Name** | Export Quiz as Printable PDF Document |
| **Level** | User Goal |
| **Primary Actor** | Authenticated User |
| **Description** | User exports quiz questions and answer keys to a structured PDF file |
| **Preconditions** | Quiz exists in the active session (UC-06 or UC-07) |
| **Postconditions** | Formatted PDF downloaded to the user's computer |

### Main Success Scenario

| Step | Actor | Action |
|------|-------|--------|
| 1 | User | On `QuizPreviewCard`, clicks "Export PDF" |
| 2 | Frontend | `QuizPdfExport` component initiates client-side rendering via jsPDF |
| 3 | Frontend | Formats header, title, and numbered questions with choices A/B/C/D |
| 4 | Frontend | Appends answer key and explanation section on the final page |
| 5 | Frontend | Triggers automatic browser download: `quiz_<title>.pdf` |

### Technical Mapping

| Component | File Path |
|-----------|-----------|
| Frontend Export Component | `frontend/src/components/quiz/QuizPdfExport.tsx` |
| PDF Engine | `jspdf` (Client-side rendering) |

---

## Overall Use Case Diagram

```
                         ┌──────────────────────────────────────┐
                         │           RAQ Chatbot System         │
                         │                                      │
     ┌──────────┐        │  ┌─────────────────────────────────┐ │
     │          │        │  │ UC-01: Register New Account     │ │
     │  User    │───────▶│  │ UC-02: User Authentication      │ │
     │ (Student │        │  │ UC-03: Manage Document Libraries│ │
     │  Teacher)│        │  │ UC-04: PDF Upload & Ingestion   │ │
     │          │        │  │ UC-05: RAG Document QA Chat     │ │
     │          │        │  │ UC-06: Generate Quizzes         │ │
     └──────────┘        │  │ UC-07: Edit & Save Quizzes      │ │
                         │  │ UC-08: Export Quiz to PDF       │ │
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

### Actor → Use Case Matrix

| Actor | UC-01 | UC-02 | UC-03 | UC-04 | UC-05 | UC-06 | UC-07 | UC-08 |
|-------|-------|-------|-------|-------|-------|-------|-------|-------|
| Unauthenticated User | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Authenticated User | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| LLM APIs | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ |
| MinIO S3 | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| NVIDIA Embedding API | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ |

### Use Case Relationships

| Relationship | Description |
|--------------|-------------|
| UC-03 `<<extends>>` UC-01 | Account registration must precede library creation |
| UC-04 `<<extends>>` UC-03 | An active library must exist before uploading documents |
| UC-05 `<<extends>>` UC-04 | Grounded chat requires at least one processed document |
| UC-06 `<<extends>>` UC-05 | Quiz generation operates as an specialized chat workflow |
| UC-07 `<<extends>>` UC-06 | Editing requires an existing generated quiz |
| UC-08 `<<extends>>` UC-06/07 | PDF export is performed on a generated or edited quiz |
