from tests.test_agents import create_agent


async def start_call(client, headers, agent_id: str, room: str = "web-abc") -> dict:
    response = await client.post(
        "/runtime/calls",
        json={"agent_id": agent_id, "room_name": room, "channel": "web"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_started_call_is_active_until_the_runtime_ends_it(client, runtime_headers):
    agent = await create_agent(client)
    call = await start_call(client, runtime_headers, agent["id"])
    transcript = [
        {"role": "assistant", "text": "Hello, how can I help?"},
        {"role": "user", "text": "When do you open?"},
    ]

    latency = [{"e2e_latency": 1840, "llm_node_ttft": 610}]
    ended = await client.post(
        f"/runtime/calls/{call['id']}/end",
        json={"transcript": transcript, "turn_latency_ms": latency, "interruptions": 2},
        headers=runtime_headers,
    )

    assert call["status"] == "active"
    assert ended.json()["status"] == "ended"
    assert ended.json()["ended_at"] is not None
    assert ended.json()["transcript"] == transcript
    assert ended.json()["turn_latency_ms"] == latency
    assert ended.json()["interruptions"] == 2


async def test_a_phone_call_keeps_its_direction_and_the_other_partys_number(
    client, runtime_headers
):
    agent = await create_agent(client)

    response = await client.post(
        "/runtime/calls",
        json={
            "agent_id": agent["id"],
            "room_name": "out-1",
            "channel": "phone",
            "direction": "outbound",
            "remote_number": "+919876543210",
        },
        headers=runtime_headers,
    )

    assert response.json()["direction"] == "outbound"
    assert response.json()["remote_number"] == "+919876543210"
    assert (await start_call(client, runtime_headers, agent["id"]))["direction"] == "inbound"


async def test_ending_a_call_twice_keeps_the_first_end(client, runtime_headers):
    agent = await create_agent(client)
    call = await start_call(client, runtime_headers, agent["id"])
    path = f"/runtime/calls/{call['id']}/end"
    first = (await client.post(path, json={"transcript": []}, headers=runtime_headers)).json()

    second = await client.post(
        path, json={"transcript": [{"role": "user", "text": "late"}]}, headers=runtime_headers
    )

    assert second.json()["ended_at"] == first["ended_at"]
    assert second.json()["transcript"] == []


async def test_calls_can_be_listed_for_one_agent_and_read(client, runtime_headers):
    first = await create_agent(client, name="First")
    second = await create_agent(client, name="Second")
    call = await start_call(client, runtime_headers, first["id"], room="web-1")
    await start_call(client, runtime_headers, second["id"], room="web-2")

    listed = (await client.get("/calls", params={"agent_id": first["id"]})).json()

    assert [c["id"] for c in listed] == [call["id"]]
    assert (await client.get(f"/calls/{call['id']}")).json()["room_name"] == "web-1"
    assert len((await client.get("/calls")).json()) == 2


async def test_call_for_an_unknown_agent_is_not_started(client, runtime_headers):
    response = await client.post(
        "/runtime/calls",
        json={"agent_id": "missing", "room_name": "web-x", "channel": "web"},
        headers=runtime_headers,
    )

    assert response.status_code == 404


async def test_unknown_call_is_not_found(client, runtime_headers):
    assert (await client.get("/calls/missing")).status_code == 404
    response = await client.post(
        "/runtime/calls/missing/end", json={"transcript": []}, headers=runtime_headers
    )
    assert response.status_code == 404
