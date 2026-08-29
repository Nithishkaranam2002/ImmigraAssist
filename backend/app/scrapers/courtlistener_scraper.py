import httpx
import re
from dataclasses import dataclass
from typing import Optional
from app.config import settings
from app.retrieval.case_relevance import score_case_text
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

# Short anchors — combined with topic terms from the user's actual question
VISA_ANCHORS = {
    "h1b": ["H-1B", "specialty occupation"],
    "h4": ["H-4", "dependent spouse"],
    "h4_ead": ["H-4", "EAD", "employment authorization", "I-765"],
    "l1": ["L-1", "intracompany transferee"],
    "o1": ["O-1", "extraordinary ability"],
    "eb1": ["EB-1", "priority worker"],
    "eb2": ["EB-2"],
    "asylum": ["asylum", "withholding of removal", "persecution"],
    "green_card": ["adjustment of status", "I-485", "lawful permanent resident"],
    "f1": ["F-1", "student", "OPT", "STEM OPT", "practical training"],
}

TOPIC_PHRASES: list[tuple[re.Pattern, list[str]]] = [
    (re.compile(r"\bforms?\b|i-765|i-539|i-129|i-140|i-485", re.I), ["forms", "filing"]),
    (re.compile(r"\bac21\b|portability", re.I), ["AC21", "portability", "H-1B transfer"]),
    (re.compile(r"\bcap\b|lottery|registration", re.I), ["H-1B cap", "lottery", "registration"]),
    (re.compile(r"\bpremium\s+processing", re.I), ["premium processing", "expedited"]),
    (re.compile(r"\beligib|qualif|require", re.I), ["eligibility", "requirements"]),
    (re.compile(r"\bdeni", re.I), ["denial", "denied", "appeal"]),
    (re.compile(r"\bnaturalization|citizenship|n-400", re.I), ["naturalization", "citizenship"]),
    (re.compile(r"\bdeport|removal|cancellation", re.I), ["deportation", "removal", "cancellation"]),
    (re.compile(r"\bcompare|versus|vs\.?\b", re.I), ["comparison", "visa category"]),
    (re.compile(r"\b180[- ]day|extension", re.I), ["180-day extension", "status extension"]),
    (re.compile(r"\bconsular|visa\s+stamp|abroad", re.I), ["consular processing", "visa stamp"]),
    (
        re.compile(r"\b(opt\b|stem\s+opt|cpt\b|practical\s+training|sevis|i-983)", re.I),
        ["STEM OPT", "OPT extension", "F-1 student", "Form I-983"],
    ),
    (
        re.compile(r"\bhow\s+long|duration|months?\b", re.I),
        ["24 month", "STEM OPT duration", "OPT period"],
    ),
]

STOP_WORDS = frozenset({
    "what", "are", "the", "for", "how", "to", "is", "a", "an", "i", "can", "do",
    "requirements", "explain", "tell", "me", "about", "please", "help", "need",
    "that", "this", "with", "from", "when", "where", "which", "who", "why",
    "should", "would", "could", "does", "did", "have", "has", "been", "being",
    "their", "there", "these", "those", "into", "through", "during", "before",
    "after", "above", "below", "between", "under", "again", "further", "then",
    "once", "here", "all", "each", "few", "more", "most", "other", "some", "such",
    "only", "own", "same", "than", "too", "very", "just", "also", "any", "both",
})

# Visa families — penalize cases that clearly belong to a different immigration topic
TOPIC_MISMATCH = {
    "h1b": [r"\basylum\b", r"\bnaturalization\b", r"\bn-400\b", r"\bf-1\b.*\bstudent\b"],
    "h4": [r"\basylum\b", r"\bnaturalization\b", r"\bh-1b\s+cap\b"],
    "h4_ead": [r"\basylum\b", r"\bnaturalization\b", r"\bh-1b\s+cap\b"],
    "l1": [r"\basylum\b", r"\bnaturalization\b", r"\bf-1\b"],
    "o1": [r"\basylum\b", r"\bnaturalization\b"],
    "eb1": [r"\basylum\b", r"\bf-1\b.*\bstudent\b"],
    "eb2": [r"\basylum\b", r"\bf-1\b.*\bstudent\b"],
    "f1": [
        r"\basylum\b", r"\bh-1b\s+cap\b", r"\bnaturalization\b",
        r"\bfair\s+admissions\b", r"\bstudents?\s+for\s+fair\b",
        r"\bh-1b\b(?!.*\b(cap[- ]?gap|student)\b)",
    ],
    "asylum": [r"\bh-1b\s+cap\b", r"\bpremium\s+processing\b", r"\bl-1\b"],
    "green_card": [r"\bf-1\b.*\bstudent\b", r"\bh-1b\s+cap\b"],
}

IMMIGRATION_VISA_TYPES = frozenset(VISA_ANCHORS.keys())


def _eb2_subtopic_terms(query: str) -> list[str]:
    """PERM is only one EB-2 path — NIW skips labor certification entirely."""
    terms: list[str] = []
    if re.search(r"\bniw\b|national\s+interest", query, re.I):
        terms.extend(["national interest waiver", "Dhanasar"])
    if re.search(r"\bperm\b|labor\s+certification", query, re.I):
        terms.extend(["PERM", "labor certification"])
    if re.search(r"exceptional\s+ability", query, re.I):
        terms.append("exceptional ability")
    if not terms:
        terms.append("advanced degree")
    return terms


MIN_RELEVANCE_SCORE = 0.22
FETCH_MULTIPLIER = 6


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


class CourtListenerScraper:

    TIMEOUT = settings.COURTLISTENER_TIMEOUT

    VISA_PATTERNS = {
        "h1b": ["h-1b", "h1b", "specialty occupation"],
        "h4": ["h-4", "h4", "dependent spouse", "h4 dependent"],
        "h4_ead": ["h-4 ead", "h4 ead", "employment authorization", "i-765", "(c)(26)"],
        "l1": ["l-1", "l1a", "l1b", "intracompany"],
        "o1": ["o-1", "extraordinary ability"],
        "eb1": ["eb-1", "eb1", "priority worker"],
        "eb2": ["eb-2", "eb2", "advanced degree", "perm"],
        "asylum": ["asylum", "withholding of removal", "convention against torture"],
        "green_card": ["adjustment of status", "lawful permanent resident", "i-485"],
        "f1": ["f-1", "student visa", "opt", "stem opt"],
    }

    def __init__(self):
        headers = {
            "User-Agent": "ImmigraAssist/1.0 Legal Research Tool",
            "Accept": "application/json",
        }
        token = getattr(settings, "COURTLISTENER_API_TOKEN", "") or ""
        if token:
            headers["Authorization"] = f"Token {token}"
        self.client = httpx.AsyncClient(timeout=self.TIMEOUT, headers=headers)

    async def search(
        self,
        query: str,
        visa_type: Optional[str] = None,
        max_results: int = 5,
    ) -> list[CourtCase]:
        if visa_type == "h4" and re.search(
            r"\bead\b|employment\s+auth|i-765|\(c\)\(26\)", query, re.I
        ):
            visa_type = "h4_ead"

        search_terms = self._build_search_query(query, visa_type)
        fetch_n = max(max_results * FETCH_MULTIPLIER, 12)

        logger.info(
            f"CourtListener search: q='{search_terms}' visa={visa_type} fetch={fetch_n}"
        )

        raw_cases: list[CourtCase] = []

        if visa_type in IMMIGRATION_VISA_TYPES:
            bia_cases = await self._fetch(search_terms, fetch_n, court="bia")
            raw_cases.extend(bia_cases)
            if len(raw_cases) < max_results:
                broader = await self._fetch(
                    search_terms,
                    fetch_n,
                    court="ca9 bia ca2 ca4 ca5 ca11",
                )
                seen = {c.case_id for c in raw_cases}
                for c in broader:
                    if c.case_id not in seen:
                        raw_cases.append(c)
                        seen.add(c.case_id)
        else:
            raw_cases = await self._fetch(
                search_terms,
                fetch_n,
                court="ca1 ca2 ca3 ca4 ca5 ca6 ca7 ca8 ca9 ca10 ca11 cadc bia",
            )

        ranked = self._rank_and_filter(raw_cases, query, visa_type, max_results)

        # Targeted second pass for F-1/OPT when initial results are weak or empty
        if visa_type == "f1" and re.search(
            r"\b(opt|stem\s+opt|cpt|practical\s+training)\b", query, re.I
        ):
            if len(ranked) < max_results:
                opt_query = '"STEM OPT" "optional practical training" F-1'
                extra = await self._fetch(opt_query, fetch_n, court="ca9 ca2 ca4 cadc bia")
                seen = {c.case_id for c in ranked}
                for c in extra:
                    if c.case_id not in seen:
                        raw_cases.append(c)
                        seen.add(c.case_id)
                ranked = self._rank_and_filter(raw_cases, query, visa_type, max_results)

        logger.info(
            f"CourtListener kept {len(ranked)}/{len(raw_cases)} cases after relevance filter"
        )
        return ranked

    async def _fetch(
        self,
        search_terms: str,
        page_size: int,
        court: str,
    ) -> list[CourtCase]:
        params = {
            "q": search_terms,
            "type": "o",
            "order_by": "score desc",
            "stat_Precedential": "on",
            "page_size": min(page_size, 20),
            "court": court,
        }
        try:
            response = await self.client.get(
                f"{COURTLISTENER_BASE}/search/",
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            cases = []
            for result in data.get("results", []):
                case = self._parse_result(result)
                if case:
                    cases.append(case)
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
            return self._parse_result(response.json())
        except Exception as e:
            logger.error(f"Failed to fetch case {case_id}: {e}")
            return None

    def _build_search_query(self, query: str, visa_type: Optional[str]) -> str:
        """Combine visa anchors with topic terms extracted from the user's question."""
        if visa_type == "f1" and re.search(
            r"\b(opt|stem\s+opt|cpt|practical\s+training)\b", query, re.I
        ):
            return '"STEM OPT" "optional practical training" F-1 student I-983'

        terms: list[str] = []

        if visa_type and visa_type in VISA_ANCHORS:
            terms.extend(VISA_ANCHORS[visa_type])
        if visa_type == "eb2":
            terms.extend(_eb2_subtopic_terms(query))

        for pattern, phrases in TOPIC_PHRASES:
            if pattern.search(query):
                terms.extend(phrases)

        normalized = re.sub(r"[^\w\s-]", " ", query.lower())
        for word in normalized.split():
            w = word.strip("-")
            if len(w) < 3 or w in STOP_WORDS:
                continue
            if w not in terms and not any(w in t.lower() for t in terms):
                terms.append(w)

        if not terms:
            terms = ["immigration", "visa"]

        # CourtListener works best with concise boolean-style queries
        return " ".join(terms[:10])

    def _tokenize(self, text: str) -> set[str]:
        normalized = re.sub(r"[^\w\s-]", " ", text.lower())
        tokens = set()
        for word in normalized.split():
            w = word.strip("-")
            if len(w) >= 3 and w not in STOP_WORDS:
                tokens.add(w)
        return tokens

    def _rank_and_filter(
        self,
        cases: list[CourtCase],
        query: str,
        visa_type: Optional[str],
        max_results: int,
    ) -> list[CourtCase]:
        if not cases:
            return []

        query_tokens = self._tokenize(query)
        if visa_type and visa_type in VISA_ANCHORS:
            for anchor in VISA_ANCHORS[visa_type]:
                query_tokens.update(self._tokenize(anchor))

        min_score = MIN_RELEVANCE_SCORE
        if visa_type == "f1" and re.search(
            r"\b(opt|stem\s+opt|cpt|practical\s+training)\b", query, re.I
        ):
            min_score = 0.30

        scored: list[tuple[float, CourtCase]] = []
        for case in cases:
            case_text = f"{case.case_name} {case.summary or ''}"
            score = score_case_text(case_text, query, visa_type)
            score = max(score, self._relevance_score(case, query_tokens, visa_type) * 0.85)
            if score >= min_score:
                case.relevance_score = round(score, 3)
                scored.append((score, case))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:max_results]]

    def _relevance_score(
        self,
        case: CourtCase,
        query_tokens: set[str],
        visa_type: Optional[str],
    ) -> float:
        text = f"{case.case_name} {case.summary or ''}".lower()
        case_tokens = self._tokenize(text)

        if not query_tokens:
            return 0.0

        overlap = query_tokens & case_tokens
        score = min(len(overlap) * 0.12, 0.48)

        # Phrase-level match (e.g. "employment authorization")
        query_joined = " ".join(sorted(query_tokens))
        for anchor_list in VISA_ANCHORS.values():
            for phrase in anchor_list:
                if phrase.lower() in text:
                    if any(t in phrase.lower() for t in query_tokens):
                        score += 0.2
                    break

        if visa_type:
            vt = visa_type.replace("_ead", "")
            if visa_type in case.visa_types or vt in case.visa_types:
                score += 0.28
            elif case.visa_types and visa_type not in case.visa_types:
                score -= 0.15

            for pattern in TOPIC_MISMATCH.get(visa_type, []):
                if re.search(pattern, text, re.I):
                    score -= 0.45

        if str(case.court).lower() == "bia":
            score += 0.08

        if case.summary and any(t in case.summary.lower() for t in query_tokens):
            score += 0.1

        # Slight boost from CourtListener BM25 (normalized)
        score += min(case.relevance_score * 0.05, 0.1)

        return max(score, 0.0)

    def _parse_result(self, result: dict) -> Optional[CourtCase]:
        try:
            case_name = (
                result.get("caseName")
                or result.get("caseNameFull")
                or result.get("case_name", "Unknown Case")
            )

            case_id = str(result.get("cluster_id") or result.get("id", ""))

            court_id = result.get("court_id") or result.get("court", "")
            if isinstance(court_id, dict):
                court_id = court_id.get("id", "")

            court_name = COURT_NAMES.get(
                str(court_id),
                str(result.get("court", "Federal Court")),
            )

            date_decided = (
                result.get("dateFiled")
                or result.get("date_filed")
                or result.get("dateDecided")
                or result.get("date_decided")
            )

            citations = result.get("citation", [])
            if isinstance(citations, list) and citations:
                citation = citations[0]
            elif isinstance(citations, str):
                citation = citations
            else:
                citation = (
                    result.get("neutralCite")
                    or result.get("lexisCite")
                    or result.get("docketNumber", "")
                )

            summary = result.get("snippet", "")
            if not summary:
                opinions = result.get("opinions", [])
                if opinions and isinstance(opinions, list):
                    summary = opinions[0].get("snippet", "")

            if summary:
                summary = re.sub(r"<[^>]+>", "", summary).strip()
                summary = summary[:300] + "..." if len(summary) > 300 else summary

            absolute_url = result.get("absolute_url", "")
            if absolute_url:
                courtlistener_url = f"https://www.courtlistener.com{absolute_url}"
            else:
                courtlistener_url = f"https://www.courtlistener.com/opinion/{case_id}/"

            meta = result.get("meta", {})
            score_data = meta.get("score", {})
            if isinstance(score_data, dict):
                bm25 = float(score_data.get("bm25", 0.5))
            else:
                bm25 = float(score_data) if score_data else 0.5

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
                relevance_score=bm25,
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
