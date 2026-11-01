"""What every after-call action is built from: the call, its agent and its analysis."""

from typing import Any

from studio_api.agents.models import Agent
from studio_api.calls.models import Call
from studio_api.config import Settings


def call_url(settings: Settings, call: Call) -> str:
    return f"{settings.console_url.rstrip('/')}/calls/{call.id}"


def duration_seconds(call: Call) -> float | None:
    if call.ended_at is None:
        return None
    return round((call.ended_at - call.started_at).total_seconds(), 1)


def call_payload(event: str, call: Call, agent: Agent, settings: Settings) -> dict[str, Any]:
    analysis = call.analysis or {}
    return {
        "event": event,
        "call": {
            "id": call.id,
            "url": call_url(settings, call),
            "agent": {"id": agent.id, "name": agent.name},
            "channel": call.channel,
            "direction": call.direction,
            "remote_number": call.remote_number,
            "started_at": call.started_at.isoformat(),
            "ended_at": call.ended_at.isoformat() if call.ended_at else None,
            "duration_seconds": duration_seconds(call),
            "outcome": call.outcome,
            "fields": call.fields,
            "transcript": call.transcript,
            "analysis_status": call.analysis_status,
            "summary": analysis.get("summary"),
            "successful": analysis.get("successful"),
            "sentiment": analysis.get("sentiment"),
            "analysis_fields": analysis.get("fields", {}),
            "cost_usd": (call.cost or {}).get("total"),
        },
    }
