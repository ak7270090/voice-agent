from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from studio_backend.campaigns.dialler import in_window, run_dialler
from studio_backend.campaigns.models import Campaign

from tests.test_agents import create_agent
from tests.test_phone_numbers import OUTBOUND, add_number

INDIA = ZoneInfo("Asia/Kolkata")
# The dialler's clock; call outcomes use the real one, so they start from now. Test campaigns
# call all day unless a test sets a window.
NOW = datetime.now(INDIA)
ALL_DAY = {"window_start": "00:00", "window_end": "23:59:59"}
# Long enough that no test call counts as lost unless a test says so.
NEVER_LOST = timedelta(days=2)
CSV = (
    "phone,name,consent,appointment_time\n"
    "+919800000001,Asha,yes,4 pm\n"
    "+919800000002,Ravi,no,5 pm\n"
    "98000,Bad,yes,6 pm\n"
)


async def make_campaign(client, contacts: int = 0, **changes) -> dict:
    agent = await create_agent(client)
    number = await add_number(client, outbound=OUTBOUND)
    body = {"name": "Reminders", "agent_id": agent["id"], "from_number_id": number["id"]}
    response = await client.post("/campaigns", json={**body, **ALL_DAY, **changes})
    assert response.status_code == 201, response.text
    campaign = response.json()
    if contacts:
        people = [
            {"phone": f"+91980000{n:04d}", "name": f"Contact {n}", "consent": True}
            for n in range(contacts)
        ]
        await client.post(f"/campaigns/{campaign['id']}/contacts", json=people)
    return campaign


async def start(client, campaign: dict) -> None:
    assert (await client.post(f"/campaigns/{campaign['id']}/start")).status_code == 200


async def dial(client, telephony, now: datetime = NOW, lost_after=NEVER_LOST) -> list[str]:
    async with client.app.state.session_factory() as session:
        return await run_dialler(session, telephony, now, lost_after)


async def contacts_of(client, campaign: dict) -> list[dict]:
    return (await client.get(f"/campaigns/{campaign['id']}/contacts")).json()


async def end_call(client, headers, telephony, room: str, outcome: str | None) -> None:
    """What the runtime does: start the call record, then end it with the flow's outcome."""
    metadata = next(m for r, m in telephony.dispatches if r == room)
    started = await client.post(
        "/runtime/calls",
        json={
            "agent_id": metadata["agent_id"],
            "room_name": room,
            "channel": "phone",
            "direction": "outbound",
            "remote_number": metadata["dial_to"],
            "campaign_contact_id": metadata["campaign_contact_id"],
        },
        headers=headers,
    )
    call_id = started.json()["id"]
    await client.post(f"/runtime/calls/{call_id}/end", json={"outcome": outcome}, headers=headers)


async def test_a_campaign_needs_a_number_that_can_call_out(client):
    agent = await create_agent(client)
    number = await add_number(client)

    response = await client.post(
        "/campaigns",
        json={"name": "R", "agent_id": agent["id"], "from_number_id": number["id"]},
    )

    assert response.status_code == 409


@pytest.mark.parametrize(
    "changes",
    [{"window_start": "20:00", "window_end": "09:00"}, {"timezone": "Mars/Base"}],
)
async def test_a_window_that_ends_first_or_an_unknown_time_zone_is_rejected(client, changes):
    agent = await create_agent(client)
    number = await add_number(client, outbound=OUTBOUND)
    body = {"name": "R", "agent_id": agent["id"], "from_number_id": number["id"], **changes}

    assert (await client.post("/campaigns", json=body)).status_code == 422


async def test_csv_import_keeps_extra_columns_skips_no_consent_and_lists_bad_rows(client):
    campaign = await make_campaign(client)

    response = await client.post(
        f"/campaigns/{campaign['id']}/contacts/csv",
        files={"file": ("contacts.csv", CSV.encode(), "text/csv")},
    )

    result = response.json()
    contacts = await contacts_of(client, campaign)
    assert result["added"] == 2 and result["skipped"] == 1
    assert result["rejected"][0]["row"] == 4
    assert contacts[0]["variables"] == {"appointment_time": "4 pm"}
    assert [c["status"] for c in contacts] == ["pending", "skipped"]


async def test_campaigns_start_pause_and_resume_but_a_paused_one_cannot_pause(client):
    campaign = await make_campaign(client)
    path = f"/campaigns/{campaign['id']}"

    assert (await client.post(f"{path}/start")).json()["status"] == "running"
    assert (await client.post(f"{path}/pause")).json()["status"] == "paused"
    assert (await client.post(f"{path}/pause")).status_code == 409
    assert (await client.post(f"{path}/start")).json()["status"] == "running"


def test_the_calling_window_is_in_the_campaigns_time_zone():
    campaign = Campaign(window_start=time(9), window_end=time(20), timezone="Asia/Kolkata")

    # 03:00 UTC is 08:30 in India; 03:30 UTC is 09:00.
    assert not in_window(campaign, datetime(2026, 11, 2, 3, 0, tzinfo=ZoneInfo("UTC")))
    assert in_window(campaign, datetime(2026, 11, 2, 3, 30, tzinfo=ZoneInfo("UTC")))
    assert not in_window(campaign, datetime(2026, 11, 2, 14, 30, tzinfo=ZoneInfo("UTC")))


async def test_nothing_is_dialled_outside_the_window_or_while_paused(client, telephony):
    campaign = await make_campaign(client, contacts=2, window_start="09:00", window_end="20:00")
    noon = datetime.combine(NOW.date(), time(12, 0), INDIA)

    assert await dial(client, telephony, noon) == []  # still a draft
    await start(client, campaign)
    assert await dial(client, telephony, noon.replace(hour=21)) == []
    await client.post(f"/campaigns/{campaign['id']}/pause")
    assert await dial(client, telephony, noon) == []


async def test_never_more_calls_at_once_than_the_limit(client, telephony, runtime_headers):
    campaign = await make_campaign(client, contacts=5, max_concurrent=2)
    await start(client, campaign)

    first = await dial(client, telephony)
    again = await dial(client, telephony)
    await end_call(client, runtime_headers, telephony, first[0], "confirmed")
    after_one_ended = await dial(client, telephony)

    assert len(first) == 2
    assert again == []
    assert len(after_one_ended) == 1


async def test_the_call_carries_the_number_the_contact_and_its_variables(client, telephony):
    campaign = await make_campaign(client)
    await client.post(
        f"/campaigns/{campaign['id']}/contacts/csv",
        files={"file": ("c.csv", CSV.encode(), "text/csv")},
    )
    await start(client, campaign)

    (room,) = await dial(client, telephony)

    metadata = dict(telephony.dispatches)[room]
    assert metadata["dial_to"] == "+919800000001"
    assert metadata["variables"] == {"name": "Asha", "appointment_time": "4 pm"}
    assert telephony.trunks[metadata["outbound_trunk_id"]]["direction"] == "outbound"


async def test_nobody_reached_is_retried_after_the_wait_until_attempts_run_out(
    client, telephony, runtime_headers
):
    campaign = await make_campaign(client, contacts=1, max_attempts=2, retry_after_minutes=30)
    await start(client, campaign)

    (first,) = await dial(client, telephony)
    await end_call(client, runtime_headers, telephony, first, "not_answered")
    too_soon = await dial(client, telephony, NOW + timedelta(minutes=10))
    (second,) = await dial(client, telephony, NOW + timedelta(minutes=31))
    await end_call(client, runtime_headers, telephony, second, "answering_machine")
    (contact,) = await contacts_of(client, campaign)

    assert too_soon == []
    assert second != first
    assert contact["status"] == "failed" and contact["attempts"] == 2
    # The next dialler pass finds nobody left to call.
    await dial(client, telephony, NOW + timedelta(minutes=32))
    assert (await client.get(f"/campaigns/{campaign['id']}")).json()["status"] == "completed"


async def test_an_opt_out_is_never_called_again_and_a_reached_person_is_done(
    client, telephony, runtime_headers
):
    campaign = await make_campaign(client, contacts=2)
    await start(client, campaign)

    rooms = await dial(client, telephony)
    await end_call(client, runtime_headers, telephony, rooms[0], "opted_out")
    await end_call(client, runtime_headers, telephony, rooms[1], "voicemail_left")
    later = await dial(client, telephony, NOW + timedelta(hours=3))

    assert later == []
    assert [c["status"] for c in await contacts_of(client, campaign)] == ["opted_out", "done"]
    assert (await client.get(f"/campaigns/{campaign['id']}")).json()["counts"] == {
        "opted_out": 1,
        "done": 1,
    }


async def test_contacts_without_consent_are_never_dialled(client, telephony):
    campaign = await make_campaign(client)
    await client.post(
        f"/campaigns/{campaign['id']}/contacts",
        json=[{"phone": "+919800000009", "name": "No consent", "consent": False}],
    )
    await start(client, campaign)

    assert await dial(client, telephony) == []
    assert (await client.get(f"/campaigns/{campaign['id']}")).json()["status"] == "completed"


async def test_a_call_that_never_reports_back_counts_as_not_answered(client, telephony):
    campaign = await make_campaign(client, contacts=1)
    await start(client, campaign)
    await dial(client, telephony)

    await dial(
        client, telephony, datetime.now(INDIA) + timedelta(minutes=20), timedelta(minutes=15)
    )

    (contact,) = await contacts_of(client, campaign)
    assert contact["status"] == "retry" and contact["outcome"] == "not_answered"


async def test_a_late_report_from_an_abandoned_call_changes_nothing(
    client, telephony, runtime_headers
):
    campaign = await make_campaign(client, contacts=1, retry_after_minutes=1)
    await start(client, campaign)
    (first,) = await dial(client, telephony)
    lost = datetime.now(INDIA) + timedelta(minutes=20)
    await dial(client, telephony, lost, timedelta(minutes=15))
    (second,) = await dial(client, telephony, lost + timedelta(minutes=2), NEVER_LOST)

    await end_call(client, runtime_headers, telephony, first, "confirmed")

    (contact,) = await contacts_of(client, campaign)
    assert second != first
    assert contact["status"] == "calling" and contact["attempts"] == 2


async def test_a_call_livekit_refuses_is_not_counted_and_is_tried_again(client, telephony):
    campaign = await make_campaign(client, contacts=1)
    await start(client, campaign)
    telephony.fail_on = "dispatch"

    refused = await dial(client, telephony)
    telephony.fail_on = None
    (placed,) = await dial(client, telephony)

    (contact,) = await contacts_of(client, campaign)
    assert refused == []
    assert contact["attempts"] == 1 and placed.endswith("-1")
