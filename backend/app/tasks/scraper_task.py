import asyncio
from celery import Task
from app.tasks.celery_app import celery_app
from app.db.postgres import AsyncSessionLocal
from app.scrapers.scraper_orchestrator import ScraperOrchestrator
from app.utils.logger import logger


class AsyncTask(Task):
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
    name="app.tasks.scraper_task.run_scrapers_task",
)
def run_scrapers_task(
    self,
    scrape_policy: bool = True,
    scrape_news: bool = True,
    scrape_bia: bool = True,
):
    """
    Celery task that runs all scrapers.

    Schedule:
    - News scraper: daily
    - Policy + BIA: weekly

    Can also be triggered manually from admin dashboard.
    """
    logger.info(
        f"Scraper task started — "
        f"policy: {scrape_policy}, "
        f"news: {scrape_news}, "
        f"bia: {scrape_bia}"
    )

    async def _run():
        async with AsyncSessionLocal() as db:
            orchestrator = ScraperOrchestrator()
            result = await orchestrator.run_all(
                db=db,
                scrape_policy=scrape_policy,
                scrape_news=scrape_news,
                scrape_bia=scrape_bia,
            )
            return {
                "status": "success",
                "total_scraped": result.total_scraped,
                "new_pages": result.new_pages,
                "changed_pages": result.changed_pages,
                "unchanged_pages": result.unchanged_pages,
                "ingestion_triggered": result.ingestion_triggered,
            }

    return self.loop.run_until_complete(_run())


# add to beat schedule in celery_app.py
SCRAPER_BEAT_SCHEDULE = {
    "scrape-news-daily": {
        "task": "app.tasks.scraper_task.run_scrapers_task",
        "schedule": 86400.0,  # every 24 hours
        "kwargs": {
            "scrape_policy": False,
            "scrape_news": True,
            "scrape_bia": False,
        },
    },
    "scrape-full-weekly": {
        "task": "app.tasks.scraper_task.run_scrapers_task",
        "schedule": 604800.0,  # every 7 days
        "kwargs": {
            "scrape_policy": True,
            "scrape_news": True,
            "scrape_bia": True,
        },
    },
}
