import asyncio
import re
from typing import Optional
from dataclasses import dataclass, field
from app.scrapers.policy_urls import (
    DIRECT_CHAPTER_URLS,
    DISCOVERY_SEED_URLS,
    LINK_EXTRACT_JS,
    is_chapter_url,
    is_part_url,
    normalize_policy_url,
    parse_policy_url,
)
from app.utils.logger import logger


@dataclass
class ScrapedPage:
    url: str
    title: str
    content: str
    source_type: str
    doc_type: str
    metadata: dict = field(default_factory=dict)


@dataclass
class ScrapeReport:
    pages: list[ScrapedPage] = field(default_factory=list)
    failed_urls: list[str] = field(default_factory=list)
    discovered_urls: list[str] = field(default_factory=list)


MIN_CONTENT_LENGTH = 200
MAX_RETRIES = 3
PAGE_TIMEOUT_MS = 60000


class USCISPolicyScraper:

    def __init__(self):
        self.source_type = "uscis_policy"
        self.doc_type = "LAW"
        self.failed_urls: list[str] = []
        self.discovered_urls: list[str] = []

    async def scrape_all(self, urls: list[str] | None = None) -> list[ScrapedPage]:
        report = await self.scrape_with_report(urls)
        return report.pages

    async def scrape_iter(self, urls: list[str] | None = None):
        """Yield pages one-by-one so ingestion can start immediately."""
        self.failed_urls = []
        target_urls = urls or await self._discover_chapter_urls()
        logger.info(f"Streaming USCIS policy scraper — {len(target_urls)} chapters")

        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                )
                batch_size = 2
                for i in range(0, len(target_urls), batch_size):
                    for url in target_urls[i:i + batch_size]:
                        page = await self._scrape_page_with_retry(context, url)
                        if page:
                            yield page
                        else:
                            self.failed_urls.append(url)
                    if i + batch_size < len(target_urls):
                        await asyncio.sleep(3)
                await browser.close()
        except Exception as e:
            logger.error(f"Streaming policy scraper error: {e}")

    async def scrape_with_report(self, urls: list[str] | None = None) -> ScrapeReport:
        self.failed_urls = []
        report = ScrapeReport()

        if urls:
            target_urls = urls
        else:
            target_urls = await self._discover_chapter_urls()
            report.discovered_urls = list(target_urls)
            logger.info(f"Discovered {len(target_urls)} policy chapter URLs")

        logger.info(f"Starting USCIS policy scraper — {len(target_urls)} chapters")

        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                )

                batch_size = 2
                for i in range(0, len(target_urls), batch_size):
                    batch = target_urls[i:i + batch_size]
                    for url in batch:
                        page = await self._scrape_page_with_retry(context, url)
                        if page:
                            report.pages.append(page)
                        else:
                            report.failed_urls.append(url)
                            self.failed_urls.append(url)

                    if i + batch_size < len(target_urls):
                        await asyncio.sleep(3)

                await browser.close()

        except Exception as e:
            logger.error(f"Playwright scraper error: {e}")

        logger.info(
            f"USCIS policy scraper complete — "
            f"{len(report.pages)} scraped, {len(report.failed_urls)} failed"
        )
        return report

    async def _discover_chapter_urls(self) -> list[str]:
        """
        Crawl TOC, volume indexes, and part indexes to find all chapter URLs.
        Falls back to DIRECT_CHAPTER_URLS if discovery fails.
        """
        chapters: set[str] = {normalize_policy_url(u) for u in DIRECT_CHAPTER_URLS}
        parts_to_crawl: set[str] = set()

        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                )

                for seed_url in DISCOVERY_SEED_URLS:
                    links = await self._extract_policy_links(context, seed_url)
                    for link in links:
                        if is_chapter_url(link):
                            chapters.add(link)
                        elif is_part_url(link):
                            parts_to_crawl.add(link)

                logger.info(
                    f"Discovery pass 1 — {len(chapters)} chapters, "
                    f"{len(parts_to_crawl)} part indexes to crawl"
                )

                for part_url in sorted(parts_to_crawl):
                    links = await self._extract_policy_links(context, part_url)
                    for link in links:
                        if is_chapter_url(link):
                            chapters.add(link)

                await browser.close()
        except Exception as e:
            logger.warning(f"Dynamic URL discovery failed, using fallback list: {e}")

        discovered = sorted(chapters)
        self.discovered_urls = discovered
        logger.info(f"Policy URL discovery complete — {len(discovered)} chapter URLs")
        return discovered

    async def _extract_policy_links(self, context, url: str) -> list[str]:
        page = None
        try:
            page = await context.new_page()
            await page.route(
                "**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,mp4}",
                lambda route: route.abort(),
            )
            await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
            await page.wait_for_timeout(1500)
            raw_links = await page.evaluate(LINK_EXTRACT_JS)
            return [normalize_policy_url(u) for u in (raw_links or [])]
        except Exception as e:
            logger.warning(f"Link extraction failed for {url}: {e}")
            return []
        finally:
            if page:
                await page.close()

    async def _scrape_page_with_retry(self, context, url: str) -> Optional[ScrapedPage]:
        for attempt in range(1, MAX_RETRIES + 1):
            result = await self._scrape_page(context, url)
            if result:
                return result
            if attempt < MAX_RETRIES:
                wait = 5 * attempt
                logger.info(f"Retry {attempt}/{MAX_RETRIES} for {url} in {wait}s")
                await asyncio.sleep(wait)
        return None

    async def _scrape_page(self, context, url: str) -> Optional[ScrapedPage]:
        page = None
        try:
            page = await context.new_page()
            await page.route(
                "**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,mp4,mp3}",
                lambda route: route.abort(),
            )

            await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
            await page.wait_for_timeout(2000)

            try:
                await page.wait_for_selector(
                    ".policy-manual-content, .chapter-content, main, article",
                    timeout=15000,
                )
            except Exception:
                pass

            title = await page.title()
            title = title.replace(" | USCIS", "").strip()

            content = ""
            selectors = [
                ".policy-manual-content",
                ".chapter-content",
                "#chapter-content",
                "main .content",
                "article",
                "main",
                ".usa-prose",
            ]

            for selector in selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        content = await element.inner_text()
                        if len(content) > MIN_CONTENT_LENGTH:
                            break
                except Exception:
                    continue

            if len(content) < MIN_CONTENT_LENGTH:
                content = await page.inner_text("body")

            content = self._clean_content(content)

            if len(content) < MIN_CONTENT_LENGTH:
                logger.warning(f"Insufficient content from {url} ({len(content)} chars)")
                return None

            metadata = parse_policy_url(url)
            logger.info(f"Scraped {url} — {len(content)} chars — '{title[:50]}'")

            return ScrapedPage(
                url=url,
                title=title,
                content=content,
                source_type=self.source_type,
                doc_type=self.doc_type,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return None
        finally:
            if page:
                await page.close()

    def _clean_content(self, text: str) -> str:
        if not text:
            return ""

        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)

        noise_patterns = [
            r'Skip to main content.*?\n',
            r'Breadcrumb.*?\n',
            r'Share this page.*?\n',
            r'Last Reviewed.*?\n',
            r'Was this page helpful.*',
            r'USCIS\.gov.*?\n',
            r'An official website.*?\n',
        ]
        for pattern in noise_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        return text.strip()
