"""Background worker: `arq studio_backend.worker.WorkerSettings`. Ingests uploaded documents, runs
the campaign dialler, analyses calls and sends their after-call actions."""

from datetime import timedelta

import httpx
from arq import cron
from sqlalchemy.ext.asyncio import create_async_engine

from studio_backend.after_call.constants import CALL_ANALYSED, DELIVER_JOB
from studio_backend.after_call.service import deliver, schedule_deliveries
from studio_backend.calls.analysis import run_analysis
from studio_backend.calls.models import Call
from studio_backend.campaigns.dialler import run_dialler
from studio_backend.config import export_provider_keys, get_settings
from studio_backend.database import create_session_factory, utc_now
from studio_backend.jobs import build_redis_settings
from studio_backend.knowledge.embeddings import create_embeddings
from studio_backend.knowledge.ingestion import ingest_document
from studio_backend.knowledge.storage import create_file_store
from studio_backend.phone_numbers.telephony import Telephony

SECONDS_PER_MINUTE = 60


async def startup(ctx: dict) -> None:
    settings = get_settings()
    export_provider_keys()
    ctx["engine"] = create_async_engine(settings.database_url, pool_pre_ping=True)
    ctx["session_factory"] = create_session_factory(ctx["engine"])
    ctx["file_store"] = create_file_store(settings)
    ctx["embeddings"] = create_embeddings(settings)
    ctx["telephony"] = Telephony(settings)
    ctx["http"] = httpx.AsyncClient(timeout=settings.delivery_timeout_seconds)


async def shutdown(ctx: dict) -> None:
    await ctx["http"].aclose()
    await ctx["engine"].dispose()


async def ingest_document_job(ctx: dict, document_id: str) -> None:
    await ingest_document(
        ctx["session_factory"], ctx["file_store"], ctx["embeddings"], get_settings(), document_id
    )


async def dial_campaigns_job(ctx: dict) -> None:
    settings = get_settings()
    async with ctx["session_factory"]() as session:
        await run_dialler(
            session,
            ctx["telephony"],
            utc_now(),
            timedelta(minutes=settings.campaign_call_timeout_minutes),
        )


async def analyse_call_job(ctx: dict, call_id: str) -> None:
    if not await run_analysis(ctx["session_factory"], get_settings(), call_id):
        return
    async with ctx["session_factory"]() as session:
        call = await session.get(Call, call_id)
        for delivery_id in await schedule_deliveries(session, call, CALL_ANALYSED):
            await ctx["redis"].enqueue_job(DELIVER_JOB, delivery_id)


async def deliver_job(ctx: dict, delivery_id: str) -> None:
    """A failed attempt is tried again later as a new job, until the attempts run out."""
    retry_in = await deliver(ctx["session_factory"], get_settings(), ctx["http"], delivery_id)
    if retry_in is not None:
        await ctx["redis"].enqueue_job(
            DELIVER_JOB, delivery_id, _defer_by=timedelta(seconds=retry_in)
        )


def dialler_seconds() -> set[int]:
    return set(range(0, SECONDS_PER_MINUTE, get_settings().dialler_interval_seconds))


class WorkerSettings:
    functions = [ingest_document_job, analyse_call_job, deliver_job]
    # unique: one dialler pass at a time, even with several workers.
    cron_jobs = [cron(dial_campaigns_job, second=dialler_seconds(), unique=True)]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = build_redis_settings(get_settings())
