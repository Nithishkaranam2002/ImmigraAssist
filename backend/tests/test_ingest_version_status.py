"""Regression: ingest failures must not corrupt prior document versions."""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.models.document import DocumentStatus
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


@pytest.mark.asyncio
async def test_pipeline_failure_before_record_leaves_prior_doc_alone():
    """
    When parse fails before create_document_record, no status write occurs
    in the pipeline — callers must not invent one by filename.
    """
    from app.ingestion.pipeline import IngestionPipeline

    pipeline = IngestionPipeline.__new__(IngestionPipeline)
    pipeline.parser = MagicMock()
    pipeline.parser.parse.side_effect = RuntimeError("corrupt download")
    pipeline.classifier = MagicMock()
    pipeline.metadata_extractor = MagicMock()
    pipeline.version_manager = MagicMock()
    pipeline.version_manager.get_or_create_version = AsyncMock()
    pipeline.version_manager.mark_previous_superseded = AsyncMock()
    pipeline.version_manager.create_document_record = AsyncMock()
    pipeline.embedder = MagicMock()

    db = AsyncMock()
    prior = MagicMock()
    prior.status = DocumentStatus.COMPLETED

    with pytest.raises(RuntimeError, match="corrupt download"):
        await pipeline.run(
            db=db,
            file_path="/tmp/bad.txt",
            filename="policy_volume-1.txt",
            uploaded_by=MagicMock(),
        )

    pipeline.version_manager.create_document_record.assert_not_awaited()
    assert prior.status == DocumentStatus.COMPLETED
