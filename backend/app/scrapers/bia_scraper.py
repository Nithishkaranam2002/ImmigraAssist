import httpx
import asyncio
import re
from dataclasses import dataclass
from typing import Optional
from app.config import settings
from app.utils.logger import logger


COURTLISTENER_BASE = "https://www.courtlistener.com/api/rest/v4"

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
    "cancellation of removal",
    "U visa humanitarian",
    "T visa trafficking victim",
    "VAWA self petition",
    "TPS temporary protected status",
    "consular processing immigrant visa",
    "INA 212 waiver inadmissibility",
    "Matter of administrative appeal",
    "BIA precedent immigration",
    "employment based immigration petition",
]

AAO_SEARCH_QUERIES = [
    "extraordinary ability O-1 visa denial",
    "national interest waiver EB-2 denial",
    "outstanding researcher professor EB-1",
    "multinational manager L-1A denial",
    "specialized knowledge L-1B denial",
    "investor visa EB-5 denial",
    "NIW national interest waiver",
    "EB-1A extraordinary ability",
    "EB-1B outstanding professor researcher",
    "O-1B arts athletics",
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
    Fetches full opinion text when available for richer chunking.
    """

    TIMEOUT = 30
    MAX_PER_PAGE = 20
    MAX_PAGES_PER_QUERY = 3

    def __init__(self):
        headers = {
            "User-Agent": "ImmigraAssist/1.0 Legal Research Tool",
            "Accept": "application/json",
        }
        token = getattr(settings, "COURTLISTENER_API_TOKEN", "") or ""
        if token:
            headers["Authorization"] = f"Token {token}"

        self.client = httpx.AsyncClient(timeout=self.TIMEOUT, headers=headers)

    async def scrape_all(self) -> list[ScrapedPage]:
        logger.info("BIA/AAO scraper started — fetching from CourtListener")
        pages = []

        bia_pages = await self._fetch_court_decisions(
            queries=BIA_SEARCH_QUERIES,
            court="bia",
            source_type="bia",
        )
        pages.extend(bia_pages)

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
        seen_ids: set[str] = set()

        for query in queries:
            for page_num in range(1, self.MAX_PAGES_PER_QUERY + 1):
                try:
                    params = {
                        "q": query,
                        "type": "o",
                        "order_by": "score desc",
                        "stat_Precedential": "on",
                        "page_size": self.MAX_PER_PAGE,
                        "page": page_num,
                    }
                    if court == "bia":
                        params["court"] = "bia"

                    response = await self.client.get(
                        f"{COURTLISTENER_BASE}/search/",
                        params=params,
                    )
                    response.raise_for_status()
                    data = response.json()
                    results = data.get("results", [])

                    if not results:
                        break

                    logger.info(
                        f"CourtListener {court.upper()} '{query[:35]}' page {page_num} "
                        f"→ {len(results)} results"
                    )

                    for result in results:
                        case_id = str(result.get("cluster_id") or result.get("id", ""))
                        if not case_id or case_id in seen_ids:
                            continue
                        seen_ids.add(case_id)

                        page = await self._parse_result(result, source_type)
                        if page:
                            pages.append(page)

                    if not data.get("next"):
                        break

                    await asyncio.sleep(1.5)

                except Exception as e:
                    logger.error(f"Failed to fetch {court} page {page_num} for '{query}': {e}")
                    break

            await asyncio.sleep(1)

        return pages

    async def _fetch_opinion_text(self, result: dict) -> str:
        """Fetch full opinion plain text from CourtListener when available."""
        opinion_id = None
        opinions = result.get("opinions", [])
        if opinions:
            opinion_id = opinions[0].get("id")

        if not opinion_id:
            cluster_id = result.get("cluster_id")
            if cluster_id:
                try:
                    resp = await self.client.get(f"{COURTLISTENER_BASE}/clusters/{cluster_id}/")
                    if resp.status_code == 200:
                        cluster = resp.json()
                        sub_opinions = cluster.get("sub_opinions", [])
                        if sub_opinions:
                            opinion_id = sub_opinions[0]
                except Exception:
                    pass

        if not opinion_id:
            return ""

        try:
            resp = await self.client.get(f"{COURTLISTENER_BASE}/opinions/{opinion_id}/")
            resp.raise_for_status()
            opinion = resp.json()
            plain = opinion.get("plain_text") or ""
            if plain and len(plain) > 500:
                return plain[:50000]
            html = opinion.get("html_with_citations") or opinion.get("html") or ""
            if html:
                return re.sub(r"<[^>]+>", " ", html)[:50000]
        except Exception as e:
            logger.debug(f"Could not fetch opinion {opinion_id}: {e}")

        return ""

    async def _parse_result(self, result: dict, source_type: str) -> Optional[ScrapedPage]:
        try:
            case_name = (
                result.get("caseName") or
                result.get("caseNameFull") or
                "Unknown Case"
            )
            case_id = str(result.get("cluster_id") or result.get("id", ""))
            court = result.get("court", source_type.upper())
            date_filed = result.get("dateFiled") or result.get("date_filed", "")
            citations = result.get("citation", [])
            citation = citations[0] if citations else ""

            snippet = result.get("snippet", "")
            if not snippet:
                opinions = result.get("opinions", [])
                if opinions:
                    snippet = opinions[0].get("snippet", "")
            if snippet:
                snippet = re.sub(r"<[^>]+>", "", snippet).strip()

            syllabus = result.get("syllabus", "")
            if syllabus:
                syllabus = re.sub(r"<[^>]+>", "", syllabus).strip()

            full_text = await self._fetch_opinion_text(result)

            absolute_url = result.get("absolute_url", "")
            url = (
                f"https://www.courtlistener.com{absolute_url}"
                if absolute_url
                else f"https://www.courtlistener.com/opinion/{case_id}/"
            )

            outcome = self._detect_outcome((snippet or "") + " " + (syllabus or "") + " " + (full_text[:2000]))

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
                content_parts.append(f"SYLLABUS:\n{syllabus}\n\n")

            if full_text:
                content_parts.append(f"FULL OPINION:\n{full_text}")
            elif snippet:
                content_parts.append(f"DECISION EXCERPT:\n{snippet}")

            content = "\n".join(content_parts)

            if len(content) < 100:
                return None

            title = f"{case_name} ({citation or case_id})"
            logger.info(f"Parsed {source_type.upper()}: {case_name[:50]} ({len(content)} chars)")

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
