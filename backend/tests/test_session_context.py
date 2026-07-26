from types import SimpleNamespace

from app.guardrails.pii_detector import PIIDetector
from app.services.session_context import (
    SessionHistory,
    expand_query_for_retrieval,
    format_session_context,
    is_follow_up_query,
    is_forms_follow_up_query,
    is_new_topic_query,
)


def test_follow_up_detection_with_deictic():
    assert is_follow_up_query(
        "What forms are needed for that?",
        has_prior_turns=True,
    )


def test_follow_up_detection_clarifying_question():
    assert is_follow_up_query(
        "Can you explain the 180 day extension?",
        has_prior_turns=True,
    )


def test_follow_up_expands_with_prior_query():
    session = SessionHistory(
        text="Q: H4 EAD?\nA: ...",
        last_query="What are the requirements for H4 EAD eligibility?",
        last_visa_type="h4",
        turn_count=1,
    )
    expanded = expand_query_for_retrieval("What forms are needed for that?", session)
    assert "H4 EAD eligibility" in expanded
    assert "What forms are needed for that?" in expanded


def test_standalone_query_not_follow_up():
    assert not is_follow_up_query(
        "What is the H-1B cap and how does the lottery work?",
        has_prior_turns=True,
    )


def test_new_topic_when_visa_changes():
    session = SessionHistory(
        text="Q: H4?\nA: ...",
        last_query="What are H4 EAD requirements?",
        last_visa_type="h4",
        turn_count=1,
    )
    assert is_new_topic_query("What is the H-1B cap and how does the lottery work?", session)


def test_same_topic_follow_up_not_new():
    session = SessionHistory(
        text="Q: H4?\nA: ...",
        last_query="What are H4 EAD requirements?",
        last_visa_type="h4",
        turn_count=1,
    )
    assert not is_new_topic_query("What forms are needed for that?", session)


def test_forms_follow_up_detection():
    assert is_forms_follow_up_query("What forms are needed for that?")
    assert not is_forms_follow_up_query("What evidence is required for AC21?")


def test_ac21_query_expands_with_subtopic_context():
    session = SessionHistory(
        text="Q: extension?\nA: ...",
        last_query="Can you explain the 180 day extension?",
        last_visa_type="h4",
        turn_count=2,
    )
    expanded = expand_query_for_retrieval("What evidence is required for AC21?", session)
    assert "AC21" in expanded
    assert "180 day extension" not in expanded


def test_new_topic_skips_retrieval_expansion():
    session = SessionHistory(
        text="Q: H4?\nA: ...",
        last_query="What are H4 EAD requirements?",
        last_visa_type="h4",
        turn_count=1,
    )
    query = "What is the H-1B cap and how does the lottery work?"
    assert expand_query_for_retrieval(query, session, new_topic=True) == query


def test_format_session_context_redacts_prior_query_pii():
    """Follow-up context must not reintroduce raw AuditLog.query PII."""
    detector = PIIDetector()
    raw_query = (
        "My client A-12345678 (SSN 123-45-6789, email client@example.com) "
        "needs H-4 EAD eligibility."
    )
    logs = [
        SimpleNamespace(
            query=raw_query,
            answer="File Form I-765 with supporting evidence.",
            visa_type_detected="h4",
        )
    ]

    history = format_session_context(
        logs,
        redact_query=lambda q: detector._regex_redact(q).redacted_text,
    )

    assert "A-12345678" not in history.text
    assert "123-45-6789" not in history.text
    assert "client@example.com" not in history.text
    assert history.last_query is not None
    assert "A-12345678" not in history.last_query
    assert "123-45-6789" not in history.last_query
    assert "client@example.com" not in history.last_query
    assert "H-4 EAD" in history.last_query
    assert history.last_visa_type == "h4"

    expanded = expand_query_for_retrieval(
        "What forms are needed for that?",
        history,
    )
    assert "A-12345678" not in expanded
    assert "123-45-6789" not in expanded
    assert "client@example.com" not in expanded
    assert "What forms are needed for that?" in expanded
