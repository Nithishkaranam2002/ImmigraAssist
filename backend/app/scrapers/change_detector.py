import hashlib
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models.scrape_record import ScrapeRecord, ScrapeStatus
from app.utils.logger import logger


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


class ChangeDetector:
    """
    Detects whether scraped content has changed since last scrape.
    Uses MD5 hash of clean text content for comparison.
    Stores records in PostgreSQL scrape_records table.
    """

    def compute_hash(self, content: str) -> str:
        """Compute MD5 hash of content."""
        return hashlib.md5(content.encode("utf-8")).hexdigest()

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
            # same content
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
                content_hash=new_hash,
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
            record.content_hash = new_hash
            record.source_type = source_type
            record.doc_type = doc_type
            record.title = title
            record.status = status
            record.error_message = error_message
            record.last_scraped_at = now
            record.scrape_count = (record.scrape_count or 0) + 1
            if old_hash != new_hash:
                record.last_changed_at = now

        await db.commit()
        logger.debug(f"Scrape record updated: {url} ({status})")
