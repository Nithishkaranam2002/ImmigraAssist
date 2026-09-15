"""DACA / VAWA / refugee must not inherit the prior exclusive visa corpus.

DACA, VAWA, and refugee were omitted from detect_visa_in_query and
MetadataFilter, so an H-1B session treated those named questions as
visaless follow-ups and exclusive-filtered to H-1B law.

First-turn DACA / VAWA / refugee EAD questions also fell through to
_infer_visa_from_topic's generic ``ead`` → h4_ead mapping, so they
retrieved only H-4 EAD (c)(26) policy (Volume 10 A/B) instead of
(c)(33) DACA, VAWA self-petitioner, or refugee/asylee EAD rules.

First-turn DACA premium-processing questions fell through to
``premium processing`` → h1b.

``asylee`` was also omitted from the asylum detector, so asylee EAD
questions exclusive-filtered to H-4 EAD.

7+ word DACA / VAWA / refugee questions without other keywords were
blocked as out of scope.
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
    text="Q: asylum?\nA: ...",
    last_query="What are asylum eligibility requirements?",
    last_visa_type="asylum",
    turn_count=1,
)


def test_detects_daca_vawa_and_refugee():
    assert detect_visa_in_query("What are DACA EAD eligibility requirements?") == "daca"
    assert detect_visa_in_query("deferred action for childhood arrivals") == "daca"
    assert detect_visa_in_query("What are I-821D eligibility requirements?") == "daca"
    assert detect_visa_in_query("What are the official DACA eligibility requirements?") == "daca"
    assert detect_visa_in_query("What are VAWA EAD eligibility requirements?") == "vawa"
    assert detect_visa_in_query("violence against women act self petition") == "vawa"
    assert detect_visa_in_query("What are the official VAWA eligibility requirements?") == "vawa"
    assert detect_visa_in_query("What are refugee EAD eligibility requirements?") == "refugee"
    assert detect_visa_in_query("What are the official refugee eligibility requirements?") == "refugee"


def test_asylee_maps_to_asylum_not_h4_ead():
    assert detect_visa_in_query("What are asylee EAD eligibility requirements?") == "asylum"
    assert detect_visa_in_query("What are asylum eligibility requirements?") == "asylum"


def test_does_not_confuse_adjacent_codes():
    assert detect_visa_in_query("What are H-1B specialty occupation requirements?") == "h1b"
    assert detect_visa_in_query("What are F-1 student visa requirements?") == "f1"
    assert detect_visa_in_query("What are asylum eligibility requirements?") == "asylum"
    # Explicit asylum still wins when refugee is also mentioned.
    assert detect_visa_in_query("asylum eligibility for a refugee") == "asylum"


def test_daca_after_h1b_is_new_topic_not_follow_up():
    query = "What are DACA eligibility requirements?"
    assert not is_follow_up_query(query, has_prior_turns=True)
    assert is_new_topic_query(query, H1B_SESSION)
    expanded = expand_query_for_retrieval(query, H1B_SESSION, new_topic=True)
    assert expanded == query
    assert "H-1B" not in expanded


def test_vawa_after_h1b_is_new_topic_not_follow_up():
    query = "What are VAWA eligibility requirements?"
    assert not is_follow_up_query(query, has_prior_turns=True)
    assert is_new_topic_query(query, H1B_SESSION)
    expanded = expand_query_for_retrieval(query, H1B_SESSION, new_topic=True)
    assert expanded == query
    assert "H-1B" not in expanded


def test_refugee_after_h1b_is_new_topic_not_follow_up():
    query = "What are refugee eligibility requirements?"
    assert not is_follow_up_query(query, has_prior_turns=True)
    assert is_new_topic_query(query, H1B_SESSION)
    expanded = expand_query_for_retrieval(query, H1B_SESSION, new_topic=True)
    assert expanded == query
    assert "H-1B" not in expanded


def test_daca_and_vawa_after_asylum_are_new_topics():
    """DACA and VAWA must not inherit the Volume 4 asylum corpus."""
    daca = "What are DACA eligibility requirements?"
    vawa = "What are VAWA eligibility requirements?"
    assert is_new_topic_query(daca, ASYLUM_SESSION)
    assert is_new_topic_query(vawa, ASYLUM_SESSION)
    assert expand_query_for_retrieval(daca, ASYLUM_SESSION, new_topic=True) == daca
    assert expand_query_for_retrieval(vawa, ASYLUM_SESSION, new_topic=True) == vawa


def test_metadata_filter_detects_daca_vawa_refugee_not_inferred_codes():
    filt = MetadataFilter()
    assert filt._detect_visa_type("What are DACA EAD eligibility requirements?") == "daca"
    assert filt._detect_visa_type("What are the official DACA eligibility requirements?") == "daca"
    assert filt._detect_visa_type("What are I-821D eligibility requirements?") == "daca"
    assert filt._detect_visa_type("What are VAWA EAD eligibility requirements?") == "vawa"
    assert filt._detect_visa_type("violence against women act self petition") == "vawa"
    assert filt._detect_visa_type("What are refugee EAD eligibility requirements?") == "refugee"
    assert filt._detect_visa_type("What are asylee EAD eligibility requirements?") == "asylum"
    assert filt._detect_visa_type("What are H-1B specialty occupation requirements?") == "h1b"
    assert filt._detect_visa_type("What are asylum eligibility requirements?") == "asylum"


def test_first_turn_daca_ead_does_not_infer_h4_ead():
    """Named DACA EAD must not exclusive-filter to H-4 EAD (c)(26) policy."""
    filt = MetadataFilter()
    query = "What are DACA EAD eligibility requirements?"
    detected = filt._detect_visa_type(query)
    assert detected == "daca"
    assert filt._infer_visa_from_topic(query) == "h4_ead"
    assert detected != "h4_ead"


def test_first_turn_vawa_ead_does_not_infer_h4_ead():
    """Named VAWA EAD must not exclusive-filter to H-4 EAD (c)(26) policy."""
    filt = MetadataFilter()
    query = "What are VAWA EAD eligibility requirements?"
    detected = filt._detect_visa_type(query)
    assert detected == "vawa"
    assert filt._infer_visa_from_topic(query) == "h4_ead"
    assert detected != "h4_ead"


def test_first_turn_refugee_ead_does_not_infer_h4_ead():
    """Named refugee EAD must not exclusive-filter to H-4 EAD (c)(26) policy."""
    filt = MetadataFilter()
    query = "What are refugee EAD eligibility requirements?"
    detected = filt._detect_visa_type(query)
    assert detected == "refugee"
    assert filt._infer_visa_from_topic(query) == "h4_ead"
    assert detected != "h4_ead"


def test_first_turn_asylee_ead_does_not_infer_h4_ead():
    """Named asylee EAD must retrieve asylum corpus, not H-4 EAD (c)(26)."""
    filt = MetadataFilter()
    query = "What are asylee EAD eligibility requirements?"
    detected = filt._detect_visa_type(query)
    assert detected == "asylum"
    assert filt._infer_visa_from_topic(query) == "h4_ead"
    assert detected != "h4_ead"


def test_first_turn_daca_premium_processing_does_not_infer_h1b():
    """Named DACA premium processing must not exclusive-filter to H-1B law."""
    filt = MetadataFilter()
    query = "What is DACA premium processing?"
    detected = filt._detect_visa_type(query)
    assert detected == "daca"
    assert filt._infer_visa_from_topic(query) == "h1b"
    assert detected != "h1b"


def test_moderator_allows_daca_vawa_refugee_questions():
    moderator = ContentModerator()
    for query in (
        "What are DACA EAD eligibility requirements?",
        "What are the official DACA eligibility requirements?",
        "What are I-821D eligibility requirements?",
        "What are VAWA EAD eligibility requirements?",
        "What are the official VAWA eligibility requirements?",
        "What are refugee EAD eligibility requirements?",
        "What are the official refugee eligibility requirements?",
        "What are asylee EAD eligibility requirements?",
        "What is DACA premium processing?",
    ):
        result = moderator.moderate(query)
        assert result.is_safe, query
