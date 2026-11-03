from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from studio_backend.agents.service import AgentNotFoundError
from studio_backend.core.database import SessionDep
from studio_backend.core.internal_auth import RuntimeAuthDep
from studio_backend.phone_numbers import service
from studio_backend.phone_numbers.schemas import (
    OutboundCall,
    OutboundCallStart,
    PhoneNumberCreate,
    PhoneNumberRead,
    PhoneNumberUpdate,
    RuntimeNumber,
)
from studio_backend.phone_numbers.telephony import Telephony, TelephonyError, get_telephony

router = APIRouter(tags=["numbers"])
runtime_router = APIRouter(prefix="/runtime", tags=["runtime"], dependencies=[RuntimeAuthDep])

TelephonyDep = Annotated[Telephony, Depends(get_telephony)]


def number_not_found(number_id: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"phone number {number_id} not found")


def agent_not_found(error: AgentNotFoundError) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"agent {error} not found")


def livekit_failed(error: TelephonyError) -> HTTPException:
    return HTTPException(status.HTTP_502_BAD_GATEWAY, f"LiveKit: {error.message}")


@router.get("/phone-numbers")
async def list_numbers(session: SessionDep) -> list[PhoneNumberRead]:
    return [PhoneNumberRead.model_validate(n) for n in await service.list_numbers(session)]


@router.post("/phone-numbers", status_code=status.HTTP_201_CREATED)
async def add_number(
    body: PhoneNumberCreate, session: SessionDep, telephony: TelephonyDep
) -> PhoneNumberRead:
    try:
        return PhoneNumberRead.model_validate(await service.add_number(session, telephony, body))
    except AgentNotFoundError as error:
        raise agent_not_found(error) from error
    except service.NumberAlreadyAddedError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, f"{error} is already added") from error
    except TelephonyError as error:
        raise livekit_failed(error) from error


@router.patch("/phone-numbers/{number_id}")
async def update_number(
    number_id: str, body: PhoneNumberUpdate, session: SessionDep
) -> PhoneNumberRead:
    try:
        return PhoneNumberRead.model_validate(await service.update_number(session, number_id, body))
    except service.PhoneNumberNotFoundError as error:
        raise number_not_found(number_id) from error
    except AgentNotFoundError as error:
        raise agent_not_found(error) from error


@router.delete("/phone-numbers/{number_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_number(number_id: str, session: SessionDep, telephony: TelephonyDep) -> None:
    try:
        await service.delete_number(session, telephony, number_id)
    except service.PhoneNumberNotFoundError as error:
        raise number_not_found(number_id) from error
    except TelephonyError as error:
        raise livekit_failed(error) from error


@router.post("/agents/{agent_id}/phone-calls", status_code=status.HTTP_201_CREATED)
async def start_outbound_call(
    agent_id: str, body: OutboundCallStart, session: SessionDep, telephony: TelephonyDep
) -> OutboundCall:
    try:
        room = await service.start_outbound_call(session, telephony, agent_id, body)
    except AgentNotFoundError as error:
        raise agent_not_found(error) from error
    except service.PhoneNumberNotFoundError as error:
        raise number_not_found(body.from_number_id) from error
    except service.CannotCallOutError as error:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"{error} has no outbound trunk, so it cannot call out"
        ) from error
    except TelephonyError as error:
        raise livekit_failed(error) from error
    return OutboundCall(room=room)


@runtime_router.get("/phone-numbers/{number_id}")
async def read_runtime_number(number_id: str, session: SessionDep) -> RuntimeNumber:
    try:
        return RuntimeNumber.model_validate(await service.get_number(session, number_id))
    except service.PhoneNumberNotFoundError as error:
        raise number_not_found(number_id) from error
