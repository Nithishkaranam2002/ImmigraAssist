"""Topic inference must not force the H-1B corpus onto unrelated programs."""
from app.retrieval.metadata_filter import MetadataFilter


def _filter() -> MetadataFilter:
    return MetadataFilter()


def test_dv_lottery_infers_green_card_not_h1b():
    filt = _filter()
    query = "What is the DV lottery process?"
    assert filt._detect_visa_type(query) is None
    assert filt._infer_visa_from_topic(query) == "green_card"


def test_diversity_visa_infers_green_card():
    filt = _filter()
    query = "Describe the diversity visa program requirements."
    assert filt._infer_visa_from_topic(query) == "green_card"


def test_h2b_cap_does_not_infer_h1b():
    filt = _filter()
    query = "What is the H-2B cap for seasonal workers?"
    assert filt._detect_visa_type(query) is None
    assert filt._infer_visa_from_topic(query) is None


def test_generic_premium_processing_does_not_infer_h1b():
    filt = _filter()
    query = "How does premium processing work?"
    assert filt._detect_visa_type(query) is None
    assert filt._infer_visa_from_topic(query) is None


def test_lca_still_infers_h1b():
    filt = _filter()
    assert filt._infer_visa_from_topic("What must an LCA include?") == "h1b"


def test_named_h1b_lottery_still_detects_h1b():
    filt = _filter()
    query = "What is the H-1B cap and how does the lottery work?"
    assert filt._detect_visa_type(query) == "h1b"
