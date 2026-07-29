import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.db.redis import get_redis
from app.config import settings
from app.utils.logger import logger


def resolve_client_ip(request: Request) -> str:
    """
    Resolve the client IP for rate limiting.

    Prefer X-Real-IP (nginx sets this from $remote_addr) over the socket peer.
    Do not trust X-Forwarded-For: the backend publishes :8000 directly, and
    clients can spoof XFF even when proxied via nginx's $proxy_add_x_forwarded_for.
    """
    real_ip = (request.headers.get("x-real-ip") or "").strip()
    if real_ip:
        # Take a single hop only; reject obvious multi-value spoof attempts.
        return real_ip.split(",")[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def rate_limit_member(now: int) -> str:
    """Unique Redis zset member so concurrent requests in the same second all count."""
    return f"{now}:{uuid.uuid4().hex}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-backed sliding-window rate limiter for expensive endpoints."""

    LIMITS = {
        "/api/v1/chat/query": (20, 60),
        "/api/v1/auth/login": (10, 60),
        "/api/v1/auth/register": (5, 60),
    }

    async def dispatch(self, request: Request, call_next):
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        path = request.url.path
        limit_cfg = self.LIMITS.get(path)
        if not limit_cfg:
            return await call_next(request)

        max_requests, window_secs = limit_cfg
        client_ip = resolve_client_ip(request)

        key = f"ratelimit:{path}:{client_ip}"
        now = int(time.time())
        window_start = now - window_secs

        try:
            redis = await get_redis()
            pipe = redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zadd(key, {rate_limit_member(now): now})
            pipe.zcard(key)
            pipe.expire(key, window_secs)
            results = await pipe.execute()
            count = results[2]

            if count > max_requests:
                logger.warning(f"Rate limit exceeded: {client_ip} on {path}")
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please wait and try again."},
                )
        except Exception as e:
            logger.error(f"Rate limit check failed, allowing request: {e}")

        return await call_next(request)
