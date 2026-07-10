import hashlib
import json
from app.db.redis import get_redis
from app.utils.logger import logger

CACHE_TTL = 3600
CACHE_VERSION = "v2"


def is_cacheable_query(*, matter_id: object | None, session_id: object | None) -> bool:
    """Only stateless queries are safe to reuse from cache."""
    return matter_id is None and session_id is None


def _cache_key(query: str, *, mode: str = "standard", user_id: str) -> str:
    normalized = query.lower().strip()
    digest = hashlib.sha256(
        f"{CACHE_VERSION}:user:{user_id}:mode:{mode}:query:{normalized}".encode()
    ).hexdigest()[:32]
    return f"query_cache:{digest}"


async def get_cached_response(
    query: str,
    *,
    mode: str = "standard",
    user_id: str,
) -> dict | None:
    try:
        redis = await get_redis()
        data = await redis.get(_cache_key(query, mode=mode, user_id=user_id))
        if data:
            logger.info("Query cache hit")
            return json.loads(data)
    except Exception as e:
        logger.debug(f"Cache read failed: {e}")
    return None


async def set_cached_response(
    query: str,
    response: dict,
    *,
    mode: str = "standard",
    user_id: str,
) -> None:
    try:
        redis = await get_redis()
        await redis.setex(
            _cache_key(query, mode=mode, user_id=user_id),
            CACHE_TTL,
            json.dumps(response),
        )
    except Exception as e:
        logger.debug(f"Cache write failed: {e}")
