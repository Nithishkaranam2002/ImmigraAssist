"""Latest COMPLETED version per filename must gate retrieval document IDs."""

import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.db.models.document import DocumentType
from app.ingestion.versioning import DocumentVersionManager
from app.retrieval.metadata_filter import MetadataFilter


def test_latest_completed_stmt_source_requires_completed_and_max_version():
    src = inspect.getsource(MetadataFilter._latest_completed_ids_stmt)
    assert "DocumentStatus.COMPLETED" in src
    assert "func.max" in src
    assert "Document.filename" in src
    assert "Document.version" in src


def test_fetch_helpers_delegate_to_latest_completed_stmt():
    fetch_src = inspect.getsource(MetadataFilter._fetch_document_ids)
    all_src = inspect.getsource(MetadataFilter._fetch_all_document_ids)
    assert "_latest_completed_ids_stmt" in fetch_src
    assert "_latest_completed_ids_stmt" in all_src
    # Old behavior selected every version with no status filter.
    assert "select(Document.id).where(Document.doc_type == doc_type)" not in fetch_src


@pytest.mark.asyncio
async def test_fetch_document_ids_executes_latest_completed_stmt():
    mf = MetadataFilter()
    expected = mf._latest_completed_ids_stmt(DocumentType.LAW, visa_type="h1b")
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=SimpleNamespace(
            fetchall=lambda: [("new-v2-id",), ("other-latest-id",)]
        )
    )

    ids = await mf._fetch_document_ids(
        db=db,
        doc_type=DocumentType.LAW,
        visa_type="h1b",
    )

    assert ids == ["new-v2-id", "other-latest-id"]
    executed = db.execute.await_args.args[0]
    # Same shape as the helper (visa + latest COMPLETED join).
    assert type(executed) is type(expected)
    assert len(executed._where_criteria) == len(expected._where_criteria)


@pytest.mark.asyncio
async def test_fetch_all_document_ids_executes_latest_completed_stmt():
    mf = MetadataFilter()
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=SimpleNamespace(fetchall=lambda: [("only-latest",)])
    )

    ids = await mf._fetch_all_document_ids(db, DocumentType.CASE)

    assert ids == ["only-latest"]
    db.execute.assert_awaited()


@pytest.mark.asyncio
async def test_mark_previous_superseded_does_not_rewrite_status():
    """Align with retrieval-side latest filter: do not resurrect FAILED→COMPLETED."""
    db = AsyncMock()
    manager = DocumentVersionManager()

    await manager.mark_previous_superseded(db, "policy_volume-1.txt", new_version=2)

    db.execute.assert_not_awaited()
    db.commit.assert_not_awaited()
