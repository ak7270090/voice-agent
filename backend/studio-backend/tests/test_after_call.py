import base64
import json

import httpx
import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from studio_backend import worker
from studio_backend.after_call.senders import sign, slack_text
from studio_backend.after_call.service import deliver

from tests.test_agents import create_agent
from tests.test_call_records import SPOKEN, end, start

SIGNING_SECRET = "whsec_0123456789abcdef"
SLACK_URL = "https://hooks.slack.com/services/T000/B000/abcdefghijklmnop"
HUBSPOT_TOKEN = "pat-na1-0123456789abcdef"
WEBHOOK = {"kind": "webhook", "event": "call.ended", "url": "https://receiver.test/calls"}
SIGNED_WEBHOOK = {**WEBHOOK, "id": "hook", "secret": "WEBHOOK_SECRET"}
SLACK = {"id": "slack", "kind": "slack", "secret": "SLACK_URL"}
HUBSPOT = {"id": "crm", "kind": "hubspot", "secret": "HUBSPOT_TOKEN"}


class Receiver:
    """Answers with the given statuses in turn (the last one repeats) and keeps the requests."""

    def __init__(self, *statuses: int, json_body: dict | None = None) -> None:
        self.statuses = list(statuses) or [200]
        self.json_body = json_body or {}
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        status = self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]
        return httpx.Response(status, json=self.json_body)


def http_for(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def save_secrets(client, **values: str) -> None:
    for name, value in values.items():
        response = await client.put(f"/secrets/{name}", json={"value": value})
        assert response.status_code == 200


async def ended_call(client, headers, actions: list[dict], room="call-1", **end_body) -> dict:
    agent = await create_agent(client, after_call_actions=actions)
    call_id = await start(
        client, headers, agent["id"], room, channel="phone", remote_number="+919876543210"
    )
    return await end(client, headers, call_id, **end_body)


def queued(job_queue, job: str = "deliver_job") -> list[str]:
    return [args[1] for args in job_queue.jobs if args[0] == job]


async def test_an_ended_call_queues_its_call_ended_actions_once(client, runtime_headers, job_queue):
    await save_secrets(client, SLACK_URL=SLACK_URL)
    call = await ended_call(
        client, runtime_headers, [WEBHOOK, SLACK], transcript=SPOKEN, outcome="booked"
    )
    await end(client, runtime_headers, call["id"], transcript=SPOKEN)

    deliveries = (await client.get(f"/calls/{call['id']}/deliveries")).json()

    # The Slack action waits for the analysis; a second end report sends nothing again.
    assert [(d["kind"], d["event"], d["status"]) for d in deliveries] == [
        ("webhook", "call.ended", "pending")
    ]
    assert queued(job_queue) == [deliveries[0]["id"]]


async def test_a_call_with_nothing_to_analyse_sends_its_analysed_actions_at_the_end(
    client, runtime_headers
):
    await save_secrets(client, SLACK_URL=SLACK_URL)
    call = await ended_call(client, runtime_headers, [WEBHOOK, SLACK], transcript=[])

    deliveries = (await client.get(f"/calls/{call['id']}/deliveries")).json()

    assert sorted(d["event"] for d in deliveries) == ["call.analysed", "call.ended"]


async def test_the_analysis_job_sends_the_analysed_actions_when_it_settles(
    client, runtime_headers, monkeypatch
):
    await save_secrets(client, SLACK_URL=SLACK_URL)
    call = await ended_call(client, runtime_headers, [SLACK], transcript=SPOKEN)
    enqueued = []

    class Redis:
        async def enqueue_job(self, *args, **kwargs):
            enqueued.append(args)

    async def analysed(*args, **kwargs):
        return True

    monkeypatch.setattr(worker, "run_analysis", analysed)
    ctx = {"session_factory": client.app.state.session_factory, "redis": Redis()}

    await worker.analyse_call_job(ctx, call["id"])

    deliveries = (await client.get(f"/calls/{call['id']}/deliveries")).json()
    assert [d["event"] for d in deliveries] == ["call.analysed"]
    assert enqueued == [("deliver_job", deliveries[0]["id"])]


async def test_a_webhook_is_signed_and_carries_the_call(client, runtime_headers, settings):
    await save_secrets(client, WEBHOOK_SECRET=SIGNING_SECRET)
    call = await ended_call(
        client, runtime_headers, [SIGNED_WEBHOOK], transcript=SPOKEN, outcome="booked"
    )
    delivery = (await client.get(f"/calls/{call['id']}/deliveries")).json()[0]
    receiver = Receiver(200)

    retry = await deliver(
        client.app.state.session_factory, settings, http_for(receiver), delivery["id"]
    )

    request = receiver.requests[0]
    timestamp = int(request.headers["X-Studio-Timestamp"])
    assert request.headers["X-Studio-Signature"] == sign(SIGNING_SECRET, timestamp, request.content)
    assert request.headers["X-Studio-Event"] == "call.ended"
    assert request.headers["X-Studio-Delivery"] == delivery["id"]
    body = json.loads(request.content)
    assert body["call"]["outcome"] == "booked"
    assert body["call"]["remote_number"] == "+919876543210"
    assert body["call"]["url"].endswith(f"/calls/{call['id']}")
    assert retry is None
    sent = (await client.get(f"/calls/{call['id']}/deliveries")).json()[0]
    assert (sent["status"], sent["attempts"], sent["response_status"]) == ("sent", 1, 200)


async def test_a_receiver_that_is_down_is_retried_with_growing_waits_then_given_up(
    client, runtime_headers, settings, monkeypatch
):
    monkeypatch.setattr(settings, "delivery_attempts", 3)
    call = await ended_call(client, runtime_headers, [WEBHOOK], transcript=SPOKEN)
    delivery_id = (await client.get(f"/calls/{call['id']}/deliveries")).json()[0]["id"]
    receiver = Receiver(503)
    factory = client.app.state.session_factory

    waits = [await deliver(factory, settings, http_for(receiver), delivery_id) for _ in range(3)]

    assert waits == [10, 30, None]
    failed = (await client.get(f"/calls/{call['id']}/deliveries")).json()[0]
    assert (failed["status"], failed["attempts"], failed["response_status"]) == ("failed", 3, 503)
    assert "503" in failed["last_error"]


async def test_a_refused_request_is_not_retried(client, runtime_headers, settings):
    call = await ended_call(client, runtime_headers, [WEBHOOK], transcript=SPOKEN)
    delivery_id = (await client.get(f"/calls/{call['id']}/deliveries")).json()[0]["id"]

    retry = await deliver(
        client.app.state.session_factory, settings, http_for(Receiver(404)), delivery_id
    )

    assert retry is None
    failed = (await client.get(f"/calls/{call['id']}/deliveries")).json()[0]
    assert (failed["status"], failed["response_status"]) == ("failed", 404)


async def test_send_again_resets_a_delivery_and_queues_it(
    client, runtime_headers, settings, job_queue
):
    call = await ended_call(client, runtime_headers, [WEBHOOK], transcript=SPOKEN)
    delivery_id = (await client.get(f"/calls/{call['id']}/deliveries")).json()[0]["id"]
    await deliver(client.app.state.session_factory, settings, http_for(Receiver(404)), delivery_id)

    response = await client.post(f"/calls/{call['id']}/deliveries/{delivery_id}/retry")

    assert (response.json()["status"], response.json()["attempts"]) == ("pending", 0)
    assert queued(job_queue).count(delivery_id) == 2
    missing = await client.post(f"/calls/{call['id']}/deliveries/nope/retry")
    assert missing.status_code == 404


async def test_an_action_removed_before_sending_is_skipped(client, runtime_headers, settings):
    call = await ended_call(client, runtime_headers, [WEBHOOK], transcript=SPOKEN)
    delivery_id = (await client.get(f"/calls/{call['id']}/deliveries")).json()[0]["id"]
    await client.patch(f"/agents/{call['agent_id']}", json={"after_call_actions": []})

    await deliver(client.app.state.session_factory, settings, http_for(Receiver()), delivery_id)

    skipped = (await client.get(f"/calls/{call['id']}/deliveries")).json()[0]
    assert (skipped["status"], skipped["last_error"]) == ("skipped", "the action was removed")


async def test_actions_need_the_secrets_they_name_to_be_saved(client):
    response = await client.post(
        "/agents",
        json={
            "name": "Clinic",
            "instructions": "Help callers.",
            "greeting": "Hello.",
            "llm_model": "openai:gpt-5.4-mini",
            "languages": ["en"],
            "language_settings": {
                "en": {"stt_model": "deepgram/nova-3", "tts_model": "x", "voice": ""}
            },
            "after_call_actions": [SLACK],
        },
    )

    assert response.status_code == 422
    assert "SLACK_URL" in response.text


@pytest.mark.parametrize(
    ("action", "message"),
    [
        ({"kind": "webhook", "url": "receiver.test"}, "a webhook needs an http(s) URL"),
        ({"kind": "slack"}, "a slack action needs the secret it sends with"),
        ({"kind": "google_sheets", "secret": "GOOGLE_KEY"}, "needs the spreadsheet ID"),
    ],
)
async def test_an_action_needs_what_its_kind_sends_with(client, action, message):
    agent = await create_agent(client)

    response = await client.patch(f"/agents/{agent['id']}", json={"after_call_actions": [action]})

    assert response.status_code == 422
    assert message in response.text


def payload(**call) -> dict:
    base = {
        "id": "c1",
        "url": "http://localhost:3000/calls/c1",
        "agent": {"id": "a1", "name": "Clinic receptionist"},
        "channel": "phone",
        "direction": "inbound",
        "remote_number": "+919876543210",
        "started_at": "2026-11-01T10:00:00+00:00",
        "ended_at": "2026-11-01T10:01:32+00:00",
        "duration_seconds": 92.0,
        "outcome": "booked",
        "fields": {"patient_name": "Asha Rao", "doctor": "Dr. Priya Mehta"},
        "transcript": [],
        "analysis_status": "done",
        "summary": "Asha booked Dr. Mehta for Monday.",
        "successful": True,
        "sentiment": "positive",
        "analysis_fields": {},
        "cost_usd": 0.0123,
    }
    return {"event": "call.analysed", "call": {**base, **call}}


def test_the_slack_message_says_who_how_it_ended_and_links_the_call():
    assert slack_text(payload()) == (
        "*Clinic receptionist* · phone inbound (+919876543210) · booked · 92 s · successful\n"
        "Asha booked Dr. Mehta for Monday.\n"
        "<http://localhost:3000/calls/c1|Open the call>"
    )


async def sent_with(client, runtime_headers, settings, actions, handler, **end_body) -> dict:
    call = await ended_call(client, runtime_headers, actions, transcript=[], **end_body)
    deliveries = (await client.get(f"/calls/{call['id']}/deliveries")).json()
    for delivery in deliveries:
        await deliver(client.app.state.session_factory, settings, http_for(handler), delivery["id"])
    return (await client.get(f"/calls/{call['id']}/deliveries")).json()[0]


async def test_slack_gets_the_message_at_its_webhook_url(client, runtime_headers, settings):
    await save_secrets(client, SLACK_URL=SLACK_URL)
    receiver = Receiver(200)

    delivery = await sent_with(client, runtime_headers, settings, [SLACK], receiver)

    assert delivery["status"] == "sent"
    assert str(receiver.requests[0].url) == SLACK_URL
    assert "Front desk" in json.loads(receiver.requests[0].content)["text"]


class FakeHubSpot:
    def __init__(self, existing: bool) -> None:
        self.existing = existing
        self.requests: list[tuple[str, dict]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == f"Bearer {HUBSPOT_TOKEN}"
        body = json.loads(request.content)
        self.requests.append((request.url.path, body))
        if request.url.path.endswith("/contacts/search"):
            return httpx.Response(200, json={"results": [{"id": "501"}] if self.existing else []})
        if request.url.path.endswith("/contacts"):
            return httpx.Response(201, json={"id": "777"})
        return httpx.Response(201, json={"id": "note-1"})


async def test_hubspot_creates_the_contact_once_and_notes_the_call_on_it(
    client, runtime_headers, settings
):
    await save_secrets(client, HUBSPOT_TOKEN=HUBSPOT_TOKEN)
    hubspot = FakeHubSpot(existing=False)

    delivery = await sent_with(
        client,
        runtime_headers,
        settings,
        [HUBSPOT],
        hubspot,
        outcome="booked",
        fields={"patient_name": "Asha Rao"},
    )

    paths = [path for path, _ in hubspot.requests]
    assert paths == [
        "/crm/v3/objects/contacts/search",
        "/crm/v3/objects/contacts",
        "/crm/v3/objects/notes",
    ]
    search, created, note = (body for _, body in hubspot.requests)
    assert search["filterGroups"][0]["filters"][0]["value"] == "+919876543210"
    assert created["properties"] == {
        "phone": "+919876543210",
        "firstname": "Asha",
        "lastname": "Rao",
    }
    assert note["associations"][0]["to"] == {"id": "777"}
    assert note["associations"][0]["types"][0]["associationTypeId"] == 202
    assert "booked" in note["properties"]["hs_note_body"]
    assert delivery["status"] == "sent"


async def test_hubspot_adds_the_note_to_an_existing_contact(client, runtime_headers, settings):
    await save_secrets(client, HUBSPOT_TOKEN=HUBSPOT_TOKEN)
    hubspot = FakeHubSpot(existing=True)

    await sent_with(client, runtime_headers, settings, [HUBSPOT], hubspot)

    assert [path for path, _ in hubspot.requests][-1] == "/crm/v3/objects/notes"
    assert len(hubspot.requests) == 2
    assert hubspot.requests[1][1]["associations"][0]["to"] == {"id": "501"}


async def test_hubspot_skips_a_browser_call_with_no_number(client, runtime_headers, settings):
    await save_secrets(client, HUBSPOT_TOKEN=HUBSPOT_TOKEN)
    agent = await create_agent(client, after_call_actions=[HUBSPOT])
    call_id = await start(client, runtime_headers, agent["id"], "web-1")
    await end(client, runtime_headers, call_id, transcript=[])
    delivery = (await client.get(f"/calls/{call_id}/deliveries")).json()[0]

    await deliver(
        client.app.state.session_factory, settings, http_for(FakeHubSpot(False)), delivery["id"]
    )

    skipped = (await client.get(f"/calls/{call_id}/deliveries")).json()[0]
    assert skipped["status"] == "skipped"
    assert "no phone number" in skipped["last_error"]


def b64decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


async def test_google_sheets_gets_a_row_with_a_token_from_a_signed_service_account_jwt(
    client, runtime_headers, settings
):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    account = {
        "client_email": "studio@project.iam.gserviceaccount.com",
        "private_key": pem,
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    await save_secrets(client, GOOGLE_KEY=json.dumps(account))
    requests: list[httpx.Request] = []

    def google(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "ya29.token"})
        assert request.headers["Authorization"] == "Bearer ya29.token"
        return httpx.Response(200, json={"updates": {"updatedRows": 1}})

    sheet = {"id": "sheet", "kind": "google_sheets", "secret": "GOOGLE_KEY", "spreadsheet_id": "S1"}
    delivery = await sent_with(client, runtime_headers, settings, [sheet], google, outcome="booked")

    assertion = dict(pair.split("=") for pair in requests[0].content.decode().split("&"))[
        "assertion"
    ]
    header, claims, signature = assertion.split(".")
    private_key.public_key().verify(
        b64decode(signature), f"{header}.{claims}".encode(), padding.PKCS1v15(), hashes.SHA256()
    )
    assert json.loads(b64decode(claims))["iss"] == account["client_email"]
    assert requests[1].url.path == "/v4/spreadsheets/S1/values/Sheet1!A1:append"
    row = json.loads(requests[1].content)["values"][0]
    assert row[1:7] == ["Front desk", "phone", "inbound", "+919876543210", "booked", ""]
    assert delivery["status"] == "sent"


async def test_a_secret_that_is_not_a_service_account_key_fails_without_retrying(
    client, runtime_headers, settings
):
    await save_secrets(client, GOOGLE_KEY="not json")
    sheet = {"id": "sheet", "kind": "google_sheets", "secret": "GOOGLE_KEY", "spreadsheet_id": "S1"}

    delivery = await sent_with(client, runtime_headers, settings, [sheet], Receiver())

    assert delivery["status"] == "failed"
    assert "service account" in delivery["last_error"]
