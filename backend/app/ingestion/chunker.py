import re
from dataclasses import dataclass, field
from typing import Optional
from app.ingestion.pdf_parser import ParsedDocument
from app.utils.logger import logger


@dataclass
class Chunk:
    text: str
    chunk_index: int
    section: Optional[str] = None
    clause: Optional[str] = None
    page_number: Optional[int] = None
    chunk_type: str = "law"           # "law" or "case"
    block_type: Optional[str] = None  # for cases: "facts", "ruling", "opinion" etc


class LawChunker:
    """
    Chunks law/policy documents by clause boundary.
    Each clause becomes one chunk.
    Falls back to section-level chunking if no clauses found.
    """

    # matches "Clause 1.1", "Clause 1.2.3", "§ 1.1" etc
    CLAUSE_SPLIT_PATTERN = re.compile(
        r"(?=Clause\s+\d+[\.\d]*|§\s*\d+[\.\d]*)",
        re.IGNORECASE
    )

    # matches "Section 1", "Section 2.1" etc
    SECTION_SPLIT_PATTERN = re.compile(
        r"(?=Section\s+\d+[\.\d]*)",
        re.IGNORECASE
    )

    # current heading tracker
    CLAUSE_HEADER = re.compile(
        r"^(Clause\s+\d+[\.\d]*|§\s*\d+[\.\d]*)(.*?)$",
        re.IGNORECASE | re.MULTILINE
    )
    SECTION_HEADER = re.compile(
        r"^(Section\s+\d+[\.\d]*)(.*?)$",
        re.IGNORECASE | re.MULTILINE
    )

    MAX_CHUNK_TOKENS = 512   # max tokens per chunk

    def chunk(self, doc: ParsedDocument) -> list[Chunk]:
        logger.info(f"Law chunking: '{doc.doc_title}'")
        chunks = []
        current_section = None
        chunk_index = 0

        # try splitting by clause first
        splits = self.CLAUSE_SPLIT_PATTERN.split(doc.raw_text)

        if len(splits) <= 2:
            # no clauses found — fall back to section splitting
            logger.warning("No clauses found, falling back to section splitting")
            splits = self.SECTION_SPLIT_PATTERN.split(doc.raw_text)

        for split in splits:
            split = split.strip()
            if not split or len(split) < 50:
                continue

            # detect section from content
            section_match = self.SECTION_HEADER.search(split)
            if section_match:
                current_section = section_match.group(1).strip()

            # detect clause label
            clause_match = self.CLAUSE_HEADER.search(split)
            clause = clause_match.group(1).strip() if clause_match else None

            # if chunk is too long, split it further by paragraph
            sub_chunks = self._split_if_too_long(split)

            for sub in sub_chunks:
                chunks.append(Chunk(
                    text=sub,
                    chunk_index=chunk_index,
                    section=current_section,
                    clause=clause,
                    chunk_type="law",
                ))
                chunk_index += 1

        logger.info(f"Law chunker produced {len(chunks)} chunks")
        return chunks

    def _split_if_too_long(self, text: str) -> list[str]:
        """Split oversized chunks by paragraph."""
        # rough token estimate: 1 token ≈ 4 chars
        if len(text) / 4 <= self.MAX_CHUNK_TOKENS:
            return [text]

        paragraphs = text.split("\n\n")
        result = []
        current = ""

        for para in paragraphs:
            if len((current + para)) / 4 > self.MAX_CHUNK_TOKENS and current:
                result.append(current.strip())
                current = para
            else:
                current += "\n\n" + para

        if current.strip():
            result.append(current.strip())

        return result


class CaseChunker:
    """
    Chunks case files by legal argument block:
    FACTS → OPINION → RULING → CITED STATUTES
    Falls back to paragraph chunking if no blocks found.
    """

    BLOCK_PATTERNS = {
        "facts": re.compile(
            r"(?=FACTS|BACKGROUND|STATEMENT OF FACTS)",
            re.IGNORECASE
        ),
        "opinion": re.compile(
            r"(?=OPINION|ANALYSIS|DISCUSSION)",
            re.IGNORECASE
        ),
        "ruling": re.compile(
            r"(?=RULING|DECISION|HELD|HOLDING|ORDER)",
            re.IGNORECASE
        ),
        "statutes": re.compile(
            r"(?=CITED|REFERENCES|STATUTES CITED|AUTHORITIES)",
            re.IGNORECASE
        ),
    }

    MAX_CHUNK_TOKENS = 768  # cases can be slightly larger chunks

    def chunk(self, doc: ParsedDocument) -> list[Chunk]:
        logger.info(f"Case chunking: '{doc.doc_title}'")
        chunks = []
        chunk_index = 0
        text = doc.raw_text

        # find all block start positions
        block_positions = []
        for block_type, pattern in self.BLOCK_PATTERNS.items():
            for match in pattern.finditer(text):
                block_positions.append((match.start(), block_type))

        # sort by position
        block_positions.sort(key=lambda x: x[0])

        if not block_positions:
            # no blocks found — fall back to paragraph chunking
            logger.warning("No case blocks found, falling back to paragraph chunking")
            return self._paragraph_fallback(text)

        # extract each block as a chunk
        for i, (start_pos, block_type) in enumerate(block_positions):
            end_pos = block_positions[i + 1][0] if i + 1 < len(block_positions) else len(text)
            block_text = text[start_pos:end_pos].strip()

            if len(block_text) < 50:
                continue

            sub_chunks = self._split_if_too_long(block_text)
            for sub in sub_chunks:
                chunks.append(Chunk(
                    text=sub,
                    chunk_index=chunk_index,
                    chunk_type="case",
                    block_type=block_type,
                ))
                chunk_index += 1

        logger.info(f"Case chunker produced {len(chunks)} chunks")
        return chunks

    def _paragraph_fallback(self, text: str) -> list[Chunk]:
        """Split by paragraph when no blocks are detected."""
        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 100]
        return [
            Chunk(
                text=para,
                chunk_index=i,
                chunk_type="case",
                block_type="paragraph",
            )
            for i, para in enumerate(paragraphs)
        ]

    def _split_if_too_long(self, text: str) -> list[str]:
        if len(text) / 4 <= self.MAX_CHUNK_TOKENS:
            return [text]

        paragraphs = text.split("\n\n")
        result = []
        current = ""

        for para in paragraphs:
            if len((current + para)) / 4 > self.MAX_CHUNK_TOKENS and current:
                result.append(current.strip())
                current = para
            else:
                current += "\n\n" + para

        if current.strip():
            result.append(current.strip())

        return result


def get_chunker(doc_type: str) -> LawChunker | CaseChunker:
    """Factory — returns the right chunker based on doc type."""
    if doc_type == "law":
        return LawChunker()
    return CaseChunker()