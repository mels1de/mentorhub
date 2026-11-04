import logging

import pytest
from fastapi import FastAPI, HTTPException
from httpx import AsyncClient
from pydantic import BaseModel, Field

from app.core.exceptions import AppError, AuthenticationError, NotFoundError
from app.core.problem_details import PROBLEM_JSON, PROBLEM_TYPE_BASE


class SkillNotFoundError(NotFoundError):
    code = "skill_not_found"


class Registration(BaseModel):
    password: str = Field(min_length=12)
    age: int


@pytest.fixture(autouse=True)
def routes(app: FastAPI) -> None:
    @app.get("/skills/{skill_id}")
    async def get_skill(skill_id: int) -> None:
        raise SkillNotFoundError(f"Skill {skill_id} not found", extensions={"skill_id": skill_id})

    @app.get("/override")
    async def override() -> None:
        raise NotFoundError(extensions={"status": 999, "type": "evil", "title": "x"})

    @app.get("/app-500")
    async def app_500() -> None:
        raise AppError("db password=hunter2")

    @app.get("/auth")
    async def auth() -> None:
        raise AuthenticationError

    @app.get("/http-exc")
    async def http_exc() -> None:
        raise HTTPException(status_code=418, detail="No coffee here", headers={"X-Extra": "1"})

    @app.post("/register")
    async def register(body: Registration) -> None: ...


async def test_domain_error_is_problem_details(client: AsyncClient) -> None:
    response = await client.get("/skills/42", headers={"X-Request-ID": "req-1"})

    assert response.status_code == 404
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.json() == {
        "type": PROBLEM_TYPE_BASE + "skill_not_found",
        "title": "Not Found",
        "status": 404,
        "detail": "Skill 42 not found",
        "instance": "/skills/42",
        "code": "skill_not_found",
        "skill_id": 42,
        "request_id": "req-1",
    }


async def test_extensions_cannot_override_standard_members(client: AsyncClient) -> None:
    response = await client.get("/override")

    body = response.json()
    assert response.status_code == body["status"] == 404
    assert body["type"] == PROBLEM_TYPE_BASE + "not_found"
    assert body["title"] == "Not Found"


async def test_5xx_app_error_hides_detail_and_logs_it(
    client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.ERROR)

    response = await client.get("/app-500")

    assert response.status_code == 500
    assert "detail" not in response.json()
    assert "hunter2" not in response.text
    [record] = [r for r in caplog.records if r.levelno == logging.ERROR]
    # structlog keeps exc_info in the event dict; ProcessorFormatter renders the traceback.
    assert isinstance(record.msg["exc_info"], AppError)  # type: ignore[index]


async def test_401_has_www_authenticate(client: AsyncClient) -> None:
    response = await client.get("/auth")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json()["code"] == "not_authenticated"


async def test_unknown_route_is_about_blank(client: AsyncClient) -> None:
    response = await client.get("/does-not-exist")

    assert response.status_code == 404
    assert response.headers["content-type"] == PROBLEM_JSON
    body = response.json()
    assert body["type"] == "about:blank"
    assert body["title"] == "Not Found"
    assert "detail" not in body  # Starlette's detail only repeats the title
    assert "code" not in body


async def test_405_keeps_allow_header(client: AsyncClient) -> None:
    response = await client.delete("/auth")

    assert response.status_code == 405
    assert response.headers["Allow"] == "GET"


async def test_http_exception_keeps_detail_and_headers(client: AsyncClient) -> None:
    response = await client.get("/http-exc")

    assert response.status_code == 418
    assert response.headers["X-Extra"] == "1"
    assert response.json()["detail"] == "No coffee here"


async def test_validation_error_lists_fields_without_echoing_input(client: AsyncClient) -> None:
    response = await client.post("/register", json={"password": "secret123", "age": "old"})

    assert response.status_code == 422
    assert response.headers["content-type"] == PROBLEM_JSON
    body = response.json()
    assert body["code"] == "validation_error"
    assert {tuple(e["loc"]) for e in body["errors"]} == {("body", "password"), ("body", "age")}
    assert all(set(e) == {"loc", "msg", "type"} for e in body["errors"])
    assert "secret123" not in response.text
