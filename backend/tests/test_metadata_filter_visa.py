"""Regression tests for query visa detection / topic inference."""
from app.retrieval.metadata_filter import MetadataFilter


def test_h4_ead_detected_before_plain_h4():
    mf = MetadataFilter()
    assert mf._detect_visa_type("What are the H-4 EAD requirements?") == "h4_ead"
    assert mf._detect_visa_type("H4 EAD filing checklist") == "h4_ead"


def test_h4_with_ead_terms_upgraded_to_h4_ead():
    mf = MetadataFilter()
    detected = mf._detect_visa_type("H-4 employment authorization evidence")
    assert detected == "h4"
    assert mf._upgrade_h4_ead("H-4 employment authorization evidence", detected) == "h4_ead"


def test_bare_employment_authorization_not_forced_to_h4_ead():
    """Generic EAD language covers OPT/asylum/AOS — must not force H-4 EAD corpus."""
    mf = MetadataFilter()
    assert mf._detect_visa_type("employment authorization for asylees") is None
    assert mf._infer_visa_from_topic("employment authorization for asylees") is None
    assert mf._infer_visa_from_topic("What is an EAD?") is None
    assert mf._infer_visa_from_topic("work auth while I-485 pending") is None


def test_h4_plus_ead_topic_still_infers_h4_ead():
    mf = MetadataFilter()
    assert mf._infer_visa_from_topic("dependent H-4 spouse need employment authorization") == "h4_ead"


def test_year_range_parses_full_year_not_century_prefix():
    """Capturing only (19|20) previously turned 2018 into year_min=20."""
    mf = MetadataFilter()
    assert mf._detect_year_range("cases after 2018") == (2018, None)
    assert mf._detect_year_range("cases between 2015 and 2020") == (2015, 2020)
