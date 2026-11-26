from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from redis.asyncio import Redis
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import Settings
from app.db.redis import create_redis
from app.db.session import create_session_factory


@dataclass(frozen=True)
class TaskResources:
    session: AsyncSession
    redis: Redis


@asynccontextmanager
async def task_resources(settings: Settings) -> AsyncIterator[TaskResources]:
    """DB session + Redis for one async task body run with asyncio.run().

    Each asyncio.run() starts a new event loop and asyncpg connections are bound to the loop
    that opened them, so a pool shared between tasks would hand out dead connections. NullPool
    opens and closes a connection per task instead.
    """
    engine = create_async_engine(settings.database_url, poolclass=pool.NullPool)
    redis = create_redis(settings)
    try:
        async with create_session_factory(engine)() as session:
            yield TaskResources(session=session, redis=redis)
    finally:
        await redis.aclose()
        await engine.dispose()
