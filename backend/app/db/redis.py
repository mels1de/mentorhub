from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis

from app.core.config import Settings

# Fail fast instead of hanging a request when Redis is unreachable.
SOCKET_TIMEOUT_SECONDS = 2.0


def create_redis(settings: Settings) -> Redis:
    return Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=SOCKET_TIMEOUT_SECONDS,
        socket_timeout=SOCKET_TIMEOUT_SECONDS,
        health_check_interval=30,
    )


def get_redis(request: Request) -> Redis:
    redis: Redis = request.app.state.redis
    return redis


RedisDep = Annotated[Redis, Depends(get_redis)]
