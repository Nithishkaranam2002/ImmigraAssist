import re
from dataclasses import dataclass

SESSION_HISTORY_TURN_LIMIT = 10
SESSION_ANSWER_SNIPPET_CHARS = 1200

FOLLOW_UP_RE = re.compile(
    r"\b("
    r"that|those|this|it|same|above|earlier|previous|you\s+said|just\s+mentioned|"
    r"explain|clarify|elaborate|more\s+detail|tell\s+me\s+more|what\s+about|how\s+about|"
    r"can\s+you|could\s+you|why\s+is|why\s+does|what\s+if|"
    r"renewal|extension|automatic\s+extension"
    r")\b",
    re.IGNORECASE,
)

VISA_IN_QUERY_RE = re.compile(
    r"\b("
    r"h[-\s]?1b|h[-\s]?4(?:\s*ead)?|l[-\s]?1[ab]?|o[-\s]?1|"
    r"eb[-\s]?[123]|f[-\s]?1|asylum|green\s*card|tn\b|e[-\s]?2"
    r")\b",
    re.IGNORECASE,
)

# Treat related codes as the same conversation topic (e.g. h4 vs h4_ead).
VISA_FAMILY: dict[str, str] = {
    "h1b": "h1b",
    "h4": "h4",
    "h4_ead": "h4",
    "l1": "l1",
    "o1": "o1",
    "eb1": "eb",
    "eb2": "eb",
    "eb3": "eb",
    "f1": "f1",
    "asylum": "asylum",
    "green_card": "gc",
}


@dataclass
class SessionHistory:
    text: str = ""
    last_query: str | None = None
    last_visa_type: str | None = None
    turn_count: int = 0

    @property
    def has_prior_turns(self) -> bool:
        return self.turn_count > 0


def detect_visa_in_query(query: str) -> str | None:
    """Lightweight visa detection for session topic tracking."""
    q = query.lower()
    if re.search(r"\bh[-\s]?4\s*ead\b", q):
        return "h4_ead"
    if re.search(r"\bh[-\s]?4\b", q):
        return "h4"
    if re.search(r"\bh[-\s]?1b\b", q):
        return "h1b"
    if re.search(r"\bl[-\s]?1[ab]?\b", q):
        return "l1"
    if re.search(r"\bo[-\s]?1\b", q):
        return "o1"
    if re.search(r"\beb[-\s]?1\b", q):
        return "eb1"
    if re.search(r"\beb[-\s]?2\b", q):
        return "eb2"
    if re.search(r"\bf[-\s]?1\b", q):
        return "f1"
    if re.search(r"\basylum\b", q):
        return "asylum"
    if re.search(r"\bgreen\s*card\b", q):
        return "green_card"
    return None


def _visa_families_differ(left: str, right: str) -> bool:
    return VISA_FAMILY.get(left, left) != VISA_FAMILY.get(right, right)


FORMS_FOLLOW_UP_RE = re.compile(
    r"\b("
    r"what\s+forms?|which\s+forms?|forms?\s+(are\s+)?needed|needed\s+for\s+that|"
    r"what\s+to\s+file|which\s+documents?\s+to\s+file"
    r")\b",
    re.IGNORECASE,
)

EXPLICIT_SUBTOPIC_RE = re.compile(
    r"\b(ac21|i[-\s]?140|portability|premium\s+processing|lca|perm|prevailing\s+wage)\b",
    re.IGNORECASE,
)

# AC21 §105 / INA 214(n) job-change portability — distinct from §106 H-4 EAD.
PORTABILITY_RE = re.compile(
    r"\bportability\b|\b(?:job|employer)\s+change\b|\bchange\s+employers?\b",
    re.IGNORECASE,
)

SUBTOPIC_RETRIEVAL_CONTEXT: list[tuple[re.Pattern, str]] = [
    # Portability must win over the generic AC21 → H-4 EAD expansion.
    (
        PORTABILITY_RE,
        "H-1B AC21 portability INA 214(n) job change employer transfer",
    ),
    (re.compile(r"\bac21\b", re.I), "H-1B AC21 section 106 H-4 EAD eligibility evidence"),
    (re.compile(r"\bi[-\s]?140\b", re.I), "H-4 EAD approved Form I-140 immigrant petition evidence"),
]


def is_portability_query(query: str) -> bool:
    """True when the user is asking about H-1B AC21 job-change portability (§105 / INA 214(n))."""
    return bool(PORTABILITY_RE.search(query))


def ac21_completeness_hints(query: str) -> list[str]:
    """Prompt checklist lines for AC21 / I-140. Portability is not H-4 EAD §106."""
    hints: list[str] = []
    if is_portability_query(query):
        hints.append(
            "AC21 portability query — explain H-1B job-change portability under "
            "INA 214(n) / AC21 §105 (new I-129, successor employer, remaining authorized stay). "
            "Do NOT recast this as H-4 EAD eligibility under AC21 §106 unless the user asked about H-4 EAD."
        )
    elif re.search(r"\bac21\b", query, re.I):
        hints.append(
            "AC21 evidence query — explain what documentation proves the H-1B principal "
            "meets AC21 §106(a) or §106(b) eligibility for H-4 EAD (per retrieved sources). "
            "Do NOT repeat the Form I-765 filing checklist unless the user asks for forms."
        )

    if (
        re.search(r"\bi[-\s]?140\b", query, re.I)
        and re.search(r"\bevidence\b", query, re.I)
        and not is_portability_query(query)
    ):
        hints.append(
            "I-140 evidence query — explain what approval notice or petition documentation "
            "demonstrates the principal's approved Form I-140 for H-4 EAD purposes."
        )
    return hints


def is_forms_follow_up_query(query: str) -> bool:
    """True when the user is asking which USCIS forms to file."""
    return bool(FORMS_FOLLOW_UP_RE.search(query))


def has_explicit_subtopic(query: str) -> bool:
    """True when the user names a specific legal concept to research."""
    return bool(EXPLICIT_SUBTOPIC_RE.search(query))


def is_follow_up_query(query: str, *, has_prior_turns: bool) -> bool:
    """Detect questions that refer to or clarify the prior exchange."""
    if not has_prior_turns:
        return False

    q = query.strip()
    if FOLLOW_UP_RE.search(q):
        return True

    if len(q.split()) > 12:
        return False

    if detect_visa_in_query(q):
        return False

    return bool(
        re.search(
            r"\b(what|which|how|forms?|needed|requirements?|documents?|steps?|fees?|timeline|mean|difference)\b",
            q,
            re.IGNORECASE,
        )
    )


def is_new_topic_query(query: str, session: SessionHistory) -> bool:
    """True when the user starts a new research thread within the same session."""
    if not session.has_prior_turns:
        return True

    q = query.strip()
    if re.search(r"\b(compare|versus|vs\.?)\b", q, re.IGNORECASE):
        return True

    detected = detect_visa_in_query(q)
    if detected and session.last_visa_type and _visa_families_differ(detected, session.last_visa_type):
        return True

    if len(q.split()) > 12 and not FOLLOW_UP_RE.search(q) and detected:
        return True

    return False


def expand_query_for_retrieval(
    query: str,
    session: SessionHistory,
    *,
    new_topic: bool = False,
) -> str:
    """Bias retrieval toward the active conversation topic when appropriate."""
    if new_topic:
        return query

    for pattern, context in SUBTOPIC_RETRIEVAL_CONTEXT:
        if pattern.search(query):
            return f"{context} {query}"

    if not session.has_prior_turns or not session.last_query:
        return query

    if is_follow_up_query(query, has_prior_turns=True):
        return f"{session.last_query} {query}"

    if not detect_visa_in_query(query):
        return f"{session.last_query} {query}"

    return query


def format_session_context(logs: list) -> SessionHistory:
    """Build conversation text and metadata from prior audit logs (oldest first)."""
    parts: list[str] = []
    last_query: str | None = None
    last_visa_type: str | None = None

    for log in logs:
        snippet = (log.answer or "")[:SESSION_ANSWER_SNIPPET_CHARS]
        parts.append(f"Q: {log.query}\nA: {snippet}")
        last_query = log.query
        if log.visa_type_detected:
            last_visa_type = log.visa_type_detected

    return SessionHistory(
        text="\n\n".join(parts),
        last_query=last_query,
        last_visa_type=last_visa_type,
        turn_count=len(logs),
    )
