import asyncio
import os
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import NoReturn

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession, create_async_engine

from app.core.config import Settings
from app.db.redis import create_redis
from app.db.session import create_engine, get_session
from app.main import create_app

# A logical Redis DB and a database only tests use, so tests never see or touch dev data.
TEST_REDIS_DB = 15
TEST_DATABASE = "mentorhub_test"
BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None, environment="test", redis_db=TEST_REDIS_DB, postgres_db=TEST_DATABASE
    )


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


async def _create_database_if_missing(settings: Settings) -> None:
    # CREATE DATABASE can't run inside a transaction, hence AUTOCOMMIT on the maintenance DB.
    admin_url = settings.database_url.rsplit("/", 1)[0] + "/postgres"
    admin = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as connection:
            exists = await connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": TEST_DATABASE}
            )
            if not exists:
                await connection.execute(text(f'CREATE DATABASE "{TEST_DATABASE}"'))
    finally:
        await admin.dispose()


@pytest.fixture(scope="session")
def test_database() -> None:
    """Create the test database once per run and migrate it to head."""
    settings = Settings(_env_file=None, environment="test", postgres_db=TEST_DATABASE)
    try:
        asyncio.run(_create_database_if_missing(settings))
    except OSError as exc:
        skip_unless_ci(f"database unavailable: {exc}")
    env = {
        **os.environ,
        "POSTGRES_HOST": settings.postgres_host,
        "POSTGRES_PORT": str(settings.postgres_port),
        "POSTGRES_USER": settings.postgres_user,
        "POSTGRES_PASSWORD": settings.postgres_password.get_secret_value(),
        "POSTGRES_DB": TEST_DATABASE,
    }
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=env,
        check=True,
        capture_output=True,
    )


@pytest.fixture
async def engine(settings: Settings, test_database: None) -> AsyncIterator[AsyncEngine]:
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
    await client.flushdb()
    await client.aclose()


@pytest.fixture
async def db_connection(engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    # The whole test runs inside one transaction that is rolled back at the end.
    async with engine.connect() as connection:
        transaction = await connection.begin()
        yield connection
        await transaction.rollback()


@pytest.fixture
async def db_session(db_connection: AsyncConnection) -> AsyncIterator[AsyncSession]:
    # Services call commit(); in this mode that only releases a SAVEPOINT inside our transaction.
    session = AsyncSession(
        bind=db_connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    yield session
    await session.close()


@pytest.fixture
async def api(app: FastAPI, db_session: AsyncSession, redis: Redis) -> AsyncIterator[AsyncClient]:
    """Client whose requests share the test's rolled-back DB transaction and the test Redis DB."""

    async def session_override() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = session_override
    async with (
        app.router.lifespan_context(app),
        # https: httpx (like a browser) never sends a Secure cookie over plain http.
        AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as ac,
    ):
        yield ac
    app.dependency_overrides.clear()


def skip_unless_ci(reason: str) -> NoReturn:
    # Locally a missing service skips the test; in CI it must fail, not silently pass.
    if os.environ.get("CI"):
        raise RuntimeError(reason)
    pytest.skip(reason)
