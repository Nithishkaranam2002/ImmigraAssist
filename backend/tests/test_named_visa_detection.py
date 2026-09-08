"""Named EB-3 / TN / E-2 detection for exclusive corpus filtering."""
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


def test_detects_eb3_tn_and_e2_for_corpus_filter():
    filt = MetadataFilter()
    assert filt._detect_visa_type("What are the EB-3 eligibility requirements?") == "eb3"
    assert filt._detect_visa_type("What are the TN visa requirements?") == "tn"
    assert filt._detect_visa_type("What is the E-2 treaty investor process?") == "e2"


def test_eb2_not_confused_with_e2():
    filt = MetadataFilter()
    assert filt._detect_visa_type("What are EB-2 NIW requirements?") == "eb2"
    assert filt._detect_visa_type("What are H-1B specialty occupation requirements?") == "h1b"
