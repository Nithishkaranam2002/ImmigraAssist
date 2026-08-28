"""H-4 EAD detection must not poison generic EAD or H-4 status queries."""
import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("MILVUS_HOST", "localhost")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("OPENAI_API_KEY", "test")

from app.retrieval.metadata_filter import MetadataFilter


def _filter() -> MetadataFilter:
    return MetadataFilter()


def test_research_hub_h4_ead_prompt_detects_h4_ead_not_h4():
    """Suggested hub question: 'What are the requirements for H4 EAD eligibility?'"""
    filt = _filter()
    query = "What are the requirements for H4 EAD eligibility?"
    assert filt._detect_visa_type(query) == "h4_ead"
    assert filt._infer_visa_from_topic(query) is None


def test_hyphenated_h4_ead_detects_h4_ead_not_h4():
    filt = _filter()
    query = "What are the H-4 EAD eligibility requirements?"
    assert filt._detect_visa_type(query) == "h4_ead"


def test_plain_h4_status_still_detects_h4():
    filt = _filter()
    query = "What are H-4 dependent spouse status requirements?"
    assert filt._detect_visa_type(query) == "h4"


def test_i485_pending_work_auth_does_not_infer_h4_ead():
    filt = _filter()
    query = "Can I get work authorization while my I-485 is pending?"
    assert filt._detect_visa_type(query) is None
    assert filt._infer_visa_from_topic(query) is None


def test_generic_ead_does_not_infer_h4_ead():
    filt = _filter()
    query = "How do I apply for an Employment Authorization Document?"
    assert filt._detect_visa_type(query) is None
    assert filt._infer_visa_from_topic(query) is None


def test_c26_category_still_infers_h4_ead():
    filt = _filter()
    query = "What evidence is required for I-765 category (c)(26)?"
    assert filt._detect_visa_type(query) is None
    assert filt._infer_visa_from_topic(query) == "h4_ead"


def test_opt_work_authorization_still_infers_f1():
    filt = _filter()
    assert filt._infer_visa_from_topic("What are the OPT work authorization rules?") == "f1"
