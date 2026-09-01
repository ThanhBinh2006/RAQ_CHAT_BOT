"""
Synthesizer Node — Finalizes and standardizes approved questions.
Filters out invalid questions, normalizes format, and accumulates results.
"""

from app.agents.assistant.tools.generate_quiz.state import QuizState
from app.core.config import settings


async def synthesizer_node(state: QuizState) -> dict:
    """
    Synthesize the final batch:
    1. Filter out invalid questions based on evaluator feedback
    2. Standardize the format
    3. Accumulate into accepted_questions
    4. Advance batch counter
    """
    draft_questions = state.get("draft_questions", [])
    eval_details = state.get("eval_details", [])
    accepted = list(state.get("accepted_questions", []))
    num_needed = state["num_questions"]

    if not draft_questions:
        return {
            "accepted_questions": accepted,
            "current_batch": state.get("current_batch", 0) + 1,
            "retry_count": 0,
            "draft_questions": None,
            "eval_feedback": None,
            "eval_details": None,
        }

    # Build a set of invalid question indices
    invalid_indices = set()
    if eval_details:
        for e in eval_details:
            if not e.get("is_valid", True):
                invalid_indices.add(e.get("index", -1))

    # Filter and standardize questions
    valid_questions = []
    for i, q in enumerate(draft_questions):
        if i in invalid_indices:
            continue

        # Standardize the question format
        standardized = {
            "question_text": q.get("question_text", "").strip(),
            "option_a": q.get("option_a", "").strip(),
            "option_b": q.get("option_b", "").strip(),
            "option_c": q.get("option_c", "").strip(),
            "option_d": q.get("option_d", "").strip(),
            "correct_answer": q.get("correct_answer", "A").upper().strip(),
            "explanation": q.get("explanation", "").strip() if q.get("explanation") else None,
            "source_page": q.get("source_page"),
        }

        # Validate correct_answer is A/B/C/D
        if standardized["correct_answer"] not in ("A", "B", "C", "D"):
            standardized["correct_answer"] = "A"

        # Skip empty questions
        if not standardized["question_text"]:
            continue

        valid_questions.append(standardized)

    # Accumulate, but don't exceed num_questions
    remaining = num_needed - len(accepted)
    to_add = valid_questions[:remaining]
    accepted.extend(to_add)

    return {
        "accepted_questions": accepted,
        "current_batch": state.get("current_batch", 0) + 1,
        "retry_count": 0,  # Reset for next batch
        "draft_questions": None,
        "eval_feedback": None,
        "eval_details": None,
    }
