"""Topic inference must not force the EB-2 corpus onto PERM / TLC questions."""
from app.retrieval.metadata_filter import MetadataFilter


def _filter() -> MetadataFilter:
    return MetadataFilter()


def test_generic_perm_does_not_infer_eb2():
    """Research hub suggestion: 'What is the PERM labor certification process?'"""
    filt = _filter()
    query = "What is the PERM labor certification process?"
    assert filt._detect_visa_type(query) is None
    assert filt._infer_visa_from_topic(query) is None


def test_h2a_labor_certification_does_not_infer_eb2():
    filt = _filter()
    query = "What is the labor certification process for H-2A agricultural workers?"
    assert filt._detect_visa_type(query) is None
    assert filt._infer_visa_from_topic(query) is None


def test_eb3_perm_does_not_infer_eb2():
    filt = _filter()
    query = "What is PERM labor certification for EB-3 workers?"
    assert filt._detect_visa_type(query) is None
    assert filt._infer_visa_from_topic(query) is None


def test_named_eb2_perm_still_detects_eb2():
    filt = _filter()
    query = "What is the EB-2 PERM labor certification process?"
    assert filt._detect_visa_type(query) == "eb2"


def test_opt_still_infers_f1():
    filt = _filter()
    assert filt._infer_visa_from_topic("What are the OPT work authorization rules?") == "f1"
