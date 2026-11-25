from typing import Any, Literal

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel

from app.core.problem_details import PROBLEM_JSON, ProblemDetail

SCHEMA_REF = "#/components/schemas/{model}"


class FieldError(BaseModel):
    loc: list[str | int]
    msg: str
    type: str


class ValidationProblem(ProblemDetail):
    code: Literal["validation_error"] = "validation_error"
    errors: list[FieldError]


def install_problem_openapi(app: FastAPI) -> None:
    """Document 422 as the body `validation_error_handler` really sends, not FastAPI's default."""

    def openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title, version=app.version, routes=app.routes, description=app.description
        )
        components = schema.setdefault("components", {}).setdefault("schemas", {})
        for model in (FieldError, ProblemDetail, ValidationProblem):
            model_schema = model.model_json_schema(ref_template=SCHEMA_REF)
            components.update(model_schema.pop("$defs", {}))
            components[model.__name__] = model_schema
        components.pop("HTTPValidationError", None)
        components.pop("ValidationError", None)

        problem_ref = {"$ref": SCHEMA_REF.format(model=ValidationProblem.__name__)}
        for operation in _operations(schema):
            response = operation.get("responses", {}).get("422")
            if response is not None:
                response["content"] = {PROBLEM_JSON: {"schema": problem_ref}}

        app.openapi_schema = schema
        return schema

    app.openapi = openapi  # type: ignore[method-assign]


def _operations(schema: dict[str, Any]) -> list[dict[str, Any]]:
    paths: dict[str, dict[str, Any]] = schema.get("paths", {})
    return [op for item in paths.values() for op in item.values() if isinstance(op, dict)]
