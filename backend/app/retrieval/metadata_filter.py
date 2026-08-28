import re
from dataclasses import dataclass
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models.chunk import Chunk as ChunkModel
from app.db.models.document import Document, DocumentType
from app.utils.logger import logger


@dataclass
class FilterContext:
    visa_type: Optional[str]          # detected from query
    year_min: Optional[int]           # if query mentions year range
    year_max: Optional[int]
    law_document_ids: list[str]       # filtered law doc IDs
    case_document_ids: list[str]      # filtered case doc IDs


# More-specific codes first: "H-4 EAD" also matches the H-4 pattern.
VISA_PATTERNS = {
    "h1b": re.compile(r"\bh[-\s]?1b\b", re.IGNORECASE),
    "h4_ead": re.compile(r"\bh[-\s]?4\s*ead\b", re.IGNORECASE),
    "h4": re.compile(r"\bh[-\s]?4\b", re.IGNORECASE),
    "l1": re.compile(r"\bl[-\s]?1[ab]?\b", re.IGNORECASE),
    "o1": re.compile(r"\bo[-\s]?1\b", re.IGNORECASE),
    "eb1": re.compile(r"\beb[-\s]?1\b", re.IGNORECASE),
    "eb2": re.compile(r"\beb[-\s]?2\b", re.IGNORECASE),
    "asylum": re.compile(r"\basylum\b", re.IGNORECASE),
    "green_card": re.compile(r"\bgreen\s*card\b", re.IGNORECASE),
    "f1": re.compile(r"\bf[-\s]?1\b", re.IGNORECASE),
}

YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")


class MetadataFilter:
    """
    Pre-filters documents in PostgreSQL before hitting Milvus.
    Detects visa type and year range from the query,
    returns only relevant document IDs for vector search.
    """

    async def build_filter_context(
        self,
        db: AsyncSession,
        query: str,
    ) -> FilterContext:
        """
        Main entry point.
        Detects visa type and year from query,
        then fetches matching document IDs from PostgreSQL.
        """
        visa_type = self._detect_visa_type(query)
        if not visa_type:
            visa_type = self._infer_visa_from_topic(query)
        year_min, year_max = self._detect_year_range(query)

        logger.info(
            f"Filter context — visa: {visa_type}, "
            f"years: {year_min}-{year_max}"
        )

        # Sequential — AsyncSession does not allow concurrent operations on one session
        law_doc_ids = await self._fetch_document_ids(
            db=db,
            doc_type=DocumentType.LAW,
            visa_type=visa_type,
        )
        case_doc_ids = await self._fetch_document_ids(
            db=db,
            doc_type=DocumentType.CASE,
            visa_type=visa_type,
            year_min=year_min,
            year_max=year_max,
        )

        # if no filtered docs found, fall back to all docs
        # so the query never returns empty handed
        if not law_doc_ids:
            logger.warning("No law docs matched filter — using all law docs")
            law_doc_ids = await self._fetch_all_document_ids(db, DocumentType.LAW)

        if not case_doc_ids:
            if visa_type:
                logger.warning(
                    f"No case docs matched visa={visa_type} — skipping unrelated case search"
                )
            else:
                logger.warning("No case docs matched filter — using all case docs")
                case_doc_ids = await self._fetch_all_document_ids(db, DocumentType.CASE)

        return FilterContext(
            visa_type=visa_type,
            year_min=year_min,
            year_max=year_max,
            law_document_ids=law_doc_ids,
            case_document_ids=case_doc_ids,
        )

    async def apply_visa_override(
        self,
        db: AsyncSession,
        filter_context: FilterContext,
        visa_type: str,
    ) -> FilterContext:
        """Re-scope document filters when visa type comes from session history."""
        if filter_context.visa_type or not visa_type:
            return filter_context

        law_doc_ids = await self._fetch_document_ids(
            db=db,
            doc_type=DocumentType.LAW,
            visa_type=visa_type,
        )
        case_doc_ids = await self._fetch_document_ids(
            db=db,
            doc_type=DocumentType.CASE,
            visa_type=visa_type,
            year_min=filter_context.year_min,
            year_max=filter_context.year_max,
        )

        if not law_doc_ids:
            law_doc_ids = filter_context.law_document_ids
        if not case_doc_ids:
            case_doc_ids = filter_context.case_document_ids

        return FilterContext(
            visa_type=visa_type,
            year_min=filter_context.year_min,
            year_max=filter_context.year_max,
            law_document_ids=law_doc_ids,
            case_document_ids=case_doc_ids,
        )

    def _detect_visa_type(self, query: str) -> Optional[str]:
        # H-4 EAD is a superset of the H-4 token; check it first.
        if VISA_PATTERNS["h4_ead"].search(query):
            return "h4_ead"
        for visa_type, pattern in VISA_PATTERNS.items():
            if visa_type == "h4_ead":
                continue
            if pattern.search(query):
                return visa_type
        return None

    def _infer_visa_from_topic(self, query: str) -> Optional[str]:
        """Map topic keywords to visa when explicit code is omitted."""
        q = query.lower()
        if re.search(r"\b(cap|lottery|premium\s+processing|lca)\b", q):
            return "h1b"
        if re.search(r"\b(opt\b|stem\s+opt|curricular\s+practical)", q):
            return "f1"
        if re.search(r"\bperm\b|labor\s+certification", q):
            return "eb2"
        # EAD / work authorization is shared by H-4 (c)(26), F-1 OPT, asylum,
        # TPS, L-2, and AOS (c)(9). Do not force the H-4 EAD corpus.
        # Explicit "H-4 EAD" is handled by _detect_visa_type.
        if re.search(r"\(c\)\s*\(26\)", q):
            return "h4_ead"
        return None

    def _detect_year_range(
        self, query: str
    ) -> tuple[Optional[int], Optional[int]]:
        """
        Extract year range from query.
        "cases after 2018" → (2018, None)
        "cases between 2015 and 2020" → (2015, 2020)
        "recent cases" → (2020, None) — default recent window
        """
        years = [int(y) for y in YEAR_PATTERN.findall(query)]

        if not years:
            if re.search(r"\brecent\b|\blatest\b|\bnew\b", query, re.IGNORECASE):
                return 2020, None
            return None, None

        years.sort()
        if len(years) == 1:
            if re.search(r"\bafter\b|\bsince\b", query, re.IGNORECASE):
                return years[0], None
            if re.search(r"\bbefore\b|\buntil\b", query, re.IGNORECASE):
                return None, years[0]
            return years[0], None

        return years[0], years[-1]

    async def _fetch_document_ids(
        self,
        db: AsyncSession,
        doc_type: DocumentType,
        visa_type: Optional[str],
        year_min: Optional[int] = None,
        year_max: Optional[int] = None,
    ) -> list[str]:
        """Fetch document IDs from PostgreSQL matching the filters."""
        query = select(Document.id).where(Document.doc_type == doc_type)

        if visa_type:
            query = query.where(Document.visa_type == visa_type)

        result = await db.execute(query)
        doc_ids = [str(row[0]) for row in result.fetchall()]
        return doc_ids

    async def _fetch_all_document_ids(
        self,
        db: AsyncSession,
        doc_type: DocumentType,
    ) -> list[str]:
        result = await db.execute(
            select(Document.id).where(Document.doc_type == doc_type)
        )
        return [str(row[0]) for row in result.fetchall()]