from sqlalchemy import select

from studio_backend.integrations.credentials.models import Secret
from studio_backend.integrations.credentials.service import preview
from tests.test_agents import create_agent

CALCOM_KEY = "cal_live_0123456789abcdef0123456789abcdef"


def flow_with_header(header: str) -> dict:
    lookup = {
        "name": "find_caller",
        "url": "https://crm.example/contacts?phone={caller_number}",
        "headers": {"Authorization": header},
    }
    return {
        "nodes": [
            {"id": "start", "type": "start"},
            {"id": "find", "type": "tool", "data": lookup},
            {"id": "done", "type": "end", "data": {"outcome": "found"}},
        ],
        "edges": [
            {"id": "e1", "source": "start", "target": "find", "kind": "always"},
            {"id": "e2", "source": "find", "target": "done", "kind": "always"},
        ],
    }


async def test_a_secret_is_listed_by_name_and_preview_and_stored_encrypted(client, sqlite_engine):
    saved = await client.put("/secrets/CALCOM_KEY", json={"value": CALCOM_KEY})

    assert saved.status_code == 200
    listed = (await client.get("/secrets")).json()
    assert [(s["name"], s["preview"]) for s in listed] == [("CALCOM_KEY", "cal_…cdef")]
    assert CALCOM_KEY not in saved.text + str(listed)
    async with sqlite_engine.connect() as connection:
        stored = (await connection.execute(select(Secret.encrypted_value))).scalar_one()
    assert CALCOM_KEY not in stored


async def test_saving_under_the_same_name_replaces_the_value(client):
    await client.put("/secrets/CALCOM_KEY", json={"value": "old-value-1234567"})
    await client.put("/secrets/CALCOM_KEY", json={"value": CALCOM_KEY})

    listed = (await client.get("/secrets")).json()
    assert [s["preview"] for s in listed] == ["cal_…cdef"]


async def test_secret_names_are_upper_case_and_deleting_a_missing_one_is_404(client):
    assert (await client.put("/secrets/calcom", json={"value": "x"})).status_code == 422
    assert (await client.delete("/secrets/NOPE")).status_code == 404


async def test_without_a_secrets_key_nothing_is_saved(client, settings, monkeypatch):
    monkeypatch.setattr(settings, "secrets_key", "")

    response = await client.put("/secrets/CALCOM_KEY", json={"value": CALCOM_KEY})

    assert response.status_code == 503


def test_short_values_show_no_characters():
    assert preview("abc123") == "••••"


async def test_the_runtime_gets_only_the_secrets_its_flow_names(client, runtime_headers):
    await client.put("/secrets/CRM_TOKEN", json={"value": "pat-0123456789abcdef"})
    await client.put("/secrets/OTHER_KEY", json={"value": "other-0123456789"})
    agent = await create_agent(client)
    await client.put(
        f"/agents/{agent['id']}/flow", json=flow_with_header("Bearer {secret.CRM_TOKEN}")
    )

    config = (
        await client.get(f"/runtime/agents/{agent['id']}?flow=draft", headers=runtime_headers)
    ).json()

    assert config["secrets"] == {"CRM_TOKEN": "pat-0123456789abcdef"}
    # Neither the agent nor its flow shows the value to the console.
    for path in (f"/agents/{agent['id']}", f"/agents/{agent['id']}/flow"):
        assert "pat-0123456789abcdef" not in (await client.get(path)).text


async def test_a_flow_naming_a_secret_that_is_not_saved_cannot_be_published(client):
    agent = await create_agent(client)
    await client.put(
        f"/agents/{agent['id']}/flow", json=flow_with_header("Bearer {secret.CRM_TOKEN}")
    )

    draft = (await client.get(f"/agents/{agent['id']}/flow")).json()
    published = await client.post(f"/agents/{agent['id']}/flow/publish")

    assert [i["message"] for i in draft["issues"]] == [
        "Secret CRM_TOKEN is not saved (add it under Settings, Secrets)"
    ]
    assert published.status_code == 422
