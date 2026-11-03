"""FastAPI application: run with `uvicorn studio_api.main:app`."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import create_async_engine

from studio_api.after_call.router import router as after_call_router
from studio_api.agents.router import router as agents_router
from studio_api.agents.router import runtime_router as agents_runtime_router
from studio_api.calls.router import router as calls_router
from studio_api.calls.router import runtime_router as calls_runtime_router
from studio_api.campaigns.router import router as campaigns_router
from studio_api.config import export_provider_keys, get_settings
from studio_api.database import create_session_factory
from studio_api.demo_clinic.router import router as demo_clinic_router
from studio_api.embeddings import create_embeddings
from studio_api.flows.router import router as flows_router
from studio_api.health import build_dependency_checks
from studio_api.health import router as health_router
from studio_api.jobs import create_job_queue
from studio_api.knowledge.router import router as knowledge_router
from studio_api.knowledge.router import runtime_router as knowledge_runtime_router
from studio_api.numbers.router import router as numbers_router
from studio_api.numbers.router import runtime_router as numbers_runtime_router
from studio_api.numbers.telephony import Telephony
from studio_api.secrets.router import router as secrets_router
from studio_api.storage import create_file_store
from studio_api.tracing import create_tracer_provider, find_langfuse_project, trace_requests

logger = logging.getLogger(__name__)


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
    app.state.file_store = create_file_store(settings)
    try:
        await app.state.file_store.ensure_bucket()
    except (BotoCoreError, ClientError):
        logger.warning("object storage unreachable; uploads fail until it is up", exc_info=True)
    export_provider_keys()
    app.state.embeddings = create_embeddings(settings)
    app.state.job_queue = await create_job_queue(settings)
    app.state.telephony = Telephony(settings)
    app.state.langfuse_project_id = await find_langfuse_project(settings, http)
    yield
    await app.state.job_queue.aclose()
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
        after_call_router,
        knowledge_router,
        knowledge_runtime_router,
        flows_router,
        numbers_router,
        numbers_runtime_router,
        campaigns_router,
        secrets_router,
        demo_clinic_router,
    ):
        app.include_router(router)
    trace_requests(app, create_tracer_provider(get_settings()))
    return app


app = create_app()
