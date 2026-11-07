import asyncio
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.api import health
from app.api.health import HealthCheck, get_health_checks


@dataclass
class FakeCheck:
    name: str
    error: Exception | None = None
    hang: bool = False

    async def check(self) -> None:
        if self.hang:
            await asyncio.Event().wait()
        if self.error:
            raise self.error


@pytest.fixture
def use_checks(app: FastAPI) -> Callable[..., None]:
    def override(*checks: HealthCheck) -> None:
        def get_checks() -> Sequence[HealthCheck]:
            return checks

        app.dependency_overrides[get_health_checks] = get_checks

    return override


async def test_live_passes(client: AsyncClient) -> None:
    response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "pass"}
    assert "X-Request-ID" in response.headers


async def test_ready_passes_without_checks(client: AsyncClient) -> None:
    response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "pass", "checks": {}}


async def test_ready_passes_when_all_checks_pass(
    client: AsyncClient, use_checks: Callable[..., None]
) -> None:
    use_checks(FakeCheck("database"), FakeCheck("redis"))

    response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "pass",
        "checks": {"database": "pass", "redis": "pass"},
    }


async def test_ready_is_503_when_a_check_fails(
    client: AsyncClient, use_checks: Callable[..., None], caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING)
    use_checks(FakeCheck("database", error=ConnectionError("pg at 10.0.0.5 refused")))

    response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "fail", "checks": {"database": "fail"}}
    assert "10.0.0.5" not in response.text
    [record] = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert record.msg["check"] == "database"  # type: ignore[index]
    assert isinstance(record.msg["exc_info"], ConnectionError)  # type: ignore[index]


async def test_ready_fails_a_hanging_check_by_timeout(
    client: AsyncClient, use_checks: Callable[..., None], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(health, "CHECK_TIMEOUT_SECONDS", 0.01)
    use_checks(FakeCheck("database", hang=True), FakeCheck("redis"))

    response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["checks"] == {"database": "fail", "redis": "pass"}


async def test_metrics_count_requests_but_not_probes(app: FastAPI, client: AsyncClient) -> None:
    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"status": "ok"}

    await client.get("/ping")
    await client.get("/health/live")
    await client.get("/health/ready")

    response = await client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert 'handler="/ping"' in response.text
    assert 'handler="/health' not in response.text
    assert 'handler="/metrics"' not in response.text


async def test_metrics_is_hidden_from_openapi(client: AsyncClient) -> None:
    paths = (await client.get("/openapi.json")).json()["paths"]

    assert "/metrics" not in paths
    assert "503" in paths["/health/ready"]["get"]["responses"]
