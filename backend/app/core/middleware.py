import re
import time
from uuid import uuid7

import structlog
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.problem_details import problem_response

REQUEST_ID_HEADER = "X-Request-ID"
# Incoming IDs end up in logs: a strict whitelist prevents log injection.
VALID_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")

access_logger = structlog.stdlib.get_logger("mentorhub.access")
error_logger = structlog.stdlib.get_logger("mentorhub.errors")


class RequestIdMiddleware:
    """Pure ASGI middleware (not BaseHTTPMiddleware): safe for streaming and WebSockets."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = self._incoming_request_id(scope) or str(uuid7())
        status_code = 500
        started = time.perf_counter()

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        with structlog.contextvars.bound_contextvars(request_id=request_id):
            try:
                await self.app(scope, receive, send_with_request_id)
            finally:
                access_logger.info(
                    "request",
                    method=scope["method"],
                    path=scope["path"],  # no query string: it may carry tokens
                    status=status_code,
                    duration_ms=round((time.perf_counter() - started) * 1000, 2),
                )

    @staticmethod
    def _incoming_request_id(scope: Scope) -> str | None:
        for name, value in scope["headers"]:
            if name == b"x-request-id":
                candidate: str = value.decode("latin-1")
                return candidate if VALID_REQUEST_ID.fullmatch(candidate) else None
        return None


class UnhandledExceptionMiddleware:
    """Catch-all for exceptions no handler knows. Must sit inside RequestIdMiddleware:
    Starlette's own 500 handling (ServerErrorMiddleware) runs outside all user middleware,
    where the request_id context and response header are already gone."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def send_tracking_start(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, send_tracking_start)
        except Exception:
            error_logger.exception("unhandled_exception")
            if response_started:
                # Headers are already sent: a 500 is impossible, let the server drop the connection.
                raise
            response = problem_response(
                status=500, title="Internal Server Error", instance=scope["path"]
            )
            await response(scope, receive, send)
