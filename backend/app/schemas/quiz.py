"""Pydantic schemas for quiz endpoints (create, read, update)."""

from pydantic import BaseModel
from typing import Literal, Optional, List
from uuid import UUID


class QuizQuestionIn(BaseModel):
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: Literal["A", "B", "C", "D"]
    explanation: Optional[str] = None
    source_page: Optional[int] = None


class QuizCreateRequest(BaseModel):
    library_id: UUID
    title: str
    description: Optional[str] = None
    questions: List[QuizQuestionIn]
    is_edited_by_user: bool = True


class QuizQuestionOut(QuizQuestionIn):
    id: UUID
    order_index: int

    model_config = {"from_attributes": True}


class QuizOut(BaseModel):
    id: UUID
    title: Optional[str] = None
    description: Optional[str] = None
    total_questions: int
    is_edited_by_user: bool
    questions: List[QuizQuestionOut]

    model_config = {"from_attributes": True}
