"""
Quiz Subgraph — StateGraph with batching + reflection loop.
init → generator → evaluator → [reflection if rejected] → synthesizer → [next batch or END]
"""

from langgraph.graph import StateGraph, START, END
from .state import QuizState
from .nodes.generator_node import generator_node
from .nodes.evaluator_node import evaluator_node
from .nodes.synthesizer_node import synthesizer_node

MAX_RETRY_PER_BATCH = 2


def init_batch_plan(state: QuizState) -> dict:
    """Calculate how many batches are needed."""
    total = -(-state["num_questions"] // state["batch_size"])  # ceil division
    return {"total_batches": total}


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
