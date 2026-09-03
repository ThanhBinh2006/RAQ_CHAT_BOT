"""
Vector similarity search over document_chunks using pgvector.
Supports both real embedding (Gemini) and mock mode.
"""

from typing import List, Optional
from sqlalchemy import text

from app.core.config import settings
from app.core.db import AsyncSessionLocal


async def _get_query_embedding(query: str, api_key: Optional[str] = None) -> List[float]:
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

    key = api_key or settings.SYSTEM_GEMINI_API_KEY
    if not key:
        # Fallback to deterministic pseudo-embedding if key is missing
        import hashlib
        hash_bytes = hashlib.sha256(query.encode()).digest()
        return [((hash_bytes[i % len(hash_bytes)] / 127.5) - 1.0) for i in range(768)]

    genai.configure(api_key=key)
    try:
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=query,
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=768
        )
        return result["embedding"]
    except Exception as e:
        print(f"Warning: text-embedding-004 failed: {e}. Trying fallback models/embedding-001...")
        try:
            result = genai.embed_content(
                model="models/embedding-001",
                content=query,
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=768
            )
            return result["embedding"]
        except Exception as e2:
            print(f"Embedding error: {e2}. Using fallback hash embedding.")
            import hashlib
            hash_bytes = hashlib.sha256(query.encode()).digest()
            return [((hash_bytes[i % len(hash_bytes)] / 127.5) - 1.0) for i in range(768)]


async def similarity_search(
    query: str,
    library_id: Optional[str] = None,
    user_id: Optional[str] = None,
    top_k: int = 6,
    api_key: Optional[str] = None,
) -> List[dict]:
    """
    Perform cosine similarity search on document_chunks
    filtered by library_id and user_id.

    Returns a list of dicts with keys:
      - content, page_number, document_id, chunk_index, score
    """
    if not library_id:
        return []

    try:
        query_embedding = await _get_query_embedding(query, api_key=api_key)

        # Format embedding as pgvector literal
        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        conditions = ["library_id = :library_id::uuid"]
        params = {
            "embedding": embedding_str,
            "library_id": library_id,
            "top_k": top_k,
        }
        if user_id:
            conditions.append("user_id = :user_id::uuid")
            params["user_id"] = user_id

        where_clause = " AND ".join(conditions)

        sql = text(f"""
            SELECT
                id,
                document_id,
                page_number,
                chunk_index,
                content,
                1 - (embedding <=> :embedding::vector) AS score
            FROM document_chunks
            WHERE {where_clause}
            ORDER BY embedding <=> :embedding::vector
            LIMIT :top_k
        """)

        async with AsyncSessionLocal() as db:
            result = await db.execute(sql, params)
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
    except Exception as e:
        print(f"Error during similarity_search: {e}")
        return []
