"""M-1 / M-2 must not inherit the prior exclusive visa corpus.

M-1 (vocational student) and M-2 (M-1 dependent) were omitted from
detect_visa_in_query and MetadataFilter, so an H-1B session treated those
named questions as visaless follow-ups and exclusive-filtered to H-1B law.

First-turn M-1 OPT questions also fell through to
_infer_visa_from_topic's ``opt`` → f1 mapping, so they retrieved only
F-1 academic OPT / STEM OPT policy instead of M-1 practical training
(no STEM OPT; shorter duration).

First-turn M-2 EAD questions fell through to generic ``ead`` → h4_ead,
so they retrieved only H-4 EAD (c)(26) policy.

First-turn M-1 premium-processing questions fell through to
``premium processing`` → h1b.

Hyphenated M-1 / M-2 spellings also failed moderator normalization,
blocking first-turn 7+ word questions as out of scope.
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
    text="Q: F-1 student visa?\nA: ...",
    last_query="What are F-1 student visa requirements?",
    last_visa_type="f1",
    turn_count=1,
)


def test_detects_m1_and_m2():
    assert detect_visa_in_query("What are M-1 OPT eligibility requirements?") == "m1"
    assert detect_visa_in_query("M1 vocational student visa") == "m1"
    assert detect_visa_in_query("What are the official M-1 eligibility requirements?") == "m1"
    assert detect_visa_in_query("What are M-2 EAD eligibility requirements?") == "m2"
    assert detect_visa_in_query("M2 dependent of vocational student") == "m2"
    assert detect_visa_in_query("What are the official M-2 eligibility requirements?") == "m2"


def test_does_not_confuse_adjacent_codes():
    assert detect_visa_in_query("What are H-1B specialty occupation requirements?") == "h1b"
    assert detect_visa_in_query("What are F-1 student visa requirements?") == "f1"
    assert detect_visa_in_query("What are F-1 OPT eligibility requirements?") == "f1"
    # Word-boundary: "am 1" / bare digits are not M-1
    assert detect_visa_in_query("What am 1 supposed to file?") is None


def test_m1_after_h1b_is_new_topic_not_follow_up():
    query = "What are M-1 eligibility requirements?"
    assert not is_follow_up_query(query, has_prior_turns=True)
    assert is_new_topic_query(query, H1B_SESSION)
    expanded = expand_query_for_retrieval(query, H1B_SESSION, new_topic=True)
    assert expanded == query
    assert "H-1B" not in expanded


def test_m2_after_h1b_is_new_topic_not_follow_up():
    query = "What are M-2 eligibility requirements?"
    assert not is_follow_up_query(query, has_prior_turns=True)
    assert is_new_topic_query(query, H1B_SESSION)
    expanded = expand_query_for_retrieval(query, H1B_SESSION, new_topic=True)
    assert expanded == query
    assert "H-1B" not in expanded


def test_m1_after_f1_is_new_topic():
    """Vocational M-1 must not inherit the academic F-1 / STEM OPT corpus."""
    query = "What are M-1 OPT eligibility requirements?"
    assert is_new_topic_query(query, F1_SESSION)
    expanded = expand_query_for_retrieval(query, F1_SESSION, new_topic=True)
    assert expanded == query
    assert "F-1" not in expanded


def test_metadata_filter_detects_m1_m2_not_inferred_codes():
    filt = MetadataFilter()
    assert filt._detect_visa_type("What are M-1 OPT eligibility requirements?") == "m1"
    assert filt._detect_visa_type("What are the official M-1 eligibility requirements?") == "m1"
    assert filt._detect_visa_type("What are M-2 EAD eligibility requirements?") == "m2"
    assert filt._detect_visa_type("What are the official M-2 eligibility requirements?") == "m2"
    assert filt._detect_visa_type("What are H-1B specialty occupation requirements?") == "h1b"
    assert filt._detect_visa_type("What are F-1 OPT eligibility requirements?") == "f1"


def test_first_turn_m1_opt_does_not_infer_f1():
    """Named M-1 OPT must not exclusive-filter to F-1 STEM OPT policy."""
    filt = MetadataFilter()
    query = "What are M-1 OPT eligibility requirements?"
    detected = filt._detect_visa_type(query)
    assert detected == "m1"
    assert filt._infer_visa_from_topic(query) == "f1"
    assert detected != "f1"


def test_first_turn_m2_ead_does_not_infer_h4_ead():
    """Named M-2 EAD must not exclusive-filter to H-4 EAD (c)(26) policy."""
    filt = MetadataFilter()
    query = "What are M-2 EAD eligibility requirements?"
    detected = filt._detect_visa_type(query)
    assert detected == "m2"
    assert filt._infer_visa_from_topic(query) == "h4_ead"
    assert detected != "h4_ead"


def test_first_turn_m1_premium_processing_does_not_infer_h1b():
    """Named M-1 premium processing must not exclusive-filter to H-1B law."""
    filt = MetadataFilter()
    query = "What is M-1 premium processing?"
    detected = filt._detect_visa_type(query)
    assert detected == "m1"
    assert filt._infer_visa_from_topic(query) == "h1b"
    assert detected != "h1b"


def test_moderator_allows_m1_m2_questions():
    moderator = ContentModerator()
    for query in (
        "What are M-1 OPT eligibility requirements?",
        "What are the official M-1 eligibility requirements?",
        "What are M-2 EAD eligibility requirements?",
        "What are the official M-2 eligibility requirements?",
        "What is M-1 premium processing?",
    ):
        result = moderator.moderate(query)
        assert result.is_safe, query
