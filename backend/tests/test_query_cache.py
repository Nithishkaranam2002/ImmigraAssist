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


def test_cache_key_is_scoped_by_user():
    query = "What forms are needed?"

    assert query_cache._cache_key(query, "standard", scope="user-a") != (
        query_cache._cache_key(query, "standard", scope="user-b")
    )


def test_cache_key_uses_current_version_namespace():
    key = query_cache._cache_key("What forms are needed?", "standard", scope="user-a")

    assert query_cache.CACHE_VERSION == "v3"
    assert key == "query_cache:8022097ecfad8df90c014337afa9e2fa"
