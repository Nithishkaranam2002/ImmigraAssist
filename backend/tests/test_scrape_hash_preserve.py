"""Scrape failure must not wipe a prior content hash (false CHANGED re-ingest)."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.models.scrape_record import ScrapeStatus
from app.scrapers.change_detector import ChangeDetector


def _scalar_result(record):
    return SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda: record))


@pytest.mark.asyncio
async def test_failure_update_preserves_existing_content_hash():
    detector = ChangeDetector()
    prior = SimpleNamespace(
        content_hash="abc123deadbeef",
        source_type="uscis_policy",
        doc_type="LAW",
        title="Vol 2 Ch 1",
        status=ScrapeStatus.UNCHANGED,
        error_message=None,
        last_scraped_at=datetime.now(timezone.utc),
        last_changed_at=datetime.now(timezone.utc),
        scrape_count=3,
    )
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_scalar_result(prior))
    db.commit = AsyncMock()
    db.add = MagicMock()

    await detector.update_record(
        db=db,
        url="https://www.uscis.gov/policy-manual/volume-2-part-h-chapter-1",
        new_hash="",
        source_type="uscis_policy",
        doc_type="LAW",
        title="Vol 2 Ch 1",
        status=ScrapeStatus.FAILED,
        error_message="timeout",
    )

    assert prior.content_hash == "abc123deadbeef"
    assert prior.status == ScrapeStatus.FAILED
    assert prior.error_message == "timeout"
    assert prior.scrape_count == 4
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_success_update_replaces_content_hash():
    detector = ChangeDetector()
    prior = SimpleNamespace(
        content_hash="oldhash",
        source_type="uscis_policy",
        doc_type="LAW",
        title="Vol 2 Ch 1",
        status=ScrapeStatus.UNCHANGED,
        error_message=None,
        last_scraped_at=datetime.now(timezone.utc),
        last_changed_at=datetime.now(timezone.utc),
        scrape_count=1,
    )
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_scalar_result(prior))
    db.commit = AsyncMock()

    await detector.update_record(
        db=db,
        url="https://www.uscis.gov/policy-manual/volume-2-part-h-chapter-1",
        new_hash="newhash999",
        source_type="uscis_policy",
        doc_type="LAW",
        title="Vol 2 Ch 1",
        status=ScrapeStatus.CHANGED,
    )

    assert prior.content_hash == "newhash999"
    assert prior.status == ScrapeStatus.CHANGED
