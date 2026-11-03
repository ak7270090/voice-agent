"""Which agent a call is for and how the caller joined, from the dispatch metadata.

Browser calls start as a text chat: with audio off the agent skips speech-to-text and voice, so
a typed chat costs only the LLM. The console's mic button turns voice on through an RPC.
"""

import json
from typing import Self

from livekit import rtc
from livekit.agents import AgentSession, UserStateChangedEvent
from pydantic import BaseModel, ValidationError, model_validator

WEB_CHANNEL = "web"
PHONE_CHANNEL = "phone"
PUBLISHED_FLOW = "published"
SET_VOICE_RPC_METHOD = "set_voice"
VOICE_ON = "on"
VOICE_OFF = "off"
USER_ROLE = "user"
AWAY_STATE = "away"
SPEAKING_STATE = "speaking"


class InvalidCallMetadataError(ValueError):
    pass


class CallMetadata(BaseModel):
    # Browser and outgoing calls name the agent; an incoming phone call names the number
    # dialled (its dispatch rule), and the API says which agent answers it now.
    agent_id: str | None = None
    number_id: str | None = None
    channel: str = PHONE_CHANNEL
    # Console test calls run the draft flow; every other call the published one.
    flow: str = PUBLISHED_FLOW
    # Outgoing calls: the number to ring, through this outbound trunk.
    dial_to: str | None = None
    outbound_trunk_id: str | None = None
    # Campaign calls: the contact being called, and what is known about them ({name}, ...).
    campaign_contact_id: str | None = None
    variables: dict[str, str] = {}

    @model_validator(mode="after")
    def names_an_agent_or_a_number(self) -> Self:
        if self.agent_id is None and self.number_id is None:
            raise ValueError("needs agent_id or number_id")
        if (self.dial_to is None) != (self.outbound_trunk_id is None):
            raise ValueError("dial_to and outbound_trunk_id go together")
        return self

    @property
    def is_web(self) -> bool:
        return self.channel == WEB_CHANNEL

    @property
    def is_outbound(self) -> bool:
        return self.dial_to is not None


def parse_call_metadata(job_metadata: str) -> CallMetadata:
    try:
        return CallMetadata.model_validate(json.loads(job_metadata or "{}"))
    except (json.JSONDecodeError, ValidationError) as error:
        raise InvalidCallMetadataError(
            f"dispatch metadata names no agent or number: {job_metadata!r}"
        ) from error


def set_voice(session: AgentSession, enabled: bool) -> None:
    if not enabled:
        session.interrupt()
    session.input.set_audio_enabled(enabled)
    session.output.set_audio_enabled(enabled)


def caller_has_spoken(session: AgentSession) -> bool:
    return any(getattr(item, "role", None) == USER_ROLE for item in session.history.items)


def register_voice_toggle(room: rtc.Room, session: AgentSession, greeting: str) -> None:
    """The console calls `set_voice` with "on" or "off" when the tester presses the mic button.

    A web call starts as chat, so its greeting was only shown; turning the mic on before saying
    anything speaks it, as a phone caller would hear it."""

    async def handle_set_voice(invocation: rtc.RpcInvocationData) -> str:
        enabled = invocation.payload == VOICE_ON
        set_voice(session, enabled)
        if enabled and not caller_has_spoken(session):
            session.say(greeting, add_to_chat_ctx=False)
        return VOICE_ON if enabled else VOICE_OFF

    room.local_participant.register_rpc_method(SET_VOICE_RPC_METHOD, handle_set_voice)


def register_idle_caller(session: AgentSession, still_there: str, goodbye: str) -> None:
    """A voice caller who goes quiet (LiveKit marks them "away" after `user_away_timeout`) is
    asked once if they are still there; quiet again, the agent says goodbye and hangs up. A
    typed chat is never asked: with the mic off there is no speech to wait for."""
    asked = False

    def on_user_state_changed(event: UserStateChangedEvent) -> None:
        nonlocal asked
        if event.new_state == SPEAKING_STATE:
            asked = False
        if event.new_state != AWAY_STATE or not session.input.audio_enabled:
            return
        if not asked:
            asked = True
            session.say(still_there)
            return
        session.say(goodbye).add_done_callback(lambda _: session.shutdown())

    session.on("user_state_changed", on_user_state_changed)
