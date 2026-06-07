import asyncio
from collections.abc import Iterable
from celery import Task
from app.tasks.celery_app import celery_app
from app.db.postgres import AsyncSessionLocal
from app.db.models.scrape_record import ScrapeStatus
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


def _select_policy_urls_to_scrape(
    all_urls: Iterable[str],
    recorded_urls: Iterable[tuple[str, ScrapeStatus | str | None]],
) -> list[str]:
    """Return URLs that are missing or previously failed."""
    recorded_statuses = {url: status for url, status in recorded_urls}
    return sorted(
        url
        for url in set(all_urls)
        if (
            url not in recorded_statuses
            or recorded_statuses[url] == ScrapeStatus.FAILED
            or recorded_statuses[url] == ScrapeStatus.FAILED.value
        )
    )


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
    retry_failed: bool = True,
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
        f"bia: {scrape_bia}, retry_failed: {retry_failed}"
    )

    async def _run():
        async with AsyncSessionLocal() as db:
            orchestrator = ScraperOrchestrator()
            result = await orchestrator.run_all(
                db=db,
                scrape_policy=scrape_policy,
                scrape_news=scrape_news,
                scrape_bia=scrape_bia,
                retry_failed=retry_failed,
            )
            return {
                "status": "success",
                "total_scraped": result.total_scraped,
                "new_pages": result.new_pages,
                "changed_pages": result.changed_pages,
                "unchanged_pages": result.unchanged_pages,
                "failed_pages": result.failed_pages,
                "retried_urls": result.retried_urls,
                "ingestion_triggered": result.ingestion_triggered,
            }

    return self.loop.run_until_complete(_run())


@celery_app.task(
    bind=True,
    base=AsyncTask,
    name="app.tasks.scraper_task.run_missing_policy_task",
)
def run_missing_policy_task(self):
    """Scrape only policy chapter URLs not yet recorded."""
    from sqlalchemy import select
    from app.scrapers.uscis_policy_scraper import USCISPolicyScraper
    from app.scrapers.policy_urls import DIRECT_CHAPTER_URLS
    from app.db.models.scrape_record import ScrapeRecord

    async def _run():
        async with AsyncSessionLocal() as db:
            scraper = USCISPolicyScraper()
            discovered = await scraper._discover_chapter_urls()
            all_urls = set(discovered) | set(DIRECT_CHAPTER_URLS)

            result = await db.execute(select(ScrapeRecord.url, ScrapeRecord.status))
            missing = _select_policy_urls_to_scrape(all_urls, result.fetchall())
            logger.info(f"Missing policy URLs to scrape: {len(missing)}")

            if not missing:
                return {"status": "success", "missing": 0, "ingestion_triggered": 0}

            orchestrator = ScraperOrchestrator()
            orch_result = await orchestrator.run_all(
                db=db,
                scrape_policy=True,
                scrape_news=False,
                scrape_bia=False,
                retry_failed=True,
                force_policy_urls=missing,
            )
            return {
                "status": "success",
                "missing_urls": len(missing),
                "scraped": orch_result.total_scraped,
                "ingestion_triggered": orch_result.ingestion_triggered,
                "failed_pages": orch_result.failed_pages,
            }

    return self.loop.run_until_complete(_run())


