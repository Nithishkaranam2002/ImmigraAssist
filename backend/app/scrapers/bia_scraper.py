import httpx
import asyncio
from dataclasses import dataclass
from typing import Optional
from app.utils.logger import logger


COURTLISTENER_BASE = "https://www.courtlistener.com/api/rest/v4"

# Immigration-specific search terms to get relevant BIA/AAO decisions
BIA_SEARCH_QUERIES = [
    "H-1B specialty occupation denial appeal",
    "H-4 dependent spouse employment authorization",
    "asylum persecution withholding removal",
    "adjustment of status lawful permanent resident",
    "L-1 intracompany transferee denial",
    "naturalization citizenship good moral character",
    "deportation removal order appeal",
    "I-140 immigrant petition denial",
    "AC21 portability H-1B job change",
    "asylum credibility determination",
]

AAO_SEARCH_QUERIES = [
    "extraordinary ability O-1 visa denial",
    "national interest waiver EB-2 denial",
    "outstanding researcher professor EB-1",
    "multinational manager L-1A denial",
    "specialized knowledge L-1B denial",
    "investor visa EB-5 denial",
]


@dataclass
class ScrapedPage:
    url: str
    title: str
    content: str
    source_type: str
    doc_type: str


class BIAScraper:
    """
    Fetches BIA and AAO immigration case decisions from CourtListener API.
    CourtListener has 4000+ BIA decisions indexed as structured data.
    Much more reliable than scraping DOJ website directly.
    """

    TIMEOUT = 20
    MAX_PER_QUERY = 3

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=self.TIMEOUT,
            headers={
                "User-Agent": "ImmigraAssist/1.0 Legal Research Tool",
                "Accept": "application/json",
            }
        )

    async def scrape_all(self) -> list[ScrapedPage]:
        logger.info("BIA/AAO scraper started — fetching from CourtListener")
        pages = []

        # fetch BIA decisions
        bia_pages = await self._fetch_court_decisions(
            queries=BIA_SEARCH_QUERIES,
            court="bia",
            source_type="bia",
        )
        pages.extend(bia_pages)

        # fetch AAO decisions
        aao_pages = await self._fetch_court_decisions(
            queries=AAO_SEARCH_QUERIES,
            court="aao",
            source_type="aao",
        )
        pages.extend(aao_pages)

        logger.info(f"BIA/AAO scraper complete — {len(pages)} decisions fetched")
        return pages

    async def _fetch_court_decisions(
        self,
        queries: list[str],
        court: str,
        source_type: str,
    ) -> list[ScrapedPage]:
        pages = []
        seen_ids = set()

        for query in queries:
            try:
                params = {
                    "q": query,
                    "type": "o",
                    "order_by": "score desc",
                    "stat_Precedential": "on",
                    "page_size": self.MAX_PER_QUERY,
                }

                # filter by court for BIA
                if court == "bia":
                    params["court"] = "bia"

                response = await self.client.get(
                    f"{COURTLISTENER_BASE}/search/",
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

                results = data.get("results", [])
                logger.info(
                    f"CourtListener {court.upper()} query '{query[:40]}' "
                    f"→ {len(results)} results"
                )

                for result in results:
                    case_id = str(
                        result.get("cluster_id") or result.get("id", "")
                    )

                    if case_id in seen_ids:
                        continue
                    seen_ids.add(case_id)

                    page = self._parse_result(result, source_type)
                    if page:
                        pages.append(page)

                # polite delay between queries
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Failed to fetch {court} decisions for '{query}': {e}")
                continue

        return pages

    def _parse_result(self, result: dict, source_type: str) -> Optional[ScrapedPage]:
        try:
            case_name = (
                result.get("caseName") or
                result.get("caseNameFull") or
                "Unknown Case"
            )

            case_id = str(
                result.get("cluster_id") or result.get("id", "")
            )

            court = result.get("court", source_type.upper())
            date_filed = (
                result.get("dateFiled") or
                result.get("date_filed", "")
            )

            citations = result.get("citation", [])
            citation = citations[0] if citations else ""

            # get snippet from opinions
            snippet = result.get("snippet", "")
            if not snippet:
                opinions = result.get("opinions", [])
                if opinions:
                    snippet = opinions[0].get("snippet", "")

            # clean HTML from snippet
            import re
            if snippet:
                snippet = re.sub(r"<[^>]+>", "", snippet).strip()

            syllabus = result.get("syllabus", "")
            if syllabus:
                syllabus = re.sub(r"<[^>]+>", "", syllabus).strip()

            absolute_url = result.get("absolute_url", "")
            url = (
                f"https://www.courtlistener.com{absolute_url}"
                if absolute_url
                else f"https://www.courtlistener.com/opinion/{case_id}/"
            )

            # detect outcome
            outcome = self._detect_outcome(snippet + " " + syllabus)

            # build full content for ingestion
            content_parts = [
                f"CASE: {case_name}",
                f"SOURCE: {source_type.upper()} Decision",
                f"COURT: {court}",
                f"DATE: {date_filed}",
                f"CITATION: {citation}",
                f"OUTCOME: {outcome or 'unknown'}",
                f"URL: {url}",
                "",
                "=" * 60,
                "",
            ]

            if syllabus:
                content_parts.append(f"SYLLABUS:\n{syllabus}\n")

            if snippet:
                content_parts.append(f"DECISION EXCERPT:\n{snippet}")

            content = "\n".join(content_parts)

            if len(content) < 100:
                return None

            title = f"{case_name} ({citation or case_id})"

            logger.info(f"Parsed {source_type.upper()} decision: {case_name[:60]}")

            return ScrapedPage(
                url=url,
                title=title,
                content=content,
                source_type=source_type,
                doc_type="CASE",
            )

        except Exception as e:
            logger.error(f"Failed to parse {source_type} result: {e}")
            return None

    def _detect_outcome(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        if any(w in text_lower for w in ["granted", "approved", "sustained"]):
            return "granted"
        if any(w in text_lower for w in ["denied", "dismissed"]):
            return "denied"
        if any(w in text_lower for w in ["remanded", "vacated"]):
            return "remanded"
        if any(w in text_lower for w in ["affirmed", "upheld"]):
            return "affirmed"
        if any(w in text_lower for w in ["reversed"]):
            return "reversed"
        return None

    async def close(self):
        await self.client.aclose()