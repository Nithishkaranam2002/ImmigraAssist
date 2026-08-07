import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from app.db.postgres import get_db
from app.db.models.user import User, UserRole
from app.db.models.document import Document, DocumentStatus
from app.api.v1.dependencies import get_current_user, require_role
from app.config import settings
from app.services.upload_paths import UnsafeUploadFilename, build_upload_path
from app.utils.logger import logger

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentResponse(BaseModel):
    id: str
    filename: str
    doc_type: str
    status: str
    version: int
    visa_type: Optional[str]
    total_chunks: int
    uploaded_by: str
    created_at: str

    class Config:
        from_attributes = True


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """
    Upload a PDF document (law or case file).
    Saves file to disk and triggers async ingestion.
    Admin only.
    """
    try:
        safe_filename, file_path = build_upload_path(
            settings.UPLOAD_DIR, file.filename
        )
    except UnsafeUploadFilename as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    # validate file size
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit",
        )

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    logger.info(f"File saved: {file_path}")

    # trigger async ingestion task
    from app.tasks.ingest_task import ingest_document_task
    task = ingest_document_task.delay(
        file_path=file_path,
        filename=safe_filename,
        uploaded_by=str(current_user.id),
    )

    return {
        "message": "Document uploaded successfully. Ingestion started.",
        "filename": safe_filename,
        "task_id": task.id,
    }


@router.get("/", response_model=list[DocumentResponse])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all documents with their ingestion status."""
    result = await db.execute(
        select(Document).order_by(Document.created_at.desc())
    )
    documents = result.scalars().all()
    return [
        DocumentResponse(
            id=str(d.id),
            filename=d.filename,
            doc_type=d.doc_type.value,
            status=d.status.value,
            version=d.version,
            visa_type=d.visa_type,
            total_chunks=d.total_chunks or 0,
            uploaded_by=str(d.uploaded_by),
            created_at=str(d.created_at),
        )
        for d in documents
    ]


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single document by ID."""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return DocumentResponse(
        id=str(doc.id),
        filename=doc.filename,
        doc_type=doc.doc_type.value,
        status=doc.status.value,
        version=doc.version,
        visa_type=doc.visa_type,
        total_chunks=doc.total_chunks or 0,
        uploaded_by=str(doc.uploaded_by),
        created_at=str(doc.created_at),
    )