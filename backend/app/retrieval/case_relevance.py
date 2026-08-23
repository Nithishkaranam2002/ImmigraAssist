"""Post-retrieval relevance filter for case chunks and court decisions."""
import re
from typing import Optional

from app.retrieval.hybrid_retriever import RetrievedChunk
from app.utils.logger import logger


STOP_WORDS = frozenset({
    "what", "are", "the", "for", "how", "to", "is", "a", "an", "can", "do",
    "long", "much", "many", "does", "did", "have", "has", "been", "being",
    "requirements", "explain", "tell", "about", "please", "help", "need",
    "that", "this", "with", "from", "when", "where", "which", "who", "why",
})

VISA_TEXT_PATTERNS: dict[str, list[str]] = {
    "h1b": [r"\bh-?1b\b", r"specialty\s+occupation", r"\blca\b"],
    "h4": [r"\bh-?4\b", r"dependent\s+spouse"],
    "h4_ead": [r"\bh-?4\b", r"\bead\b", r"employment\s+authorization", r"i-765", r"\(c\)\(26\)"],
    "l1": [r"\bl-?1[ab]?\b", r"intracompany"],
    "o1": [r"\bo-?1\b", r"extraordinary\s+ability"],
    "eb1": [r"\beb-?1\b", r"priority\s+worker"],
    "eb2": [r"\beb-?2\b", r"\bperm\b", r"labor\s+certification"],
    "asylum": [r"\basylum\b", r"withholding\s+of\s+removal", r"persecution"],
    "green_card": [r"adjustment\s+of\s+status", r"i-485", r"lawful\s+permanent\s+resident"],
    "f1": [
        r"\bf-?1\b", r"\bopt\b", r"stem\s+opt", r"\bcpt\b", r"\bsevis\b",
        r"i-983", r"practical\s+training", r"optional\s+practical",
        r"student\s+visa", r"designated\s+school", r"student\s+employment",
        r"alliance\s+of\s+technology\s+workers", r"technology\s+workers.*dhs",
    ],
}

TOPIC_MISMATCH: dict[str, list[str]] = {
    "h1b": [r"\basylum\b", r"\bnaturalization\b", r"\bn-400\b", r"\bfair\s+admissions\b"],
    "h4": [r"\basylum\b", r"\bnaturalization\b", r"\bh-1b\s+cap\b"],
    "h4_ead": [r"\basylum\b", r"\bnaturalization\b", r"\bh-1b\s+cap\b"],
    "l1": [r"\basylum\b", r"\bnaturalization\b", r"\bfair\s+admissions\b"],
    "o1": [r"\basylum\b", r"\bnaturalization\b"],
    "eb1": [r"\basylum\b", r"\bfair\s+admissions\b"],
    "eb2": [r"\basylum\b", r"\bfair\s+admissions\b"],
    "f1": [
        r"\basylum\b", r"\bnaturalization\b", r"\bn-400\b",
        r"\bfair\s+admissions\b", r"\bstudents?\s+for\s+fair\b",
        r"\bh-1b\b(?!.*\b(cap[- ]?gap|student)\b)",
        r"\bspecialty\s+occupation\b(?!.*\bstudent\b)",
    ],
    "asylum": [r"\bh-1b\s+cap\b", r"\bpremium\s+processing\b"],
    "green_card": [r"\bh-1b\s+cap\b", r"\bfair\s+admissions\b"],
}

QUERY_TOPIC_MISMATCH: list[tuple[re.Pattern, list[str]]] = [
    (
        # CPT is school-authorized practical training — not the 24-month STEM OPT / I-983 program.
        re.compile(r"\b(cpt\b|curricular\s+practical)\b", re.I),
        [
            r"\bstem\s+opt\b",
            r"\bi-983\b",
            r"\b24[- ]month\b",
            r"\bh-1b\b",
            r"\bspecialty\s+occupation\b",
            r"\bfair\s+admissions\b",
            r"\bstudents?\s+for\s+fair\b",
            r"\bnaturalization\b",
            r"\basylum\b",
        ],
    ),
    (
        re.compile(r"\b(opt|stem\s+opt|cpt|practical\s+training|sevis|i-983)\b", re.I),
        [
            r"\bh-1b\b", r"\bspecialty\s+occupation\b", r"\blca\b",
            r"\bfair\s+admissions\b", r"\bstudents?\s+for\s+fair\b",
            r"\bnaturalization\b", r"\basylum\b",
        ],
    ),
]

MIN_CHUNK_RELEVANCE = 0.28


def _tokenize(text: str) -> set[str]:
    normalized = re.sub(r"[^\w\s-]", " ", text.lower())
    return {
        w.strip("-")
        for w in normalized.split()
        if len(w.strip("-")) >= 3 and w.strip("-") not in STOP_WORDS
    }


def _text_matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text, re.I) for p in patterns)


def score_case_text(
    text: str,
    query: str,
    visa_type: Optional[str] = None,
    *,
    chunk_visa_type: Optional[str] = None,
) -> float:
    """Score how relevant a case body/name is to the user query."""
    haystack = re.sub(r"[_-]+", " ", text.lower())
    query_tokens = _tokenize(query)
    text_tokens = _tokenize(text)

    if not query_tokens:
        return 0.0

    overlap = query_tokens & text_tokens
    score = min(len(overlap) * 0.14, 0.42)

    if visa_type and visa_type in VISA_TEXT_PATTERNS:
        if _text_matches_any(haystack, VISA_TEXT_PATTERNS[visa_type]):
            score += 0.32
        elif chunk_visa_type and chunk_visa_type.replace("_ead", "") == visa_type.replace("_ead", ""):
            score += 0.22
        elif chunk_visa_type and chunk_visa_type != visa_type:
            score -= 0.2

        for pattern in TOPIC_MISMATCH.get(visa_type, []):
            if re.search(pattern, haystack, re.I):
                score -= 0.5

    for query_pat, mismatch_patterns in QUERY_TOPIC_MISMATCH:
        if query_pat.search(query):
            for pattern in mismatch_patterns:
                if re.search(pattern, haystack, re.I):
                    score -= 0.55

    # Hard gate: student/OPT questions must mention student-pathway terms in the case.
    if visa_type == "f1" and re.search(
        r"\b(opt|stem\s+opt|cpt|practical\s+training)\b", query, re.I
    ):
        if not _text_matches_any(haystack, VISA_TEXT_PATTERNS["f1"]):
            return 0.0

    return max(score, 0.0)


def filter_case_chunks(
    chunks: list[RetrievedChunk],
    query: str,
    visa_type: Optional[str] = None,
    min_score: float = MIN_CHUNK_RELEVANCE,
    *,
    filename_by_doc_id: Optional[dict[str, str]] = None,
) -> list[RetrievedChunk]:
    """Drop vector-retrieved case chunks that do not match the query topic."""
    if not chunks:
        return []

    kept: list[RetrievedChunk] = []
    for chunk in chunks:
        prefix = ""
        if filename_by_doc_id:
            prefix = filename_by_doc_id.get(chunk.document_id, "") + " "
        score = score_case_text(
            f"{prefix}{chunk.text}",
            query,
            visa_type,
            chunk_visa_type=chunk.visa_type,
        )
        if score >= min_score:
            kept.append(chunk)

    if len(kept) < len(chunks):
        logger.info(
            f"Case relevance filter kept {len(kept)}/{len(chunks)} chunks "
            f"(visa={visa_type})"
        )
    return kept


def filter_court_cases(
    cases: list,
    query: str,
    visa_type: Optional[str] = None,
    min_score: float = MIN_CHUNK_RELEVANCE,
) -> list:
    """Drop live CourtListener results that do not match the query topic."""
    if not cases:
        return []

    kept = []
    for case in cases:
        text = f"{getattr(case, 'case_name', '')} {getattr(case, 'summary', '') or ''}"
        score = score_case_text(text, query, visa_type)
        if score >= min_score:
            kept.append(case)

    if len(kept) < len(cases):
        logger.info(
            f"Court case filter kept {len(kept)}/{len(cases)} decisions (visa={visa_type})"
        )
    return kept
