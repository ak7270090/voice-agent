"""Tokens for test calls from the console: each one joins a new room and dispatches the runtime
into it with {"agent_id": ..., "channel": "web"}, so the call starts as a text chat."""

import json
from datetime import timedelta
from uuid import uuid4

from livekit import api

from studio_api.agents.constants import (
    BROWSER_CALL_IDENTITY_PREFIX,
    BROWSER_CALL_PARTICIPANT_NAME,
    BROWSER_CALL_ROOM_PREFIX,
    WEB_CHANNEL,
)
from studio_api.agents.schemas import BrowserCall
from studio_api.config import Settings


def build_browser_call(settings: Settings, agent_id: str) -> BrowserCall:
    room_name = f"{BROWSER_CALL_ROOM_PREFIX}{uuid4().hex[:10]}"
    dispatch = api.RoomAgentDispatch(
        agent_name=settings.runtime_agent_name,
        metadata=json.dumps({"agent_id": agent_id, "channel": WEB_CHANNEL}),
    )
    token = (
        api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(f"{BROWSER_CALL_IDENTITY_PREFIX}{uuid4().hex[:8]}")
        .with_name(BROWSER_CALL_PARTICIPANT_NAME)
        .with_ttl(timedelta(minutes=settings.browser_call_token_ttl_minutes))
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
        .with_room_config(api.RoomConfiguration(agents=[dispatch]))
        .to_jwt()
    )
    return BrowserCall(url=settings.livekit_url, token=token, room=room_name)
