import httpx
import re
from dataclasses import dataclass
from typing import Optional
from app.utils.logger import logger


COURTLISTENER_BASE = "https://www.courtlistener.com/api/rest/v4"

COURT_NAMES = {
    "ca1": "1st Circuit",
    "ca2": "2nd Circuit",
    "ca3": "3rd Circuit",
    "ca4": "4th Circuit",
    "ca5": "5th Circuit",
    "ca6": "6th Circuit",
    "ca7": "7th Circuit",
    "ca8": "8th Circuit",
    "ca9": "9th Circuit",
    "ca10": "10th Circuit",
    "ca11": "11th Circuit",
    "cadc": "D.C. Circuit",
    "scotus": "Supreme Court",
    "bia": "Board of Immigration Appeals",
    "dcd": "District Court, D.C.",
    "nyed": "E.D. New York",
    "cand": "N.D. California",
    "txsd": "S.D. Texas",
}

VISA_TERM_MAP = {
    "h1b": "H-1B specialty occupation nonimmigrant visa petition",
    "h4": "H-4 dependent spouse nonimmigrant visa employment authorization",
    "l1": "L-1 intracompany transferee visa",
    "o1": "O-1 extraordinary ability visa",
    "eb1": "EB-1 priority worker immigrant petition",
    "eb2": "EB-2 advanced degree immigrant petition",
    "asylum": "asylum withholding removal persecution immigration",
    "green_card": "adjustment of status lawful permanent resident I-485",
    "f1": "F-1 student visa OPT employment authorization",
}


@dataclass
class CourtCase:
    case_name: str
    case_id: str
    court: str
    court_name: str
    date_decided: Optional[str]
    citation: Optional[str]
    summary: Optional[str]
    full_text_url: str
    courtlistener_url: str
    relevance_score: float
    visa_types: list[str]
    outcome: Optional[str]


from app.config import settings


class CourtListenerScraper:

    TIMEOUT = settings.COURTLISTENER_TIMEOUT

    VISA_PATTERNS = {
        "h1b": ["h-1b", "h1b", "specialty occupation"],
        "h4": ["h-4", "h4 ead", "h4 dependent", "h-4 visa"],
        "l1": ["l-1", "l1a", "l1b", "intracompany"],
        "o1": ["o-1", "extraordinary ability"],
        "eb1": ["eb-1", "eb1", "priority worker"],
        "eb2": ["eb-2", "eb2", "advanced degree"],
        "asylum": ["asylum", "withholding of removal", "convention against torture"],
        "green_card": ["adjustment of status", "lawful permanent resident", "i-485"],
        "f1": ["f-1", "student visa", "opt", "stem opt"],
    }

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=self.TIMEOUT,
            headers={
                "User-Agent": "ImmigraAssist/1.0 Legal Research Tool",
                "Accept": "application/json",
            }
        )

    async def search(
        self,
        query: str,
        visa_type: Optional[str] = None,
        max_results: int = 5,
    ) -> list[CourtCase]:

        search_terms = self._build_search_query(query, visa_type)

        logger.info(
            f"CourtListener search: '{search_terms}' visa_type={visa_type}"
        )

        params = {
            "q": search_terms,
            "type": "o",
            "order_by": "score desc",
            "stat_Precedential": "on",
            "page_size": max_results,
            "court": "ca1 ca2 ca3 ca4 ca5 ca6 ca7 ca8 ca9 ca10 ca11 cadc bia dcd",
        }

        try:
            response = await self.client.get(
                f"{COURTLISTENER_BASE}/search/",
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            logger.info(f"CourtListener raw results count: {len(results)}")

            cases = []
            for result in results:
                case = self._parse_result(result)
                if case:
                    cases.append(case)

            logger.info(f"CourtListener parsed {len(cases)} cases")
            return cases

        except httpx.TimeoutException:
            logger.error("CourtListener API timeout")
            return []
        except httpx.HTTPStatusError as e:
            logger.error(f"CourtListener API error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"CourtListener search failed: {e}")
            return []

    async def get_case_detail(self, case_id: str) -> Optional[CourtCase]:
        try:
            response = await self.client.get(
                f"{COURTLISTENER_BASE}/opinions/{case_id}/",
            )
            response.raise_for_status()
            data = response.json()
            return self._parse_result(data)
        except Exception as e:
            logger.error(f"Failed to fetch case {case_id}: {e}")
            return None

    def _build_search_query(self, query: str, visa_type: Optional[str]) -> str:
        # use focused visa-specific terms as primary query
        # not the full user question which confuses CourtListener
        if visa_type and visa_type in VISA_TERM_MAP:
            return VISA_TERM_MAP[visa_type]

        # fallback — extract key nouns from query
        words = re.sub(r'[^\w\s]', '', query.lower())
        stop_words = {
            'what', 'are', 'the', 'for', 'how', 'to', 'is',
            'a', 'an', 'i', 'can', 'do', 'requirements', 'explain',
            'tell', 'me', 'about', 'please', 'help', 'need',
        }
        key_words = [w for w in words.split() if w not in stop_words][:6]
        base = " ".join(key_words)

        if "immigra" not in base:
            base += " immigration"

        return base

    def _parse_result(self, result: dict) -> Optional[CourtCase]:
        try:
            case_name = (
                result.get("caseName") or
                result.get("caseNameFull") or
                result.get("case_name", "Unknown Case")
            )

            case_id = str(
                result.get("cluster_id") or
                result.get("id", "")
            )

            court_id = result.get("court_id") or result.get("court", "")
            if isinstance(court_id, dict):
                court_id = court_id.get("id", "")

            court_name = COURT_NAMES.get(
                str(court_id),
                str(result.get("court", "Federal Court"))
            )

            date_decided = (
                result.get("dateFiled") or
                result.get("date_filed") or
                result.get("dateDecided") or
                result.get("date_decided")
            )

            citations = result.get("citation", [])
            if isinstance(citations, list) and citations:
                citation = citations[0]
            elif isinstance(citations, str):
                citation = citations
            else:
                citation = (
                    result.get("neutralCite") or
                    result.get("lexisCite") or
                    result.get("docketNumber", "")
                )

            summary = result.get("snippet", "")
            if not summary:
                opinions = result.get("opinions", [])
                if opinions and isinstance(opinions, list):
                    summary = opinions[0].get("snippet", "")

            if summary:
                summary = re.sub(r"<[^>]+>", "", summary)
                summary = summary.strip()
                summary = summary[:300] + "..." if len(summary) > 300 else summary

            absolute_url = result.get("absolute_url", "")
            if absolute_url:
                courtlistener_url = f"https://www.courtlistener.com{absolute_url}"
            else:
                courtlistener_url = f"https://www.courtlistener.com/opinion/{case_id}/"

            meta = result.get("meta", {})
            score_data = meta.get("score", {})
            if isinstance(score_data, dict):
                score = float(score_data.get("bm25", 0.5))
            else:
                score = float(score_data) if score_data else 0.5

            text_to_check = f"{case_name} {summary or ''}".lower()
            visa_types = []
            for visa, patterns in self.VISA_PATTERNS.items():
                if any(p in text_to_check for p in patterns):
                    visa_types.append(visa)

            outcome = self._detect_outcome(result, summary or "")

            return CourtCase(
                case_name=case_name,
                case_id=case_id,
                court=str(court_id),
                court_name=court_name,
                date_decided=date_decided,
                citation=citation if citation else None,
                summary=summary if summary else None,
                full_text_url=courtlistener_url,
                courtlistener_url=courtlistener_url,
                relevance_score=score,
                visa_types=visa_types,
                outcome=outcome,
            )

        except Exception as e:
            logger.error(f"Failed to parse CourtListener result: {e}")
            return None

    def _detect_outcome(self, result: dict, text: str) -> Optional[str]:
        text_lower = text.lower()
        if any(w in text_lower for w in ["granted", "approved", "reversed in favor"]):
            return "granted"
        if any(w in text_lower for w in ["denied", "dismissed", "affirmed denial"]):
            return "denied"
        if any(w in text_lower for w in ["remanded", "vacated", "sent back"]):
            return "remanded"
        if any(w in text_lower for w in ["affirmed", "upheld"]):
            return "affirmed"
        return None

    async def close(self):
        await self.client.aclose()