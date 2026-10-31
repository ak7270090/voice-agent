"""Phone calls over LiveKit SIP: who is on the line, ringing out with voicemail detection, and
handing the caller to a person.

An incoming call's caller joins the room as a SIP participant before the agent; an outgoing call
is dialled by the agent itself, after its session starts, so LiveKit's answering-machine
detection hears the first word ("Hello?" or "You've reached ...").
"""

import logging
from dataclasses import dataclass

from livekit import api, rtc
from livekit.agents import AMD, AgentSession, AMDCategory

logger = logging.getLogger(__name__)

SIP_PHONE_ATTRIBUTE = "sip.phoneNumber"
CALLEE_IDENTITY = "callee"
TEL_SCHEME = "tel:"
SIP_SCHEMES = ("sip:", "sips:")
# A person, or a greeting too short or unclear to call a machine: talk.
TALK_TO = (AMDCategory.HUMAN, AMDCategory.UNCERTAIN)

NOT_ANSWERED_OUTCOME = "not_answered"
VOICEMAIL_LEFT_OUTCOME = "voicemail_left"
ANSWERING_MACHINE_OUTCOME = "answering_machine"
TRANSFERRED_OUTCOME = "transferred"
TRANSFER_FAILED_OUTCOME = "transfer_failed"


@dataclass
class PhoneLine:
    """The phone side of a call; `outcome` overrides the flow's when the call ends here."""

    remote_number: str | None = None
    identity: str | None = None
    outcome: str | None = None


def caller_line(participant: rtc.RemoteParticipant) -> PhoneLine:
    return PhoneLine(
        remote_number=participant.attributes.get(SIP_PHONE_ATTRIBUTE) or None,
        identity=participant.identity,
    )


def transfer_uri(destination: str) -> str:
    """ "+919876543210" → "tel:+919876543210"; a sip: address is used as it is."""
    return destination if destination.startswith(SIP_SCHEMES) else f"{TEL_SCHEME}{destination}"


async def ring(
    livekit: api.LiveKitAPI,
    room_name: str,
    to_number: str,
    trunk_id: str,
    amd_llm_model: str,
    session: AgentSession,
) -> AMDCategory | None:
    """Rings `to_number` and returns who answered; None when nobody did (busy, no answer,
    declined). With no detection model, anyone who answers counts as a person."""
    request = api.CreateSIPParticipantRequest(
        room_name=room_name,
        sip_trunk_id=trunk_id,
        sip_call_to=to_number,
        participant_identity=CALLEE_IDENTITY,
        wait_until_answered=True,
    )
    if not amd_llm_model:
        return AMDCategory.HUMAN if await _dial(livekit, request) else None
    # Started before dialling so no audio is missed; it listens once the call is answered.
    async with AMD(
        session,
        llm=amd_llm_model,
        stt=None,
        participant_identity=CALLEE_IDENTITY,
        ivr_detection=False,
        suppress_compatibility_warning=True,
    ) as detector:
        if not await _dial(livekit, request):
            return None
        return (await detector.execute()).category


async def _dial(livekit: api.LiveKitAPI, request: api.CreateSIPParticipantRequest) -> bool:
    try:
        await livekit.sip.create_sip_participant(request)
    except api.TwirpError as error:
        logger.info(
            "call to %s not answered: %s %s", request.sip_call_to, error.code, error.metadata
        )
        return False
    return True


def answer(
    session: AgentSession, category: AMDCategory | None, greeting: str, voicemail_message: str
) -> str | None:
    """Greets a person, or leaves the voicemail message on a machine and hangs up. Returns the
    call's outcome when it ends here (None: the conversation goes on)."""
    if category in TALK_TO:
        # The person's "Hello?" may already have a reply queued: the greeting goes first.
        session.interrupt()
        session.say(greeting)
        return None
    if category == AMDCategory.MACHINE_VM and voicemail_message:
        session.say(voicemail_message, allow_interruptions=False).add_done_callback(
            lambda _: session.shutdown()
        )
        return VOICEMAIL_LEFT_OUTCOME
    session.shutdown()
    return NOT_ANSWERED_OUTCOME if category is None else ANSWERING_MACHINE_OUTCOME


async def transfer(
    livekit: api.LiveKitAPI, room_name: str, identity: str, destination: str
) -> bool:
    """Hands the caller to `destination` (a cold transfer: the agent leaves the call)."""
    request = api.TransferSIPParticipantRequest(
        room_name=room_name,
        participant_identity=identity,
        transfer_to=transfer_uri(destination),
        play_dialtone=False,
    )
    try:
        await livekit.sip.transfer_sip_participant(request)
    except api.TwirpError as error:
        logger.warning("transfer to %s failed: %s %s", destination, error.code, error.message)
        return False
    return True
