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
    Uses NVIDIA Nemotron-3-Embed-1B (2048 dims) or mock mode.
    """
    if settings.USE_MOCK_LLM:
        import hashlib
        hash_bytes = hashlib.sha256(query.encode()).digest()
        embedding = []
        for i in range(2048):
            byte_val = hash_bytes[i % len(hash_bytes)]
            embedding.append((byte_val / 127.5) - 1.0)
        return embedding

    import httpx

    # Ưu tiên lấy key NVIDIA Embedding từ: 
    # 1. api_key từ người dùng (nếu có)
    # 2. SYSTEM_NVIDIA_EMBEDDING_KEY trong .env
    # 3. SYSTEM_NVIDIA_API_KEY trong .env
    nv_key = api_key if (api_key and (api_key.startswith("nvapi-") or "nvapi" in api_key)) else (
        settings.SYSTEM_NVIDIA_EMBEDDING_KEY or settings.SYSTEM_NVIDIA_API_KEY
    )
    
    if nv_key:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(
                "https://integrate.api.nvidia.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {nv_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "input": [query],
                    "model": settings.DEFAULT_EMBEDDING_MODEL,
                    "input_type": "query",
                }
            )
            if res.status_code == 200:
                data = res.json()
                return data["data"][0]["embedding"]
            else:
                print(f"NVIDIA embedding error ({res.status_code}): {res.text}")

    # Fallback to Gemini if configured
    gemini_key = api_key if (api_key and not api_key.startswith("nvapi-")) else settings.SYSTEM_GEMINI_API_KEY
    if gemini_key:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=query,
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=2048
        )
        return result["embedding"]

    raise ValueError("SYSTEM_NVIDIA_EMBEDDING_KEY hoặc user NVIDIA Embedding API key là bắt buộc cho query embedding")


async def _generate_hypothetical_answers(query: str, api_key: Optional[str] = None) -> List[str]:
    """
    Kỹ thuật HyDE (Hypothetical Document Embeddings):
    Dùng DeepSeek V4 Pro sinh 4 câu/đoạn TRẢ LỜI giả định (2 Tiếng Việt, 2 Tiếng Anh)
    trước khi tìm kiếm vector.
    """
    if settings.USE_MOCK_LLM:
        return [
            f"Khái niệm: {query} là một kiến thức trọng tâm trong tài liệu.",
            f"Về nguyên lý hoạt động, {query} được tổ chức theo cấu trúc chuẩn.",
            f"Definition: {query} is a fundamental concept in computing.",
            f"In networking systems, {query} plays an essential role.",
        ]

    try:
        from app.llm.llm_factory import get_llm
        from langchain_core.messages import HumanMessage

        llm_key = api_key or settings.SYSTEM_NVIDIA_API_KEY
        llm = get_llm(settings.DEFAULT_CHAT_MODEL, {"nvidia": llm_key} if llm_key else {}, temperature=0.3)
        prompt = f"""Bạn là một chuyên gia RAG (Hypothetical Document Embeddings - HyDE).
Nhiệm vụ: Dựa vào câu hỏi dưới đây của người dùng, hãy viết ra đúng 4 câu/đoạn TRẢ LỜI giả định ngắn gọn (mỗi câu 1-2 dòng) có thể xuất hiện trong tài liệu hoặc giáo trình để giải đáp cho câu hỏi này:
- 2 câu/đoạn TRẢ LỜI bằng TIẾNG VIỆT (chứa định nghĩa, từ khóa học thuật tiếng Việt)
- 2 câu/đoạn TRẢ LỜI bằng TIẾNG ANH (chứa thuật ngữ chuyên ngành tiếng Anh tương ứng)

Câu hỏi gốc: "{query}"

Quy tắc xuất kết quả:
Chỉ trả về đúng 4 dòng, mỗi dòng là một câu/đoạn trả lời giả định. Không đánh số (1, 2..), không thêm gạch đầu dòng, không có lời dẫn.
"""
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content
        if isinstance(content, list):
            content = " ".join([p.get("text", "") for p in content if isinstance(p, dict)])

        lines = [line.strip().lstrip("0123456789.-* ") for line in str(content).strip().split("\n") if line.strip()]
        answers = [a for a in lines if a and len(a) > 5]
        return answers[:4]
    except Exception as e:
        print(f"HyDE answers generation warning: {e}")
        return []


async def similarity_search(
    query: str,
    library_id: Optional[str] = None,
    user_id: Optional[str] = None,
    top_k: int = 6,
    api_key: Optional[str] = None,
    llm_api_key: Optional[str] = None,
) -> List[dict]:
    """
    Perform HyDE (Hypothetical Document Embeddings) cosine similarity search:
    1. Generate 4 hypothetical answers (2 Vietnamese, 2 English) using LLM key.
    2. Embed the original query + all 4 hypothetical answers using Embedding key.
    3. Search pgvector for each embedding.
    4. Deduplicate retrieved chunks by ID, taking the maximum similarity score.
    5. Return top_k most relevant unique chunks.
    """
    if not library_id:
        return []

    # 1. Sinh 4 câu trả lời giả định (2 Tiếng Việt, 2 Tiếng Anh)
    hypothetical_answers = await _generate_hypothetical_answers(query, api_key=llm_api_key)
    search_texts = [query] + hypothetical_answers
    print(f"🔍 HyDE Search: Truy vấn gốc + {len(hypothetical_answers)} câu trả lời giả định:")
    for idx, ans in enumerate(search_texts):
        print(f"   [{idx}] {ans}")

    # 2. Tìm kiếm vector cho từng câu trả lời giả định
    chunk_map = {}  # chunk_id -> chunk dict

    for text_query in search_texts:
        try:
            query_embedding = await _get_query_embedding(text_query, api_key=api_key)
            embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

            conditions = ["library_id = CAST(:library_id AS uuid)"]
            params = {
                "embedding": embedding_str,
                "library_id": library_id,
                "top_k": top_k,
            }
            if user_id:
                conditions.append("user_id = CAST(:user_id AS uuid)")
                params["user_id"] = user_id

            where_clause = " AND ".join(conditions)

            sql = text(f"""
                SELECT
                    id,
                    document_id,
                    page_number,
                    chunk_index,
                    content,
                    1 - (embedding <=> CAST(:embedding AS vector)) AS score
                FROM document_chunks
                WHERE {where_clause}
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT :top_k
            """)

            async with AsyncSessionLocal() as db:
                result = await db.execute(sql, params)
                rows = result.fetchall()

            for row in rows:
                row_id = str(row.id)
                score = float(row.score) if row.score else 0.0
                if row_id not in chunk_map or score > chunk_map[row_id]["score"]:
                    chunk_map[row_id] = {
                        "id": row_id,
                        "document_id": str(row.document_id),
                        "page_number": row.page_number,
                        "chunk_index": row.chunk_index,
                        "content": row.content,
                        "score": score,
                    }
        except Exception as e:
            print(f"Error querying embedding for '{text_query}': {e}")

    # 3. Sắp xếp các chunk theo điểm tương đồng cao nhất và lấy top_k
    sorted_chunks = sorted(chunk_map.values(), key=lambda x: x["score"], reverse=True)
    return sorted_chunks[:top_k]
