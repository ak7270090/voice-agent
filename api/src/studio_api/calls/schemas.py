from typing import Literal

from pydantic import BaseModel, ConfigDict

from studio_api.calls.constants import CHANNELS, TRANSCRIPT_ROLES
from studio_api.database import UtcDateTime


class TranscriptTurn(BaseModel):
    role: Literal[TRANSCRIPT_ROLES]
    text: str


class CallStart(BaseModel):
    agent_id: str
    room_name: str
    channel: Literal[CHANNELS]


class CallEnd(BaseModel):
    transcript: list[TranscriptTurn] = []


class CallRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str
    room_name: str
    channel: str
    status: str
    started_at: UtcDateTime
    ended_at: UtcDateTime | None
    transcript: list[TranscriptTurn]
