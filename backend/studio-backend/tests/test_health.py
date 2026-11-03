import asyncio
import socket

import pytest
from fastapi.testclient import TestClient
from studio_backend.config import get_settings
from studio_backend.health import get_dependency_checks
from studio_backend.main import create_app


async def passing_check() -> None:
    return None


async def failing_check() -> None:
    raise ConnectionError("refused")


async def hanging_check() -> None:
    await asyncio.sleep(10)


def client_with_checks(checks: dict) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_dependency_checks] = lambda: checks
    return TestClient(app)


def test_health_is_ok_when_every_dependency_answers():
    response = client_with_checks({"database": passing_check, "redis": passing_check}).get(
        "/health"
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "dependencies": {"database": "ok", "redis": "ok"},
    }


def test_health_is_degraded_and_names_the_failing_dependency():
    response = client_with_checks({"database": passing_check, "redis": failing_check}).get(
        "/health"
    )

    assert response.status_code == 503
    assert response.json()["dependencies"] == {
        "database": "ok",
        "redis": "error: ConnectionError",
    }


def test_health_reports_a_hanging_dependency_as_timed_out(monkeypatch):
    monkeypatch.setattr(get_settings(), "health_check_timeout_seconds", 0.05)

    response = client_with_checks({"storage": hanging_check}).get("/health")

    assert response.status_code == 503
    assert response.json()["dependencies"] == {"storage": "error: TimeoutError"}


def local_stack_is_running() -> bool:
    try:
        with socket.create_connection(("localhost", 5432), timeout=0.5):
            return True
    except OSError:
        return False


@pytest.mark.skipif(not local_stack_is_running(), reason="docker compose stack is not running")
def test_health_reaches_the_real_services_of_the_running_stack():
    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.json() == {
        "status": "ok",
        "dependencies": {"database": "ok", "redis": "ok", "storage": "ok", "runtime": "ok"},
    }
