from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models.document import Document, DocumentType, DocumentStatus
from app.utils.logger import logger
import uuid


class DocumentVersionManager:
    """
    Handles document versioning.
    When a new version of a law doc is uploaded, the old one stays
    but is marked as superseded. New one gets version = old + 1.
    """

    async def get_or_create_version(
        self,
        db: AsyncSession,
        filename: str,
        doc_type: DocumentType,
        visa_type: str | None,
    ) -> int:
        """
        Check if a doc with same filename exists.
        If yes return next version number.
        If no return version 1.
        """
        result = await db.execute(
            select(Document)
            .where(Document.filename == filename)
            .where(Document.doc_type == doc_type)
            .order_by(Document.version.desc())
        )
        existing = result.scalars().first()

        if existing:
            next_version = existing.version + 1
            logger.info(
                f"Document '{filename}' already exists at v{existing.version}. "
                f"New version will be v{next_version}"
            )
            return next_version

        return 1

    async def mark_previous_superseded(
        self,
        db: AsyncSession,
        filename: str,
        new_version: int,
    ):
        """
        Reserve a supersession hook for prior versions.

        Previously this forced status=COMPLETED on every older row, which
        resurrected FAILED ingest attempts into the retrievable corpus.
        True supersession needs an is_latest (or equivalent) flag; until
        that exists, leave prior statuses untouched.
        """
        if new_version <= 1:
            return

        logger.info(
            f"New version v{new_version} for '{filename}' — "
            f"prior versions left unchanged pending is_latest support"
        )

    async def create_document_record(
        self,
        db: AsyncSession,
        filename: str,
        file_path: str,
        doc_type: DocumentType,
        version: int,
        visa_type: str | None,
        uploaded_by: uuid.UUID,
    ) -> Document:
        """Create the document record in PostgreSQL."""
        doc = Document(
            filename=filename,
            file_path=file_path,
            doc_type=doc_type,
            status=DocumentStatus.PENDING,
            version=version,
            visa_type=visa_type,
            uploaded_by=uploaded_by,
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        logger.info(f"Created document record: {doc.id} v{version}")
        return doc