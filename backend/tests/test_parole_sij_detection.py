"""
Humanitarian parole and SIJ were omitted from detect_visa_in_query and
MetadataFilter, so an H-1B session treated those named questions as
visaless follow-ups and exclusive-filtered to H-1B law.

First-turn parole / parolee / SIJ EAD questions also fell through to
_infer_visa_from_topic's generic ``ead`` → h4_ead mapping, so they
retrieved only H-4 EAD (c)(26) policy (Volume 10 A/B) instead of
parole (c)(11) or special-immigrant-juvenile work authorization.

First-turn parole and SIJ premium-processing questions fell through to
``premium processing`` → h1b.

7+ word parole / SIJ questions without other keywords were blocked as
out of scope.
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


def test_detects_parole_and_sij():
    assert detect_visa_in_query("What are humanitarian parole EAD eligibility requirements?") == "parole"
    assert detect_visa_in_query("What are the official humanitarian parole eligibility requirements?") == "parole"
    assert detect_visa_in_query("parole in place for military families") == "parole"
    assert detect_visa_in_query("What are parolee EAD eligibility requirements?") == "parole"
    assert detect_visa_in_query("What are SIJ EAD eligibility requirements?") == "sij"
    assert detect_visa_in_query("What are SIJS eligibility requirements?") == "sij"
    assert detect_visa_in_query("What are the official SIJ eligibility requirements?") == "sij"
    assert detect_visa_in_query("What are the special immigrant juvenile eligibility requirements?") == "sij"


def test_does_not_confuse_adjacent_codes():
    assert detect_visa_in_query("What are H-1B specialty occupation requirements?") == "h1b"
    assert detect_visa_in_query("What are F-1 student visa requirements?") == "f1"
    assert detect_visa_in_query("What are asylum eligibility requirements?") == "asylum"
    # Explicit asylum and green card still win when parole is also mentioned.
    assert detect_visa_in_query("asylum eligibility after parole") == "asylum"
    assert detect_visa_in_query("advance parole for a pending green card") == "green_card"
    # Named SIJ stays SIJ even when the question also says green card.
    assert detect_visa_in_query("What are SIJ green card eligibility requirements?") == "sij"
    assert detect_visa_in_query("H-1B parole eligibility requirements") == "h1b"


def test_parole_after_h1b_is_new_topic_not_follow_up():
    query = "What are humanitarian parole eligibility requirements?"
    assert not is_follow_up_query(query, has_prior_turns=True)
    assert is_new_topic_query(query, H1B_SESSION)
    expanded = expand_query_for_retrieval(query, H1B_SESSION, new_topic=True)
    assert expanded == query
    assert "H-1B" not in expanded


def test_sij_after_h1b_is_new_topic_not_follow_up():
    query = "What are SIJ eligibility requirements?"
    assert not is_follow_up_query(query, has_prior_turns=True)
    assert is_new_topic_query(query, H1B_SESSION)
    expanded = expand_query_for_retrieval(query, H1B_SESSION, new_topic=True)
    assert expanded == query
    assert "H-1B" not in expanded


def test_special_immigrant_juvenile_after_h1b_is_new_topic():
    query = "What are the special immigrant juvenile eligibility requirements?"
    assert is_new_topic_query(query, H1B_SESSION)
    assert expand_query_for_retrieval(query, H1B_SESSION, new_topic=True) == query


def test_metadata_filter_detects_parole_and_sij_not_inferred_codes():
    filt = MetadataFilter()
    assert filt._detect_visa_type("What are humanitarian parole EAD eligibility requirements?") == "parole"
    assert filt._detect_visa_type("What are parolee EAD eligibility requirements?") == "parole"
    assert filt._detect_visa_type("What are the official humanitarian parole eligibility requirements?") == "parole"
    assert filt._detect_visa_type("What are SIJ EAD eligibility requirements?") == "sij"
    assert filt._detect_visa_type("What are SIJS eligibility requirements?") == "sij"
    assert filt._detect_visa_type("special immigrant juvenile status") == "sij"
    assert filt._detect_visa_type("What are H-1B specialty occupation requirements?") == "h1b"
    assert filt._detect_visa_type("advance parole for a pending green card") == "green_card"
    assert filt._detect_visa_type("What are SIJ green card eligibility requirements?") == "sij"
    assert filt._detect_visa_type("asylum eligibility after parole") == "asylum"


def test_first_turn_parole_ead_does_not_infer_h4_ead():
    """Named parole EAD must not exclusive-filter to H-4 EAD (c)(26) policy."""
    filt = MetadataFilter()
    query = "What are humanitarian parole EAD eligibility requirements?"
    detected = filt._detect_visa_type(query)
    assert detected == "parole"
    assert filt._infer_visa_from_topic(query) == "h4_ead"
    assert detected != "h4_ead"


def test_first_turn_parolee_ead_does_not_infer_h4_ead():
    filt = MetadataFilter()
    query = "What are parolee EAD eligibility requirements?"
    detected = filt._detect_visa_type(query)
    assert detected == "parole"
    assert filt._infer_visa_from_topic(query) == "h4_ead"
    assert detected != "h4_ead"


def test_first_turn_sij_ead_does_not_infer_h4_ead():
    """Named SIJ EAD must not exclusive-filter to H-4 EAD (c)(26) policy."""
    filt = MetadataFilter()
    query = "What are SIJ EAD eligibility requirements?"
    detected = filt._detect_visa_type(query)
    assert detected == "sij"
    assert filt._infer_visa_from_topic(query) == "h4_ead"
    assert detected != "h4_ead"


def test_first_turn_parole_premium_processing_does_not_infer_h1b():
    filt = MetadataFilter()
    query = "What is humanitarian parole premium processing?"
    detected = filt._detect_visa_type(query)
    assert detected == "parole"
    assert filt._infer_visa_from_topic(query) == "h1b"
    assert detected != "h1b"


def test_first_turn_sij_premium_processing_does_not_infer_h1b():
    filt = MetadataFilter()
    query = "What is SIJ premium processing?"
    detected = filt._detect_visa_type(query)
    assert detected == "sij"
    assert filt._infer_visa_from_topic(query) == "h1b"
    assert detected != "h1b"


def test_moderator_allows_parole_and_sij_questions():
    moderator = ContentModerator()
    for query in (
        "What are humanitarian parole EAD eligibility requirements?",
        "What are the official humanitarian parole eligibility requirements?",
        "What are parolee EAD eligibility requirements?",
        "What is humanitarian parole premium processing?",
        "What are SIJ EAD eligibility requirements?",
        "What are the official SIJ eligibility requirements?",
        "What are the special immigrant juvenile eligibility requirements?",
        "What is SIJ premium processing?",
    ):
        result = moderator.moderate(query)
        assert result.is_safe, query
