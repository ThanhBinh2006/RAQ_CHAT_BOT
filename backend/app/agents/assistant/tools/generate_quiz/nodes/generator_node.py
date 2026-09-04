"""
Generator Node — Produces draft quiz questions from document context.
Uses a fast model (e.g., Groq Llama 3.3 70B) for speed.
"""

from app.agents.assistant.tools.generate_quiz.state import QuizState
from app.core.config import settings


async def generator_node(state: QuizState) -> dict:
    """
    Generate a batch of draft quiz questions based on document context.
    If there's rejection feedback from the evaluator, incorporate it.
    """
    from app.services.vector_store import similarity_search
    from app.llm.llm_factory import get_llm

    num_needed = min(
        state["batch_size"],
        state["num_questions"] - len(state["accepted_questions"]),
    )

    if num_needed <= 0:
        return {"draft_questions": []}

    # Fetch context chunks:
    # If this is a retry within the same batch, reuse existing context_chunks.
    # Otherwise, fetch new chunks excluding previously used chunks (WHERE id NOT IN used_chunk_ids).
    focus = state.get("focus_topic") or "toàn bộ nội dung tài liệu"
    used_chunk_ids = list(state.get("used_chunk_ids") or [])

    if state.get("retry_count", 0) > 0 and state.get("context_chunks"):
        chunks = state["context_chunks"]
    else:
        api_keys = state.get("api_keys") or {}
        embedding_key = api_keys.get("nvidia_embedding") or api_keys.get("nvidia") or api_keys.get("gemini")
        llm_key = api_keys.get("nvidia") or api_keys.get("gemini")

        chunks = await similarity_search(
            query=f"Kiến thức trọng tâm: {focus}",
            library_id=state.get("library_id"),
            user_id=state.get("user_id"),
            top_k=10,
            exclude_chunk_ids=used_chunk_ids,
            api_key=embedding_key,
            llm_api_key=llm_key,
        )

        for c in chunks:
            cid = c.get("id")
            if cid and cid not in used_chunk_ids:
                used_chunk_ids.append(cid)

    context_text = "\n\n".join(
        f"[Trang {c['page_number']}] {c['content']}" for c in chunks
    )

    # Build the generation prompt
    feedback_section = ""
    if state.get("eval_feedback") and state["eval_feedback"] != "approved":
        feedback_section = f"""
⚠️ LƯU Ý: Batch trước đã bị đánh giá KHÔNG ĐẠT. Hãy cải thiện dựa trên phản hồi sau:
{state['eval_feedback']}

Các vấn đề cụ thể cần tránh:
{chr(10).join(f"- Câu {e.get('index', '?')}: {e.get('issue', 'N/A')}" for e in (state.get('eval_details') or []) if not e.get('is_valid', True))}
"""

    prompt = f"""Bạn là chuyên gia soạn đề trắc nghiệm. Hãy tạo chính xác {num_needed} câu hỏi trắc nghiệm 4 lựa chọn (A/B/C/D) dựa trên tài liệu sau.

📌 Chủ đề trọng tâm: {focus}

📖 NỘI DUNG TÀI LIỆU:
{context_text}

{feedback_section}

📋 YÊU CẦU:
1. Mỗi câu hỏi phải bám sát nội dung tài liệu (KHÔNG hallucinate thông tin ngoài).
2. 4 lựa chọn phải rõ ràng, không mập mờ, chỉ có DUY NHẤT 1 đáp án đúng.
3. Trộn đều các mức độ: Nhớ, Hiểu, Vận dụng.
4. Kèm giải thích ngắn gọn cho đáp án đúng.
5. Ghi rõ số trang nguồn (source_page) nếu biết.

Trả lời theo đúng format JSON sau (KHÔNG thêm bất kỳ text nào khác):
{{
  "questions": [
    {{
      "question_text": "...",
      "option_a": "...",
      "option_b": "...",
      "option_c": "...",
      "option_d": "...",
      "correct_answer": "A",
      "explanation": "...",
      "source_page": 1
    }}
  ]
}}"""

    # Mock mode
    if settings.USE_MOCK_LLM:
        mock_questions = []
        for i in range(num_needed):
            mock_questions.append({
                "question_text": f"[Mock] Câu hỏi {len(state['accepted_questions']) + i + 1} về {focus}?",
                "option_a": "Đáp án A (đúng)",
                "option_b": "Đáp án B",
                "option_c": "Đáp án C",
                "option_d": "Đáp án D",
                "correct_answer": "A",
                "explanation": f"Đây là câu hỏi mock về {focus}.",
                "source_page": 1,
            })
        return {
            "draft_questions": mock_questions,
            "context_chunks": chunks,
            "used_chunk_ids": used_chunk_ids,
            "retry_count": state.get("retry_count", 0),
        }

    # Real mode
    generator_model = (state.get("model_config") or {}).get("generator", settings.DEFAULT_CHAT_MODEL)
    llm = get_llm(
        generator_model,
        state.get("api_keys") or {},
        temperature=0.7,
    )

    from langchain_core.messages import HumanMessage
    response = await llm.ainvoke([HumanMessage(content=prompt)])

    # Parse JSON from response
    import json
    import re

    content = response.content
    # Extract JSON from possible markdown code blocks
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
    if json_match:
        content = json_match.group(1)

    try:
        parsed = json.loads(content)
        draft_questions = parsed.get("questions", [])
    except json.JSONDecodeError:
        # Fallback: try to find JSON object in the response
        try:
            start = content.index("{")
            end = content.rindex("}") + 1
            parsed = json.loads(content[start:end])
            draft_questions = parsed.get("questions", [])
        except (ValueError, json.JSONDecodeError):
            draft_questions = []

    return {
        "draft_questions": draft_questions,
        "context_chunks": chunks,
        "used_chunk_ids": used_chunk_ids,
        "retry_count": state.get("retry_count", 0),
    }
