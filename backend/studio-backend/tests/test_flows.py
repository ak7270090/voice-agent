import pytest
from pydantic import ValidationError

from studio_api.config import get_settings
from studio_api.flows.schemas import Flow
from studio_api.flows.templates import (
    build_clinic_booking_flow,
    build_lead_qualifier_flow,
    build_reminder_flow,
    calcom_clinic_settings,
)
from studio_api.flows.validation import validate_flow
from tests.test_agents import create_agent

SMALL_FLOW = {
    "nodes": [
        {"id": "start", "type": "start"},
        {
            "id": "ask",
            "type": "step",
            "data": {"name": "Ask", "fields": [{"name": "email", "type": "text"}]},
        },
        {"id": "done", "type": "end", "data": {"outcome": "collected", "message": "Thanks!"}},
    ],
    "edges": [
        {"id": "e1", "source": "start", "target": "ask", "kind": "always"},
        {"id": "e2", "source": "ask", "target": "done", "kind": "fields_complete"},
    ],
}


def issues_of(flow: dict) -> list[str]:
    return [issue.message for issue in validate_flow(Flow.model_validate(flow))]


@pytest.mark.parametrize(
    "build",
    [
        build_reminder_flow,
        build_lead_qualifier_flow,
        lambda: build_clinic_booking_flow("http://api:8000"),
    ],
)
def test_template_flows_are_valid(build):
    assert validate_flow(build()) == []


def test_small_flow_is_valid():
    assert issues_of(SMALL_FLOW) == []


def test_flow_without_a_start_is_invalid():
    flow = {**SMALL_FLOW, "nodes": SMALL_FLOW["nodes"][1:], "edges": SMALL_FLOW["edges"][1:]}

    assert "A flow needs exactly one Start node" in issues_of(flow)


def test_edge_kinds_must_suit_their_source():
    edges = [
        *SMALL_FLOW["edges"],
        {"id": "e3", "source": "done", "target": "ask", "kind": "always"},
    ]

    assert "An end node cannot have a 'always' edge" in issues_of({**SMALL_FLOW, "edges": edges})


def test_condition_edges_need_a_condition():
    edges = [SMALL_FLOW["edges"][0], {"id": "e2", "source": "ask", "target": "done"}]

    assert "Say when to take this edge" in issues_of({**SMALL_FLOW, "edges": edges})


def test_unreachable_nodes_and_unknown_attached_tools_are_reported():
    nodes = [
        *SMALL_FLOW["nodes"],
        {"id": "orphan", "type": "end", "data": {"outcome": "lost"}},
    ]
    nodes[1] = {**nodes[1], "data": {**nodes[1]["data"], "tools": ["done"]}}

    issues = issues_of({**SMALL_FLOW, "nodes": nodes})

    assert "Nothing leads to this node" in issues
    assert "Attached tool 'done' is not a tool node" in issues


def test_tool_in_the_path_needs_known_placeholders_and_a_url():
    nodes = [
        *SMALL_FLOW["nodes"],
        {"id": "lookup", "type": "tool", "data": {"name": "lookup", "url": "ftp://x/{phone}"}},
    ]
    edges = [
        SMALL_FLOW["edges"][0],
        {"id": "e2", "source": "ask", "target": "lookup", "kind": "fields_complete"},
        {"id": "e3", "source": "lookup", "target": "done", "kind": "success"},
    ]

    issues = issues_of({"nodes": nodes, "edges": edges})

    assert "Tool needs an http(s) URL" in issues
    assert "Placeholders ['phone'] are not fields of any step" in issues


def test_a_tool_in_the_path_may_use_the_callers_number():
    lookup = {"name": "lookup", "url": "https://crm.example/customers?phone={caller_number}"}
    nodes = [*SMALL_FLOW["nodes"], {"id": "lookup", "type": "tool", "data": lookup}]
    edges = [
        SMALL_FLOW["edges"][0],
        {"id": "e2", "source": "ask", "target": "lookup", "kind": "fields_complete"},
        {"id": "e3", "source": "lookup", "target": "done", "kind": "success"},
    ]

    assert issues_of({"nodes": nodes, "edges": edges}) == []


@pytest.mark.parametrize(
    ("destination", "valid"),
    [("", True), ("+919876543210", True), ("sip:desk@pbx.example.com", True), ("desk", False)],
)
def test_transfer_goes_to_a_phone_number_or_a_sip_address(destination, valid):
    transfer = {"id": "desk", "type": "transfer", "data": {"destination": destination}}
    nodes = [*SMALL_FLOW["nodes"][:2], transfer]
    edges = [
        SMALL_FLOW["edges"][0],
        {"id": "e2", "source": "ask", "target": "desk", "kind": "fields_complete"},
    ]

    issues = issues_of({"nodes": nodes, "edges": edges})

    assert (issues == []) is valid


def test_unknown_node_type_is_rejected_by_the_schema():
    with pytest.raises(ValidationError):
        Flow.model_validate({"nodes": [{"id": "x", "type": "teleport"}]})


async def test_draft_is_saved_with_issues_but_cannot_be_published(client):
    agent = await create_agent(client)
    broken = {**SMALL_FLOW, "edges": SMALL_FLOW["edges"][:1]}

    saved = await client.put(f"/agents/{agent['id']}/flow", json=broken)
    publish = await client.post(f"/agents/{agent['id']}/flow/publish")

    assert saved.status_code == 200
    assert [issue["node_id"] for issue in saved.json()["issues"]] == ["done"]
    assert publish.status_code == 422


async def test_publishing_numbers_versions_and_the_runtime_gets_draft_or_published(
    client, runtime_headers
):
    agent = await create_agent(client)
    path = f"/agents/{agent['id']}/flow"
    await client.put(path, json=SMALL_FLOW)
    first = (await client.post(f"{path}/publish")).json()
    edited = {
        **SMALL_FLOW,
        "nodes": [*SMALL_FLOW["nodes"][:2], {**SMALL_FLOW["nodes"][2], "data": {"outcome": "v2"}}],
    }
    await client.put(path, json=edited)
    runtime = f"/runtime/agents/{agent['id']}"

    published = (await client.get(runtime, headers=runtime_headers)).json()
    draft = (await client.get(runtime, params={"flow": "draft"}, headers=runtime_headers)).json()
    versions = (await client.get(f"{path}/versions")).json()
    listed = (await client.get(f"/agents/{agent['id']}")).json()

    assert first["published_version"] == 1
    assert published["flow_version"] == 1
    assert published["flow"]["nodes"][2]["data"]["outcome"] == "collected"
    assert draft["flow"]["nodes"][2]["data"]["outcome"] == "v2"
    assert [version["version"] for version in versions] == [1]
    assert listed["has_flow"] and listed["published_flow_version"] == 1


async def test_removing_the_flow_makes_test_calls_prompt_only(client, runtime_headers):
    agent = await create_agent(client)
    path = f"/agents/{agent['id']}/flow"
    await client.put(path, json=SMALL_FLOW)

    removed = (await client.delete(path)).json()
    no_flow_publish = await client.post(f"{path}/publish")
    draft = await client.get(
        f"/runtime/agents/{agent['id']}", params={"flow": "draft"}, headers=runtime_headers
    )

    assert removed["flow"] is None
    assert no_flow_publish.status_code == 409
    assert draft.json()["flow"] is None


async def test_clinic_template_creates_an_agent_with_its_flow(client):
    response = await client.post("/agents/from-template", json={"template_id": "clinic-booking"})

    flow = (await client.get(f"/agents/{response.json()['id']}/flow")).json()

    assert response.json()["has_flow"]
    assert flow["issues"] == []
    assert get_settings().demo_clinic_api_url in str(flow["flow"])


async def test_cal_com_clinic_template_asks_for_the_key_and_each_event_type(client):
    response = await client.post(
        "/agents/from-template", json={"template_id": "clinic-booking-calcom"}
    )

    draft = (await client.get(f"/agents/{response.json()['id']}/flow")).json()

    messages = {issue["message"] for issue in draft["issues"]}
    assert "Secret CALCOM_KEY is not saved (add it under Settings, Secrets)" in messages
    assert (
        "Set the Cal.com event type for Dr. Anil Sharma, Dr. Priya Mehta, Dr. Ravi Iyer, "
        "Dr. Sana Khan" in messages
    )


async def test_cal_com_clinic_flow_publishes_once_the_key_and_event_types_are_set(client):
    calcom = calcom_clinic_settings()
    for number, resource in enumerate(calcom.resources, start=1):
        resource.event_type_id = number
    flow = build_clinic_booking_flow("http://api:8000", calcom=calcom).model_dump(mode="json")
    agent = await create_agent(client)
    await client.put("/secrets/CALCOM_KEY", json={"value": "cal_live_0123456789abcdef"})
    await client.put(f"/agents/{agent['id']}/flow", json=flow)

    published = await client.post(f"/agents/{agent['id']}/flow/publish")

    assert published.status_code == 200, published.text


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"calcom": None}, "Set up the Cal.com settings"),
        ({"api_key_secret": ""}, "Choose the secret that holds the Cal.com API key"),
        ({"resources": []}, "Add at least one doctor and its Cal.com event type"),
        ({"time_zone": "India"}, "'India' is not a time zone, e.g. Asia/Kolkata"),
    ],
)
def test_cal_com_tools_need_their_settings(change, message):
    calcom = {
        "api_key_secret": "CALCOM_KEY",
        "resources": [{"name": "Dr. Priya Mehta", "event_type_id": 7}],
    }
    data = {"kind": "calcom_booking", "name": "book", "calcom": {**calcom, **change}}
    if change == {"calcom": None}:
        data["calcom"] = None
    nodes = [*SMALL_FLOW["nodes"], {"id": "book", "type": "tool", "data": data}]
    nodes[1] = {**nodes[1], "data": {**nodes[1]["data"], "tools": ["book"]}}

    assert message in issues_of({**SMALL_FLOW, "nodes": nodes})


@pytest.mark.parametrize("method", ["get", "put", "delete"])
async def test_flow_of_an_unknown_agent_is_not_found(client, method):
    kwargs = {"json": SMALL_FLOW} if method == "put" else {}

    response = await getattr(client, method)("/agents/missing/flow", **kwargs)

    assert response.status_code == 404
    assert (await client.post("/agents/missing/flow/publish")).status_code == 404
    assert (await client.get("/agents/missing/flow/versions")).status_code == 404


def test_tool_can_only_save_to_fields_that_exist():
    nodes = [
        *SMALL_FLOW["nodes"],
        {
            "id": "lookup",
            "type": "tool",
            "data": {
                "name": "lookup",
                "url": "https://crm.example/lookup",
                "save_to_fields": {"email": "contact.email", "vip": "contact.vip"},
            },
        },
    ]
    nodes[1] = {**nodes[1], "data": {**nodes[1]["data"], "tools": ["lookup"]}}

    assert "Save to fields: ['vip'] are not fields of any step" in issues_of(
        {**SMALL_FLOW, "nodes": nodes}
    )
