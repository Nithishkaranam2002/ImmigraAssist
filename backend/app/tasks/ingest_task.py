import asyncio
from celery import Task
from sqlalchemy import select
from app.tasks.celery_app import celery_app
from app.db.postgres import AsyncSessionLocal
from app.db.models.document import Document, DocumentStatus
from app.db.models.scrape_record import ScrapeStatus
from app.ingestion.pipeline import IngestionPipeline
from app.scrapers.change_detector import ChangeDetector
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
    source_url: str | None = None,
    scrape_final_status: str | None = None,
):
    """
    Background task for full document ingestion.

    Flow:
    1. Create async DB session
    2. Run IngestionPipeline
    3. On success → trigger remap task if law doc; confirm scrape record
    4. On failure → mark document as failed, retry up to 3 times;
       after final failure mark scrape record failed when source_url set
    """
    logger.info(
        f"Celery ingest task started — "
        f"file: {filename}, "
        f"task_id: {self.request.id}"
    )

    async def _confirm_scrape_success():
        if not source_url or not scrape_final_status:
            return
        try:
            final_status = ScrapeStatus(scrape_final_status)
        except ValueError:
            final_status = ScrapeStatus.CHANGED
        async with AsyncSessionLocal() as db:
            detector = ChangeDetector()
            await detector.mark_ingest_complete(
                db=db,
                url=source_url,
                final_status=final_status,
            )

    async def _confirm_scrape_failure(error: Exception):
        if not source_url:
            return
        async with AsyncSessionLocal() as db:
            detector = ChangeDetector()
            await detector.mark_ingest_failed(
                db=db,
                url=source_url,
                error_message=str(error),
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
                # mark document as failed in DB
                try:
                    result = await db.execute(
                        select(Document).where(
                            Document.filename == filename
                        )
                    )
                    doc = result.scalars().first()
                    if doc:
                        doc.status = DocumentStatus.FAILED
                        doc.error_message = str(e)
                        await db.commit()
                except Exception as db_error:
                    logger.error(
                        f"Failed to update document status: {db_error}"
                    )
                raise

    try:
        result = self.loop.run_until_complete(_run())
        self.loop.run_until_complete(_confirm_scrape_success())
        return result
    except Exception as exc:
        logger.error(
            f"Ingest task failed — "
            f"file: {filename}, "
            f"attempt: {self.request.retries + 1}/"
            f"{(self.max_retries or 0) + 1}"
        )
        is_final = self.request.retries >= (self.max_retries or 0)
        if is_final:
            try:
                self.loop.run_until_complete(_confirm_scrape_failure(exc))
            except Exception as scrape_err:
                logger.error(
                    f"Failed to mark scrape ingest failure: {scrape_err}"
                )
            raise
        raise self.retry(exc=exc)
