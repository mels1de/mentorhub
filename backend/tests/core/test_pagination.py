import uuid
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.core.pagination import (
    MAX_PAGE_SIZE,
    CursorParams,
    CursorQuery,
    InvalidCursorError,
    Page,
    PageParams,
    PageQuery,
    decode_cursor,
    encode_cursor,
)
from app.main import create_app


@pytest.mark.parametrize(
    ("page", "size", "offset"),
    [(1, 20, 0), (2, 20, 20), (5, 100, 400)],
)
def test_page_params_offset(page: int, size: int, offset: int) -> None:
    assert PageParams(page=page, size=size).offset == offset


@pytest.mark.parametrize(
    ("total", "pages"),
    [(0, 0), (1, 1), (20, 1), (21, 2), (100, 5)],
)
def test_page_counts_pages(total: int, pages: int) -> None:
    page = Page[int].create([], total=total, params=PageParams(size=20))

    assert page.pages == pages


@pytest.mark.parametrize("params", [{"page": 0}, {"size": 0}, {"size": MAX_PAGE_SIZE + 1}])
def test_page_params_reject_out_of_range(params: dict[str, int]) -> None:
    with pytest.raises(ValidationError):
        PageParams.model_validate(params)


def test_cursor_params_reject_oversized_limit() -> None:
    with pytest.raises(ValidationError):
        CursorParams(limit=MAX_PAGE_SIZE + 1)


def test_cursor_round_trip_restores_types() -> None:
    created_at = datetime(2026, 11, 15, 9, 30, 0, 123456, tzinfo=UTC)
    id_ = uuid.uuid7()

    cursor = encode_cursor([created_at, id_])

    assert decode_cursor(cursor, [datetime, uuid.UUID]) == (created_at, id_)


def test_cursor_is_url_safe() -> None:
    cursor = encode_cursor(["???>>>", 1])

    assert "=" not in cursor
    assert cursor.isascii()
    assert not set(cursor) & {"+", "/"}


@pytest.mark.parametrize(
    "cursor",
    [
        "not base64!",  # outside the alphabet
        encode_cursor(["2026-11-15T09:30:00Z"])[:-3],  # truncated
        "bm90IGpzb24",  # base64 of "not json"
        encode_cursor(["2026-11-15T09:30:00Z"]),  # wrong arity
        encode_cursor(["yesterday", "not-a-uuid"]),  # wrong types
    ],
)
def test_decode_rejects_tampered_cursor(cursor: str) -> None:
    with pytest.raises(InvalidCursorError):
        decode_cursor(cursor, [datetime, uuid.UUID])


@pytest.fixture
def pagination_app() -> FastAPI:
    app = create_app()

    @app.get("/pages")
    async def pages(params: PageQuery) -> PageParams:
        return params

    @app.get("/cursors")
    async def cursors(params: CursorQuery) -> CursorParams:
        return params

    return app


async def test_query_models_read_params_and_defaults(pagination_app: FastAPI) -> None:
    async with AsyncClient(transport=ASGITransport(app=pagination_app), base_url="http://t") as c:
        pages = await c.get("/pages", params={"page": 3})
        cursors = await c.get("/cursors", params={"cursor": "abc", "limit": 5})

    assert pages.json() == {"page": 3, "size": 20}
    assert cursors.json() == {"cursor": "abc", "limit": 5}


async def test_oversized_page_is_problem_details_422(pagination_app: FastAPI) -> None:
    async with AsyncClient(transport=ASGITransport(app=pagination_app), base_url="http://t") as c:
        response = await c.get("/pages", params={"size": MAX_PAGE_SIZE + 1})

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
