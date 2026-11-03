"""Scenario regression run: typed calls against the running stack with the real LLM.

Each scenario joins a browser test call as the tester (LiveKit, like the console does), types
the caller's lines one by one, waits for each reply, and checks the call record the runtime
saves. A run fails when fewer scenarios pass, or the median reply is >10% slower, than the
saved baseline.

    backend\\voice-agent\\.venv\\Scripts\\python.exe evals\\run_scenarios.py [--save-baseline]

Needs the stack up (API, worker, runtime) and LiveKit keys in .env.local. Typed calls cost only
LLM tokens; the silent-caller check needs voice, so it stays a unit test (test_channels).
"""

import argparse
import asyncio
import json
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import httpx
from livekit import rtc

API = "http://localhost:8000"
DEMO_CLINIC = "http://localhost:8100"
TEMPLATE_ID = "clinic-booking"
AGENT_NAME = "Clinic booking (scenario runs)"
DOCTOR = "skin"
PHYSICIAN = "general physician"
AFTERNOON = "12:00"
DAYS_AHEAD = 60
# Booked, read back then changed (two), taken by someone else, and booked instead.
SLOTS_NEEDED = 5
TRANSCRIPTION_TOPIC = "lk.transcription"
CHAT_TOPIC = "lk.chat"
AGENT_STATE_ATTRIBUTE = "lk.agent.state"
LISTENING = "listening"
# A step's opening line and the rest of its reply arrive as separate messages; the agent is
# done when nothing new has come for this long and it is listening.
QUIET_SECONDS = 1.5
REPLY_TIMEOUT_SECONDS = 60
RECORD_WAIT_SECONDS = 4
# Fail the run if the median reply gets this much slower than the baseline.
ALLOWED_SLOWDOWN = 1.10
BASELINE_FILE = Path(__file__).with_name("scenarios_baseline.json")


@dataclass
class Scenario:
    name: str
    lines: list[str]
    # Any of these outcomes passes (None: the call ended without reaching an End node).
    expected_outcomes: tuple[str | None, ...]
    # A value, or a set of allowed values (e.g. any free afternoon time).
    expected_fields: dict = field(default_factory=dict)
    # Words some agent reply must contain (e.g. a doctor's name the agent had to offer).
    expected_in_replies: tuple[str, ...] = ()


@dataclass
class Result:
    scenario: Scenario
    passed: bool
    outcome: str | None
    reply_seconds: list[float]
    replies: list[str]
    problem: str = ""


class TesterCall:
    """One browser test call, joined the way the console joins it."""

    def __init__(self) -> None:
        self.room = rtc.Room()
        self.replies: list[str] = []
        self.first_text_at: float | None = None
        self.last_message_at = 0.0
        self.agent_state = ""
        self.ended = asyncio.Event()

    async def join(self, url: str, token: str) -> None:
        self.room.register_text_stream_handler(TRANSCRIPTION_TOPIC, self._on_stream)
        self.room.on("participant_attributes_changed", self._on_attributes)
        self.room.on("disconnected", lambda *_: self.ended.set())
        await self.room.connect(url, token)

    def _on_stream(self, reader: rtc.TextStreamReader, identity: str) -> None:
        if identity != self.room.local_participant.identity:
            asyncio.get_running_loop().create_task(self._read(reader))

    async def _read(self, reader: rtc.TextStreamReader) -> None:
        text = ""
        async for chunk in reader:
            if self.first_text_at is None and chunk.strip():
                self.first_text_at = time.perf_counter()
            text += chunk
            self.last_message_at = time.perf_counter()
        self.replies.append(text.strip())

    def _on_attributes(self, changed: dict[str, str], participant: rtc.Participant) -> None:
        if AGENT_STATE_ATTRIBUTE in changed:
            self.agent_state = changed[AGENT_STATE_ATTRIBUTE]

    async def say(self, line: str | None) -> float | None:
        """Types a line (None: just waits for the greeting); seconds to the reply's first text."""
        replies_before = len(self.replies)
        self.first_text_at = None
        sent_at = time.perf_counter()
        if line is not None:
            await self.room.local_participant.send_text(line, topic=CHAT_TOPIC)
        deadline = sent_at + REPLY_TIMEOUT_SECONDS
        while time.perf_counter() < deadline and not self.ended.is_set():
            quiet = time.perf_counter() - self.last_message_at >= QUIET_SECONDS
            if len(self.replies) > replies_before and quiet and self.agent_state == LISTENING:
                break
            await asyncio.sleep(0.1)
        return None if self.first_text_at is None else self.first_text_at - sent_at

    async def leave(self) -> None:
        if not self.ended.is_set():
            await self.room.disconnect()


async def free_day(
    api: httpx.AsyncClient,
    doctor: str,
    needed: int,
    earliest: str = "00:00",
    not_on: date | None = None,
) -> tuple[date, list[str]]:
    """A day in the next two months with `needed` free times from `earliest` on, so
    scenarios never take each other's slot and re-runs never collide."""
    for offset in range(1, DAYS_AHEAD):
        day = date.today() + timedelta(days=offset)
        if day == not_on:
            continue
        response = await api.get(
            f"{DEMO_CLINIC}/availability", params={"doctor": doctor, "day": day.isoformat()}
        )
        free = [time for time in response.json()["free_times"] if time >= earliest]
        if len(free) >= needed:
            return day, free
    raise RuntimeError(f"no day with {needed} free times for {doctor} in the next two months")


def spoken_day(day: date) -> str:
    return f"{day.day} {day:%B}"


def spoken_clock(clock: str) -> str:
    hour, minute = (int(part) for part in clock.split(":"))
    suffix = "am" if hour < 12 else "pm"
    return f"{hour % 12 or 12}:{minute:02d} {suffix}"


async def build_scenarios(api: httpx.AsyncClient) -> list[Scenario]:
    day, (booked, read_back, changed, taken, instead, *_) = await free_day(
        api, DOCTOR, SLOTS_NEEDED
    )
    when = spoken_day(day)
    physician_day, (physician_time, *_) = await free_day(api, PHYSICIAN, 1)
    afternoon_day, afternoon_times = await free_day(api, DOCTOR, 1, AFTERNOON, not_on=day)
    asking = f"I want to book an appointment with the {DOCTOR} doctor."
    patient = "My name is Rohan Gupta and I am 34 years old."
    # Someone else takes this slot first, so the booking gets 409 and the flow goes back.
    someone_else = await api.post(
        f"{DEMO_CLINIC}/appointments",
        json={
            "patient_name": "Asha Rao",
            "patient_age": 41,
            "doctor": DOCTOR,
            "day": day.isoformat(),
            "time": taken,
        },
    )
    someone_else.raise_for_status()
    return [
        Scenario(
            "booking",
            [asking, patient, f"{when}, please.", f"{spoken_clock(booked)} works.", "Yes."],
            ("booked",),
            {"patient_name": "Rohan Gupta", "patient_age": 34, "time": booked},
        ),
        Scenario(
            "changes a detail at the read-back",
            [
                asking,
                patient,
                f"{when}, please.",
                f"{spoken_clock(read_back)} works.",
                "No, I'd like a different time.",
                f"{spoken_clock(changed)}, please.",
                "Yes, that's right.",
            ],
            ("booked",),
            {"time": changed},
        ),
        Scenario(
            "slot taken at booking",
            [
                asking,
                patient,
                f"{when}, please.",
                f"{spoken_clock(taken)} please.",
                "Yes.",
                f"Then {spoken_clock(instead)} on the same day.",
                "Yes.",
            ],
            ("booked",),
            {"time": instead},
        ),
        # The caller names no doctor: the agent must ask, naming the doctors, and book the one
        # chosen (a phone call once saved "doctor appointment" as the doctor).
        Scenario(
            "doctor not named",
            [
                "I want to book a doctor appointment.",
                patient,
                f"{spoken_day(physician_day)}, please.",
                "A general physician, please.",
                f"{spoken_clock(physician_time)} works.",
                "Yes.",
            ],
            ("booked",),
            {"doctor": "Dr. Anil Sharma", "time": physician_time},
            expected_in_replies=("Mehta",),
        ),
        # A vague time: the booked time must be one the clinic said was free, never made up
        # (the same phone call once got 12:00 for "the afternoon" without any check).
        Scenario(
            "asks for the afternoon",
            [
                asking,
                patient,
                f"{spoken_day(afternoon_day)}, please.",
                "Something in the afternoon, please.",
                "The earliest of those is fine.",
                "Yes.",
            ],
            ("booked",),
            {"time": set(afternoon_times)},
        ),
        Scenario("asks for a person", ["Can I talk to a person, please?"], ("transfer_requested",)),
        # The scenario agent has no knowledge base, so this only checks the question path:
        # a reply, no booking. It may answer and stay, or say goodbye ("answered").
        Scenario("asks a question", ["What are your opening hours?"], (None, "answered")),
    ]


async def clinic_agent(api: httpx.AsyncClient) -> str:
    """The scenario agent, with the clinic template's current flow as its draft."""
    templates = (await api.get("/agent-templates")).json()
    template = next(t for t in templates if t["id"] == TEMPLATE_ID)
    agents = (await api.get("/agents")).json()
    agent = next((a for a in agents if a["name"] == AGENT_NAME), None)
    if agent is None:
        created = await api.post(
            "/agents/from-template", json={"template_id": TEMPLATE_ID, "name": AGENT_NAME}
        )
        return created.raise_for_status().json()["id"]
    (await api.put(f"/agents/{agent['id']}/flow", json=template["flow"])).raise_for_status()
    return agent["id"]


def matches(actual: object, expected: object) -> bool:
    return actual in expected if isinstance(expected, set) else actual == expected


async def run(api: httpx.AsyncClient, agent_id: str, scenario: Scenario) -> Result:
    response = await api.post(f"/agents/{agent_id}/browser-calls")
    browser_call = response.raise_for_status().json()
    call = TesterCall()
    await call.join(browser_call["url"], browser_call["token"])
    await call.say(None)
    seconds = [await call.say(line) for line in scenario.lines]
    await call.leave()
    await asyncio.sleep(RECORD_WAIT_SECONDS)
    calls = (await api.get("/calls", params={"agent_id": agent_id, "limit": 20})).json()
    record = next((c for c in calls if c["room_name"] == browser_call["room"]), None)
    timed = [s for s in seconds if s is not None]
    if record is None:
        return Result(scenario, False, None, timed, call.replies, "no call record")
    wrong = {
        name: record["fields"].get(name)
        for name, value in scenario.expected_fields.items()
        if not matches(record["fields"].get(name), value)
    }
    said = " ".join(call.replies)
    unsaid = [words for words in scenario.expected_in_replies if words not in said]
    outcome_ok = record["outcome"] in scenario.expected_outcomes
    passed = outcome_ok and not wrong and not unsaid and None not in seconds
    if passed:
        problem = ""
    elif wrong:
        problem = f"fields {wrong}"
    elif unsaid:
        problem = f"never said {unsaid}"
    else:
        problem = "unexpected outcome or no reply"
    return Result(scenario, passed, record["outcome"], timed, call.replies, problem)


def report(results: list[Result]) -> dict:
    for result in results:
        mark = "PASS" if result.passed else "FAIL"
        median = statistics.median(result.reply_seconds) if result.reply_seconds else 0
        print(
            f"{mark}  {result.scenario.name:40} outcome={result.outcome!s:20} "
            f"median reply {median:.2f}s  {result.problem}"
        )
        print(f"        reply seconds: {[round(s, 2) for s in result.reply_seconds]}")
        if not result.passed:
            for reply in result.replies:
                print(f"        agent: {reply}")
    all_seconds = sorted(s for r in results for s in r.reply_seconds)
    summary = {
        "pass_rate": sum(r.passed for r in results) / len(results),
        "median_reply_seconds": round(statistics.median(all_seconds), 3),
        "p95_reply_seconds": round(all_seconds[int(0.95 * (len(all_seconds) - 1))], 3),
        "replies": len(all_seconds),
    }
    print(json.dumps(summary, indent=2))
    return summary


def regressed(summary: dict) -> bool:
    if not BASELINE_FILE.exists():
        print("no baseline yet (--save-baseline to keep this run as one)")
        return False
    baseline = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
    slower = summary["median_reply_seconds"] > baseline["median_reply_seconds"] * ALLOWED_SLOWDOWN
    fewer = summary["pass_rate"] < baseline["pass_rate"]
    print(f"baseline: {baseline}")
    return slower or fewer


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--save-baseline", action="store_true")
    args = parser.parse_args()
    async with httpx.AsyncClient(base_url=API, timeout=10) as api:
        agent_id = await clinic_agent(api)
        results = [await run(api, agent_id, scenario) for scenario in await build_scenarios(api)]
    summary = report(results)
    if args.save_baseline:
        BASELINE_FILE.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        return 0
    return 1 if regressed(summary) or summary["pass_rate"] < 1 else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
