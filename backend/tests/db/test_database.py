import uuid
from collections.abc import AsyncIterator
from datetime import datetime

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import MetaData, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped

from app.db.base import NAMING_CONVENTION, TYPE_ANNOTATION_MAP, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.health import DatabaseCheck
from app.db.session import SessionDep

pytestmark = pytest.mark.integration


class _Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = TYPE_ANNOTATION_MAP


class _Note(UUIDPrimaryKeyMixin, TimestampMixin, _Base):
    __tablename__ = "test_notes"

    body: Mapped[str]


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    # Postgres DDL is transactional: the table and rows vanish on rollback.
    async with engine.connect() as connection:
        transaction = await connection.begin()
        await connection.run_sync(_Base.metadata.create_all)
        async with AsyncSession(bind=connection, expire_on_commit=False) as session:
            yield session
        await transaction.rollback()


async def test_database_check_passes(engine: AsyncEngine) -> None:
    await DatabaseCheck(engine).check()


async def test_ready_reports_database(client: AsyncClient, engine: AsyncEngine) -> None:
    response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "pass", "checks": {"database": "pass"}}


async def test_insert_fills_uuid7_and_tz_aware_timestamps(session: AsyncSession) -> None:
    note = _Note(body="hello")
    session.add(note)
    await session.flush()
    await session.refresh(note)

    assert isinstance(note.id, uuid.UUID)
    assert note.id.version == 7
    assert isinstance(note.created_at, datetime)
    assert note.created_at.tzinfo is not None
    assert note.updated_at == note.created_at


async def test_session_dependency_yields_working_session(
    app: FastAPI, client: AsyncClient, engine: AsyncEngine
) -> None:
    @app.get("/test/db")
    async def db_route(session: SessionDep) -> dict[str, int]:
        return {"value": (await session.execute(select(text("1")))).scalar_one()}

    response = await client.get("/test/db")

    assert response.json() == {"value": 1}
