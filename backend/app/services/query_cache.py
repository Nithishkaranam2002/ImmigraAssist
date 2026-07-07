import hashlib
import json
from app.db.redis import get_redis
from app.utils.logger import logger

CACHE_TTL = 3600
CACHE_VERSION = "v3"


def is_cacheable_query(
    *,
    matter_id: object | None = None,
    session_id: object | None = None,
    extra_context: object | None = None,
) -> bool:
    """Only stateless chat responses are safe to reuse across requests."""
    return matter_id is None and session_id is None and extra_context is None


def _cache_key(query: str, mode: str = "standard") -> str:
    normalized = query.lower().strip()
    digest = hashlib.sha256(f"{CACHE_VERSION}:{mode}:{normalized}".encode()).hexdigest()[:32]
    return f"query_cache:{digest}"


async def get_cached_response(query: str, mode: str = "standard") -> dict | None:
    try:
        redis = await get_redis()
        data = await redis.get(_cache_key(query, mode))
        if data:
            logger.info("Query cache hit")
            return json.loads(data)
    except Exception as e:
        logger.debug(f"Cache read failed: {e}")
    return None


async def set_cached_response(query: str, response: dict, mode: str = "standard") -> None:
    try:
        redis = await get_redis()
        await redis.setex(
            _cache_key(query, mode),
            CACHE_TTL,
            json.dumps(response),
        )
    except Exception as e:
        logger.debug(f"Cache write failed: {e}")
