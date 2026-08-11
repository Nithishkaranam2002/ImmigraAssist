"""Redis connection logs must not include the password."""

from app.db.redis import _redact_redis_url


def test_redact_redis_url_with_password():
    url = "redis://:super-secret-pass@redis:6379/0"
    redacted = _redact_redis_url(url)
    assert "super-secret-pass" not in redacted
    assert redacted == "redis://:***@redis:6379/0"


def test_redact_redis_url_without_password_unchanged():
    url = "redis://localhost:6379/0"
    assert _redact_redis_url(url) == url
