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
    def __init__(self) -> None:
        self.input = FakeAudioSwitch()
        self.output = FakeAudioSwitch()
        self.interrupted = False

    def interrupt(self) -> None:
        self.interrupted = True


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


async def test_mic_button_rpc_turns_voice_on():
    session = FakeSession()
    handlers = {}
    participant = SimpleNamespace(register_rpc_method=lambda name, fn: handlers.update({name: fn}))
    register_voice_toggle(SimpleNamespace(local_participant=participant), session)

    answer = await handlers["set_voice"](SimpleNamespace(payload="on"))

    assert answer == "on"
    assert session.input.enabled is True
    assert not session.interrupted
