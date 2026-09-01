"""Pydantic schemas for document upload and ingestion progress."""

from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class DocumentOut(BaseModel):
    id: UUID
    library_id: UUID
    file_name: str
    total_pages: Optional[int] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class IngestionProgressOut(BaseModel):
    document_id: UUID
    file_name: str
    status: str
    total_chunks: int
    processed_chunks: int
    progress_percent: float
    error_message: Optional[str] = None
