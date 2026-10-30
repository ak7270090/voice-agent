from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from studio_api.agents.constants import AGENT_STATUSES
from studio_api.database import UtcDateTime


class VoiceSettings(BaseModel):
    """Models are "provider/model" strings, e.g. "openai/tts-1"."""

    stt_model: str
    tts_model: str
    voice: str


class AgentFields(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    instructions: str = Field(min_length=1)
    greeting: str = Field(min_length=1)
    llm_model: str = Field(min_length=1)
    languages: list[str] = Field(min_length=1)
    language_settings: dict[str, VoiceSettings]

    @model_validator(mode="after")
    def every_language_has_voice_settings(self) -> Self:
        missing = [code for code in self.languages if code not in self.language_settings]
        if missing:
            raise ValueError(f"language_settings is missing {missing}")
        return self


class AgentCreate(AgentFields):
    pass


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    instructions: str | None = Field(default=None, min_length=1)
    greeting: str | None = Field(default=None, min_length=1)
    llm_model: str | None = Field(default=None, min_length=1)
    languages: list[str] | None = Field(default=None, min_length=1)
    language_settings: dict[str, VoiceSettings] | None = None
    status: Literal[AGENT_STATUSES] | None = None


class AgentRead(AgentFields):
    model_config = ConfigDict(from_attributes=True)

    id: str
    template: str | None
    status: str
    created_at: UtcDateTime
    updated_at: UtcDateTime


class AgentTemplate(BaseModel):
    id: str
    name: str
    summary: str
    channel_label: str
    fields: AgentFields


class FromTemplateRequest(BaseModel):
    template_id: str
    name: str | None = None


class BrowserCall(BaseModel):
    url: str
    token: str
    room: str


class RuntimeAgentConfig(BaseModel):
    """Everything the runtime needs to run a call for this agent."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    instructions: str
    greeting: str
    llm_model: str
    languages: list[str]
    language_settings: dict[str, VoiceSettings]
