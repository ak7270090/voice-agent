from datetime import time
from typing import Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from studio_api.campaigns.constants import MAX_ATTEMPTS, MAX_CONCURRENT_CALLS
from studio_api.database import UtcDateTime
from studio_api.numbers.schemas import E164Number


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    agent_id: str
    from_number_id: str
    window_start: time = time(9, 0)
    window_end: time = time(20, 0)
    timezone: str = "Asia/Kolkata"
    # The LiveKit free plan runs 5 agent sessions at once.
    max_concurrent: int = Field(default=2, ge=1, le=MAX_CONCURRENT_CALLS)
    max_attempts: int = Field(default=3, ge=1, le=MAX_ATTEMPTS)
    retry_after_minutes: int = Field(default=30, ge=1, le=24 * 60)

    @field_validator("timezone")
    @classmethod
    def known_time_zone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as error:
            raise ValueError(f"unknown time zone {value!r}") from error
        return value

    @model_validator(mode="after")
    def window_ends_after_it_starts(self) -> Self:
        if self.window_end <= self.window_start:
            raise ValueError("the calling window must end after it starts")
        return self


class CampaignRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    agent_id: str
    from_number_id: str
    status: str
    window_start: time
    window_end: time
    timezone: str
    max_concurrent: int
    max_attempts: int
    retry_after_minutes: int
    created_at: UtcDateTime
    # Contacts per status, e.g. {"done": 3, "retry": 1}.
    counts: dict[str, int] = {}


class ContactCreate(BaseModel):
    phone: E164Number
    name: str = Field(default="", max_length=120)
    consent: bool = False
    variables: dict[str, str] = {}


class ContactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    phone: str
    name: str
    variables: dict[str, str]
    consent: bool
    status: str
    attempts: int
    next_attempt_at: UtcDateTime | None
    outcome: str | None
    updated_at: UtcDateTime


class RejectedRow(BaseModel):
    row: int
    reason: str


class ContactImport(BaseModel):
    added: int
    # Added but never dialled: no consent.
    skipped: int
    rejected: list[RejectedRow]
