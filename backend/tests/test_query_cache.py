from app.services.query_cache import _cache_key


def test_cache_key_is_scoped_by_user():
    query = "What are H-4 EAD requirements?"

    assert _cache_key(query, "standard", scope="user-a") != _cache_key(
        query, "standard", scope="user-b"
    )


def test_cache_key_normalizes_query_within_scope():
    assert _cache_key("  What Are H-4 EAD Requirements?  ", scope="user-a") == _cache_key(
        "what are h-4 ead requirements?",
        scope="user-a",
    )
