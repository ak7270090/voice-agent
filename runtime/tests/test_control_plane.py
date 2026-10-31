import json

import httpx
import pytest

from studio_runtime.config import Settings
from studio_runtime.control_plane import (
    CallRecord,
    ControlPlaneClient,
    TranscriptTurn,
    create_control_plane_client,
)

AGENT = {
    "id": "agent-1",
    "name": "Front desk",
    "instructions": "Be helpful.",
    "greeting": "Hello!",
    "llm_model": "openai:gpt-4.1-mini",
    "languages": ["en"],
    "language_settings": {
        "en": {
            "stt_model": "openai/gpt-4o-mini-transcribe",
            "tts_model": "openai/tts-1",
            "voice": "alloy",
        }
    },
}


def client_answering(handler) -> tuple[ControlPlaneClient, list[httpx.Request]]:
    requests: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return handler(request)

    http = httpx.AsyncClient(transport=httpx.MockTransport(record), base_url="http://api")
    return ControlPlaneClient(http), requests


async def test_agent_config_is_read_from_the_runtime_endpoint():
    client, requests = client_answering(lambda request: httpx.Response(200, json=AGENT))

    config = await client.get_agent_config("agent-1", "draft")

    assert requests[0].url.path == "/runtime/agents/agent-1"
    assert requests[0].url.params["flow"] == "draft"
    assert config.starting_language == "en"
    assert config.language_settings["en"].voice == "alloy"


async def test_missing_agent_raises():
    client, _ = client_answering(lambda request: httpx.Response(404))

    with pytest.raises(httpx.HTTPStatusError):
        await client.get_agent_config("missing", "published")


async def test_call_is_started_and_ended_with_its_transcript():
    client, requests = client_answering(lambda request: httpx.Response(201, json={"id": "call-1"}))

    call_id = await client.start_call("agent-1", "web-abc", "web")
    await client.end_call(
        call_id,
        CallRecord(transcript=[TranscriptTurn(role="user", text="Hi")], outcome="booked"),
    )
    await client.aclose()

    assert call_id == "call-1"
    assert json.loads(requests[0].content) == {
        "agent_id": "agent-1",
        "room_name": "web-abc",
        "channel": "web",
        "direction": "inbound",
        "remote_number": None,
    }
    assert requests[1].url.path == "/runtime/calls/call-1/end"
    assert json.loads(requests[1].content) == {
        "transcript": [{"role": "user", "text": "Hi"}],
        "outcome": "booked",
        "fields": {},
        "flow_path": [],
        "turn_latency_ms": [],
        "interruptions": 0,
    }


async def test_a_campaign_call_record_names_its_contact():
    client, requests = client_answering(lambda request: httpx.Response(201, json={"id": "call-2"}))

    await client.start_call("agent-1", "out-1", "phone", "outbound", "+9198", "contact-1")
    await client.aclose()

    assert json.loads(requests[0].content)["campaign_contact_id"] == "contact-1"


async def test_the_number_dialled_says_which_agent_answers():
    client, requests = client_answering(
        lambda request: httpx.Response(
            200, json={"id": "n-1", "number": "+14155550100", "agent_id": "agent-1"}
        )
    )

    number = await client.get_phone_number("n-1")
    await client.aclose()

    assert requests[0].url.path == "/runtime/phone-numbers/n-1"
    assert number.agent_id == "agent-1"


def test_client_sends_the_runtime_token_to_the_configured_api():
    client = create_control_plane_client(Settings(api_url="http://api:8000", runtime_api_token="t"))

    assert str(client._http.base_url) == "http://api:8000"
    assert client._http.headers["Authorization"] == "Bearer t"
