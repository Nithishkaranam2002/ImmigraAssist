import hashlib
import json
from app.db.redis import get_redis
from app.utils.logger import logger

CACHE_TTL = 3600
CACHE_VERSION = "v3"


def is_cacheable_chat_request(
    *,
    stream: bool,
    matter_id: object | None,
    session_id: object | None,
) -> bool:
    return not stream and matter_id is None and session_id is None


def _cache_key(query: str, mode: str = "standard", user_id: str = "") -> str:
    normalized = query.lower().strip()
    digest = hashlib.sha256(
        f"{CACHE_VERSION}:{user_id}:{mode}:{normalized}".encode()
    ).hexdigest()[:32]
    return f"query_cache:{digest}"


async def get_cached_response(
    query: str,
    mode: str = "standard",
    user_id: str = "",
) -> dict | None:
    try:
        redis = await get_redis()
        data = await redis.get(_cache_key(query, mode, str(user_id)))
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
    user_id: str = "",
) -> None:
    try:
        redis = await get_redis()
        await redis.setex(
            _cache_key(query, mode, str(user_id)),
            CACHE_TTL,
            json.dumps(response),
        )
    except Exception as e:
        logger.debug(f"Cache write failed: {e}")
