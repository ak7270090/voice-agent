from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from studio_api.agents.service import AgentNotFoundError
from studio_api.calls import service
from studio_api.calls.schemas import CallEnd, CallRead, CallStart
from studio_api.database import SessionDep
from studio_api.security import RuntimeAuthDep

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200

router = APIRouter(tags=["calls"])
runtime_router = APIRouter(prefix="/runtime", tags=["runtime"], dependencies=[RuntimeAuthDep])


def call_not_found(call_id: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"call {call_id} not found")


@router.get("/calls")
async def list_calls(
    session: SessionDep,
    agent_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
) -> list[CallRead]:
    calls = await service.list_calls(session, agent_id, limit)
    return [CallRead.model_validate(call) for call in calls]


@router.get("/calls/{call_id}")
async def read_call(call_id: str, session: SessionDep) -> CallRead:
    try:
        return CallRead.model_validate(await service.get_call(session, call_id))
    except service.CallNotFoundError as error:
        raise call_not_found(call_id) from error


@runtime_router.post("/calls", status_code=status.HTTP_201_CREATED)
async def start_call(body: CallStart, session: SessionDep) -> CallRead:
    try:
        return CallRead.model_validate(await service.start_call(session, body))
    except AgentNotFoundError as error:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"agent {body.agent_id} not found"
        ) from error


@runtime_router.post("/calls/{call_id}/end")
async def end_call(call_id: str, body: CallEnd, session: SessionDep) -> CallRead:
    try:
        return CallRead.model_validate(await service.end_call(session, call_id, body))
    except service.CallNotFoundError as error:
        raise call_not_found(call_id) from error
