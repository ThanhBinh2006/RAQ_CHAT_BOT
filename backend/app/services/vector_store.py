"""
Vector similarity search over document_chunks using pgvector.
Supports both real embedding (Gemini) and mock mode.
"""

from typing import List, Optional
from sqlalchemy import text

from app.core.config import settings
from app.core.db import AsyncSessionLocal


async def _get_query_embedding(query: str) -> List[float]:
    """
    Generate embedding for a search query.
    Uses Gemini text-embedding-004 or mock mode.
    """
    if settings.USE_MOCK_LLM:
        import hashlib
        hash_bytes = hashlib.sha256(query.encode()).digest()
        embedding = []
        for i in range(768):
            byte_val = hash_bytes[i % len(hash_bytes)]
            embedding.append((byte_val / 127.5) - 1.0)
        return embedding

    import google.generativeai as genai

    api_key = settings.SYSTEM_GEMINI_API_KEY
    if not api_key:
        raise ValueError("SYSTEM_GEMINI_API_KEY is required for query embedding")

    genai.configure(api_key=api_key)
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=query,
        task_type="RETRIEVAL_QUERY",
    )
    return result["embedding"]


async def similarity_search(
    query: str,
    library_id: str,
    user_id: str,
    top_k: int = 6,
    api_key: Optional[str] = None,
) -> List[dict]:
    """
    Perform cosine similarity search on document_chunks
    filtered by library_id and user_id.

    Returns a list of dicts with keys:
      - content, page_number, document_id, chunk_index, score
    """
    # If user provides their own Gemini key, use it for query embedding
    if api_key and not settings.USE_MOCK_LLM:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=query,
            task_type="RETRIEVAL_QUERY",
        )
        query_embedding = result["embedding"]
    else:
        query_embedding = await _get_query_embedding(query)

    # Format embedding as pgvector literal
    embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

    sql = text("""
        SELECT
            id,
            document_id,
            page_number,
            chunk_index,
            content,
            1 - (embedding <=> :embedding::vector) AS score
        FROM document_chunks
        WHERE library_id = :library_id::uuid
          AND user_id = :user_id::uuid
        ORDER BY embedding <=> :embedding::vector
        LIMIT :top_k
    """)

    async with AsyncSessionLocal() as db:
        result = await db.execute(sql, {
            "embedding": embedding_str,
            "library_id": library_id,
            "user_id": user_id,
            "top_k": top_k,
        })
        rows = result.fetchall()

    return [
        {
            "id": str(row.id),
            "document_id": str(row.document_id),
            "page_number": row.page_number,
            "chunk_index": row.chunk_index,
            "content": row.content,
            "score": float(row.score) if row.score else 0,
        }
        for row in rows
    ]
