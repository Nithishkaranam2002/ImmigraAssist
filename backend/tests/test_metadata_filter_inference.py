"""Topic inference must not treat the English verb 'opt for/to/out' as F-1 OPT."""
from app.retrieval.metadata_filter import MetadataFilter


def _filter() -> MetadataFilter:
    return MetadataFilter()


def test_opt_for_consular_processing_does_not_infer_f1():
    """Common AOS vs consular question must not retrieve only the F-1/STEM OPT corpus."""
    filt = _filter()
    query = "Should I opt for consular processing or adjustment of status?"
    assert filt._detect_visa_type(query) is None
    assert filt._infer_visa_from_topic(query) is None


def test_opt_to_file_does_not_infer_f1():
    filt = _filter()
    query = "Should I opt to file I-485 now or wait for the priority date?"
    assert filt._detect_visa_type(query) is None
    assert filt._infer_visa_from_topic(query) is None


def test_opt_out_does_not_infer_f1():
    filt = _filter()
    query = "Can I opt out of the immigrant visa interview?"
    assert filt._detect_visa_type(query) is None
    assert filt._infer_visa_from_topic(query) is None


def test_opt_program_still_infers_f1():
    filt = _filter()
    assert filt._infer_visa_from_topic("What are the OPT work authorization rules?") == "f1"
    assert filt._infer_visa_from_topic("How long is the STEM OPT extension?") == "f1"


def test_named_f1_opt_still_detects_f1():
    filt = _filter()
    query = "What is OPT for F-1 students?"
    assert filt._detect_visa_type(query) == "f1"
