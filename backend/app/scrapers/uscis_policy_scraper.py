import asyncio
import re
from typing import Optional
from dataclasses import dataclass, field
from app.utils.logger import logger


@dataclass
class ScrapedPage:
    url: str
    title: str
    content: str
    source_type: str
    doc_type: str


@dataclass
class ScrapeReport:
    pages: list[ScrapedPage] = field(default_factory=list)
    failed_urls: list[str] = field(default_factory=list)


# Fallback chapter URLs if dynamic discovery fails
DIRECT_CHAPTER_URLS = [
    "https://www.uscis.gov/policy-manual/volume-1-part-a-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-1-part-a-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-1-part-a-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-1-part-b-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-1-part-b-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-1-part-b-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-2-part-a-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-2-part-a-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-2-part-b-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-2-part-b-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-2-part-b-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-2-part-f-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-2-part-f-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-2-part-f-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-2-part-f-chapter-4",
    "https://www.uscis.gov/policy-manual/volume-2-part-f-chapter-5",
    "https://www.uscis.gov/policy-manual/volume-3-part-b-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-3-part-b-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-3-part-b-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-3-part-c-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-3-part-c-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-6-part-b-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-6-part-b-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-6-part-b-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-6-part-b-chapter-4",
    "https://www.uscis.gov/policy-manual/volume-6-part-d-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-6-part-d-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-6-part-d-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-6-part-e-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-6-part-e-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-6-part-f-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-6-part-f-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-6-part-f-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-6-part-f-chapter-4",
    "https://www.uscis.gov/policy-manual/volume-6-part-g-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-6-part-g-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-6-part-g-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-7-part-a-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-7-part-a-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-7-part-a-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-7-part-b-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-7-part-b-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-7-part-b-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-8-part-a-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-8-part-a-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-8-part-b-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-8-part-b-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-8-part-b-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-8-part-g-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-8-part-g-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-8-part-g-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-9-part-a-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-9-part-a-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-9-part-b-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-9-part-b-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-10-part-a-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-10-part-a-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-10-part-b-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-10-part-b-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-12-part-a-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-12-part-a-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-12-part-b-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-12-part-b-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-12-part-b-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-12-part-b-chapter-4",
    "https://www.uscis.gov/policy-manual/volume-12-part-d-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-12-part-d-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-12-part-d-chapter-3",
]

POLICY_INDEX_URLS = [
    "https://www.uscis.gov/policy-manual",
    "https://www.uscis.gov/policy-manual/table-of-contents",
]

MIN_CONTENT_LENGTH = 200
MAX_RETRIES = 3
PAGE_TIMEOUT_MS = 60000


class USCISPolicyScraper:

    def __init__(self):
        self.source_type = "uscis_policy"
        self.doc_type = "LAW"
        self.failed_urls: list[str] = []

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
        """Crawl policy manual index pages to find all chapter URLs."""
        discovered: set[str] = set(DIRECT_CHAPTER_URLS)

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

                for index_url in POLICY_INDEX_URLS:
                    page = None
                    try:
                        page = await context.new_page()
                        await page.route(
                            "**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2}",
                            lambda route: route.abort(),
                        )
                        await page.goto(index_url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
                        links = await page.evaluate("""() => {
                            const urls = [];
                            for (const a of document.querySelectorAll('a[href]')) {
                                const href = a.href;
                                if (href.includes('/policy-manual/volume-') &&
                                    href.includes('-chapter-')) {
                                    urls.push(href.split('#')[0].split('?')[0]);
                                }
                            }
                            return [...new Set(urls)];
                        }""")
                        discovered.update(links or [])
                    except Exception as e:
                        logger.warning(f"URL discovery failed for {index_url}: {e}")
                    finally:
                        if page:
                            await page.close()

                await browser.close()
        except Exception as e:
            logger.warning(f"Dynamic URL discovery failed, using fallback list: {e}")

        return sorted(discovered)

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

            logger.info(f"Scraped {url} — {len(content)} chars — '{title[:50]}'")

            return ScrapedPage(
                url=url,
                title=title,
                content=content,
                source_type=self.source_type,
                doc_type=self.doc_type,
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
