"""Ingested H-4 EAD documents must not be tagged as plain H-4."""
from app.ingestion.classifier import DocumentClassifier


def test_h4_ead_document_tagged_h4_ead_not_h4():
    clf = DocumentClassifier()
    text = (
        "This chapter covers H-4 EAD eligibility for certain dependent spouses "
        "under 8 CFR 274a.12(c)(26) and Form I-765."
    )
    assert clf._detect_visa_type(text) == "h4_ead"


def test_plain_h4_document_still_tagged_h4():
    clf = DocumentClassifier()
    text = "H-4 dependent spouses may apply to change or extend status on Form I-539."
    assert clf._detect_visa_type(text) == "h4"
