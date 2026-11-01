"""Live check of Phase 7: a typed call books a real Cal.com slot, and the call's signed webhooks
reach a local receiver.

    runtime\\.venv\\Scripts\\python.exe tools\\integrations\\calcom_check.py

Needs the stack up (API, worker, runtime), CALCOM_API_KEY in .env.local, and the Cal.com event
types made for the demo clinic's doctors (titles start with the doctor's name). The worker
reaches the receiver at host.docker.internal. The test booking is cancelled at the end.
"""

import asyncio
import hashlib
import hmac
import json
import secrets
import sys
import threading
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

sys.path.insert(0, str(Path(__file__).parents[1] / "scenarios"))
from run_scenarios import TesterCall, spoken_clock, spoken_day  # noqa: E402

API = "http://localhost:8000"
CALCOM = "https://api.cal.com/v2"
ENV_FILE = Path(__file__).parents[2] / ".env.local"
TEMPLATE_ID = "clinic-booking-calcom"
AGENT_NAME = "Clinic booking (Cal.com check)"
DOCTOR = "Dr. Priya Mehta"
TIME_ZONE = "Asia/Kolkata"
RECEIVER_PORT = 9911
RECEIVER_URL = f"http://host.docker.internal:{RECEIVER_PORT}/calls"
DELIVERY_WAIT_SECONDS = 90
RECORD_WAIT_SECONDS = 4


def env_value(name: str) -> str:
    for line in ENV_FILE.read_text().splitlines():
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1].strip()
    raise SystemExit(f"{name} is not set in .env.local")


class Receiver(BaseHTTPRequestHandler):
    """Keeps each webhook with whether its signature checks out."""

    signing_secret = ""
    received: list[dict] = []

    def do_POST(self) -> None:  # noqa: N802 - the http.server hook name
        body = self.rfile.read(int(self.headers["Content-Length"]))
        timestamp = self.headers.get("X-Studio-Timestamp", "")
        expected = hmac.new(
            self.signing_secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256
        ).hexdigest()
        signed = hmac.compare_digest(
            self.headers.get("X-Studio-Signature", ""), f"sha256={expected}"
        )
        self.received.append(
            {"event": self.headers["X-Studio-Event"], "signed": signed, **json.loads(body)}
        )
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args) -> None:
        pass


async def event_types(calcom: httpx.AsyncClient) -> dict[str, int]:
    found = (await calcom.get("/event-types", headers={"cal-api-version": "2024-06-14"})).json()
    return {event["title"]: event["id"] for event in found["data"]}


async def free_slot(calcom: httpx.AsyncClient, event_type_id: int) -> tuple[date, str]:
    """The last free time on the doctor's first open day at least two days out."""
    start = date.today() + timedelta(days=2)
    response = await calcom.get(
        "/slots",
        params={
            "eventTypeId": event_type_id,
            "start": start.isoformat(),
            "end": (start + timedelta(days=13)).isoformat(),
            "timeZone": TIME_ZONE,
        },
        headers={"cal-api-version": "2024-09-04"},
    )
    by_day = response.raise_for_status().json()["data"]
    day = min(slot_day for slot_day, slots in by_day.items() if slots)
    last = by_day[day][-1]["start"]
    return date.fromisoformat(day), datetime.fromisoformat(last).astimezone(
        ZoneInfo(TIME_ZONE)
    ).strftime("%H:%M")


async def check_agent(api: httpx.AsyncClient, ids: dict[str, int]) -> str:
    templates = (await api.get("/agent-templates")).json()
    flow = next(t for t in templates if t["id"] == TEMPLATE_ID)["flow"]
    for node in flow["nodes"]:
        for resource in (node["data"].get("calcom") or {}).get("resources", []):
            resource["event_type_id"] = next(
                id_ for title, id_ in ids.items() if title.startswith(resource["name"])
            )
    agents = (await api.get("/agents")).json()
    agent = next((a for a in agents if a["name"] == AGENT_NAME), None)
    if agent is None:
        created = await api.post(
            "/agents/from-template", json={"template_id": TEMPLATE_ID, "name": AGENT_NAME}
        )
        agent = created.raise_for_status().json()
    (await api.put(f"/agents/{agent['id']}/flow", json=flow)).raise_for_status()
    draft = (await api.get(f"/agents/{agent['id']}/flow")).json()
    if draft["issues"]:
        raise SystemExit(f"flow issues: {draft['issues']}")
    hooks = [
        {
            "id": f"hook-{event}",
            "kind": "webhook",
            "event": event,
            "url": RECEIVER_URL,
            "secret": "WEBHOOK_SECRET",
        }
        for event in ("call.ended", "call.analysed")
    ]
    response = await api.patch(f"/agents/{agent['id']}", json={"after_call_actions": hooks})
    response.raise_for_status()
    return agent["id"]


async def main() -> int:
    calcom_key = env_value("CALCOM_API_KEY")
    signing_secret = secrets.token_hex(16)
    Receiver.signing_secret = signing_secret
    server = HTTPServer(("0.0.0.0", RECEIVER_PORT), Receiver)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    calcom = httpx.AsyncClient(
        base_url=CALCOM, headers={"Authorization": f"Bearer {calcom_key}"}, timeout=20
    )
    async with httpx.AsyncClient(base_url=API, timeout=20) as api:
        for name, value in (("CALCOM_KEY", calcom_key), ("WEBHOOK_SECRET", signing_secret)):
            (await api.put(f"/secrets/{name}", json={"value": value})).raise_for_status()
        ids = await event_types(calcom)
        agent_id = await check_agent(api, ids)
        day, clock = await free_slot(
            calcom, next(i for t, i in ids.items() if t.startswith(DOCTOR))
        )
        print(f"booking {DOCTOR} on {day} at {clock}")

        browser_call = (
            (await api.post(f"/agents/{agent_id}/browser-calls")).raise_for_status().json()
        )
        call = TesterCall()
        await call.join(browser_call["url"], browser_call["token"])
        await call.say(None)
        for line in (
            "I want to book an appointment with the skin doctor.",
            "My name is Test Patient and I am 30 years old.",
            f"{spoken_day(day)}, please.",
            f"{spoken_clock(clock)} works.",
            "Yes.",
        ):
            await call.say(line)
            print(f"  caller: {line}\n  agent:  {call.replies[-1] if call.replies else ''}")
        await call.leave()
        await asyncio.sleep(RECORD_WAIT_SECONDS)

        calls = (await api.get("/calls", params={"agent_id": agent_id, "limit": 5})).json()
        record = next(c for c in calls if c["room_name"] == browser_call["room"])
        bookings = [t for t in record["tool_calls"] if t["name"] == "book_appointment" and t["ok"]]
        booking_id = json.loads(bookings[-1]["result"])["booking_id"] if bookings else None
        booked_at = record["fields"].get("time")
        print(f"outcome: {record['outcome']}, booking id: {booking_id}, time: {booked_at}")
        print("key in the call record:", calcom_key in json.dumps(record))

        deliveries = []
        for _ in range(DELIVERY_WAIT_SECONDS):
            deliveries = (await api.get(f"/calls/{record['id']}/deliveries")).json()
            if len(deliveries) == 2 and all(d["status"] != "pending" for d in deliveries):
                break
            await asyncio.sleep(1)
        print("deliveries:", [(d["event"], d["status"], d["response_status"]) for d in deliveries])
        print(
            "received:",
            [
                (r["event"], r["signed"], r["call"]["outcome"], bool(r["call"]["summary"]))
                for r in Receiver.received
            ],
        )

        passed = record["outcome"] == "booked" and booking_id is not None
        if booking_id:
            listed = await calcom.get(
                "/bookings",
                params={"status": "upcoming", "take": 50},
                headers={"cal-api-version": "2024-08-13"},
            )
            booking = next((b for b in listed.json()["data"] if str(b["id"]) == booking_id), None)
            print("in Cal.com:", booking is not None and booking["start"])
            passed = passed and booking is not None
            if booking:
                cancelled = await calcom.post(
                    f"/bookings/{booking['uid']}/cancel",
                    json={"cancellationReason": "Automated Phase 7 check"},
                    headers={"cal-api-version": "2024-08-13"},
                )
                print("test booking cancelled:", cancelled.status_code)
        signed = sorted(r["event"] for r in Receiver.received if r["signed"])
        passed = passed and signed == ["call.analysed", "call.ended"]
    await calcom.aclose()
    server.shutdown()
    print("PASSED" if passed else "FAILED")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
