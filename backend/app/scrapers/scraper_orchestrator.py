import os
import uuid
import aiofiles
from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.user import User, UserRole
from app.scrapers.uscis_policy_scraper import USCISPolicyScraper
from app.scrapers.uscis_news_scraper import USCISNewsScraper
from app.scrapers.bia_scraper import BIAScraper
from app.scrapers.change_detector import ChangeDetector, ChangeType
from app.db.models.scrape_record import ScrapeStatus
from app.db.models.policy_alert import PolicyAlert
from app.config import settings
from app.utils.logger import logger


@dataclass
class OrchestratorResult:
    total_scraped: int
    new_pages: int
    changed_pages: int
    unchanged_pages: int
    failed_pages: int
    ingestion_triggered: int
    retried_urls: int = 0


class ScraperOrchestrator:
    """
    Coordinates all scrapers and triggers ingestion for changed content.

    Flow for each scraped page:
    1. Scrape content
    2. Check if content changed (change detector)
    3. If new or changed → save as temp file → trigger ingestion pipeline
    4. Update scrape record
    5. Log results
    """

    def __init__(self):
        self.change_detector = ChangeDetector()

    async def _get_scraper_user_id(self, db: AsyncSession) -> str:
        """Resolve a valid user ID for scraper-triggered ingestion."""
        for query in (
            select(User).where(User.role == UserRole.SUPER_ADMIN).limit(1),
            select(User).where(User.email == settings.ADMIN_EMAIL).limit(1),
            select(User).limit(1),
        ):
            result = await db.execute(query)
            user = result.scalars().first()
            if user:
                return str(user.id)
        raise RuntimeError("No user found for scraper ingestion")

    async def run_all(
        self,
        db: AsyncSession,
        scrape_policy: bool = True,
        scrape_news: bool = True,
        scrape_bia: bool = True,
        retry_failed: bool = False,
        force_policy_urls: list[str] | None = None,
    ) -> OrchestratorResult:
        logger.info("Scraper orchestrator started")

        result = OrchestratorResult(
            total_scraped=0,
            new_pages=0,
            changed_pages=0,
            unchanged_pages=0,
            failed_pages=0,
            ingestion_triggered=0,
        )

        scraper_user_id = await self._get_scraper_user_id(db)

        scrapers = []
        if scrape_policy:
            scrapers.append(USCISPolicyScraper())
        if scrape_news:
            scrapers.append(USCISNewsScraper())
        if scrape_bia:
            scrapers.append(BIAScraper())

        for scraper in scrapers:
            try:
                if isinstance(scraper, USCISPolicyScraper):
                    urls = force_policy_urls
                    async for page in scraper.scrape_iter(urls=urls):
                        result.total_scraped += 1
                        page_result = await self._process_page(db, page, scraper_user_id)
                        if page_result == "new":
                            result.new_pages += 1
                            result.ingestion_triggered += 1
                        elif page_result == "changed":
                            result.changed_pages += 1
                            result.ingestion_triggered += 1
                        elif page_result == "unchanged":
                            result.unchanged_pages += 1
                        elif page_result == "failed":
                            result.failed_pages += 1

                    if scraper.failed_urls:
                        await self._record_failed_urls(db, scraper.failed_urls)
                        result.failed_pages += len(scraper.failed_urls)
                    if retry_failed and scraper.failed_urls:
                        logger.info(f"Retrying {len(scraper.failed_urls)} failed policy URLs")
                        failed = list(scraper.failed_urls)
                        scraper.failed_urls = []
                        async for page in scraper.scrape_iter(urls=failed):
                            result.retried_urls += 1
                            result.total_scraped += 1
                            page_result = await self._process_page(db, page, scraper_user_id)
                            if page_result in ("new", "changed"):
                                result.ingestion_triggered += 1
                                if page_result == "new":
                                    result.new_pages += 1
                                else:
                                    result.changed_pages += 1
                        if scraper.failed_urls:
                            await self._record_failed_urls(db, scraper.failed_urls)
                        result.failed_pages += len(scraper.failed_urls)
                else:
                    pages = await scraper.scrape_all()
                    result.total_scraped += len(pages)
                    for page in pages:
                        page_result = await self._process_page(db, page, scraper_user_id)
                        if page_result == "new":
                            result.new_pages += 1
                            result.ingestion_triggered += 1
                        elif page_result == "changed":
                            result.changed_pages += 1
                            result.ingestion_triggered += 1
                        elif page_result == "unchanged":
                            result.unchanged_pages += 1
                        elif page_result == "failed":
                            result.failed_pages += 1

            except Exception as e:
                logger.error(f"Scraper {scraper.__class__.__name__} failed: {e}")

        logger.info(
            f"Orchestrator complete — "
            f"scraped: {result.total_scraped}, "
            f"new: {result.new_pages}, "
            f"changed: {result.changed_pages}, "
            f"unchanged: {result.unchanged_pages}, "
            f"ingestion triggered: {result.ingestion_triggered}"
        )

        return result

    def _get_content(self, page) -> str:
        """
        Safely get content from a page object.
        Handles both old scraper format (clean_text)
        and new Playwright format (content).
        """
        if hasattr(page, "content") and page.content:
            return page.content
        if hasattr(page, "clean_text") and page.clean_text:
            return page.clean_text
        return ""

    def _get_metadata(self, page) -> dict:
        """
        Safely get metadata from a page object.
        Returns empty dict if no metadata attribute.
        """
        if hasattr(page, "metadata") and page.metadata:
            return page.metadata
        return {}

    async def _process_page(
        self,
        db: AsyncSession,
        page,
        scraper_user_id: str,
    ) -> str:
        """
        Process a single scraped page.
        Returns: "new", "changed", "unchanged", or "failed"
        """
        try:
            content = self._get_content(page)

            if not content:
                logger.warning(f"Empty content for {page.url} — skipping")
                return "failed"

            # check for changes
            change_result = await self.change_detector.check(
                db=db,
                url=page.url,
                content=content,
            )

            if not change_result.should_process:
                await self.change_detector.update_record(
                    db=db,
                    url=page.url,
                    new_hash=change_result.new_hash,
                    source_type=page.source_type,
                    doc_type=page.doc_type,
                    title=page.title,
                    status=ScrapeStatus.UNCHANGED,
                )
                return "unchanged"

            # save content as temp file for ingestion
            file_path = await self._save_as_temp_file(page, content)

            # trigger ingestion pipeline
            from app.tasks.ingest_task import ingest_document_task
            ingest_document_task.delay(
                file_path=file_path,
                filename=f"{page.source_type}_{self._url_to_filename(page.url)}.txt",
                uploaded_by=scraper_user_id,
            )

            # update scrape record
            status = (
                ScrapeStatus.NEW
                if change_result.change_type == ChangeType.NEW
                else ScrapeStatus.CHANGED
            )
            await self.change_detector.update_record(
                db=db,
                url=page.url,
                new_hash=change_result.new_hash,
                source_type=page.source_type,
                doc_type=page.doc_type,
                title=page.title,
                status=status,
            )

            if page.source_type in ("uscis_news", "uscis_policy"):
                summary = content[:300].replace("\n", " ").strip()
                db.add(
                    PolicyAlert(
                        title=page.title[:500],
                        url=page.url,
                        source_type=page.source_type,
                        summary=summary,
                    )
                )

            logger.info(
                f"{status.value.upper()}: {page.title[:60]} "
                f"({len(content)} chars) → ingestion triggered"
            )

            return change_result.change_type.value

        except Exception as e:
            logger.error(f"Failed to process page {page.url}: {e}")
            try:
                await self.change_detector.update_record(
                    db=db,
                    url=page.url,
                    new_hash="",
                    source_type=page.source_type,
                    doc_type=page.doc_type,
                    title=page.title,
                    status=ScrapeStatus.FAILED,
                    error_message=str(e),
                )
            except Exception:
                pass
            return "failed"

    async def _save_as_temp_file(self, page, content: str) -> str:
        """
        Save scraped content as a temp text file
        so the existing ingestion pipeline can process it.
        """
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        filename = f"scraped_{page.source_type}_{uuid.uuid4()}.txt"
        file_path = os.path.join(settings.UPLOAD_DIR, filename)

        metadata = self._get_metadata(page)

        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(f"TITLE: {page.title}\n")
            await f.write(f"SOURCE: {page.source_type}\n")
            await f.write(f"URL: {page.url}\n")
            await f.write(f"DOC_TYPE: {page.doc_type}\n")
            for key, value in metadata.items():
                await f.write(f"{key.upper()}: {value}\n")
            await f.write("\n" + "=" * 60 + "\n\n")
            await f.write(content)

        return file_path

    def _url_to_filename(self, url: str) -> str:
        import re
        name = url.replace("https://", "").replace("http://", "")
        name = re.sub(r"[^\w]", "_", name)
        return name[:80]

    async def _record_failed_urls(self, db: AsyncSession, urls: list[str]) -> None:
        """Persist scrape failures so admin completeness reflects gaps."""
        for url in urls:
            try:
                await self.change_detector.update_record(
                    db=db,
                    url=url,
                    new_hash="",
                    source_type="uscis_policy",
                    doc_type="LAW",
                    title=url.split("/")[-1].replace("-", " ").title()[:200],
                    status=ScrapeStatus.FAILED,
                    error_message="Page scrape failed after retries",
                )
            except Exception as e:
                logger.warning(f"Could not record failed URL {url}: {e}")