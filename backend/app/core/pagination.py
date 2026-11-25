import base64
import json
import math
from collections.abc import Sequence
from typing import Annotated, Any, Self

from fastapi import Query
from pydantic import BaseModel, Field, TypeAdapter
from pydantic_core import to_jsonable_python

from app.core.exceptions import AppError

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
# Deep OFFSETs scan and discard every skipped row; past this, narrow the filters instead.
MAX_PAGE = 10_000
MAX_CURSOR_LENGTH = 512


class InvalidCursorError(AppError):
    status_code = 422
    code = "invalid_cursor"
    title = "Unprocessable Content"


class PageParams(BaseModel):
    page: int = Field(1, ge=1, le=MAX_PAGE, description="Page number, starting at 1.")
    size: int = Field(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page.")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


class Page[T](BaseModel):
    items: list[T]
    total: int = Field(description="Number of items matching the query, across all pages.")
    page: int
    size: int
    pages: int

    @classmethod
    def create(cls, items: Sequence[T], total: int, params: PageParams) -> Self:
        return cls(
            items=list(items),
            total=total,
            page=params.page,
            size=params.size,
            pages=math.ceil(total / params.size),
        )


class CursorParams(BaseModel):
    cursor: str | None = Field(
        None,
        max_length=MAX_CURSOR_LENGTH,
        description="Opaque `next_cursor` from the previous page; omit for the first page.",
    )
    limit: int = Field(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page.")


class CursorPage[T](BaseModel):
    items: list[T]
    next_cursor: str | None = Field(description="Pass as `cursor` to get the next page.")
    has_more: bool


PageQuery = Annotated[PageParams, Query()]
CursorQuery = Annotated[CursorParams, Query()]


def encode_cursor(values: Sequence[object]) -> str:
    payload = json.dumps(to_jsonable_python(list(values)), separators=(",", ":"))
    return base64.urlsafe_b64encode(payload.encode()).rstrip(b"=").decode()


def decode_cursor(cursor: str, types: Sequence[type[Any]]) -> tuple[Any, ...]:
    """Decode a cursor back into typed sort-key values; any tampering → InvalidCursorError."""
    try:
        raw = base64.b64decode(cursor + "=" * (-len(cursor) % 4), altchars=b"-_", validate=True)
        values = json.loads(raw)
        if not isinstance(values, list):
            raise ValueError("cursor payload is not a list")
        # strict=True: a cursor with the wrong number of values raises instead of truncating.
        return tuple(
            TypeAdapter(type_).validate_python(value)
            for type_, value in zip(types, values, strict=True)
        )
    # binascii.Error, UnicodeDecodeError, JSONDecodeError and ValidationError are all ValueErrors.
    except ValueError as exc:
        raise InvalidCursorError("The cursor is malformed or expired.") from exc
