from pydantic import BaseModel, ConfigDict, Field

from studio_api.database import UtcDateTime
from studio_api.secrets.constants import SECRET_VALUE_MAX_LENGTH


class SecretWrite(BaseModel):
    value: str = Field(min_length=1, max_length=SECRET_VALUE_MAX_LENGTH)


class SecretRead(BaseModel):
    """Never the value: only its name and a preview."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    preview: str
    created_at: UtcDateTime
    updated_at: UtcDateTime
