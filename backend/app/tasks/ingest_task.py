import asyncio
from celery import Task
from app.tasks.celery_app import celery_app
from app.db.postgres import AsyncSessionLocal
from app.ingestion.pipeline import IngestionPipeline
from app.utils.logger import logger
import uuid


class DatabaseTask(Task):
    """
    Base task class that manages async database sessions.
    Celery runs synchronously so we manage the event loop here.
    """
    _loop = None

    @property
    def loop(self):
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        return self._loop


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.tasks.ingest_task.ingest_document_task",
    max_retries=3,
    default_retry_delay=60,
)
def ingest_document_task(
    self,
    file_path: str,
    filename: str,
    uploaded_by: str,
):
    """
    Background task for full document ingestion.

    Flow:
    1. Create async DB session
    2. Run IngestionPipeline
    3. On success → trigger remap task if law doc
    4. On failure → mark document as failed, retry up to 3 times
    """
    logger.info(
        f"Celery ingest task started — "
        f"file: {filename}, "
        f"task_id: {self.request.id}"
    )

    async def _run():
        async with AsyncSessionLocal() as db:
            try:
                pipeline = IngestionPipeline()
                doc = await pipeline.run(
                    db=db,
                    file_path=file_path,
                    filename=filename,
                    uploaded_by=uuid.UUID(uploaded_by),
                )

                logger.info(
                    f"Ingestion complete — "
                    f"doc_id: {doc.id}, "
                    f"chunks: {doc.total_chunks}, "
                    f"type: {doc.doc_type.value}"
                )

                # trigger section remapper only for law documents
                if doc.doc_type.value == "law":
                    logger.info(
                        f"Triggering section remap task "
                        f"for law doc: {doc.id}"
                    )
                    from app.tasks.remap_task import remap_sections_task
                    remap_sections_task.delay(document_id=str(doc.id))

                return {
                    "status": "success",
                    "document_id": str(doc.id),
                    "total_chunks": doc.total_chunks,
                }

            except Exception as e:
                logger.error(
                    f"Ingestion failed for '{filename}': {e}"
                )
                # IngestionPipeline.run already marks its own doc_record FAILED
                # when a new version row was created. Do NOT look up by
                # filename here — that can mark a prior COMPLETED corpus
                # document FAILED when parse/classify fails before a new
                # row exists, or when .first() returns the wrong version.
                raise

    try:
        return self.loop.run_until_complete(_run())
    except Exception as exc:
        logger.error(
            f"Ingest task failed — "
            f"file: {filename}, "
            f"attempt: {self.request.retries + 1}/3"
        )
        raise self.retry(exc=exc)