"""CourtListener removal phrases must not rewrite visa or petition cancellation."""

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


def test_ina_222g_visa_cancellation_is_not_removal_proceedings():
    """Deportation phrases used to lead the query and drop "travel"."""
    terms = _terms(
        "Does a consular officer's visa cancellation under INA 222(g) "
        "void the visa for future travel?",
        None,
    )
    assert "deportation" not in terms
    assert "removal" not in terms
    assert "cancellation" in terms
    assert "222" in terms
    assert "void" in terms
    assert "travel" in terms


def test_overstay_visa_cancellation_keeps_the_reentry_bar():
    terms = _terms(
        "Does automatic visa cancellation under INA 222(g) bar reentry after an overstay?",
        None,
    )
    assert "deportation" not in terms
    assert "removal" not in terms
    assert "222" in terms
    assert "bar" in terms
    assert "reentry" in terms
    assert "overstay" in terms


def test_h1b_petition_cancellation_is_not_removal_proceedings():
    terms = _terms(
        "Can the employer request cancellation of the H-1B petition before approval?",
        "h1b",
    )
    assert "deportation" not in terms
    assert "removal" not in terms
    assert "h-1b" in terms
    assert "cancellation" in terms
    assert "petition" in terms
    assert "approval" in terms


def test_cancellation_of_removal_still_searches_removal_terms():
    terms = _terms(
        "What are the eligibility requirements for cancellation of removal?",
        None,
    )
    assert "deportation" in terms
    assert "removal" in terms
    assert "cancellation" in terms


def test_grounds_of_removal_still_search_deportation():
    terms = _terms("What are the grounds of removal?", None)
    assert "deportation" in terms
    assert "removal" in terms
    assert "grounds" in terms
