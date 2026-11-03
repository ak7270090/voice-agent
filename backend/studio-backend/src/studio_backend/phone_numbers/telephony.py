"""LiveKit's telephony side of a number: SIP trunks, the dispatch rule that starts the runtime
for each incoming call, and the dispatch that places an outgoing one.

Incoming: provider → inbound trunk (accepts calls to the number) → dispatch rule (a new room per
call, the runtime dispatched with {"number_id": ...}). Outgoing: the runtime is dispatched into a
new room with the number to dial and the outbound trunk, and dials it itself (so it can listen
for a voicemail greeting from the first word).
"""

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Request
from livekit import api

from studio_backend.config import Settings
from studio_backend.phone_numbers.constants import (
    INBOUND_CALL_ROOM_PREFIX,
    LIVEKIT_RESOURCE_PREFIX,
    PHONE_CHANNEL,
)
from studio_backend.phone_numbers.schemas import OutboundTrunk

TelephonyError = api.TwirpError


class Telephony:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @asynccontextmanager
    async def _livekit(self) -> AsyncIterator[api.LiveKitAPI]:
        client = api.LiveKitAPI(
            self._settings.livekit_url,
            self._settings.livekit_api_key,
            self._settings.livekit_api_secret,
        )
        try:
            yield client
        finally:
            await client.aclose()

    async def create_inbound_trunk(self, number: str) -> str:
        request = api.CreateSIPInboundTrunkRequest(
            trunk=api.SIPInboundTrunkInfo(
                name=f"{LIVEKIT_RESOURCE_PREFIX} {number} in",
                numbers=[number],
                # Encrypted audio (SRTP) as well as plain: Linphone encrypts by default, and
                # with plain-only LiveKit heard nothing and dropped the call after ~20 s.
                media_encryption=api.SIPMediaEncryption.SIP_MEDIA_ENCRYPT_ALLOW,
            )
        )
        async with self._livekit() as livekit:
            return (await livekit.sip.create_inbound_trunk(request)).sip_trunk_id

    async def create_outbound_trunk(self, number: str, outbound: OutboundTrunk) -> str:
        request = api.CreateSIPOutboundTrunkRequest(
            trunk=api.SIPOutboundTrunkInfo(
                name=f"{LIVEKIT_RESOURCE_PREFIX} {number} out",
                address=outbound.address,
                numbers=[number],
                auth_username=outbound.username,
                auth_password=outbound.password,
                # Offers encrypted audio too: Linphone refused plain-only with 488.
                media_encryption=api.SIPMediaEncryption.SIP_MEDIA_ENCRYPT_ALLOW,
            )
        )
        async with self._livekit() as livekit:
            return (await livekit.sip.create_outbound_trunk(request)).sip_trunk_id

    async def create_dispatch_rule(self, number_id: str, number: str, trunk_id: str | None) -> str:
        dispatch = api.RoomAgentDispatch(
            agent_name=self._settings.runtime_agent_name,
            metadata=json.dumps({"number_id": number_id, "channel": PHONE_CHANNEL}),
        )
        request = api.CreateSIPDispatchRuleRequest(
            dispatch_rule=api.SIPDispatchRuleInfo(
                name=f"{LIVEKIT_RESOURCE_PREFIX} {number}",
                # Empty for a LiveKit number: the rule is assigned to the number instead.
                trunk_ids=[trunk_id] if trunk_id else [],
                rule=api.SIPDispatchRule(
                    dispatch_rule_individual=api.SIPDispatchRuleIndividual(
                        room_prefix=INBOUND_CALL_ROOM_PREFIX
                    )
                ),
                room_config=api.RoomConfiguration(agents=[dispatch]),
            )
        )
        async with self._livekit() as livekit:
            return (await livekit.sip.create_dispatch_rule(request)).sip_dispatch_rule_id

    async def delete(self, dispatch_rule_id: str | None, trunk_ids: list[str]) -> None:
        async with self._livekit() as livekit:
            if dispatch_rule_id:
                await livekit.sip.delete_dispatch_rule(
                    api.DeleteSIPDispatchRuleRequest(sip_dispatch_rule_id=dispatch_rule_id)
                )
            for trunk_id in trunk_ids:
                await livekit.sip.delete_trunk(api.DeleteSIPTrunkRequest(sip_trunk_id=trunk_id))

    async def dispatch_outbound_call(self, room: str, metadata: dict) -> None:
        request = api.CreateAgentDispatchRequest(
            agent_name=self._settings.runtime_agent_name, room=room, metadata=json.dumps(metadata)
        )
        async with self._livekit() as livekit:
            await livekit.agent_dispatch.create_dispatch(request)


def get_telephony(request: Request) -> Telephony:
    return request.app.state.telephony
