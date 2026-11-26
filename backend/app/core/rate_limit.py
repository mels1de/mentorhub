"""Fixed-window rate limiting in Redis: INCR a per-window counter that expires with the window.

Fixed window allows up to 2x the limit around a window boundary; for brute-force protection
that is acceptable and it costs one round-trip. A sliding log would be exact but stores every
request.
"""

from collections.abc import Awaitable, Callable
from datetime import timedelta

from fastapi import Request
from redis.asyncio import Redis

from app.core.dependencies import SettingsDep
from app.core.exceptions import TooManyRequestsError
from app.core.security import hash_token
from app.db.redis import RedisDep


class RateLimiter:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def hit(self, key: str, *, limit: int, window: timedelta) -> None:
        redis_key = f"rl:{key}"
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.incr(redis_key)
            # NX: only the first hit starts the window; later hits must not extend it.
            pipe.expire(redis_key, window, nx=True)
            pipe.ttl(redis_key)
            count, _, ttl = await pipe.execute()
        if int(count) > limit:
            raise TooManyRequestsError(
                "Too many requests. Please try again later.", retry_after=max(int(ttl), 1)
            )


def client_ip(request: Request) -> str:
    # Behind a reverse proxy run uvicorn with --proxy-headers / --forwarded-allow-ips,
    # otherwise every client shares the proxy's address.
    return request.client.host if request.client else "unknown"


def anonymized(value: str) -> str:
    # Keys hold a hash, not the raw email, so a Redis dump doesn't list who tried to log in.
    return hash_token(value.strip().lower())[:32]


def rate_limit(
    scope: str, *, limit: int, window: timedelta
) -> Callable[[Request, Redis, SettingsDep], Awaitable[None]]:
    """Route dependency: at most `limit` requests per client IP per `window`."""

    async def dependency(request: Request, redis: RedisDep, settings: SettingsDep) -> None:
        if settings.rate_limit_enabled:
            key = f"{scope}:ip:{client_ip(request)}"
            await RateLimiter(redis).hit(key, limit=limit, window=window)

    return dependency
