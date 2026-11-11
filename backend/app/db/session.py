from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(settings.database_url, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    # Objects stay readable after commit; a refresh would need I/O, which async can't do lazily.
    return async_sessionmaker(engine, expire_on_commit=False)


def get_engine(request: Request) -> AsyncEngine:
    engine: AsyncEngine = request.app.state.engine
    return engine


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    # Services commit explicitly; close() rolls back whatever they did not commit.
    async with session_factory() as session:
        yield session


# scope="function": the session is closed before the response is sent, not after it.
SessionDep = Annotated[AsyncSession, Depends(get_session, scope="function")]
