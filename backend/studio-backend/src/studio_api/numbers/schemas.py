from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from studio_api.database import UtcDateTime
from studio_api.numbers.constants import E164_PATTERN, LIVEKIT_PROVIDER, PROVIDERS

E164Number = Annotated[str, Field(pattern=E164_PATTERN)]


class OutboundTrunk(BaseModel):
    """The provider's SIP termination: sent to LiveKit once, never stored here."""

    # A host name such as "example.pstn.twilio.com", not a sip: URI.
    address: str = Field(min_length=1, max_length=200)
    username: str = ""
    password: str = ""


class PhoneNumberCreate(BaseModel):
    number: E164Number
    label: str = Field(default="", max_length=120)
    provider: Literal[PROVIDERS]
    agent_id: str | None = None
    outbound: OutboundTrunk | None = None

    @model_validator(mode="after")
    def livekit_numbers_take_no_outbound_trunk(self) -> Self:
        if self.provider == LIVEKIT_PROVIDER and self.outbound is not None:
            raise ValueError("numbers rented from LiveKit cannot call out yet")
        return self


class PhoneNumberUpdate(BaseModel):
    label: str | None = Field(default=None, max_length=120)
    agent_id: str | None = None


class PhoneNumberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    number: str
    label: str
    provider: str
    agent_id: str | None
    dispatch_rule_id: str
    can_call_out: bool
    can_transfer: bool
    created_at: UtcDateTime


class RuntimeNumber(BaseModel):
    """What the runtime needs when a call to this number starts."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    number: str
    agent_id: str | None


class OutboundCallStart(BaseModel):
    to_number: E164Number
    from_number_id: str


class OutboundCall(BaseModel):
    room: str
