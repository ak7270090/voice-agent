"""What can change during a call: voice on or off, and a caller who has gone quiet.

Browser calls start as a text chat: with audio off the agent skips speech-to-text and voice, so
a typed chat costs only the LLM. The dashboard's mic button turns voice on through an RPC.
"""

from livekit import rtc
from livekit.agents import AgentSession, UserStateChangedEvent

SET_VOICE_RPC_METHOD = "set_voice"
VOICE_ON = "on"
VOICE_OFF = "off"
USER_ROLE = "user"
AWAY_STATE = "away"
SPEAKING_STATE = "speaking"


def set_voice(session: AgentSession, enabled: bool) -> None:
    if not enabled:
        session.interrupt()
    session.input.set_audio_enabled(enabled)
    session.output.set_audio_enabled(enabled)


def caller_has_spoken(session: AgentSession) -> bool:
    return any(getattr(item, "role", None) == USER_ROLE for item in session.history.items)


def register_voice_toggle(room: rtc.Room, session: AgentSession, greeting: str) -> None:
    """The dashboard calls `set_voice` with "on" or "off" when the tester presses the mic button.

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
