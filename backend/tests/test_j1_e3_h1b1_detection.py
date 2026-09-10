"""J-1 / E-3 / H-1B1 must not inherit the prior exclusive visa corpus.

J-1 and E-3 were omitted from detect_visa_in_query and MetadataFilter,
so an H-1B (or L-1) session treated those named questions as visaless
follow-ups and exclusive-filtered to the prior visa's law.

H-1B1 is an official Chile/Singapore FTA classification. The H-1B
word-boundary pattern ``\\bh[-\\s]?1b\\b`` misses the trailing 1, so
H-1B1 questions were likewise treated as visaless.

Hyphenated J-1 / E-3 / H-1B1 spellings also failed moderator
normalization, blocking first-turn 7+ word questions as out of scope.
"""
import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("MILVUS_HOST", "localhost")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("OPENAI_API_KEY", "test")

from app.guardrails.content_moderator import ContentModerator
from app.retrieval.metadata_filter import MetadataFilter
from app.services.session_context import (
    SessionHistory,
    detect_visa_in_query,
    expand_query_for_retrieval,
    is_follow_up_query,
    is_new_topic_query,
)


H1B_SESSION = SessionHistory(
    text="Q: H-1B specialty occupation?\nA: ...",
    last_query="What are H-1B specialty occupation requirements?",
    last_visa_type="h1b",
    turn_count=1,
)

L1_SESSION = SessionHistory(
    text="Q: L-1 intracompany transferee?\nA: ...",
    last_query="What are L-1 intracompany transferee requirements?",
    last_visa_type="l1",
    turn_count=1,
)


def test_detects_j1_e3_and_h1b1():
    assert detect_visa_in_query("What are the J-1 two-year residence requirements?") == "j1"
    assert detect_visa_in_query("J1 exchange visitor 212(e)") == "j1"
    assert detect_visa_in_query("What are the E-3 eligibility requirements?") == "e3"
    assert detect_visa_in_query("E3 Australian specialty occupation") == "e3"
    assert detect_visa_in_query("What are the H-1B1 eligibility requirements?") == "h1b"
    assert detect_visa_in_query("H1B1 Chile Singapore FTA") == "h1b"


def test_bare_h1b_still_detected():
    assert detect_visa_in_query("What are H-1B specialty occupation requirements?") == "h1b"


def test_e3_not_confused_with_e2_or_eb3():
    assert detect_visa_in_query("What are the E-3 eligibility requirements?") == "e3"
    assert detect_visa_in_query("What are H-1B specialty occupation requirements?") == "h1b"


def test_j1_after_h1b_is_new_topic_not_follow_up():
    query = "What are the J-1 two-year residence requirements?"
    assert not is_follow_up_query(query, has_prior_turns=True)
    assert is_new_topic_query(query, H1B_SESSION)
    expanded = expand_query_for_retrieval(query, H1B_SESSION, new_topic=True)
    assert expanded == query
    assert "H-1B" not in expanded


def test_e3_after_l1_is_new_topic_not_follow_up():
    query = "What are the E-3 eligibility requirements?"
    assert not is_follow_up_query(query, has_prior_turns=True)
    assert is_new_topic_query(query, L1_SESSION)
    expanded = expand_query_for_retrieval(query, L1_SESSION, new_topic=True)
    assert expanded == query
    assert "L-1" not in expanded


def test_h1b1_after_l1_is_new_topic():
    query = "What are the H-1B1 eligibility requirements?"
    assert not is_follow_up_query(query, has_prior_turns=True)
    assert is_new_topic_query(query, L1_SESSION)
    expanded = expand_query_for_retrieval(query, L1_SESSION, new_topic=True)
    assert expanded == query
    assert "L-1" not in expanded


def test_h1b1_after_h1b_does_not_prepend_prior_query():
    """H-1B1 shares the H-1B family (Volume 2 Part H) but must not prepend."""
    query = "What are the H-1B1 eligibility requirements?"
    assert detect_visa_in_query(query) == "h1b"
    assert not is_follow_up_query(query, has_prior_turns=True)
    expanded = expand_query_for_retrieval(query, H1B_SESSION, new_topic=False)
    assert expanded == query


def test_metadata_filter_detects_j1_e3_h1b1():
    filt = MetadataFilter()
    assert filt._detect_visa_type("What are the J-1 two-year residence requirements?") == "j1"
    assert filt._detect_visa_type("What are the E-3 eligibility requirements?") == "e3"
    assert filt._detect_visa_type("What are the H-1B1 eligibility requirements?") == "h1b"
    assert filt._detect_visa_type("What are H-1B specialty occupation requirements?") == "h1b"


def test_moderator_allows_j1_e3_h1b1_questions():
    moderator = ContentModerator()
    for query in (
        "What are the J-1 two-year residence requirements?",
        "What are the official J-1 two-year home residence requirements?",
        "What are the official E-3 specialty occupation requirements?",
        "What are the official H-1B1 eligibility requirements?",
        "Explain the H-1B1 Chile Singapore FTA specialty occupation criteria",
    ):
        result = moderator.moderate(query)
        assert result.is_safe, query
