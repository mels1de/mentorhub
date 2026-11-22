from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, Select, func, literal, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.core.pagination import CursorParams, PageParams, decode_cursor, encode_cursor


async def paginate_offset[M](
    session: AsyncSession, stmt: Select[M], params: PageParams
) -> tuple[list[M], int]:
    """`stmt` must have a deterministic ORDER BY ending in a unique column."""
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = (await session.execute(count_stmt)).scalar_one()
    rows = await session.scalars(stmt.limit(params.size).offset(params.offset))
    return list(rows.all()), total


async def paginate_keyset[M](
    session: AsyncSession,
    stmt: Select[M],
    params: CursorParams,
    *,
    order_by: Sequence[InstrumentedAttribute[Any]],
    descending: bool = True,
) -> tuple[list[M], str | None]:
    """Order by `order_by` (all NOT NULL, the last one unique, e.g. `(created_at, id)`).

    Replaces any ORDER BY on `stmt`. Returns the page and the cursor for the next one.
    """
    if params.cursor is not None:
        values = decode_cursor(params.cursor, [col.type.python_type for col in order_by])
        key = tuple_(*order_by)
        after = tuple_(*(literal(v, col.type) for col, v in zip(order_by, values, strict=True)))
        condition: ColumnElement[bool] = key < after if descending else key > after
        stmt = stmt.where(condition)

    ordering = [col.desc() if descending else col.asc() for col in order_by]
    # One extra row tells us whether a next page exists, without a COUNT.
    stmt = stmt.order_by(None).order_by(*ordering).limit(params.limit + 1)
    rows = list((await session.scalars(stmt)).all())

    if len(rows) <= params.limit:
        return rows, None
    items = rows[: params.limit]
    last = items[-1]
    return items, encode_cursor([getattr(last, col.key) for col in order_by])
