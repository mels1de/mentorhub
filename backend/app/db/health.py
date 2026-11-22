from dataclasses import dataclass

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


@dataclass(frozen=True)
class DatabaseCheck:
    engine: AsyncEngine
    name: str = "database"

    async def check(self) -> None:
        async with self.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))


@dataclass(frozen=True)
class RedisCheck:
    redis: Redis
    name: str = "redis"

    async def check(self) -> None:
        await self.redis.ping()
