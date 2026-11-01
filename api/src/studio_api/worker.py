"""Background worker: `arq studio_api.worker.WorkerSettings`. Ingests uploaded documents and
runs the campaign dialler."""

from datetime import timedelta

from arq import cron
from sqlalchemy.ext.asyncio import create_async_engine

from studio_api.calls.analysis import run_analysis
from studio_api.campaigns.dialler import run_dialler
from studio_api.config import export_provider_keys, get_settings
from studio_api.database import create_session_factory, utc_now
from studio_api.embeddings import create_embeddings
from studio_api.jobs import build_redis_settings
from studio_api.knowledge.ingestion import ingest_document
from studio_api.numbers.telephony import Telephony
from studio_api.storage import create_file_store

SECONDS_PER_MINUTE = 60


async def startup(ctx: dict) -> None:
    settings = get_settings()
    export_provider_keys()
    ctx["engine"] = create_async_engine(settings.database_url, pool_pre_ping=True)
    ctx["session_factory"] = create_session_factory(ctx["engine"])
    ctx["file_store"] = create_file_store(settings)
    ctx["embeddings"] = create_embeddings(settings)
    ctx["telephony"] = Telephony(settings)


async def shutdown(ctx: dict) -> None:
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
    await run_analysis(ctx["session_factory"], get_settings(), call_id)


def dialler_seconds() -> set[int]:
    return set(range(0, SECONDS_PER_MINUTE, get_settings().dialler_interval_seconds))


class WorkerSettings:
    functions = [ingest_document_job, analyse_call_job]
    # unique: one dialler pass at a time, even with several workers.
    cron_jobs = [cron(dial_campaigns_job, second=dialler_seconds(), unique=True)]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = build_redis_settings(get_settings())
