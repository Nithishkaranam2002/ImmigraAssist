import asyncio
import re
from typing import Optional
from dataclasses import dataclass
from app.utils.logger import logger


@dataclass
class ScrapedPage:
    url: str
    title: str
    content: str
    source_type: str
    doc_type: str


# All USCIS Policy Manual chapter URLs we want to scrape
DIRECT_CHAPTER_URLS = [
    # Volume 1 - General Policies and Procedures
    "https://www.uscis.gov/policy-manual/volume-1-part-a-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-1-part-a-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-1-part-a-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-1-part-b-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-1-part-b-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-1-part-b-chapter-3",

    # Volume 2 - Nonimmigrants
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

    # Volume 3 - Humanitarian Protection and Parole
    "https://www.uscis.gov/policy-manual/volume-3-part-b-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-3-part-b-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-3-part-b-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-3-part-c-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-3-part-c-chapter-2",

    # Volume 6 - Immigrants
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

    # Volume 7 - Adjustment of Status
    "https://www.uscis.gov/policy-manual/volume-7-part-a-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-7-part-a-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-7-part-a-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-7-part-b-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-7-part-b-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-7-part-b-chapter-3",

    # Volume 8 - Admissibility
    "https://www.uscis.gov/policy-manual/volume-8-part-a-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-8-part-a-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-8-part-b-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-8-part-b-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-8-part-b-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-8-part-g-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-8-part-g-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-8-part-g-chapter-3",

    # Volume 9 - Waivers
    "https://www.uscis.gov/policy-manual/volume-9-part-a-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-9-part-a-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-9-part-b-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-9-part-b-chapter-2",

    # Volume 10 - Employment Authorization
    "https://www.uscis.gov/policy-manual/volume-10-part-a-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-10-part-a-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-10-part-b-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-10-part-b-chapter-2",

    # Volume 12 - Citizenship and Naturalization
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

MIN_CONTENT_LENGTH = 200


class USCISPolicyScraper:

    def __init__(self):
        self.source_type = "uscis_policy"
        self.doc_type = "LAW"

    async def scrape_all(self) -> list[ScrapedPage]:
        logger.info(f"Starting Playwright USCIS scraper — {len(DIRECT_CHAPTER_URLS)} chapters")
        pages = []

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

                # scrape in batches of 3 to avoid overwhelming USCIS
                batch_size = 3
                for i in range(0, len(DIRECT_CHAPTER_URLS), batch_size):
                    batch = DIRECT_CHAPTER_URLS[i:i + batch_size]
                    tasks = [self._scrape_page(context, url) for url in batch]
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    for url, result in zip(batch, results):
                        if isinstance(result, Exception):
                            logger.error(f"Failed to scrape {url}: {result}")
                        elif result:
                            pages.append(result)

                    # polite delay between batches
                    if i + batch_size < len(DIRECT_CHAPTER_URLS):
                        await asyncio.sleep(2)

                await browser.close()

        except Exception as e:
            logger.error(f"Playwright scraper error: {e}")

        logger.info(f"Playwright scraper complete — {len(pages)} pages scraped")
        return pages

    async def _scrape_page(self, context, url: str) -> Optional[ScrapedPage]:
        page = None
        try:
            page = await context.new_page()

            # block images, fonts, media to speed up
            await page.route(
                "**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,mp4,mp3}",
                lambda route: route.abort()
            )

            await page.goto(url, wait_until="networkidle", timeout=30000)

            # wait for main content to load
            try:
                await page.wait_for_selector(
                    ".policy-manual-content, .chapter-content, main, article",
                    timeout=10000
                )
            except Exception:
                # continue even if selector not found
                pass

            # extract title
            title = await page.title()
            title = title.replace(" | USCIS", "").strip()

            # extract main content — try multiple selectors
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

            # fallback — get all body text
            if len(content) < MIN_CONTENT_LENGTH:
                content = await page.inner_text("body")

            # clean the content
            content = self._clean_content(content)

            if len(content) < MIN_CONTENT_LENGTH:
                logger.warning(f"Insufficient content from {url} ({len(content)} chars)")
                return None

            logger.info(f"Scraped {url} — {len(content)} chars — '{title}'")

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

        # remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)

        # remove navigation noise
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