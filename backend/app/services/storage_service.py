"""
MinIO S3-compatible storage service for PDF files.
"""

import io
from minio import Minio
from app.core.config import settings

# ── MinIO Client (singleton) ────────────────────────────────
_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_USE_SSL,
)


def _ensure_bucket():
    """Create the bucket if it doesn't exist."""
    if not _client.bucket_exists(settings.MINIO_BUCKET_NAME):
        _client.make_bucket(settings.MINIO_BUCKET_NAME)


def upload_file(object_name: str, file_data: bytes, content_type: str = "application/pdf"):
    """Upload a file to MinIO."""
    _ensure_bucket()
    _client.put_object(
        bucket_name=settings.MINIO_BUCKET_NAME,
        object_name=object_name,
        data=io.BytesIO(file_data),
        length=len(file_data),
        content_type=content_type,
    )


def get_file(object_name: str) -> bytes:
    """Download a file from MinIO and return its bytes."""
    response = _client.get_object(
        bucket_name=settings.MINIO_BUCKET_NAME,
        object_name=object_name,
    )
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def delete_file(object_name: str):
    """Delete a file from MinIO."""
    _client.remove_object(
        bucket_name=settings.MINIO_BUCKET_NAME,
        object_name=object_name,
    )


def get_presigned_url(object_name: str, expires_hours: int = 1) -> str:
    """Generate a presigned URL for temporary file access."""
    from datetime import timedelta
    return _client.presigned_get_object(
        bucket_name=settings.MINIO_BUCKET_NAME,
        object_name=object_name,
        expires=timedelta(hours=expires_hours),
    )
