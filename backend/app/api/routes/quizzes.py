"""
Quiz CRUD routes: create, get, update.
"""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db, get_current_user
from app.db.models import Quiz, QuizQuestion, User
from app.schemas.quiz import QuizCreateRequest, QuizOut, QuizQuestionOut

router = APIRouter(prefix="/api/quizzes", tags=["quizzes"])


@router.post("", response_model=QuizOut, status_code=201)
async def create_quiz(
    payload: QuizCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save a new quiz (typically after user edits the draft from chat)."""
    if not payload.questions:
        raise HTTPException(400, "Quiz phải có ít nhất 1 câu hỏi")

    quiz = Quiz(
        id=uuid4(),
        library_id=payload.library_id,
        user_id=current_user.id,
        title=payload.title,
        description=payload.description,
        total_questions=len(payload.questions),
        is_edited_by_user=payload.is_edited_by_user,
    )
    db.add(quiz)
    await db.flush()  # Get quiz.id for FK

    for idx, q in enumerate(payload.questions):
        db.add(QuizQuestion(
            id=uuid4(),
            quiz_id=quiz.id,
            order_index=idx,
            question_text=q.question_text,
            option_a=q.option_a,
            option_b=q.option_b,
            option_c=q.option_c,
            option_d=q.option_d,
            correct_answer=q.correct_answer,
            explanation=q.explanation,
            source_page=q.source_page,
        ))
    await db.commit()
    await db.refresh(quiz)
    return await _to_quiz_out(db, quiz)


@router.get("/{quiz_id}", response_model=QuizOut)
async def get_quiz(
    quiz_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a quiz with all its questions."""
    try:
        uid = UUID(quiz_id) if isinstance(quiz_id, str) else quiz_id
    except (ValueError, TypeError):
        raise HTTPException(404, "Không tìm thấy quiz")

    quiz = await db.get(Quiz, uid)
    if not quiz or quiz.user_id != current_user.id:
        raise HTTPException(404, "Không tìm thấy quiz")
    return await _to_quiz_out(db, quiz)


@router.put("/{quiz_id}", response_model=QuizOut)
async def update_quiz(
    quiz_id: str,
    payload: QuizCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an existing quiz — replaces all questions."""
    try:
        uid = UUID(quiz_id) if isinstance(quiz_id, str) else quiz_id
    except (ValueError, TypeError):
        raise HTTPException(404, "Không tìm thấy quiz")

    quiz = await db.get(Quiz, uid)
    if not quiz or quiz.user_id != current_user.id:
        raise HTTPException(404, "Không tìm thấy quiz")

    # Delete old questions
    old_questions = await db.execute(
        select(QuizQuestion).where(QuizQuestion.quiz_id == quiz.id)
    )
    for old_q in old_questions.scalars().all():
        await db.delete(old_q)

    # Update quiz metadata
    quiz.title = payload.title
    quiz.description = payload.description
    quiz.total_questions = len(payload.questions)
    quiz.is_edited_by_user = True

    # Insert new questions
    for idx, q in enumerate(payload.questions):
        db.add(QuizQuestion(
            id=uuid4(),
            quiz_id=quiz.id,
            order_index=idx,
            question_text=q.question_text,
            option_a=q.option_a,
            option_b=q.option_b,
            option_c=q.option_c,
            option_d=q.option_d,
            correct_answer=q.correct_answer,
            explanation=q.explanation,
            source_page=q.source_page,
        ))

    await db.commit()
    await db.refresh(quiz)
    return await _to_quiz_out(db, quiz)


@router.get("/library/{library_id}", response_model=list[QuizOut])
async def list_quizzes_by_library(
    library_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all quizzes in a library."""
    result = await db.execute(
        select(Quiz)
        .where(Quiz.library_id == library_id, Quiz.user_id == current_user.id)
        .order_by(Quiz.created_at.desc())
    )
    quizzes = result.scalars().all()
    return [await _to_quiz_out(db, q) for q in quizzes]


async def _to_quiz_out(db: AsyncSession, quiz: Quiz) -> QuizOut:
    """Convert Quiz ORM model to QuizOut response with questions."""
    result = await db.execute(
        select(QuizQuestion)
        .where(QuizQuestion.quiz_id == quiz.id)
        .order_by(QuizQuestion.order_index)
    )
    questions = result.scalars().all()
    return QuizOut(
        id=quiz.id,
        title=quiz.title,
        description=quiz.description,
        total_questions=quiz.total_questions,
        is_edited_by_user=quiz.is_edited_by_user,
        questions=[QuizQuestionOut.model_validate(q) for q in questions],
    )
