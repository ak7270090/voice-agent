from contextlib import asynccontextmanager

import httpx
import pytest

from studio_backend.health import build_dependency_checks


class FakeConnection:
    def __init__(self, executed: list[str]) -> None:
        self.executed = executed

    async def execute(self, statement) -> None:
        self.executed.append(str(statement))


class FakeEngine:
    def __init__(self) -> None:
        self.executed: list[str] = []

    @asynccontextmanager
    async def connect(self):
        yield FakeConnection(self.executed)


class FakeRedis:
    async def ping(self) -> bool:
        return True


def build_checks(engine: FakeEngine, answers: dict[str, int]) -> dict:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(answers.get(str(request.url), 404))
    )
    return build_dependency_checks(
        engine,
        FakeRedis(),
        httpx.AsyncClient(transport=transport),
        "http://storage:9000",
        "http://runtime:8081/",
    )


async def test_database_check_runs_a_query():
    engine = FakeEngine()

    await build_checks(engine, {})["database"]()

    assert engine.executed == ["SELECT 1"]


async def test_storage_and_runtime_checks_call_their_health_urls():
    checks = build_checks(
        FakeEngine(),
        {"http://storage:9000/health": 200, "http://runtime:8081/": 200},
    )

    await checks["storage"]()
    await checks["runtime"]()
    assert await checks["redis"]() is True


async def test_url_check_fails_when_the_service_answers_with_an_error():
    checks = build_checks(FakeEngine(), {"http://runtime:8081/": 503})

    with pytest.raises(httpx.HTTPStatusError):
        await checks["runtime"]()
