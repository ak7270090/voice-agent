"""FastAPI application: run with `uvicorn studio_api.main:app`."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import create_async_engine

from studio_api.agents.router import router as agents_router
from studio_api.agents.router import runtime_router as agents_runtime_router
from studio_api.calls.router import router as calls_router
from studio_api.calls.router import runtime_router as calls_runtime_router
from studio_api.config import get_settings
from studio_api.database import create_session_factory
from studio_api.health import build_dependency_checks
from studio_api.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    redis = Redis.from_url(settings.redis_url)
    http = httpx.AsyncClient(timeout=settings.health_check_timeout_seconds)
    app.state.session_factory = create_session_factory(engine)
    app.state.dependency_checks = build_dependency_checks(
        engine, redis, http, settings.s3_endpoint, settings.runtime_health_url
    )
    yield
    await http.aclose()
    await redis.aclose()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="Voice Agent Studio API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for router in (
        health_router,
        agents_router,
        agents_runtime_router,
        calls_router,
        calls_runtime_router,
    ):
        app.include_router(router)
    return app


app = create_app()
