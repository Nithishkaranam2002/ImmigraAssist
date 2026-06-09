"""Tests for post-retrieval case relevance filtering."""
from app.retrieval.case_relevance import filter_case_chunks, score_case_text
from app.retrieval.hybrid_retriever import RetrievedChunk


def _chunk(text: str, visa_type: str = "") -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="c1",
        document_id="d1",
        text=text,
        section=None,
        clause=None,
        doc_version="",
        visa_type=visa_type,
        source="case",
        score=0.9,
        vector_score=0.9,
        bm25_score=0.8,
    )


def test_stem_opt_query_rejects_h1b_employer_case():
    text = (
        "Stellar IT Solutions petitioned for H-1B specialty occupation "
        "for a software developer position."
    )
    score = score_case_text(
        text,
        "How long is the STEM OPT extension?",
        "f1",
    )
    assert score == 0.0


def test_stem_opt_query_rejects_fair_admissions_case():
    text = "Students for Fair Admissions challenged university affirmative action policies."
    score = score_case_text(
        text,
        "How long is the STEM OPT extension?",
        "f1",
    )
    assert score == 0.0


def test_stem_opt_query_accepts_opt_case():
    text = (
        "The F-1 student sought a 24-month STEM OPT extension after "
        "post-completion OPT under Form I-983 training plan."
    )
    score = score_case_text(
        text,
        "How long is the STEM OPT extension?",
        "f1",
    )
    assert score >= 0.28


def test_stem_opt_accepts_washtech_litigation():
    text = (
        "Washington Alliance of Technology Workers v. U.S. Department of "
        "Homeland Security — challenge to STEM OPT employment rules."
    )
    score = score_case_text(
        text,
        "How long is the STEM OPT extension?",
        "f1",
    )
    assert score >= 0.28


def test_filter_drops_irrelevant_chunks():
    good = _chunk(
        "F-1 STEM OPT extension granted for 24 months under SEVIS reporting rules."
    )
    bad = _chunk("H-1B specialty occupation denial for IT consulting employer.")
    result = filter_case_chunks(
        [bad, good],
        "How long is the STEM OPT extension?",
        "f1",
    )
    assert len(result) == 1
    assert "STEM OPT" in result[0].text
