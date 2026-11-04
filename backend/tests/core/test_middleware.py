import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

import pytest
import structlog
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from httpx import AsyncClient

from app.core.problem_details import PROBLEM_JSON


@pytest.fixture(autouse=True)
def routes(app: FastAPI) -> None:
    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/whoami")
    async def whoami() -> dict[str, Any]:
        await asyncio.sleep(0.01)  # let concurrent requests interleave
        return structlog.contextvars.get_contextvars()

    @app.get("/crash")
    async def crash() -> None:
        raise RuntimeError("secret internal state")

    @app.get("/crash-mid-stream")
    async def crash_mid_stream() -> StreamingResponse:
        async def chunks() -> AsyncIterator[bytes]:
            yield b"partial"
            raise RuntimeError("stream broke")

        return StreamingResponse(chunks())


def access_records(caplog: pytest.LogCaptureFixture) -> list[dict[str, Any]]:
    # structlog hands its event dict to stdlib logging as record.msg.
    return [r.msg for r in caplog.records if r.name == "mentorhub.access"]  # type: ignore[misc]


async def test_generates_uuid7_request_id(client: AsyncClient) -> None:
    response = await client.get("/ping")

    assert UUID(response.headers["X-Request-ID"]).version == 7


async def test_echoes_valid_incoming_request_id(client: AsyncClient) -> None:
    response = await client.get("/ping", headers={"X-Request-ID": "frontend-abc_1.2"})

    assert response.headers["X-Request-ID"] == "frontend-abc_1.2"


@pytest.mark.parametrize("bad_id", ["a" * 65, "has space", "semi;colon", ""])
async def test_replaces_invalid_incoming_request_id(client: AsyncClient, bad_id: str) -> None:
    response = await client.get("/ping", headers={"X-Request-ID": bad_id})

    assert UUID(response.headers["X-Request-ID"]).version == 7


async def test_request_id_is_set_on_404(client: AsyncClient) -> None:
    response = await client.get("/does-not-exist")

    assert response.status_code == 404
    assert "X-Request-ID" in response.headers


async def test_access_log_has_request_id_status_and_duration(
    client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)

    response = await client.get("/ping?token=secret", headers={"X-Request-ID": "req-1"})

    [record] = access_records(caplog)
    assert record["request_id"] == "req-1"
    assert record["status"] == response.status_code == 200
    assert record["path"] == "/ping"
    assert record["duration_ms"] >= 0


async def test_concurrent_requests_keep_their_own_request_id(client: AsyncClient) -> None:
    responses = await asyncio.gather(
        *(client.get("/whoami", headers={"X-Request-ID": f"req-{i}"}) for i in range(10))
    )

    for i, response in enumerate(responses):
        assert response.json() == {"request_id": f"req-{i}"}


async def test_context_is_cleared_after_request(client: AsyncClient) -> None:
    await client.get("/ping", headers={"X-Request-ID": "req-1"})

    assert structlog.contextvars.get_contextvars() == {}


async def test_unhandled_exception_returns_500_problem_with_request_id(
    client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)

    # ASGITransport re-raises app exceptions: getting a response proves nothing escaped.
    response = await client.get("/crash", headers={"X-Request-ID": "req-500"})

    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == "req-500"
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.json()["request_id"] == "req-500"
    assert "secret internal state" not in response.text

    [error] = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert error.msg["request_id"] == "req-500"  # type: ignore[index]
    assert error.exc_info is not None
    [access] = access_records(caplog)
    assert access["status"] == 500


async def test_exception_after_response_started_is_reraised(client: AsyncClient) -> None:
    with pytest.raises(RuntimeError, match="stream broke"):
        await client.get("/crash-mid-stream")
