"""
PDF ingestion service: extract text, chunk, embed, and store in document_chunks.
Supports both real (Gemini text-embedding-004) and mock embedding modes.
"""

import uuid
import math
from datetime import datetime, timezone
from typing import List

import fitz  # PyMuPDF
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.db.models import Document, IngestionJob, DocumentChunk

# ── Text Splitter Configuration ──────────────────────────────
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150,
    separators=["\n\n", "\n", ". ", " ", ""],
)


def _extract_pages_from_pdf(file_content: bytes) -> List[dict]:
    """
    Extract text from each page of a PDF file using PyMuPDF.
    Returns a list of dicts with 'page_number' (1-indexed) and 'text'.
    """
    doc = fitz.open(stream=file_content, filetype="pdf")
    pages = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text").strip()
        if text:
            pages.append({
                "page_number": page_num + 1,
                "text": text,
            })
    doc.close()
    return pages


def _chunk_pages(pages: List[dict]) -> List[dict]:
    """
    Split page texts into overlapping chunks.
    Each chunk retains its source page_number.
    """
    all_chunks = []
    chunk_idx = 0
    for page in pages:
        chunks = splitter.split_text(page["text"])
        for chunk_text in chunks:
            all_chunks.append({
                "page_number": page["page_number"],
                "chunk_index": chunk_idx,
                "content": chunk_text,
            })
            chunk_idx += 1
    return all_chunks


async def _get_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of texts.
    Uses Gemini text-embedding-004 (768 dims) or mock mode.
    """
    if settings.USE_MOCK_LLM:
        # Mock mode: return random-ish vectors of 768 dims (deterministic per text)
        import hashlib
        embeddings = []
        for text in texts:
            # Create a deterministic pseudo-embedding based on text hash
            hash_bytes = hashlib.sha256(text.encode()).digest()
            # Expand hash to 768 floats between -1 and 1
            embedding = []
            for i in range(768):
                byte_val = hash_bytes[i % len(hash_bytes)]
                embedding.append((byte_val / 127.5) - 1.0)
            embeddings.append(embedding)
        return embeddings

    # Real mode: use Gemini text-embedding-004
    import google.generativeai as genai

    api_key = settings.SYSTEM_GEMINI_API_KEY
    if not api_key:
        raise ValueError("SYSTEM_GEMINI_API_KEY is required for embedding generation")

    genai.configure(api_key=api_key)

    # Process in batches of 100 (Gemini batch limit)
    all_embeddings = []
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=batch,
            task_type="RETRIEVAL_DOCUMENT",
        )
        all_embeddings.extend(result["embedding"])

    return all_embeddings


async def ingest_document(document_id: str, file_content: bytes):
    """
    Full ingestion pipeline:
    1. Extract text pages from PDF
    2. Split into chunks
    3. Generate embeddings
    4. Store in document_chunks
    5. Update progress along the way
    """
    async with AsyncSessionLocal() as db:
        try:
            # Get document and job records
            doc = await db.get(Document, document_id)
            if not doc:
                return

            from sqlalchemy import select
            result = await db.execute(
                select(IngestionJob).where(IngestionJob.document_id == document_id)
            )
            job = result.scalar_one_or_none()
            if not job:
                return

            # Update status
            doc.status = "processing"
            job.started_at = datetime.now(timezone.utc)
            await db.commit()

            # Step 1: Extract pages
            pages = _extract_pages_from_pdf(file_content)
            doc.total_pages = len(pages)

            # Step 2: Chunk
            chunks = _chunk_pages(pages)
            total_chunks = len(chunks)
            job.total_chunks = total_chunks
            await db.commit()

            if total_chunks == 0:
                doc.status = "ready"
                job.progress_percent = 100
                job.finished_at = datetime.now(timezone.utc)
                await db.commit()
                return

            # Step 3 & 4: Embed and store in batches
            embed_batch_size = 50
            for i in range(0, total_chunks, embed_batch_size):
                batch = chunks[i:i + embed_batch_size]
                texts = [c["content"] for c in batch]

                # Generate embeddings for this batch
                embeddings = await _get_embeddings(texts)

                # Store chunks with embeddings
                for j, (chunk, embedding) in enumerate(zip(batch, embeddings)):
                    db.add(DocumentChunk(
                        id=uuid.uuid4(),
                        library_id=doc.library_id,
                        document_id=doc.id,
                        user_id=doc.user_id,
                        page_number=chunk["page_number"],
                        chunk_index=chunk["chunk_index"],
                        content=chunk["content"],
                        embedding=embedding,
                        meta_data={
                            "file_name": doc.file_name,
                            "page_number": chunk["page_number"],
                        },
                    ))

                # Update progress
                processed = min(i + embed_batch_size, total_chunks)
                job.processed_chunks = processed
                job.progress_percent = round((processed / total_chunks) * 100, 2)
                await db.commit()

            # Finalize
            doc.status = "ready"
            job.progress_percent = 100
            job.finished_at = datetime.now(timezone.utc)
            await db.commit()

        except Exception as e:
            # Mark as failed
            doc = await db.get(Document, document_id)
            if doc:
                doc.status = "failed"

            from sqlalchemy import select
            result = await db.execute(
                select(IngestionJob).where(IngestionJob.document_id == document_id)
            )
            job = result.scalar_one_or_none()
            if job:
                job.error_message = str(e)
                job.finished_at = datetime.now(timezone.utc)

            await db.commit()
            raise
