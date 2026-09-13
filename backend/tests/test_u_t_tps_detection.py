"""U / T / TPS must not inherit the prior exclusive visa corpus.

U visa, T visa, and TPS were omitted from detect_visa_in_query and
MetadataFilter, so an H-1B session treated those named questions as
visaless follow-ups and exclusive-filtered to H-1B law.

First-turn U / T / TPS EAD questions also fell through to
_infer_visa_from_topic's generic ``ead`` → h4_ead mapping, so they
retrieved only H-4 EAD (c)(26) policy instead of (a)(19)/(a)(16)/(a)(12).

First-turn U / T premium-processing questions fell through to
``premium processing`` → h1b.

Hyphenated U-1 / T-1 and bare TPS spellings also failed moderator
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

ASYLUM_SESSION = SessionHistory(
    text="Q: asylum eligibility?\nA: ...",
    last_query="What are asylum eligibility requirements?",
    last_visa_type="asylum",
    turn_count=1,
)


def test_detects_u_t_and_tps():
    assert detect_visa_in_query("What are U visa EAD eligibility requirements?") == "u"
    assert detect_visa_in_query("U-visa bona fide determination") == "u"
    assert detect_visa_in_query("What are the official U-1 eligibility requirements?") == "u"
    assert detect_visa_in_query("U nonimmigrant status") == "u"
    assert detect_visa_in_query("What are T visa EAD eligibility requirements?") == "t"
    assert detect_visa_in_query("T-visa trafficking victim") == "t"
    assert detect_visa_in_query("What are T-1 EAD eligibility requirements?") == "t"
    assert detect_visa_in_query("T nonimmigrant status") == "t"
    assert detect_visa_in_query("What are TPS EAD eligibility requirements?") == "tps"
    assert detect_visa_in_query("temporary protected status work authorization") == "tps"


def test_does_not_confuse_adjacent_codes():
    assert detect_visa_in_query("What are H-1B specialty occupation requirements?") == "h1b"
    assert detect_visa_in_query("What are F-1 student visa requirements?") == "f1"
    assert detect_visa_in_query("What are asylum eligibility requirements?") == "asylum"
    # US / U.S. visa is not the U nonimmigrant category
    assert detect_visa_in_query("What are US visa interview requirements?") is None
    assert detect_visa_in_query("What are U.S. visa stamp requirements?") is None
    # TN is not a T visa; TPS is not a T visa
    assert detect_visa_in_query("What are TN visa eligibility requirements?") is None
    assert detect_visa_in_query("What are TPS eligibility requirements?") == "tps"


def test_u_after_h1b_is_new_topic_not_follow_up():
    query = "What are U visa eligibility requirements?"
    assert not is_follow_up_query(query, has_prior_turns=True)
    assert is_new_topic_query(query, H1B_SESSION)
    expanded = expand_query_for_retrieval(query, H1B_SESSION, new_topic=True)
    assert expanded == query
    assert "H-1B" not in expanded


def test_t_after_h1b_is_new_topic_not_follow_up():
    query = "What are T visa eligibility requirements?"
    assert not is_follow_up_query(query, has_prior_turns=True)
    assert is_new_topic_query(query, H1B_SESSION)
    expanded = expand_query_for_retrieval(query, H1B_SESSION, new_topic=True)
    assert expanded == query
    assert "H-1B" not in expanded


def test_tps_after_h1b_is_new_topic_not_follow_up():
    query = "What are TPS eligibility requirements?"
    assert not is_follow_up_query(query, has_prior_turns=True)
    assert is_new_topic_query(query, H1B_SESSION)
    expanded = expand_query_for_retrieval(query, H1B_SESSION, new_topic=True)
    assert expanded == query
    assert "H-1B" not in expanded


def test_tps_after_asylum_is_new_topic():
    query = "What are TPS EAD eligibility requirements?"
    assert is_new_topic_query(query, ASYLUM_SESSION)
    expanded = expand_query_for_retrieval(query, ASYLUM_SESSION, new_topic=True)
    assert expanded == query
    assert "asylum" not in expanded.lower()


def test_metadata_filter_detects_u_t_tps_not_inferred_codes():
    filt = MetadataFilter()
    assert filt._detect_visa_type("What are U visa EAD eligibility requirements?") == "u"
    assert filt._detect_visa_type("What are the official U-1 eligibility requirements?") == "u"
    assert filt._detect_visa_type("What are T visa EAD eligibility requirements?") == "t"
    assert filt._detect_visa_type("What are T-1 EAD eligibility requirements?") == "t"
    assert filt._detect_visa_type("What are TPS EAD eligibility requirements?") == "tps"
    assert filt._detect_visa_type("temporary protected status work authorization") == "tps"
    assert filt._detect_visa_type("What are H-1B specialty occupation requirements?") == "h1b"


def test_first_turn_u_ead_does_not_infer_h4_ead():
    """Named U visa EAD must not exclusive-filter to H-4 EAD (c)(26) policy."""
    filt = MetadataFilter()
    query = "What are U visa EAD eligibility requirements?"
    detected = filt._detect_visa_type(query)
    assert detected == "u"
    assert filt._infer_visa_from_topic(query) == "h4_ead"
    assert detected != "h4_ead"


def test_first_turn_t_ead_does_not_infer_h4_ead():
    """Named T visa EAD must not exclusive-filter to H-4 EAD (c)(26) policy."""
    filt = MetadataFilter()
    query = "What are T visa EAD eligibility requirements?"
    detected = filt._detect_visa_type(query)
    assert detected == "t"
    assert filt._infer_visa_from_topic(query) == "h4_ead"
    assert detected != "h4_ead"


def test_first_turn_tps_ead_does_not_infer_h4_ead():
    """Named TPS EAD must not exclusive-filter to H-4 EAD (c)(26) policy."""
    filt = MetadataFilter()
    query = "What are TPS EAD eligibility requirements?"
    detected = filt._detect_visa_type(query)
    assert detected == "tps"
    assert filt._infer_visa_from_topic(query) == "h4_ead"
    assert detected != "h4_ead"


def test_first_turn_u_premium_processing_does_not_infer_h1b():
    """Named U visa premium processing must not exclusive-filter to H-1B law."""
    filt = MetadataFilter()
    query = "What is U visa premium processing?"
    detected = filt._detect_visa_type(query)
    assert detected == "u"
    assert filt._infer_visa_from_topic(query) == "h1b"
    assert detected != "h1b"


def test_moderator_allows_u_t_tps_questions():
    moderator = ContentModerator()
    for query in (
        "What are U visa EAD eligibility requirements?",
        "What are the official U-1 eligibility requirements?",
        "What are T visa EAD eligibility requirements?",
        "What are the official T-1 eligibility requirements?",
        "What are TPS EAD eligibility requirements?",
        "What are the official TPS eligibility requirements?",
        "What are temporary protected status eligibility requirements?",
    ):
        result = moderator.moderate(query)
        assert result.is_safe, query
