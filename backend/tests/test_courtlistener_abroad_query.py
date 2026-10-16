"""CourtListener consular phrases must not rewrite every abroad question."""

import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("MILVUS_HOST", "localhost")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app.scrapers.courtlistener_scraper import CourtListenerScraper


def _terms(query: str, visa_type: str | None) -> str:
    return CourtListenerScraper()._build_search_query(query, visa_type).lower()


def test_h1b_travel_abroad_during_pending_extension_is_not_consular():
    terms = _terms(
        "Can an H-1B worker travel abroad while an extension of stay is pending?",
        "h1b",
    )
    assert "consular" not in terms
    assert "visa stamp" not in terms
    assert "h-1b" in terms
    assert "travel" in terms
    assert "abroad" in terms
    assert "stay" in terms
    assert "pending" in terms


def test_lpr_abandonment_abroad_keeps_the_one_year_limit():
    """Consular phrases used to fill the 10-term cap and drop "year"."""
    terms = _terms(
        "Does a lawful permanent resident abandon status by living abroad for a continuous year?",
        None,
    )
    assert "consular" not in terms
    assert "visa stamp" not in terms
    assert "abandon" in terms
    assert "resident" in terms
    assert "year" in terms


def test_advance_parole_travel_abroad_is_not_consular():
    terms = _terms(
        "Can the client travel abroad while advance parole is pending?",
        None,
    )
    assert "consular" not in terms
    assert "visa stamp" not in terms
    assert "advance" in terms
    assert "parole" in terms
    assert "pending" in terms


def test_f1_study_abroad_keeps_the_semester():
    terms = _terms(
        "Can an F-1 student leave to study abroad for one semester?",
        "f1",
    )
    assert "consular" not in terms
    assert "visa stamp" not in terms
    assert "f-1" in terms
    assert "study" in terms
    assert "abroad" in terms
    assert "semester" in terms


def test_consular_processing_still_searches_that_doctrine():
    terms = _terms(
        "What is consular processing versus adjustment of status?",
        None,
    )
    assert "consular processing" in terms
    assert "visa stamp" in terms
    assert "adjustment" in terms


def test_visa_stamp_still_searches_consular_processing():
    terms = _terms(
        "When does the client get a visa stamp after the interview?",
        None,
    )
    assert "consular processing" in terms
    assert "visa stamp" in terms
    assert "interview" in terms
