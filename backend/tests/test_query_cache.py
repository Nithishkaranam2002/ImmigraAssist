import asyncio
import json
from uuid import uuid4

from app.services import query_cache
from app.services.query_cache import (
    get_cached_response,
    is_cacheable_query,
    set_cached_response,
)


class FakeRedis:
    def __init__(self):
        self.values: dict[str, str] = {}

    async def get(self, key: str):
        return self.values.get(key)

    async def setex(self, key: str, ttl: int, value: str):
        self.values[key] = value


def test_cache_keys_are_scoped_by_user(monkeypatch):
    redis = FakeRedis()

    async def fake_get_redis():
        return redis

    monkeypatch.setattr(query_cache, "get_redis", fake_get_redis)

    asyncio.run(
        set_cached_response(
            "What forms are needed?",
            {"answer": "user A answer"},
            user_id="user-a",
        )
    )

    assert (
        asyncio.run(
            get_cached_response(
                "What forms are needed?",
                user_id="user-b",
            )
        )
        is None
    )
    assert asyncio.run(
        get_cached_response(
            "What forms are needed?",
            user_id="user-a",
        )
    ) == {"answer": "user A answer"}

    assert len(redis.values) == 1
    assert json.loads(next(iter(redis.values.values()))) == {"answer": "user A answer"}


def test_contextual_queries_are_not_cacheable():
    assert is_cacheable_query(matter_id=None, session_id=None)
    assert not is_cacheable_query(matter_id=uuid4(), session_id=None)
    assert not is_cacheable_query(matter_id=None, session_id=uuid4())
