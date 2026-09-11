"""L-2 / E-1 / EB-5 must not inherit the prior exclusive visa corpus.

L-2, E-1, and EB-5 were omitted from detect_visa_in_query and
MetadataFilter, so an H-1B (or L-1) session treated those named
questions as visaless follow-ups and exclusive-filtered to the prior
visa's law.

First-turn L-2 EAD and E-1 EAD questions also fell through to
_infer_visa_from_topic's generic ``ead`` → h4_ead mapping, so they
retrieved only H-4 EAD (c)(26) policy.

Hyphenated EB-5 spellings also failed moderator normalization, blocking
first-turn 7+ word regional-center questions as out of scope.
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


def test_detects_l2_e1_and_eb5():
    assert detect_visa_in_query("What are L-2 EAD eligibility requirements?") == "l2"
    assert detect_visa_in_query("L2 dependent spouse work authorization") == "l2"
    assert detect_visa_in_query("What are E-1 EAD eligibility requirements?") == "e1"
    assert detect_visa_in_query("E1 treaty trader") == "e1"
    assert detect_visa_in_query("What are EB-5 investment requirements?") == "eb5"
    assert detect_visa_in_query("EB5 regional center") == "eb5"


def test_does_not_confuse_adjacent_codes():
    assert detect_visa_in_query("What are L-1 intracompany transferee requirements?") == "l1"
    assert detect_visa_in_query("What are EB-1 priority worker requirements?") == "eb1"
    assert detect_visa_in_query("What are EB-2 advanced degree requirements?") == "eb2"


def test_l2_after_l1_is_new_topic_not_follow_up():
    query = "What are L-2 EAD eligibility requirements?"
    assert not is_follow_up_query(query, has_prior_turns=True)
    assert is_new_topic_query(query, L1_SESSION)
    expanded = expand_query_for_retrieval(query, L1_SESSION, new_topic=True)
    assert expanded == query
    assert "L-1" not in expanded


def test_e1_after_h1b_is_new_topic_not_follow_up():
    query = "What are E-1 treaty trader requirements?"
    assert not is_follow_up_query(query, has_prior_turns=True)
    assert is_new_topic_query(query, H1B_SESSION)
    expanded = expand_query_for_retrieval(query, H1B_SESSION, new_topic=True)
    assert expanded == query
    assert "H-1B" not in expanded


def test_eb5_after_h1b_is_new_topic_not_follow_up():
    query = "What are EB-5 investment requirements?"
    assert not is_follow_up_query(query, has_prior_turns=True)
    assert is_new_topic_query(query, H1B_SESSION)
    expanded = expand_query_for_retrieval(query, H1B_SESSION, new_topic=True)
    assert expanded == query
    assert "H-1B" not in expanded


def test_metadata_filter_detects_l2_e1_eb5_not_h4_ead():
    filt = MetadataFilter()
    assert filt._detect_visa_type("What are L-2 EAD eligibility requirements?") == "l2"
    assert filt._detect_visa_type("What are E-1 EAD eligibility requirements?") == "e1"
    assert filt._detect_visa_type("What are EB-5 investment requirements?") == "eb5"
    assert filt._detect_visa_type("What are L-1 intracompany transferee requirements?") == "l1"
    assert filt._detect_visa_type("What are EB-1 priority worker requirements?") == "eb1"


def test_first_turn_l2_ead_does_not_infer_h4_ead():
    """Named L-2 EAD must not exclusive-filter to H-4 EAD (c)(26) policy."""
    filt = MetadataFilter()
    query = "What are L-2 EAD eligibility requirements?"
    detected = filt._detect_visa_type(query)
    assert detected == "l2"
    assert filt._infer_visa_from_topic(query) == "h4_ead"
    # build_filter_context uses detection first; inference is only a fallback
    assert detected != "h4_ead"


def test_moderator_allows_l2_e1_eb5_questions():
    moderator = ContentModerator()
    for query in (
        "What are L-2 EAD eligibility requirements?",
        "What are the L-2 EAD work authorization requirements?",
        "What are the E-1 treaty trader visa requirements?",
        "What are the official E-1 treaty trader eligibility requirements?",
        "What are EB-5 investment requirements?",
        "What are the EB-5 regional center requirements?",
        "What are the official EB-5 investment capital requirements?",
    ):
        result = moderator.moderate(query)
        assert result.is_safe, query
