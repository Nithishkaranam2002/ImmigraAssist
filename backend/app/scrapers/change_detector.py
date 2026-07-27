import hashlib
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models.scrape_record import ScrapeRecord, ScrapeStatus
from app.utils.logger import logger

# ScrapeRecord stays FAILED with this message until Celery ingest confirms.
# Avoids a new Postgres enum value while still retrying incomplete ingest.
INGEST_PENDING_MESSAGE = "INGEST_PENDING"
INGEST_PENDING_RETRY_AFTER = timedelta(hours=1)


class ChangeType(str, Enum):
    NEW = "new"               # never seen before
    CHANGED = "changed"       # seen before, content changed
    UNCHANGED = "unchanged"   # seen before, same content


@dataclass
class ChangeResult:
    url: str
    change_type: ChangeType
    old_hash: str | None
    new_hash: str
    should_process: bool      # True for NEW and CHANGED
    # When True, caller must not overwrite scrape status (ingest still pending).
    skip_status_update: bool = False


class ChangeDetector:
    """
    Detects whether scraped content has changed since last scrape.
    Uses MD5 hash of clean text content for comparison.
    Stores records in PostgreSQL scrape_records table.
    """

    def compute_hash(self, content: str) -> str:
        """Compute MD5 hash of content."""
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def _is_ingest_pending(self, record: ScrapeRecord) -> bool:
        return (
            record.status == ScrapeStatus.FAILED
            and record.error_message == INGEST_PENDING_MESSAGE
        )

    def _should_retry_failed(self, record: ScrapeRecord) -> bool:
        """Retry hard failures always; retry ingest-pending only after timeout."""
        if record.status != ScrapeStatus.FAILED:
            return False
        if not self._is_ingest_pending(record):
            return True
        if not record.last_scraped_at:
            return True
        scraped_at = record.last_scraped_at
        if scraped_at.tzinfo is None:
            scraped_at = scraped_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - scraped_at >= INGEST_PENDING_RETRY_AFTER

    async def check(
        self,
        db: AsyncSession,
        url: str,
        content: str,
    ) -> ChangeResult:
        """
        Check if content at URL has changed.
        Returns ChangeResult with change type and whether to process.
        """
        new_hash = self.compute_hash(content)

        result = await db.execute(
            select(ScrapeRecord).where(ScrapeRecord.url == url)
        )
        record = result.scalars().first()

        if not record:
            # never seen before
            logger.info(f"NEW content detected: {url}")
            return ChangeResult(
                url=url,
                change_type=ChangeType.NEW,
                old_hash=None,
                new_hash=new_hash,
                should_process=True,
            )

        if record.content_hash == new_hash:
            # Re-process if previous scrape/ingestion failed (or ingest never confirmed)
            if self._should_retry_failed(record):
                logger.info(f"RETRY previously failed: {url}")
                return ChangeResult(
                    url=url,
                    change_type=ChangeType.CHANGED,
                    old_hash=record.content_hash,
                    new_hash=new_hash,
                    should_process=True,
                )
            if self._is_ingest_pending(record):
                logger.debug(f"INGEST still pending: {url}")
                return ChangeResult(
                    url=url,
                    change_type=ChangeType.UNCHANGED,
                    old_hash=record.content_hash,
                    new_hash=new_hash,
                    should_process=False,
                    skip_status_update=True,
                )
            logger.debug(f"UNCHANGED: {url}")
            return ChangeResult(
                url=url,
                change_type=ChangeType.UNCHANGED,
                old_hash=record.content_hash,
                new_hash=new_hash,
                should_process=False,
            )

        # content changed
        logger.info(f"CHANGED content detected: {url}")
        return ChangeResult(
            url=url,
            change_type=ChangeType.CHANGED,
            old_hash=record.content_hash,
            new_hash=new_hash,
            should_process=True,
        )

    async def update_record(
        self,
        db: AsyncSession,
        url: str,
        new_hash: str,
        source_type: str,
        doc_type: str,
        title: str,
        status: ScrapeStatus,
        error_message: str | None = None,
    ):
        """
        Create or update the scrape record after processing.
        """
        result = await db.execute(
            select(ScrapeRecord).where(ScrapeRecord.url == url)
        )
        record = result.scalars().first()

        now = datetime.now(timezone.utc)

        if not record:
            record = ScrapeRecord(
                url=url,
                content_hash=new_hash or None,
                source_type=source_type,
                doc_type=doc_type,
                title=title,
                status=status,
                error_message=error_message,
                last_scraped_at=now,
                last_changed_at=now,
                scrape_count=1,
            )
            db.add(record)
        else:
            old_hash = record.content_hash
            # Preserve last good hash when recording a failure with empty hash
            if new_hash or status != ScrapeStatus.FAILED:
                record.content_hash = new_hash
            record.source_type = source_type
            record.doc_type = doc_type
            record.title = title
            record.status = status
            record.error_message = error_message
            record.last_scraped_at = now
            record.scrape_count = (record.scrape_count or 0) + 1
            if new_hash and old_hash != new_hash:
                record.last_changed_at = now

        await db.commit()
        logger.debug(f"Scrape record updated: {url} ({status})")

    async def mark_ingest_complete(
        self,
        db: AsyncSession,
        url: str,
        final_status: ScrapeStatus,
    ) -> None:
        """Promote an ingest-pending scrape record after successful ingestion."""
        result = await db.execute(
            select(ScrapeRecord).where(ScrapeRecord.url == url)
        )
        record = result.scalars().first()
        if not record:
            logger.warning(f"No scrape record to mark complete for {url}")
            return
        record.status = final_status
        record.error_message = None
        await db.commit()
        logger.info(f"Scrape ingest confirmed: {url} → {final_status.value}")

    async def mark_ingest_failed(
        self,
        db: AsyncSession,
        url: str,
        error_message: str,
    ) -> None:
        """Mark scrape record failed after ingest retries are exhausted."""
        result = await db.execute(
            select(ScrapeRecord).where(ScrapeRecord.url == url)
        )
        record = result.scalars().first()
        if not record:
            logger.warning(f"No scrape record to mark failed for {url}")
            return
        record.status = ScrapeStatus.FAILED
        record.error_message = (error_message or "ingestion failed")[:2000]
        await db.commit()
        logger.warning(f"Scrape ingest failed permanently: {url}")
