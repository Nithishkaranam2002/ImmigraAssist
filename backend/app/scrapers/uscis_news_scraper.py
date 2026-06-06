import asyncio
import re
from dataclasses import dataclass
from typing import Optional
from app.utils.logger import logger


BASE_URL = "https://www.uscis.gov"

NEWS_LISTING_URLS = [
    "https://www.uscis.gov/newsroom/alerts",
    "https://www.uscis.gov/newsroom/news-releases",
    "https://www.uscis.gov/newsroom/policy-manual-updates",
]

MIN_CONTENT_LENGTH = 100


@dataclass
class ScrapedPage:
    url: str
    title: str
    content: str
    source_type: str
    doc_type: str


class USCISNewsScraper:
    """
    Scrapes USCIS newsroom for policy alerts, news releases,
    and policy manual updates using Playwright for JS-rendered content.
    """

    def __init__(self):
        self.source_type = "uscis_news"
        self.doc_type = "LAW"

    async def scrape_all(self) -> list[ScrapedPage]:
        logger.info("USCIS News scraper started")
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

                # first collect all article URLs from listing pages
                article_urls = []
                for listing_url in NEWS_LISTING_URLS:
                    urls = await self._get_article_urls(context, listing_url)
                    article_urls.extend(urls)
                    logger.info(f"Found {len(urls)} articles at {listing_url}")
                    await asyncio.sleep(1)

                # deduplicate
                article_urls = list(set(article_urls))
                logger.info(f"Total news articles found: {len(article_urls)}")

                # limit to latest 50 articles
                article_urls = article_urls[:50]

                # scrape articles in batches of 2 (more reliable on small servers)
                for i in range(0, len(article_urls), 2):
                    batch = article_urls[i:i + 3]
                    tasks = [self._scrape_article(context, url) for url in batch]
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    for url, result in zip(batch, results):
                        if isinstance(result, Exception):
                            logger.error(f"Failed to scrape {url}: {result}")
                        elif result:
                            pages.append(result)

                    if i + 2 < len(article_urls):
                        await asyncio.sleep(2)

                await browser.close()

        except Exception as e:
            logger.error(f"USCIS News Playwright scraper error: {e}")

        logger.info(f"USCIS News scraper complete — {len(pages)} articles scraped")
        return pages

    async def _get_article_urls(self, context, listing_url: str) -> list[str]:
        """Extract article URLs from a news listing page."""
        page = None
        try:
            page = await context.new_page()
            await page.route(
                "**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2}",
                lambda route: route.abort()
            )
            await page.goto(listing_url, wait_until="domcontentloaded", timeout=60000)

            # wait for article links to load
            try:
                await page.wait_for_selector("a[href*='/newsroom/']", timeout=10000)
            except Exception:
                pass

            # extract all newsroom article links
            links = await page.evaluate("""() => {
                const links = document.querySelectorAll('a[href]');
                const urls = [];
                for (const link of links) {
                    const href = link.href;
                    if (href.includes('/newsroom/alerts/') ||
                        href.includes('/newsroom/news-releases/') ||
                        href.includes('/newsroom/policy-manual-updates/')) {
                        urls.push(href);
                    }
                }
                return [...new Set(urls)];
            }""")

            return links or []

        except Exception as e:
            logger.error(f"Failed to get article URLs from {listing_url}: {e}")
            return []
        finally:
            if page:
                await page.close()

    async def _scrape_article(self, context, url: str) -> Optional[ScrapedPage]:
        """Scrape a single USCIS news article."""
        page = None
        try:
            page = await context.new_page()
            await page.route(
                "**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,mp4,mp3}",
                lambda route: route.abort()
            )

            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(1500)

            # extract title
            title = await page.title()
            title = title.replace(" | USCIS", "").strip()

            # try to get h1
            try:
                h1 = await page.inner_text("h1")
                if h1:
                    title = h1.strip()
            except Exception:
                pass

            # extract date
            date = ""
            try:
                date = await page.inner_text(
                    ".field--name-field-date, .date, time, .published-date",
                )
                date = date.strip()
            except Exception:
                pass

            # extract main content
            content = ""
            selectors = [
                ".usa-prose",
                "main .content",
                ".field--name-body",
                "article",
                "main",
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
                logger.warning(f"Insufficient content from {url}")
                return None

            # detect alert type
            alert_type = self._detect_alert_type(url, title, content)

            # build structured content
            full_content = f"USCIS {alert_type.upper()}: {title}\n"
            if date:
                full_content += f"Date: {date}\n"
            full_content += f"Source: {url}\n"
            full_content += f"\n{'=' * 60}\n\n"
            full_content += content

            logger.info(f"Scraped news: '{title[:60]}' ({len(content)} chars)")

            return ScrapedPage(
                url=url,
                title=title,
                content=full_content,
                source_type=self.source_type,
                doc_type=self.doc_type,
            )

        except Exception as e:
            logger.error(f"Error scraping news article {url}: {e}")
            return None
        finally:
            if page:
                await page.close()

    def _detect_alert_type(self, url: str, title: str, content: str) -> str:
        if "alerts" in url:
            return "Alert"
        if "news-releases" in url:
            return "News Release"
        if "policy-manual-updates" in url:
            return "Policy Update"
        text = (title + content).lower()
        if any(w in text for w in ["fee", "filing fee", "premium processing"]):
            return "Fee Update"
        if any(w in text for w in ["form", "i-765", "i-485", "i-129"]):
            return "Form Update"
        return "News"

    def _clean_content(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        noise_patterns = [
            r'Skip to main content.*?\n',
            r'Breadcrumb.*?\n',
            r'Share this page.*?\n',
            r'Was this page helpful.*',
            r'An official website.*?\n',
            r'USCIS\.gov.*?\n',
        ]
        for pattern in noise_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        return text.strip()

    async def close(self):
        pass