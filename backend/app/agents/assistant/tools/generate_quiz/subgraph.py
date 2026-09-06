"""
Quiz Subgraph — StateGraph with batching + reflection loop.
init → generator → evaluator → [reflection if rejected] → synthesizer → [next batch or END]
"""

from langgraph.graph import StateGraph, START, END
from .state import QuizState
from .nodes.generator_node import generator_node
from .nodes.evaluator_node import evaluator_node
from .nodes.synthesizer_node import synthesizer_node

from app.core.config import settings

MAX_RETRY_PER_BATCH = 2


async def init_batch_plan(state: QuizState) -> dict:
    """Calculate how many batches are needed and generate aspect_hints for each batch using structured LLM."""
    total = -(-state["num_questions"] // state["batch_size"])  # ceil division
    total = max(1, total)
    focus = state.get("focus_topic") or "toàn bộ nội dung tài liệu"
    num_questions = state.get("num_questions", 0)
    event_queue = state.get("event_queue")

    if event_queue:
        await event_queue.put({
            "type": "tool_status",
            "tool": "generate_quiz",
            "phase": "init",
            "batch": 0,
            "total_batches": total,
            "label": f"Đang lập kế hoạch biên soạn {num_questions} câu hỏi ({total} đợt)...",
        })

    if settings.USE_MOCK_LLM:
        aspect_hints = [f"Khía cạnh {i + 1}: Nội dung về {focus}" for i in range(total)]
        if event_queue:
            await event_queue.put({
                "type": "tool_status",
                "tool": "generate_quiz",
                "phase": "plan_ready",
                "batch": 0,
                "total_batches": total,
                "label": f"Đã lập kế hoạch {total} đợt câu hỏi. Bắt đầu đợt 1...",
            })
        return {"total_batches": total, "aspect_hints": aspect_hints}

    try:
        from app.llm.llm_factory import get_structured_llm
        from app.agents.assistant.tools.generate_quiz.schemas import QuizBatchPlan
        from langchain_core.messages import HumanMessage

        model_config = state.get("model_config") or {}
        api_keys = state.get("api_keys") or {}
        planner_model = model_config.get("supervisor") or model_config.get("generator")

        llm = get_structured_llm(
            planner_model,
            api_keys,
            schema=QuizBatchPlan,
            temperature=0.3,
        )

        prompt = f"""Bạn là chuyên gia lập kế hoạch biên soạn đề thi trắc nghiệm.
Chủ đề kiến thức: "{focus}"
Tổng số câu hỏi cần tạo: {num_questions}
Số đợt (batch) cần chia: {total} đợt

Nhiệm vụ: Hãy phân chia chủ đề trên thành đúng {total} góc nhìn/khía cạnh kiến thức trọng tâm riêng biệt (mỗi đợt một khía cạnh rõ ràng, mang tính bao quát và không trùng lặp, bám sát các khía cạnh từ cơ bản đến nâng cao).
"""
        response = await llm.ainvoke([HumanMessage(content=prompt)])

        if isinstance(response, QuizBatchPlan):
            aspect_hints = response.aspect_hints
        elif isinstance(response, dict):
            aspect_hints = response.get("aspect_hints", [])
        else:
            aspect_hints = []

        # Bù thêm nếu LLM trả về ít hơn total
        while len(aspect_hints) < total:
            aspect_hints.append(f"Phần {len(aspect_hints) + 1}: Chuyên sâu về {focus}")

        print(f"📋 Đã lập kế hoạch {len(aspect_hints)} khía cạnh cho {total} batch:")
        for b_idx, hint in enumerate(aspect_hints):
            print(f"   [Batch {b_idx}] {hint}")

    except Exception as e:
        print(f"Lỗi lập kế hoạch batch aspects: {e}")
        aspect_hints = [f"Phần {i + 1}: Kiến thức trọng tâm về {focus}" for i in range(total)]

    if event_queue:
        await event_queue.put({
            "type": "tool_status",
            "tool": "generate_quiz",
            "phase": "plan_ready",
            "batch": 0,
            "total_batches": total,
            "label": f"Đã lập kế hoạch {total} đợt câu hỏi. Bắt đầu đợt 1...",
        })

    return {
        "total_batches": total,
        "aspect_hints": aspect_hints,
    }


def should_continue_after_eval(state: QuizState) -> str:
    """
    After evaluation, decide whether to:
    - Proceed to synthesizer (approved or max retries hit)
    - Loop back to generator (rejected, needs improvement)
    """
    if state.get("eval_feedback") == "approved":
        return "synthesizer"
    if state.get("retry_count", 0) >= MAX_RETRY_PER_BATCH:
        return "synthesizer"  # Accept best effort, avoid infinite loop
    return "generator"  # Reflection: regenerate with feedback


def has_more_batches(state: QuizState) -> str:
    """
    After synthesizing a batch, check if we need more questions.
    """
    if len(state.get("accepted_questions", [])) < state["num_questions"]:
        return "generator"
    return END


# ── Build the subgraph ───────────────────────────────────────
graph = StateGraph(QuizState)
graph.add_node("init", init_batch_plan)
graph.add_node("generator", generator_node)
graph.add_node("evaluator", evaluator_node)
graph.add_node("synthesizer", synthesizer_node)

graph.add_edge(START, "init")
graph.add_edge("init", "generator")
graph.add_edge("generator", "evaluator")
graph.add_conditional_edges(
    "evaluator",
    should_continue_after_eval,
    {"generator": "generator", "synthesizer": "synthesizer"},
)
graph.add_conditional_edges(
    "synthesizer",
    has_more_batches,
    {"generator": "generator", END: END},
)

quiz_subgraph = graph.compile()
