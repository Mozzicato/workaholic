import asyncio
from collections.abc import Awaitable
from typing import Literal

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["health"])

_DEPENDENCY_TIMEOUT_SECONDS = 2.0

DependencyStatus = Literal["ok", "unavailable"]


class HealthResponse(BaseModel):
    status: Literal["ok"]


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: dict[str, DependencyStatus]


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness: the process is up. Deliberately checks nothing else."""
    return HealthResponse(status="ok")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse}},
)
async def ready(request: Request) -> JSONResponse:
    """Readiness: configured dependencies are reachable. Never calls AI providers."""
    probes: dict[str, Awaitable[object]] = {"database": request.app.state.database.ping()}
    if request.app.state.redis is not None:
        probes["redis"] = request.app.state.redis.ping()

    statuses = await asyncio.gather(*(_check(name, probe) for name, probe in probes.items()))
    checks = dict(zip(probes, statuses, strict=True))
    is_ready = all(status == "ok" for status in checks.values())
    body = ReadinessResponse(status="ready" if is_ready else "not_ready", checks=checks)
    return JSONResponse(status_code=200 if is_ready else 503, content=body.model_dump())


async def _check(name: str, probe: Awaitable[object]) -> DependencyStatus:
    try:
        await asyncio.wait_for(probe, timeout=_DEPENDENCY_TIMEOUT_SECONDS)
    except Exception as exc:
        logger.warning("readiness_check_failed", dependency=name, error_type=type(exc).__name__)
        return "unavailable"
    return "ok"
