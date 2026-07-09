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


def _cache_key(query: str, mode: str = "standard", scope: str | None = None) -> str:
    normalized = query.lower().strip()
    scope_part = scope or "global"
    digest = hashlib.sha256(
        f"{CACHE_VERSION}:{scope_part}:{mode}:{normalized}".encode()
    ).hexdigest()[:32]
    return f"query_cache:{digest}"


async def get_cached_response(
    query: str,
    mode: str = "standard",
    scope: str | None = None,
) -> dict | None:
    try:
        redis = await get_redis()
        data = await redis.get(_cache_key(query, mode, scope))
        if data:
            logger.info("Query cache hit")
            return json.loads(data)
    except Exception as e:
        logger.debug(f"Cache read failed: {e}")
    return None


async def set_cached_response(
    query: str,
    response: dict,
    mode: str = "standard",
    scope: str | None = None,
) -> None:
    try:
        redis = await get_redis()
        await redis.setex(
            _cache_key(query, mode, scope),
            CACHE_TTL,
            json.dumps(response),
        )
    except Exception as e:
        logger.debug(f"Cache write failed: {e}")
