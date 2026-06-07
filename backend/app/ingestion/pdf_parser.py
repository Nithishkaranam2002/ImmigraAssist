import fitz  # pymupdf
import pdfplumber
import re
from dataclasses import dataclass
from typing import Optional
from app.utils.logger import logger


@dataclass
class ParsedPage:
    page_number: int
    text: str
    headings: list[str]


@dataclass
class ParsedDocument:
    raw_text: str
    pages: list[ParsedPage]
    total_pages: int
    doc_title: str
    doc_section: Optional[str] = None
    source_url: Optional[str] = None


class PDFParser:

    SECTION_PATTERN = re.compile(
        r"(Section\s+\d+[\.\d]*[\s\S]{0,100}?)(?=Section\s+\d+|$)",
        re.IGNORECASE
    )
    CLAUSE_PATTERN = re.compile(
        r"(Clause\s+\d+[\.\d]*|§\s*\d+[\.\d]*)",
        re.IGNORECASE
    )

    def parse(self, file_path: str) -> ParsedDocument:
        """
        Main entry point.
        Detects file type and routes to correct parser.
        """
        logger.info(f"Parsing file: {file_path}")

        if file_path.endswith(".txt"):
            return self._parse_text_file(file_path)
        else:
            return self._parse_pdf_file(file_path)

    def _parse_text_file(self, file_path: str) -> ParsedDocument:
        """Parse a plain text file (scraped web content)."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()

            doc_title = file_path.split("/")[-1].replace(".txt", "")
            doc_section = None
            source_url = None
            body = text

            lines = text.split("\n")
            header_end = 0
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith("TITLE:"):
                    doc_title = stripped.replace("TITLE:", "").strip()
                elif stripped.startswith("SECTION:"):
                    doc_section = stripped.replace("SECTION:", "").strip()
                elif stripped.startswith("URL:"):
                    source_url = stripped.replace("URL:", "").strip()
                elif stripped.startswith("=" * 20):
                    header_end = i + 1
                    break

            if header_end:
                body = "\n".join(lines[header_end:])

            body = self._clean_text(body)

            pages = [ParsedPage(
                page_number=1,
                text=body,
                headings=self._extract_headings(body),
            )]

            logger.info(f"Parsed text file: '{doc_title}' ({len(body)} chars)")

            return ParsedDocument(
                raw_text=body,
                pages=pages,
                total_pages=1,
                doc_title=doc_title,
                doc_section=doc_section,
                source_url=source_url,
            )

        except Exception as e:
            logger.error(f"Failed to parse text file {file_path}: {e}")
            raise

    def _parse_pdf_file(self, file_path: str) -> ParsedDocument:
        """Parse a PDF file."""
        pages = []
        full_text_parts = []

        try:
            fitz_doc = fitz.open(file_path)
            doc_title = fitz_doc.metadata.get("title", "") or file_path.split("/")[-1]
            total_pages = fitz_doc.page_count
            fitz_doc.close()

            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text(
                        x_tolerance=2,
                        y_tolerance=2,
                    )

                    if not text or len(text.strip()) < 20:
                        continue

                    text = self._clean_text(text)
                    headings = self._extract_headings(text)
                    full_text_parts.append(text)

                    pages.append(ParsedPage(
                        page_number=page_num,
                        text=text,
                        headings=headings,
                    ))

            full_text = "\n\n".join(full_text_parts)
            logger.info(f"Parsed {len(pages)} pages from '{doc_title}'")

            return ParsedDocument(
                raw_text=full_text,
                pages=pages,
                total_pages=total_pages,
                doc_title=doc_title,
            )

        except Exception as e:
            logger.error(f"Failed to parse PDF {file_path}: {e}")
            raise

    def _clean_text(self, text: str) -> str:
        text = re.sub(r" {2,}", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"^\d+\s*$", "", text, flags=re.MULTILINE)
        return text.strip()

    def _extract_headings(self, text: str) -> list[str]:
        headings = []
        for match in self.CLAUSE_PATTERN.finditer(text):
            headings.append(match.group().strip())
        return headings