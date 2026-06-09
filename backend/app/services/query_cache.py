import hashlib
import json
from uuid import UUID
from app.db.redis import get_redis
from app.utils.logger import logger

CACHE_TTL = 3600


def _cache_key(query: str, mode: str = "standard", user_id: UUID | str | None = None) -> str:
    normalized = query.lower().strip()
    scope = str(user_id) if user_id else "anonymous"
    digest = hashlib.sha256(f"{scope}:{mode}:{normalized}".encode()).hexdigest()[:32]
    return f"query_cache:{digest}"


async def get_cached_response(
    query: str,
    mode: str = "standard",
    user_id: UUID | str | None = None,
) -> dict | None:
    try:
        redis = await get_redis()
        data = await redis.get(_cache_key(query, mode, user_id))
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
    user_id: UUID | str | None = None,
) -> None:
    try:
        redis = await get_redis()
        await redis.setex(
            _cache_key(query, mode, user_id),
            CACHE_TTL,
            json.dumps(response),
        )
    except Exception as e:
        logger.debug(f"Cache write failed: {e}")
