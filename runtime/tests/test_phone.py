from types import SimpleNamespace

import pytest
from livekit import api
from livekit.agents import AMDCategory

from studio_runtime import worker
from studio_runtime.phone import (
    PhoneLine,
    answer,
    caller_line,
    ring,
    transfer,
    transfer_uri,
)


class FakeSip:
    def __init__(self, refuse: bool = False) -> None:
        self.refuse = refuse
        self.requests: list = []

    def _maybe_refuse(self, request) -> None:
        self.requests.append(request)
        if self.refuse:
            raise api.TwirpError("unavailable", "busy", status=503, metadata={"sip_status": "486"})

    async def create_sip_participant(self, request) -> None:
        self._maybe_refuse(request)

    async def transfer_sip_participant(self, request) -> None:
        self._maybe_refuse(request)


class FakeSpeech:
    def __init__(self) -> None:
        self.done_callbacks: list = []

    def add_done_callback(self, callback) -> None:
        self.done_callbacks.append(callback)

    def finish(self) -> None:
        for callback in self.done_callbacks:
            callback(self)

    def __await__(self):
        self.finish()
        yield from ()


class FakeSession:
    def __init__(self) -> None:
        self.said: list[str] = []
        self.speeches: list[FakeSpeech] = []
        self.interrupted = False
        self.shut_down = False

    def say(self, text: str, **options) -> FakeSpeech:
        self.said.append(text)
        self.speeches.append(FakeSpeech())
        return self.speeches[-1]

    def interrupt(self) -> None:
        self.interrupted = True

    def shutdown(self) -> None:
        self.shut_down = True


@pytest.mark.parametrize(
    ("destination", "uri"),
    [("+914412345678", "tel:+914412345678"), ("sip:desk@pbx.example", "sip:desk@pbx.example")],
)
def test_transfers_go_to_a_tel_or_sip_uri(destination, uri):
    assert transfer_uri(destination) == uri


def test_the_callers_number_comes_from_the_sip_participant():
    participant = SimpleNamespace(identity="sip_1", attributes={"sip.phoneNumber": "+9198"})

    assert caller_line(participant) == PhoneLine(remote_number="+9198", identity="sip_1")


async def test_ringing_without_detection_counts_whoever_answers_as_a_person():
    sip = FakeSip()

    category = await ring(SimpleNamespace(sip=sip), "out-1", "+9198", "ST_1", "", FakeSession())

    assert category == AMDCategory.HUMAN
    assert sip.requests[0].sip_call_to == "+9198"
    assert sip.requests[0].sip_trunk_id == "ST_1"
    assert sip.requests[0].wait_until_answered


async def test_a_call_nobody_answers_has_no_category():
    livekit = SimpleNamespace(sip=FakeSip(refuse=True))

    assert await ring(livekit, "out-1", "+9198", "ST_1", "", FakeSession()) is None


def test_a_person_hears_the_greeting_first():
    session = FakeSession()

    outcome = answer(session, AMDCategory.HUMAN, "Hi, this is City Clinic.", "Please call back.")

    assert outcome is None
    assert session.interrupted
    assert session.said == ["Hi, this is City Clinic."]
    assert not session.shut_down


def test_a_voicemail_gets_the_message_then_the_call_ends():
    session = FakeSession()

    outcome = answer(session, AMDCategory.MACHINE_VM, "Hi.", "Please call City Clinic back.")

    assert outcome == "voicemail_left"
    assert session.said == ["Please call City Clinic back."]
    assert not session.shut_down
    session.speeches[0].finish()
    assert session.shut_down


@pytest.mark.parametrize(
    ("category", "message", "outcome"),
    [
        (AMDCategory.MACHINE_VM, "", "answering_machine"),
        (AMDCategory.MACHINE_UNAVAILABLE, "Call back.", "answering_machine"),
        (None, "Call back.", "not_answered"),
    ],
)
def test_otherwise_the_agent_hangs_up_without_speaking(category, message, outcome):
    session = FakeSession()

    assert answer(session, category, "Hi.", message) == outcome
    assert session.said == []
    assert session.shut_down


async def test_a_transfer_hands_the_sip_caller_to_the_destination():
    sip = FakeSip()

    moved = await transfer(SimpleNamespace(sip=sip), "call-1", "sip_1", "+914412345678")

    assert moved
    assert sip.requests[0].participant_identity == "sip_1"
    assert sip.requests[0].transfer_to == "tel:+914412345678"


async def hand_over(refuse: bool, line: PhoneLine, transfer_to: str = "+914412345678"):
    sip = FakeSip(refuse=refuse)
    ctx = SimpleNamespace(api=SimpleNamespace(sip=sip), room=SimpleNamespace(name="call-1"))
    session = FakeSession()
    runner = SimpleNamespace(transfer_to=transfer_to)
    await worker.hand_over_or_hang_up(ctx, session, runner, line, "Sorry, try later.")
    return session, sip


async def test_after_the_transfer_message_the_caller_is_handed_over():
    line = PhoneLine(identity="sip_1")

    session, sip = await hand_over(refuse=False, line=line)

    assert line.outcome == "transferred"
    assert session.said == []
    assert session.shut_down


async def test_a_failed_transfer_is_said_before_hanging_up():
    line = PhoneLine(identity="sip_1")

    session, _ = await hand_over(refuse=True, line=line)

    assert line.outcome == "transfer_failed"
    assert session.said == ["Sorry, try later."]
    assert session.shut_down


async def test_a_browser_call_at_a_transfer_just_ends():
    line = PhoneLine()

    session, sip = await hand_over(refuse=False, line=line)

    assert sip.requests == []
    assert line.outcome is None
    assert session.shut_down


class NumberControlPlane:
    def __init__(self, agent_id: str | None) -> None:
        self.agent_id = agent_id

    async def get_phone_number(self, number_id: str):
        return SimpleNamespace(number="+14155550100", agent_id=self.agent_id)


async def test_an_incoming_call_is_answered_by_the_agent_bound_to_the_number_now():
    metadata = SimpleNamespace(agent_id=None, number_id="n-1")

    assert await worker.agent_for(NumberControlPlane("agent-2"), metadata) == "agent-2"
    with pytest.raises(LookupError):
        await worker.agent_for(NumberControlPlane(None), metadata)
