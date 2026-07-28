"""Regression: ingest failures must not corrupt prior document versions."""
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.ingestion.versioning import DocumentVersionManager


BACKEND_ROOT = Path(__file__).resolve().parents[1]
INGEST_TASK_PATH = BACKEND_ROOT / "app" / "tasks" / "ingest_task.py"


@pytest.mark.asyncio
async def test_mark_previous_superseded_does_not_rewrite_status():
    """FAILED prior attempts must not be resurrected as COMPLETED."""
    db = AsyncMock()
    manager = DocumentVersionManager()

    await manager.mark_previous_superseded(db, "policy_volume-1.txt", new_version=2)

    db.execute.assert_not_awaited()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_mark_previous_superseded_noop_for_first_version():
    db = AsyncMock()
    manager = DocumentVersionManager()

    await manager.mark_previous_superseded(db, "policy_volume-1.txt", new_version=1)

    db.execute.assert_not_awaited()
    db.commit.assert_not_awaited()


def test_ingest_task_does_not_mark_failed_by_filename():
    """
    Re-ingest parse/classify failures used to SELECT by filename and mark
    whichever row came back first as FAILED — often the prior COMPLETED
    corpus document. Pipeline.run already marks its own doc_record.
    """
    source = INGEST_TASK_PATH.read_text()
    assert "Document.filename" not in source
    assert "DocumentStatus.FAILED" not in source
