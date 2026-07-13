import asyncio
import os


os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_USER", "postgres")
os.environ.setdefault("POSTGRES_PASSWORD", "postgres")
os.environ.setdefault("POSTGRES_DB", "immigraassist_test")
os.environ.setdefault("MILVUS_HOST", "localhost")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

from app.services import query_cache


class FakeRedis:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def setex(self, key, ttl, value):
        self.store[key] = value


def run(coro):
    return asyncio.run(coro)


def test_cache_key_is_scoped_by_user():
    assert query_cache._cache_key("What is H-1B?", "standard", "user-a") != (
        query_cache._cache_key("What is H-1B?", "standard", "user-b")
    )
    assert query_cache._cache_key(" What is H-1B? ", "standard", "user-a") == (
        query_cache._cache_key("what is h-1b?", "standard", "user-a")
    )


def test_cached_responses_do_not_cross_users(monkeypatch):
    fake_redis = FakeRedis()

    async def fake_get_redis():
        return fake_redis

    monkeypatch.setattr(query_cache, "get_redis", fake_get_redis)

    run(
        query_cache.set_cached_response(
            "What forms are needed?",
            {"answer": "user A answer"},
            "standard",
            "user-a",
        )
    )

    assert run(
        query_cache.get_cached_response(
            "What forms are needed?",
            "standard",
            "user-b",
        )
    ) is None
    assert run(
        query_cache.get_cached_response(
            "What forms are needed?",
            "standard",
            "user-a",
        )
    ) == {"answer": "user A answer"}


def test_contextual_chat_requests_bypass_cache():
    assert query_cache.is_cacheable_chat_request(
        stream=False,
        matter_id=None,
        session_id=None,
    )
    assert not query_cache.is_cacheable_chat_request(
        stream=True,
        matter_id=None,
        session_id=None,
    )
    assert not query_cache.is_cacheable_chat_request(
        stream=False,
        matter_id="matter-id",
        session_id=None,
    )
    assert not query_cache.is_cacheable_chat_request(
        stream=False,
        matter_id=None,
        session_id="session-id",
    )
