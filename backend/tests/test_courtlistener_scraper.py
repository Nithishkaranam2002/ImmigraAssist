"""Unit tests for CourtListener query building and relevance filtering."""
import pytest
from app.scrapers.courtlistener_scraper import CourtCase, CourtListenerScraper


@pytest.fixture
def scraper():
    return CourtListenerScraper()


def test_build_search_includes_question_topic_not_only_visa(scraper):
    q = "What forms are required for H-4 EAD eligibility?"
    terms = scraper._build_search_query(q, "h4_ead")
    assert "forms" in terms.lower() or "filing" in terms.lower()
    assert "H-4" in terms or "EAD" in terms


def test_h4_ead_detected_from_ead_in_query(scraper):
    q = "Can my spouse get an EAD on H-4?"
    terms = scraper._build_search_query(q, "h4")
    assert "EAD" in terms or "employment" in terms


def test_relevance_penalizes_asylum_for_h1b(scraper):
    case = CourtCase(
        case_name="Matter of Negusie",
        case_id="1",
        court="bia",
        court_name="BIA",
        date_decided="2008-01-01",
        citation=None,
        summary="Asylum and persecution withholding analysis for respondent.",
        full_text_url="https://example.com",
        courtlistener_url="https://example.com",
        relevance_score=0.9,
        visa_types=["asylum"],
        outcome=None,
    )
    score = scraper._relevance_score(
        case,
        scraper._tokenize("H-1B cap lottery registration requirements"),
        "h1b",
    )
    assert score < 0.22


def test_relevance_boosts_matching_h4_ead_case(scraper):
    case = CourtCase(
        case_name="Matter of Example H-4 EAD",
        case_id="2",
        court="bia",
        court_name="BIA",
        date_decided="2020-01-01",
        citation=None,
        summary="H-4 spouse employment authorization under (c)(26) and Form I-765.",
        full_text_url="https://example.com",
        courtlistener_url="https://example.com",
        relevance_score=0.5,
        visa_types=["h4_ead"],
        outcome="granted",
    )
    score = scraper._relevance_score(
        case,
        scraper._tokenize("What forms for H-4 EAD eligibility?"),
        "h4_ead",
    )
    assert score >= 0.22


def test_stem_opt_query_drops_unrelated_cases(scraper):
    unrelated = CourtCase(
        case_name="Students For Fair Admissions Inc v. President",
        case_id="x",
        court="bia",
        court_name="AAO",
        date_decided=None,
        citation=None,
        summary="Affirmative action challenge unrelated to student visas.",
        full_text_url="https://example.com",
        courtlistener_url="https://example.com",
        relevance_score=0.95,
        visa_types=[],
        outcome=None,
    )
    result = scraper._rank_and_filter(
        [unrelated],
        "How long is the STEM OPT extension?",
        "f1",
        3,
    )
    assert result == []


def test_rank_and_filter_drops_irrelevant(scraper):
    good = CourtCase(
        case_name="H-4 EAD employment authorization",
        case_id="a",
        court="bia",
        court_name="BIA",
        date_decided=None,
        citation=None,
        summary="H-4 EAD I-765 eligibility requirements.",
        full_text_url="https://example.com",
        courtlistener_url="https://example.com",
        relevance_score=0.5,
        visa_types=["h4_ead"],
        outcome=None,
    )
    bad = CourtCase(
        case_name="Matter of Unrelated Naturalization",
        case_id="b",
        court="bia",
        court_name="BIA",
        date_decided=None,
        citation=None,
        summary="Naturalization and citizenship requirements N-400.",
        full_text_url="https://example.com",
        courtlistener_url="https://example.com",
        relevance_score=0.9,
        visa_types=[],
        outcome=None,
    )
    result = scraper._rank_and_filter(
        [bad, good],
        "What are H-4 EAD requirements?",
        "h4_ead",
        2,
    )
    assert len(result) >= 1
    assert result[0].case_id == "a"
