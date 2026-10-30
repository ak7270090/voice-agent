from types import SimpleNamespace

import pytest

from studio_runtime.channels import (
    InvalidCallMetadataError,
    parse_call_metadata,
    register_voice_toggle,
    set_voice,
)


class FakeAudioSwitch:
    def __init__(self) -> None:
        self.enabled: bool | None = None

    def set_audio_enabled(self, enabled: bool) -> None:
        self.enabled = enabled


class FakeSession:
    def __init__(self, roles: tuple[str, ...] = ("assistant",)) -> None:
        self.input = FakeAudioSwitch()
        self.output = FakeAudioSwitch()
        self.interrupted = False
        self.history = SimpleNamespace(items=[SimpleNamespace(role=role) for role in roles])
        self.said: list[str] = []

    def interrupt(self) -> None:
        self.interrupted = True

    def say(self, text: str, add_to_chat_ctx: bool = True) -> None:
        self.said.append(text)


def test_browser_metadata_names_the_agent_and_the_web_channel():
    metadata = parse_call_metadata('{"agent_id": "agent-1", "channel": "web"}')

    assert metadata.agent_id == "agent-1"
    assert metadata.is_web


def test_metadata_without_a_channel_is_a_phone_call():
    assert not parse_call_metadata('{"agent_id": "agent-1"}').is_web


@pytest.mark.parametrize("raw", ["", "not json", '{"channel": "web"}'])
def test_metadata_without_an_agent_is_rejected(raw):
    with pytest.raises(InvalidCallMetadataError):
        parse_call_metadata(raw)


def test_turning_voice_off_interrupts_and_mutes_both_directions():
    session = FakeSession()

    set_voice(session, enabled=False)

    assert session.interrupted
    assert session.input.enabled is False
    assert session.output.enabled is False


def toggle_for(session: FakeSession):
    handlers = {}
    participant = SimpleNamespace(register_rpc_method=lambda name, fn: handlers.update({name: fn}))
    register_voice_toggle(SimpleNamespace(local_participant=participant), session, "Welcome!")
    return handlers["set_voice"]


async def test_mic_on_before_the_caller_spoke_turns_voice_on_and_says_the_greeting():
    session = FakeSession()

    answer = await toggle_for(session)(SimpleNamespace(payload="on"))

    assert answer == "on"
    assert session.input.enabled is True
    assert not session.interrupted
    assert session.said == ["Welcome!"]


async def test_mic_on_after_the_caller_typed_does_not_repeat_the_greeting():
    session = FakeSession(roles=("assistant", "user", "assistant"))

    await toggle_for(session)(SimpleNamespace(payload="on"))

    assert session.said == []
