"""Pydantic schemas for library and chat session endpoints."""

from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


# ── Library ──────────────────────────────────────────────────
class LibraryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    icon_or_color: Optional[str] = None


class LibraryOut(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    icon_or_color: Optional[str] = None
    total_documents: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Chat Session ─────────────────────────────────────────────
class SessionCreate(BaseModel):
    title: Optional[str] = None


class SessionOut(BaseModel):
    id: UUID
    library_id: UUID
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
