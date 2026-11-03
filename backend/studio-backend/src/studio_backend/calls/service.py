from collections import Counter
from datetime import timedelta
from statistics import quantiles

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from studio_backend.agents.models import Agent
from studio_backend.agents.service import get_agent
from studio_backend.calls.constants import (
    ANALYSIS_PENDING,
    ANALYSIS_SKIPPED,
    ENDED_STATUS,
    LATENCY_FIELD,
    NO_OUTCOME,
    PHONE_CHANNEL,
    USER_ROLE,
)
from studio_backend.calls.costs import call_cost
from studio_backend.calls.models import Call
from studio_backend.calls.schemas import AgentSuccess, CallEnd, CallStart, DayCount, Metrics
from studio_backend.campaigns.service import record_call_outcome
from studio_backend.config import Settings
from studio_backend.database import assume_utc, utc_now

PERCENTILES = 100


class CallNotFoundError(LookupError):
    pass


async def start_call(session: AsyncSession, start: CallStart) -> Call:
    await get_agent(session, start.agent_id)
    call = Call(**start.model_dump())
    session.add(call)
    await session.commit()
    return call


async def get_call(session: AsyncSession, call_id: str) -> Call:
    call = await session.get(Call, call_id)
    if call is None:
        raise CallNotFoundError(call_id)
    return call


def duration_seconds(call: Call) -> float:
    if call.ended_at is None:
        return 0.0
    return (assume_utc(call.ended_at) - assume_utc(call.started_at)).total_seconds()


async def end_call(session: AsyncSession, call_id: str, end: CallEnd, settings: Settings) -> Call:
    """Idempotent: a second end (e.g. a retried request) keeps the first end time. Prices the
    call, and marks it for post-call analysis unless the caller never spoke."""
    call = await get_call(session, call_id)
    if call.status != ENDED_STATUS:
        call.status = ENDED_STATUS
        call.ended_at = utc_now()
        call.transcript = [turn.model_dump() for turn in end.transcript]
        call.outcome = end.outcome
        call.fields = end.fields
        call.flow_path = end.flow_path
        call.turn_latency_ms = end.turn_latency_ms
        call.interruptions = end.interruptions
        call.usage = end.usage
        call.tool_calls = end.tool_calls
        agent = await get_agent(session, call.agent_id)
        phone_seconds = duration_seconds(call) if call.channel == PHONE_CHANNEL else 0.0
        call.cost = call_cost(end.usage, agent.llm_model, phone_seconds, settings)
        spoke = any(turn.role == USER_ROLE for turn in end.transcript)
        call.analysis_status = ANALYSIS_PENDING if spoke else ANALYSIS_SKIPPED
        if call.campaign_contact_id is not None:
            await record_call_outcome(
                session, call.campaign_contact_id, call.room_name, end.outcome, utc_now()
            )
        await session.commit()
    return call


async def list_calls(
    session: AsyncSession,
    limit: int,
    agent_id: str | None = None,
    channel: str | None = None,
    direction: str | None = None,
    outcome: str | None = None,
) -> list[Call]:
    query = select(Call).order_by(Call.started_at.desc()).limit(limit)
    for column, value in (
        (Call.agent_id, agent_id),
        (Call.channel, channel),
        (Call.direction, direction),
        (Call.outcome, outcome),
    ):
        if value is not None:
            query = query.where(column == value)
    return list(await session.scalars(query))


def percentile(values: list[float], wanted: int) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    return round(quantiles(values, n=PERCENTILES, method="inclusive")[wanted - 1], 1)


async def metrics(session: AsyncSession, days: int) -> Metrics:
    """The dashboard over the last `days` days (ended calls; today counts as a day)."""
    since = utc_now() - timedelta(days=days)
    calls = [
        call
        for call in await session.scalars(select(Call).where(Call.status == ENDED_STATUS))
        if assume_utc(call.started_at) >= since
    ]
    per_day = Counter(assume_utc(call.started_at).date().isoformat() for call in calls)
    first_day = since.date()
    day_list = [
        DayCount(day=(first_day + timedelta(days=n)).isoformat(), calls=0)
        for n in range(1, days + 1)
    ]
    for entry in day_list:
        entry.calls = per_day.get(entry.day, 0)
    costs = [call.cost["total"] for call in calls if "total" in (call.cost or {})]
    durations = [duration_seconds(call) for call in calls]
    latencies = [
        turn[LATENCY_FIELD]
        for call in calls
        for turn in call.turn_latency_ms
        if LATENCY_FIELD in turn
    ]
    names = {agent.id: agent.name for agent in await session.scalars(select(Agent))}
    by_agent: dict[str, AgentSuccess] = {}
    for call in calls:
        row = by_agent.setdefault(
            call.agent_id,
            AgentSuccess(
                agent_id=call.agent_id,
                name=names.get(call.agent_id, call.agent_id),
                calls=0,
                analysed=0,
                successful=0,
            ),
        )
        row.calls += 1
        if "successful" in (call.analysis or {}):
            row.analysed += 1
            row.successful += bool(call.analysis["successful"])
    return Metrics(
        days=day_list,
        calls=len(calls),
        outcomes=dict(Counter(call.outcome or NO_OUTCOME for call in calls)),
        average_cost=round(sum(costs) / len(costs), 5) if costs else None,
        total_cost=round(sum(costs), 5),
        average_duration_seconds=round(sum(durations) / len(durations), 1) if durations else None,
        latency_p50_ms=percentile(latencies, 50),
        latency_p95_ms=percentile(latencies, 95),
        agents=sorted(by_agent.values(), key=lambda row: row.calls, reverse=True),
    )
