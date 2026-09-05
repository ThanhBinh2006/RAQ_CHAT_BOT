"""
Vector similarity search over document_chunks using pgvector.
Supports both real embedding (Gemini) and mock mode.
"""

import uuid
from typing import List, Optional, Dict
from sqlalchemy import text

from app.core.config import settings
from app.core.db import AsyncSessionLocal


async def _get_query_embedding(query: str,embedding_model:str=None, api_key: Optional[str] = None) -> List[float]:
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
    if api_key:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(
                "https://integrate.api.nvidia.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "input": [query],
                    "model": embedding_model,
                    "input_type": "query",
                }
            )
            if res.status_code == 200:
                data = res.json()
                return data["data"][0]["embedding"]
            else:
                print(f"NVIDIA embedding error ({res.status_code}): {res.text}")
                
    raise ValueError("SYSTEM_DEFAUT_EMBEDDING_KEY or DEFAULT_MODEL là bắt buộc cho query embedding")


async def _generate_hypothetical_answers(
    query: str,
    llm_model: str = None,
    api_key: Optional[str] = None,
    num_answers: int = 2,
    aspect_hint: Optional[str] = None,
) -> List[str]:
    """
    Kỹ thuật HyDE (Hypothetical Document Embeddings):
    Dùng LLM sinh num_answers câu/đoạn TRẢ LỜI giả định ngắn gọn
    trước khi tìm kiếm vector. Có thể định hướng theo aspect_hint.
    """
    if settings.USE_MOCK_LLM:
        return [
            f"Khái niệm: {query} là một kiến thức trọng tâm trong tài liệu. {aspect_hint or ''}",
            f"Về nguyên lý hoạt động, {query} được tổ chức theo cấu trúc chuẩn.",
        ][:num_answers]

    try:
        from app.llm.llm_factory import get_llm, _detect_provider
        from langchain_core.messages import HumanMessage

        provider = _detect_provider(llm_model) if llm_model else "default"
        api_keys_dict = {provider: api_key} if api_key else {}
        llm = get_llm(llm_model, api_keys_dict, temperature=0.3)

        aspect_text = f"\n🎯 Góc độ/Khía cạnh cần tập trung: {aspect_hint}" if aspect_hint else ""

        prompt = f"""Bạn là một chuyên gia RAG (Hypothetical Document Embeddings - HyDE).
Nhiệm vụ: Dựa vào chủ đề/câu hỏi dưới đây, hãy viết ra đúng {num_answers} đoạn TRẢ LỜI hoặc NỘI DUNG giả định ngắn gọn (mỗi đoạn 1-2 câu, chứa các từ khóa học thuật/chuyên môn trọng tâm) có thể xuất hiện trong tài liệu hoặc giáo trình để phục vụ tìm kiếm:{aspect_text}

Chủ đề/Câu hỏi: "{query}"

Quy tắc xuất kết quả:
- Chỉ trả về đúng {num_answers} dòng, mỗi dòng là một đoạn trả lời giả định.
- Mỗi đoạn khai thác một góc nhìn khác nhau, súc tích, không lặp từ.
- Không đánh số (1, 2..), không thêm gạch đầu dòng, không có lời dẫn.
"""
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content
        if isinstance(content, list):
            content = " ".join([p.get("text", "") for p in content if isinstance(p, dict)])

        lines = [line.strip().lstrip("0123456789.-* ") for line in str(content).strip().split("\n") if line.strip()]
        answers = [a for a in lines if a and len(a) > 5]
        return answers[:num_answers]
    except Exception as e:
        print(f"HyDE answers generation warning: {e}")
        return []
def map_model_to_key(model_name: str, api_keys: Optional[Dict[str, str]] = None) -> Optional[str]:
    from app.llm.llm_factory import _resolve_api_key, _detect_provider
    return _resolve_api_key(_detect_provider(model_name), api_keys)

async def similarity_search(
    query: str,
    library_id: Optional[str] = None,
    user_id: Optional[str] = None,
    top_k: int = 6,
    exclude_chunk_ids: Optional[List[str]] = None,
    embedding_model: str = None,
    api_key: Optional[str] = None,
    llm_model: str = None,
    llm_api_key: Optional[str] = None,
    num_hypothetical: int = 2,
    aspect_hint: Optional[str] = None,
) -> List[dict]:
    """
    Perform HyDE (Hypothetical Document Embeddings) cosine similarity search:
    1. Generate num_hypothetical answers oriented by aspect_hint using LLM key.
    2. Embed the original query + hypothetical answers using Embedding key.
    3. Search pgvector for each embedding (excluding exclude_chunk_ids if provided).
    4. Deduplicate retrieved chunks by ID, taking the maximum similarity score.
    5. Return top_k most relevant unique chunks.
    """
    if not library_id:
        return []

    # 1. Sinh các câu trả lời giả định theo aspect_hint (mặc định 2 câu để tiết kiệm token)
    hypothetical_answers = []
    if num_hypothetical > 0:
        hypothetical_answers = await _generate_hypothetical_answers(
            query,
            llm_model=llm_model,
            api_key=llm_api_key,
            num_answers=num_hypothetical,
            aspect_hint=aspect_hint,
        )
    search_texts = [query] + hypothetical_answers
    print(f"🔍 HyDE Search: Truy vấn gốc + {len(hypothetical_answers)} câu trả lời giả định (aspect: {aspect_hint or 'tổng quan'}):")
    for idx, ans in enumerate(search_texts):
        print(f"   [{idx}] {ans}")

    # Validate and clean exclude_chunk_ids
    valid_exclude_ids = []
    if exclude_chunk_ids:
        for eid in exclude_chunk_ids:
            try:
                valid_exclude_ids.append(str(uuid.UUID(str(eid))))
            except (ValueError, TypeError):
                pass

    # 2. Tìm kiếm vector cho từng câu trả lời giả định
    chunk_map = {}  # chunk_id -> chunk dict

    for text_query in search_texts:
        try:
            query_embedding = await _get_query_embedding(text_query, embedding_model=embedding_model, api_key=api_key)
            embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

            conditions = ["dc.library_id = CAST(:library_id AS uuid)"]
            params = {
                "embedding": embedding_str,
                "library_id": library_id,
                "top_k": top_k,
            }
            if user_id:
                conditions.append("dc.user_id = CAST(:user_id AS uuid)")
                params["user_id"] = user_id

            if valid_exclude_ids:
                cast_uuids = ", ".join(f"CAST('{uid}' AS uuid)" for uid in valid_exclude_ids)
                conditions.append(f"dc.id NOT IN ({cast_uuids})")

            where_clause = " AND ".join(conditions)

            sql = text(f"""
                SELECT
                    dc.id,
                    dc.document_id,
                    dc.page_number,
                    dc.chunk_index,
                    dc.content,
                    d.file_name,
                    1 - (dc.embedding <=> CAST(:embedding AS vector)) AS score
                FROM document_chunks dc
                LEFT JOIN documents d ON dc.document_id = d.id
                WHERE {where_clause}
                ORDER BY dc.embedding <=> CAST(:embedding AS vector)
                LIMIT :top_k
            """)

            async with AsyncSessionLocal() as db:
                result = await db.execute(sql, params)
                rows = result.fetchall()

            for row in rows:
                row_id = str(row.id)
                if valid_exclude_ids and row_id in valid_exclude_ids:
                    continue
                score = float(row.score) if row.score else 0.0
                if row_id not in chunk_map or score > chunk_map[row_id]["score"]:
                    chunk_map[row_id] = {
                        "id": row_id,
                        "document_id": str(row.document_id),
                        "file_name": getattr(row, "file_name", None) or "Tài liệu",
                        "page_number": row.page_number,
                        "chunk_index": row.chunk_index,
                        "content": row.content,
                        "score": score,
                    }
        except Exception as e:
            print(f"Error querying embedding for '{text_query}': {e}")

    # 3. Sắp xếp các chunk theo điểm tương đồng cao nhất và lấy top_k
    sorted_chunks = sorted(chunk_map.values(), key=lambda x: x["score"], reverse=True)

    # Fallback: nếu loại trừ hết sạch chunk (ví dụ tài liệu ngắn), tự động tìm lại không loại trừ để không bị rỗng
    if not sorted_chunks and valid_exclude_ids:
        print("⚠️ Hết chunk mới để loại trừ, tải lại các chunk sẵn có...")
        return await similarity_search(
            query=query,
            library_id=library_id,
            user_id=user_id,
            top_k=top_k,
            exclude_chunk_ids=None,
            embedding_model=embedding_model,
            api_key=api_key,
            llm_model=llm_model,
            llm_api_key=llm_api_key,
            num_hypothetical=num_hypothetical,
            aspect_hint=aspect_hint,
        )

    return sorted_chunks[:top_k]
