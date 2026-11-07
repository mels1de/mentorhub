import asyncio
from collections.abc import Sequence
from typing import Annotated, Literal, Protocol

import structlog
from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel

logger = structlog.stdlib.get_logger(__name__)

CHECK_TIMEOUT_SECONDS = 2.0

type CheckStatus = Literal["pass", "fail"]


class HealthCheck(Protocol):
    @property
    def name(self) -> str: ...

    async def check(self) -> None:
        """Return if the dependency is usable, raise otherwise."""
        ...


class LiveResponse(BaseModel):
    status: Literal["pass"] = "pass"


class ReadyResponse(BaseModel):
    status: CheckStatus
    checks: dict[str, CheckStatus]


def get_health_checks() -> Sequence[HealthCheck]:
    return ()


router = APIRouter(prefix="/health", tags=["health"])


# Liveness must not touch dependencies: a DB outage would make the orchestrator restart every pod.
@router.get("/live")
async def live() -> LiveResponse:
    return LiveResponse()


@router.get(
    "/ready",
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadyResponse}},
)
async def ready(
    response: Response,
    checks: Annotated[Sequence[HealthCheck], Depends(get_health_checks)],
) -> ReadyResponse:
    results = await asyncio.gather(*(_run(check) for check in checks))
    healthy = all(result == "pass" for result in results)
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadyResponse(
        status="pass" if healthy else "fail",
        checks={check.name: result for check, result in zip(checks, results, strict=True)},
    )


async def _run(check: HealthCheck) -> CheckStatus:
    try:
        async with asyncio.timeout(CHECK_TIMEOUT_SECONDS):
            await check.check()
    except Exception as exc:
        # The reason goes to the log only: the response is public.
        logger.warning("health_check_failed", check=check.name, exc_info=exc)
        return "fail"
    return "pass"
