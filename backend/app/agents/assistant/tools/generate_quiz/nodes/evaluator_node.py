"""
Evaluator Node — Reviews draft questions for quality and accuracy.
Uses a high-quality model (e.g., Gemini 2.5 Flash) for precision.
"""

from app.agents.assistant.tools.generate_quiz.state import QuizState
from app.core.config import settings


async def evaluator_node(state: QuizState) -> dict:
    """
    Evaluate a batch of draft questions for:
    - Factual accuracy against source documents
    - Answer correctness (only one correct option)
    - No ambiguity in options
    - No hallucinated content
    """
    draft_questions = state.get("draft_questions", [])
    event_queue = state.get("event_queue")
    batch_idx = state.get("current_batch", 0)
    current_b = batch_idx + 1
    total_b = state.get("total_batches") or 1

    if event_queue:
        await event_queue.put({
            "type": "tool_status",
            "tool": "generate_quiz",
            "phase": "evaluating",
            "batch": current_b,
            "total_batches": total_b,
            "label": f"Đang kiểm duyệt chất lượng câu hỏi Đợt {current_b}/{total_b}...",
        })

    if not draft_questions:
        return {
            "eval_feedback": "approved",
            "eval_details": [],
        }

    # Format questions for evaluation
    questions_text = ""
    for i, q in enumerate(draft_questions):
        questions_text += f"""
--- Câu {i + 1} ---
Câu hỏi: {q.get('question_text', '')}
A. {q.get('option_a', '')}
B. {q.get('option_b', '')}
C. {q.get('option_c', '')}
D. {q.get('option_d', '')}
Đáp án đúng: {q.get('correct_answer', '')}
Giải thích: {q.get('explanation', '')}
"""

    # Context for verification
    context_chunks = state.get("context_chunks", [])
    context_text = "\n\n".join(
        f"[{c.get('file_name', 'Tài liệu')} - Trang {c.get('page_number', '?')}] {c.get('content', '')}"
        for c in context_chunks[:6]
    )

    prompt = f"""Bạn là chuyên gia kiểm duyệt đề thi. Hãy đánh giá từng câu hỏi trắc nghiệm dưới đây:

📖 TÀI LIỆU GỐC (để đối chiếu):
{context_text}

📝 CÁC CÂU HỎI CẦN ĐÁNH GIÁ:
{questions_text}

📋 TIÊU CHÍ ĐÁNH GIÁ:
1. Câu hỏi có bám sát tài liệu không? (Không hallucinate)
2. Đáp án đúng có thực sự đúng không?
3. Các lựa chọn sai có hợp lý và không gây nhầm lẫn không?
4. Câu hỏi có rõ ràng, không mập mờ không?
5. Trên lệch độ dài các câu trả lời không được quá khác nhau, dẫn đến việc quá dễ để chọn
6. Trong từng câu hỏi Không quá dễ nhận ra đáp án đúng
7. Câu hỏi và các phương án A, B, C, D TUYỆT ĐỐI KHÔNG ĐƯỢC CHỨA trích dẫn nguồn (như tên file, số trang, tag [Trang X]). Thông tin nguồn chỉ được phép nằm ở phần giải thích.

Trả lời theo JSON format:
{{
  "overall_verdict": "approved" hoặc "rejected",
  "valid_count": <số câu hợp lệ>,
  "total_count": <tổng số câu>,
  "evaluations": [
    {{"index": 0, "is_valid": true/false, "issue": "mô tả vấn đề nếu không hợp lệ"}}
  ],
  "summary_feedback": "Tóm tắt phản hồi để cải thiện"
}}

Quy tắc: Nếu >= 80% câu hợp lệ → "approved", ngược lại → "rejected"."""

    # Mock mode
    if settings.USE_MOCK_LLM:
        return {
            "eval_feedback": "approved",
            "eval_details": [
                {"index": i, "is_valid": True, "issue": None}
                for i in range(len(draft_questions))
            ],
        }

    # Real mode
    from app.llm.llm_factory import get_structured_llm
    from app.agents.assistant.tools.generate_quiz.schemas import EvaluationResult
    from langchain_core.messages import HumanMessage

    evaluator_model = (state.get("model_config") or {}).get("evaluator", None)
    llm = get_structured_llm(
        evaluator_model,
        state.get("api_keys") or {},
        schema=EvaluationResult,
        temperature=0.0,
    )

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        if isinstance(response, EvaluationResult):
            verdict = response.overall_verdict
            evaluations = [e.model_dump() for e in response.evaluations]
            summary = response.summary_feedback
        elif isinstance(response, dict):
            verdict = response.get("overall_verdict", "approved")
            evaluations = response.get("evaluations", [])
            summary = response.get("summary_feedback", "")
        else:
            verdict = "approved"
            evaluations = []
            summary = ""
    except Exception:
        # If any unexpected error, approve by default to avoid infinite loops
        return {
            "eval_feedback": "approved",
            "eval_details": [],
        }

    return {
        "eval_feedback": verdict if verdict == "approved" else summary,
        "eval_details": evaluations,
        "retry_count": state.get("retry_count", 0) + (0 if verdict == "approved" else 1),
    }
