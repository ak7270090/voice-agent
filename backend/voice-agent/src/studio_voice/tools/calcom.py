"""Cal.com tools: a resource's (a doctor's) free times on a day, and booking one.

They answer in the demo clinic's shape (free_times, next_open_days, booking_id, ...), so a
booking flow works the same against either. Cal.com API v2: GET /slots, POST /bookings.
"""

import re
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from studio_voice.flows.schema import CalcomResource, CalcomSettings, ToolData
from studio_voice.tools.http_tool import ToolResult

AVAILABILITY_KIND = "calcom_availability"
BOOKING_KIND = "calcom_booking"
KINDS = (AVAILABILITY_KIND, BOOKING_KIND)
DAY_FIELD = "day"
TIME_FIELD = "time"
EMAIL_FIELD = "email"
# Each endpoint has its own version header; without it Cal.com answers in an older format.
SLOTS_API_VERSION = "2024-09-04"
BOOKINGS_API_VERSION = "2024-08-13"
ME_API_VERSION = "2024-06-11"
# One request covers the asked day and the days after it, for "next open days".
SEARCH_DAYS = 14
SUGGESTED_DAYS = 3
SERVER_ERROR_STATUS = 500
AUTH_ERROR_STATUSES = (401, 403)
# Booking metadata: Cal.com keeps up to 50 keys of up to 40 characters, values up to 500.
MAX_METADATA_KEYS = 20
MAX_METADATA_KEY_CHARS = 40
MAX_METADATA_VALUE_CHARS = 500
# Words that say "doctor" rather than which one.
TITLE_WORDS = {"dr", "doctor", "doc"}
SLOT_TAKEN_HINTS = ("not available", "already has booking", "no available", "taken")
SLOT_TAKEN = "that time is no longer free"


def words(text: str) -> list[str]:
    return [word for word in re.findall(r"[a-z]+", text.lower()) if word not in TITLE_WORDS]


def find_resource(resources: list[CalcomResource], text: str) -> CalcomResource | None:
    """By full name, first or last name ("Priya", "Dr. Mehta"), then a keyword ("skin")."""
    wanted = words(text)
    if not wanted:
        return None
    for resource in resources:
        if set(wanted) <= set(words(resource.name)):
            return resource
    lowered = text.lower()
    for resource in resources:
        if any(keyword.lower() in lowered for keyword in resource.keywords if keyword):
            return resource
    return None


def inputs(tool: ToolData) -> list[str]:
    """The fields the tool reads (an attached tool asks the LLM for these)."""
    calcom = tool.calcom or CalcomSettings()
    names = [calcom.resource_field, DAY_FIELD]
    if tool.kind == BOOKING_KIND:
        names += [TIME_FIELD, calcom.name_field]
    return names


def error_message(response: httpx.Response) -> str:
    try:
        error = response.json().get("error", {})
        message = error.get("message") if isinstance(error, dict) else str(error)
    except ValueError:
        message = None
    return str(message or response.text[:200] or response.status_code)


async def call_calcom(
    http: httpx.AsyncClient, tool: ToolData, values: dict[str, Any], secrets: dict[str, str]
) -> ToolResult:
    calcom = tool.calcom or CalcomSettings()
    key = secrets.get(calcom.api_key_secret) if calcom.api_key_secret else None
    if not key:
        return ToolResult(False, {"error": f"secret {calcom.api_key_secret or '?'} is not set"})
    needed = [name for name in inputs(tool) if values.get(name) in (None, "")]
    if needed:
        return ToolResult(False, {"error": f"missing value for {needed[0]}"})
    resource = find_resource(calcom.resources, str(values[calcom.resource_field]))
    if resource is None or resource.event_type_id is None:
        return ToolResult(
            False,
            {
                "error": f"no {calcom.resource_field} matches '{values[calcom.resource_field]}'",
                "choices": [entry.name for entry in calcom.resources],
            },
        )
    try:
        day = date.fromisoformat(str(values[DAY_FIELD]))
    except ValueError:
        return ToolResult(False, {"error": f"'{values[DAY_FIELD]}' is not a day (YYYY-MM-DD)"})
    headers = {"Authorization": f"Bearer {key}"}
    try:
        if tool.kind == AVAILABILITY_KIND:
            return await _availability(http, calcom, resource, day, headers)
        return await _book(http, calcom, resource, day, values, headers)
    except httpx.HTTPError as error:
        return ToolResult(False, {"error": type(error).__name__}, unavailable=True)


def _failed(response: httpx.Response) -> ToolResult:
    if response.status_code >= SERVER_ERROR_STATUS:
        return ToolResult(False, {"error": "Cal.com did not answer"}, unavailable=True)
    if response.status_code in AUTH_ERROR_STATUSES:
        return ToolResult(False, {"error": "Cal.com refused the API key"})
    return ToolResult(False, {"error": error_message(response)})


async def _availability(
    http: httpx.AsyncClient,
    calcom: CalcomSettings,
    resource: CalcomResource,
    day: date,
    headers: dict[str, str],
) -> ToolResult:
    response = await http.get(
        f"{calcom.api_url}/slots",
        params={
            "eventTypeId": resource.event_type_id,
            "start": day.isoformat(),
            "end": (day + timedelta(days=SEARCH_DAYS - 1)).isoformat(),
            "timeZone": calcom.time_zone,
        },
        headers={**headers, "cal-api-version": SLOTS_API_VERSION},
    )
    if not response.is_success:
        return _failed(response)
    # {"2026-11-02": [{"start": "2026-11-02T11:00:00.000+05:30"}, ...], ...}
    slots_by_day = response.json().get("data", {})
    zone = ZoneInfo(calcom.time_zone)
    times_by_day = {
        date.fromisoformat(slot_day): [
            datetime.fromisoformat(slot["start"]).astimezone(zone).strftime("%H:%M")
            for slot in slots
        ]
        for slot_day, slots in slots_by_day.items()
        if slots
    }
    free_times = times_by_day.get(day, [])
    next_open_days = []
    if not free_times:
        later = sorted(open_day for open_day in times_by_day if open_day > day)
        next_open_days = [f"{d:%A} {d.isoformat()}" for d in later[:SUGGESTED_DAYS]]
    return ToolResult(
        True,
        {
            calcom.resource_field: resource.name,
            "day": day.isoformat(),
            "weekday": f"{day:%A}",
            "free_times": free_times,
            "next_open_days": next_open_days,
        },
    )


def metadata(values: dict[str, Any]) -> dict[str, str]:
    """The call's collected details, kept on the booking for the front desk."""
    entries = [
        (name[:MAX_METADATA_KEY_CHARS], str(value)[:MAX_METADATA_VALUE_CHARS])
        for name, value in values.items()
        if value not in (None, "")
    ]
    return dict(entries[:MAX_METADATA_KEYS])


async def _account(
    http: httpx.AsyncClient, calcom: CalcomSettings, headers: dict[str, str]
) -> ToolResult:
    """The Cal.com account's own email: a phone caller rarely gives one, and Cal.com refuses
    addresses that cannot receive mail, so the booking goes to the clinic's inbox."""
    response = await http.get(
        f"{calcom.api_url}/me", headers={**headers, "cal-api-version": ME_API_VERSION}
    )
    if not response.is_success:
        return _failed(response)
    return ToolResult(True, {"email": response.json()["data"]["email"]})


async def _book(
    http: httpx.AsyncClient,
    calcom: CalcomSettings,
    resource: CalcomResource,
    day: date,
    values: dict[str, Any],
    headers: dict[str, str],
) -> ToolResult:
    try:
        start_time = time.fromisoformat(str(values[TIME_FIELD]))
    except ValueError:
        return ToolResult(False, {"error": f"'{values[TIME_FIELD]}' is not a time (HH:MM)"})
    zone = ZoneInfo(calcom.time_zone)
    start = datetime.combine(day, start_time, zone).astimezone(UTC)
    name = str(values[calcom.name_field])
    email = str(values.get(EMAIL_FIELD) or calcom.attendee_email)
    if not email:
        account = await _account(http, calcom, headers)
        if not account.ok:
            return account
        email = account.data["email"]
    response = await http.post(
        f"{calcom.api_url}/bookings",
        json={
            "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "eventTypeId": resource.event_type_id,
            "attendee": {"name": name, "email": email, "timeZone": calcom.time_zone},
            "metadata": metadata(values),
        },
        headers={**headers, "cal-api-version": BOOKINGS_API_VERSION},
    )
    if not response.is_success:
        failed = _failed(response)
        message = str(failed.data.get("error", "")).lower()
        if not failed.unavailable and any(hint in message for hint in SLOT_TAKEN_HINTS):
            return ToolResult(False, {"error": SLOT_TAKEN, "detail": failed.data["error"]})
        return failed
    booking = response.json().get("data", {})
    return ToolResult(
        True,
        {
            "booking_id": str(booking.get("id", "")),
            calcom.resource_field: resource.name,
            calcom.name_field: name,
            "day": day.isoformat(),
            "weekday": f"{day:%A}",
            "time": start_time.strftime("%H:%M"),
        },
    )
