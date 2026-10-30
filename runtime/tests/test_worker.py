from types import SimpleNamespace

from studio_runtime.config import Settings
from studio_runtime.worker import create_server, run_call


def test_server_takes_its_health_port_and_load_threshold_from_settings():
    server = create_server(Settings(health_port=9100, worker_load_threshold=0.9))

    assert server._port == 9100
    assert server._load_threshold == 0.9


def test_server_registers_the_call_handler_under_the_configured_agent_name():
    server = create_server(Settings(agent_name="studio-test"))

    assert server._agent_name == "studio-test"
    assert server._entrypoint_fnc is run_call


async def test_call_handler_joins_the_room():
    joined = []

    async def connect() -> None:
        joined.append(True)

    await run_call(SimpleNamespace(connect=connect, room=SimpleNamespace(name="room-1")))

    assert joined == [True]
