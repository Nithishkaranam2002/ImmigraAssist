import re
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.retrieval.hybrid_retriever import RetrievedChunk
from app.retrieval.section_resolver import SectionResolver
from app.db.models.document import Document
from app.utils.logger import logger


MAX_CONTEXT_TOKENS = 9000
AVG_CHARS_PER_TOKEN = 4

VOLUME_TOPICS = {
    "1": "General Policies",
    "2": "Nonimmigrant Visas",
    "3": "Humanitarian Protection",
    "6": "Immigrant Visas",
    "7": "Adjustment of Status",
    "8": "Admissibility",
    "9": "Waivers",
    "10": "Employment Authorization",
    "11": "Travel Documents",
    "12": "Citizenship & Naturalization",
}


def _filename_to_label(filename: str, visa_type: str = "") -> str:
    if not filename:
        if visa_type:
            return f"USCIS {visa_type.upper()} Policy Manual"
        return "USCIS Policy Manual"

    name = filename.lower()
    name = name.replace("uscis_policy_www_uscis_gov_policy_manual_", "")
    name = name.replace(".txt", "")

    parts = name.split("_")
    vol = ""
    part = ""
    chapter = ""

    for i, p in enumerate(parts):
        if p == "volume" and i + 1 < len(parts):
            vol = parts[i + 1]
        if p == "part" and i + 1 < len(parts):
            part = parts[i + 1].upper()
        if p == "chapter" and i + 1 < len(parts):
            chapter = parts[i + 1]

    topic = VOLUME_TOPICS.get(vol, "")
    label_parts = ["USCIS Policy Manual"]

    if vol:
        vol_str = f"Vol. {vol}"
        if topic:
            vol_str += f" ({topic})"
        label_parts.append(vol_str)

    if part:
        label_parts.append(f"Part {part}")

    if chapter:
        label_parts.append(f"Ch. {chapter}")

    return " — ".join(label_parts)


def _filename_to_case_info(filename: str) -> dict:
    if not filename:
        return {"label": "Immigration Case Precedent", "url": None}

    name = filename.lower()

    source = "BIA"
    if name.startswith("aao_"):
        source = "AAO"

    name = name.replace("bia_", "").replace("aao_", "")
    name = name.replace("uscis_news_", "")
    name = name.replace("www_courtlistener_com_opinion_", "")
    name = name.replace(".txt", "")

    # split into parts — find numeric opinion ID
    parts = name.split("_")
    opinion_id = None
    case_parts = []

    for p in parts:
        if p.isdigit() and not opinion_id:
            opinion_id = p
        elif opinion_id:
            case_parts.append(p)

    # build CourtListener URL
    url = None
    if opinion_id:
        slug = "-".join(case_parts).strip("-") if case_parts else "opinion"
        url = f"https://www.courtlistener.com/opinion/{opinion_id}/{slug}/"

    # build readable label
    case_name = " ".join(
        w.capitalize() for w in case_parts if w and w != ""
    ).strip()

    if not case_name:
        case_name = f"Decision {opinion_id or ''}"

    label = f"Matter of {case_name} ({source})" if case_name else f"{source} Decision"

    return {"label": label[:80], "url": url}


@dataclass
class BuiltContext:
    context_text: str
    law_references: list[dict]
    case_references: list[dict]
    court_case_references: list[dict]
    total_tokens_estimate: int


class ContextBuilder:

    def __init__(self):
        self.resolver = SectionResolver()

    async def build(
        self,
        db: AsyncSession,
        law_chunks: list[RetrievedChunk],
        case_chunks: list[RetrievedChunk],
        court_cases: list = [],
    ) -> BuiltContext:

        logger.info(
            f"Building context from {len(law_chunks)} law chunks, "
            f"{len(case_chunks)} case chunks, "
            f"{len(court_cases)} court cases"
        )

        # Sequential — AsyncSession does not allow concurrent operations on one session
        case_chunks = await self.resolver.resolve(db, case_chunks)
        doc_filenames = await self._fetch_doc_filenames_by_doc_id(db, law_chunks)
        case_filenames = await self._fetch_doc_filenames_by_doc_id(db, case_chunks)

        law_section = self._format_law_chunks(law_chunks, doc_filenames)
        case_section = self._format_case_chunks(case_chunks, case_filenames)
        court_section = self._format_court_cases(court_cases)

        full_context = ""

        if law_section["text"]:
            full_context += "## RELEVANT LAWS AND POLICIES\n\n"
            full_context += law_section["text"]
            full_context += "\n\n"

        if case_section["text"]:
            full_context += "## RELEVANT CASE PRECEDENTS\n\n"
            full_context += case_section["text"]
            full_context += "\n\n"

        if court_section["text"]:
            full_context += "## RELEVANT COURT DECISIONS\n\n"
            full_context += court_section["text"]
            full_context += "\n\n"

        full_context = self._trim_to_budget(full_context)
        total_tokens = len(full_context) // AVG_CHARS_PER_TOKEN

        logger.info(f"Context built — ~{total_tokens} tokens")

        return BuiltContext(
            context_text=full_context,
            law_references=law_section["references"],
            case_references=case_section["references"],
            court_case_references=court_section["references"],
            total_tokens_estimate=total_tokens,
        )

    async def _fetch_doc_filenames_by_doc_id(
        self,
        db: AsyncSession,
        chunks: list[RetrievedChunk],
    ) -> dict[str, str]:
        if not chunks:
            return {}
        try:
            doc_ids = list(set(c.document_id for c in chunks if c.document_id))
            if not doc_ids:
                return {}
            result = await db.execute(
                select(Document.id, Document.filename)
                .where(Document.id.in_(doc_ids))
            )
            rows = result.all()
            return {str(row.id): row.filename for row in rows}
        except Exception as e:
            logger.error(f"Failed to fetch doc filenames: {e}")
            return {}

    def _format_law_chunks(
        self,
        chunks: list[RetrievedChunk],
        doc_filenames: dict[str, str],
    ) -> dict:
        parts = []
        references = []

        for i, chunk in enumerate(chunks, start=1):
            filename = doc_filenames.get(chunk.document_id, "")
            citation_label = _filename_to_label(filename, chunk.visa_type or "")

            label_parts = [citation_label]
            if chunk.section and len(chunk.section) < 100:
                label_parts.append(chunk.section)
            if chunk.clause and len(chunk.clause) < 100:
                label_parts.append(chunk.clause)

            label = " | ".join(label_parts)
            parts.append(f"[LAW {i}] {label}\n{chunk.text.strip()}")

            references.append({
                "index": i,
                "label": citation_label,
                "section": chunk.section,
                "clause": chunk.clause,
                "version": chunk.doc_version,
                "visa_type": chunk.visa_type,
                "filename": filename,
            })

        return {"text": "\n\n".join(parts), "references": references}

    def _format_case_chunks(
        self,
        chunks: list[RetrievedChunk],
        case_filenames: dict[str, str] = {},
    ) -> dict:
        parts = []
        references = []

        for i, chunk in enumerate(chunks, start=1):
            filename = case_filenames.get(chunk.document_id, "")
            case_info = _filename_to_case_info(filename)

            parts.append(
                f"[CASE {i}] {case_info['label']}\n{chunk.text.strip()}"
            )
            references.append({
                "index": i,
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "label": case_info["label"],
                "url": case_info["url"],
                "score": chunk.score,
                "visa_type": chunk.visa_type,
                "source": chunk.source,
            })

        return {"text": "\n\n".join(parts), "references": references}

    def _format_court_cases(self, court_cases: list) -> dict:
        if not court_cases:
            return {"text": "", "references": []}

        parts = []
        references = []

        for i, case in enumerate(court_cases, start=1):
            case_text = f"[COURT {i}] {case.case_name}"
            if case.citation:
                case_text += f" ({case.citation})"
            if case.court_name:
                case_text += f"\nCourt: {case.court_name}"
            if case.date_decided:
                case_text += f" | Date: {case.date_decided}"
            if case.outcome:
                case_text += f" | Outcome: {case.outcome}"
            if case.summary:
                case_text += f"\nSummary: {case.summary}"
            case_text += f"\nSource: {case.courtlistener_url}"

            parts.append(case_text)
            references.append({
                "index": i,
                "case_name": case.case_name,
                "citation": case.citation,
                "court": case.court_name,
                "date": case.date_decided,
                "url": case.courtlistener_url,
                "outcome": case.outcome,
            })

        return {"text": "\n\n".join(parts), "references": references}

    def _trim_to_budget(self, text: str) -> str:
        max_chars = MAX_CONTEXT_TOKENS * AVG_CHARS_PER_TOKEN

        if len(text) <= max_chars:
            return text

        logger.warning(
            f"Context too long ({len(text)} chars), "
            f"trimming to {max_chars} chars"
        )

        trimmed = text[:max_chars]
        last_para = trimmed.rfind("\n\n")
        if last_para > max_chars * 0.8:
            trimmed = trimmed[:last_para]

        trimmed += "\n\n[Context trimmed due to length limit]"
        return trimmed