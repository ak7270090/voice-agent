from types import SimpleNamespace

import httpx
from livekit.agents.llm import ChatMessage

from studio_voice.call import session as call_session
from studio_voice.call.session import run_call
from studio_voice.core.config import Settings
from studio_voice.worker import create_server


def test_server_takes_its_health_port_and_load_threshold_from_settings():
    server = create_server(Settings(health_port=9100, worker_load_threshold=0.9))

    assert server._port == 9100
    assert server._load_threshold == 0.9


def test_server_registers_the_call_handler_under_the_configured_agent_name():
    server = create_server(Settings(agent_name="studio-test"))

    assert server._agent_name == "studio-test"
    assert server._entrypoint_fnc is run_call


def test_a_campaign_contacts_details_fill_the_greeting_and_are_told_to_the_llm():
    config = SimpleNamespace(
        greeting="Hello {name}, about your {appointment_time} appointment.",
        voicemail_message="Hi {name}, please call us back.",
        instructions="Remind patients.",
    )

    call_session.personalise(config, {"name": "Asha", "appointment_time": "4 pm"})

    assert config.greeting == "Hello Asha, about your 4 pm appointment."
    assert config.voicemail_message == "Hi Asha, please call us back."
    assert config.instructions.endswith("name: Asha; appointment_time: 4 pm.")


def test_without_details_a_placeholder_is_left_out_not_said():
    config = SimpleNamespace(greeting="Hello {name}.", voicemail_message="", instructions="x")

    call_session.personalise(config, {})

    assert config.greeting == "Hello ."
    assert config.instructions == "x"


class UnreachableControlPlane:
    closed = False

    async def get_agent_config(self, agent_id: str, flow: str):
        raise httpx.ConnectError("api down")

    async def aclose(self) -> None:
        self.closed = True


class FakeJobContext:
    def __init__(self, metadata: str) -> None:
        self.job = SimpleNamespace(metadata=metadata)
        self.proc = SimpleNamespace(userdata={"tracer_provider": None})
        self.sent: list[tuple[str, str]] = []
        self.shut_down = False

        async def send_text(text: str, topic: str) -> None:
            self.sent.append((topic, text))

        self.room = SimpleNamespace(local_participant=SimpleNamespace(send_text=send_text))

    async def connect(self) -> None:
        pass

    def shutdown(self) -> None:
        self.shut_down = True


async def test_browser_call_for_an_agent_that_cannot_be_loaded_says_so_and_ends(monkeypatch):
    backend_client = UnreachableControlPlane()
    monkeypatch.setattr(call_session, "create_backend_client", lambda settings: backend_client)
    ctx = FakeJobContext('{"agent_id": "agent-1", "channel": "web"}')

    await run_call(ctx)

    assert ctx.sent == [
        (
            "lk.transcription",
            "Sorry, this agent is not available right now. Please try again later.",
        )
    ]
    assert ctx.shut_down
    assert backend_client.closed


class FakeSession:
    def __init__(self) -> None:
        self.handlers: dict = {}
        self.shut_down = False

    def on(self, event: str, handler) -> None:
        self.handlers[event] = handler

    def shutdown(self) -> None:
        self.shut_down = True


def test_the_call_ends_only_after_the_end_message_is_heard_in_full():
    session = FakeSession()
    runner = SimpleNamespace(ended=True, final_message="Booked: A-1001.")
    call_session.end_after_final_message(session, runner)
    cut_off = ChatMessage(role="assistant", content=["Booked: A-1001."], interrupted=True)
    heard = ChatMessage(role="assistant", content=["Booked: A-1001."])

    session.handlers["conversation_item_added"](SimpleNamespace(item=cut_off))
    assert not session.shut_down
    session.handlers["conversation_item_added"](SimpleNamespace(item=heard))
    assert session.shut_down
