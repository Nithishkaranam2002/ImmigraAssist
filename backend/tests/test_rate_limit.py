"""Auth/chat rate limits must count every request and ignore spoofed XFF."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request

from app.middleware.rate_limit import (
    RateLimitMiddleware,
    rate_limit_member,
    resolve_client_ip,
)


def _request(headers: dict[str, str], client_host: str | None = "203.0.113.10") -> Request:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/v1/auth/login",
        "raw_path": b"/api/v1/auth/login",
        "query_string": b"",
        "headers": [
            (k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in headers.items()
        ],
        "client": (client_host, 54321) if client_host else None,
        "server": ("testserver", 80),
    }
    return Request(scope)


def test_rate_limit_members_are_unique_within_same_second():
    now = 1_700_000_000
    members = {rate_limit_member(now) for _ in range(50)}
    assert len(members) == 50
    assert all(m.startswith(f"{now}:") for m in members)


def test_resolve_client_ip_prefers_x_real_ip_over_xff_and_peer():
    req = _request(
        {
            "x-real-ip": "198.51.100.7",
            "x-forwarded-for": "203.0.113.1, 198.51.100.7",
        },
        client_host="10.0.0.2",
    )
    assert resolve_client_ip(req) == "198.51.100.7"


def test_resolve_client_ip_ignores_spoofed_xff():
    """Client-controlled XFF must not become the rate-limit key."""
    req = _request(
        {"x-forwarded-for": "203.0.113.99, 198.51.100.1"},
        client_host="10.0.0.5",
    )
    assert resolve_client_ip(req) == "10.0.0.5"


def test_resolve_client_ip_falls_back_to_unknown():
    req = _request({}, client_host=None)
    assert resolve_client_ip(req) == "unknown"


class _FakePipeline:
    def __init__(self, store: dict[str, dict[str, float]]):
        self.store = store
        self._key: str | None = None
        self._ops: list[str] = []

    def zremrangebyscore(self, key, min_score, max_score):
        self._key = key
        self._ops.append("zrem")
        bucket = self.store.setdefault(key, {})
        for member, score in list(bucket.items()):
            if min_score <= score <= max_score:
                del bucket[member]
        return self

    def zadd(self, key, mapping):
        self._key = key
        self._ops.append("zadd")
        bucket = self.store.setdefault(key, {})
        bucket.update(mapping)
        return self

    def zcard(self, key):
        self._key = key
        self._ops.append("zcard")
        return self

    def expire(self, key, _seconds):
        self._key = key
        self._ops.append("expire")
        return self

    async def execute(self):
        key = self._key or ""
        count = len(self.store.get(key, {}))
        # Mirror real pipeline result order: rem, add, card, expire
        return [0, True, count, True]


@pytest.mark.asyncio
async def test_middleware_counts_burst_in_same_second():
    """Regression: same-second login bursts must each consume a rate-limit slot."""
    store: dict[str, dict[str, float]] = {}
    redis = SimpleNamespace(pipeline=lambda: _FakePipeline(store))

    middleware = RateLimitMiddleware(app=MagicMock())
    call_next = AsyncMock(return_value=SimpleNamespace(status_code=200))
    req = _request({"x-real-ip": "198.51.100.20"})

    with (
        patch("app.middleware.rate_limit.settings") as settings_mock,
        patch("app.middleware.rate_limit.get_redis", AsyncMock(return_value=redis)),
        patch("app.middleware.rate_limit.time") as time_mock,
    ):
        settings_mock.RATE_LIMIT_ENABLED = True
        time_mock.time.return_value = 1_700_000_000

        allowed = 0
        blocked = 0
        # Login limit is 10/60s; the 11th request in the same second must 429.
        for _ in range(11):
            response = await middleware.dispatch(req, call_next)
            if getattr(response, "status_code", None) == 429:
                blocked += 1
            else:
                allowed += 1

    assert allowed == 10
    assert blocked == 1
    assert call_next.await_count == 10
    key = "ratelimit:/api/v1/auth/login:198.51.100.20"
    assert len(store[key]) == 11
