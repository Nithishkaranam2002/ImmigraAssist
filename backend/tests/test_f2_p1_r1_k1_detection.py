"""F-2 / P-1 / R-1 / K-1 must not inherit the prior exclusive visa corpus.

F-2, P-1, R-1, and K-1 were omitted from detect_visa_in_query and
MetadataFilter, so an H-1B (or F-1) session treated those named
questions as visaless follow-ups and exclusive-filtered to the prior
visa's law.

First-turn K-1 EAD and F-2 EAD questions also fell through to
_infer_visa_from_topic's generic ``ead`` → h4_ead mapping, so they
retrieved only H-4 EAD (c)(26) policy.

First-turn P-1 / R-1 premium-processing questions fell through to
``premium processing`` → h1b, exclusive-filtering athlete and
religious-worker questions to H-1B specialty-occupation law.

Hyphenated K-1 / P-1 / R-1 spellings also failed moderator
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

F1_SESSION = SessionHistory(
    text="Q: F-1 student status?\nA: ...",
    last_query="What are F-1 student visa requirements?",
    last_visa_type="f1",
    turn_count=1,
)


def test_detects_f2_p1_r1_and_k1():
    assert detect_visa_in_query("What are F-2 EAD eligibility requirements?") == "f2"
    assert detect_visa_in_query("F2 dependent spouse") == "f2"
    assert detect_visa_in_query("What are P-1 athlete eligibility requirements?") == "p1"
    assert detect_visa_in_query("P1 internationally recognized athlete") == "p1"
    assert detect_visa_in_query("What are the official P-1A athlete eligibility requirements?") == "p1"
    assert detect_visa_in_query("What are R-1 religious worker requirements?") == "r1"
    assert detect_visa_in_query("R1 minister") == "r1"
    assert detect_visa_in_query("What are K-1 EAD eligibility requirements?") == "k1"
    assert detect_visa_in_query("K1 fiancé visa") == "k1"


def test_does_not_confuse_adjacent_codes():
    assert detect_visa_in_query("What are F-1 student visa requirements?") == "f1"
    assert detect_visa_in_query("What are H-1B specialty occupation requirements?") == "h1b"
    # F-2A is the family-based immigrant category, not F-2 student dependent
    assert detect_visa_in_query("What are F-2A eligibility requirements?") is None


def test_f2_after_f1_is_new_topic_not_follow_up():
    query = "What are F-2 work authorization requirements?"
    assert not is_follow_up_query(query, has_prior_turns=True)
    assert is_new_topic_query(query, F1_SESSION)
    expanded = expand_query_for_retrieval(query, F1_SESSION, new_topic=True)
    assert expanded == query
    assert "F-1" not in expanded


def test_p1_after_h1b_is_new_topic_not_follow_up():
    query = "What are P-1 athlete eligibility requirements?"
    assert not is_follow_up_query(query, has_prior_turns=True)
    assert is_new_topic_query(query, H1B_SESSION)
    expanded = expand_query_for_retrieval(query, H1B_SESSION, new_topic=True)
    assert expanded == query
    assert "H-1B" not in expanded


def test_r1_after_h1b_is_new_topic_not_follow_up():
    query = "What are R-1 religious worker requirements?"
    assert not is_follow_up_query(query, has_prior_turns=True)
    assert is_new_topic_query(query, H1B_SESSION)
    expanded = expand_query_for_retrieval(query, H1B_SESSION, new_topic=True)
    assert expanded == query
    assert "H-1B" not in expanded


def test_k1_after_h1b_is_new_topic_not_follow_up():
    query = "What are K-1 fiancé visa requirements?"
    assert not is_follow_up_query(query, has_prior_turns=True)
    assert is_new_topic_query(query, H1B_SESSION)
    expanded = expand_query_for_retrieval(query, H1B_SESSION, new_topic=True)
    assert expanded == query
    assert "H-1B" not in expanded


def test_metadata_filter_detects_f2_p1_r1_k1_not_inferred_codes():
    filt = MetadataFilter()
    assert filt._detect_visa_type("What are F-2 EAD eligibility requirements?") == "f2"
    assert filt._detect_visa_type("What are P-1 athlete eligibility requirements?") == "p1"
    assert filt._detect_visa_type("What are the official P-1A athlete eligibility requirements?") == "p1"
    assert filt._detect_visa_type("What are R-1 religious worker requirements?") == "r1"
    assert filt._detect_visa_type("What are K-1 EAD eligibility requirements?") == "k1"
    assert filt._detect_visa_type("What are F-1 student visa requirements?") == "f1"


def test_first_turn_k1_ead_does_not_infer_h4_ead():
    """Named K-1 EAD must not exclusive-filter to H-4 EAD (c)(26) policy."""
    filt = MetadataFilter()
    query = "What are K-1 EAD eligibility requirements?"
    detected = filt._detect_visa_type(query)
    assert detected == "k1"
    assert filt._infer_visa_from_topic(query) == "h4_ead"
    assert detected != "h4_ead"


def test_first_turn_f2_ead_does_not_infer_h4_ead():
    """Named F-2 EAD must not exclusive-filter to H-4 EAD (c)(26) policy."""
    filt = MetadataFilter()
    query = "What are F-2 EAD eligibility requirements?"
    detected = filt._detect_visa_type(query)
    assert detected == "f2"
    assert filt._infer_visa_from_topic(query) == "h4_ead"
    assert detected != "h4_ead"


def test_first_turn_p1_premium_processing_does_not_infer_h1b():
    """Named P-1 premium processing must not exclusive-filter to H-1B law."""
    filt = MetadataFilter()
    query = "What is P-1 premium processing?"
    detected = filt._detect_visa_type(query)
    assert detected == "p1"
    assert filt._infer_visa_from_topic(query) == "h1b"
    assert detected != "h1b"


def test_first_turn_r1_premium_processing_does_not_infer_h1b():
    filt = MetadataFilter()
    query = "What is R-1 premium processing?"
    detected = filt._detect_visa_type(query)
    assert detected == "r1"
    assert filt._infer_visa_from_topic(query) == "h1b"
    assert detected != "h1b"


def test_moderator_allows_f2_p1_r1_k1_questions():
    moderator = ContentModerator()
    for query in (
        "What are F-2 EAD eligibility requirements?",
        "What are the official F-2 dependent eligibility requirements?",
        "What are P-1 athlete eligibility requirements?",
        "What are the official P-1A athlete eligibility requirements?",
        "What are R-1 religious worker requirements?",
        "What are the official R-1 religious worker eligibility requirements?",
        "What are K-1 EAD eligibility requirements?",
        "What are the official K-1 fiancé eligibility requirements?",
    ):
        result = moderator.moderate(query)
        assert result.is_safe, query
