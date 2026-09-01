"""
Document upload and ingestion progress routes.
"""

import asyncio
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db, get_current_user
from app.db.models import Document, Library, IngestionJob, User
from app.schemas.document import DocumentOut, IngestionProgressOut

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentOut, status_code=201)
async def upload_document(
    library_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a PDF file to a library.
    Stores the file in MinIO and triggers background ingestion.
    """
    # Validate library ownership
    library = await db.get(Library, library_id)
    if not library or library.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Không tìm thấy thư viện")

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file PDF")

    # Read file content
    file_content = await file.read()

    # Upload to MinIO
    from app.services.storage_service import upload_file
    file_path = f"{current_user.id}/{library_id}/{uuid4()}/{file.filename}"
    upload_file(file_path, file_content, content_type="application/pdf")

    # Create document record
    doc = Document(
        id=uuid4(),
        library_id=library_id,
        user_id=current_user.id,
        file_name=file.filename,
        file_path_minio=file_path,
        status="processing",
    )
    db.add(doc)

    # Create ingestion job
    job = IngestionJob(
        id=uuid4(),
        document_id=doc.id,
    )
    db.add(job)

    # Update library document count
    library.total_documents = (library.total_documents or 0) + 1

    await db.commit()
    await db.refresh(doc)

    # Trigger background ingestion
    asyncio.create_task(_run_ingestion(str(doc.id), file_content))

    return doc


async def _run_ingestion(document_id: str, file_content: bytes):
    """Background task to process PDF and create vector embeddings."""
    from app.services.ingestion_service import ingest_document
    try:
        await ingest_document(document_id, file_content)
    except Exception as e:
        # Log the error; ingestion_service will update the job status
        import traceback
        traceback.print_exc()


@router.get("/{document_id}/progress", response_model=IngestionProgressOut)
async def get_progress(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Poll the ingestion progress for a document."""
    doc = await db.get(Document, document_id)
    if not doc or doc.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")

    result = await db.execute(
        select(IngestionJob).where(IngestionJob.document_id == document_id)
    )
    job = result.scalar_one_or_none()

    return IngestionProgressOut(
        document_id=doc.id,
        file_name=doc.file_name,
        status=doc.status,
        total_chunks=job.total_chunks if job else 0,
        processed_chunks=job.processed_chunks if job else 0,
        progress_percent=float(job.progress_percent) if job else 0,
        error_message=job.error_message if job else None,
    )


@router.get("/library/{library_id}", response_model=list[DocumentOut])
async def list_documents(
    library_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all documents in a library."""
    library = await db.get(Library, library_id)
    if not library or library.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Không tìm thấy thư viện")

    result = await db.execute(
        select(Document)
        .where(Document.library_id == library_id)
        .order_by(Document.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a document, its chunks, and the file from MinIO."""
    doc = await db.get(Document, document_id)
    if not doc or doc.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")

    # Delete from MinIO
    from app.services.storage_service import delete_file
    try:
        delete_file(doc.file_path_minio)
    except Exception:
        pass  # File may already be gone

    # Update library count
    library = await db.get(Library, doc.library_id)
    if library:
        library.total_documents = max((library.total_documents or 1) - 1, 0)

    # Cascade delete handles chunks and ingestion job
    await db.delete(doc)
    await db.commit()
