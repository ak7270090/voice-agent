from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from studio_api.agents import models as agent_models  # noqa: F401 - registers the tables
from studio_api.calls import models as call_models  # noqa: F401 - registers the tables
from studio_api.config import get_settings
from studio_api.database import Base, create_session_factory
from studio_api.main import create_app

RUNTIME_TOKEN = "test-runtime-token"


@pytest.fixture
def settings(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "runtime_api_token", RUNTIME_TOKEN)
    monkeypatch.setattr(settings, "livekit_url", "wss://example.livekit.cloud")
    monkeypatch.setattr(settings, "livekit_api_key", "test-key")
    monkeypatch.setattr(settings, "livekit_api_secret", "test-secret-that-is-long-enough-for-hs256")
    return settings


@pytest.fixture
async def client(settings) -> AsyncIterator[httpx.AsyncClient]:
    """The API on an in-memory SQLite database; no Docker needed."""
    engine = create_async_engine(
        "sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    app = create_app()
    app.state.session_factory = create_session_factory(engine)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http
    await engine.dispose()


@pytest.fixture
def runtime_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {RUNTIME_TOKEN}"}
