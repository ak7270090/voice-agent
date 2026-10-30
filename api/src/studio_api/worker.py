"""Background worker: `arq studio_api.worker.WorkerSettings`. Ingests uploaded documents."""

from sqlalchemy.ext.asyncio import create_async_engine

from studio_api.config import export_provider_keys, get_settings
from studio_api.database import create_session_factory
from studio_api.embeddings import create_embeddings
from studio_api.jobs import build_redis_settings
from studio_api.knowledge.ingestion import ingest_document
from studio_api.storage import create_file_store


async def startup(ctx: dict) -> None:
    settings = get_settings()
    export_provider_keys()
    ctx["engine"] = create_async_engine(settings.database_url, pool_pre_ping=True)
    ctx["session_factory"] = create_session_factory(ctx["engine"])
    ctx["file_store"] = create_file_store(settings)
    ctx["embeddings"] = create_embeddings(settings)


async def shutdown(ctx: dict) -> None:
    await ctx["engine"].dispose()


async def ingest_document_job(ctx: dict, document_id: str) -> None:
    await ingest_document(
        ctx["session_factory"], ctx["file_store"], ctx["embeddings"], get_settings(), document_id
    )


class WorkerSettings:
    functions = [ingest_document_job]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = build_redis_settings(get_settings())
