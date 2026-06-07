import re
from dataclasses import dataclass

FOLLOW_UP_RE = re.compile(
    r"\b(that|those|this|it|same|above|earlier|previous|you\s+said|just\s+mentioned)\b",
    re.IGNORECASE,
)


@dataclass
class SessionHistory:
    text: str = ""
    last_query: str | None = None
    last_visa_type: str | None = None

    @property
    def has_prior_turns(self) -> bool:
        return bool(self.text)


def is_follow_up_query(query: str, *, has_prior_turns: bool) -> bool:
    """Detect short or deictic questions that refer to the prior exchange."""
    if not has_prior_turns:
        return False

    q = query.strip()
    if FOLLOW_UP_RE.search(q):
        return True

    if len(q.split()) > 8:
        return False

    has_visa = bool(
        re.search(
            r"\b(h[-\s]?1b|h[-\s]?4|l[-\s]?1|o[-\s]?1|eb[-\s]?[12]|f[-\s]?1|asylum|green\s*card)\b",
            q,
            re.IGNORECASE,
        )
    )
    if has_visa:
        return False

    return bool(
        re.search(
            r"\b(what|which|how|forms?|needed|requirements?|documents?|steps?|fees?|timeline)\b",
            q,
            re.IGNORECASE,
        )
    )


def expand_query_for_retrieval(query: str, session: SessionHistory) -> str:
    """Bias retrieval toward the prior topic when the user asks a follow-up."""
    if not is_follow_up_query(query, has_prior_turns=session.has_prior_turns):
        return query
    if not session.last_query:
        return query
    return f"{session.last_query} {query}"


def format_session_context(logs: list) -> SessionHistory:
    """Build conversation text and metadata from prior audit logs (oldest first)."""
    parts: list[str] = []
    last_query: str | None = None
    last_visa_type: str | None = None

    for log in logs:
        parts.append(f"Q: {log.query}\nA: {(log.answer or '')[:500]}")
        last_query = log.query
        if log.visa_type_detected:
            last_visa_type = log.visa_type_detected

    return SessionHistory(
        text="\n\n".join(parts),
        last_query=last_query,
        last_visa_type=last_visa_type,
    )
