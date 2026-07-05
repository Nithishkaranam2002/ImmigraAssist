import asyncio
import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_USER", "postgres")
os.environ.setdefault("POSTGRES_PASSWORD", "postgres")
os.environ.setdefault("POSTGRES_DB", "immigraassist_test")
os.environ.setdefault("MILVUS_HOST", "localhost")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app.services import query_cache


class FakeRedis:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def setex(self, key, ttl, value):
        self.store[key] = value


def test_cached_responses_are_isolated_by_scope(monkeypatch):
    redis = FakeRedis()

    async def fake_get_redis():
        return redis

    monkeypatch.setattr(query_cache, "get_redis", fake_get_redis)

    async def run():
        await query_cache.set_cached_response(
            "What forms does this client need?",
            {"answer": "Use Alice's matter notes", "audit_log_id": "audit-a"},
            cache_scope="user:user-a",
        )

        same_user = await query_cache.get_cached_response(
            "what forms does this client need?",
            cache_scope="user:user-a",
        )
        other_user = await query_cache.get_cached_response(
            "what forms does this client need?",
            cache_scope="user:user-b",
        )

        assert same_user["answer"] == "Use Alice's matter notes"
        assert other_user is None

    asyncio.run(run())
