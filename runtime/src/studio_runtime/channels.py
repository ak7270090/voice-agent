"""Which agent a call is for and how the caller joined, from the dispatch metadata.

Browser calls start as a text chat: with audio off the agent skips speech-to-text and voice, so
a typed chat costs only the LLM. The console's mic button turns voice on through an RPC.
"""

import json

from livekit import rtc
from livekit.agents import AgentSession
from pydantic import BaseModel, ValidationError

WEB_CHANNEL = "web"
PHONE_CHANNEL = "phone"
PUBLISHED_FLOW = "published"
SET_VOICE_RPC_METHOD = "set_voice"
VOICE_ON = "on"
VOICE_OFF = "off"
USER_ROLE = "user"


class InvalidCallMetadataError(ValueError):
    pass


class CallMetadata(BaseModel):
    agent_id: str
    channel: str = PHONE_CHANNEL
    # Console test calls run the draft flow; every other call the published one.
    flow: str = PUBLISHED_FLOW

    @property
    def is_web(self) -> bool:
        return self.channel == WEB_CHANNEL


def parse_call_metadata(job_metadata: str) -> CallMetadata:
    try:
        return CallMetadata.model_validate(json.loads(job_metadata or "{}"))
    except (json.JSONDecodeError, ValidationError) as error:
        raise InvalidCallMetadataError(
            f"dispatch metadata has no agent_id: {job_metadata!r}"
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
