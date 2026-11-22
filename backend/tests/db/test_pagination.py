import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import MetaData, UnaryExpression, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped

from app.core.pagination import CursorParams, InvalidCursorError, PageParams, encode_cursor
from app.db.base import NAMING_CONVENTION, TYPE_ANNOTATION_MAP, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.pagination import paginate_keyset, paginate_offset

pytestmark = pytest.mark.integration

T0 = datetime(2026, 1, 1, tzinfo=UTC)


class _Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = TYPE_ANNOTATION_MAP


class _Item(UUIDPrimaryKeyMixin, TimestampMixin, _Base):
    __tablename__ = "test_pagination_items"

    n: Mapped[int]


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with engine.connect() as connection:
        transaction = await connection.begin()
        await connection.run_sync(_Base.metadata.create_all)
        async with AsyncSession(bind=connection, expire_on_commit=False) as session:
            yield session
        await transaction.rollback()


async def add_items(session: AsyncSession, count: int, *, start: int = 0) -> None:
    # Three rows share each timestamp, so ordering by created_at alone would be ambiguous.
    session.add_all(
        _Item(n=start + i, created_at=T0 + timedelta(seconds=(start + i) // 3))
        for i in range(count)
    )
    await session.flush()


def newest_first() -> list[UnaryExpression[Any]]:
    return [_Item.created_at.desc(), _Item.id.desc()]


async def all_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.scalars(select(_Item.id).order_by(*newest_first()))).all())


# --- offset ---------------------------------------------------------------------------


async def test_offset_pages_cover_everything_once(session: AsyncSession) -> None:
    await add_items(session, 45)
    stmt = select(_Item).order_by(*newest_first())

    pages = [await paginate_offset(session, stmt, PageParams(page=p, size=20)) for p in (1, 2, 3)]

    assert [len(items) for items, _ in pages] == [20, 20, 5]
    assert {total for _, total in pages} == {45}
    assert [item.id for items, _ in pages for item in items] == await all_ids(session)


async def test_offset_total_respects_filters(session: AsyncSession) -> None:
    await add_items(session, 45)
    stmt = select(_Item).where(_Item.n < 10).order_by(*newest_first())

    items, total = await paginate_offset(session, stmt, PageParams(size=3))

    assert total == 10
    assert len(items) == 3


async def test_offset_page_past_the_end_is_empty_with_total(session: AsyncSession) -> None:
    await add_items(session, 5)

    items, total = await paginate_offset(session, select(_Item), PageParams(page=3, size=20))

    assert items == []
    assert total == 5


# --- keyset ---------------------------------------------------------------------------


async def walk(session: AsyncSession, *, limit: int, descending: bool = True) -> list[list[_Item]]:
    pages: list[list[_Item]] = []
    cursor: str | None = None
    while True:
        items, cursor = await paginate_keyset(
            session,
            select(_Item),
            CursorParams(cursor=cursor, limit=limit),
            order_by=[_Item.created_at, _Item.id],
            descending=descending,
        )
        pages.append(items)
        if cursor is None:
            return pages


async def test_keyset_walk_with_ties_covers_everything_once(session: AsyncSession) -> None:
    await add_items(session, 47)

    pages = await walk(session, limit=10)

    assert [len(page) for page in pages] == [10, 10, 10, 10, 7]
    assert [item.id for page in pages for item in page] == await all_ids(session)


async def test_keyset_ascending(session: AsyncSession) -> None:
    await add_items(session, 25)

    pages = await walk(session, limit=10, descending=False)

    assert [item.id for page in pages for item in page] == list(reversed(await all_ids(session)))


async def test_keyset_exact_multiple_has_no_empty_last_page(session: AsyncSession) -> None:
    await add_items(session, 20)

    pages = await walk(session, limit=10)

    assert [len(page) for page in pages] == [10, 10]


async def test_keyset_ignores_rows_inserted_above_while_scrolling(session: AsyncSession) -> None:
    await add_items(session, 30)
    params = CursorParams(limit=10)
    first, cursor = await paginate_keyset(
        session, select(_Item), params, order_by=[_Item.created_at, _Item.id]
    )

    await add_items(session, 5, start=100)  # newer than everything already shown
    second, _ = await paginate_keyset(
        session,
        select(_Item),
        CursorParams(cursor=cursor, limit=10),
        order_by=[_Item.created_at, _Item.id],
    )

    assert [i.n for i in first] == list(range(29, 19, -1))
    assert [i.n for i in second] == list(range(19, 9, -1))


async def test_keyset_combines_with_filters(session: AsyncSession) -> None:
    await add_items(session, 30)
    stmt = select(_Item).where(_Item.n % 2 == 0)

    items, cursor = await paginate_keyset(
        session, stmt, CursorParams(limit=20), order_by=[_Item.created_at, _Item.id]
    )

    assert len(items) == 15
    assert all(i.n % 2 == 0 for i in items)
    assert cursor is None


async def test_keyset_rejects_cursor_with_wrong_types(session: AsyncSession) -> None:
    bad = encode_cursor(["not-a-date", "not-a-uuid"])

    with pytest.raises(InvalidCursorError):
        await paginate_keyset(
            session,
            select(_Item),
            CursorParams(cursor=bad),
            order_by=[_Item.created_at, _Item.id],
        )
