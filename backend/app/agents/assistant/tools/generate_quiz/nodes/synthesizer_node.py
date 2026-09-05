"""
Synthesizer Node — Finalizes, standardizes, and rewrites flawed questions.
Uses get_structured_llm with SynthesizedBatch schema to recreate invalid/flawed
questions based on evaluator feedback, grounded in document context.
Accumulates approved and rewritten questions into accepted_questions.
"""

from typing import Optional, List, Dict
import logging
from langchain_core.messages import HumanMessage

from app.agents.assistant.tools.generate_quiz.state import QuizState
from app.agents.assistant.tools.generate_quiz.schemas import SynthesizedBatch
from app.llm.llm_factory import get_structured_llm
from app.core.config import settings

logger = logging.getLogger(__name__)


def _standardize_question(q: dict) -> Optional[dict]:
    """Validate and standardize a question dict into the canonical format."""
    if not isinstance(q, dict):
        return None

    question_text = str(q.get("question_text") or "").strip()
    opt_a = str(q.get("option_a") or "").strip()
    opt_b = str(q.get("option_b") or "").strip()
    opt_c = str(q.get("option_c") or "").strip()
    opt_d = str(q.get("option_d") or "").strip()

    if not question_text or not opt_a or not opt_b or not opt_c or not opt_d:
        return None

    ans = str(q.get("correct_answer") or "A").upper().strip()
    if ans not in ("A", "B", "C", "D"):
        for choice in ("A", "B", "C", "D"):
            if choice in ans:
                ans = choice
                break
        else:
            ans = "A"

    explanation = str(q.get("explanation") or "").strip() or None

    source_page = q.get("source_page")
    try:
        source_page = int(source_page) if source_page is not None else None
    except (ValueError, TypeError):
        source_page = None

    return {
        "question_text": question_text,
        "option_a": opt_a,
        "option_b": opt_b,
        "option_c": opt_c,
        "option_d": opt_d,
        "correct_answer": ans,
        "explanation": explanation,
        "source_page": source_page,
    }


async def synthesizer_node(state: QuizState) -> dict:
    """
    Synthesize the batch:
    1. Separate draft questions into valid vs. flawed based on evaluator feedback.
    2. Preserve valid questions as-is (standardizing format).
    3. Recreate / rewrite flawed questions using get_structured_llm with SynthesizedBatch.
    4. Assemble the finalized questions in order and accumulate into accepted_questions.
    5. Advance current_batch and reset transient batch state.
    """
    draft_questions = state.get("draft_questions") or []
    eval_details = state.get("eval_details") or []
    accepted = list(state.get("accepted_questions") or [])
    num_needed = state.get("num_questions", 0)
    context_chunks = state.get("context_chunks") or []
    model_config = state.get("model_config") or {}
    api_keys = state.get("api_keys") or {}

    if not draft_questions:
        return {
            "accepted_questions": accepted,
            "current_batch": state.get("current_batch", 0) + 1,
            "retry_count": 0,
            "context_chunks": [],
            "draft_questions": None,
            "eval_feedback": None,
            "eval_details": None,
        }

    # Map evaluator details by question index
    eval_map: Dict[int, dict] = {}
    for e in eval_details:
        idx = e.get("index")
        if idx is not None:
            eval_map[idx] = e

    flawed_items = []  # List of tuples: (original_index, draft_question, issue_description)
    valid_by_index: Dict[int, dict] = {}

    for i, q in enumerate(draft_questions):
        e = eval_map.get(i)
        is_valid = e.get("is_valid", True) if e else True
        if not is_valid:
            issue = e.get("issue") or "Không đạt tiêu chuẩn kiểm duyệt của evaluator"
            flawed_items.append((i, q, issue))
        else:
            std = _standardize_question(q)
            if std:
                valid_by_index[i] = std
            else:
                flawed_items.append((i, q, "Thiếu thông tin bắt buộc hoặc định dạng không đúng"))

    rewritten_by_index: Dict[int, dict] = {}
    extra_rewritten: List[dict] = []

    # If there are flawed questions, rewrite them using get_structured_llm
    if flawed_items:
        if settings.USE_MOCK_LLM:
            for orig_idx, q, issue in flawed_items:
                rewritten_by_index[orig_idx] = {
                    "question_text": f"[Đã sửa] {q.get('question_text', f'Câu hỏi {orig_idx + 1}')}",
                    "option_a": q.get("option_a") or "Đáp án A (đã sửa, đúng)",
                    "option_b": q.get("option_b") or "Đáp án B",
                    "option_c": q.get("option_c") or "Đáp án C",
                    "option_d": q.get("option_d") or "Đáp án D",
                    "correct_answer": "A",
                    "explanation": f"Đã viết lại để khắc phục lỗi: {issue}",
                    "source_page": q.get("source_page") or 1,
                }
        else:
            context_text = "\n\n".join(
                f"[Trang {c.get('page_number', '?')}] {c.get('content', '')}"
                for c in context_chunks[:8]
            )

            questions_to_fix_text = ""
            for num, (orig_idx, q, issue) in enumerate(flawed_items, 1):
                questions_to_fix_text += f"""
--- Câu cần sửa {num} (Index gốc: {orig_idx}) ---
Câu hỏi: {q.get('question_text', '')}
A. {q.get('option_a', '')}
B. {q.get('option_b', '')}
C. {q.get('option_c', '')}
D. {q.get('option_d', '')}
Đáp án hiện tại: {q.get('correct_answer', '')}
Giải thích: {q.get('explanation', '')}
Trang nguồn: {q.get('source_page', 'N/A')}
⚠️ Lỗi được chuyên gia kiểm duyệt chỉ ra: {issue}
"""

            prompt = f"""Bạn là chuyên gia biên tập và hoàn thiện đề thi trắc nghiệm (Quiz Synthesizer / Editor).
Dưới đây là {len(flawed_items)} câu hỏi trắc nghiệm chưa đạt tiêu chuẩn. Nhiệm vụ của bạn là VIẾT LẠI / TẠO LẠI hoàn chỉnh {len(flawed_items)} câu hỏi này để khắc phục triệt để các lỗi được chỉ ra.

📖 TÀI LIỆU GỐC (đối chiếu để tạo/sửa nội dung chính xác):
{context_text}

📝 DANH SÁCH CÂU HỎI CẦN SỬA ĐỔI:
{questions_to_fix_text}

📋 YÊU CẦU BẮT BUỘC:
1. Sửa đổi nội dung câu hỏi và các phương án để khắc phục triệt để lỗi (issue) đã nêu.
2. Thông tin và đáp án đúng phải bám sát tuyệt đối nội dung tài liệu gốc (KHÔNG bịa đặt / hallucinate).
3. Mỗi câu hỏi phải có đủ 4 phương án lựa chọn: option_a, option_b, option_c, option_d.
4. Chỉ có DUY NHẤT 1 đáp án đúng (correct_answer phải là một trong: "A", "B", "C", "D").
5. Độ dài và văn phong các phương án phải tương đương nhau, tránh để đáp án đúng quá dài hoặc quá lộ liễu.
6. Cung cấp giải thích ngắn gọn, rõ ràng cho đáp án đúng và kèm source_page chính xác."""

            try:
                synthesizer_model = model_config.get("synthesizer") or model_config.get("supervisor")
                llm = get_structured_llm(
                    synthesizer_model,
                    api_keys,
                    schema=SynthesizedBatch,
                    temperature=0.3,
                )
                response = await llm.ainvoke([HumanMessage(content=prompt)])

                if isinstance(response, SynthesizedBatch):
                    rewritten_raw = [q.model_dump() for q in response.questions]
                elif isinstance(response, dict):
                    rewritten_raw = response.get("questions") or response.get("rewritten_questions") or []
                else:
                    rewritten_raw = []

                for i, item in enumerate(rewritten_raw):
                    std = _standardize_question(item)
                    if not std:
                        continue
                    if i < len(flawed_items):
                        target_idx = flawed_items[i][0]
                        rewritten_by_index[target_idx] = std
                    else:
                        extra_rewritten.append(std)

            except Exception as e:
                logger.warning(f"Synthesizer LLM rewrite error: {e}")
                # Fallback: try best-effort standardization of original flawed questions
                for orig_idx, q, _ in flawed_items:
                    if orig_idx not in rewritten_by_index:
                        fallback_std = _standardize_question(q)
                        if fallback_std:
                            rewritten_by_index[orig_idx] = fallback_std

    # Assemble finalized questions in original batch order
    final_batch_questions = []
    for i in range(len(draft_questions)):
        if i in valid_by_index:
            final_batch_questions.append(valid_by_index[i])
        elif i in rewritten_by_index:
            final_batch_questions.append(rewritten_by_index[i])

    # Append any extra rewritten questions if available
    final_batch_questions.extend(extra_rewritten)

    # Accumulate into accepted_questions up to num_needed
    remaining = max(0, num_needed - len(accepted))
    to_add = final_batch_questions[:remaining]
    accepted.extend(to_add)

    return {
        "accepted_questions": accepted,
        "current_batch": state.get("current_batch", 0) + 1,
        "retry_count": 0,  # Reset for next batch
        "context_chunks": [],  # Clear context chunks so next batch loads fresh ones
        "draft_questions": None,
        "eval_feedback": None,
        "eval_details": None,
    }
