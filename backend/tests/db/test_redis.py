import pytest
from httpx import AsyncClient
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings
from app.db.health import RedisCheck
from app.db.redis import create_redis

pytestmark = pytest.mark.integration


async def test_redis_check_passes(redis: Redis) -> None:
    await RedisCheck(redis).check()


async def test_redis_check_fails_when_unreachable(settings: Settings) -> None:
    client = create_redis(settings.model_copy(update={"redis_port": 1}))
    try:
        with pytest.raises(RedisConnectionError):
            await RedisCheck(client).check()
    finally:
        await client.aclose()


async def test_ready_reports_all_dependencies(
    client: AsyncClient, engine: AsyncEngine, redis: Redis
) -> None:
    response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "pass", "checks": {"database": "pass", "redis": "pass"}}
