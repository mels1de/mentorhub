from collections.abc import Mapping
from http import HTTPStatus

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError

PROBLEM_JSON = "application/problem+json"
PROBLEM_TYPE_BASE = "https://github.com/mels1de/mentorhub/blob/main/docs/errors.md#"

logger = structlog.stdlib.get_logger(__name__)


class ProblemDetail(BaseModel):
    """RFC 9457 body. Extension members (`code`, `request_id`, `errors`, ...) are extra fields."""

    model_config = ConfigDict(extra="allow")

    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None


def problem_response(
    *,
    status: int,
    title: str,
    instance: str | None,
    type_: str = "about:blank",
    detail: str | None = None,
    extensions: Mapping[str, object] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    # Standard members are merged last so an extension can never overwrite them.
    problem = ProblemDetail.model_validate(
        {
            **(extensions or {}),
            "request_id": structlog.contextvars.get_contextvars().get("request_id"),
            "type": type_,
            "title": title,
            "status": status,
            "detail": detail,
            "instance": instance,
        }
    )
    return JSONResponse(
        problem.model_dump(mode="json", exclude_none=True),
        status_code=status,
        headers=headers,
        media_type=PROBLEM_JSON,
    )


def _status_phrase(status: int) -> str:
    try:
        return HTTPStatus(status).phrase
    except ValueError:
        return "Error"


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    detail = exc.detail
    if exc.status_code >= 500:
        logger.error("app_error", code=exc.code, exc_info=exc)
        detail = None  # 5xx details are internal
    return problem_response(
        status=exc.status_code,
        title=exc.title,
        instance=request.url.path,
        type_=PROBLEM_TYPE_BASE + exc.code,
        detail=detail,
        extensions={**exc.extensions, "code": exc.code},
        headers=exc.headers,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    # Framework-level errors (unknown route, wrong method, security deps): no domain meaning.
    title = _status_phrase(exc.status_code)
    detail = exc.detail if isinstance(exc.detail, str) and exc.detail != title else None
    return problem_response(
        status=exc.status_code,
        title=title,
        instance=request.url.path,
        detail=detail,
        headers=exc.headers,
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Only loc/msg/type: Pydantic's `input` and `ctx` would echo submitted values (passwords).
    errors = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return problem_response(
        status=422,
        title="Unprocessable Content",
        instance=request.url.path,
        type_=PROBLEM_TYPE_BASE + "validation_error",
        detail="The request contains invalid fields.",
        extensions={"code": "validation_error", "errors": errors},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
