import asyncio
import httpx
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from app.utils.logger import logger


@dataclass
class ScrapedPage:
    url: str
    title: str
    raw_html: str
    clean_text: str
    source_type: str        # uscis_policy, uscis_news, bia
    doc_type: str           # law or case
    metadata: dict


class BaseScraper(ABC):
    """
    Base class for all scrapers.
    Handles HTTP requests, rate limiting, retries, and user agent.
    Each specific scraper inherits this and implements parse().
    """

    # be a good citizen — don't hammer government servers
    RATE_LIMIT_SECONDS = 2.0
    MAX_RETRIES = 3
    TIMEOUT_SECONDS = 30

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; ImmigraAssist-Bot/1.0; "
            "Legal Research Tool; contact@immigraassist.com)"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    def __init__(self):
        self.client = httpx.AsyncClient(
            headers=self.HEADERS,
            timeout=self.TIMEOUT_SECONDS,
            follow_redirects=True,
        )

    async def fetch(self, url: str) -> Optional[str]:
        """
        Fetch a URL with retry logic and rate limiting.
        Returns raw HTML or None on failure.
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                await asyncio.sleep(self.RATE_LIMIT_SECONDS)
                response = await self.client.get(url)
                response.raise_for_status()
                logger.debug(f"Fetched: {url} ({response.status_code})")
                return response.text

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.warning(f"404 Not Found: {url}")
                    return None
                if e.response.status_code == 429:
                    wait = 10 * (attempt + 1)
                    logger.warning(f"Rate limited on {url} — waiting {wait}s")
                    await asyncio.sleep(wait)
                else:
                    logger.error(f"HTTP error {e.response.status_code} for {url}")

            except httpx.TimeoutException:
                logger.warning(f"Timeout on {url} — attempt {attempt + 1}/{self.MAX_RETRIES}")
                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Unexpected error fetching {url}: {e}")
                break

        logger.error(f"Failed to fetch {url} after {self.MAX_RETRIES} attempts")
        return None

    @abstractmethod
    async def get_urls(self) -> list[str]:
        """Return list of URLs to scrape."""
        pass

    @abstractmethod
    async def parse(self, url: str, html: str) -> Optional[ScrapedPage]:
        """Parse HTML into a ScrapedPage."""
        pass

    async def scrape_all(self) -> list[ScrapedPage]:
        """
        Main entry point.
        Gets all URLs, fetches and parses each one.
        """
        urls = await self.get_urls()
        logger.info(f"{self.__class__.__name__}: scraping {len(urls)} URLs")

        pages = []
        for url in urls:
            html = await self.fetch(url)
            if not html:
                continue
            page = await self.parse(url, html)
            if page:
                pages.append(page)

        logger.info(f"{self.__class__.__name__}: scraped {len(pages)} pages")
        return pages

    async def close(self):
        await self.client.aclose()
