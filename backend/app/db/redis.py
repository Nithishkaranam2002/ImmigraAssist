import re
import redis.asyncio as aioredis
from app.config import settings
from app.utils.logger import logger


# single async redis client reused across the app
_redis_client: aioredis.Redis | None = None

_REDIS_PASSWORD_IN_URL = re.compile(r"(redis://:)([^@]+)(@)")


def _redact_redis_url(url: str) -> str:
    """Strip password from redis://:password@host URLs before logging."""
    return _REDIS_PASSWORD_IN_URL.sub(r"\1***\3", url)


async def get_redis() -> aioredis.Redis:
    """
    Returns the Redis client.
    Creates it on first call, reuses after that.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
        logger.info(
            f"Redis client connected at {_redact_redis_url(settings.REDIS_URL)}"
        )
    return _redis_client


async def close_redis():
    """Close Redis connection on app shutdown."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis connection closed")