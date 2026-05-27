import asyncio
from celery import Task
from app.tasks.celery_app import celery_app
from app.db.postgres import AsyncSessionLocal
from app.ingestion.section_mapper import SectionMapper
from app.utils.logger import logger


class AsyncTask(Task):
    """Base task with async event loop management."""
    _loop = None

    @property
    def loop(self):
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        return self._loop


@celery_app.task(
    bind=True,
    base=AsyncTask,
    name="app.tasks.remap_task.remap_sections_task",
    max_retries=2,
    default_retry_delay=120,
)
def remap_sections_task(self, document_id: str):
    """
    Background task that runs section mapper after
    a new law document is ingested.

    Finds all old section references in case chunks
    and maps them to the new document's sections.

    Only runs after law document ingestion — not for case files.
    """
    logger.info(
        f"Section remap task started — "
        f"triggered by doc: {document_id}, "
        f"task_id: {self.request.id}"
    )

    async def _run():
        async with AsyncSessionLocal() as db:
            try:
                mapper = SectionMapper()
                await mapper.run(db=db)

                logger.info(
                    f"Section remap complete — "
                    f"triggered by doc: {document_id}"
                )

                return {
                    "status": "success",
                    "triggered_by_document": document_id,
                }

            except Exception as e:
                logger.error(
                    f"Section remap failed — "
                    f"doc: {document_id}, "
                    f"error: {e}"
                )
                raise

    try:
        return self.loop.run_until_complete(_run())
    except Exception as exc:
        logger.error(
            f"Remap task failed — "
            f"doc: {document_id}, "
            f"attempt: {self.request.retries + 1}/2"
        )
        raise self.retry(exc=exc)