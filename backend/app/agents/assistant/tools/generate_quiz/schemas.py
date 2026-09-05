"""
Pydantic schemas for structured output from quiz generation nodes.
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional, List


class DraftQuestion(BaseModel):
    """A single draft quiz question from the Generator."""
    question_text: str = Field(description="Nội dung câu hỏi")
    option_a: str = Field(description="Đáp án A")
    option_b: str = Field(description="Đáp án B")
    option_c: str = Field(description="Đáp án C")
    option_d: str = Field(description="Đáp án D")
    correct_answer: Literal["A", "B", "C", "D"] = Field(description="Đáp án đúng")
    explanation: Optional[str] = Field(default=None, description="Giải thích đáp án")
    source_page: Optional[int] = Field(default=None, description="Số trang nguồn")
    source_file: Optional[str] = Field(default=None, description="Tên file tài liệu nguồn (ví dụ: giao_trinh.pdf)")


class DraftQuestionBatch(BaseModel):
    """A batch of draft questions from the Generator."""
    questions: List[DraftQuestion] = Field(description="Danh sách câu hỏi nháp")


class QuestionEvaluation(BaseModel):
    """Evaluation result for a single question."""
    index: int = Field(description="Vị trí câu hỏi trong batch (0-indexed)")
    is_valid: bool = Field(description="Câu hỏi hợp lệ hay không")
    issue: Optional[str] = Field(default=None, description="Vấn đề cần sửa nếu không hợp lệ")


class EvaluationResult(BaseModel):
    """Evaluation result for an entire batch."""
    overall_verdict: Literal["approved", "rejected"] = Field(
        description="'approved' nếu >= 80% câu hỏi hợp lệ, ngược lại 'rejected'"
    )
    valid_count: int = Field(description="Số câu hỏi hợp lệ")
    total_count: int = Field(description="Tổng số câu hỏi trong batch")
    evaluations: List[QuestionEvaluation] = Field(description="Chi tiết đánh giá từng câu")
    summary_feedback: str = Field(description="Tóm tắt phản hồi để Generator cải thiện")


class SynthesizedQuestion(BaseModel):
    """A finalized question after synthesis."""
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: Literal["A", "B", "C", "D"]
    explanation: Optional[str] = None
    source_page: Optional[int] = None
    source_file: Optional[str] = None


class SynthesizedBatch(BaseModel):
    """Finalized batch of questions from the Synthesizer."""
    questions: List[SynthesizedQuestion]


class QuizBatchPlan(BaseModel):
    """Batch plan containing aspect hints for each batch."""
    aspect_hints: List[str] = Field(
        description="Danh sách các khía cạnh kiến thức trọng tâm riêng biệt cho từng batch, đúng số lượng batch yêu cầu"
    )
