import os
from collections.abc import AsyncIterator
from typing import NoReturn

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings
from app.db.redis import create_redis
from app.db.session import create_engine
from app.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None, environment="test")


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    # ASGITransport does not send lifespan events, so run the lifespan ourselves.
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac,
    ):
        yield ac


@pytest.fixture
async def engine(settings: Settings) -> AsyncIterator[AsyncEngine]:
    engine = create_engine(settings)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except OSError as exc:
        await engine.dispose()
        skip_unless_ci(f"database unavailable: {exc}")
    yield engine
    await engine.dispose()


@pytest.fixture
async def redis(settings: Settings) -> AsyncIterator[Redis]:
    client = create_redis(settings)
    try:
        await client.ping()
    except RedisConnectionError as exc:
        await client.aclose()
        skip_unless_ci(f"redis unavailable: {exc}")
    yield client
    await client.aclose()


def skip_unless_ci(reason: str) -> NoReturn:
    # Locally a missing service skips the test; in CI it must fail, not silently pass.
    if os.environ.get("CI"):
        raise RuntimeError(reason)
    pytest.skip(reason)
