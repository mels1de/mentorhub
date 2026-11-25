from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.core.openapi import ValidationProblem
from app.core.problem_details import PROBLEM_JSON


@pytest.fixture
async def schema(app: FastAPI, client: AsyncClient) -> dict[str, Any]:
    @app.get("/items/{item_id}")
    async def get_item(item_id: int) -> dict[str, int]:
        return {"id": item_id}

    response = await client.get("/openapi.json")
    assert response.status_code == 200
    result: dict[str, Any] = response.json()
    return result


async def test_422_is_documented_as_validation_problem(schema: dict[str, Any]) -> None:
    response = schema["paths"]["/items/{item_id}"]["get"]["responses"]["422"]

    assert response["content"] == {
        PROBLEM_JSON: {"schema": {"$ref": "#/components/schemas/ValidationProblem"}}
    }


async def test_default_validation_schemas_are_replaced(schema: dict[str, Any]) -> None:
    components = schema["components"]["schemas"]

    assert {"ProblemDetail", "ValidationProblem", "FieldError"} <= components.keys()
    assert "HTTPValidationError" not in components
    assert "ValidationError" not in components
    assert components["ValidationProblem"]["properties"]["errors"]["items"] == {
        "$ref": "#/components/schemas/FieldError"
    }


async def test_real_422_body_matches_documented_model(
    schema: dict[str, Any], client: AsyncClient
) -> None:
    response = await client.get("/items/not-a-number")

    assert response.status_code == 422
    problem = ValidationProblem.model_validate(response.json())
    assert problem.errors[0].loc == ["path", "item_id"]
