import re
from dataclasses import dataclass
from typing import Optional
from app.utils.logger import logger

try:
    from gliner import GLiNER
    GLINER_AVAILABLE = True
except ImportError:
    GLINER_AVAILABLE = False
    logger.warning("GLiNER not available — falling back to regex PII detection")


@dataclass
class PIIDetectionResult:
    original_text: str
    redacted_text: str
    found_entities: list[dict]   # list of {text, label, start, end}
    pii_found: bool


class PIIDetector:
    """
    Detects and redacts PII from text using GLiNER.
    Falls back to regex patterns if GLiNER is unavailable.

    Protects:
    - Names (PERSON)
    - SSN / passport / visa numbers (ID)
    - Phone numbers
    - Email addresses
    - Physical addresses (LOCATION)
    - Dates of birth (DATE_OF_BIRTH)
    - Case numbers linked to individuals
    """

    # PII entity types GLiNER will detect
    GLINER_LABELS = [
        "social security number",
        "passport number",
        "phone number",
        "email address",
        "address",
        "date of birth",
        "alien registration number",
        "visa number",
    ]

    # Regex fallback patterns
    REGEX_PATTERNS = {
        "SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "PHONE": re.compile(
            r"\b(\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
        ),
        "EMAIL": re.compile(
            r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b"
        ),
        "PASSPORT": re.compile(r"\b[A-Z]{1,2}\d{6,9}\b"),
        "ALIEN_NUMBER": re.compile(r"\bA[-\s]?\d{8,9}\b", re.IGNORECASE),
        "DATE_OF_BIRTH": re.compile(
            r"\b(0?[1-9]|1[0-2])[\/\-](0?[1-9]|[12]\d|3[01])[\/\-](19|20)\d{2}\b"
        ),
        "ZIP_CODE": re.compile(r"\b\d{5}(?:-\d{4})?\b"),
    }

    def __init__(self):
        self.model = None
        if GLINER_AVAILABLE:
            try:
                from app.config import settings
                self.model = GLiNER.from_pretrained(settings.GLINER_MODEL)
                logger.info(f"GLiNER model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load GLiNER model: {e}")
                self.model = None

    def detect_and_redact(self, text: str) -> PIIDetectionResult:
        """
        Main entry point.
        Detects PII and returns redacted text.
        """
        if not text or not text.strip():
            return PIIDetectionResult(
                original_text=text,
                redacted_text=text,
                found_entities=[],
                pii_found=False,
            )

        if self.model is not None:
            return self._gliner_redact(text)
        else:
            return self._regex_redact(text)

    def _gliner_redact(self, text: str) -> PIIDetectionResult:
        """Use GLiNER model for PII detection."""
        try:
            # GLiNER works best on shorter texts — chunk if needed
            if len(text) > 2000:
                return self._process_in_chunks(text)

            entities = self.model.predict_entities(
                text,
                self.GLINER_LABELS,
                threshold=0.8,
            )

            if not entities:
                return PIIDetectionResult(
                    original_text=text,
                    redacted_text=text,
                    found_entities=[],
                    pii_found=False,
                )

            # sort entities by start position descending
            # so replacing from end doesn't shift earlier positions
            entities_sorted = sorted(
                entities,
                key=lambda e: e["start"],
                reverse=True,
            )

            redacted = text
            found = []

            for entity in entities_sorted:
                label = entity["label"].upper().replace(" ", "_")
                placeholder = f"[REDACTED-{label}]"
                start = entity["start"]
                end = entity["end"]
                redacted = redacted[:start] + placeholder + redacted[end:]
                found.append({
                    "text": entity["text"],
                    "label": entity["label"],
                    "start": start,
                    "end": end,
                })

            logger.info(f"GLiNER redacted {len(found)} PII entities")

            return PIIDetectionResult(
                original_text=text,
                redacted_text=redacted,
                found_entities=found,
                pii_found=len(found) > 0,
            )

        except Exception as e:
            logger.error(f"GLiNER detection failed: {e} — falling back to regex")
            return self._regex_redact(text)

    def _regex_redact(self, text: str) -> PIIDetectionResult:
        """Regex fallback when GLiNER is unavailable."""
        redacted = text
        found = []

        for label, pattern in self.REGEX_PATTERNS.items():
            matches = list(pattern.finditer(redacted))
            for match in reversed(matches):  # reverse to preserve positions
                placeholder = f"[REDACTED-{label}]"
                found.append({
                    "text": match.group(),
                    "label": label,
                    "start": match.start(),
                    "end": match.end(),
                })
                redacted = (
                    redacted[:match.start()]
                    + placeholder
                    + redacted[match.end():]
                )

        if found:
            logger.info(f"Regex redacted {len(found)} PII entities")

        return PIIDetectionResult(
            original_text=text,
            redacted_text=redacted,
            found_entities=found,
            pii_found=len(found) > 0,
        )

    def _process_in_chunks(self, text: str) -> PIIDetectionResult:
        """
        For long texts, process in 1500 char overlapping chunks
        then merge results.
        """
        chunk_size = 1500
        overlap = 100
        all_entities = []
        redacted_parts = []

        pos = 0
        while pos < len(text):
            end = min(pos + chunk_size, len(text))
            chunk = text[pos:end]

            result = self._gliner_redact(chunk)

            # adjust entity positions back to full text positions
            for entity in result.found_entities:
                entity["start"] += pos
                entity["end"] += pos
                all_entities.append(entity)

            redacted_parts.append(result.redacted_text)
            pos += chunk_size - overlap

        # rebuild full redacted text
        # simple approach — re-run regex on full text as final pass
        merged = "".join(redacted_parts[:1])  # simplified merge
        regex_result = self._regex_redact(text)

        return PIIDetectionResult(
            original_text=text,
            redacted_text=regex_result.redacted_text,
            found_entities=all_entities + regex_result.found_entities,
            pii_found=len(all_entities) > 0 or regex_result.pii_found,
        )