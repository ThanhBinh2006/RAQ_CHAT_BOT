-- =============================================================
-- RAQ Chatbot — Database Schema (PostgreSQL + pgvector)
-- 9 bảng chuẩn hóa theo mô hình Thư viện Độc lập
-- =============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 2. libraries
CREATE TABLE libraries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    icon_or_color VARCHAR(50),
    total_documents INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_libraries_user ON libraries(user_id);

-- 3. documents
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    library_id UUID NOT NULL REFERENCES libraries(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_name VARCHAR(500) NOT NULL,
    file_path_minio TEXT NOT NULL,
    total_pages INT,
    status VARCHAR(30) DEFAULT 'pending',   -- pending | processing | ready | failed
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_documents_library ON documents(library_id);

-- 4. ingestion_jobs
CREATE TABLE ingestion_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    total_chunks INT DEFAULT 0,
    processed_chunks INT DEFAULT 0,
    progress_percent NUMERIC(5,2) DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ
);

-- 5. document_chunks
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    library_id UUID NOT NULL REFERENCES libraries(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    page_number INT,
    chunk_index INT,
    content TEXT NOT NULL,
    embedding VECTOR(768),
    metadata JSONB
);
CREATE INDEX idx_chunks_library_user ON document_chunks(library_id, user_id);
-- IVFFlat index for vector cosine similarity search
-- Note: requires at least ~100 rows to be effective; okay to create early
CREATE INDEX idx_chunks_embedding ON document_chunks
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 6. quizzes (created BEFORE chat_messages because chat_messages.quiz_id references it)
CREATE TABLE quizzes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    library_id UUID NOT NULL REFERENCES libraries(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    description TEXT,
    total_questions INT,
    is_edited_by_user BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 7. quiz_questions
CREATE TABLE quiz_questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    order_index INT NOT NULL,
    question_text TEXT NOT NULL,
    option_a TEXT,
    option_b TEXT,
    option_c TEXT,
    option_d TEXT,
    correct_answer CHAR(1) CHECK (correct_answer IN ('A','B','C','D')),
    explanation TEXT,
    source_page INT
);
CREATE INDEX idx_questions_quiz ON quiz_questions(quiz_id, order_index);

-- 8. chat_sessions
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    library_id UUID NOT NULL REFERENCES libraries(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 9. chat_messages
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(10) NOT NULL CHECK (role IN ('user','assistant')),
    content TEXT NOT NULL,
    citations JSONB,
    quiz_id UUID REFERENCES quizzes(id),
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_messages_session ON chat_messages(session_id, created_at);
