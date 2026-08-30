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


def test_consular_green_card_query_rejects_i485_aos_case():
    text = (
        "The applicant's Form I-485 adjustment of status was denied "
        "for failure to maintain lawful status."
    )
    score = score_case_text(
        text,
        "What is the process for consular processing a family-based green card?",
        "green_card",
    )
    assert score < 0.28


def test_consular_green_card_query_accepts_nvc_case():
    text = (
        "The National Visa Center scheduled a consular processing interview "
        "after the DS-260 immigrant visa application was filed."
    )
    score = score_case_text(
        text,
        "What is the process for consular processing a family-based green card?",
        "green_card",
    )
    assert score >= 0.28


def test_aos_green_card_query_still_accepts_i485_case():
    text = (
        "The applicant's Form I-485 adjustment of status was denied "
        "for failure to maintain lawful status."
    )
    score = score_case_text(
        text,
        "What evidence is required for I-485 adjustment of status?",
        "green_card",
    )
    assert score >= 0.28


def test_compare_aos_vs_consular_does_not_zero_out_either_path():
    aos_text = (
        "The applicant's Form I-485 adjustment of status was denied "
        "for failure to maintain lawful status."
    )
    consular_text = (
        "The National Visa Center scheduled a consular processing interview "
        "after the DS-260 immigrant visa application was filed."
    )
    q = "Explain adjustment of status vs consular processing for a green card"
    assert score_case_text(aos_text, q, "green_card") >= 0.28
    assert score_case_text(consular_text, q, "green_card") >= 0.28
