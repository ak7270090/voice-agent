"""Cal.com tools against a fake Cal.com that checks what a real one needs (key, version headers,
a UTC booking time) and answers in its v2 format."""

import json
from datetime import date

import httpx
import pytest
from studio_voice.flows.runner import FlowRunner
from studio_voice.flows.schema import CalcomResource, Flow, ToolData
from studio_voice.languages import parsers_for
from studio_voice.tools.calcom import call_calcom, find_resource

KEY = "cal_live_0123456789abcdef"
MONDAY = date(2026, 11, 2)
RESOURCES = [
    {"name": "Dr. Priya Mehta", "event_type_id": 7724786, "keywords": ["skin", "rash"]},
    {"name": "Dr. Anil Sharma", "event_type_id": 7724785, "keywords": ["fever"]},
]
SETTINGS = {
    "api_key_secret": "CALCOM_KEY",
    "time_zone": "Asia/Kolkata",
    "resources": RESOURCES,
    "attendee_email": "front-desk@example.com",
}


class FakeCalcom:
    """Dr. Mehta has 11:00 and 11:30 on Monday 2 November, nothing on Tuesday, 11:00 on
    Wednesday. Booking 11:00 Monday works once; the second time it is taken."""

    def __init__(self, status: int = 200) -> None:
        self.status = status
        self.requests: list[httpx.Request] = []
        self.booked: set[str] = set()

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.headers.get("Authorization") != f"Bearer {KEY}":
            return httpx.Response(401, json={"status": "error"})
        if self.status != 200:
            return httpx.Response(self.status, json={"status": "error"})
        if request.url.path == "/v2/slots":
            assert request.headers["cal-api-version"] == "2024-09-04"
            return httpx.Response(
                200,
                json={
                    "status": "success",
                    "data": {
                        "2026-11-02": [
                            {"start": "2026-11-02T11:00:00.000+05:30"},
                            {"start": "2026-11-02T11:30:00.000+05:30"},
                        ],
                        "2026-11-04": [{"start": "2026-11-04T11:00:00.000+05:30"}],
                    },
                },
            )
        if request.url.path == "/v2/me":
            return httpx.Response(
                200, json={"status": "success", "data": {"email": "clinic@hospital.test"}}
            )
        assert request.url.path == "/v2/bookings"
        assert request.headers["cal-api-version"] == "2024-08-13"
        start = json.loads(request.content)["start"]
        if start in self.booked:
            message = "User either already has booking at this time or is not available"
            return httpx.Response(400, json={"status": "error", "error": {"message": message}})
        self.booked.add(start)
        return httpx.Response(201, json={"status": "success", "data": {"id": 11223344}})


def tool(kind: str, **settings) -> ToolData:
    name = "check_availability" if kind == "calcom_availability" else "book_appointment"
    return ToolData(kind=kind, name=name, calcom={**SETTINGS, **settings})


async def run(fake: FakeCalcom, data: ToolData, values: dict, secrets: dict | None = None):
    async with httpx.AsyncClient(transport=httpx.MockTransport(fake)) as http:
        return await call_calcom(
            http, data, values, {"CALCOM_KEY": KEY} if secrets is None else secrets
        )


@pytest.mark.parametrize(
    ("said", "expected"),
    [
        ("Dr. Priya Mehta", "Dr. Priya Mehta"),
        ("Priya", "Dr. Priya Mehta"),
        ("doctor mehta", "Dr. Priya Mehta"),
        ("a skin doctor", "Dr. Priya Mehta"),
        ("Sharma", "Dr. Anil Sharma"),
        ("a doctor", None),
        ("Dr. Khan", None),
    ],
)
def test_a_resource_is_found_by_name_part_or_keyword(said, expected):
    resources = [CalcomResource(**resource) for resource in RESOURCES]

    found = find_resource(resources, said)

    assert (found.name if found else None) == expected


async def test_free_times_are_the_days_slots_in_local_time():
    fake = FakeCalcom()

    result = await run(fake, tool("calcom_availability"), {"doctor": "Priya", "day": "2026-11-02"})

    assert result.ok
    assert result.data == {
        "doctor": "Dr. Priya Mehta",
        "day": "2026-11-02",
        "weekday": "Monday",
        "free_times": ["11:00", "11:30"],
        "next_open_days": [],
    }
    params = fake.requests[0].url.params
    assert (params["eventTypeId"], params["start"], params["end"]) == (
        "7724786",
        "2026-11-02",
        "2026-11-15",
    )
    assert params["timeZone"] == "Asia/Kolkata"


async def test_a_day_with_nothing_free_offers_the_next_open_days():
    result = await run(
        FakeCalcom(), tool("calcom_availability"), {"doctor": "skin", "day": "2026-11-03"}
    )

    assert result.data["free_times"] == []
    assert result.data["next_open_days"] == ["Wednesday 2026-11-04"]


async def test_an_unknown_doctor_fails_with_the_choices_and_sends_nothing():
    fake = FakeCalcom()

    result = await run(
        fake, tool("calcom_availability"), {"doctor": "Dr. Khan", "day": "2026-11-02"}
    )

    assert not result.ok
    assert result.data["choices"] == ["Dr. Priya Mehta", "Dr. Anil Sharma"]
    assert fake.requests == []


async def test_booking_sends_the_time_in_utc_with_the_attendee_and_call_details():
    fake = FakeCalcom()
    values = {
        "doctor": "Dr. Priya Mehta",
        "day": "2026-11-02",
        "time": "11:00",
        "patient_name": "Asha Rao",
        "patient_age": 34,
    }

    result = await run(fake, tool("calcom_booking"), values)

    sent = json.loads(fake.requests[0].content)
    assert sent["start"] == "2026-11-02T05:30:00Z"
    assert sent["eventTypeId"] == 7724786
    assert sent["attendee"] == {
        "name": "Asha Rao",
        "email": "front-desk@example.com",
        "timeZone": "Asia/Kolkata",
    }
    assert sent["metadata"]["patient_age"] == "34"
    assert result.ok
    assert result.data == {
        "booking_id": "11223344",
        "doctor": "Dr. Priya Mehta",
        "patient_name": "Asha Rao",
        "day": "2026-11-02",
        "weekday": "Monday",
        "time": "11:00",
    }


async def test_a_collected_email_is_used_and_a_taken_slot_says_so():
    fake = FakeCalcom()
    values = {
        "doctor": "Priya",
        "day": "2026-11-02",
        "time": "11:00",
        "patient_name": "Asha Rao",
        "email": "asha@example.com",
    }

    await run(fake, tool("calcom_booking"), values)
    again = await run(fake, tool("calcom_booking"), values)

    assert json.loads(fake.requests[0].content)["attendee"]["email"] == "asha@example.com"
    assert not again.ok
    assert again.data["error"] == "that time is no longer free"


async def test_without_an_attendee_email_the_booking_goes_to_the_cal_com_accounts_email():
    fake = FakeCalcom()
    values = {"doctor": "Priya", "day": "2026-11-02", "time": "11:30", "patient_name": "Ravi"}

    result = await run(fake, tool("calcom_booking", attendee_email=""), values)

    assert result.ok
    assert [request.url.path for request in fake.requests] == ["/v2/me", "/v2/bookings"]
    assert json.loads(fake.requests[1].content)["attendee"]["email"] == "clinic@hospital.test"


@pytest.mark.parametrize(
    ("status", "error", "unavailable"),
    [(503, "Cal.com did not answer", True), (403, "Cal.com refused the API key", False)],
)
async def test_cal_com_errors_say_whether_to_try_again(status, error, unavailable):
    result = await run(
        FakeCalcom(status), tool("calcom_availability"), {"doctor": "Priya", "day": "2026-11-02"}
    )

    assert (result.ok, result.data["error"], result.unavailable) == (False, error, unavailable)


async def test_without_the_key_nothing_is_sent():
    fake = FakeCalcom()

    result = await run(
        fake, tool("calcom_availability"), {"doctor": "Priya", "day": "2026-11-02"}, secrets={}
    )

    assert result.data == {"error": "secret CALCOM_KEY is not set"}
    assert fake.requests == []


async def test_in_a_flow_the_result_fills_fields_and_the_end_message_without_the_key():
    fake = FakeCalcom()
    check = tool("calcom_availability").model_dump()
    check["save_to_fields"] = {"doctor": "doctor"}
    flow = Flow.model_validate(
        {
            "nodes": [
                {"id": "start", "type": "start"},
                {"id": "check", "type": "tool", "data": check},
                {"id": "done", "type": "end", "data": {"message": "{doctor} is free {weekday}."}},
            ],
            "edges": [
                {"id": "e1", "source": "start", "target": "check", "kind": "always"},
                {"id": "e2", "source": "check", "target": "done", "kind": "success"},
            ],
        }
    )
    runner = FlowRunner(
        flow,
        httpx.AsyncClient(transport=httpx.MockTransport(fake)),
        parsers_for("en"),
        MONDAY,
        call_values={"doctor": "skin", "day": "2026-11-02"},
        secrets={"CALCOM_KEY": KEY},
    )

    await runner.start()

    assert runner.fields["doctor"] == "Dr. Priya Mehta"
    assert runner.final_message == "Dr. Priya Mehta is free Monday."
    assert runner.tool_calls[0]["ok"]
    assert KEY not in json.dumps(runner.tool_calls)
