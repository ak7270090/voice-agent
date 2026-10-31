from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from studio_api.agents.service import get_agent
from studio_api.database import new_id
from studio_api.numbers.constants import (
    OUTBOUND_CALL_ROOM_PREFIX,
    PHONE_CHANNEL,
    SIP_TRUNK_PROVIDER,
)
from studio_api.numbers.models import PhoneNumber
from studio_api.numbers.schemas import OutboundCallStart, PhoneNumberCreate, PhoneNumberUpdate
from studio_api.numbers.telephony import Telephony


class PhoneNumberNotFoundError(LookupError):
    pass


class NumberAlreadyAddedError(ValueError):
    pass


class CannotCallOutError(ValueError):
    pass


async def list_numbers(session: AsyncSession) -> list[PhoneNumber]:
    return list(await session.scalars(select(PhoneNumber).order_by(PhoneNumber.created_at)))


async def get_number(session: AsyncSession, number_id: str) -> PhoneNumber:
    number = await session.get(PhoneNumber, number_id)
    if number is None:
        raise PhoneNumberNotFoundError(number_id)
    return number


async def add_number(
    session: AsyncSession, telephony: Telephony, body: PhoneNumberCreate
) -> PhoneNumber:
    """Creates LiveKit's side first; if any part fails, the parts already made are removed."""
    if body.agent_id is not None:
        await get_agent(session, body.agent_id)
    taken = await session.scalar(select(PhoneNumber).where(PhoneNumber.number == body.number))
    if taken is not None:
        raise NumberAlreadyAddedError(body.number)
    number = PhoneNumber(
        id=new_id(),
        number=body.number,
        label=body.label,
        provider=body.provider,
        agent_id=body.agent_id,
    )
    try:
        if body.provider == SIP_TRUNK_PROVIDER:
            number.inbound_trunk_id = await telephony.create_inbound_trunk(body.number)
        if body.outbound is not None:
            number.outbound_trunk_id = await telephony.create_outbound_trunk(
                body.number, body.outbound
            )
        number.dispatch_rule_id = await telephony.create_dispatch_rule(
            number.id, body.number, number.inbound_trunk_id
        )
    except Exception:
        await _remove_from_livekit(telephony, number)
        raise
    session.add(number)
    await session.commit()
    return number


async def update_number(
    session: AsyncSession, number_id: str, changes: PhoneNumberUpdate
) -> PhoneNumber:
    number = await get_number(session, number_id)
    changed = changes.model_dump(exclude_unset=True)
    if changed.get("agent_id") is not None:
        await get_agent(session, changed["agent_id"])
    for field, value in changed.items():
        setattr(number, field, value)
    await session.commit()
    return number


async def delete_number(session: AsyncSession, telephony: Telephony, number_id: str) -> None:
    number = await get_number(session, number_id)
    await _remove_from_livekit(telephony, number)
    await session.delete(number)
    await session.commit()


async def _remove_from_livekit(telephony: Telephony, number: PhoneNumber) -> None:
    trunk_ids = [
        trunk_id for trunk_id in (number.inbound_trunk_id, number.outbound_trunk_id) if trunk_id
    ]
    if number.dispatch_rule_id or trunk_ids:
        await telephony.delete(number.dispatch_rule_id, trunk_ids)


async def start_outbound_call(
    session: AsyncSession, telephony: Telephony, agent_id: str, body: OutboundCallStart
) -> str:
    """Dispatches the runtime into a new room with the number to dial; returns the room."""
    agent = await get_agent(session, agent_id)
    number = await get_number(session, body.from_number_id)
    if not number.can_call_out:
        raise CannotCallOutError(number.number)
    room = f"{OUTBOUND_CALL_ROOM_PREFIX}{uuid4().hex[:10]}"
    await telephony.dispatch_outbound_call(
        room,
        {
            "agent_id": agent.id,
            "channel": PHONE_CHANNEL,
            "dial_to": body.to_number,
            "outbound_trunk_id": number.outbound_trunk_id,
        },
    )
    return room
