import os
import uuid
import aiofiles
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from app.scrapers.uscis_policy_scraper import USCISPolicyScraper
from app.scrapers.uscis_news_scraper import USCISNewsScraper
from app.scrapers.bia_scraper import BIAScraper
from app.scrapers.change_detector import ChangeDetector, ChangeType
from app.db.models.scrape_record import ScrapeStatus
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

    async def run_all(
        self,
        db: AsyncSession,
        scrape_policy: bool = True,
        scrape_news: bool = True,
        scrape_bia: bool = True,
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

        scrapers = []
        if scrape_policy:
            scrapers.append(USCISPolicyScraper())
        if scrape_news:
            scrapers.append(USCISNewsScraper())
        if scrape_bia:
            scrapers.append(BIAScraper())

        for scraper in scrapers:
            try:
                pages = await scraper.scrape_all()
                result.total_scraped += len(pages)

                for page in pages:
                    page_result = await self._process_page(db, page)
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
                uploaded_by="7d090fe7-cde4-4cdf-b403-b802c14abff6",
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