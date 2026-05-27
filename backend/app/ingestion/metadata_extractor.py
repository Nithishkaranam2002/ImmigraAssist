import re
from dataclasses import dataclass
from typing import Optional
from app.ingestion.chunker import Chunk
from app.utils.logger import logger


@dataclass
class ChunkMetadata:
    visa_type: Optional[str]
    section: Optional[str]
    clause: Optional[str]
    cited_sections: list[str]     # old section references found in this chunk
    year_references: list[str]    # years mentioned
    form_references: list[str]    # I-140, I-765 etc


class MetadataExtractor:
    """
    Extracts structured metadata from each chunk.
    This metadata goes into PostgreSQL for fast pre-filtering.
    """

    VISA_PATTERNS = {
        "h1b": re.compile(r"\bh[-\s]?1b\b", re.IGNORECASE),
        "h4": re.compile(r"\bh[-\s]?4\b", re.IGNORECASE),
        "h4_ead": re.compile(r"\bh[-\s]?4\s*ead\b", re.IGNORECASE),
        "l1": re.compile(r"\bl[-\s]?1[ab]?\b", re.IGNORECASE),
        "o1": re.compile(r"\bo[-\s]?1\b", re.IGNORECASE),
        "eb1": re.compile(r"\beb[-\s]?1\b", re.IGNORECASE),
        "eb2": re.compile(r"\beb[-\s]?2\b", re.IGNORECASE),
        "asylum": re.compile(r"\basylum\b", re.IGNORECASE),
        "green_card": re.compile(r"\bgreen\s*card\b", re.IGNORECASE),
        "f1": re.compile(r"\bf[-\s]?1\b", re.IGNORECASE),
    }

    # matches old section/clause refs like "Section 1, Clause 1.3" or "§ 245(a)"
    SECTION_REF_PATTERN = re.compile(
        r"(Section\s+\d+[\.\d]*(?:,\s*Clause\s+\d+[\.\d]*)?|§\s*\d+[\.\d]*(?:\([a-z]\))?)",
        re.IGNORECASE
    )

    # matches USCIS form numbers like I-140, I-765, I-485
    FORM_REF_PATTERN = re.compile(r"\bI-\d{3,4}\b", re.IGNORECASE)

    # matches 4-digit years between 1900-2099
    YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")

    def extract(self, chunk: Chunk) -> ChunkMetadata:
        text = chunk.text

        visa_type = self._detect_visa(text)
        cited_sections = self._extract_section_refs(text)
        form_references = self.FORM_REF_PATTERN.findall(text)
        year_references = self.YEAR_PATTERN.findall(text)

        return ChunkMetadata(
            visa_type=visa_type,
            section=chunk.section,
            clause=chunk.clause,
            cited_sections=cited_sections,
            year_references=list(set(year_references)),
            form_references=list(set(form_references)),
        )

    def _detect_visa(self, text: str) -> Optional[str]:
        for visa_type, pattern in self.VISA_PATTERNS.items():
            if pattern.search(text):
                return visa_type
        return None

    def _extract_section_refs(self, text: str) -> list[str]:
        matches = self.SECTION_REF_PATTERN.findall(text)
        return list(set(m.strip() for m in matches))