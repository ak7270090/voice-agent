from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from studio_api.calls.constants import (
    CHANNELS,
    DIRECTIONS,
    INBOUND_DIRECTION,
    TRANSCRIPT_ROLES,
)
from studio_api.database import UtcDateTime


class TranscriptTurn(BaseModel):
    role: Literal[TRANSCRIPT_ROLES]
    text: str


class CallStart(BaseModel):
    agent_id: str
    room_name: str
    channel: Literal[CHANNELS]
    direction: Literal[DIRECTIONS] = INBOUND_DIRECTION
    remote_number: str | None = Field(default=None, max_length=20)
    campaign_contact_id: str | None = None


class CallEnd(BaseModel):
    transcript: list[TranscriptTurn] = []
    outcome: str | None = None
    fields: dict[str, Any] = {}
    flow_path: list[str] = []
    turn_latency_ms: list[dict[str, float]] = []
    interruptions: int = Field(default=0, ge=0)


class CallRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str
    room_name: str
    channel: str
    direction: str
    remote_number: str | None
    campaign_contact_id: str | None
    status: str
    started_at: UtcDateTime
    ended_at: UtcDateTime | None
    transcript: list[TranscriptTurn]
    outcome: str | None
    fields: dict[str, Any]
    flow_path: list[str]
    turn_latency_ms: list[dict[str, float]]
    interruptions: int
