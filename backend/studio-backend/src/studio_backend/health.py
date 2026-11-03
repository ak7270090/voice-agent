"""Health endpoint: whether the API can reach Postgres, Redis, object storage and the runtime."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Annotated, Literal

import httpx
from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from studio_backend.config import SettingsDep

DependencyCheck = Callable[[], Awaitable[object]]

HEALTHY = "ok"
STORAGE_LIVENESS_PATH = "/health"

router = APIRouter(tags=["health"])


class HealthReport(BaseModel):
    status: Literal["ok", "degraded"]
    dependencies: dict[str, str]


def build_dependency_checks(
    engine: AsyncEngine,
    redis: Redis,
    http: httpx.AsyncClient,
    storage_endpoint: str,
    runtime_health_url: str,
) -> dict[str, DependencyCheck]:
    async def check_database() -> None:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    def url_check(url: str) -> DependencyCheck:
        async def check_url() -> None:
            response = await http.get(url)
            response.raise_for_status()

        return check_url

    return {
        "database": check_database,
        "redis": redis.ping,
        "storage": url_check(f"{storage_endpoint}{STORAGE_LIVENESS_PATH}"),
        "runtime": url_check(runtime_health_url),
    }


def get_dependency_checks(request: Request) -> dict[str, DependencyCheck]:
    return request.app.state.dependency_checks


DependencyChecksDep = Annotated[dict[str, DependencyCheck], Depends(get_dependency_checks)]


async def _run_check(check: DependencyCheck, timeout_seconds: float) -> str:
    try:
        async with asyncio.timeout(timeout_seconds):
            await check()
    except Exception as error:  # any failure means the dependency is unhealthy
        return f"error: {type(error).__name__}"
    return HEALTHY


@router.get("/health")
async def read_health(
    checks: DependencyChecksDep, settings: SettingsDep, response: Response
) -> HealthReport:
    results = await asyncio.gather(
        *(_run_check(check, settings.health_check_timeout_seconds) for check in checks.values())
    )
    dependencies = dict(zip(checks, results, strict=True))
    healthy = all(result == HEALTHY for result in results)
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthReport(status="ok" if healthy else "degraded", dependencies=dependencies)
