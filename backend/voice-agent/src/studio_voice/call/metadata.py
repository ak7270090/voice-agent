"""Which agent a call is for and how the caller joined, from the dispatch metadata."""

import json
from typing import Self

from pydantic import BaseModel, ValidationError, model_validator

WEB_CHANNEL = "web"
PHONE_CHANNEL = "phone"
PUBLISHED_FLOW = "published"


class InvalidCallMetadataError(ValueError):
    pass


class CallMetadata(BaseModel):
    # Browser and outgoing calls name the agent; an incoming phone call names the number
    # dialled (its dispatch rule), and the backend says which agent answers it now.
    agent_id: str | None = None
    number_id: str | None = None
    channel: str = PHONE_CHANNEL
    # Dashboard test calls run the draft flow; every other call the published one.
    flow: str = PUBLISHED_FLOW
    # Outgoing calls: the number to ring, through this outbound trunk.
    dial_to: str | None = None
    outbound_trunk_id: str | None = None
    # Campaign calls: the contact being called, and what is known about them ({name}, ...).
    campaign_contact_id: str | None = None
    variables: dict[str, str] = {}

    @model_validator(mode="after")
    def names_an_agent_or_a_number(self) -> Self:
        if self.agent_id is None and self.number_id is None:
            raise ValueError("needs agent_id or number_id")
        if (self.dial_to is None) != (self.outbound_trunk_id is None):
            raise ValueError("dial_to and outbound_trunk_id go together")
        return self

    @property
    def is_web(self) -> bool:
        return self.channel == WEB_CHANNEL

    @property
    def is_outbound(self) -> bool:
        return self.dial_to is not None


def parse_call_metadata(job_metadata: str) -> CallMetadata:
    try:
        return CallMetadata.model_validate(json.loads(job_metadata or "{}"))
    except (json.JSONDecodeError, ValidationError) as error:
        raise InvalidCallMetadataError(
            f"dispatch metadata names no agent or number: {job_metadata!r}"
        ) from error
