import pytest
from sqlalchemy import select

from studio_backend.calls.costs import call_cost
from studio_backend.calls.models import Call
from studio_backend.core.config import Settings
from tests.test_agents import create_agent

PRICED_MODEL = "openai:gpt-5.4-mini"
SPOKEN = [
    {"role": "assistant", "text": "Hello, how can I help?"},
    {"role": "user", "text": "Book me in please."},
]
USAGE = {
    "llm_input_tokens": 10_000,
    "llm_cached_input_tokens": 4_000,
    "llm_output_tokens": 500,
    "stt_seconds": 90,
    "tts_characters": 2_000,
}


def priced(**changes) -> Settings:
    prices = {PRICED_MODEL: {"input": 0.75, "cached_input": 0.075, "output": 4.50}}
    return Settings(
        llm_prices=prices,
        stt_price_per_minute=0.0048,
        tts_price_per_1k_characters=0.030,
        phone_price_per_minute=0.01,
        **changes,
    )


def test_a_calls_cost_is_its_usage_at_the_configured_prices():
    cost = call_cost(USAGE, PRICED_MODEL, phone_seconds=120, settings=priced())

    # LLM: 6,000 fresh input x 0.75 + 4,000 cached x 0.075 + 500 output x 4.50, per million.
    assert cost["llm"] == pytest.approx(0.0045 + 0.0003 + 0.00225)
    assert cost["stt"] == pytest.approx(1.5 * 0.0048)
    assert cost["tts"] == pytest.approx(2 * 0.030)
    assert cost["phone"] == pytest.approx(2 * 0.01)
    assert cost["total"] == pytest.approx(0.00705 + 0.0072 + 0.06 + 0.02)
    assert cost["llm_unpriced"] is False


def test_a_model_with_no_price_is_marked_unpriced_not_free():
    cost = call_cost(USAGE, "anthropic:some-model", phone_seconds=0, settings=priced())

    assert cost["llm"] == 0 and cost["llm_unpriced"] is True


async def start(client, headers, agent_id: str, room: str, **extra) -> str:
    body = {"agent_id": agent_id, "room_name": room, "channel": "web", **extra}
    response = await client.post("/runtime/calls", json=body, headers=headers)
    return response.json()["id"]


async def end(client, headers, call_id: str, **body) -> dict:
    response = await client.post(f"/runtime/calls/{call_id}/end", json=body, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def test_ending_a_call_prices_it_and_queues_its_analysis(client, runtime_headers, job_queue):
    agent = await create_agent(client, llm_model=PRICED_MODEL)
    call_id = await start(client, runtime_headers, agent["id"], "web-1")

    ended = await end(client, runtime_headers, call_id, transcript=SPOKEN, usage=USAGE)

    assert ended["cost"]["total"] > 0 and ended["cost"]["llm_unpriced"] is False
    assert ended["usage"]["stt_seconds"] == 90
    assert ended["analysis_status"] == "pending"
    assert job_queue.jobs == [("analyse_call_job", call_id)]


async def test_a_call_where_the_caller_never_spoke_is_not_analysed(
    client, runtime_headers, job_queue
):
    agent = await create_agent(client)
    call_id = await start(client, runtime_headers, agent["id"], "out-1", channel="phone")

    ended = await end(client, runtime_headers, call_id, outcome="not_answered")

    assert ended["analysis_status"] == "skipped"
    assert job_queue.jobs == []


async def test_a_call_links_to_its_langfuse_session_and_livekit_recording(
    client, runtime_headers, settings, monkeypatch
):
    monkeypatch.setattr(settings, "langfuse_project_id", "proj-1")
    monkeypatch.setattr(settings, "langfuse_base_url", "https://us.cloud.langfuse.com/")
    monkeypatch.setattr(
        settings, "livekit_session_url_template", "https://cloud.livekit.io/s/{room_sid}"
    )
    agent = await create_agent(client)
    call_id = await start(client, runtime_headers, agent["id"], "web-7", room_sid="RM_abc")

    call = (await client.get(f"/calls/{call_id}")).json()

    assert call["langfuse_url"] == "https://us.cloud.langfuse.com/project/proj-1/sessions/web-7"
    assert call["recording_url"] == "https://cloud.livekit.io/s/RM_abc"


async def test_without_settings_a_call_has_no_links(client, runtime_headers):
    agent = await create_agent(client)
    call_id = await start(client, runtime_headers, agent["id"], "web-8")

    call = (await client.get(f"/calls/{call_id}")).json()

    assert call["langfuse_url"] is None and call["recording_url"] is None


async def test_calls_can_be_filtered_by_channel_direction_and_outcome(client, runtime_headers):
    agent = await create_agent(client)
    web = await start(client, runtime_headers, agent["id"], "web-1")
    phone = await start(
        client, runtime_headers, agent["id"], "out-1", channel="phone", direction="outbound"
    )
    await end(client, runtime_headers, web, outcome="booked")
    await end(client, runtime_headers, phone, outcome="not_answered")

    def ids(response) -> list[str]:
        return [call["id"] for call in response.json()]

    assert ids(await client.get("/calls", params={"channel": "phone"})) == [phone]
    assert ids(await client.get("/calls", params={"direction": "outbound"})) == [phone]
    assert ids(await client.get("/calls", params={"outcome": "booked"})) == [web]


async def test_the_dashboard_counts_outcomes_costs_latency_and_success(
    client, runtime_headers, sqlite_engine
):
    agent = await create_agent(client, name="Front desk", llm_model=PRICED_MODEL)
    latencies = [1000, 1200, 1400, 1600, 3000]
    outcomes = ["booked", "booked", "not_answered", None, "booked"]
    for n, (latency, outcome) in enumerate(zip(latencies, outcomes, strict=True)):
        call_id = await start(client, runtime_headers, agent["id"], f"web-{n}")
        await end(
            client,
            runtime_headers,
            call_id,
            outcome=outcome,
            transcript=SPOKEN,
            usage=USAGE,
            turn_latency_ms=[{"e2e_latency": latency}],
        )
    # What the analysis job would save: three of the five calls succeeded.
    async with client.app.state.session_factory() as session:
        for n, call in enumerate(await session.scalars(select(Call).order_by(Call.room_name))):
            call.analysis = {"successful": n < 3}
        await session.commit()

    metrics = (await client.get("/metrics", params={"days": 7})).json()

    assert metrics["calls"] == 5
    assert metrics["outcomes"] == {"booked": 3, "not_answered": 1, "none": 1}
    assert metrics["days"][-1]["calls"] == 5 and len(metrics["days"]) == 7
    assert metrics["latency_p50_ms"] == 1400
    assert metrics["latency_p95_ms"] == pytest.approx(2720)
    assert metrics["average_cost"] == pytest.approx(metrics["total_cost"] / 5)
    (row,) = metrics["agents"]
    assert (row["name"], row["calls"], row["analysed"], row["successful"]) == (
        "Front desk",
        5,
        5,
        3,
    )
