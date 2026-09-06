"""
Library and ChatSession CRUD routes.
"""

from uuid import uuid4
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_user
from app.db.models import Library, ChatSession, ChatMessage, Document, User, Quiz
from app.schemas.library import LibraryCreate, LibraryOut, SessionCreate, SessionOut
from app.schemas.chat import MessageOut

router = APIRouter(prefix="/api/libraries", tags=["libraries"])


# ── Library CRUD ─────────────────────────────────────────────

@router.get("", response_model=list[LibraryOut])
async def list_libraries(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all libraries belonging to the current user."""
    result = await db.execute(
        select(Library)
        .where(Library.user_id == current_user.id)
        .order_by(Library.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=LibraryOut, status_code=status.HTTP_201_CREATED)
async def create_library(
    payload: LibraryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new library for the current user."""
    library = Library(
        id=uuid4(),
        user_id=current_user.id,
        name=payload.name,
        description=payload.description,
        icon_or_color=payload.icon_or_color,
    )
    db.add(library)
    await db.commit()
    await db.refresh(library)
    return library


@router.get("/{library_id}", response_model=LibraryOut)
async def get_library(
    library_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific library by ID."""
    library = await db.get(Library, library_id)
    if not library or library.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Không tìm thấy thư viện")
    return library


@router.delete("/{library_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_library(
    library_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a library and all its associated data (cascade)."""
    library = await db.get(Library, library_id)
    if not library or library.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Không tìm thấy thư viện")
    await db.delete(library)
    await db.commit()


# ── Chat Sessions within a Library ───────────────────────────

@router.get("/{library_id}/sessions", response_model=list[SessionOut])
async def list_sessions(
    library_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all chat sessions in a library."""
    # Verify library ownership
    library = await db.get(Library, library_id)
    if not library or library.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Không tìm thấy thư viện")

    result = await db.execute(
        select(ChatSession)
        .where(
            ChatSession.library_id == library_id,
            ChatSession.user_id == current_user.id,
        )
        .order_by(ChatSession.updated_at.desc())
    )
    return result.scalars().all()


@router.post("/{library_id}/sessions", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(
    library_id: str,
    payload: SessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new chat session in a library."""
    library = await db.get(Library, library_id)
    if not library or library.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Không tìm thấy thư viện")

    session = ChatSession(
        id=uuid4(),
        library_id=library_id,
        user_id=current_user.id,
        title=payload.title or "Đoạn chat mới",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.delete("/{library_id}/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    library_id: str,
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a specific chat session."""
    session = await db.get(ChatSession, session_id)
    if not session or session.user_id != current_user.id or str(session.library_id) != library_id:
        raise HTTPException(status_code=404, detail="Không tìm thấy đoạn chat")
    await db.delete(session)
    await db.commit()


@router.get("/{library_id}/sessions/{session_id}/messages", response_model=list[MessageOut])
async def list_session_messages(
    library_id: str,
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all chat messages for a given session in chronological order."""
    session = await db.get(ChatSession, session_id)
    if not session or session.user_id != current_user.id or str(session.library_id) != library_id:
        raise HTTPException(status_code=404, detail="Không tìm thấy đoạn chat")

    result = await db.execute(
        select(ChatMessage)
        .options(selectinload(ChatMessage.quiz).selectinload(Quiz.questions))
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
    )
    return result.scalars().all()
