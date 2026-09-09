"""O-1A / EB-1A subclass suffixes must detect as o1 / eb1.

Word-boundary patterns like ``\\bo[-\\s]?1\\b`` miss official USCIS
designations (O-1A, O-1B, EB-1A, EB-1B, EB-1C), so those questions were
treated as visaless follow-ups and inherited the prior exclusive corpus.
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


def test_detects_o1_and_eb1_subclasses():
    assert detect_visa_in_query("What are the O-1A evidentiary requirements?") == "o1"
    assert detect_visa_in_query("What are the O-1B arts criteria?") == "o1"
    assert detect_visa_in_query("O1A petition evidence") == "o1"
    assert detect_visa_in_query("What are the EB-1A criteria?") == "eb1"
    assert detect_visa_in_query("What are EB-1B outstanding professor requirements?") == "eb1"
    assert detect_visa_in_query("Explain EB-1C multinational manager eligibility") == "eb1"
    assert detect_visa_in_query("EB1A extraordinary ability") == "eb1"


def test_bare_o1_and_eb1_still_detected():
    assert detect_visa_in_query("What are the O-1 extraordinary ability requirements?") == "o1"
    assert detect_visa_in_query("What are EB-1 priority worker requirements?") == "eb1"


def test_o1a_after_h1b_is_new_topic_not_follow_up():
    query = "What are the O-1A evidentiary requirements?"
    assert not is_follow_up_query(query, has_prior_turns=True)
    assert is_new_topic_query(query, H1B_SESSION)
    expanded = expand_query_for_retrieval(query, H1B_SESSION, new_topic=True)
    assert expanded == query
    assert "H-1B" not in expanded


def test_eb1a_after_h1b_is_new_topic_not_follow_up():
    query = "What are the EB-1A criteria?"
    assert not is_follow_up_query(query, has_prior_turns=True)
    assert is_new_topic_query(query, H1B_SESSION)
    expanded = expand_query_for_retrieval(query, H1B_SESSION, new_topic=True)
    assert expanded == query
    assert "H-1B" not in expanded


def test_metadata_filter_detects_subclasses():
    filt = MetadataFilter()
    assert filt._detect_visa_type("What are the O-1A evidentiary requirements?") == "o1"
    assert filt._detect_visa_type("What are the O-1B arts criteria?") == "o1"
    assert filt._detect_visa_type("What are the EB-1A criteria?") == "eb1"
    assert filt._detect_visa_type("Explain EB-1C multinational manager eligibility") == "eb1"
    assert filt._detect_visa_type("What are EB-1 priority worker requirements?") == "eb1"
    assert filt._detect_visa_type("What are H-1B specialty occupation requirements?") == "h1b"


def test_moderator_allows_subclass_questions():
    moderator = ContentModerator()
    for query in (
        "What are the official O-1A evidentiary requirements?",
        "Explain the EB-1A extraordinary ability criteria in detail",
        "Walk me through typical O-1A extraordinary ability criteria for scientists",
    ):
        result = moderator.moderate(query)
        assert result.is_safe, query
