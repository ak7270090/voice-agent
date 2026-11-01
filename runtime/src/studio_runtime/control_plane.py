"""The runtime's view of the API: an agent's settings at call start, and the call record."""

from typing import Any

import httpx
from pydantic import BaseModel

from studio_runtime.config import Settings
from studio_runtime.flows.schema import Flow
from studio_runtime.observability import TRACE_CONTEXT_HOOKS

INBOUND_DIRECTION = "inbound"
OUTBOUND_DIRECTION = "outbound"


class VoiceSettings(BaseModel):
    stt_model: str
    tts_model: str
    voice: str


class AgentConfig(BaseModel):
    id: str
    name: str
    instructions: str
    greeting: str
    voicemail_message: str = ""
    llm_model: str
    languages: list[str]
    language_settings: dict[str, VoiceSettings]
    knowledge_base_ids: list[str] = []
    flow: Flow | None = None
    flow_version: int | None = None
    # Values for the flow's {secret.NAME} placeholders; kept in memory for the call only.
    secrets: dict[str, str] = {}

    @property
    def starting_language(self) -> str:
        return self.languages[0]


class TranscriptTurn(BaseModel):
    role: str
    text: str
    # When it was said (Unix seconds).
    at: float | None = None


class CallRecord(BaseModel):
    transcript: list[TranscriptTurn]
    outcome: str | None = None
    fields: dict[str, Any] = {}
    flow_path: list[str] = []
    turn_latency_ms: list[dict[str, float]] = []
    # Agent replies the caller talked over: a high share means turn-taking cuts in or lags.
    interruptions: int = 0
    # Tokens, speech-to-text seconds and characters spoken; the API prices them.
    usage: dict[str, float] = {}
    tool_calls: list[dict[str, Any]] = []


class PhoneNumber(BaseModel):
    id: str
    number: str
    agent_id: str | None = None


class KnowledgeHit(BaseModel):
    document_name: str
    text: str
    score: float


class ControlPlaneClient:
    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http

    async def get_agent_config(self, agent_id: str, flow: str) -> AgentConfig:
        response = await self._http.get(f"/runtime/agents/{agent_id}", params={"flow": flow})
        response.raise_for_status()
        return AgentConfig.model_validate(response.json())

    async def get_phone_number(self, number_id: str) -> PhoneNumber:
        response = await self._http.get(f"/runtime/phone-numbers/{number_id}")
        response.raise_for_status()
        return PhoneNumber.model_validate(response.json())

    async def start_call(
        self,
        agent_id: str,
        room_name: str,
        channel: str,
        direction: str = INBOUND_DIRECTION,
        remote_number: str | None = None,
        campaign_contact_id: str | None = None,
        room_sid: str | None = None,
    ) -> str:
        call = {
            "agent_id": agent_id,
            "room_name": room_name,
            "channel": channel,
            "direction": direction,
            "remote_number": remote_number,
        }
        if campaign_contact_id is not None:
            call["campaign_contact_id"] = campaign_contact_id
        if room_sid:
            call["room_sid"] = room_sid
        response = await self._http.post("/runtime/calls", json=call)
        response.raise_for_status()
        return response.json()["id"]

    async def end_call(self, call_id: str, record: CallRecord) -> None:
        response = await self._http.post(
            f"/runtime/calls/{call_id}/end", json=record.model_dump(mode="json")
        )
        response.raise_for_status()

    async def search_knowledge(self, agent_id: str, query: str) -> list[KnowledgeHit]:
        response = await self._http.post(
            f"/runtime/agents/{agent_id}/knowledge-search", json={"query": query}
        )
        response.raise_for_status()
        return [KnowledgeHit.model_validate(hit) for hit in response.json()]

    async def aclose(self) -> None:
        await self._http.aclose()


def create_control_plane_client(settings: Settings) -> ControlPlaneClient:
    return ControlPlaneClient(
        httpx.AsyncClient(
            base_url=settings.api_url,
            headers={"Authorization": f"Bearer {settings.runtime_api_token}"},
            timeout=settings.api_timeout_seconds,
            # The API continues the call's trace (agent config, knowledge search, call record).
            event_hooks=TRACE_CONTEXT_HOOKS,
        )
    )
