from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from studio_backend.calls.constants import (
    CHANNELS,
    DIRECTIONS,
    INBOUND_DIRECTION,
    TRANSCRIPT_ROLES,
)
from studio_backend.database import UtcDateTime


class TranscriptTurn(BaseModel):
    role: Literal[TRANSCRIPT_ROLES]
    text: str
    # When it was said (Unix seconds); None for calls recorded before this was kept.
    at: float | None = None


class CallStart(BaseModel):
    agent_id: str
    room_name: str
    channel: Literal[CHANNELS]
    direction: Literal[DIRECTIONS] = INBOUND_DIRECTION
    remote_number: str | None = Field(default=None, max_length=20)
    campaign_contact_id: str | None = None
    room_sid: str | None = Field(default=None, max_length=40)


class CallEnd(BaseModel):
    transcript: list[TranscriptTurn] = []
    outcome: str | None = None
    fields: dict[str, Any] = {}
    flow_path: list[str] = []
    turn_latency_ms: list[dict[str, float]] = []
    interruptions: int = Field(default=0, ge=0)
    usage: dict[str, float] = {}
    tool_calls: list[dict[str, Any]] = []


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
    room_sid: str | None
    usage: dict[str, float]
    cost: dict[str, float | bool]
    tool_calls: list[dict[str, Any]]
    analysis_status: str | None
    analysis: dict[str, Any]
    # Filled by the router from settings.
    langfuse_url: str | None = None
    recording_url: str | None = None


class DayCount(BaseModel):
    day: str
    calls: int


class AgentSuccess(BaseModel):
    agent_id: str
    name: str
    calls: int
    analysed: int
    successful: int


class Metrics(BaseModel):
    days: list[DayCount]
    calls: int
    outcomes: dict[str, int]
    average_cost: float | None
    total_cost: float
    average_duration_seconds: float | None
    latency_p50_ms: float | None
    latency_p95_ms: float | None
    agents: list[AgentSuccess]
