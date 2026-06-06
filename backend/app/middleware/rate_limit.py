import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.db.redis import get_redis
from app.config import settings
from app.utils.logger import logger


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
        client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
        if "," in client_ip:
            client_ip = client_ip.split(",")[0].strip()

        key = f"ratelimit:{path}:{client_ip}"
        now = int(time.time())
        window_start = now - window_secs

        try:
            redis = await get_redis()
            pipe = redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zadd(key, {str(now): now})
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
