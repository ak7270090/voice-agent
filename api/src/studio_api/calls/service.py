from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from studio_api.agents.service import get_agent
from studio_api.calls.constants import ENDED_STATUS
from studio_api.calls.models import Call
from studio_api.calls.schemas import CallEnd, CallStart
from studio_api.campaigns.service import record_call_outcome
from studio_api.database import utc_now


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


async def end_call(session: AsyncSession, call_id: str, end: CallEnd) -> Call:
    """Idempotent: a second end (e.g. a retried request) keeps the first end time."""
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
        if call.campaign_contact_id is not None:
            await record_call_outcome(
                session, call.campaign_contact_id, call.room_name, end.outcome, utc_now()
            )
        await session.commit()
    return call


async def list_calls(session: AsyncSession, agent_id: str | None, limit: int) -> list[Call]:
    query = select(Call).order_by(Call.started_at.desc()).limit(limit)
    if agent_id is not None:
        query = query.where(Call.agent_id == agent_id)
    return list(await session.scalars(query))
