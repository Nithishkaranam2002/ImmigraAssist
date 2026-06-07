import re
from dataclasses import dataclass
from app.utils.logger import logger


@dataclass
class ClassificationResult:
    doc_type: str           # "law" or "case"
    confidence: float       # 0.0 to 1.0
    detected_visa_type: str | None


class DocumentClassifier:
    """
    Classifies uploaded PDFs as either law/policy docs or case files.

    Strategy: rule-based keyword classifier first (fast, no model needed).
    ONNX model layer can be plugged in later on top for edge cases.

    Law doc signals:  Section, Clause, Policy, Regulation, USCIS, Federal Register
    Case doc signals: v., Docket, Petitioner, Respondent, HELD, Circuit, Court
    """

    LAW_KEYWORDS = [
        "section", "clause", "policy", "regulation", "federal register",
        "uscis", "department of homeland security", "8 c.f.r",
        "immigration and nationality act", "effective date", "final rule",
    ]

    CASE_KEYWORDS = [
        "petitioner", "respondent", "docket", "circuit", "court",
        "held", "ruling", "opinion", "judge", "appeal", "denied",
        "approved", "remanded", "matter of", "in re", "v.",
        "board of immigration appeals", "bia",
    ]

    VISA_PATTERNS = {
        "h1b": re.compile(r"\bh[-\s]?1b\b", re.IGNORECASE),
        "h4": re.compile(r"\bh[-\s]?4\b", re.IGNORECASE),
        "h4_ead": re.compile(r"\bh[-\s]?4\s*ead\b", re.IGNORECASE),
        "l1": re.compile(r"\bl[-\s]?1[ab]?\b", re.IGNORECASE),
        "o1": re.compile(r"\bo[-\s]?1\b", re.IGNORECASE),
        "eb1": re.compile(r"\beb[-\s]?1\b", re.IGNORECASE),
        "eb2": re.compile(r"\beb[-\s]?2\b", re.IGNORECASE),
        "asylum": re.compile(r"\basylum\b", re.IGNORECASE),
        "green_card": re.compile(r"\bgreen\s*card\b|\blawful permanent resident\b", re.IGNORECASE),
        "f1": re.compile(r"\bf[-\s]?1\b", re.IGNORECASE),
    }

    def classify(self, text: str, file_metadata: dict | None = None) -> ClassificationResult:
        """
        Classify document type and detect visa type from text.
        Uses first 3000 chars — enough signal without reading whole doc.
        """
        header_visa = None
        if file_metadata:
            header_visa = file_metadata.get("visa_type")
            if file_metadata.get("source") == "uscis_policy":
                return ClassificationResult(
                    doc_type="law",
                    confidence=0.95,
                    detected_visa_type=header_visa or self._detect_visa_type(text[:5000]),
                )

        sample = text[:3000].lower()

        law_score = sum(1 for kw in self.LAW_KEYWORDS if kw in sample)
        case_score = sum(1 for kw in self.CASE_KEYWORDS if kw in sample)

        total = law_score + case_score
        if total == 0:
            # no signal — default to law doc
            logger.warning("Classifier found no signal, defaulting to 'law'")
            return ClassificationResult(
                doc_type="law",
                confidence=0.5,
                detected_visa_type=None,
            )

        if law_score >= case_score:
            doc_type = "law"
            confidence = law_score / total
        else:
            doc_type = "case"
            confidence = case_score / total

        visa_type = header_visa or self._detect_visa_type(text[:5000])

        logger.info(
            f"Classified as '{doc_type}' "
            f"(confidence={confidence:.2f}, visa={visa_type})"
        )

        return ClassificationResult(
            doc_type=doc_type,
            confidence=confidence,
            detected_visa_type=visa_type,
        )

    def _detect_visa_type(self, text: str) -> str | None:
        """Detect the primary visa type mentioned in the document."""
        for visa_type, pattern in self.VISA_PATTERNS.items():
            if pattern.search(text):
                return visa_type
        return None