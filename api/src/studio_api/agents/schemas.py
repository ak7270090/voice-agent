from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from studio_api.agents.constants import AGENT_STATUSES, ANALYSIS_FIELD_TYPES, CHOICE_FIELD
from studio_api.database import UtcDateTime
from studio_api.flows.schemas import Flow, Identifier


class VoiceSettings(BaseModel):
    """Models are "provider/model" strings, e.g. "openai/tts-1"."""

    stt_model: str
    tts_model: str
    voice: str


class AnalysisField(BaseModel):
    """A question the post-call analysis answers for every call, e.g. "asked_about_fees",
    yes/no, "Did the caller ask what the visit costs?"."""

    name: Identifier
    type: Literal[ANALYSIS_FIELD_TYPES] = "text"
    description: str = Field(min_length=1)
    # The allowed answers of a "choice" field.
    choices: list[str] = []

    @model_validator(mode="after")
    def choices_go_with_choice(self) -> Self:
        if (self.type == CHOICE_FIELD) != bool(self.choices):
            raise ValueError("a choice field needs choices, and only a choice field has them")
        return self


class AgentFields(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    instructions: str = Field(min_length=1)
    greeting: str = Field(min_length=1)
    voicemail_message: str = ""
    llm_model: str = Field(min_length=1)
    languages: list[str] = Field(min_length=1)
    language_settings: dict[str, VoiceSettings]
    analysis_fields: list[AnalysisField] = []
    # When a call counts as successful, in plain words; empty: the analysis judges by the goal.
    success_rule: str = ""

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
    voicemail_message: str | None = None
    llm_model: str | None = Field(default=None, min_length=1)
    languages: list[str] | None = Field(default=None, min_length=1)
    language_settings: dict[str, VoiceSettings] | None = None
    status: Literal[AGENT_STATUSES] | None = None
    knowledge_base_ids: list[str] | None = None
    analysis_fields: list[AnalysisField] | None = None
    success_rule: str | None = None


class AgentRead(AgentFields):
    model_config = ConfigDict(from_attributes=True)

    id: str
    template: str | None
    status: str
    knowledge_base_ids: list[str]
    published_flow_version: int | None
    has_flow: bool
    created_at: UtcDateTime
    updated_at: UtcDateTime


class AgentTemplate(BaseModel):
    id: str
    name: str
    summary: str
    channel_label: str
    fields: AgentFields
    flow: Flow | None = None


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
    voicemail_message: str
    llm_model: str
    languages: list[str]
    language_settings: dict[str, VoiceSettings]
    knowledge_base_ids: list[str]
    # The draft for console test calls, the published flow otherwise; None for prompt-only.
    flow: Flow | None = None
    flow_version: int | None = None
    # Values of the secrets the flow's tools name ({secret.NAME}); no others.
    secrets: dict[str, str] = {}
