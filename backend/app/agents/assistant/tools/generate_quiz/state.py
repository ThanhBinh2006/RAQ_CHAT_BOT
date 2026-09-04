"""
QuizState — Internal state for the quiz generation subgraph.
"""

from typing import TypedDict, Optional, List, Dict


class QuizState(TypedDict):
    """State for the quiz generation subgraph (batching + reflection)."""
    library_id: str
    user_id: str
    focus_topic: Optional[str]
    num_questions: int
    batch_size: int
    total_batches: int
    current_batch: int
    retry_count: int

    # Context from vector search
    context_chunks: List[dict]
    used_chunk_ids: List[str]

    # Draft questions from generator
    draft_questions: Optional[List[dict]]

    # Evaluation feedback
    eval_feedback: Optional[str]        # "approved" or rejection reason
    eval_details: Optional[List[dict]]  # Per-question feedback

    # Accumulated approved questions across all batches
    accepted_questions: List[dict]

    # Model configuration (passed from parent state)
    model_config: Dict[str, str]
    api_keys: Dict[str, str]
