"""Exports the read-only demo's data from the running API into console/public/demo-data/.

Only the showcase agents (renamed for visitors) and their calls, campaigns and flows go out.
Phone numbers outside the test range are replaced, links to private dashboards are dropped,
secret previews are hidden, and the export fails if anything that looks private is left.

    api\\.venv\\Scripts\\python.exe tools\\showcase\\export_fixtures.py
"""

import hashlib
import json
import re
import shutil
import sys
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

from studio_api.calls.service import percentile

API = "http://localhost:8000"
OUT = Path(__file__).parents[2] / "console" / "public" / "demo-data"
# Agent name in the database -> name visitors see. Agents not listed (the customer personas
# answering campaign calls, one-off checks) stay out, with their calls.
SHOWCASE_AGENTS = {
    "Clinic booking (scenario runs)": "City Hospital receptionist",
    "Clinic booking (Cal.com check)": "City Hospital receptionist (Cal.com)",
    "Reminder (campaign runs)": "Appointment reminders",
}
MAX_CALLS = 120
METRIC_PERIODS = (7, 14, 30)
LATENCY_FIELD = "e2e_latency"
NO_OUTCOME = "none"
# Numbers in this range are reserved for tests (no real line has them); others are replaced.
TEST_NUMBER = re.compile(r"\+1500555\d{4}")
PHONE_NUMBER = re.compile(r"\+\d{8,15}")
PRIVATE_PATTERNS = (
    re.compile(r"cal_live_\w+"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"pat-[a-z0-9-]{10,}"),
    re.compile(r"whsec_\w+"),
    re.compile(r"@gmail\.com"),
    re.compile(r"dustin", re.IGNORECASE),
)


def masked_number(number: str) -> str:
    if TEST_NUMBER.fullmatch(number):
        return number
    digest = int(hashlib.sha256(number.encode()).hexdigest(), 16) % 10_000
    return f"+1500555{digest:04d}"


def mask(value):
    """Every phone number in a JSON value, replaced unless it is a test number."""
    if isinstance(value, str):
        return PHONE_NUMBER.sub(lambda match: masked_number(match.group()), value)
    if isinstance(value, dict):
        return {key: mask(item) for key, item in value.items()}
    if isinstance(value, list):
        return [mask(item) for item in value]
    return value


def write(path: str, data) -> None:
    file = OUT / f"{path}.json"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def parse_time(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def metrics(calls: list[dict], names: dict[str, str], days: int) -> dict:
    """The dashboard for the exported calls only, as `calls.service.metrics` computes it."""
    since = datetime.now(UTC) - timedelta(days=days)
    calls = [c for c in calls if c["status"] == "ended" and parse_time(c["started_at"]) >= since]
    per_day = Counter(parse_time(c["started_at"]).date().isoformat() for c in calls)
    day_list = [(since.date() + timedelta(days=n)).isoformat() for n in range(1, days + 1)]
    costs = [c["cost"]["total"] for c in calls if "total" in c["cost"]]
    durations = [
        (parse_time(c["ended_at"]) - parse_time(c["started_at"])).total_seconds()
        for c in calls
        if c["ended_at"]
    ]
    latencies = [
        t[LATENCY_FIELD] for c in calls for t in c["turn_latency_ms"] if LATENCY_FIELD in t
    ]
    agents: dict[str, dict] = {}
    for call in calls:
        row = agents.setdefault(
            call["agent_id"],
            {"agent_id": call["agent_id"], "name": names[call["agent_id"]], "calls": 0,
             "analysed": 0, "successful": 0},
        )  # fmt: skip
        row["calls"] += 1
        if "successful" in call["analysis"]:
            row["analysed"] += 1
            row["successful"] += bool(call["analysis"]["successful"])
    return {
        "days": [{"day": day, "calls": per_day.get(day, 0)} for day in day_list],
        "calls": len(calls),
        "outcomes": dict(Counter(c["outcome"] or NO_OUTCOME for c in calls)),
        "average_cost": round(sum(costs) / len(costs), 5) if costs else None,
        "total_cost": round(sum(costs), 5),
        "average_duration_seconds": round(sum(durations) / len(durations), 1)
        if durations
        else None,
        "latency_p50_ms": percentile(latencies, 50),
        "latency_p95_ms": percentile(latencies, 95),
        "agents": sorted(agents.values(), key=lambda row: row["calls"], reverse=True),
    }


def public_call(call: dict) -> dict:
    """No links to private dashboards (Langfuse, LiveKit), and no unended calls."""
    return {**call, "langfuse_url": None, "recording_url": None}


def keep_call(call: dict) -> bool:
    # Phone calls from a real handset (not a test number) stay out: they may carry a voice.
    number = call["remote_number"]
    return call["status"] == "ended" and (number is None or bool(TEST_NUMBER.fullmatch(number)))


def check_private(root: Path) -> list[str]:
    found = []
    for file in root.rglob("*.json"):
        text = file.read_text(encoding="utf-8")
        found += [
            f"{file.relative_to(root)}: {p.pattern}" for p in PRIVATE_PATTERNS if p.search(text)
        ]
        for number in PHONE_NUMBER.findall(text):
            if not TEST_NUMBER.fullmatch(number):
                found.append(f"{file.relative_to(root)}: unmasked number")
    return found


def main() -> int:
    api = httpx.Client(base_url=API, timeout=30)
    get = lambda path, **params: api.get(path, params=params).raise_for_status().json()  # noqa: E731
    agents = [a for a in get("/agents") if a["name"] in SHOWCASE_AGENTS]
    missing = set(SHOWCASE_AGENTS) - {a["name"] for a in agents}
    if missing:
        print(f"missing agents: {sorted(missing)}")
        return 1
    for agent in agents:
        agent["name"] = SHOWCASE_AGENTS[agent["name"]]
    names = {agent["id"]: agent["name"] for agent in agents}
    shutil.rmtree(OUT, ignore_errors=True)

    calls = []
    for agent in agents:
        calls += [public_call(c) for c in get("/calls", agent_id=agent["id"], limit=200)]
    calls = sorted(filter(keep_call, calls), key=lambda c: c["started_at"], reverse=True)
    calls = mask(calls[:MAX_CALLS])
    write("calls", calls)
    for call in calls:
        write(f"calls/{call['id']}/deliveries", get(f"/calls/{call['id']}/deliveries"))
    for days in METRIC_PERIODS:
        write(f"metrics-{days}", metrics(calls, names, days))

    write("agents", agents)
    write("agent-templates", get("/agent-templates"))
    for agent in agents:
        write(f"agents/{agent['id']}/flow", mask(get(f"/agents/{agent['id']}/flow")))
        write(f"agents/{agent['id']}/flow/versions", get(f"/agents/{agent['id']}/flow/versions"))

    campaigns = [c for c in get("/campaigns") if c["agent_id"] in names]
    write("campaigns", campaigns)
    for campaign in campaigns:
        write(
            f"campaigns/{campaign['id']}/contacts",
            mask(get(f"/campaigns/{campaign['id']}/contacts")),
        )

    numbers = mask(get("/phone-numbers"))
    for number in numbers:
        if number["agent_id"] not in names:
            number["agent_id"] = None
    write("phone-numbers", [n for n in numbers if n["agent_id"] or n["can_call_out"]])

    knowledge_bases = get("/knowledge-bases")
    write("knowledge-bases", knowledge_bases)
    for base in knowledge_bases:
        write(
            f"knowledge-bases/{base['id']}/documents",
            get(f"/knowledge-bases/{base['id']}/documents"),
        )

    write("secrets", [{**s, "preview": "••••"} for s in get("/secrets")])

    problems = check_private(OUT)
    if problems:
        print("private data left in the export:\n  " + "\n  ".join(problems))
        return 1
    size = sum(f.stat().st_size for f in OUT.rglob("*.json"))
    print(f"exported {len(agents)} agents, {len(calls)} calls, {len(campaigns)} campaigns "
          f"({size / 1024:.0f} KB) to {OUT}")  # fmt: skip
    return 0


if __name__ == "__main__":
    sys.exit(main())
