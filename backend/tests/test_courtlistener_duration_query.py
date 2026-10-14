"""CourtListener duration phrases must not rewrite non-OPT questions as STEM OPT."""

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


def test_h1b_stay_limit_is_not_stem_opt():
    terms = _terms(
        "How long can an H-1B beneficiary remain in the United States?",
        "h1b",
    )
    assert "stem opt" not in terms
    assert "24 month" not in terms
    assert "opt period" not in terms
    assert "h-1b" in terms
    assert "beneficiary" in terms


def test_l1_duration_is_not_stem_opt():
    terms = _terms("What is the maximum duration of L-1A status?", "l1")
    assert "stem opt" not in terms
    assert "24 month" not in terms
    assert "opt period" not in terms
    assert "l-1" in terms
    assert "duration" in terms


def test_unlawful_presence_months_are_not_stem_opt():
    terms = _terms(
        "How many months of unlawful presence trigger the ten-year bar?",
        None,
    )
    assert "stem opt" not in terms
    assert "24 month" not in terms
    assert "opt period" not in terms
    assert "unlawful" in terms
    assert "presence" in terms


def test_stem_opt_duration_still_searches_the_extension():
    """A STEM OPT timing question must keep the 24-month phrases."""
    terms = _terms("How long is the STEM OPT extension?", None)
    assert "24 month" in terms
    assert "stem opt duration" in terms
    assert "opt period" in terms


def test_explicit_24_month_opt_still_searches_the_extension():
    # visa_type is unset so the F-1 OPT early return does not replace the query.
    terms = _terms("Is the 24-month OPT extension still available?", None)
    assert "24 month" in terms
    assert "stem opt duration" in terms
