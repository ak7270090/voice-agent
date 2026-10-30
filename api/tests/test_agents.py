import asyncio

import jwt
import pytest

# The Windows clock can give two quick inserts the same timestamp.
CLOCK_TICK_SECONDS = 0.05

VOICE = {
    "stt_model": "openai/gpt-4o-mini-transcribe",
    "tts_model": "openai/tts-1",
    "voice": "alloy",
}
NEW_AGENT = {
    "name": "Front desk",
    "instructions": "Answer questions about opening hours.",
    "greeting": "Hello, how can I help?",
    "llm_model": "openai:gpt-4.1-mini",
    "languages": ["en"],
    "language_settings": {"en": VOICE},
}


async def create_agent(client, **changes) -> dict:
    response = await client.post("/agents", json={**NEW_AGENT, **changes})
    assert response.status_code == 201, response.text
    return response.json()


async def test_created_agent_is_a_draft_and_can_be_read_back(client):
    created = await create_agent(client)

    read = (await client.get(f"/agents/{created['id']}")).json()

    assert read["name"] == "Front desk"
    assert read["status"] == "draft"
    assert read["language_settings"] == {"en": VOICE}


async def test_agent_without_voice_settings_for_a_language_is_rejected(client):
    response = await client.post("/agents", json={**NEW_AGENT, "languages": ["en", "hi"]})

    assert response.status_code == 422


async def test_agents_are_listed_newest_first(client):
    await create_agent(client, name="First")
    await asyncio.sleep(CLOCK_TICK_SECONDS)
    await create_agent(client, name="Second")

    names = [agent["name"] for agent in (await client.get("/agents")).json()]

    assert names == ["Second", "First"]


async def test_update_changes_only_the_given_fields(client):
    created = await create_agent(client)

    response = await client.patch(
        f"/agents/{created['id']}", json={"greeting": "Hi there!", "status": "live"}
    )

    assert response.status_code == 200
    assert response.json()["greeting"] == "Hi there!"
    assert response.json()["status"] == "live"
    assert response.json()["instructions"] == NEW_AGENT["instructions"]


async def test_update_that_adds_a_language_without_voice_settings_is_rejected(client):
    created = await create_agent(client)

    response = await client.patch(f"/agents/{created['id']}", json={"languages": ["en", "hi"]})

    assert response.status_code == 422


async def test_deleted_agent_is_gone(client):
    created = await create_agent(client)

    assert (await client.delete(f"/agents/{created['id']}")).status_code == 204
    assert (await client.get(f"/agents/{created['id']}")).status_code == 404


@pytest.mark.parametrize(
    ("method", "path"),
    [("get", "/agents/missing"), ("patch", "/agents/missing"), ("delete", "/agents/missing")],
)
async def test_unknown_agent_is_not_found(client, method, path):
    kwargs = {"json": {}} if method == "patch" else {}

    response = await getattr(client, method)(path, **kwargs)

    assert response.status_code == 404


async def test_agent_created_from_a_template_copies_its_fields(client):
    templates = (await client.get("/agent-templates")).json()
    clinic = next(t for t in templates if t["id"] == "clinic-booking")

    response = await client.post(
        "/agents/from-template", json={"template_id": "clinic-booking", "name": "City Hospital"}
    )

    agent = response.json()
    assert response.status_code == 201
    assert agent["name"] == "City Hospital"
    assert agent["template"] == "clinic-booking"
    assert agent["instructions"] == clinic["fields"]["instructions"]


async def test_unknown_template_is_not_found(client):
    response = await client.post("/agents/from-template", json={"template_id": "nope"})

    assert response.status_code == 404


async def test_browser_call_token_dispatches_the_runtime_with_the_agent_id(client, settings):
    created = await create_agent(client)

    response = await client.post(f"/agents/{created['id']}/browser-calls")

    call = response.json()
    claims = jwt.decode(call["token"], options={"verify_signature": False})
    dispatch = claims["roomConfig"]["agents"][0]
    assert response.status_code == 201
    assert call["url"] == settings.livekit_url
    assert claims["video"]["room"] == call["room"]
    assert dispatch["agentName"] == settings.runtime_agent_name
    assert f'"agent_id": "{created["id"]}"' in dispatch["metadata"]


async def test_browser_call_for_an_unknown_agent_is_not_found(client):
    assert (await client.post("/agents/missing/browser-calls")).status_code == 404


async def test_runtime_reads_an_agents_config_with_its_token(client, runtime_headers):
    created = await create_agent(client)

    response = await client.get(f"/runtime/agents/{created['id']}", headers=runtime_headers)

    assert response.status_code == 200
    assert response.json()["instructions"] == NEW_AGENT["instructions"]
    assert "status" not in response.json()


async def test_runtime_config_for_an_unknown_agent_is_not_found(client, runtime_headers):
    response = await client.get("/runtime/agents/missing", headers=runtime_headers)

    assert response.status_code == 404


async def test_runtime_endpoints_reject_a_missing_or_wrong_token(client):
    created = await create_agent(client)
    path = f"/runtime/agents/{created['id']}"

    assert (await client.get(path)).status_code == 401
    assert (await client.get(path, headers={"Authorization": "Bearer wrong"})).status_code == 401
