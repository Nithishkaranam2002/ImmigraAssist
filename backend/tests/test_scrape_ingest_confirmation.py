"""Regression tests for scraper ingest confirmation and retrieval doc status."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.models.document import DocumentStatus
from app.db.models.scrape_record import ScrapeStatus
from app.scrapers.change_detector import (
    INGEST_PENDING_MESSAGE,
    INGEST_PENDING_RETRY_AFTER,
    ChangeDetector,
    ChangeType,
)


def _record(**kwargs):
    defaults = {
        "url": "https://www.uscis.gov/policy-manual/volume-1-part-a",
        "content_hash": "abc123",
        "status": ScrapeStatus.FAILED,
        "error_message": INGEST_PENDING_MESSAGE,
        "last_scraped_at": datetime.now(timezone.utc),
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_ingest_pending_within_timeout_does_not_reprocess():
    detector = ChangeDetector()
    record = _record()
    assert detector._should_retry_failed(record) is False
    assert detector._is_ingest_pending(record) is True


def test_ingest_pending_after_timeout_retries():
    detector = ChangeDetector()
    record = _record(
        last_scraped_at=datetime.now(timezone.utc) - INGEST_PENDING_RETRY_AFTER - timedelta(minutes=1),
    )
    assert detector._should_retry_failed(record) is True


def test_hard_failure_always_retries():
    detector = ChangeDetector()
    record = _record(
        error_message="celery worker blew up",
        last_scraped_at=datetime.now(timezone.utc),
    )
    assert detector._should_retry_failed(record) is True


def test_successful_status_does_not_retry_on_same_hash():
    detector = ChangeDetector()
    record = _record(
        status=ScrapeStatus.NEW,
        error_message=None,
    )
    assert detector._should_retry_failed(record) is False


@pytest.mark.asyncio
async def test_check_preserves_ingest_pending_status():
    detector = ChangeDetector()
    content = "policy chapter body"
    content_hash = detector.compute_hash(content)
    record = _record(content_hash=content_hash)

    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = record
    db.execute = AsyncMock(return_value=result)

    change = await detector.check(db, record.url, content)
    assert change.should_process is False
    assert change.skip_status_update is True
    assert change.change_type == ChangeType.UNCHANGED


@pytest.mark.asyncio
async def test_check_retries_true_failure_with_same_hash():
    detector = ChangeDetector()
    content = "policy chapter body"
    content_hash = detector.compute_hash(content)
    record = _record(
        content_hash=content_hash,
        error_message="ingestion failed: boom",
    )

    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = record
    db.execute = AsyncMock(return_value=result)

    change = await detector.check(db, record.url, content)
    assert change.should_process is True
    assert change.change_type == ChangeType.CHANGED


@pytest.mark.asyncio
async def test_update_record_preserves_hash_on_empty_failure():
    detector = ChangeDetector()
    existing = SimpleNamespace(
        url="https://example.com/a",
        content_hash="goodhash",
        source_type="uscis_policy",
        doc_type="law",
        title="old",
        status=ScrapeStatus.NEW,
        error_message=None,
        last_scraped_at=datetime.now(timezone.utc),
        last_changed_at=datetime.now(timezone.utc),
        scrape_count=2,
    )
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = existing
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock()
    db.commit = AsyncMock()

    await detector.update_record(
        db=db,
        url=existing.url,
        new_hash="",
        source_type="uscis_policy",
        doc_type="law",
        title="old",
        status=ScrapeStatus.FAILED,
        error_message="Page scrape failed after retries",
    )

    assert existing.content_hash == "goodhash"
    assert existing.status == ScrapeStatus.FAILED


@pytest.mark.asyncio
async def test_process_page_marks_ingest_pending_not_new():
    import sys
    from app.scrapers.scraper_orchestrator import ScraperOrchestrator
    from app.scrapers.change_detector import ChangeResult

    orch = ScraperOrchestrator()
    page = SimpleNamespace(
        url="https://www.justice.gov/eoir/page/file/example",
        title="BIA decision",
        source_type="bia",
        doc_type="case",
        content="full chapter text",
        metadata={},
    )
    change = ChangeResult(
        url=page.url,
        change_type=ChangeType.NEW,
        old_hash=None,
        new_hash="hash1",
        should_process=True,
    )

    delayed = MagicMock()
    fake_task = SimpleNamespace(delay=delayed)
    fake_module = SimpleNamespace(ingest_document_task=fake_task)

    with (
        patch.object(orch.change_detector, "check", AsyncMock(return_value=change)),
        patch.object(orch.change_detector, "update_record", AsyncMock()) as update_record,
        patch.object(orch, "_save_as_temp_file", AsyncMock(return_value="/tmp/x.txt")),
        patch.dict(sys.modules, {"app.tasks.ingest_task": fake_module}),
    ):
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        result = await orch._process_page(db, page, "user-id")

    assert result == "new"
    update_record.assert_awaited()
    kwargs = update_record.await_args.kwargs
    assert kwargs["status"] == ScrapeStatus.FAILED
    assert kwargs["error_message"] == INGEST_PENDING_MESSAGE
    delayed.assert_called_once()
    call_kwargs = delayed.call_args.kwargs
    assert call_kwargs["source_url"] == page.url
    assert call_kwargs["scrape_final_status"] == ScrapeStatus.NEW.value


def test_metadata_filter_queries_require_completed_status():
    import inspect
    from app.retrieval import metadata_filter as mf

    src = inspect.getsource(mf.MetadataFilter._fetch_document_ids)
    assert "DocumentStatus.COMPLETED" in src
    src_all = inspect.getsource(mf.MetadataFilter._fetch_all_document_ids)
    assert "DocumentStatus.COMPLETED" in src_all
    # Guard against accidental unused import removal
    assert DocumentStatus.COMPLETED.value == "completed"
