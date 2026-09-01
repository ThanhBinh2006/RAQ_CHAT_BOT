"""Pydantic schemas for chat messages."""

from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class MessageCreate(BaseModel):
    content: str
    role: str = "user"


class CitationOut(BaseModel):
    page_number: Optional[int] = None
    document_id: Optional[str] = None


class MessageOut(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    citations: Optional[List[CitationOut]] = None
    quiz_id: Optional[UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}
