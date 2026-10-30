import re
import socket
import zlib
from collections.abc import AsyncIterator

import httpx
import pytest
from langchain_core.embeddings import Embeddings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool, StaticPool

from studio_api.agents import models as agent_models  # noqa: F401 - registers the tables
from studio_api.calls import models as call_models  # noqa: F401 - registers the tables
from studio_api.config import get_settings
from studio_api.database import Base, create_session_factory
from studio_api.knowledge.constants import EMBEDDING_DIMENSIONS
from studio_api.main import create_app

RUNTIME_TOKEN = "test-runtime-token"
TEST_DATABASE = "studio_test"


class WordEmbeddings(Embeddings):
    """Bag of words hashed into the vector, so texts that share words are similar."""

    def _embed(self, text_value: str) -> list[float]:
        vector = [0.0] * EMBEDDING_DIMENSIONS
        for word in re.findall(r"\w+", text_value.lower()):
            vector[zlib.crc32(word.encode()) % EMBEDDING_DIMENSIONS] += 1.0
        vector[0] += 0.01  # never all zeros
        return vector

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(item) for item in texts]

    def embed_query(self, text_value: str) -> list[float]:
        return self._embed(text_value)


class MemoryFileStore:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    async def ensure_bucket(self) -> None:
        pass

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        self.files[key] = data

    async def get(self, key: str) -> bytes:
        return self.files[key]

    async def delete(self, key: str) -> None:
        self.files.pop(key, None)


class RecordingJobQueue:
    def __init__(self) -> None:
        self.jobs: list[tuple] = []

    async def enqueue(self, job_name: str, *args: object) -> None:
        self.jobs.append((job_name, *args))


@pytest.fixture
def settings(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "runtime_api_token", RUNTIME_TOKEN)
    monkeypatch.setattr(settings, "livekit_url", "wss://example.livekit.cloud")
    monkeypatch.setattr(settings, "livekit_api_key", "test-key")
    monkeypatch.setattr(settings, "livekit_api_secret", "test-secret-that-is-long-enough-for-hs256")
    return settings


@pytest.fixture
def file_store() -> MemoryFileStore:
    return MemoryFileStore()


@pytest.fixture
def job_queue() -> RecordingJobQueue:
    return RecordingJobQueue()


async def serve(engine: AsyncEngine, file_store, job_queue) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()
    app.state.session_factory = create_session_factory(engine)
    app.state.file_store = file_store
    app.state.job_queue = job_queue
    app.state.embeddings = WordEmbeddings()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        http.app = app
        yield http


@pytest.fixture
async def sqlite_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(
        "sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def client(
    settings, sqlite_engine, file_store, job_queue
) -> AsyncIterator[httpx.AsyncClient]:
    """The API on an in-memory SQLite database; no Docker needed."""
    async for http in serve(sqlite_engine, file_store, job_queue):
        yield http


def postgres_is_running() -> bool:
    try:
        with socket.create_connection(("localhost", 5432), timeout=0.5):
            return True
    except OSError:
        return False


@pytest.fixture
async def postgres_engine(settings) -> AsyncIterator[AsyncEngine]:
    """A throwaway `studio_test` database on the compose Postgres (vector search needs it)."""
    if not postgres_is_running():
        pytest.skip("docker compose Postgres is not running")
    admin = create_async_engine(
        settings.database_url, isolation_level="AUTOCOMMIT", poolclass=NullPool
    )
    async with admin.connect() as connection:
        await connection.execute(text(f"DROP DATABASE IF EXISTS {TEST_DATABASE} WITH (FORCE)"))
        await connection.execute(text(f"CREATE DATABASE {TEST_DATABASE}"))
    await admin.dispose()
    base_url = settings.database_url.rsplit("/", 1)[0]
    engine = create_async_engine(f"{base_url}/{TEST_DATABASE}", poolclass=NullPool)
    async with engine.begin() as connection:
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await connection.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def postgres_client(
    postgres_engine, file_store, job_queue
) -> AsyncIterator[httpx.AsyncClient]:
    async for http in serve(postgres_engine, file_store, job_queue):
        yield http


@pytest.fixture
def runtime_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {RUNTIME_TOKEN}"}
