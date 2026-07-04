import os


os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("MILVUS_HOST", "localhost")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app.services import query_cache  # noqa: E402


def test_cache_key_is_scoped_by_user_context():
    query = "What are H-1B specialty occupation requirements?"

    first_user = query_cache._cache_key(query, scope="user-a")
    second_user = query_cache._cache_key(query, scope="user-b")

    assert first_user != second_user


def test_cache_key_version_bumped_after_global_cache_fix():
    key = query_cache._cache_key("What are H-4 EAD requirements?", scope="user-a")

    assert query_cache.CACHE_VERSION == "v3"
    assert key.startswith("query_cache:")
