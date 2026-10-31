"""Agent-to-agent campaign run: real outbound calls through LiveKit, answered by agents.

The campaign's outbound trunk points at this project's own LiveKit SIP URI, so each call rings
one of our test numbers, where a small "customer" agent plays one part: a patient who will come,
one who wants another time, one who asks not to be called again, an answering machine. One
number has no trunk (nobody answers) and one contact gave no consent. The run passes when every
contact ends as expected and no more calls ran at once than the campaign allows.

    runtime\\.venv\\Scripts\\python.exe tools\\campaigns\\agent_to_agent.py <sip-host> [--clean]

<sip-host> is the LiveKit project's SIP URI without "sip:" (LiveKit dashboard → Settings).
Needs the stack up (API, worker, runtime). Costs LiveKit, speech and LLM minutes only.
"""

import argparse
import asyncio
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx

API = "http://localhost:8000"
TEMPLATE_ID = "appointment-reminder"
CAMPAIGN_AGENT = "Reminder (campaign runs)"
CALLER_ID = "+15005550111"
NOBODY_THERE = "+15005550299"
TIMEZONE = "Asia/Kolkata"
MAX_CONCURRENT = 2
MAX_ATTEMPTS = 2
RUN_TIMEOUT_SECONDS = 600
POLL_SECONDS = 2
GREETING = (
    "Hello {name}, this is City Hospital calling about your appointment tomorrow at "
    "{appointment_time}. Will you be able to come?"
)
VOICEMAIL = (
    "Hello {name}, this is City Hospital reminding you of your appointment tomorrow at "
    "{appointment_time}. Please call us if you need to change it. Goodbye."
)
CUSTOMER_RULES = "Answer in one short sentence. Never ask questions back."


@dataclass(frozen=True)
class Persona:
    name: str
    number: str
    greeting: str
    instructions: str


@dataclass(frozen=True)
class Expected:
    name: str
    phone: str
    consent: bool
    status: str
    outcome: str | None


PERSONAS = [
    Persona(
        "Asha",
        "+15005550201",
        "Hello?",
        "You are Asha, a patient. When reminded of your appointment, say yes, you will come.",
    ),
    Persona(
        "Ravi",
        "+15005550202",
        "Hello?",
        "You are Ravi, a patient. You cannot come tomorrow: ask to move the appointment.",
    ),
    Persona(
        "Meena",
        "+15005550203",
        "Hello?",
        "You are Meena. You do not want these calls: ask them not to call you again.",
    ),
    Persona(
        "Rohan",
        "+15005550204",
        "Hi, you've reached Rohan Gupta. I can't take your call right now. Please leave your "
        "name and number after the tone.",
        "You are an answering machine. After your greeting, say nothing at all.",
    ),
]
EXPECTED = [
    Expected("Asha", "+15005550201", True, "done", "confirmed"),
    Expected("Ravi", "+15005550202", True, "done", "reschedule_requested"),
    Expected("Meena", "+15005550203", True, "opted_out", "opted_out"),
    Expected("Rohan", "+15005550204", True, "done", "voicemail_left"),
    Expected("Kiran", NOBODY_THERE, True, "failed", "not_answered"),
    Expected("Dev", "+15005550205", False, "skipped", None),
]


async def ok(response: httpx.Response) -> dict | list:
    if response.is_error:
        raise RuntimeError(f"{response.request.method} {response.request.url}: {response.text}")
    return response.json() if response.content else {}


async def number_for(
    api: httpx.AsyncClient, number: str, agent_id: str | None, outbound: dict | None = None
) -> dict:
    """The test number, added (with its LiveKit trunks) on the first run, rebound after."""
    existing = next(
        (n for n in await ok(await api.get("/phone-numbers")) if n["number"] == number), None
    )
    if existing is None:
        body = {"number": number, "label": "campaign runs", "provider": "sip_trunk"}
        return await ok(
            await api.post(
                "/phone-numbers", json={**body, "agent_id": agent_id, "outbound": outbound}
            )
        )
    return await ok(
        await api.patch(f"/phone-numbers/{existing['id']}", json={"agent_id": agent_id})
    )


async def agent_named(api: httpx.AsyncClient, name: str, create: dict) -> dict:
    agents = await ok(await api.get("/agents"))
    agent = next((a for a in agents if a["name"] == name), None)
    return agent or await ok(await api.post("/agents", json=create))


async def set_up(api: httpx.AsyncClient, sip_host: str) -> tuple[str, str]:
    """The reminder agent (published flow, personalised greeting) and the customer agents."""
    template = next(
        t for t in await ok(await api.get("/agent-templates")) if t["id"] == TEMPLATE_ID
    )
    reminder = await agent_named(
        api,
        CAMPAIGN_AGENT,
        {**template["fields"], "name": CAMPAIGN_AGENT},
    )
    await ok(
        await api.patch(
            f"/agents/{reminder['id']}",
            json={"greeting": GREETING, "voicemail_message": VOICEMAIL},
        )
    )
    await ok(await api.put(f"/agents/{reminder['id']}/flow", json=template["flow"]))
    await ok(await api.post(f"/agents/{reminder['id']}/flow/publish"))
    for persona in PERSONAS:
        customer = await agent_named(
            api,
            f"Customer: {persona.name}",
            {
                **template["fields"],
                "name": f"Customer: {persona.name}",
                "greeting": persona.greeting,
                "instructions": f"{persona.instructions} {CUSTOMER_RULES}",
            },
        )
        await number_for(api, persona.number, customer["id"])
    caller = await number_for(
        api, CALLER_ID, None, {"address": sip_host, "username": "", "password": ""}
    )
    return reminder["id"], caller["id"]


def window_around_now() -> dict:
    now = datetime.now(ZoneInfo(TIMEZONE))
    start, end = now - timedelta(minutes=5), now + timedelta(hours=1)
    if start.date() != end.date():
        return {"window_start": "00:00", "window_end": "23:59:59"}
    return {"window_start": f"{start:%H:%M}", "window_end": f"{end:%H:%M}"}


async def run(api: httpx.AsyncClient, sip_host: str) -> bool:
    agent_id, caller_id = await set_up(api, sip_host)
    campaign = await ok(
        await api.post(
            "/campaigns",
            json={
                "name": f"Agent-to-agent {datetime.now():%H:%M}",
                "agent_id": agent_id,
                "from_number_id": caller_id,
                "timezone": TIMEZONE,
                "max_concurrent": MAX_CONCURRENT,
                "max_attempts": MAX_ATTEMPTS,
                "retry_after_minutes": 1,
                **window_around_now(),
            },
        )
    )
    path = f"/campaigns/{campaign['id']}"
    contacts = [
        {
            "phone": e.phone,
            "name": e.name,
            "consent": e.consent,
            "variables": {"appointment_time": "4 pm"},
        }
        for e in EXPECTED
    ]
    await ok(await api.post(f"{path}/contacts", json=contacts))
    await ok(await api.post(f"{path}/start"))
    print(f"campaign {campaign['id']} started")
    most_at_once, deadline, last = 0, time.time() + RUN_TIMEOUT_SECONDS, ""
    while time.time() < deadline:
        await asyncio.sleep(POLL_SECONDS)
        state = await ok(await api.get(path))
        rows = await ok(await api.get(f"{path}/contacts"))
        most_at_once = max(most_at_once, sum(r["status"] == "calling" for r in rows))
        summary = ", ".join(f"{r['name']}={r['status']}" for r in rows)
        if summary != last:
            print(f"  {time.strftime('%H:%M:%S')} {summary}")
            last = summary
        if state["status"] == "completed":
            break
    rows = {r["name"]: r for r in await ok(await api.get(f"{path}/contacts"))}
    passed = most_at_once <= MAX_CONCURRENT
    print(f"\nmost calls at once: {most_at_once} (limit {MAX_CONCURRENT})")
    for e in EXPECTED:
        row = rows[e.name]
        good = row["status"] == e.status and row["outcome"] == e.outcome
        passed &= good
        print(
            f"{'PASS' if good else 'FAIL'}  {e.name:6} status={row['status']:10} "
            f"outcome={row['outcome']!s:22} attempts={row['attempts']}  "
            f"(expected {e.status}, {e.outcome})"
        )
    return passed


async def clean(api: httpx.AsyncClient) -> None:
    """Removes the test numbers (and their LiveKit trunks); their campaigns go with them."""
    test_numbers = {CALLER_ID, *(p.number for p in PERSONAS)}
    for number in await ok(await api.get("/phone-numbers")):
        if number["number"] in test_numbers:
            await api.delete(f"/phone-numbers/{number['id']}")


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("sip_host", help="LiveKit SIP URI host, e.g. abc123.sip.livekit.cloud")
    parser.add_argument("--clean", action="store_true", help="remove the test numbers after")
    args = parser.parse_args()
    async with httpx.AsyncClient(base_url=API, timeout=30) as api:
        try:
            passed = await run(api, args.sip_host)
        finally:
            if args.clean:
                await clean(api)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
