from typing import Literal, Self
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from studio_api.after_call.constants import (
    ACTION_KINDS,
    ACTIONS_NEEDING_A_SECRET,
    CALL_ANALYSED,
    EVENTS,
    GOOGLE_SHEETS_ACTION,
    WEBHOOK_ACTION,
)
from studio_api.database import UtcDateTime
from studio_api.secrets.constants import SECRET_NAME_PATTERN


def new_action_id() -> str:
    return uuid4().hex[:8]


class AfterCallAction(BaseModel):
    """Sends each call's result somewhere once it ends or is analysed."""

    id: str = Field(default_factory=new_action_id, min_length=1, max_length=36)
    kind: Literal[ACTION_KINDS]
    event: Literal[EVENTS] = CALL_ANALYSED
    enabled: bool = True
    # Webhooks: where to POST the call.
    url: str = ""
    # The stored secret it uses: a webhook's signing secret (optional), the Slack webhook URL,
    # the HubSpot private app token, or the Google service account's JSON key.
    secret: str = Field(default="", pattern=f"({SECRET_NAME_PATTERN})|^$")
    # Google Sheets: the ID in the sheet's link (/spreadsheets/d/<id>/edit), and its tab.
    spreadsheet_id: str = ""
    sheet_name: str = "Sheet1"

    @model_validator(mode="after")
    def has_what_its_kind_needs(self) -> Self:
        if self.kind == WEBHOOK_ACTION and not self.url.startswith(("http://", "https://")):
            raise ValueError("a webhook needs an http(s) URL")
        if self.kind in ACTIONS_NEEDING_A_SECRET and not self.secret:
            raise ValueError(f"a {self.kind} action needs the secret it sends with")
        if self.kind == GOOGLE_SHEETS_ACTION and not self.spreadsheet_id:
            raise ValueError("a google_sheets action needs the spreadsheet ID")
        return self


class DeliveryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    call_id: str
    action_id: str
    kind: str
    event: str
    status: str
    attempts: int
    response_status: int | None
    last_error: str
    created_at: UtcDateTime
    updated_at: UtcDateTime
