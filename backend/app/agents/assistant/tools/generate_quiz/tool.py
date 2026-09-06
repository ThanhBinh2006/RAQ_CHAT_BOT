"""
Tool 2: generate_quiz — Invokes the quiz subgraph to generate quiz questions.
"""

from typing import Annotated, Optional
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState


@tool
async def generate_quiz(
    num_questions: int,
    focus_topic: Optional[str],
    state: Annotated[dict, InjectedState],
) -> dict:
    """Sinh bộ đề trắc nghiệm N câu (tối đa 100) bám sát tài liệu trong Thư viện
    hiện tại. Dùng tool này khi người dùng yêu cầu 'tạo đề', 'tạo N câu trắc nghiệm',
    'sinh câu hỏi ôn tập', kèm chủ đề trọng tâm nếu có."""

    from .subgraph import quiz_subgraph

    n = min(num_questions, 100)

    try:
        result = await quiz_subgraph.ainvoke({
            "library_id": state.get("library_id"),
            "user_id": state.get("user_id"),
            "focus_topic": focus_topic,
            "num_questions": n,
            "batch_size": 20,
            "total_batches": 0,
            "current_batch": 0,
            "retry_count": 0,
            "aspect_hints": [],
            "context_chunks": [],
            "used_chunk_ids": [],
            "draft_questions": None,
            "eval_feedback": None,
            "eval_details": None,
            "accepted_questions": [],
            "model_config": state.get("model_config"),
            "api_keys": state.get("api_keys") or {},
            "event_queue": state.get("event_queue"),
            "error": None,
        })

        accepted = result.get("accepted_questions", [])
        err = result.get("error")
        if err:
            msg = f"Đã sinh được {len(accepted)} câu hỏi trắc nghiệm (quá trình dừng sớm do sự cố: {err})."
        else:
            msg = f"Đã sinh xong {len(accepted)} câu hỏi trắc nghiệm."

        return {
            "quiz_draft": accepted,
            "message": msg,
            "error": err,
        }
    except Exception as e:
        print(f"Unhandled error in generate_quiz tool: {e}")
        return {
            "quiz_draft": [],
            "message": f"Quá trình sinh câu hỏi trắc nghiệm gặp sự cố: {str(e)}",
            "error": str(e),
        }
