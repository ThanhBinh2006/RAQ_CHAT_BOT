"""
PDF ingestion service: extract text, chunk, embed, and store in document_chunks.
Supports both real (Gemini text-embedding-004) and mock embedding modes.
"""

import uuid
import math
from datetime import datetime, timezone
from typing import List, Optional

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


async def _get_embeddings(
    texts: List[str],
    embedding_model: Optional[str] = None,
    api_key: Optional[str] = None,
) -> List[List[float]]:
    """
    Generate embeddings for a list of texts.
    Uses the provided embedding_model and api_key, or mock mode.
    """
    if settings.USE_MOCK_LLM:
        # Mock mode: return random-ish vectors of 2048 dims (deterministic per text)
        import hashlib
        embeddings = []
        for text in texts:
            # Create a deterministic pseudo-embedding based on text hash
            hash_bytes = hashlib.sha256(text.encode()).digest()
            # Expand hash to 2048 floats between -1 and 1
            embedding = []
            for i in range(2048):
                byte_val = hash_bytes[i % len(hash_bytes)]
                embedding.append((byte_val / 127.5) - 1.0)
            embeddings.append(embedding)
        return embeddings

    # Real mode
    if not api_key:
        raise ValueError("API key is required for embedding generation")

    import httpx
    all_embeddings = []
    batch_size = 32
    async with httpx.AsyncClient(timeout=60.0) as client:
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            res = await client.post(
                "https://integrate.api.nvidia.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "input": batch,
                    "model": embedding_model,
                    "input_type": "passage",
                }
            )
            if res.status_code == 200:
                data = res.json()
                # data["data"] sorted by index
                sorted_items = sorted(data["data"], key=lambda x: x["index"])
                all_embeddings.extend([item["embedding"] for item in sorted_items])
            else:
                raise ValueError(f"Ingestion embedding error ({res.status_code}): {res.text}")
    return all_embeddings


async def ingest_document(
    document_id: str,
    file_content: bytes,
    embedding_model: Optional[str] = None,
    api_key: Optional[str] = None,
):
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
                embeddings = await _get_embeddings(texts, embedding_model=embedding_model, api_key=api_key)

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
