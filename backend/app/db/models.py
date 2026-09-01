"""
SQLAlchemy ORM models for the 9 database tables.
Uses pgvector for embedding storage.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Text, Integer, Boolean, Numeric,
    ForeignKey, CheckConstraint, Index, DateTime,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, relationship
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


# ── 1. User ──────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    libraries = relationship("Library", back_populates="user", cascade="all, delete-orphan")


# ── 2. Library ───────────────────────────────────────────────
class Library(Base):
    __tablename__ = "libraries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    icon_or_color = Column(String(50))
    total_documents = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="libraries")
    documents = relationship("Document", back_populates="library", cascade="all, delete-orphan")
    sessions = relationship("ChatSession", back_populates="library", cascade="all, delete-orphan")
    quizzes = relationship("Quiz", back_populates="library", cascade="all, delete-orphan")


# ── 3. Document ──────────────────────────────────────────────
class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    library_id = Column(UUID(as_uuid=True), ForeignKey("libraries.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    file_name = Column(String(500), nullable=False)
    file_path_minio = Column(Text, nullable=False)
    total_pages = Column(Integer)
    status = Column(String(30), default="pending")  # pending | processing | ready | failed
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    library = relationship("Library", back_populates="documents")
    ingestion_job = relationship("IngestionJob", back_populates="document", uselist=False, cascade="all, delete-orphan")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


# ── 4. IngestionJob ──────────────────────────────────────────
class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    total_chunks = Column(Integer, default=0)
    processed_chunks = Column(Integer, default=0)
    progress_percent = Column(Numeric(5, 2), default=0)
    error_message = Column(Text)
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))

    document = relationship("Document", back_populates="ingestion_job")


# ── 5. DocumentChunk ─────────────────────────────────────────
class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    library_id = Column(UUID(as_uuid=True), ForeignKey("libraries.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer)
    chunk_index = Column(Integer)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(768))  # pgvector 768-dim (text-embedding-004)
    metadata = Column(JSONB)

    document = relationship("Document", back_populates="chunks")


# ── 6. ChatSession ───────────────────────────────────────────
class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    library_id = Column(UUID(as_uuid=True), ForeignKey("libraries.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    library = relationship("Library", back_populates="sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


# ── 7. ChatMessage ───────────────────────────────────────────
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(10), nullable=False)  # 'user' | 'assistant'
    content = Column(Text, nullable=False)
    citations = Column(JSONB)
    quiz_id = Column(UUID(as_uuid=True), ForeignKey("quizzes.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session = relationship("ChatSession", back_populates="messages")

    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="ck_message_role"),
    )


# ── 8. Quiz ──────────────────────────────────────────────────
class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    library_id = Column(UUID(as_uuid=True), ForeignKey("libraries.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255))
    description = Column(Text)
    total_questions = Column(Integer)
    is_edited_by_user = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    library = relationship("Library", back_populates="quizzes")
    questions = relationship("QuizQuestion", back_populates="quiz", cascade="all, delete-orphan")


# ── 9. QuizQuestion ──────────────────────────────────────────
class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quiz_id = Column(UUID(as_uuid=True), ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    order_index = Column(Integer, nullable=False)
    question_text = Column(Text, nullable=False)
    option_a = Column(Text)
    option_b = Column(Text)
    option_c = Column(Text)
    option_d = Column(Text)
    correct_answer = Column(String(1))  # A, B, C, or D
    explanation = Column(Text)
    source_page = Column(Integer)

    quiz = relationship("Quiz", back_populates="questions")

    __table_args__ = (
        CheckConstraint("correct_answer IN ('A','B','C','D')", name="ck_correct_answer"),
    )
