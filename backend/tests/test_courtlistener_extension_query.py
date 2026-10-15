"""CourtListener 180-day phrases must not rewrite every extension question."""

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


def test_h1b_six_year_extension_is_not_180_day():
    terms = _terms(
        "What is the maximum H-1B extension beyond the six-year statutory limit?",
        "h1b",
    )
    assert "180-day" not in terms
    assert "status extension" not in terms
    assert "h-1b" in terms
    assert "extension" in terms
    assert "six-year" in terms
    assert "statutory" in terms
    assert "limit" in terms


def test_ac21_extension_keeps_the_six_year_limit():
    """180-day phrases used to fill the 10-term cap and drop "six" and "years"."""
    terms = _terms(
        "Can an H-1B worker get an extension beyond six years under AC21?",
        "h1b",
    )
    assert "180-day" not in terms
    assert "status extension" not in terms
    assert "h-1b" in terms
    assert "ac21" in terms
    assert "six" in terms


def test_l1_extension_of_stay_is_not_180_day():
    terms = _terms("How do I file an L-1 extension of stay?", "l1")
    assert "180-day" not in terms
    assert "status extension" not in terms
    assert "l-1" in terms
    assert "extension" in terms
    assert "stay" in terms


def test_i751_extension_is_not_180_day():
    terms = _terms(
        "Does the I-751 extension letter extend conditional permanent residence?",
        None,
    )
    assert "180-day" not in terms
    assert "status extension" not in terms
    assert "i-751" in terms
    assert "conditional" in terms
    assert "residence" in terms


def test_stem_opt_extension_is_not_180_day():
    # visa_type is unset so the F-1 OPT early return does not replace the query.
    terms = _terms("How long is the STEM OPT extension?", None)
    assert "180-day" not in terms
    assert "status extension" not in terms
    assert "stem opt" in terms


def test_explicit_180_day_extension_still_searches_that_doctrine():
    terms = _terms("Can you explain the 180 day extension?", None)
    assert "180-day extension" in terms
    assert "status extension" in terms


def test_180_day_automatic_extension_still_searches_that_doctrine():
    terms = _terms(
        "What is the 180-day automatic extension of employment authorization?",
        None,
    )
    assert "180-day extension" in terms
    assert "status extension" in terms
    assert "employment" in terms
    assert "authorization" in terms
