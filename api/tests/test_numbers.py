from tests.test_agents import create_agent

TRUNK_NUMBER = "+14155550100"
OUTBOUND = {"address": "example.pstn.twilio.com", "username": "studio", "password": "secret"}


async def add_number(client, **changes) -> dict:
    body = {"number": TRUNK_NUMBER, "provider": "sip_trunk", **changes}
    response = await client.post("/phone-numbers", json=body)
    assert response.status_code == 201, response.text
    return response.json()


async def test_a_trunk_number_gets_trunks_and_a_rule_that_names_only_the_number(client, telephony):
    agent = await create_agent(client)

    number = await add_number(client, agent_id=agent["id"], outbound=OUTBOUND)

    rule = telephony.rules[number["dispatch_rule_id"]]
    assert rule["number_id"] == number["id"]
    assert telephony.trunks[rule["trunk_id"]] == {"direction": "inbound", "number": TRUNK_NUMBER}
    assert number["can_call_out"] and number["can_transfer"]
    assert "password" not in str(number)
    assert [n["id"] for n in (await client.get("/phone-numbers")).json()] == [number["id"]]


async def test_a_livekit_number_has_a_rule_but_no_trunk_and_cannot_call_out(client, telephony):
    number = await add_number(client, provider="livekit")

    assert telephony.trunks == {}
    assert telephony.rules[number["dispatch_rule_id"]]["trunk_id"] is None
    assert not number["can_call_out"] and not number["can_transfer"]


async def test_a_livekit_number_with_an_outbound_trunk_is_rejected(client):
    body = {"number": TRUNK_NUMBER, "provider": "livekit", "outbound": OUTBOUND}

    assert (await client.post("/phone-numbers", json=body)).status_code == 422


async def test_a_number_that_is_not_e164_is_rejected(client):
    body = {"number": "98765 43210", "provider": "sip_trunk"}

    assert (await client.post("/phone-numbers", json=body)).status_code == 422


async def test_the_same_number_cannot_be_added_twice(client):
    await add_number(client)

    response = await client.post(
        "/phone-numbers", json={"number": TRUNK_NUMBER, "provider": "sip_trunk"}
    )

    assert response.status_code == 409


async def test_when_livekit_refuses_a_part_the_parts_already_made_are_removed(client, telephony):
    telephony.fail_on = "rule"

    response = await client.post(
        "/phone-numbers",
        json={"number": TRUNK_NUMBER, "provider": "sip_trunk", "outbound": OUTBOUND},
    )

    assert response.status_code == 502
    assert "rule refused" in response.json()["detail"]
    assert telephony.trunks == {}
    assert (await client.get("/phone-numbers")).json() == []


async def test_binding_another_agent_changes_only_the_row(client, telephony):
    first = await create_agent(client, name="First")
    second = await create_agent(client, name="Second")
    number = await add_number(client, agent_id=first["id"])
    rules_before = dict(telephony.rules)

    response = await client.patch(
        f"/phone-numbers/{number['id']}", json={"agent_id": second["id"], "label": "Main line"}
    )

    assert response.json()["agent_id"] == second["id"]
    assert response.json()["label"] == "Main line"
    assert telephony.rules == rules_before


async def test_binding_an_unknown_agent_is_not_found(client):
    number = await add_number(client)

    response = await client.patch(f"/phone-numbers/{number['id']}", json={"agent_id": "nope"})

    assert response.status_code == 404


async def test_deleting_a_number_removes_its_livekit_side(client, telephony):
    number = await add_number(client, outbound=OUTBOUND)

    assert (await client.delete(f"/phone-numbers/{number['id']}")).status_code == 204
    assert telephony.trunks == {} and telephony.rules == {}
    assert (await client.delete(f"/phone-numbers/{number['id']}")).status_code == 404


async def test_the_runtime_reads_which_agent_answers_a_number(client, runtime_headers):
    agent = await create_agent(client)
    number = await add_number(client, agent_id=agent["id"])

    response = await client.get(f"/runtime/phone-numbers/{number['id']}", headers=runtime_headers)

    assert response.json() == {"id": number["id"], "number": TRUNK_NUMBER, "agent_id": agent["id"]}
    missing = await client.get("/runtime/phone-numbers/nope", headers=runtime_headers)
    assert missing.status_code == 404


async def test_call_me_dispatches_the_runtime_with_the_number_to_dial(client, telephony):
    agent = await create_agent(client)
    number = await add_number(client, outbound=OUTBOUND)

    response = await client.post(
        f"/agents/{agent['id']}/phone-calls",
        json={"to_number": "+919876543210", "from_number_id": number["id"]},
    )

    room, metadata = telephony.dispatches[0]
    assert response.status_code == 201
    assert response.json() == {"room": room}
    assert room.startswith("out-")
    assert metadata["agent_id"] == agent["id"]
    assert metadata["dial_to"] == "+919876543210"
    assert telephony.trunks[metadata["outbound_trunk_id"]]["direction"] == "outbound"


async def test_call_me_from_a_number_without_an_outbound_trunk_is_a_conflict(client):
    agent = await create_agent(client)
    number = await add_number(client)

    response = await client.post(
        f"/agents/{agent['id']}/phone-calls",
        json={"to_number": "+919876543210", "from_number_id": number["id"]},
    )

    assert response.status_code == 409


async def test_call_me_from_an_unknown_number_or_for_an_unknown_agent_is_not_found(client):
    agent = await create_agent(client)
    body = {"to_number": "+919876543210", "from_number_id": "nope"}

    assert (await client.post(f"/agents/{agent['id']}/phone-calls", json=body)).status_code == 404
    assert (await client.post("/agents/nope/phone-calls", json=body)).status_code == 404
