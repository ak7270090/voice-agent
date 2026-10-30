import json

import httpx
import pytest

from studio_runtime.config import Settings
from studio_runtime.control_plane import (
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

    config = await client.get_agent_config("agent-1")

    assert requests[0].url.path == "/runtime/agents/agent-1"
    assert config.starting_language == "en"
    assert config.language_settings["en"].voice == "alloy"


async def test_missing_agent_raises():
    client, _ = client_answering(lambda request: httpx.Response(404))

    with pytest.raises(httpx.HTTPStatusError):
        await client.get_agent_config("missing")


async def test_call_is_started_and_ended_with_its_transcript():
    client, requests = client_answering(lambda request: httpx.Response(201, json={"id": "call-1"}))

    call_id = await client.start_call("agent-1", "web-abc", "web")
    await client.end_call(call_id, [TranscriptTurn(role="user", text="Hi")])
    await client.aclose()

    assert call_id == "call-1"
    assert json.loads(requests[0].content) == {
        "agent_id": "agent-1",
        "room_name": "web-abc",
        "channel": "web",
    }
    assert requests[1].url.path == "/runtime/calls/call-1/end"
    assert json.loads(requests[1].content) == {"transcript": [{"role": "user", "text": "Hi"}]}


def test_client_sends_the_runtime_token_to_the_configured_api():
    client = create_control_plane_client(Settings(api_url="http://api:8000", runtime_api_token="t"))

    assert str(client._http.base_url) == "http://api:8000"
    assert client._http.headers["Authorization"] == "Bearer t"
