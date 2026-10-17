"""CourtListener 180-day phrases must not rewrite every 180-day period."""

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


def test_unlawful_presence_180_days_keeps_the_three_year_bar():
    """Status-extension phrases used to fill the 10-term cap and drop "bar"."""
    terms = _terms(
        "Does accruing 180 days of unlawful presence before departure "
        "trigger the statutory three-year bar?",
        None,
    )
    assert "180-day extension" not in terms
    assert "status extension" not in terms
    assert "unlawful" in terms
    assert "presence" in terms
    assert "departure" in terms
    assert "three-year" in terms
    assert "bar" in terms


def test_unlawful_presence_180_days_is_not_a_status_extension():
    terms = _terms(
        "Does 180 days of unlawful presence trigger the three-year bar?",
        None,
    )
    assert "180-day extension" not in terms
    assert "status extension" not in terms
    assert "180" in terms
    assert "unlawful" in terms
    assert "presence" in terms
    assert "three-year" in terms
    assert "bar" in terms


def test_180_day_extension_still_searches_that_doctrine():
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
    assert "automatic" in terms
    assert "employment" in terms
    assert "authorization" in terms
