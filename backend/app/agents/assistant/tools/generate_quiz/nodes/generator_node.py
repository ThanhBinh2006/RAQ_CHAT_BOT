"""
Generator Node — Produces draft quiz questions from document context.
Uses a fast model (e.g., Groq Llama 3.3 70B) for speed.
"""

from typing import List, Dict
from app.agents.assistant.tools.generate_quiz.state import QuizState
from app.core.config import settings


async def generator_node(state: QuizState) -> dict:
    """
    Generate a batch of draft quiz questions based on document context.
    If there's rejection feedback from the evaluator, incorporate it.
    """
    from app.services.vector_store import similarity_search, map_model_to_key

    num_needed = min(
        state["batch_size"],
        state["num_questions"] - len(state["accepted_questions"]),
    )

    if num_needed <= 0:
        return {"draft_questions": []}

    focus = state.get("focus_topic") or "toàn bộ nội dung tài liệu"
    used_chunk_ids = list(state.get("used_chunk_ids") or [])

    # Lấy aspect_hint được lập kế hoạch từ init_batch_plan (hoặc fallback default)
    batch_idx = state.get("current_batch", 0)
    aspect_hints = state.get("aspect_hints") or []
    if batch_idx < len(aspect_hints) and aspect_hints[batch_idx]:
        aspect_hint = aspect_hints[batch_idx]
    else:
        aspect_hint = f"Kiến thức trọng tâm về {focus} (đợt {batch_idx + 1})"

    event_queue = state.get("event_queue")
    total_b = state.get("total_batches") or 1
    current_b = batch_idx + 1
    retry_c = state.get("retry_count", 0)
    if event_queue:
        retry_suffix = f" (thử lại lần {retry_c})" if retry_c > 0 else ""
        await event_queue.put({
            "type": "tool_status",
            "tool": "generate_quiz",
            "phase": "generating",
            "batch": current_b,
            "total_batches": total_b,
            "label": f"Đang biên soạn câu hỏi Đợt {current_b}/{total_b}{retry_suffix}...",
        })

    if state.get("retry_count", 0) > 0 and state.get("context_chunks"):
        chunks = state["context_chunks"]
    else:
        api_keys = state.get("api_keys", {})
        model_config = state.get("model_config", {})
        embedding_key = api_keys.get("default_embed")
        llm_key = map_model_to_key(model_config.get("supervisor", "default"), api_keys)

        try:
            chunks = await similarity_search(
                query=f"Kiến thức trọng tâm: {focus}",
                library_id=state.get("library_id"),
                user_id=state.get("user_id"),
                top_k=20, 
                exclude_chunk_ids=used_chunk_ids,
                embedding_model=model_config.get("embed"),
                api_key=embedding_key,
                llm_model=model_config.get("supervisor", "default"),
                llm_api_key=llm_key,
                num_hypothetical=2,  # Chỉ 2 câu giả định thay vì 4, tiết kiệm 50% token embedding
                aspect_hint=aspect_hint,  # Mỗi batch 1 góc nhìn khác biệt
            )
            for c in chunks:
                cid = c.get("id")
                if cid and cid not in used_chunk_ids:
                    used_chunk_ids.append(cid)
        except Exception as e:
            print(f"Error in generator_node similarity_search: {e}")
            if event_queue:
                await event_queue.put({
                    "type": "tool_status",
                    "tool": "generate_quiz",
                    "phase": "error",
                    "batch": current_b,
                    "total_batches": total_b,
                    "label": f"Lỗi tìm kiếm tài liệu đợt {current_b}: {str(e)[:70]}. Dừng và trả về câu hỏi hiện có.",
                })
            return {
                "draft_questions": [],
                "error": f"Lỗi tìm kiếm tài liệu đợt {current_b}: {str(e)}",
                "used_chunk_ids": used_chunk_ids,
            }

    context_text = "\n\n".join(
        f"[{c.get('file_name', 'Tài liệu')} - Trang {c['page_number']}] {c['content'].strip()}" for c in chunks
    )

    # Trích xuất ngắn gọn vài từ khóa của câu đã tạo (tối đa ~15 token) để tránh lặp ý
    accepted = state.get("accepted_questions") or []
    existing_topics_hint = ""
    if accepted:
        recent_snippets = [
            " ".join(str(q.get("question_text", "")).split()[:6])
            for q in accepted[-4:] if q.get("question_text")
        ]
        if recent_snippets:
            topics_str = ", ".join(f'"{s}..."' for s in recent_snippets)
            existing_topics_hint = f"\n🚫 Đã có câu hỏi về: {topics_str}. Hãy khai thác kiến thức/khía cạnh khác trong tài liệu."

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
🎯 Góc nhìn trọng tâm của đợt này: {aspect_hint}{existing_topics_hint}

📖 NỘI DUNG TÀI LIỆU:
{context_text}

{feedback_section}

📋 YÊU CẦU BẮT BUỘC:
1. Mỗi câu hỏi phải bám sát nội dung tài liệu (KHÔNG hallucinate thông tin ngoài).
2. ĐA DẠNG HÓA NỘI DUNG: Mỗi câu hỏi phải khai thác một nội dung/đoạn văn khác nhau trong tài liệu, TUYỆT ĐỐI KHÔNG hỏi nhiều câu về cùng một ý.
3. PHÂN BỔ ĐỀU ĐÁP ÁN ĐÚNG: Đáp án đúng (correct_answer) PHẢI được chia đều giữa A, B, C, D (TUYỆT ĐỐI KHÔNG để một chữ cái như B hoặc A lặp lại liên tiếp nhiều lần).
4. 4 lựa chọn (option_a, option_b, option_c, option_d) phải rõ ràng, có độ dài tương đương, chỉ có DUY NHẤT 1 đáp án đúng.
5. TUYỆT ĐỐI KHÔNG ĐƯỢC CHỨA TRÍCH DẪN NGUỒN trong câu hỏi (question_text) hoặc các lựa chọn (option_a, option_b, option_c, option_d):
   - KHÔNG viết tên file, số trang, tag ngoặc vuông hoặc cụm từ trích dẫn (ví dụ: '[Tên_file - Trang X]', 'Theo tài liệu...', '(Trang Y)') trong câu hỏi hoặc các lựa chọn. Câu hỏi và 4 lựa chọn phải hoàn toàn tự nhiên, chuẩn mực như đề thi thật.
   - Trích dẫn nguồn (tên file, số trang) CHỈ ĐƯỢC PHÉP nằm trong phần giải thích ('explanation') hoặc các trường metadata ('source_file', 'source_page').
6. Ghi rõ tên file tài liệu nguồn (source_file) và số trang (source_page) dựa trên thông tin `[tên_file - Trang X]` tương ứng.
7. Kèm giải thích chi tiết cho đáp án đúng (có thể trích dẫn nguồn tài liệu và số trang tại đây).

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
      "source_page": 1,
      "source_file": "ten_file.pdf"
    }}
  ]
}}"""

    # Mock mode
    if settings.USE_MOCK_LLM:
        mock_questions = []
        targets = ["A", "B", "C", "D"]
        for i in range(num_needed):
            ans = targets[i % 4]
            c_file = chunks[i % len(chunks)].get("file_name", "tai_lieu.pdf") if chunks else "tai_lieu.pdf"
            c_page = chunks[i % len(chunks)].get("page_number", 1) if chunks else 1
            mock_questions.append({
                "question_text": f"Câu hỏi {len(state['accepted_questions']) + i + 1} về {focus}: Khía cạnh nào sau đây là chính xác?",
                "option_a": f"Đáp án A {'(đúng)' if ans == 'A' else ''}",
                "option_b": f"Đáp án B {'(đúng)' if ans == 'B' else ''}",
                "option_c": f"Đáp án C {'(đúng)' if ans == 'C' else ''}",
                "option_d": f"Đáp án D {'(đúng)' if ans == 'D' else ''}",
                "explanation": f"[{c_file} - Trang {c_page}] Đây là nội dung kiến thức về {focus} ({aspect_hint}).",
                "source_page": c_page,
                "source_file": c_file,
            })
        return {
            "draft_questions": mock_questions,
            "context_chunks": chunks,
            "used_chunk_ids": used_chunk_ids,
            "retry_count": state.get("retry_count", 0),
        }

    # Real mode
    from app.llm.llm_factory import get_structured_llm
    from app.agents.assistant.tools.generate_quiz.schemas import DraftQuestionBatch
    from langchain_core.messages import HumanMessage
    import re

    def _clean_text_citations(text: str) -> str:
        if not text:
            return ""
        cleaned = re.sub(r"\[(?:\s*[^\]]*?(?:\.pdf|Trang|trang|Nguồn|nguồn|Page|page|Mock|mock)[^\]]*?)\]", "", text, flags=re.IGNORECASE)
        cleaned = re.sub(r"\((?:\s*[^)]*?(?:Trang|trang|Page|page)\s*\d+[^)]*?)\)", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^(?:Theo|Dựa vào)\s+tài liệu\s*[^,:]*[,:]\s*", "", cleaned, flags=re.IGNORECASE)
        return re.sub(r"\s+", " ", cleaned).strip()

    generator_model = (state.get("model_config") or {}).get("generator", None)
    llm = get_structured_llm(
        generator_model,
        state.get("api_keys") or {},
        schema=DraftQuestionBatch,
        temperature=0.7,
    )

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        if isinstance(response, DraftQuestionBatch):
            draft_questions = [q.model_dump() for q in response.questions]
        elif isinstance(response, dict):
            draft_questions = response.get("questions", [])
        else:
            draft_questions = []
    except Exception as e:
        print(f"Error in generator_node LLM invocation: {e}")
        if event_queue:
            await event_queue.put({
                "type": "tool_status",
                "tool": "generate_quiz",
                "phase": "error",
                "batch": current_b,
                "total_batches": total_b,
                "label": f"Gặp sự cố ở đợt {current_b}: {str(e)[:70]}. Đang dừng và tổng hợp câu hỏi đã có...",
            })
        return {
            "draft_questions": [],
            "error": f"Lỗi tạo câu hỏi đợt {current_b}: {str(e)}",
            "context_chunks": chunks,
            "used_chunk_ids": used_chunk_ids,
            "retry_count": state.get("retry_count", 0),
        }

    # Clean any citations from question_text and options
    for q in draft_questions:
        if isinstance(q, dict):
            q["question_text"] = _clean_text_citations(q.get("question_text", ""))
            q["option_a"] = _clean_text_citations(q.get("option_a", ""))
            q["option_b"] = _clean_text_citations(q.get("option_b", ""))
            q["option_c"] = _clean_text_citations(q.get("option_c", ""))
            q["option_d"] = _clean_text_citations(q.get("option_d", ""))

    return {
        "draft_questions": draft_questions,
        "context_chunks": chunks,
        "used_chunk_ids": used_chunk_ids,
        "retry_count": state.get("retry_count", 0),
    }
