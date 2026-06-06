import re
from dataclasses import dataclass, field
from typing import Optional
from app.llm.gpt_client import GPTResponse
from app.utils.logger import logger


@dataclass
class ParsedResponse:
    answer: str
    cited_laws: list[str]
    cited_cases: list[str]
    important_notes: list[str]
    next_steps: list[str]
    risks: list[str]
    related_forms: list[str]
    raw_content: str
    is_well_formed: bool


class ResponseParser:
    """
    Parses the structured GPT response into clean sections.

    GPT is instructed to return:
    **ANSWER:** ...
    **CITED LAWS:** ...
    **CITED CASES:** ...
    **IMPORTANT NOTES:** ...

    This parser extracts each section.
    Falls back gracefully if GPT doesn't follow the format.
    """

    # section header patterns
    ANSWER_PATTERN = re.compile(
        r"\*\*ANSWER:\*\*\s*(.*?)(?=\*\*CITED LAWS:\*\*|\*\*CITED CASES:\*\*|\*\*IMPORTANT NOTES:\*\*|$)",
        re.DOTALL | re.IGNORECASE,
    )
    CITED_LAWS_PATTERN = re.compile(
        r"\*\*CITED LAWS:\*\*\s*(.*?)(?=\*\*CITED CASES:\*\*|\*\*IMPORTANT NOTES:\*\*|\*\*ANSWER:\*\*|$)",
        re.DOTALL | re.IGNORECASE,
    )
    CITED_CASES_PATTERN = re.compile(
        r"\*\*CITED CASES:\*\*\s*(.*?)(?=\*\*CITED LAWS:\*\*|\*\*IMPORTANT NOTES:\*\*|\*\*ANSWER:\*\*|$)",
        re.DOTALL | re.IGNORECASE,
    )
    NOTES_PATTERN = re.compile(
        r"\*\*IMPORTANT NOTES:\*\*\s*(.*?)(?=\*\*NEXT STEPS:\*\*|\*\*RISKS|\*\*RELATED FORMS:\*\*|\*\*ANSWER:\*\*|$)",
        re.DOTALL | re.IGNORECASE,
    )
    NEXT_STEPS_PATTERN = re.compile(
        r"\*\*NEXT STEPS:\*\*\s*(.*?)(?=\*\*RISKS|\*\*RELATED FORMS:\*\*|$)",
        re.DOTALL | re.IGNORECASE,
    )
    RISKS_PATTERN = re.compile(
        r"\*\*RISKS(?:\s*&\s*CONSIDERATIONS)?:\*\*\s*(.*?)(?=\*\*RELATED FORMS:\*\*|$)",
        re.DOTALL | re.IGNORECASE,
    )
    FORMS_PATTERN = re.compile(
        r"\*\*RELATED FORMS:\*\*\s*(.*?)$",
        re.DOTALL | re.IGNORECASE,
    )

    def parse(self, gpt_response: GPTResponse) -> ParsedResponse:
        """
        Main entry point.
        Parses GPT response content into structured sections.
        """
        content = gpt_response.content

        if not content or not content.strip():
            logger.warning("GPT returned empty content")
            return self._empty_response(content)

        # extract each section
        answer = self._extract_section(self.ANSWER_PATTERN, content)
        cited_laws_raw = self._extract_section(self.CITED_LAWS_PATTERN, content)
        cited_cases_raw = self._extract_section(self.CITED_CASES_PATTERN, content)
        notes_raw = self._extract_section(self.NOTES_PATTERN, content)
        next_steps_raw = self._extract_section(self.NEXT_STEPS_PATTERN, content)
        risks_raw = self._extract_section(self.RISKS_PATTERN, content)
        forms_raw = self._extract_section(self.FORMS_PATTERN, content)

        is_well_formed = bool(answer)

        if not is_well_formed:
            logger.warning(
                "GPT response not well-formed — "
                "missing expected sections, using full content as answer"
            )
            # graceful fallback — use entire response as answer
            return ParsedResponse(
                answer=content.strip(),
                cited_laws=[],
                cited_cases=[],
                important_notes=[],
                next_steps=[],
                risks=[],
                related_forms=[],
                raw_content=content,
                is_well_formed=False,
            )

        cited_laws = self._parse_bullet_list(cited_laws_raw or "")
        cited_cases = self._parse_bullet_list(cited_cases_raw or "")
        important_notes = self._parse_bullet_list(notes_raw or "")
        next_steps = self._parse_bullet_list(next_steps_raw or "")
        risks = self._parse_bullet_list(risks_raw or "")
        related_forms = self._parse_bullet_list(forms_raw or "")

        logger.info(
            f"Response parsed — "
            f"{len(cited_laws)} law refs, "
            f"{len(cited_cases)} case refs, "
            f"{len(important_notes)} notes"
        )

        return ParsedResponse(
            answer=answer.strip() if answer else "",
            cited_laws=cited_laws,
            cited_cases=cited_cases,
            important_notes=important_notes,
            next_steps=next_steps,
            risks=risks,
            related_forms=related_forms,
            raw_content=content,
            is_well_formed=True,
        )

    def _extract_section(
        self,
        pattern: re.Pattern,
        content: str,
    ) -> Optional[str]:
        """Extract a section from content using regex pattern."""
        match = pattern.search(content)
        if match:
            return match.group(1).strip()
        return None

    def _parse_bullet_list(self, text: str) -> list[str]:
        """
        Parse a bullet list from text.
        Handles - bullets, * bullets, numbered lists, and plain lines.
        """
        if not text or not text.strip():
            return []

        lines = text.strip().split("\n")
        items = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # strip bullet markers
            line = re.sub(r"^[-*•]\s+", "", line)
            line = re.sub(r"^\d+\.\s+", "", line)

            if line:
                items.append(line)

        return items

    def _empty_response(self, content: str) -> ParsedResponse:
        return ParsedResponse(
            answer="I was unable to generate a response. Please try again.",
            cited_laws=[],
            cited_cases=[],
            important_notes=["Response generation failed — please retry"],
            next_steps=[],
            risks=[],
            related_forms=[],
            raw_content=content,
            is_well_formed=False,
        )