from app.services import query_cache
from app.services.query_cache import is_cacheable_query


def test_plain_query_is_cacheable():
    assert is_cacheable_query()


def test_matter_query_is_not_cacheable():
    assert not is_cacheable_query(matter_id="matter-123")


def test_session_query_is_not_cacheable():
    assert not is_cacheable_query(session_id="session-123")


def test_extra_context_query_is_not_cacheable():
    assert not is_cacheable_query(extra_context="client document text")


def test_cache_key_uses_current_version_namespace():
    key = query_cache._cache_key("What forms are needed?", "standard")

    assert query_cache.CACHE_VERSION == "v3"
    assert key == "query_cache:03392c28a4af8174b33caa390f9f947a"
